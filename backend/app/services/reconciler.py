"""
Reconciliation service: matches statement lines to eBay transactions.
Uses fuzzy date (±3 days) and amount (±$1.00) matching.
"""
from datetime import timedelta
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.statement import StatementLine, StatementUpload
from app.models.transaction import Transaction


async def reconcile_upload(db: AsyncSession, upload_id: int) -> dict:
    """Run reconciliation for all unreconciled lines in an upload."""
    # Fetch unreconciled eBay-related lines
    lines_result = await db.execute(
        select(StatementLine).where(
            and_(
                StatementLine.upload_id == upload_id,
                StatementLine.reconciled == False,
                StatementLine.category.in_(["ebay_purchase", "ebay_sale"]),
            )
        )
    )
    lines = lines_result.scalars().all()

    matched = 0
    unmatched = 0

    for line in lines:
        tx = await _find_match(db, line)
        if tx:
            line.reconciled = True
            line.transaction_id = tx.id
            tx.reconciled = True
            tx.statement_line_id = line.id
            matched += 1
        else:
            unmatched += 1

    # Update upload stats
    upload_result = await db.execute(
        select(StatementUpload).where(StatementUpload.id == upload_id)
    )
    upload = upload_result.scalar_one_or_none()
    if upload:
        upload.lines_reconciled = matched

    await db.commit()
    return {"matched": matched, "unmatched": unmatched, "total": len(lines)}


async def _find_match(
    db: AsyncSession, line: StatementLine
) -> Optional[Transaction]:
    if not line.line_date or line.amount is None:
        return None

    # Determine transaction type from category and amount sign
    if line.category == "ebay_sale" or line.amount > 0:
        tx_type = "sale"
    else:
        tx_type = "purchase"

    date_low = line.line_date - timedelta(days=3)
    date_high = line.line_date + timedelta(days=3)
    abs_amount = abs(line.amount)
    amount_low = abs_amount - 1.00
    amount_high = abs_amount + 1.00

    result = await db.execute(
        select(Transaction).where(
            and_(
                Transaction.transaction_type == tx_type,
                Transaction.reconciled == False,
                Transaction.transaction_date >= date_low,
                Transaction.transaction_date <= date_high,
                Transaction.amount >= amount_low,
                Transaction.amount <= amount_high,
            )
        )
    )
    candidates = result.scalars().all()

    if not candidates:
        return None

    # Score by date proximity and amount proximity
    best = min(
        candidates,
        key=lambda t: (
            abs((t.transaction_date - line.line_date).days) * 10
            + abs(t.amount - abs_amount)
        ),
    )
    return best
