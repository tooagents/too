from typing import TypedDict

from app.schemas.sch_acc_coa import COARoot, NormalBalanceType


_DEFAULT_NORMAL_BALANCE: dict[COARoot, NormalBalanceType] = {
    "asset": "debit",
    "expense": "debit",
    "liability": "credit",
    "equity": "credit",
    "revenue": "credit",
}

_LEVEL1_CODES: dict[COARoot, str] = {
    "asset": "1000",
    "liability": "2000",
    "equity": "3000",
    "revenue": "4000",
    "expense": "5000",
}

_LEVEL1_LABELS: dict[COARoot, str] = {
    "asset": "Asset",
    "liability": "Liability",
    "equity": "Equity",
    "revenue": "Revenue",
    "expense": "Expense",
}


class CoaTemplateAccount(TypedDict):
    coa_code: str
    coa_name: str
    parent_id: COARoot
    coa_status: str | None
    coa_level: str | None
    normal_balance: NormalBalanceType
    is_posting: bool
    is_readonly: bool


def _label(value: str) -> str:
    return " ".join(value.replace("_", " ").replace("-", " ").split()).title()


def _level1_key(value: str) -> COARoot:
    return value.strip().lower()  # type: ignore[return-value]


def _level1_row(level1: COARoot) -> CoaTemplateAccount:
    return {
        "coa_code": _LEVEL1_CODES[level1],
        "coa_name": _LEVEL1_LABELS[level1],
        "parent_id": _LEVEL1_LABELS[level1],
        "coa_status": None,
        "coa_level": None,
        "normal_balance": _DEFAULT_NORMAL_BALANCE[level1],
        "is_posting": False,
        "is_readonly": True,
    }


def _group_row(
    code: str,
    name: str,
    level1: COARoot,
    level2: str,
    level3: str | None = None,
) -> CoaTemplateAccount:
    return {
        "coa_code": code,
        "coa_name": name,
        "parent_id": _LEVEL1_LABELS[level1],
        "coa_status": _label(level2),
        "coa_level": _label(level3) if level3 else None,
        "normal_balance": _DEFAULT_NORMAL_BALANCE[level1],
        "is_posting": False,
        "is_readonly": False,
    }


def _posting(
    code: str,
    name: str,
    level1: COARoot,
    level2: str,
    level3: str,
    normal_balance: NormalBalanceType,
) -> CoaTemplateAccount:
    return {
        "coa_code": code,
        "coa_name": name,
        "parent_id": _LEVEL1_LABELS[level1],
        "coa_status": _label(level2),
        "coa_level": _label(level3),
        "normal_balance": normal_balance,
        "is_posting": True,
        "is_readonly": False,
    }


