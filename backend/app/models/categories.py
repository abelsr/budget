from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.identity import new_id


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    icon: Mapped[str] = mapped_column(String(60))
    color: Mapped[str] = mapped_column(String(7))
    type: Mapped[str] = mapped_column(String(10))
    active: Mapped[bool] = mapped_column(default=True)
    deleted: Mapped[bool] = mapped_column(default=False)

    household: Mapped["Household"] = relationship(back_populates="categories")


class MerchantRule(Base):
    __tablename__ = "merchant_rules"
    __table_args__ = (UniqueConstraint("household_id", "match_text", name="uq_merchant_rules_household_match_text"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    household_id: Mapped[str] = mapped_column(ForeignKey("households.id"), index=True)
    pattern: Mapped[str] = mapped_column(String(120))
    match_text: Mapped[str] = mapped_column(String(120))
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    category: Mapped[Category] = relationship(lazy="joined")
