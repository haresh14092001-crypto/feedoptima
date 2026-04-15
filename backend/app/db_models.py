from datetime import date, datetime
from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from .db import Base


class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    category = Column(String(50), nullable=False)
    dry_matter_pct = Column(Float, nullable=False)
    crude_protein_pct = Column(Float, nullable=False)
    energy_mj_per_kg = Column(Float, nullable=False)
    default_price_per_kg = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    price_records = relationship(
        "PriceRecord",
        back_populates="ingredient",
        order_by="PriceRecord.effective_date.desc()",
        cascade="all, delete-orphan",
    )


class PriceRecord(Base):
    __tablename__ = "price_records"

    id = Column(Integer, primary_key=True, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=False)
    price_per_kg = Column(Float, nullable=False)
    source = Column(String(100), nullable=False, default="manual")
    effective_date = Column(Date, nullable=False, default=date.today)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    ingredient = relationship("Ingredient", back_populates="price_records")
