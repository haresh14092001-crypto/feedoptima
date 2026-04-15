from datetime import date
from typing import Iterable, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from .db_models import Ingredient, PriceRecord
from .data.feed_data import get_default_feed_ingredients
from .models import FeedIngredient


def get_ingredient_by_name(session: Session, name: str) -> Optional[Ingredient]:
    return session.scalar(select(Ingredient).where(Ingredient.name == name))


def list_ingredients(session: Session) -> List[Ingredient]:
    return session.scalars(select(Ingredient).order_by(Ingredient.name)).all()


def create_ingredient(session: Session, feed: FeedIngredient) -> Ingredient:
    ingredient = Ingredient(
        name=feed.name,
        category=feed.category,
        dry_matter_pct=feed.dry_matter_pct,
        crude_protein_pct=feed.crude_protein_pct,
        energy_mj_per_kg=feed.energy_mj_per_kg,
        default_price_per_kg=feed.cost_per_kg,
    )
    session.add(ingredient)
    session.commit()
    session.refresh(ingredient)
    return ingredient


def upsert_ingredient(session: Session, feed: FeedIngredient) -> Ingredient:
    existing = get_ingredient_by_name(session, feed.name)
    if existing:
        existing.category = feed.category
        existing.dry_matter_pct = feed.dry_matter_pct
        existing.crude_protein_pct = feed.crude_protein_pct
        existing.energy_mj_per_kg = feed.energy_mj_per_kg
        existing.default_price_per_kg = feed.cost_per_kg
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing
    return create_ingredient(session, feed)


def add_price_record(
    session: Session,
    ingredient: Ingredient,
    price_per_kg: float,
    source: str = "manual",
    effective_date: Optional[date] = None,
) -> PriceRecord:
    record = PriceRecord(
        ingredient_id=ingredient.id,
        price_per_kg=price_per_kg,
        source=source,
        effective_date=effective_date or date.today(),
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def get_latest_price(session: Session, ingredient: Ingredient) -> Optional[PriceRecord]:
    return session.scalar(
        select(PriceRecord)
        .where(PriceRecord.ingredient_id == ingredient.id)
        .order_by(PriceRecord.effective_date.desc(), PriceRecord.created_at.desc())
        .limit(1)
    )


def seed_default_catalog(session: Session) -> List[Ingredient]:
    ingredients = []
    for feed in get_default_feed_ingredients():
        ingredients.append(upsert_ingredient(session, feed))
    return ingredients


def update_price_records(session: Session, prices: Iterable[tuple[str, float, str, Optional[date]]]) -> List[PriceRecord]:
    records = []
    for name, price, source, effective_date in prices:
        ingredient = get_ingredient_by_name(session, name)
        if not ingredient:
            continue
        records.append(add_price_record(session, ingredient, price, source, effective_date))
    return records
