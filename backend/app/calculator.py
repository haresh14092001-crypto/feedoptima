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


def _nutrition_from_ingredient(weight_kg: float, ingredient: FeedIngredient) -> tuple[float, float, float]:
    dm = weight_kg * ingredient.dry_matter_pct
    cp = dm * ingredient.crude_protein_pct
    energy = weight_kg * ingredient.energy_mj_per_kg
    return dm, cp, energy


def _build_concentrate_mix(
    target_cp_kg: float,
    target_energy_mj: float,
    current_cp_kg: float,
    current_energy_mj: float,
    current_dm: float,
    dm_target: float,
    species: str,
) -> List[RationComponent]:
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

    green = _choose_cheapest_ingredient("green_fodder")
    dry = _choose_cheapest_ingredient("dry_fodder")

    green_dm = target.dry_matter_kg * proportion["green"]
    dry_dm = target.dry_matter_kg * proportion["dry"]

    green_weight = _estimate_component_weight(green_dm, green)
    dry_weight = _estimate_component_weight(dry_dm, dry)

    green_comp = RationComponent(
        name=green.name,
        category=green.category,
        weight_kg=round(green_weight, 2),
        dry_matter_kg=round(green_dm, 2),
        crude_protein_pct=green.crude_protein_pct,
        energy_mj=round(green_weight * green.energy_mj_per_kg, 2),
        cost_inr=round(green_weight * green.cost_per_kg, 2),
    )
    dry_comp = RationComponent(
        name=dry.name,
        category=dry.category,
        weight_kg=round(dry_weight, 2),
        dry_matter_kg=round(dry_dm, 2),
        crude_protein_pct=dry.crude_protein_pct,
        energy_mj=round(dry_weight * dry.energy_mj_per_kg, 2),
        cost_inr=round(dry_weight * dry.cost_per_kg, 2),
    )

    current_dm = green_comp.dry_matter_kg + dry_comp.dry_matter_kg
    current_cp = green_comp.dry_matter_kg * green_comp.crude_protein_pct + dry_comp.dry_matter_kg * dry_comp.crude_protein_pct
    current_energy = green_comp.energy_mj + dry_comp.energy_mj
    target_cp_kg = target.dry_matter_kg * target.crude_protein_pct

    concentrate_components = _build_concentrate_mix(
        target_cp_kg=target_cp_kg,
        target_energy_mj=target.energy_mj,
        current_cp_kg=current_cp,
        current_energy_mj=current_energy,
        current_dm=current_dm,
        dm_target=target.dry_matter_kg,
        species=request.species.value,
    )

    components = [green_comp, dry_comp] + concentrate_components
    total_cost = sum(component.cost_inr for component in components)
    total_dm = sum(component.dry_matter_kg for component in components)

    summary = (
        f"Daily ration for {request.species.value} ({request.purpose.value}) target {target.dry_matter_kg} kg DM, "
        f"expected cost ₹{round(total_cost,2)}."
    )

    instructions = [
        f"Feed approximately {green_comp.weight_kg} kg of {green_comp.name} and {dry_comp.weight_kg} kg of {dry_comp.name}.",
        f"Use {', '.join(component.name for component in concentrate_components)} to meet protein and energy shortfall.",
        "Re-check ingredient prices and green fodder quality weekly; adjust concentrate mix if nutrient density changes.",
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
