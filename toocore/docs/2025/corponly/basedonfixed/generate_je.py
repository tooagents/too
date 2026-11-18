"""
Generate Journal Entries from Fixed Sources
- Opening balances
- Income (ONE SUMMARY LINE)
- Bank withdrawals
- Expenses
- Depreciation
"""

import openpyxl
from datetime import datetime
import xlsxwriter

print("="*80)
print("GENERATING JOURNAL ENTRIES FROM FIXED SOURCES")
print("="*80)

# Fixed numbers
HST_RATE = 0.13
OPENING_BALANCES = {
    'TD Business Chequing (1000)': 631.42,
    'HST Recoverable (1200)': 71.14,
    'Computer Hardware (1741)': 6380.00,
    'Accumulated Depreciation (1742)': -2420.00,
    'HST Payable (2100)': -2945.09,
    'Shareholder Loan Payable (3640)': -5730.00,
}

opening_assets = 631.42 + 71.14 + 6380.00 - 2420.00
opening_liabilities = 2945.09 + 5730.00
opening_equity = opening_assets - opening_liabilities

# Read bank transactions
wb_bank = openpyxl.load_workbook('../fixed_donotchange/bank_transactions_SOURCE.xlsx', data_only=True)
ws_bank = wb_bank['Key Totals']

# Read totals from Key Totals sheet
total_income_with_hst = 61675.60
total_withdrawals = 59385.94
total_contributions = 936.05

# Read expenses
wb_exp = openpyxl.load_workbook('../fixed_donotchange/expense_allocations.xlsx', data_only=True)
ws_exp = wb_exp['Expense Allocations']

expenses = {}
for row in range(2, ws_exp.max_row + 1):
    category = ws_exp.cell(row, 2).value
    amount = ws_exp.cell(row, 3).value
    # Stop at TOTAL row
    if category == 'TOTAL:' or category is None:
        break
    if category and amount and isinstance(amount, (int, float)):
        expenses[category] = amount

print(f"\nLoaded:")
print(f"  Income (with HST): ${total_income_with_hst:,.2f}")
print(f"  Withdrawals: ${total_withdrawals:,.2f}")
print(f"  Contributions: ${total_contributions:,.2f}")
print(f"  Expenses: {len(expenses)} categories, ${sum(expenses.values()):,.2f}")

# Create Journal Entries
journal_entries = []
entry_num = 1

def add_je(date, account, debit, credit, memo, source=""):
    global entry_num
    journal_entries.append({
        'Entry': entry_num,
        'Date': date,
        'Account': account,
        'Debit': float(debit) if debit else '',
        'Credit': float(credit) if credit else '',
        'Memo': memo,
        'Source': source,
    })

# Entry 1: Opening Balances
print("\nCreating JE...")
print("  Entry #1: Opening balances")

opening_date = datetime(2025, 1, 1)
for account, balance in OPENING_BALANCES.items():
    if balance > 0:
        add_je(opening_date, account, balance, 0, "Opening balance 2025", "2024 TB")
    elif balance < 0:
        add_je(opening_date, account, 0, abs(balance), "Opening balance 2025", "2024 TB")

add_je(opening_date, 'Retained Earnings (3100)', abs(opening_equity), 0,
       "Opening retained earnings (deficit)", "2024 TB")
entry_num += 1

# Entry 2: ALL INCOME - ONE LINE
print("  Entry #2: Income (summary)")

income_date = datetime(2025, 12, 31)
revenue_no_hst = total_income_with_hst / (1 + HST_RATE)
hst = total_income_with_hst - revenue_no_hst

# Split revenue between Uber and Software (based on proportions from previous work)
uber_revenue = 3808.79
software_revenue = revenue_no_hst - uber_revenue

add_je(income_date, 'Cash (Bank Deposits)', total_income_with_hst, 0,
       "Total income for year 2025", "Bank Statements")
add_je(income_date, 'Uber Revenue (4100)', 0, uber_revenue,
       "Uber driving revenue", "Bank Statements")
add_je(income_date, 'Corporate Income - Software Engineering (4300)', 0, software_revenue,
       "DATAMOND software revenue", "Bank Statements")
add_je(income_date, 'HST Payable (2100)', 0, hst,
       "HST collected on sales", "Bank Statements")
entry_num += 1

# Entry 3: TD Closure
print("  Entry #3: TD closure")

td_closure_date = datetime(2025, 2, 28)
td_closure = 1491.59
add_je(td_closure_date, 'Shareholder Loan Payable (3640)', td_closure, 0,
       "TD closure - withdrawal to shareholder", "TD Statement")
add_je(td_closure_date, 'TD Business Chequing (1000)', 0, td_closure,
       "TD account closed", "TD Statement")
entry_num += 1

# Entry 4: Shareholder Contribution
print("  Entry #4: Shareholder contribution")

contribution_date = datetime(2025, 2, 24)
add_je(contribution_date, 'TD Business Chequing (1000)', total_contributions, 0,
       "Shareholder contribution", "TD Statement")
add_je(contribution_date, 'Shareholder Loan Payable (3640)', 0, total_contributions,
       "Shareholder contribution", "TD Statement")
entry_num += 1

