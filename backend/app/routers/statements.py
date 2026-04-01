import os
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.statement import StatementLine, StatementUpload
from app.schemas.statement import ReconcileResponse, StatementLineOut, StatementUploadOut, UploadResponse
from app.services.reconciler import reconcile_upload
from app.services.statement_parser import parse_statement

UPLOAD_DIR = Path("data/uploads")
router = APIRouter(prefix="/statements", tags=["statements"])


@router.post("/upload", response_model=UploadResponse)
async def upload_statement(
    file: UploadFile = File(...),
    bank_name: str = Form("generic"),
    db: AsyncSession = Depends(get_db),
):
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    filename = file.filename or "statement"

    # Parse lines
    lines_data = parse_statement(content, filename, bank_name)
    if not lines_data:
        raise HTTPException(status_code=422, detail="Could not parse any lines from the uploaded file.")

    # Save file to disk
    save_path = UPLOAD_DIR / filename
    with open(save_path, "wb") as f:
        f.write(content)

    # Create upload record
    upload = StatementUpload(
        filename=filename,
        file_type="pdf" if filename.lower().endswith(".pdf") else "csv",
        bank_name=bank_name,
        lines_parsed=len(lines_data),
    )
    db.add(upload)
    await db.flush()

    # Save lines
    line_objects = []
    for ld in lines_data:
        line = StatementLine(
            upload_id=upload.id,
            line_date=ld.get("line_date"),
            description=ld.get("description"),
            amount=ld.get("amount"),
            category=ld.get("category", "unknown"),
        )
        db.add(line)
        line_objects.append(line)

    await db.commit()
    await db.refresh(upload)
    for line in line_objects:
        await db.refresh(line)

    preview = [StatementLineOut.model_validate(ln) for ln in line_objects[:20]]
    return UploadResponse(
        upload_id=upload.id,
        lines_found=len(lines_data),
        preview=preview,
        message=f"Parsed {len(lines_data)} lines successfully.",
    )


@router.post("/{upload_id}/reconcile", response_model=ReconcileResponse)
async def reconcile(upload_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(StatementUpload).where(StatementUpload.id == upload_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Upload not found")

    stats = await reconcile_upload(db, upload_id)
    return ReconcileResponse(upload_id=upload_id, **stats)


@router.get("/unreconciled", response_model=list[StatementLineOut])
async def get_unreconciled(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(StatementLine)
        .where(StatementLine.reconciled == False)
        .order_by(StatementLine.line_date.desc())
        .limit(100)
    )
    return [StatementLineOut.model_validate(ln) for ln in result.scalars().all()]


@router.get("/uploads", response_model=list[StatementUploadOut])
async def list_uploads(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(StatementUpload).order_by(StatementUpload.upload_date.desc())
    )
    return [StatementUploadOut.model_validate(u) for u in result.scalars().all()]
