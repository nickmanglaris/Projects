from datetime import date, datetime
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class StatementUpload(Base):
    __tablename__ = "statement_uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    file_type: Mapped[str] = mapped_column(String, nullable=False)  # 'csv' | 'pdf'
    bank_name: Mapped[str] = mapped_column(String, default="generic")
    upload_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    lines_parsed: Mapped[int] = mapped_column(Integer, default=0)
    lines_reconciled: Mapped[int] = mapped_column(Integer, default=0)


class StatementLine(Base):
    __tablename__ = "statement_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    upload_id: Mapped[int] = mapped_column(Integer, ForeignKey("statement_uploads.id"), nullable=False, index=True)
    line_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    category: Mapped[str] = mapped_column(String, default="unknown")  # 'ebay_purchase'|'ebay_sale'|'shipping'|'unknown'
    reconciled: Mapped[bool] = mapped_column(Boolean, default=False)
    transaction_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("transactions.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
