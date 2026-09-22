from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.db_schemas import SCHEMA_TOO_ACC
from app.db.models.too.z_base import Base, BaseMixin


class BankStatementTransaction(Base, BaseMixin):
    """Raw bank statement transactions - imported as-is from PDF/CSV"""

    __tablename__ = "bank_statement_transactions"
    __table_args__ = {"schema": SCHEMA_TOO_ACC}

    # Statement metadata
    bank_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    account_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    account_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    statement_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    statement_period: Mapped[str | None] = mapped_column(String(50), nullable=True)  # e.g., "August 2024"

    # Transaction details
    transaction_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    debit_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    credit_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)

    # Source tracking
    source_file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    row_number: Mapped[int | None] = mapped_column(nullable=True)  # Original row number in statement
