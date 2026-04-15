from datetime import date
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, PositiveFloat


class Species(str, Enum):
    cattle = "cattle"
    buffalo = "buffalo"
    goat = "goat"
    sheep = "sheep"
    poultry = "poultry"


class Purpose(str, Enum):
    dairy = "dairy"
    growth = "growth"
    maintenance = "maintenance"
    meat = "meat"
    layer = "layer"
    broiler = "broiler"


class RationRequest(BaseModel):
    species: Species
    body_weight_kg: PositiveFloat = Field(..., description="Live body weight in kg")
    milk_yield_lpd: Optional[float] = Field(
        0.0,
        description="Milk yield per day in liters; only used for dairy animals.",
    )
    purpose: Purpose
    use_ai: bool = Field(False, description="Enable AI explanation for the response.")


class RationComponent(BaseModel):
    name: str
    category: str
    weight_kg: float
    dry_matter_kg: float
    crude_protein_pct: float
    energy_mj: float
    cost_inr: float


class RationResponse(BaseModel):
    species: Species
    purpose: Purpose
    body_weight_kg: float
    milk_yield_lpd: float
    total_dry_matter_kg: float
    total_cost_inr: float
    components: List[RationComponent]
    summary: str
    instructions: List[str]
    ai_notes: Optional[str] = None


class IngredientCreate(BaseModel):
    name: str
    category: str
    dry_matter_pct: float
    crude_protein_pct: float
    energy_mj_per_kg: float
    cost_per_kg: float


class IngredientResponse(BaseModel):
    name: str
    category: str
    dry_matter_pct: float
    crude_protein_pct: float
    energy_mj_per_kg: float
    latest_price_per_kg: Optional[float] = None


class PriceCreate(BaseModel):
    ingredient_name: str
    price_per_kg: PositiveFloat
    source: str = "manual"
    effective_date: Optional[date] = None


class PriceResponse(BaseModel):
    ingredient_name: str
    price_per_kg: float
    source: str
    effective_date: date


class PriceUpdateRequest(BaseModel):
    prices: List[PriceCreate]
