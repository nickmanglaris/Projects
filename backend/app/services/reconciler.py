"""
Reconciliation service: matches statement lines to eBay transactions.
For lines without a match, creates new Transaction records so they
appear in the dashboard.
Uses fuzzy date (±3 days) and amount (±$1.00) matching.
"""
from datetime import timedelta
from typing import Optional
from datetime import date as date_type

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.statement import StatementLine, StatementUpload
from app.models.transaction import Transaction

# Categories that should become Transaction records
CATEGORY_TX_TYPE = {
    "ebay_sale": "sale",
    "ebay_purchase": "purchase",
    "psa_grading": "purchase",
    "shipping": "purchase",
    "card_purchase": "purchase",
}
# Categories to silently skip (payments, credits, finance charges)
SKIP_CATEGORIES = {"skip", "unknown"}


async def reconcile_upload(db: AsyncSession, upload_id: int) -> dict:
    """Run reconciliation for all unreconciled lines in an upload."""
    lines_result = await db.execute(
        select(StatementLine).where(
            and_(
                StatementLine.upload_id == upload_id,
                StatementLine.reconciled == False,
            )
        )
    )
    lines = lines_result.scalars().all()

    matched = 0
    created = 0
    skipped = 0

    for line in lines:
        if line.category in SKIP_CATEGORIES:
            skipped += 1
            continue
        tx_type = CATEGORY_TX_TYPE.get(line.category)
        if not tx_type:
            skipped += 1
            continue

        # Try to match an existing eBay transaction
        tx = await _find_match(db, line, tx_type)
        if tx:
            line.reconciled = True
            line.transaction_id = tx.id
            tx.reconciled = True
            tx.statement_line_id = line.id
            matched += 1
        else:
            # Create a new transaction from the statement line
            tx = _create_from_line(line, tx_type)
            db.add(tx)
            await db.flush()
            line.reconciled = True
            line.transaction_id = tx.id
            tx.statement_line_id = line.id
            created += 1

    upload_result = await db.execute(
        select(StatementUpload).where(StatementUpload.id == upload_id)
    )
    upload = upload_result.scalar_one_or_none()
    if upload:
        upload.lines_reconciled = matched + created

    await db.commit()
    return {"matched": matched, "created": created, "skipped": skipped, "total": len(lines)}


def _create_from_line(line: StatementLine, tx_type: str) -> Transaction:
    """Create a new Transaction from an unmatched statement line."""
    amount = abs(line.amount) if line.amount else 0.0
    tx_date = line.line_date or date_type.today()
    desc = line.description or "Imported from statement"

    return Transaction(
        transaction_type=tx_type,
        card_name=desc[:200],
        amount=amount,
        ebay_fees=0.0,
        shipping_cost=0.0,
        net_amount=-amount if tx_type == "purchase" else amount,
        transaction_date=tx_date,
        source="statement",
        reconciled=True,
        notes=f"Imported from bank statement (category: {line.category})",
    )


async def _find_match(
    db: AsyncSession, line: StatementLine, tx_type: str
) -> Optional[Transaction]:
    if not line.line_date or line.amount is None:
        return None

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
