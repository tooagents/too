import base64
import json
import logging
import re
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO

from anthropic import Anthropic
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncConnection

from app.config import get_settings_singleton
from app.db.conn.pgconn import get_admin_conn
from app.db.models.acc.ac_bankstatement import BankStatementTransaction

router = APIRouter(prefix="/bankstatement", tags=["bankstatement"])
logger = logging.getLogger("app.http")

BS_TABLE = BankStatementTransaction.__table__
settings = get_settings_singleton()


class BankStatementUploadResponse(BaseModel):
    message: str
    transactions_imported: int
    bank_name: str | None = None
    account_name: str | None = None
    account_number: str | None = None
    statement_date: str | None = None


def _parse_td_date(date_str: str) -> date | None:
    """Parse TD Bank date formats like 'Aug 23, 2024' or 'Sep 03, 2024'"""
    if not date_str or not date_str.strip():
        return None
    try:
        # Try parsing "Aug 23, 2024" format
        return datetime.strptime(date_str.strip(), "%b %d, %Y").date()
    except ValueError:
        try:
            # Try parsing "August 2024" format
            return datetime.strptime(date_str.strip(), "%B %Y").date()
        except ValueError:
            logger.warning(f"Could not parse date: {date_str}")
            return None


def _clean_amount(amount_str: str | None) -> Decimal | None:
    """Clean and convert amount string to Decimal"""
    if not amount_str or not str(amount_str).strip():
        return None
    try:
        # Remove dollar signs, commas, and spaces
        cleaned = re.sub(r"[$,\s]", "", str(amount_str))
        if not cleaned or cleaned == "-":
            return None
        return Decimal(cleaned)
    except Exception as e:
        logger.warning(f"Could not parse amount: {amount_str} - {e}")
        return None


def _extract_account_number(text: str) -> str | None:
    """Extract account number from text like 'TD BASIC BUSINESS PLAN - 1039 5033741'"""
    # Look for pattern like "- 1039 5033741" or similar
    match = re.search(r"-\s*(\d[\d\s]+)$", text)
    if match:
        return match.group(1).strip()
    return None


async def _parse_td_statement_pdf(pdf_content: bytes, filename: str) -> dict:
    """Parse TD Bank statement PDF and extract transactions"""
    try:
        import pdfplumber
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="pdfplumber is not installed. Please install it: pip install pdfplumber",
        )

    transactions = []
    bank_name = "TD Bank"
    account_name = None
    account_number = None
    statement_date = None
    statement_period = None

    try:
        with pdfplumber.open(BytesIO(pdf_content)) as pdf:
            # Parse first page for metadata
            if len(pdf.pages) > 0:
                first_page = pdf.pages[0]
                first_text = first_page.extract_text()

                # Extract account info
                for line in first_text.split("\n"):
                    if "BASIC BUSINESS PLAN" in line or "TD" in line and "PLAN" in line:
                        account_name = line.strip()
                        account_number = _extract_account_number(line)
                    if "As at:" in line or "As of:" in line:
                        date_part = line.split(":")[-1].strip()
                        statement_date = _parse_td_date(date_part)

            # Parse all pages for transactions
            for page_num, page in enumerate(pdf.pages):
                # Extract tables
                tables = page.extract_tables()

                for table in tables:
                    if not table or len(table) < 2:
                        continue

                    # Try to identify header row
                    header_idx = None
                    for idx, row in enumerate(table):
                        if row and any(cell and ("Date" in str(cell) or "Description" in str(cell)) for cell in row):
                            header_idx = idx
                            break

                    if header_idx is None:
                        continue

                    # Process data rows
                    for row_idx in range(header_idx + 1, len(table)):
                        row = table[row_idx]
                        if not row or len(row) < 3:
                            continue

                        # Skip empty rows
                        if all(not cell or not str(cell).strip() for cell in row):
                            continue

                        # TD statement format: [Date, Description, Debit, Credit, Balance]
                        try:
                            trans_date = _parse_td_date(row[0]) if len(row) > 0 else None
                            description = str(row[1]).strip() if len(row) > 1 and row[1] else None
                            debit = _clean_amount(row[2]) if len(row) > 2 else None
                            credit = _clean_amount(row[3]) if len(row) > 3 else None
                            balance = _clean_amount(row[4]) if len(row) > 4 else None

                            # Skip if no meaningful data
                            if not trans_date and not description:
                                continue

                            # Determine statement period from first transaction
                            if trans_date and not statement_period:
                                statement_period = trans_date.strftime("%B %Y")

                            transactions.append({
                                "bank_name": bank_name,
                                "account_name": account_name,
                                "account_number": account_number,
                                "statement_date": statement_date,
                                "statement_period": statement_period,
                                "transaction_date": trans_date,
                                "description": description,
                                "debit_amount": debit,
                                "credit_amount": credit,
                                "balance": balance,
                                "source_file_name": filename,
                                "row_number": len(transactions) + 1,
                            })
                        except Exception as e:
                            logger.warning(f"Error parsing row {row_idx} on page {page_num}: {e}")
                            continue

    except Exception as e:
        logger.exception(f"Error parsing PDF: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error parsing PDF: {str(e)}",
        )

    return {
        "transactions": transactions,
        "bank_name": bank_name,
        "account_name": account_name,
        "account_number": account_number,
        "statement_date": statement_date,
    }


