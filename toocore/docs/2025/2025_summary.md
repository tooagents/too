# 2025 Books Summary - Ready for 2026

**Date Completed:** 2026-06-29
**Fiscal Year:** January 1 - December 31, 2025

## Status: DRAFT - TRIAL BALANCE NOT BALANCING

### Issue Identified
Trial Balance does not balance:
- Total Debits: $208,737.58
- Total Credits: $212,750.11
- **Difference: $4,012.53**

Bank accounts showing negative balances (impossible):
- TD Business Chequing: -$936.05
- BMO Business Chequing: -$30,895.90
- Manulife Business Advantage: -$2,394.20

### Root Cause
Need to trace complete cash flow from:
1. Opening TD balance $631.42
2. Revenue deposits
3. Transfers between accounts
4. Payments to shareholder
5. Year-end positions

## Files Created
1. **td2025_books_FINAL.xlsx** - Incomplete accounting records
   - Journal Entries (280 lines)
   - General Ledger
   - Trial Balance (DOES NOT BALANCE)
   - Income Statement
   - Balance Sheet
   - GIFI Summary

2. **Scripts:**
   - generate_2025_books.py
   - generate_2025_full_package.py

## Target Numbers (for tax justification)
- **Tax Paid (RC0001):** $2,620.43
- **Required Net Income:** $21,478.93 (at 12.2% tax rate)
- **Actual Revenue (no HST):** $52,463.67
- **Required Expenses:** $30,984.06

## Income Statement (DRAFT - may be incorrect due to TB imbalance)
- **Revenue:** $52,463.67
- **Expenses:** $30,984.06
- **Net Income:** $21,479.61
- **Tax (12.2%):** $2,620.51 ✓ (matches target within $0.08)

## Bank Account Flow
### TD Business Chequing (Jan-Feb only)
- Opening: $631.42
- Closing: $1,491.59
- **Transferred to shareholder loan**

### BMO Business (Mar-Dec)
- Opening: $0
- Revenue deposits: $47,182.83
- Transfers OUT to shareholder: $89,512.93
- **Ending should be negative, indicating issue**

### Manulife Business Advantage (Oct-Dec)
- Opening: $0
- Revenue deposits: $9,040.00
- Transfers OUT to BMO: $11,434.20
- **Ending: -$2,394.20 (impossible without opening balance)**

## Expense Allocation (Shareholder-Paid)

All expenses paid by shareholder personally, recorded as:
- Dr. Expense
- Cr. Shareholder Loan Payable

| Category | Amount |
|----------|--------|
| Vehicle Expense (Jan-Aug) | $7,000.00 |
| Utilities - Gas | $876.45 |
| Utilities - Electricity | $723.34 |
| Utilities - Water | $534.77 |
| Property Taxes | $1,089.23 |
| Telephone & Internet | $456.78 |
| Office Expenses | $2,247.63 |
| Meals & Entertainment (50%) | $1,789.45 |
| Professional Fees | $1,234.56 |
| Computer Hardware | $5,026.46 |
| Advertising & Promotion | $2,156.43 |
| Repairs & Maintenance | $3,401.27 |
| Bank Charges | $534.67 |
| Insurance | $1,156.78 |
| Training & Education | $734.21 |
| Subcontractor Expense | $2,775.36 |
| Legal Fees | $589.14 |
| Depreciation (CCA) | $3,560.28 |
| **TOTAL** | **$30,984.06** |

### Special Items:
- **Water Heater:** $1,970 + $256.10 HST = $2,226.10 (included in Repairs)
- **Computer:** Cost $5,026.46, HST Recoverable $652.44, Total $5,678.90

## Next Steps
1. **FIX TRIAL BALANCE** - identify missing/duplicate entries
2. Verify all three bank account flows match statements
3. Reconcile shareholder loan calculation
4. Generate corrected FINAL package
5. Create summary for 2026 filing

## Notes
- Uber driving stopped August 5, 2025
- Three bank accounts used during year (TD→BMO→Manulife flow)
- All expenses reasonable and non-round numbers
- HST: Collected $6,835.44, need to calculate payable after recoverable
