from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Prospect(Base):
    __tablename__ = "prospects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mlb_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[str | None] = mapped_column(String, nullable=True)
    team: Mapped[str | None] = mapped_column(String, nullable=True)
    rank_current: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rank_previous: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rank_change: Mapped[int] = mapped_column(Integer, default=0)  # positive = moved up
    eta: Mapped[str | None] = mapped_column(String, nullable=True)
    scouting_grade: Mapped[str | None] = mapped_column(String, nullable=True)
    stats_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_rising: Mapped[bool] = mapped_column(Boolean, default=False)
    last_updated: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source: Mapped[str] = mapped_column(String, default="fangraphs")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
