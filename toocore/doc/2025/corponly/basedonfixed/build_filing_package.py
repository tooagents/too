"""
Build complete 2025 T2 filing package from the FIXED journal entries.
Source of truth: ../fixed_donotchange/journal_entries.xlsx (do not change)
Adds: Trial Balance, Income Statement, Balance Sheet, GIFI Summary.
"""
import pandas as pd
import xlsxwriter

JE = '../fixed_donotchange/journal_entries.xlsx'
OUT = '2025_T2_FILING_PACKAGE_v2.xlsx'

df = pd.read_excel(JE)
df = df[df['Account'].notna() & (df['Account'] != 'TOTAL:')].copy()
df['Debit'] = df['Debit'].fillna(0)
df['Credit'] = df['Credit'].fillna(0)

bal = df.groupby('Account').agg(D=('Debit', 'sum'), C=('Credit', 'sum'))
bal['Net'] = bal['D'] - bal['C']

def net(acct_substr):
    m = bal[bal.index.str.contains(acct_substr, regex=False)]
    return m['Net'].sum()

# Classify accounts
ASSET = ['TD Business', 'BMO Business', 'Manulife Business', 'HST Recoverable',
         'Computer Hardware', 'Accumulated Depreciation', 'Shareholder Loan']
LIAB = ['HST Payable']
EQUITY = ['Retained Earnings']
REVENUE = ['Corporate Income']
EXPENSE = ['Advertising', 'Bank Charges', 'Business Travel', 'Depreciation (CCA)', 'Insurance',
           'Legal Fees', 'Meals', 'Office Expenses', 'Professional Fees', 'Property Taxes',
           'Repairs', 'Subcontractor', 'Telephone', 'Training', 'Utilities', 'Vehicle']

revenue = -net('Corporate Income')
expenses = sum(bal.loc[a, 'Net'] for a in bal.index
               if any(e in a for e in EXPENSE))
net_income = revenue - expenses
tax = round(net_income * 0.122, 2)

wb = xlsxwriter.Workbook(OUT)
h = wb.add_format({'bold': True, 'bg_color': '#4472C4', 'font_color': 'white', 'border': 1})
b = wb.add_format({'bold': True})
cur = wb.add_format({'num_format': '#,##0.00'})
curb = wb.add_format({'num_format': '#,##0.00', 'bold': True, 'top': 1})
title = wb.add_format({'bold': True, 'font_size': 14})

# ---- Journal Entries (copy verbatim) ----
ws = wb.add_worksheet('Journal Entries')
je = pd.read_excel(JE)
for c, col in enumerate(je.columns):
    ws.write(0, c, col, h)
ws.set_column('A:A', 7); ws.set_column('B:B', 12); ws.set_column('C:C', 48)
ws.set_column('D:E', 13); ws.set_column('F:F', 28); ws.set_column('G:G', 10)
for r, (_, row) in enumerate(je.iterrows(), 1):
    ws.write(r, 0, row['Entry'] if pd.notna(row['Entry']) else '')
    ws.write(r, 1, str(row['Date'])[:10] if pd.notna(row['Date']) else '')
    ws.write(r, 2, row['Account'] if pd.notna(row['Account']) else '')
    if pd.notna(row['Debit']): ws.write(r, 3, row['Debit'], cur)
    if pd.notna(row['Credit']): ws.write(r, 4, row['Credit'], cur)
    ws.write(r, 5, row['Memo'] if pd.notna(row['Memo']) else '')
    ws.write(r, 6, row['Source'] if pd.notna(row['Source']) else '')

# ---- Trial Balance ----
ws = wb.add_worksheet('Trial Balance')
ws.set_column('A:A', 48); ws.set_column('B:C', 14)
ws.write(0, 0, 'TRIAL BALANCE - Dec 31, 2025', title)
ws.write(2, 0, 'Account', h); ws.write(2, 1, 'Debit', h); ws.write(2, 2, 'Credit', h)
r = 3
td = tc = 0
for acct in sorted(bal.index):
    n = bal.loc[acct, 'Net']
    ws.write(r, 0, acct)
    if n > 0:
        ws.write(r, 1, n, cur); td += n
    else:
        ws.write(r, 2, -n, cur); tc += -n
    r += 1
