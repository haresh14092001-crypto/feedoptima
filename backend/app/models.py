from typing import Literal
from pydantic import BaseModel


class FeedIngredient(BaseModel):
    name: str
    category: Literal["green_fodder", "dry_fodder", "concentrate", "byproduct"]
    dry_matter_pct: float
    crude_protein_pct: float
    energy_mj_per_kg: float
    cost_per_kg: float


class NutrientTarget(BaseModel):
    dry_matter_kg: float
    crude_protein_pct: float
    energy_mj: float
    notes: str
