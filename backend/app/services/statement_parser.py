"""
Bank statement parser supporting CSV and PDF formats.
Classifies eBay-related transactions automatically.
"""
import io
import re
from datetime import date
from typing import Optional

import pandas as pd

BANK_PROFILES = {
    "chase": {
        "date": "Transaction Date",
        "desc": "Description",
        "amount": "Amount",
    },
    "paypal": {
        "date": "Date",
        "desc": "Name",
        "amount": "Net",
    },
    "bofa": {
        "date": "Date",
        "desc": "Description",
        "amount": "Amount",
    },
    "wellsfargo": {
        "date": "Date",
        "desc": "Description",
        "amount": "Amount",
    },
}

EBAY_PATTERNS = re.compile(
    r"ebay|paypal\s*\*ebay|ebay\s*inc|paypal\s*\*\s*ebay",
    re.IGNORECASE,
)
SHIPPING_PATTERNS = re.compile(r"usps|fedex|ups\b|stamps\.com|pirateship", re.IGNORECASE)
PSA_PATTERNS = re.compile(r"\bpsa\b|collectors\s*universe", re.IGNORECASE)

DATE_RE = re.compile(
    r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|[A-Z][a-z]{2}\s+\d{1,2},?\s+\d{4})\b"
)
AMOUNT_RE = re.compile(r"-?\$?[\d,]+\.\d{2}(?:\s+CR)?")


def _classify(description: str, amount: float) -> str:
    desc = description or ""
    if PSA_PATTERNS.search(desc):
        return "psa_grading"
    if SHIPPING_PATTERNS.search(desc):
        return "shipping"
    if EBAY_PATTERNS.search(desc):
        return "ebay_sale" if amount > 0 else "ebay_purchase"
    return "unknown"


def _parse_date(val: str) -> Optional[date]:
    if not val:
        return None
    for fmt in ("%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d", "%m/%d/%y", "%b %d, %Y", "%b %d %Y"):
        try:
            from datetime import datetime
            return datetime.strptime(str(val).strip(), fmt).date()
        except ValueError:
            continue
    return None


def _normalize_amount(val) -> Optional[float]:
    if val is None:
        return None
    s = str(val).replace(",", "").replace("$", "").strip()
    is_credit = s.upper().endswith(" CR")
    s = s.replace(" CR", "").replace("CR", "").strip()
    try:
        f = float(s)
        return abs(f) if is_credit else f
    except ValueError:
        return None


def parse_csv(content: bytes, bank_name: str = "generic") -> list[dict]:
    """Parse a CSV bank statement into a list of line dicts."""
    profile = BANK_PROFILES.get(bank_name.lower())
    df = pd.read_csv(io.BytesIO(content), encoding="utf-8", on_bad_lines="skip")
    df.columns = df.columns.str.strip()

    if profile:
        col_date = _find_col(df, profile["date"])
        col_desc = _find_col(df, profile["desc"])
        col_amount = _find_col(df, profile["amount"])
    else:
        # Generic: try common column name guesses
        col_date = _find_col(df, "date") or _find_col(df, "transaction date") or df.columns[0]
        col_desc = _find_col(df, "description") or _find_col(df, "memo") or df.columns[1]
        col_amount = _find_col(df, "amount") or _find_col(df, "debit") or df.columns[2]

    lines = []
    for _, row in df.iterrows():
        raw_date = str(row.get(col_date, ""))
        raw_desc = str(row.get(col_desc, ""))
        raw_amount = row.get(col_amount)

        parsed_date = _parse_date(raw_date)
        amount = _normalize_amount(raw_amount)
        if amount is None:
            continue

        lines.append({
            "line_date": parsed_date,
            "description": raw_desc.strip(),
            "amount": amount,
            "category": _classify(raw_desc, amount),
        })
    return lines


def _find_col(df: pd.DataFrame, name: str) -> Optional[str]:
    for col in df.columns:
        if col.strip().lower() == name.strip().lower():
            return col
    return None


def parse_pdf(content: bytes, bank_name: str = "generic") -> list[dict]:
    """Parse a PDF bank statement using pdfplumber."""
    try:
        import pdfplumber
    except ImportError:
        return []

    lines = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            # Try table extraction first
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    for row in table:
                        if not row or len(row) < 3:
                            continue
                        # Heuristic: first date-like col, last amount-like col, middle is desc
                        date_val = None
                        amount_val = None
                        desc_val = None

                        for cell in row:
                            cell_str = str(cell or "").strip()
                            if DATE_RE.search(cell_str) and date_val is None:
                                date_val = cell_str
                            elif AMOUNT_RE.search(cell_str):
                                amount_val = cell_str
                            elif len(cell_str) > 5 and desc_val is None:
                                desc_val = cell_str

                        if amount_val:
                            parsed_date = _parse_date(date_val or "")
                            amount = _normalize_amount(amount_val)
                            if amount is not None:
                                lines.append({
                                    "line_date": parsed_date,
                                    "description": (desc_val or "").strip(),
                                    "amount": amount,
                                    "category": _classify(desc_val or "", amount),
                                })
            else:
                # Fallback: raw text line parsing
                text = page.extract_text() or ""
                for line in text.split("\n"):
                    date_match = DATE_RE.search(line)
                    amount_match = AMOUNT_RE.search(line)
                    if date_match and amount_match:
                        parsed_date = _parse_date(date_match.group(0))
                        amount = _normalize_amount(amount_match.group(0))
                        if amount is not None:
                            desc = line[: amount_match.start()].replace(date_match.group(0), "").strip()
                            lines.append({
                                "line_date": parsed_date,
                                "description": desc,
                                "amount": amount,
                                "category": _classify(desc, amount),
                            })
    return lines


def parse_excel(content: bytes, bank_name: str = "generic") -> list[dict]:
    """Parse an Excel bank statement (.xlsx / .xls) into a list of line dicts."""
    profile = BANK_PROFILES.get(bank_name.lower())
    df = pd.read_excel(io.BytesIO(content))
    df.columns = df.columns.str.strip().str.replace(r'\s+', ' ', regex=True)

    if profile:
        col_date = _find_col(df, profile["date"])
        col_desc = _find_col(df, profile["desc"])
        col_amount = _find_col(df, profile["amount"])
    else:
        col_date = _find_col(df, "date") or _find_col(df, "transaction date") or df.columns[0]
        col_desc = _find_col(df, "description") or _find_col(df, "memo") or df.columns[1]
        col_amount = _find_col(df, "amount") or _find_col(df, "debit") or df.columns[2]

    lines = []
    for _, row in df.iterrows():
        raw_date = str(row.get(col_date, ""))
        raw_desc = str(row.get(col_desc, ""))
        raw_amount = row.get(col_amount)

        parsed_date = _parse_date(raw_date)
        amount = _normalize_amount(raw_amount)
        if amount is None:
            continue

        lines.append({
            "line_date": parsed_date,
            "description": raw_desc.strip(),
            "amount": amount,
            "category": _classify(raw_desc, amount),
        })
    return lines


def parse_statement(content: bytes, filename: str, bank_name: str = "generic") -> list[dict]:
    """Entry point: dispatch to CSV, Excel, or PDF parser based on filename."""
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return parse_pdf(content, bank_name)
    if lower.endswith(".xlsx") or lower.endswith(".xls"):
        return parse_excel(content, bank_name)
    return parse_csv(content, bank_name)
