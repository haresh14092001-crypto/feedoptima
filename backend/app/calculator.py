from typing import List

from sqlalchemy.exc import OperationalError

from .ai import build_nutrition_prompt, generate_ai_explanation
from .crud import get_latest_price, list_ingredients
from .data.feed_data import get_feeds_by_category
from .data.standard_data import get_nutrient_targets
from .db import SessionLocal
from .models import FeedIngredient
from .schemas import Purpose, RationRequest, RationResponse, RationComponent


def _load_catalog_feeds() -> List[FeedIngredient]:
    with SessionLocal() as session:
        try:
            db_ingredients = list_ingredients(session)
        except OperationalError:
            return []

        if not db_ingredients:
            return []

        feed_ingredients: List[FeedIngredient] = []
        for ingredient in db_ingredients:
            latest_price = get_latest_price(session, ingredient)
            cost_per_kg = latest_price.price_per_kg if latest_price else getattr(ingredient, "default_price_per_kg", 0.0) or 0.0
            feed_ingredients.append(
                FeedIngredient(
                    name=ingredient.name,
                    category=ingredient.category,
                    dry_matter_pct=ingredient.dry_matter_pct,
                    crude_protein_pct=ingredient.crude_protein_pct,
                    energy_mj_per_kg=ingredient.energy_mj_per_kg,
                    cost_per_kg=cost_per_kg,
                )
            )
        return feed_ingredients


def _choose_cheapest_ingredient(category: str) -> FeedIngredient:
    feeds = [item for item in _load_catalog_feeds() if item.category == category]
    if not feeds:
        feeds = get_feeds_by_category(category)
    return min(feeds, key=lambda item: item.cost_per_kg)


def _estimate_component_weight(dry_matter_kg: float, ingredient: FeedIngredient) -> float:
    return dry_matter_kg / ingredient.dry_matter_pct


def _nutrition_from_ingredient(weight_kg: float, ingredient: FeedIngredient) -> tuple[float, float, float, float, float, float]:
    dm = weight_kg * ingredient.dry_matter_pct
    cp = dm * ingredient.crude_protein_pct
    energy = weight_kg * ingredient.energy_mj_per_kg
    calcium = weight_kg * ingredient.calcium_pct
    phosphorus = weight_kg * ingredient.phosphorus_pct
    fiber = weight_kg * ingredient.fiber_pct
    return dm, cp, energy, calcium, phosphorus, fiber


def _calculate_nutrition_score(
    components: List[RationComponent],
    target: NutrientTarget,
    total_cost: float,
    max_cost: float = 0.0
) -> float:
    """Calculate a score for ration quality (higher is better)"""
    if not components:
        return 0.0

    total_dm = sum(c.dry_matter_kg for c in components)
    total_cp = sum(c.dry_matter_kg * c.crude_protein_pct for c in components)
    total_energy = sum(c.energy_mj for c in components)
    total_calcium = sum(c.calcium_pct * c.weight_kg for c in components)
    total_phosphorus = sum(c.phosphorus_pct * c.weight_kg for c in components)
    total_fiber = sum(c.fiber_pct * c.weight_kg for c in components)

    # Calculate fulfillment percentages
    dm_score = min(total_dm / target.dry_matter_kg, 1.0) if target.dry_matter_kg > 0 else 1.0
    cp_score = min((total_cp / total_dm) / target.crude_protein_pct, 1.0) if target.crude_protein_pct > 0 else 1.0
    energy_score = min(total_energy / target.energy_mj, 1.0) if target.energy_mj > 0 else 1.0
    calcium_score = min(total_calcium / (target.dry_matter_kg * target.calcium_pct), 1.0) if target.calcium_pct > 0 else 1.0
    phosphorus_score = min(total_phosphorus / (target.dry_matter_kg * target.phosphorus_pct), 1.0) if target.phosphorus_pct > 0 else 1.0
    fiber_score = min(total_fiber / (target.dry_matter_kg * target.fiber_pct), 1.0) if target.fiber_pct > 0 else 1.0

    # Cost penalty (lower cost is better, but don't exceed max_cost)
    cost_penalty = 0.0
    if max_cost > 0:
        if total_cost > max_cost:
            cost_penalty = 1.0  # Severe penalty for exceeding budget
        else:
            cost_penalty = total_cost / max_cost * 0.3  # Moderate penalty for high cost

    # Weighted score (nutrition fulfillment minus cost penalty)
    nutrition_score = (dm_score + cp_score + energy_score + calcium_score + phosphorus_score + fiber_score) / 6.0
    final_score = nutrition_score - cost_penalty

    return max(0.0, final_score)  # Ensure non-negative


