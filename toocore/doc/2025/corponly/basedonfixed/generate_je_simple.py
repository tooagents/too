"""
Simple JE - Just Fixed Numbers
"""
import openpyxl
from datetime import datetime
import xlsxwriter

# Fixed numbers
HST_RATE = 0.13
INCOME_WITH_HST = 61675.60
SHAREHOLDER_LOAN_BANK = 51074.92

# Opening balances
OPENING = {
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

# Read expenses
wb_exp = openpyxl.load_workbook('../fixed_donotchange/expense_allocations.xlsx', data_only=True)
ws_exp = wb_exp['Expense Allocations']

expenses = {}
for row in range(2, ws_exp.max_row + 1):
    cat = ws_exp.cell(row, 2).value
    amt = ws_exp.cell(row, 3).value
    if cat == 'TOTAL:' or cat is None:
        break
    if cat and amt:
        expenses[cat] = amt

# Create JE
je = []
entry_num = 1

def add(date, account, debit, credit, memo, source=""):
    global entry_num
    je.append({
        'Entry': entry_num,
        'Date': date,
        'Account': account,
        'Debit': float(debit) if debit else '',
        'Credit': float(credit) if credit else '',
        'Memo': memo,
        'Source': source,
    })

# Entry 1: Opening
d = datetime(2025, 1, 1)
for acc, bal in OPENING.items():
    if bal > 0:
        add(d, acc, bal, 0, "Opening balance", "2024 TB")
    else:
        add(d, acc, 0, abs(bal), "Opening balance", "2024 TB")
add(d, 'Retained Earnings (3100)', abs(opening_equity), 0, "Opening equity", "2024 TB")
entry_num += 1

# Entry 2: Income (ONE LINE)
d = datetime(2025, 12, 31)
revenue = INCOME_WITH_HST / 1.13
hst = INCOME_WITH_HST - revenue
add(d, 'BMO Business Chequing (1010)', INCOME_WITH_HST, 0, "Total income 2025", "Bank")
add(d, 'Corporate Income - Software Engineering (4300)', 0, revenue, "Revenue", "Bank")
add(d, 'HST Payable (2100)', 0, hst, "HST collected", "Bank")
entry_num += 1

# Entry 3-20: Expenses
for cat, amt in expenses.items():
    add(d, cat, amt, 0, "Expense", "Receipts")
    if 'Depreciation' in cat:
        add(d, 'Accumulated Depreciation (1742)', 0, amt, "CCA", "CCA")
    entry_num += 1

# Shareholder paid expenses
cash_exp = sum(amt for cat, amt in expenses.items() if 'Depreciation' not in cat)
add(d, 'Shareholder Loan Payable (3640)', 0, cash_exp, "Shareholder paid expenses", "Summary")
entry_num += 1

# Withdrawals (from bank: stage 1 = 51074.92)
# Opening -5730 + contrib 936 - withdrawals = -51074.92
# withdrawals = 5730 - 936 - 51074.92 = -46280.92 (negative means we need to debit 46280.92 + actual cash)
# Actually: 51074.92 = net result, so withdrawals - contributions - opening = 51074.92
# withdrawals = 51074.92 + 5730 - 936 = 55868.92

# But income is 61675.60, ending bank is 4566.05
# So: 631.42 + 61675.60 - withdrawals = 4566.05
# withdrawals = 631.42 + 61675.60 - 4566.05 = 57740.97

withdrawals = 57740.97
add(d, 'Shareholder Loan Payable (3640)', withdrawals, 0, "Withdrawals from bank", "Bank")
add(d, 'BMO Business Chequing (1010)', 0, withdrawals, "Cash out", "Bank")
entry_num += 1

# Bank ending adjustment
add(d, 'Manulife Business Advantage (1020)', 1.95, 0, "Manulife ending", "Bank")
add(d, 'BMO Business Chequing (1010)', 0, 1.95, "Transfer to ML", "Bank")
entry_num += 1

# Create Excel
workbook = xlsxwriter.Workbook('journal_entries.xlsx')
fmt_h = workbook.add_format({'bold': True, 'bg_color': '#4472C4', 'font_color': 'white', 'border': 1})
fmt_d = workbook.add_format({'num_format': 'yyyy-mm-dd'})
fmt_c = workbook.add_format({'num_format': '#,##0.00'})
fmt_t = workbook.add_format({'bold': True, 'num_format': '#,##0.00', 'top': 1, 'bottom': 6})

ws = workbook.add_worksheet('Journal Entries')
ws.set_column('A:A', 8)
ws.set_column('B:B', 12)
ws.set_column('C:C', 50)
ws.set_column('D:D', 12)
ws.set_column('E:E', 12)
ws.set_column('F:F', 50)
ws.set_column('G:G', 20)

headers = ['Entry', 'Date', 'Account', 'Debit', 'Credit', 'Memo', 'Source']
for col, h in enumerate(headers):
    ws.write(0, col, h, fmt_h)

for row_idx, e in enumerate(je, start=1):
    ws.write(row_idx, 0, e['Entry'])
    ws.write(row_idx, 1, e['Date'], fmt_d)
    ws.write(row_idx, 2, e['Account'])
    if e['Debit'] != '':
        ws.write(row_idx, 3, e['Debit'], fmt_c)
    if e['Credit'] != '':
        ws.write(row_idx, 4, e['Credit'], fmt_c)
    ws.write(row_idx, 5, e['Memo'])
    ws.write(row_idx, 6, e['Source'])

last = len(je) + 1
ws.write(last, 2, 'TOTAL:', fmt_h)
ws.write_formula(last, 3, f'=SUM(D2:D{last})', fmt_t)
ws.write_formula(last, 4, f'=SUM(E2:E{last})', fmt_t)

workbook.close()

dr = sum(e['Debit'] for e in je if e['Debit'] != '')
cr = sum(e['Credit'] for e in je if e['Credit'] != '')
print(f"Total DR: ${dr:,.2f}, CR: ${cr:,.2f}, Balanced: {'YES' if abs(dr-cr)<0.01 else 'NO'}")
print(f"Created: journal_entries.xlsx ({len(je)} lines, {entry_num-1} entries)")
