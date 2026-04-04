from datetime import date, datetime
from sqlalchemy import Date, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GradingSubmission(Base):
    __tablename__ = "grading_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Card identification — maps directly to 130point search queries
    player_name: Mapped[str] = mapped_column(String, nullable=False)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    card_set: Mapped[str] = mapped_column(String, nullable=False)   # e.g. "Bowman Chrome"
    variation: Mapped[str | None] = mapped_column(String, nullable=True)  # e.g. "Refractor"
    card_number: Mapped[str | None] = mapped_column(String, nullable=True)  # e.g. "BCP-1"

    # PSA submission tracking
    psa_order_number: Mapped[str | None] = mapped_column(String, nullable=True)
    submitted_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    estimated_return: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String, default="submitted")
    # Status values: submitted | received | grading | graded | shipped | returned

    # Results (filled in when card comes back)
    grade_received: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cert_number: Mapped[str | None] = mapped_column(String, nullable=True)

    # Financials
    purchase_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    grading_fee: Mapped[float | None] = mapped_column(Float, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
