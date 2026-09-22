# 2024 Books Summary - Ready for 2025

**Date Completed:** 2026-06-28
**Fiscal Year:** January 1 - December 31, 2024

## Files Created

1. **td2024_tax_package_FINAL.xlsx** - Complete accounting records
   - General Ledger
   - Trial Balance (with GIFI codes)
   - GIFI Summary (matches filed T2)
   - Journal Entries (224 lines)
   - Chart of Accounts

2. **Database Table:** `too_acc.bank_statement_transactions`
   - For importing bank PDFs via API

3. **API Endpoint:** `/api/acc/bankstatement/upload` (no auth)

## Key 2024 Numbers

| Item | Amount |
|------|--------|
| **Revenue** | $24,075.00 |
| COGS | $2,178.00 |
| **Gross Profit** | $21,897.00 |
| Total Expenses | $19,826.00 |
| **Net Income** | $71.00 |
| **Shareholder Loan (business owes you)** | **$5,730.00** |

## Chart of Accounts Structure

### Assets (1000-1999)
- 1000 - TD Business Chequing
- 1061 - Accounts Receivable
- 1200 - HST Recoverable
- 1741 - Computer Hardware (Class 50)
- 1742 - Accumulated Depreciation

### Liabilities (2000-3999)
- 2100 - HST Payable
- 2620 - Accounts Payable
- **3640 - Shareholder Loan Payable** (business owes shareholder)
- Various CC Payables (BMO, CIBC, AMEX, MBNA, etc.)

### Revenue (4000-4999)
- 4100 - Uber Revenue
- 4200 - Corporate Income - VentureLab
- 4300 - Corporate Income - Software Engineering
- 4900 - Other Income - Bank Bonus
- 4910 - Other Income - Windfall

### Expenses (5000-9999)
- 5100 - Cost of Goods Sold (GIFI 8518)
- 6100 - Bank Charges
- 6200-6220 - Utilities (Gas, Electricity, Water)
- 6300 - Property Taxes
- 6860 - Professional Fees
- 6521 - Advertising and Promotion
- 6670 - Office Expenses
- 6225 - Telephone and Utilities
- 6275 - Meals and Entertainment (50% deductible)
- 6281 - Vehicle Expense
- 6710 - Repairs and Maintenance
- 6762 - Depreciation Expense (CCA)
- 6970 - Miscellaneous Expenses

## GIFI Code Mapping (for T2)

| GIFI | Description | Account(s) |
|------|-------------|------------|
| 1001 | Cash | TD Business Chequing |
| 1741 | Computer Hardware | Computer Hardware + Accumulated Depreciation |
| 3640 | **Due to Shareholders** | **Shareholder Loan Payable** |
| 8000 | Revenue | All revenue accounts |
| 8518 | Cost of Goods Sold | COGS |
| 8860 | Professional Fees | Professional Fees |
| 8521 | Advertising and Promotion | Advertising and Promotion |
| 8670 | Office Expenses | Office Expenses |
| 9225 | Telephone and Utilities | Utilities + Phone |
| 9275 | Meals and Entertainment | Meals (50% deductible) |
| 9281 | Vehicle Expense | Vehicle Expense |
| 8710 | Repairs and Maintenance | Repairs |
| 8760 | Property Taxes | Property Taxes |
| 8762 | Depreciation (CCA) | CCA |
| 9970 | Miscellaneous | Bank Charges + Misc |

## Business Structure

- **Type:** Ontario Corporation
- **Fiscal Year End:** December 31
- **Accounting Method:** Accrual basis
- **HST Rate:** 13%
- **Primary Income:** Uber driving, VentureLab contracts, Software engineering

## Income Sources

1. **TD Bank Account** - ALL income deposited here
   - Uber revenue (with 13% HST included)
   - VentureLab payments (with 13% HST included)
   - Software engineering fees (with 13% HST included)

2. **Personal Credit Cards** - ALL expenses paid here
   - Vehicle expenses (largest: $7,755)
   - Computer purchase ($6,380)
   - COGS, professional fees, advertising, etc.

## Key Decisions Made

1. **Shareholder Loan Treatment:**
   - Personal expenses paid = credit to Shareholder Loan Payable
   - Personal withdrawals = debit to Shareholder Loan Payable
   - Net position: Business owes shareholder $5,730

2. **HST Split:**
   - All revenue has 13% HST included (split on entry)
   - All expenses with HST are split (HST Recoverable captured)
   - Net HST payable shown on balance sheet

3. **Personal CC Payments:**
   - CC payments from TD bank = reduce liability
   - Underlying CC purchases = expenses (booked as year-end adjustments for 2024)

## For 2025 Processing

### What to Collect:
1. TD Bank statement (full year or YTD)
2. **All 7 personal credit card statements** (this is critical!)
   - BMO Visa
   - CIBC Visa
   - AMEX
   - MBNA
   - National Bank MC
   - PC Mastercard
   - Canadian Tire MC

3. Vehicle logbook for business %
4. Major receipts for verification

### Process:
1. Upload TD bank statement → extract transactions
2. Upload each CC statement → extract expenses
3. Match CC expenses to business categories
4. Calculate vehicle business %
5. Generate journal entries
6. Produce GL, TB, IS, BS
7. Match to 2025 T2 (when filed)

### Opening Balances for 2025 (as of Jan 1, 2025):
- TD Business Chequing: $631.42
- HST Recoverable: $71.14
- HST Payable: $2,945.09
- Shareholder Loan Payable: **$5,730.00** (business owes you)
- Computer Hardware: $6,380.00
- Accumulated Depreciation: $2,420.00

## Important Notes

- **Never show UFile to external parties** - show them YOUR BOOKS
- Books = official financial statements
- UFile = just tax filing tool
- All receipts should eventually be linked to journal entries via "Source Document" column

## Contact Context
- Using Claude Code as replacement for QuickBooks/Xero/Wave
- Books must match filed T2 exactly
- Audit trail via Entry # in GL linking back to JE
- Receipt tracking for CRA audit readiness
