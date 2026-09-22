from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

COARoot = Literal["Asset", "Liability", "Equity", "Revenue", "Expense"]
NormalBalanceType = Literal["Debit", "Credit"]

class COABase(BaseModel):
    coa_code: str = Field(min_length=1, max_length=20)
    coa_name: str = Field(min_length=1, max_length=255)
    parent_id: UUID | None = None
    coa_level: int | None = None
    normal_balance: NormalBalanceType
    is_posting: bool = True
    is_deleted: bool | None = None


class COACreate(COABase):
    pass

class COAUpdate(BaseModel):
    coa_code: str | None = None
    coa_name: str | None = None
    parent_id: UUID | None = None
    coa_level: int | None = None
    normal_balance: NormalBalanceType | None = None
    is_posting: bool | None = None
    is_deleted: bool | None = None


class COAOut(COABase):
    id: UUID
    model_config = {"from_attributes": True}

class COATreeOut(COAOut):
    children: list["COATreeOut"] = Field(default_factory=list)


