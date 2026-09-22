from pydantic import BaseModel


class SeedTableSummary(BaseModel):
    created: int = 0
    updated: int = 0
    deleted: int = 0


class SeedTablesSummary(BaseModel):
    biz: SeedTableSummary
    clients: SeedTableSummary
    items: SeedTableSummary
    payment_methods: SeedTableSummary
    fees: SeedTableSummary
    taxes: SeedTableSummary
    coa: SeedTableSummary
    invoices: SeedTableSummary | None = None
    invoice_items: SeedTableSummary | None = None
    invoice_payments: SeedTableSummary | None = None


class SeedRefreshOut(BaseModel):
    seed_version: str
    tables: SeedTablesSummary
