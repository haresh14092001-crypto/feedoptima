from typing import List
from ..models import FeedIngredient


def get_default_feed_ingredients() -> List[FeedIngredient]:
    return [
        FeedIngredient(
            name="Napier Grass",
            category="green_fodder",
            dry_matter_pct=0.25,
            crude_protein_pct=0.12,
            energy_mj_per_kg=6.0,
            cost_per_kg=4.0,
        ),
        FeedIngredient(
            name="Maize Green",
            category="green_fodder",
            dry_matter_pct=0.22,
            crude_protein_pct=0.09,
            energy_mj_per_kg=6.5,
            cost_per_kg=3.5,
        ),
        FeedIngredient(
            name="Wheat Straw",
            category="dry_fodder",
            dry_matter_pct=0.90,
            crude_protein_pct=0.04,
            energy_mj_per_kg=4.3,
            cost_per_kg=8.0,
        ),
        FeedIngredient(
            name="Maize Stover",
            category="dry_fodder",
            dry_matter_pct=0.90,
            crude_protein_pct=0.05,
            energy_mj_per_kg=5.0,
            cost_per_kg=7.0,
        ),
        FeedIngredient(
            name="Maize Grain",
            category="concentrate",
            dry_matter_pct=0.88,
            crude_protein_pct=0.09,
            energy_mj_per_kg=12.0,
            cost_per_kg=18.0,
        ),
        FeedIngredient(
            name="Soybean Meal",
            category="concentrate",
            dry_matter_pct=0.90,
            crude_protein_pct=0.45,
            energy_mj_per_kg=11.5,
            cost_per_kg=36.0,
        ),
        FeedIngredient(
            name="Wheat Bran",
            category="concentrate",
            dry_matter_pct=0.88,
            crude_protein_pct=0.16,
            energy_mj_per_kg=9.5,
            cost_per_kg=12.0,
        ),
        FeedIngredient(
            name="Groundnut Oil Cake",
            category="concentrate",
            dry_matter_pct=0.90,
            crude_protein_pct=0.35,
            energy_mj_per_kg=9.7,
            cost_per_kg=30.0,
        ),
        FeedIngredient(
            name="Rice Bran",
            category="concentrate",
            dry_matter_pct=0.88,
            crude_protein_pct=0.12,
            energy_mj_per_kg=8.5,
            cost_per_kg=14.0,
        ),
        FeedIngredient(
            name="Sunflower Oil Cake",
            category="concentrate",
            dry_matter_pct=0.90,
            crude_protein_pct=0.30,
            energy_mj_per_kg=9.0,
            cost_per_kg=28.0,
        ),
    ]


def get_feeds_by_category(category: str) -> List[FeedIngredient]:
    return [f for f in get_default_feed_ingredients() if f.category == category]
