"""
2025 T2 DEFENSIBLE package - FINAL.
Profile: solo IT consultant (DATAMOND, e-transfer, work-from-home) + part-year Uber Eats.
Revenue = filed GST truth (overrides bank): DATAMOND 52,200 + Uber 3,754.27 = 55,954.27 net.
Quick Method spread added to income. Accounts Receivable for DATAMOND invoiced-2025-paid-2026.
WQ360 $3,000 (same-day pass-through) and Uber $450.83 (personal reimbursement) EXCLUDED as
non-income. Expenses booked GROSS (HST-included, no ITC) - matches Quick Method treatment.
Does NOT touch fixed_donotchange. Output: 2025_T2_DEFENSIBLE.xlsx
"""
import xlsxwriter

# ---------- REVENUE (filed GST truth) ----------
DATAMOND_NET = 52200.00
UBER_NET = 3754.27
REVENUE_NET = round(DATAMOND_NET + UBER_NET, 2)          # 55,954.27
HST_CHARGED = round(6786.00 + 230.50, 2)                 # 7,016.50 (billed to clients)
HST_REMITTED = 5241.43                                   # filed GST Line 109/115 (Quick Method)
QM_SPREAD = round(HST_CHARGED - HST_REMITTED, 2)         # 1,775.07 -> taxable income
T2_REVENUE = round(REVENUE_NET + QM_SPREAD, 2)           # 57,729.34

# ---------- CASH vs A/R reconciliation ----------
BILLINGS_INCL = round(REVENUE_NET + HST_CHARGED, 2)      # 62,970.77 total billed (tax-incl)
DATAMOND_RECEIVED = 54240.00                             # 24 x 2,260 in bank
UBER_RECEIVED = round(4303.95 + 131.65 - 450.83, 2)      # bank Uber less personal reimbursement = 3,984.77
INCOME_CASH = round(DATAMOND_RECEIVED + UBER_RECEIVED, 2)  # 58,224.77 tax-incl received
AR = round(BILLINGS_INCL - INCOME_CASH, 2)               # 4,746.00 DATAMOND invoiced 2025, paid 2026
UBER_REIMB = 450.83                                       # personal grocery reimbursement (business owes SH)

# ---------- EXPENSES (defensible, gross/HST-included) ----------
VEH_PCT = 0.50
veh_pool = 6928.41 + 1156.78                             # gas/maint/lease + AUTO insurance
vehicle = round(veh_pool * VEH_PCT, 2)
home_prop_tax = round(1089.23 * 0.20, 2)
home_utilities = round(1981.35 * 0.20, 2)
home_repairs = round((3373.18 - 2226.10) * 0.20, 2)     # water heater excluded (personal capital)

EXP = [
    ('Motor Vehicle (50%, incl auto ins.)', vehicle, '9281'),
    ('Depreciation (CCA - Class 50)',        3560.28, '8670'),
    ('Business Travel - air to NY',          2967.65, '9200'),
    ('Cloud/Software (AWS, Azure, subs)',    1361.28, '8811'),
    ('Professional + Legal Fees',            1306.15 + 472.66, '8860'),
    ('Training and Education',               763.33,  '9210'),
    ('Telephone and Internet',               447.41,  '9225'),
    ('Property Taxes (20% home office)',     home_prop_tax, '9180'),
    ('Utilities (20% home office)',          home_utilities, '9220'),
    ('Repairs & Maintenance (20% home)',     home_repairs, '8960'),
    ('Meals & Entertainment (50%)',          364.61,  '8523'),
    ('Bank Charges',                         181.29,  '8714'),
]
expenses = round(sum(a for _, a, _ in EXP), 2)
CCA = 3560.28
cash_expenses = round(expenses - CCA, 2)                # paid by shareholder via credit card
net_income = round(T2_REVENUE - expenses, 2)
tax = round(net_income * 0.122, 2)
TOPUP = round(tax - 2620.43, 2)

# ---------- OPENING BALANCES (2024 TB) ----------
OPEN = {
    'TD Business Chequing (1000)':       ('D', 631.42),
    'HST Recoverable (1200)':            ('D', 71.14),
    'Computer Hardware (1741)':          ('D', 6380.00),
    'Accumulated Depreciation (1742)':   ('C', 2420.00),
    'HST Payable (2100)':                ('C', 2945.09),
    'Shareholder Loan Payable (3640)':   ('C', 5730.00),
    'Retained Earnings (3100)':          ('D', 4012.53),
}

