from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ebay_item_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    transaction_type: Mapped[str] = mapped_column(String, nullable=False)  # 'purchase' | 'sale'
    card_name: Mapped[str] = mapped_column(String, nullable=False)
    player_name: Mapped[str | None] = mapped_column(String, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    variation: Mapped[str | None] = mapped_column(String, nullable=True)
    grade: Mapped[str | None] = mapped_column(String, nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    ebay_fees: Mapped[float] = mapped_column(Float, default=0.0)
    shipping_cost: Mapped[float] = mapped_column(Float, default=0.0)
    net_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(String, default="ebay")  # 'ebay' | 'manual'
    reconciled: Mapped[bool] = mapped_column(Boolean, default=False)
    statement_line_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("statement_lines.id"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
