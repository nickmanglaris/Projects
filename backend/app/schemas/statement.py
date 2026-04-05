from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


class StatementLineOut(BaseModel):
    id: int
    upload_id: int
    line_date: Optional[date] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    category: str
    reconciled: bool
    transaction_id: Optional[int] = None

    model_config = {"from_attributes": True}


class StatementUploadOut(BaseModel):
    id: int
    filename: str
    file_type: str
    bank_name: str
    upload_date: datetime
    lines_parsed: int
    lines_reconciled: int

    model_config = {"from_attributes": True}


class UploadResponse(BaseModel):
    upload_id: int
    lines_found: int
    preview: list[StatementLineOut]
    message: str


class ReconcileResponse(BaseModel):
    upload_id: int
    matched: int
    created: int
    skipped: int
    total: int