# ---------- BUILD JOURNAL ENTRIES ----------
J = []
for acct, (side, amt) in OPEN.items():
    J.append((1, '2025-01-01', acct, amt if side == 'D' else None,
              amt if side == 'C' else None, 'Opening balance', '2024 TB'))

# Revenue (accrual, Quick Method): cash received + A/R = revenue + HST remitted
J.append((2, '2025-12-31', 'BMO Business Chequing (1010)', INCOME_CASH, None, 'Income received (DATAMOND+Uber)', 'Bank'))
J.append((2, '2025-12-31', 'Accounts Receivable (1100)', AR, None, 'DATAMOND invoiced 2025, paid 2026', 'Invoices'))
J.append((2, '2025-12-31', 'Corporate Income - Software Engineering (4300)', None, T2_REVENUE, 'Revenue incl Quick Method spread', 'GST/Invoices'))
J.append((2, '2025-12-31', 'HST Payable (2100)', None, HST_REMITTED, 'HST net remitted (Quick Method)', 'GST'))

# Uber personal-grocery reimbursement: cash in, business owes shareholder (not income)
J.append((3, '2025-12-31', 'BMO Business Chequing (1010)', UBER_REIMB, None, 'Reimburse SH personal grocery', 'Bank'))
J.append((3, '2025-12-31', 'Shareholder Loan Payable (3640)', None, UBER_REIMB, 'Owed to shareholder', 'Bank'))

e = 4
for name, amt, _ in EXP:
    J.append((e, '2025-12-31', name, amt, None, 'Expense', 'Receipts'))
    if name.startswith('Depreciation'):
        J.append((e, '2025-12-31', 'Accumulated Depreciation (1742)', None, amt, 'CCA', 'CCA'))
    e += 1
J.append((e, '2025-12-31', 'Shareholder Loan Payable (3640)', None, cash_expenses, 'Shareholder paid expenses', 'Summary')); e += 1

# Withdrawal plug: force BMO to actual ending (3,932.68); reduces shareholder loan
BMO_inflow = round(INCOME_CASH + UBER_REIMB, 2)
ML_END = 1.95
BMO_END = 3932.68
withdrawal = round(BMO_inflow - BMO_END - ML_END, 2)
J.append((e, '2025-12-31', 'Shareholder Loan Payable (3640)', withdrawal, None, 'Withdrawals from bank', 'Bank'))
J.append((e, '2025-12-31', 'BMO Business Chequing (1010)', None, withdrawal, 'Cash out', 'Bank')); e += 1
J.append((e, '2025-12-31', 'Manulife Business Advantage (1020)', ML_END, None, 'Manulife ending', 'Bank'))
J.append((e, '2025-12-31', 'BMO Business Chequing (1010)', None, ML_END, 'Transfer to ML', 'Bank'))

# ---------- LEDGER ----------
bal = {}
for _, _, acct, d, c, _, _ in J:
    bal[acct] = round(bal.get(acct, 0) + (d or 0) - (c or 0), 2)
td = round(sum(v for v in bal.values() if v > 0), 2)
tc = round(sum(-v for v in bal.values() if v < 0), 2)
sl_end = bal['Shareholder Loan Payable (3640)']    # >0 = shareholder owes business

# ---------- EXCEL ----------
wb = xlsxwriter.Workbook('2025_T2_DEFENSIBLE.xlsx')
h = wb.add_format({'bold': True, 'bg_color': '#4472C4', 'font_color': 'white', 'border': 1})
b = wb.add_format({'bold': True})
cur = wb.add_format({'num_format': '#,##0.00'})
curb = wb.add_format({'num_format': '#,##0.00', 'bold': True, 'top': 1})
ttl = wb.add_format({'bold': True, 'font_size': 14})

ws = wb.add_worksheet('Journal Entries')
ws.set_column('A:A', 6); ws.set_column('B:B', 12); ws.set_column('C:C', 46); ws.set_column('D:E', 12); ws.set_column('F:F', 32); ws.set_column('G:G', 13)
for i, col in enumerate(['Entry', 'Date', 'Account', 'Debit', 'Credit', 'Memo', 'Source']):
    ws.write(0, i, col, h)
