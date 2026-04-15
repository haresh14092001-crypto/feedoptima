from datetime import date
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .crud import (
    add_price_record,
    get_ingredient_by_name,
    list_ingredients,
    seed_default_catalog,
)
from .db import SessionLocal, init_db
from .schemas import (
    IngredientCreate,
    IngredientResponse,
    PriceCreate,
    PriceResponse,
    PriceUpdateRequest,
    RationRequest,
    RationResponse,
)
from .calculator import optimize_ration
from .scrapers import fetch_sample_market_prices, fetch_tnau_feed_ingredients

app = FastAPI(
    title="FeedOptima API",
    description="Rule-based livestock ration optimization with AI-driven explanation and database-backed feed catalog.",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def _ingredient_response(record, latest_price) -> IngredientResponse:
    return IngredientResponse(
        name=record.name,
        category=record.category,
        dry_matter_pct=record.dry_matter_pct,
        crude_protein_pct=record.crude_protein_pct,
        energy_mj_per_kg=record.energy_mj_per_kg,
        latest_price_per_kg=latest_price.price_per_kg if latest_price else getattr(record, "default_price_per_kg", None),
    )


def _price_response(record) -> PriceResponse:
    return PriceResponse(
        ingredient_name=record.ingredient.name,
        price_per_kg=record.price_per_kg,
        source=record.source,
        effective_date=record.effective_date,
    )


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok", "service": "FeedOptima"}


@app.post("/ration/optimize", response_model=RationResponse)
def optimize_ration_endpoint(request: RationRequest) -> RationResponse:
    return optimize_ration(request)


@app.get("/catalog", response_model=List[IngredientResponse])
def read_catalog() -> List[IngredientResponse]:
    with SessionLocal() as session:
        ingredients = list_ingredients(session)
        return [
            _ingredient_response(ingredient, ingredient.price_records[0] if ingredient.price_records else None)
            for ingredient in ingredients
        ]


@app.post("/catalog/seed", response_model=List[IngredientResponse])
def seed_catalog() -> List[IngredientResponse]:
    with SessionLocal() as session:
        ingredients = seed_default_catalog(session)
        return [
            _ingredient_response(ingredient, ingredient.price_records[0] if ingredient.price_records else None)
            for ingredient in ingredients
        ]


@app.post("/catalog/ingredient", response_model=IngredientResponse)
def create_catalog_ingredient(ingredient: IngredientCreate) -> IngredientResponse:
    from .db_models import Ingredient as IngredientModel

    with SessionLocal() as session:
        existing = get_ingredient_by_name(session, ingredient.name)
        if existing:
            existing.category = ingredient.category
            existing.dry_matter_pct = ingredient.dry_matter_pct
            existing.crude_protein_pct = ingredient.crude_protein_pct
            existing.energy_mj_per_kg = ingredient.energy_mj_per_kg
            existing.default_price_per_kg = ingredient.cost_per_kg
            session.add(existing)
            session.commit()
            session.refresh(existing)
            latest = existing.price_records[0] if existing.price_records else None
            return _ingredient_response(existing, latest)

        new_ingredient = IngredientModel(
            name=ingredient.name,
            category=ingredient.category,
            dry_matter_pct=ingredient.dry_matter_pct,
            crude_protein_pct=ingredient.crude_protein_pct,
            energy_mj_per_kg=ingredient.energy_mj_per_kg,
            default_price_per_kg=ingredient.cost_per_kg,
        )
        session.add(new_ingredient)
        session.commit()
        session.refresh(new_ingredient)
        return _ingredient_response(new_ingredient, None)


@app.post("/catalog/prices", response_model=List[PriceResponse])
def update_prices(request: PriceUpdateRequest) -> List[PriceResponse]:
    updated_records = []
    with SessionLocal() as session:
        for price_update in request.prices:
            ingredient = get_ingredient_by_name(session, price_update.ingredient_name)
            if not ingredient:
                raise HTTPException(status_code=404, detail=f"Ingredient not found: {price_update.ingredient_name}")
            record = add_price_record(
                session=session,
                ingredient=ingredient,
                price_per_kg=price_update.price_per_kg,
                source=price_update.source,
                effective_date=price_update.effective_date,
            )
            updated_records.append(record)
    return [_price_response(record) for record in updated_records]


@app.post("/catalog/sync-market-prices", response_model=List[PriceResponse])
def sync_market_prices() -> List[PriceResponse]:
    prices = fetch_sample_market_prices()
    updated_records = []
    with SessionLocal() as session:
        for ingredient_name, price in prices.items():
            ingredient = get_ingredient_by_name(session, ingredient_name)
            if not ingredient:
                continue
            updated_records.append(
                add_price_record(
                    session=session,
                    ingredient=ingredient,
                    price_per_kg=price,
                    source="market_sample",
                    effective_date=date.today(),
                )
            )
    return [_price_response(record) for record in updated_records]


@app.get("/scrape/tnau")
def scrape_tnau() -> dict:
    ingredients = fetch_tnau_feed_ingredients()
    return {
        "source": "TNAU Feed Ingredients",
        "count": len(ingredients),
        "ingredients": ingredients,
        "note": "This endpoint scrapes publicly available feed ingredient names to support local feed catalog creation.",
    }


@app.get("/scrape/market-prices")
def scrape_market_prices() -> dict:
    prices = fetch_sample_market_prices()
    return {
        "source": "Sample Market Price Data",
        "count": len(prices),
        "prices": prices,
        "note": "This endpoint provides sample market price data suitable for catalog price updates.",
    }