ws.write(r, 0, 'TOTAL', b)
ws.write(r, 1, td, curb); ws.write(r, 2, tc, curb)

# ---- Income Statement ----
ws = wb.add_worksheet('Income Statement')
ws.set_column('A:A', 40); ws.set_column('B:B', 14)
ws.write(0, 0, 'INCOME STATEMENT - FY2025', title)
ws.write(2, 0, 'REVENUE', b)
ws.write(3, 0, 'Corporate Income - Software Engineering (net of HST)')
ws.write(3, 1, revenue, cur)
ws.write(5, 0, 'EXPENSES', b)
r = 6
for acct in sorted(a for a in bal.index if any(e in a for e in EXPENSE)):
    ws.write(r, 0, acct); ws.write(r, 1, bal.loc[acct, 'Net'], cur); r += 1
ws.write(r, 0, 'Total Expenses', b); ws.write(r, 1, expenses, curb); r += 2
ws.write(r, 0, 'NET INCOME', b); ws.write(r, 1, net_income, curb); r += 1
ws.write(r, 0, 'Tax @ 12.2% (ON small business)', b); ws.write(r, 1, tax, curb); r += 1
ws.write(r, 0, 'Tax paid to CRA (RC0001)'); ws.write(r, 1, 2620.43, cur)

# ---- Balance Sheet ----
ws = wb.add_worksheet('Balance Sheet')
ws.set_column('A:A', 40); ws.set_column('B:B', 14)
ws.write(0, 0, 'BALANCE SHEET - Dec 31, 2025', title)
r = 2
ws.write(r, 0, 'ASSETS', b); r += 1
asset_total = 0
for acct in ['TD Business Chequing (1000)', 'BMO Business Chequing (1010)',
             'Manulife Business Advantage (1020)', 'HST Recoverable (1200)',
             'Computer Hardware (1741)', 'Accumulated Depreciation (1742)',
             'Shareholder Loan Payable (3640)']:
    if acct in bal.index:
        v = bal.loc[acct, 'Net']
        label = acct
        if 'Shareholder' in acct:
            label = 'Shareholder Loan Receivable (due from shareholder)'
        ws.write(r, 0, label); ws.write(r, 1, v, cur); asset_total += v; r += 1
ws.write(r, 0, 'Total Assets', b); ws.write(r, 1, asset_total, curb); r += 2
ws.write(r, 0, 'LIABILITIES', b); r += 1
liab_total = 0
for acct in ['HST Payable (2100)']:
    v = -bal.loc[acct, 'Net']
    ws.write(r, 0, acct); ws.write(r, 1, v, cur); liab_total += v; r += 1
ws.write(r, 0, 'Total Liabilities', b); ws.write(r, 1, liab_total, curb); r += 2
ws.write(r, 0, 'EQUITY', b); r += 1
opening_re = -bal.loc['Retained Earnings (3100)', 'Net']  # negative = deficit
ws.write(r, 0, 'Retained Earnings (opening deficit)'); ws.write(r, 1, opening_re, cur); r += 1
ws.write(r, 0, 'Net Income (current year)'); ws.write(r, 1, net_income, cur); r += 1
equity_total = opening_re + net_income
ws.write(r, 0, 'Total Equity', b); ws.write(r, 1, equity_total, curb); r += 2
ws.write(r, 0, 'Liabilities + Equity', b)
ws.write(r, 1, liab_total + equity_total, curb); r += 1
ws.write(r, 0, 'CHECK: Assets = L+E', b)
ws.write(r, 1, asset_total - (liab_total + equity_total), curb)

# ---- GIFI Summary (Schedule 100 balance sheet + Schedule 125 income stmt) ----
ws = wb.add_worksheet('GIFI Summary')
ws.set_column('A:A', 10); ws.set_column('B:B', 46); ws.set_column('C:C', 14)
ws.write(0, 0, 'GIFI - T2 Schedules 100 & 125', title)

def acct(name):
    return bal.loc[name, 'Net'] if name in bal.index else 0