for r, (en, dt, ac, d, c, m, s) in enumerate(J, 1):
    ws.write(r, 0, en); ws.write(r, 1, dt); ws.write(r, 2, ac)
    if d: ws.write(r, 3, d, cur)
    if c: ws.write(r, 4, c, cur)
    ws.write(r, 5, m); ws.write(r, 6, s)

ws = wb.add_worksheet('Trial Balance')
ws.set_column('A:A', 46); ws.set_column('B:C', 13)
ws.write(0, 0, 'TRIAL BALANCE - Dec 31, 2025', ttl)
ws.write(2, 0, 'Account', h); ws.write(2, 1, 'Debit', h); ws.write(2, 2, 'Credit', h)
r = 3
for acct in sorted(bal):
    n = bal[acct]
    ws.write(r, 0, acct)
    if n > 0: ws.write(r, 1, n, cur)
    elif n < 0: ws.write(r, 2, -n, cur)
    r += 1
ws.write(r, 0, 'TOTAL', b); ws.write(r, 1, td, curb); ws.write(r, 2, tc, curb)

ws = wb.add_worksheet('Income Statement')
ws.set_column('A:A', 42); ws.set_column('B:B', 13)
ws.write(0, 0, 'INCOME STATEMENT - FY2025', ttl)
ws.write(2, 0, 'REVENUE', b)
ws.write(3, 0, '  Sales - net of HST (DATAMOND + Uber)'); ws.write(3, 1, REVENUE_NET, cur)
ws.write(4, 0, '  Quick Method spread (taxable)'); ws.write(4, 1, QM_SPREAD, cur)
ws.write(5, 0, 'Total Revenue', b); ws.write(5, 1, T2_REVENUE, curb)
ws.write(7, 0, 'EXPENSES', b); r = 8
for name, amt, _ in EXP:
    ws.write(r, 0, '  ' + name); ws.write(r, 1, amt, cur); r += 1
ws.write(r, 0, 'Total Expenses', b); ws.write(r, 1, expenses, curb); r += 2
ws.write(r, 0, 'NET INCOME', b); ws.write(r, 1, net_income, curb); r += 1
ws.write(r, 0, 'Tax @ 12.2%', b); ws.write(r, 1, tax, curb); r += 1
ws.write(r, 0, 'Tax already paid (RC0001)'); ws.write(r, 1, 2620.43, cur); r += 1
ws.write(r, 0, 'TOP-UP OWING TO CRA', b); ws.write(r, 1, TOPUP, curb)

ws = wb.add_worksheet('Balance Sheet')
ws.set_column('A:A', 46); ws.set_column('B:B', 13)
ws.write(0, 0, 'BALANCE SHEET - Dec 31, 2025', ttl); r = 2
ws.write(r, 0, 'ASSETS', b); r += 1
assets = 0
ASSET_ACCTS = ['TD Business Chequing (1000)', 'BMO Business Chequing (1010)', 'Manulife Business Advantage (1020)',
               'Accounts Receivable (1100)', 'HST Recoverable (1200)', 'Computer Hardware (1741)',
               'Accumulated Depreciation (1742)', 'Shareholder Loan Payable (3640)']
for acct in ASSET_ACCTS:
    v = bal.get(acct, 0)
    label = 'Shareholder Loan Receivable (due from shareholder)' if 'Shareholder' in acct else acct
    ws.write(r, 0, label); ws.write(r, 1, v, cur); assets += v; r += 1
assets = round(assets, 2)
ws.write(r, 0, 'Total Assets', b); ws.write(r, 1, assets, curb); r += 2
ws.write(r, 0, 'LIABILITIES', b); r += 1
liab = round(-bal['HST Payable (2100)'], 2)
ws.write(r, 0, 'HST Payable (2100)  [2024 + 2025 owing]'); ws.write(r, 1, liab, cur); r += 1
ws.write(r, 0, 'Total Liabilities', b); ws.write(r, 1, liab, curb); r += 2
ws.write(r, 0, 'EQUITY', b); r += 1
ws.write(r, 0, 'Retained Earnings (opening deficit)'); ws.write(r, 1, -4012.53, cur); r += 1
ws.write(r, 0, 'Net Income (current year)'); ws.write(r, 1, net_income, cur); r += 1
equity = round(-4012.53 + net_income, 2)
ws.write(r, 0, 'Total Equity', b); ws.write(r, 1, equity, curb); r += 2
ws.write(r, 0, 'CHECK: Assets - (L + E)', b); ws.write(r, 1, round(assets - liab - equity, 2), curb)