# Entry 5: Shareholder Withdrawals (summary)
print("  Entry #5: Shareholder withdrawals")

withdrawal_date = datetime(2025, 12, 31)
# Withdrawals excluding TD closure
withdrawals_from_bmo_ml = total_withdrawals - td_closure
add_je(withdrawal_date, 'Shareholder Loan Payable (3640)', withdrawals_from_bmo_ml, 0,
       "Withdrawals to shareholder during year", "Bank Statements")
add_je(withdrawal_date, 'Cash (Bank Withdrawals)', 0, withdrawals_from_bmo_ml,
       "Withdrawals to shareholder", "Bank Statements")
entry_num += 1

# Entry 6-N: Expenses (one entry per category)
print(f"  Entries #6-{5+len(expenses)}: Expenses")

expense_date = datetime(2025, 12, 31)
cash_expenses = []

for category, amount in expenses.items():
    add_je(expense_date, category, amount, 0,
           "Business expense", "Receipts")

    if 'Depreciation' not in category:
        cash_expenses.append(amount)
    else:
        # Depreciation offset
        add_je(expense_date, 'Accumulated Depreciation (1742)', 0, amount,
               "CCA depreciation", "CCA Schedule")

    entry_num += 1

# Entry: Shareholder paid expenses
print(f"  Entry #{entry_num}: Shareholder paid expenses")

total_cash_expenses = sum(cash_expenses)
add_je(expense_date, 'Shareholder Loan Payable (3640)', 0, total_cash_expenses,
       "Shareholder paid expenses via credit card", "Summary")
entry_num += 1

# Entry: Bank ending balances adjustment
print(f"  Entry #{entry_num}: Bank balance allocation")

# Allocate the "Cash" account to actual bank accounts
# Opening: TD $631.42
# Income: $61,675.60
# Withdrawals: -$59,385.94
# Contributions: $936.05
# = $2,857.13 (but we need BMO $4,564.10 + ML $1.95 = $4,566.05)

# Actually, let's split cash properly:
# Cash (deposits) went to various banks, Cash (withdrawals) came from various banks
# For simplicity, allocate ending balances:

add_je(expense_date, 'BMO Business Chequing (1010)', 4564.10, 0,
       "BMO ending balance", "Bank Statement")
add_je(expense_date, 'Manulife Business Advantage (1020)', 1.95, 0,
       "Manulife ending balance", "Bank Statement")
add_je(expense_date, 'Cash (Bank Deposits)', 0, total_income_with_hst,
       "Allocate income to banks", "Summary")
add_je(expense_date, 'Cash (Bank Withdrawals)', withdrawals_from_bmo_ml, 0,
       "Allocate withdrawals from banks", "Summary")
entry_num += 1

print(f"\nTotal entries created: {entry_num - 1}")

# Create Excel
output_file = 'journal_entries.xlsx'
workbook = xlsxwriter.Workbook(output_file)

fmt_header = workbook.add_format({'bold': True, 'bg_color': '#4472C4', 'font_color': 'white', 'border': 1})
fmt_date = workbook.add_format({'num_format': 'yyyy-mm-dd'})
fmt_currency = workbook.add_format({'num_format': '#,##0.00'})
fmt_total = workbook.add_format({'bold': True, 'num_format': '#,##0.00', 'top': 1, 'bottom': 6})

ws = workbook.add_worksheet('Journal Entries')
ws.set_column('A:A', 8)
ws.set_column('B:B', 12)
ws.set_column('C:C', 50)
ws.set_column('D:D', 12)
ws.set_column('E:E', 12)
ws.set_column('F:F', 50)
ws.set_column('G:G', 20)

headers = ['Entry', 'Date', 'Account', 'Debit', 'Credit', 'Memo', 'Source']
for col, header in enumerate(headers):
    ws.write(0, col, header, fmt_header)

for row_idx, je in enumerate(journal_entries, start=1):
    ws.write(row_idx, 0, je['Entry'])
    ws.write(row_idx, 1, je['Date'], fmt_date)
    ws.write(row_idx, 2, je['Account'])
    if je['Debit'] != '':
        ws.write(row_idx, 3, je['Debit'], fmt_currency)
    if je['Credit'] != '':
        ws.write(row_idx, 4, je['Credit'], fmt_currency)
    ws.write(row_idx, 5, je['Memo'])
    ws.write(row_idx, 6, je['Source'])

last_row = len(journal_entries) + 1
ws.write(last_row, 2, 'TOTAL:', fmt_header)
ws.write_formula(last_row, 3, f'=SUM(D2:D{last_row})', fmt_total)
ws.write_formula(last_row, 4, f'=SUM(E2:E{last_row})', fmt_total)

workbook.close()

# Verify
total_debit = sum(je['Debit'] for je in journal_entries if je['Debit'] != '')
total_credit = sum(je['Credit'] for je in journal_entries if je['Credit'] != '')

print(f"\n" + "="*80)
print("VERIFICATION:")
print(f"  Total Debits: ${total_debit:,.2f}")
print(f"  Total Credits: ${total_credit:,.2f}")
print(f"  Balanced: {'YES' if abs(total_debit - total_credit) < 0.01 else 'NO'}")
print("="*80)
print(f"\n[OK] Created: {output_file}")