def _with_hierarchy_rows(posting_accounts: list[CoaTemplateAccount]) -> list[CoaTemplateAccount]:
    rows: list[CoaTemplateAccount] = []
    seen_level1: set[COARoot] = set()
    level2_blocks: dict[tuple[COARoot, str], int] = {}
    level2_codes: dict[tuple[COARoot, str], str] = {}
    level3_codes: dict[tuple[COARoot, str, str], str] = {}
    level3_counts: dict[tuple[COARoot, str], int] = {}
    posting_counts: dict[tuple[COARoot, str, str], int] = {}
    next_level2_block: dict[COARoot, int] = {}

    for account in posting_accounts:
        level1 = _level1_key(account["parent_id"])
        level2 = account["coa_status"]
        level3 = account["coa_level"]
        if level2 is None or level3 is None:
            continue
        level2_key = (level1, level2)
        level3_key = (level1, level2, level3)
        if level3_key in level3_codes:
            continue
        level3_codes[level3_key] = ""
        level2_blocks[level2_key] = level2_blocks.get(level2_key, 0) + 1

    level3_codes.clear()

    for account in posting_accounts:
        level1 = _level1_key(account["parent_id"])
        level2 = account["coa_status"]
        level3 = account["coa_level"]

        if level1 not in seen_level1:
            rows.append(_level1_row(level1))
            seen_level1.add(level1)

        if level2 is not None:
            level2_key = (level1, level2)
            if level2_key not in level2_codes:
                block_start = next_level2_block.get(level1, 1)
                reserved_blocks = max(1, (level2_blocks.get(level2_key, 1) + 8) // 9)
                next_level2_block[level1] = block_start + reserved_blocks
                level2_code = f"{_LEVEL1_CODES[level1][0]}{block_start}00"
                level2_codes[level2_key] = level2_code
                rows.append(_group_row(level2_code, _label(level2), level1, level2))

            if level3 is not None:
                level3_key = (level1, level2, level3)
                if level3_key not in level3_codes:
                    level3_parent_key = (level1, level2)
                    level3_counts[level3_parent_key] = level3_counts.get(level3_parent_key, 0) + 1
                    level3_index = level3_counts[level3_parent_key]
                    block_offset = (level3_index - 1) // 9
                    level3_digit = ((level3_index - 1) % 9) + 1
                    level3_code = f"{level2_codes[level2_key][0]}{int(level2_codes[level2_key][1]) + block_offset}{level3_digit}0"
                    level3_codes[level3_key] = level3_code
                    rows.append(_group_row(level3_code, _label(level3), level1, level2, level3))

                posting_counts[level3_key] = posting_counts.get(level3_key, 0) + 1
                account = {
                    **account,
                    "coa_code": f"{level3_codes[level3_key][:3]}{posting_counts[level3_key]}",
                }

        rows.append(account)

    return rows


def minimal_ca_template() -> list[CoaTemplateAccount]:
    return _with_hierarchy_rows([
        _posting("1000", "Bank", "asset", "current_asset", "cash_and_bank", "debit"),
        _posting("1100", "Accounts Receivable", "asset", "current_asset", "accounts_receivable", "debit"),
        _posting("2000", "Accounts Payable", "liability", "current_liability", "accounts_payable", "credit"),
        _posting("2150", "GST/HST Payable", "liability", "current_liability", "sales_tax", "credit"),
        _posting("3000", "Owner Equity", "equity", "equity", "owner_equity", "credit"),
        _posting("3900", "Retained Earnings", "equity", "equity", "retained_earnings", "credit"),
        _posting("4000", "Sales", "revenue", "operating_revenue", "sales_revenue", "credit"),
        _posting("5000", "General Expense", "expense", "operating_expense", "operating_expenses", "debit"),
    ])


def cra_reporting_ca_template() -> list[CoaTemplateAccount]:
    return _with_hierarchy_rows([
        _posting("1000", "Bank", "asset", "current_asset", "cash_and_bank", "debit"),
        _posting("1050", "Savings", "asset", "current_asset", "cash_and_bank", "debit"),
        _posting("1100", "Accounts Receivable", "asset", "current_asset", "accounts_receivable", "debit"),
        _posting("1200", "GST/HST Receivable", "asset", "current_asset", "sales_tax", "debit"),
        _posting("1500", "Equipment", "asset", "non_current_asset", "property_plant_equipment", "debit"),
        _posting("2000", "Accounts Payable", "liability", "current_liability", "accounts_payable", "credit"),
        _posting("2150", "GST/HST Payable", "liability", "current_liability", "sales_tax", "credit"),
        _posting("2200", "Payroll Liabilities", "liability", "current_liability", "payroll_liabilities", "credit"),
        _posting("3000", "Owner Contributions", "equity", "equity", "owner_equity", "credit"),
        _posting("3100", "Owner Draws", "equity", "equity", "owner_draws", "debit"),
        _posting("3900", "Retained Earnings", "equity", "equity", "retained_earnings", "credit"),
        _posting("4000", "Business Income", "revenue", "operating_revenue", "sales_revenue", "credit"),
        _posting("4100", "Professional Fees Revenue", "revenue", "operating_revenue", "service_revenue", "credit"),
        _posting("5000", "Advertising", "expense", "operating_expense", "advertising", "debit"),
        _posting("5010", "Meals and Entertainment", "expense", "operating_expense", "meals_and_entertainment", "debit"),
        _posting("5020", "Bad Debts", "expense", "operating_expense", "bad_debts", "debit"),
        _posting("5030", "Insurance", "expense", "operating_expense", "insurance", "debit"),
        _posting("5040", "Interest and Bank Charges", "expense", "non_operating_expense", "interest_and_bank_charges", "debit"),
        _posting("5050", "Business Taxes, Licences and Memberships", "expense", "operating_expense", "taxes_licenses_memberships", "debit"),
        _posting("5060", "Office Expenses", "expense", "operating_expense", "office_expenses", "debit"),
        _posting("5070", "Supplies", "expense", "operating_expense", "supplies", "debit"),
        _posting("5080", "Legal, Accounting and Other Professional Fees", "expense", "operating_expense", "professional_fees", "debit"),
        _posting("5090", "Management and Administration Fees", "expense", "operating_expense", "management_admin_fees", "debit"),
        _posting("5100", "Rent", "expense", "operating_expense", "rent", "debit"),
        _posting("5110", "Maintenance and Repairs", "expense", "operating_expense", "repairs_maintenance", "debit"),
        _posting("5120", "Salaries, Wages and Benefits", "expense", "operating_expense", "payroll_expense", "debit"),
        _posting("5130", "Property Taxes", "expense", "operating_expense", "property_taxes", "debit"),
        _posting("5140", "Travel", "expense", "operating_expense", "travel", "debit"),
        _posting("5150", "Telephone and Utilities", "expense", "operating_expense", "telephone_utilities", "debit"),
        _posting("5160", "Fuel Costs", "expense", "operating_expense", "fuel_costs", "debit"),
        _posting("5170", "Delivery, Freight and Express", "expense", "operating_expense", "delivery_freight", "debit"),
        _posting("5180", "Motor Vehicle Expenses", "expense", "operating_expense", "motor_vehicle", "debit"),
        _posting("5190", "Capital Cost Allowance", "expense", "operating_expense", "capital_cost_allowance", "debit"),
        _posting("5200", "Other Expenses", "expense", "operating_expense", "other_expenses", "debit"),
    ])


def regular_sme_ca_template() -> list[CoaTemplateAccount]:
    return _with_hierarchy_rows([
        _posting("1000", "Operating Bank", "asset", "current_asset", "cash_and_bank", "debit"),
        _posting("1010", "Savings", "asset", "current_asset", "cash_and_bank", "debit"),
        _posting("1020", "Undeposited Funds", "asset", "current_asset", "cash_and_bank", "debit"),
        _posting("1100", "Accounts Receivable", "asset", "current_asset", "accounts_receivable", "debit"),
        _posting("1150", "Allowance for Doubtful Accounts", "asset", "current_asset", "accounts_receivable", "credit"),
        _posting("1200", "Inventory", "asset", "current_asset", "inventory", "debit"),
        _posting("1250", "Prepaid Expenses", "asset", "current_asset", "prepaid_expenses", "debit"),
        _posting("1300", "GST/HST Receivable", "asset", "current_asset", "sales_tax", "debit"),
        _posting("1500", "Computer Equipment", "asset", "non_current_asset", "equipment", "debit"),
        _posting("1510", "Furniture and Fixtures", "asset", "non_current_asset", "equipment", "debit"),
        _posting("1600", "Leasehold Improvements", "asset", "non_current_asset", "leasehold_improvements", "debit"),
        _posting("2000", "Accounts Payable", "liability", "current_liability", "accounts_payable", "credit"),
        _posting("2100", "Credit Card Payable", "liability", "current_liability", "credit_cards", "credit"),
        _posting("2150", "GST/HST Payable", "liability", "current_liability", "sales_tax", "credit"),
        _posting("2200", "Payroll Source Deductions Payable", "liability", "current_liability", "payroll_liabilities", "credit"),
        _posting("2210", "Wages Payable", "liability", "current_liability", "payroll_liabilities", "credit"),
        _posting("2300", "Customer Deposits", "liability", "current_liability", "deferred_revenue", "credit"),
        _posting("2500", "Business Loan Payable", "liability", "non_current_liability", "loans_payable", "credit"),
        _posting("3000", "Owner Contributions", "equity", "equity", "owner_equity", "credit"),
        _posting("3100", "Owner Draws", "equity", "equity", "owner_draws", "debit"),
        _posting("3900", "Retained Earnings", "equity", "equity", "retained_earnings", "credit"),
        _posting("4000", "Product Sales", "revenue", "operating_revenue", "product_sales", "credit"),
        _posting("4100", "Service Revenue", "revenue", "operating_revenue", "service_revenue", "credit"),
        _posting("4200", "Subscription Revenue", "revenue", "operating_revenue", "subscription_revenue", "credit"),
        _posting("4300", "Shipping Income", "revenue", "operating_revenue", "shipping_income", "credit"),
        _posting("4900", "Interest Income", "revenue", "non_operating_revenue", "interest_income", "credit"),
        _posting("5000", "Cost of Goods Sold", "expense", "cost_of_sales", "cost_of_goods_sold", "debit"),
        _posting("5010", "Inventory Purchases", "expense", "cost_of_sales", "inventory_purchases", "debit"),
        _posting("5020", "Direct Labour", "expense", "cost_of_sales", "direct_labour", "debit"),
        _posting("5030", "Subcontractors", "expense", "cost_of_sales", "subcontractors", "debit"),
        _posting("5040", "Packaging and Shipping Supplies", "expense", "cost_of_sales", "packaging_supplies", "debit"),
        _posting("5100", "Advertising and Promotion", "expense", "operating_expense", "advertising", "debit"),
        _posting("5110", "Meals and Entertainment", "expense", "operating_expense", "meals_and_entertainment", "debit"),
        _posting("5120", "Software and Subscriptions", "expense", "operating_expense", "software_subscriptions", "debit"),
        _posting("5130", "Payment Processing Fees", "expense", "operating_expense", "merchant_fees", "debit"),
        _posting("5140", "Office Supplies", "expense", "operating_expense", "office_supplies", "debit"),
        _posting("5150", "Professional Fees", "expense", "operating_expense", "professional_fees", "debit"),
        _posting("5160", "Rent", "expense", "operating_expense", "rent", "debit"),
        _posting("5170", "Repairs and Maintenance", "expense", "operating_expense", "repairs_maintenance", "debit"),
        _posting("5180", "Salaries and Wages", "expense", "operating_expense", "payroll_expense", "debit"),
        _posting("5190", "Employee Benefits", "expense", "operating_expense", "employee_benefits", "debit"),
        _posting("5200", "Telephone and Internet", "expense", "operating_expense", "telephone_internet", "debit"),
        _posting("5210", "Utilities", "expense", "operating_expense", "utilities", "debit"),
        _posting("5220", "Travel", "expense", "operating_expense", "travel", "debit"),
        _posting("5230", "Vehicle Expense", "expense", "operating_expense", "vehicle_expense", "debit"),
        _posting("5240", "Insurance", "expense", "operating_expense", "insurance", "debit"),
        _posting("5250", "Training and Education", "expense", "operating_expense", "training", "debit"),
        _posting("5300", "Bank Charges", "expense", "non_operating_expense", "bank_charges", "debit"),
        _posting("5310", "Loan Interest", "expense", "non_operating_expense", "interest_expense", "debit"),
        _posting("5320", "Foreign Exchange Gain/Loss", "expense", "non_operating_expense", "foreign_exchange", "debit"),
        _posting("5900", "Other Business Expense", "expense", "other_expense", "other_business_expense", "debit"),
    ])


COA_TEMPLATES: dict[str, tuple[str, list[CoaTemplateAccount]]] = {
    "minimal-ca": ("Minimal Canada", minimal_ca_template()),
    "cra-reporting-ca": ("CRA Reporting Canada", cra_reporting_ca_template()),
    "regular-sme-ca": ("Regular SME Canada", regular_sme_ca_template()),
}


def get_coa_template(template_key: str) -> list[CoaTemplateAccount] | None:
    if template_key == "generic":
        return generic_startup_template()
    template = COA_TEMPLATES.get(template_key)
    return template[1] if template else None


def get_coa_template_name(template_key: str) -> str | None:
    if template_key == "generic":
        return "Minimal Canada"
    template = COA_TEMPLATES.get(template_key)
    return template[0] if template else None


def list_coa_templates() -> list[dict[str, object]]:
    return [
        {"key": key, "name": name, "posting_account_count": sum(1 for account in accounts if account["is_posting"])}
        for key, (name, accounts) in COA_TEMPLATES.items()
    ]


def generic_startup_template() -> list[CoaTemplateAccount]:
    return minimal_ca_template()
