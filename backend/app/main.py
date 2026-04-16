from datetime import date
from typing import List

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
from functools import lru_cache
import hashlib
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
    description="AI-enabled livestock feed ration optimization with comprehensive nutritional analysis.",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error handling middleware
@app.middleware("http")
async def add_error_handling(request: Request, call_next):
    try:
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal server error: {str(e)}", "type": "server_error"}
        )

# Rate limiting (simple in-memory implementation)
request_counts = {}

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    current_time = int(time.time() / 60)  # Per minute

    key = f"{client_ip}:{current_time}"
    if key not in request_counts:
        request_counts[key] = 0
    request_counts[key] += 1

    # Clean old entries
    to_remove = [k for k in request_counts.keys() if int(k.split(':')[1]) < current_time - 5]
    for k in to_remove:
        del request_counts[k]

    if request_counts[key] > 30:  # 30 requests per minute
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Please try again later.", "type": "rate_limit"}
        )

    response = await call_next(request)
    return response


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


@lru_cache(maxsize=100)
def _cached_optimize_ration(request_hash: str, request_data: str) -> str:
    """Cache ration optimization results to improve performance"""
    import json
    from .calculator import optimize_ration
    from .schemas import RationRequest

    request_dict = json.loads(request_data)
    request = RationRequest(**request_dict)
    result = optimize_ration(request)
    return result.model_dump_json()


@app.post("/ration/optimize", response_model=RationResponse)
def optimize_ration_endpoint(request: RationRequest) -> RationResponse:
    """Optimize livestock feed ration with comprehensive nutritional analysis"""
    try:
        # Input validation
        if request.body_weight_kg <= 0:
            raise HTTPException(status_code=400, detail="Body weight must be positive")
        if request.milk_yield_lpd and request.milk_yield_lpd < 0:
            raise HTTPException(status_code=400, detail="Milk yield cannot be negative")
        if request.max_cost_per_day and request.max_cost_per_day < 0:
            raise HTTPException(status_code=400, detail="Maximum cost cannot be negative")

        # Create cache key
        request_str = request.model_dump_json()
        request_hash = hashlib.md5(request_str.encode()).hexdigest()

        # Try to get cached result
        try:
            cached_result = _cached_optimize_ration(request_hash, request_str)
            return RationResponse.model_validate_json(cached_result)
        except Exception:
            # Cache miss or error, compute fresh result
            from .calculator import optimize_ration
            result = optimize_ration(request)
            return result

    except HTTPException:
        raise
    except Exception as e:
        # Graceful degradation - return basic ration if AI fails
        if "AI" in str(e) or "OpenAI" in str(e) or "Ollama" in str(e):
            request.use_ai = False
            try:
                from .calculator import optimize_ration
                result = optimize_ration(request)
                result.ai_notes = "AI explanation unavailable due to service issues. Basic optimization provided."
                return result
            except Exception as inner_e:
                raise HTTPException(status_code=500, detail=f"Optimization failed: {str(inner_e)}")
        else:
            raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")


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