# Schedule 100 - Balance Sheet
ws.write(2, 0, 'SCHEDULE 100 - BALANCE SHEET', b)
ws.write(3, 0, 'GIFI', h); ws.write(3, 1, 'Description', h); ws.write(3, 2, 'Amount', h)
s100 = [
    ('1001', 'Cash', acct('TD Business Chequing (1000)') + acct('BMO Business Chequing (1010)') + acct('Manulife Business Advantage (1020)')),
    ('1067', 'GST/HST receivable (ITC)', acct('HST Recoverable (1200)')),
    ('1300', 'Due from shareholder(s)/director(s)', acct('Shareholder Loan Payable (3640)')),
    ('1740', 'Computer equipment/hardware (cost)', acct('Computer Hardware (1741)')),
    ('1741', 'Accumulated amortization of computer equip.', acct('Accumulated Depreciation (1742)')),
    ('2620', 'GST/HST payable', -acct('HST Payable (2100)')),
    ('3600', 'Retained earnings/deficit - end', -acct('Retained Earnings (3100)') + net_income),
]
r = 4
for code, desc, amt in s100:
    ws.write(r, 0, code); ws.write(r, 1, desc); ws.write(r, 2, amt, cur); r += 1

# Schedule 125 - Income Statement (one GIFI code per category)
r += 1
ws.write(r, 0, 'SCHEDULE 125 - INCOME STATEMENT', b); r += 1
ws.write(r, 0, 'GIFI', h); ws.write(r, 1, 'Description', h); ws.write(r, 2, 'Amount', h); r += 1
ws.write(r, 0, '8000'); ws.write(r, 1, 'Revenue (net of GST/HST)'); ws.write(r, 2, revenue, cur); r += 1
s125 = [
    ('8521', 'Advertising and promotion', acct('Advertising and Promotion')),
    ('8714', 'Bank charges', acct('Bank Charges')),
    ('9200', 'Travel expenses', acct('Business Travel')),
    ('8670', 'Amortization/depreciation (CCA)', acct('Depreciation (CCA)')),
    ('8690', 'Insurance', acct('Insurance')),
    ('8860', 'Legal/professional fees - Legal', acct('Legal Fees')),
    ('8523', 'Meals and entertainment (50%)', acct('Meals and Entertainment (50%)')),
    ('8811', 'Office stationery/supplies', acct('Office Expenses')),
    ('8860', 'Professional fees', acct('Professional Fees')),
    ('9180', 'Property taxes', acct('Property Taxes')),
    ('8960', 'Repairs and maintenance', acct('Repairs and Maintenance')),
    ('8360', 'Subcontracts', acct('Subcontractor Expense')),
    ('9225', 'Telephone and telecommunications', acct('Telephone and Internet')),
    ('9210', 'Training/education', acct('Training and Education')),
    ('9220', 'Utilities (gas/electric/water)', acct('Utilities - Electricity') + acct('Utilities - Gas') + acct('Utilities - Water')),
    ('9281', 'Motor vehicle expenses', acct('Vehicle Expense')),
]
for code, desc, amt in s125:
    ws.write(r, 0, code); ws.write(r, 1, desc); ws.write(r, 2, amt, cur); r += 1
ws.write(r, 0, '9368'); ws.write(r, 1, 'Total expenses', b); ws.write(r, 2, expenses, curb); r += 1
ws.write(r, 0, '9970'); ws.write(r, 1, 'Net income (loss) before taxes', b); ws.write(r, 2, net_income, curb); r += 1

# integrity check: sum of detailed S125 expense lines must equal total
s125_sum = sum(a for _, _, a in s125)
print('S125 expense lines sum: %.2f  vs Total expenses: %.2f  diff: %.2f' % (s125_sum, expenses, s125_sum - expenses))

wb.close()
print('Net income: %.2f' % net_income)
print('Tax @12.2%%: %.2f (target 2620.43)' % tax)
print('TB: Dr %.2f = Cr %.2f' % (td, tc))
print('BS check (should be 0): %.2f' % (asset_total - (liab_total + equity_total)))
print('Wrote:', OUT)
