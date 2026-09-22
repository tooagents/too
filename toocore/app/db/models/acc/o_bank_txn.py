from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.db_schemas import SCHEMA_TOO_ACC
from app.db.models.too.z_base import Base, BaseMixin


class OBankTxn(Base, BaseMixin):
    """Business bank transaction (流水账) - the honest running log of money in/out.

    This is NOT accounting: no debit/credit-in-the-accounting-sense, no COA, no JE.
    It reflects exactly what the bank shows. Invoices link to a deposit via
    invoice_payment.bank_txn_id (one deposit -> many invoice payments).
    """

    __tablename__ = "o_bank_txn"
    __table_args__ = {"schema": SCHEMA_TOO_ACC}

    txn_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Which bank / account this row came from (e.g. "ICBC ****1234", "OCBC SGD").
    bank_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Bank narration goes in the inherited BaseMixin.description (length-less
    # String == TEXT on Postgres, so no override needed).
    debit: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)   # money out
    credit: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)  # money in
    balance: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    source: Mapped[str | None] = mapped_column(String(32), nullable=True)  # paste | manual | upload

    # type/status are inherited from BaseMixin (uncapped String).
    #   type: opening_balance | invoice | expense | transfer | other
    #   status: active | ...
    note: Mapped[str | None] = mapped_column(Text, nullable=True)  # user free-text note
    # Binary reconcile state (a deposit-level workflow flag). True only when the
    # deposit is FULLY applied to invoices; partial application stays False. The
    # actual invoice links/amounts live in invoice_payment; this is the yes/no flag.
    is_reconciled: Mapped[bool | None] = mapped_column(Boolean, default=False, nullable=True)
