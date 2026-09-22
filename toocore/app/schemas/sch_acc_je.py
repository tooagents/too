from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

COARoot = Literal["Asset", "Liability", "Equity", "Revenue", "Expense"]
NormalBalanceType = Literal["Debit", "Credit"]


class TransactionOut(BaseModel):
    id: UUID
    txn_date: date
    description: str
    amount: Decimal
    currency: str
    status: str
    source_file_name: str | None
    created_at: datetime
    journal_id: UUID | None = None
    is_deleted: bool | None = None

    model_config = {"from_attributes": True}


class JournalGenerateIn(BaseModel):
    transaction_id: UUID
    force: bool = False


class JournalLineUpdateIn(BaseModel):
    id: UUID | None = None
    account_id: UUID
    line_type: NormalBalanceType
    amount: Decimal
    description: str | None = None


class JournalEntryUpdateIn(BaseModel):
    entry_date: date | None = None
    memo: str | None = None
    lines: list[JournalLineUpdateIn]


class TransactionUpdateIn(BaseModel):
    txn_date: date | None = None
    description: str | None = None
    amount: Decimal | None = None
    status: str | None = None


class JournalLineOut(BaseModel):
    id: UUID
    journal_entry_id: UUID
    account_id: UUID
    coa_code: str | None = None
    coa_name: str | None = None
    parent_id: UUID | None = None
    coa_status: str | None = None
    coa_level: int | None = None
    line_type: NormalBalanceType
    amount: Decimal
    description: str | None

    model_config = {"from_attributes": True}


class JournalEntryOut(BaseModel):
    id: UUID
    entry_no: int
    entry_date: date
    memo: str | None
    source: str
    entry_status: str
    period_yyyymm: int
    posted_at: datetime
    is_reversal: bool
    lines: list[JournalLineOut] = []


class TrialBalanceRow(BaseModel):
    account_id: UUID
    coa_code: str
    coa_name: str
    parent_id: str
    coa_status: str | None
    coa_level: int | None
    normal_balance: NormalBalanceType | None
    debit: Decimal
    credit: Decimal
    balance: Decimal


class ReportSectionRow(BaseModel):
    account_id: UUID
    coa_code: str
    coa_name: str
    parent_id: str
    coa_status: str | None
    coa_level: int | None
    amount: Decimal


class ReportLevel3(BaseModel):
    coa_level: int | None
    amount: Decimal
    posting_accounts: list[ReportSectionRow]


class ReportLevel2(BaseModel):
    coa_status: str | None
    amount: Decimal
    level3: list[ReportLevel3]


class ReportSection(BaseModel):
    parent_id: str
    amount: Decimal
    level2: list[ReportLevel2]


class BalanceSheetOut(BaseModel):
    as_of: date
    sections: dict[str, ReportSection]
    totals: dict[str, Decimal]


class IncomeStatementOut(BaseModel):
    from_date: date
    to_date: date
    sections: dict[str, ReportSection]
    totals: dict[str, Decimal]
