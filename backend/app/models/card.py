from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    card_name: Mapped[str] = mapped_column(String, nullable=False)
    player_name: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    variation: Mapped[str | None] = mapped_column(String, nullable=True)
    grade: Mapped[str | None] = mapped_column(String, nullable=True)
    is_owned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_watchlist: Mapped[bool] = mapped_column(Boolean, default=False)
    purchase_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