@router.post("/upload", response_model=BankStatementUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_bank_statement(
    file: UploadFile = File(..., description="Bank statement PDF file"),
    conn: AsyncConnection = Depends(get_admin_conn),
) -> BankStatementUploadResponse:
    """
    Upload and parse bank statement PDF (no authentication required).

    This endpoint extracts transactions from TD Bank statements and stores them as raw data.
    No processing or reconciliation is performed - just converts PDF to table format.
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported",
        )

    # Read file content
    try:
        pdf_content = await file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error reading file: {str(e)}",
        )

    # Parse PDF
    parsed_data = await _parse_td_statement_pdf(pdf_content, file.filename)

    if not parsed_data["transactions"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No transactions found in PDF. Please check the file format.",
        )

    # Insert transactions into database
    try:
        await conn.execute(insert(BS_TABLE).values(parsed_data["transactions"]))
    except Exception as e:
        logger.exception(f"Error inserting transactions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving transactions: {str(e)}",
        )

    return BankStatementUploadResponse(
        message=f"Successfully imported {len(parsed_data['transactions'])} transactions from {file.filename}",
        transactions_imported=len(parsed_data["transactions"]),
        bank_name=parsed_data["bank_name"],
        account_name=parsed_data["account_name"],
        account_number=parsed_data["account_number"],
        statement_date=parsed_data["statement_date"].isoformat() if parsed_data["statement_date"] else None,
    )


@router.get("/transactions", response_model=list[dict])
async def list_bank_transactions(
    limit: int = 100,
    account_number: str | None = None,
    conn: AsyncConnection = Depends(get_admin_conn),
) -> list[dict]:
    """
    List imported bank statement transactions (no authentication required).

    Optional filters:
    - limit: Maximum number of transactions to return (default 100)
    - account_number: Filter by bank account number
    """
    stmt = select(BS_TABLE).order_by(BS_TABLE.c.transaction_date.desc(), BS_TABLE.c.created_at.desc())

    if account_number:
        stmt = stmt.where(BS_TABLE.c.account_number == account_number)

    stmt = stmt.limit(max(1, min(1000, limit)))

    result = await conn.execute(stmt)
    rows = result.mappings().all()

    # Convert to dict for response
    transactions = []
    for row in rows:
        trans = dict(row)
        # Convert date objects to strings
        if trans.get("transaction_date"):
            trans["transaction_date"] = trans["transaction_date"].isoformat()
        if trans.get("statement_date"):
            trans["statement_date"] = trans["statement_date"].isoformat()
        if trans.get("created_at"):
            trans["created_at"] = trans["created_at"].isoformat()
        transactions.append(trans)

    return transactions