def _optimize_concentrate_mix_advanced(
    target: NutrientTarget,
    current_nutrition: tuple[float, float, float, float, float, float],  # dm, cp, energy, ca, p, fiber
    dm_target: float,
    max_cost: float = 0.0,
    preferred_feeds: List[str] = None,
    avoid_feeds: List[str] = None,
) -> List[RationComponent]:
    """Advanced optimization using multiple candidate combinations"""
    current_dm, current_cp, current_energy, current_ca, current_p, current_fiber = current_nutrition
    required_dm = max(0.0, dm_target - current_dm)

    if required_dm <= 0.01:  # Minimal concentrate needed
        return []

    candidates = [item for item in _load_catalog_feeds() if item.category in ["concentrate", "mineral_mix", "vitamin_premix"]]
    if not candidates:
        candidates = get_feeds_by_category("concentrate")

    # Filter based on preferences
    if preferred_feeds:
        preferred_candidates = [c for c in candidates if c.name in preferred_feeds]
        if preferred_candidates:
            candidates = preferred_candidates + [c for c in candidates if c not in preferred_candidates]

    if avoid_feeds:
        candidates = [c for c in candidates if c.name not in avoid_feeds]

    # Try different combinations (simplified approach - in production use linear programming)
    best_combination = []
    best_score = 0.0

    # Try single ingredient first
    for candidate in candidates[:5]:  # Limit to top 5 to avoid computation explosion
        weight = required_dm / candidate.dry_matter_pct
        cost = weight * candidate.cost_per_kg

        if max_cost > 0 and cost > max_cost:
            continue

        dm, cp, energy, ca, p, fiber = _nutrition_from_ingredient(weight, candidate)

        test_components = [RationComponent(
            name=candidate.name,
            category=candidate.category,
            weight_kg=round(weight, 2),
            dry_matter_kg=round(dm, 2),
            crude_protein_pct=candidate.crude_protein_pct,
            energy_mj=round(energy, 2),
            calcium_pct=candidate.calcium_pct,
            phosphorus_pct=candidate.phosphorus_pct,
            fiber_pct=candidate.fiber_pct,
            cost_inr=round(cost, 2),
            availability_score=candidate.availability_score,
        )]

        score = _calculate_nutrition_score(test_components, target, cost, max_cost)
        if score > best_score:
            best_score = score
            best_combination = test_components

    # Try two-ingredient combinations for better balance
    for i, primary in enumerate(candidates[:3]):
        for secondary in candidates[i+1:i+3]:
            if primary.name == secondary.name:
                continue

            # Simple ratio optimization
            for ratio in [0.3, 0.5, 0.7]:
                primary_weight = required_dm * ratio / primary.dry_matter_pct
                secondary_weight = required_dm * (1-ratio) / secondary.dry_matter_pct
                total_cost = primary_weight * primary.cost_per_kg + secondary_weight * secondary.cost_per_kg

                if max_cost > 0 and total_cost > max_cost:
                    continue

                p_dm, p_cp, p_energy, p_ca, p_p, p_fiber = _nutrition_from_ingredient(primary_weight, primary)
                s_dm, s_cp, s_energy, s_ca, s_p, s_fiber = _nutrition_from_ingredient(secondary_weight, secondary)

                test_components = [
                    RationComponent(
                        name=primary.name,
                        category=primary.category,
                        weight_kg=round(primary_weight, 2),
                        dry_matter_kg=round(p_dm, 2),
                        crude_protein_pct=primary.crude_protein_pct,
                        energy_mj=round(p_energy, 2),
                        calcium_pct=primary.calcium_pct,
                        phosphorus_pct=primary.phosphorus_pct,
                        fiber_pct=primary.fiber_pct,
                        cost_inr=round(primary_weight * primary.cost_per_kg, 2),
                        availability_score=primary.availability_score,
                    ),
                    RationComponent(
                        name=secondary.name,
                        category=secondary.category,
                        weight_kg=round(secondary_weight, 2),
                        dry_matter_kg=round(s_dm, 2),
                        crude_protein_pct=secondary.crude_protein_pct,
                        energy_mj=round(s_energy, 2),
                        calcium_pct=secondary.calcium_pct,
                        phosphorus_pct=secondary.phosphorus_pct,
                        fiber_pct=secondary.fiber_pct,
                        cost_inr=round(secondary_weight * secondary.cost_per_kg, 2),
                        availability_score=secondary.availability_score,
                    )
                ]

                score = _calculate_nutrition_score(test_components, target, total_cost, max_cost)
                if score > best_score:
                    best_score = score
                    best_combination = test_components

    return best_combination
    candidates = [item for item in _load_catalog_feeds() if item.category == "concentrate"]
    if not candidates:
        candidates = get_feeds_by_category("concentrate")

    primary = min(candidates, key=lambda item: item.cost_per_kg)
    secondary = max(candidates, key=lambda item: item.crude_protein_pct)
    required_dm = max(0.0, dm_target - current_dm)
    primary_weight = required_dm / primary.dry_matter_pct

    primary_dm, primary_cp, primary_energy = _nutrition_from_ingredient(primary_weight, primary)
    total_cp = current_cp_kg + primary_cp
    total_energy = current_energy_mj + primary_energy

    if total_cp >= target_cp_kg and total_energy >= target_energy_mj:
        return [
            RationComponent(
                name=primary.name,
                category=primary.category,
                weight_kg=round(primary_weight, 2),
                dry_matter_kg=round(primary_dm, 2),
                crude_protein_pct=primary.crude_protein_pct,
                energy_mj=round(primary_energy, 2),
                cost_inr=round(primary_weight * primary.cost_per_kg, 2),
            )
        ]

    second_weight = 0.0
    if secondary.name != primary.name:
        cp_short = max(0.0, target_cp_kg - total_cp)
        energy_short = max(0.0, target_energy_mj - total_energy)
        if cp_short > 0:
            second_weight = cp_short / (secondary.dry_matter_pct * secondary.crude_protein_pct)
            second_dm, second_cp, second_energy = _nutrition_from_ingredient(second_weight, secondary)
            total_cp += second_cp
            total_energy += second_energy
        if total_energy < target_energy_mj:
            energy_short = target_energy_mj - total_energy
            filler = primary
            filler_weight = energy_short / filler.energy_mj_per_kg
            primary_weight += filler_weight
            primary_dm, primary_cp, primary_energy = _nutrition_from_ingredient(primary_weight, primary)
            total_energy = current_energy_mj + primary_energy + second_energy

    output: List[RationComponent] = [
        RationComponent(
            name=primary.name,
            category=primary.category,
            weight_kg=round(primary_weight, 2),
            dry_matter_kg=round(primary_dm, 2),
            crude_protein_pct=primary.crude_protein_pct,
            energy_mj=round(primary_energy, 2),
            cost_inr=round(primary_weight * primary.cost_per_kg, 2),
        )
    ]
    if second_weight > 0.0:
        second_dm, second_cp, second_energy = _nutrition_from_ingredient(second_weight, secondary)
        output.append(
            RationComponent(
                name=secondary.name,
                category=secondary.category,
                weight_kg=round(second_weight, 2),
                dry_matter_kg=round(second_dm, 2),
                crude_protein_pct=secondary.crude_protein_pct,
                energy_mj=round(second_energy, 2),
                cost_inr=round(second_weight * secondary.cost_per_kg, 2),
            )
        )
    return output


