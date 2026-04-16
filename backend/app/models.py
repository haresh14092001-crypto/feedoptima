from typing import Literal
from pydantic import BaseModel


class FeedIngredient(BaseModel):
    name: str
    category: Literal["green_fodder", "dry_fodder", "concentrate", "byproduct", "mineral_mix", "vitamin_premix"]
    dry_matter_pct: float
    crude_protein_pct: float
    energy_mj_per_kg: float
    calcium_pct: float = 0.0
    phosphorus_pct: float = 0.0
    fiber_pct: float = 0.0
    cost_per_kg: float
    availability_score: float = 1.0  # 0-1 scale for regional availability
    quality_variability: float = 0.1  # Standard deviation in quality


class NutrientTarget(BaseModel):
    dry_matter_kg: float
    crude_protein_pct: float
    energy_mj: float
    calcium_pct: float = 0.0
    phosphorus_pct: float = 0.0
    fiber_pct: float = 0.0
    notes: str


class OptimizationConstraints(BaseModel):
    max_cost_per_day: float = 0.0  # 0 means no limit
    preferred_feeds: list[str] = []  # Feed names to prioritize
    avoid_feeds: list[str] = []  # Feed names to avoid
    region: str = "general"  # For location-based pricing/availability
