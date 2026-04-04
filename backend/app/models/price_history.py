from datetime import date, datetime
from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PriceHistory(Base):
    __tablename__ = "price_history"
    __table_args__ = (UniqueConstraint("card_id", "snapshot_date", name="uq_card_snapshot"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    card_id: Mapped[int] = mapped_column(Integer, ForeignKey("cards.id"), nullable=False, index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    avg_sale_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String, default="ebay_completed")
    # PSA graded card prices from 130point.com (added via migration)
    psa10_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    psa9_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    psa8_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