def optimize_ration(request: RationRequest) -> RationResponse:
    target = get_nutrient_targets(
        species=request.species,
        purpose=request.purpose,
        body_weight_kg=request.body_weight_kg,
        milk_yield_lpd=request.milk_yield_lpd or 0.0,
    )

    proportion = {
        Purpose.dairy: {"green": 0.35, "dry": 0.35, "conc": 0.30},
        Purpose.growth: {"green": 0.25, "dry": 0.35, "conc": 0.40},
        Purpose.meat: {"green": 0.20, "dry": 0.35, "conc": 0.45},
        Purpose.maintenance: {"green": 0.30, "dry": 0.40, "conc": 0.30},
        Purpose.layer: {"green": 0.0, "dry": 0.20, "conc": 0.80},
        Purpose.broiler: {"green": 0.0, "dry": 0.20, "conc": 0.80},
    }[request.purpose]

    # Select feeds based on preferences and availability
    green_feeds = [item for item in _load_catalog_feeds() if item.category == "green_fodder"]
    if not green_feeds:
        green_feeds = get_feeds_by_category("green_fodder")

    dry_feeds = [item for item in _load_catalog_feeds() if item.category == "dry_fodder"]
    if not dry_feeds:
        dry_feeds = get_feeds_by_category("dry_fodder")

    # Prioritize preferred feeds, then by cost and availability
    def feed_priority(feed):
        priority = 0
        if request.preferred_feeds and feed.name in request.preferred_feeds:
            priority += 100
        if request.avoid_feeds and feed.name in request.avoid_feeds:
            priority -= 1000
        priority -= feed.cost_per_kg * 10  # Lower cost is better
        priority += feed.availability_score * 20  # Higher availability is better
        return priority

    green_feeds.sort(key=feed_priority, reverse=True)
    dry_feeds.sort(key=feed_priority, reverse=True)

    green = green_feeds[0] if green_feeds else get_feeds_by_category("green_fodder")[0]
    dry = dry_feeds[0] if dry_feeds else get_feeds_by_category("dry_fodder")[0]

    green_dm = target.dry_matter_kg * proportion["green"]
    dry_dm = target.dry_matter_kg * proportion["dry"]

    green_weight = _estimate_component_weight(green_dm, green)
    dry_weight = _estimate_component_weight(dry_dm, dry)

    # Calculate nutrition from roughages
    green_dm_actual, green_cp, green_energy, green_ca, green_p, green_fiber = _nutrition_from_ingredient(green_weight, green)
    dry_dm_actual, dry_cp, dry_energy, dry_ca, dry_p, dry_fiber = _nutrition_from_ingredient(dry_weight, dry)

    green_comp = RationComponent(
        name=green.name,
        category=green.category,
        weight_kg=round(green_weight, 2),
        dry_matter_kg=round(green_dm_actual, 2),
        crude_protein_pct=green.crude_protein_pct,
        energy_mj=round(green_energy, 2),
        calcium_pct=green.calcium_pct,
        phosphorus_pct=green.phosphorus_pct,
        fiber_pct=green.fiber_pct,
        cost_inr=round(green_weight * green.cost_per_kg, 2),
        availability_score=green.availability_score,
    )
    dry_comp = RationComponent(
        name=dry.name,
        category=dry.category,
        weight_kg=round(dry_weight, 2),
        dry_matter_kg=round(dry_dm_actual, 2),
        crude_protein_pct=dry.crude_protein_pct,
        energy_mj=round(dry_energy, 2),
        calcium_pct=dry.calcium_pct,
        phosphorus_pct=dry.phosphorus_pct,
        fiber_pct=dry.fiber_pct,
        cost_inr=round(dry_weight * dry.cost_per_kg, 2),
        availability_score=dry.availability_score,
    )

    current_nutrition = (
        green_comp.dry_matter_kg + dry_comp.dry_matter_kg,
        green_cp + dry_cp,
        green_comp.energy_mj + dry_comp.energy_mj,
        green_ca + dry_ca,
        green_p + dry_p,
        green_fiber + dry_fiber,
    )

    # Use advanced optimization for concentrates
    concentrate_components = _optimize_concentrate_mix_advanced(
        target=target,
        current_nutrition=current_nutrition,
        dm_target=target.dry_matter_kg,
        max_cost=request.max_cost_per_day or 0.0,
        preferred_feeds=request.preferred_feeds,
        avoid_feeds=request.avoid_feeds,
    )

    components = [green_comp, dry_comp] + concentrate_components
    total_cost = sum(component.cost_inr for component in components)
    total_dm = sum(component.dry_matter_kg for component in components)

    # Enhanced summary with nutritional balance
    nutritional_balance = []
    total_cp_pct = sum(c.dry_matter_kg * c.crude_protein_pct for c in components) / total_dm
    total_energy_per_kg = sum(c.energy_mj for c in components) / sum(c.weight_kg for c in components)
    total_ca_pct = sum(c.calcium_pct * c.weight_kg for c in components) / sum(c.weight_kg for c in components)
    total_p_pct = sum(c.phosphorus_pct * c.weight_kg for c in components) / sum(c.weight_kg for c in components)

    if total_cp_pct >= target.crude_protein_pct * 0.9:
        nutritional_balance.append("✓ Protein adequate")
    else:
        nutritional_balance.append("⚠ Protein may be low")

    if total_energy_per_kg >= target.energy_mj / target.dry_matter_kg * 0.9:
        nutritional_balance.append("✓ Energy adequate")
    else:
        nutritional_balance.append("⚠ Energy may be low")

    if total_ca_pct >= target.calcium_pct * 0.8:
        nutritional_balance.append("✓ Calcium adequate")
    else:
        nutritional_balance.append("⚠ Calcium may be low")

    if total_p_pct >= target.phosphorus_pct * 0.8:
        nutritional_balance.append("✓ Phosphorus adequate")
    else:
        nutritional_balance.append("⚠ Phosphorus may be low")

    summary = (
        f"Optimized ration for {request.species.value} ({request.purpose.value}) - "
        f"{total_dm:.1f} kg DM, ₹{total_cost:.0f}/day. "
        f"Nutritional balance: {' | '.join(nutritional_balance)}"
    )

    instructions = [
        f"Feed {green_comp.weight_kg:.1f} kg of {green_comp.name} and {dry_comp.weight_kg:.1f} kg of {dry_comp.name} as base roughages.",
        f"Add concentrates: {', '.join(f'{c.weight_kg:.1f} kg {c.name}' for c in concentrate_components)} to meet nutrient requirements.",
        "Monitor animal performance and adjust based on body condition, milk production, and health indicators.",
        "Test feed quality periodically as nutrient content can vary seasonally.",
        "Ensure constant access to clean water and mineral blocks.",
        target.notes,
    ]

    ai_notes = None
    if request.use_ai:
        prompt = build_nutrition_prompt(
            request_data=request.model_dump(),
            target_data=target.model_dump(),
            recommendation={
                "components": [component.model_dump() for component in components],
                "summary": summary,
                "nutritional_balance": nutritional_balance,
            },
        )
        ai_notes = generate_ai_explanation(prompt)

    return RationResponse(
        species=request.species,
        purpose=request.purpose,
        body_weight_kg=request.body_weight_kg,
        milk_yield_lpd=request.milk_yield_lpd or 0.0,
        total_dry_matter_kg=round(total_dm, 2),
        total_cost_inr=round(total_cost, 2),
        components=components,
        summary=summary,
        instructions=instructions,
        ai_notes=ai_notes,
    )