ws = wb.add_worksheet('GIFI Summary')
ws.set_column('A:A', 9); ws.set_column('B:B', 46); ws.set_column('C:C', 13)
ws.write(0, 0, 'GIFI - T2 Schedules 100 & 125', ttl)
ws.write(2, 0, 'SCHEDULE 100 - BALANCE SHEET', b)
ws.write(3, 0, 'GIFI', h); ws.write(3, 1, 'Description', h); ws.write(3, 2, 'Amount', h)
s100 = [
    ('1001', 'Cash', round(bal['TD Business Chequing (1000)'] + bal['BMO Business Chequing (1010)'] + bal['Manulife Business Advantage (1020)'], 2)),
    ('1060', 'Accounts receivable', bal.get('Accounts Receivable (1100)', 0)),
    ('1067', 'GST/HST receivable (ITC)', 71.14),
    ('1300', 'Due from shareholder(s)/director(s)', sl_end),
    ('1740', 'Computer equipment (cost)', 6380.00),
    ('1741', 'Accumulated amortization', -5980.28),
    ('2620', 'GST/HST payable', liab),
    ('3600', 'Retained earnings - end', equity),
]
r = 4
for code, desc, amt in s100:
    ws.write(r, 0, code); ws.write(r, 1, desc); ws.write(r, 2, amt, cur); r += 1
r += 1
ws.write(r, 0, 'SCHEDULE 125 - INCOME STATEMENT', b); r += 1
ws.write(r, 0, 'GIFI', h); ws.write(r, 1, 'Description', h); ws.write(r, 2, 'Amount', h); r += 1
ws.write(r, 0, '8000'); ws.write(r, 1, 'Revenue (net + Quick Method spread)'); ws.write(r, 2, T2_REVENUE, cur); r += 1
for name, amt, code in EXP:
    ws.write(r, 0, code); ws.write(r, 1, name); ws.write(r, 2, amt, cur); r += 1
ws.write(r, 0, '9368'); ws.write(r, 1, 'Total expenses', b); ws.write(r, 2, expenses, curb); r += 1
ws.write(r, 0, '9970'); ws.write(r, 1, 'Net income before tax', b); ws.write(r, 2, net_income, curb)

wb.close()

print('REVENUE net (GST truth):  %.2f' % REVENUE_NET)
print('Quick Method spread:      %.2f' % QM_SPREAD)
print('T2 REVENUE:               %.2f' % T2_REVENUE)
print('Expenses:                 %.2f' % expenses)
print('NET INCOME:               %.2f' % net_income)
print('Tax @12.2%%:               %.2f' % tax)
print('Already paid:             2620.43')
print('TOP-UP OWING:             %.2f' % TOPUP)
print('-' * 50)
print('Accounts Receivable:      %.2f' % AR)
print('Income cash received:     %.2f  (+ A/R %.2f = billings %.2f)' % (INCOME_CASH, AR, BILLINGS_INCL))
print('Withdrawal plug:          %.2f' % withdrawal)
print('Trial Balance:            Dr %.2f = Cr %.2f  (diff %.2f)' % (td, tc, round(td - tc, 2)))
print('Balance Sheet check (0):  %.2f' % round(assets - liab - equity, 2))
print('Cash ending:              %.2f  (TD %.2f + BMO %.2f + ML %.2f)' % (
    bal['TD Business Chequing (1000)'] + bal['BMO Business Chequing (1010)'] + bal['Manulife Business Advantage (1020)'],
    bal['TD Business Chequing (1000)'], bal['BMO Business Chequing (1010)'], bal['Manulife Business Advantage (1020)']))
print('Shareholder owes business: %.2f  (s.15(2) repay by 2026-12-31)' % sl_end)
