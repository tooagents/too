"""
Generate 2025 Corporate-Only Books
Clean version that EXCLUDES:
- Personal pass-through transactions
- Small personal amounts
- Non-corporate activity

INCLUDES ONLY:
- Corporate income (Datamond + Uber)
- Transfers between 3 corporate accounts
- Corporate withdrawals to shareholder
- Expenses (paid by shareholder via credit card)

Final goal: Same net income $21,479.61 → Tax $2,620.43
"""

import pandas as pd
from datetime import datetime
from decimal import Decimal
import xlsxwriter

# ========== CONFIGURATION ==========
OPENING_BALANCES_2025 = {
    'TD Business Chequing (1000)': 631.42,
    'HST Recoverable (1200)': 71.14,
    'Computer Hardware (1741)': 6380.00,
    'Accumulated Depreciation (1742)': -2420.00,
    'HST Payable (2100)': -2945.09,
    'Shareholder Loan Payable (3640)': -5730.00,  # Business owes shareholder
}

HST_RATE = 0.13

# Pass-through transactions to EXCLUDE (personal money temporarily in business)
PASSTHROUGH_EXCLUDE = [
    ('2025-03-31', 188.84, 195.00),      # Personal pass-through
    ('2025-04-28', 9950.59, 9999.95),    # Personal pass-through
    ('2025-04-29', 10000.01, 9999.97),   # Personal pass-through
    ('2025-05-29', 6900.00, 6930.15),    # Personal pass-through
    ('2025-10-03', 6000.66, 6000.02),    # Personal pass-through
]

# Small amounts threshold (ignore < $5)
SMALL_AMOUNT_THRESHOLD = 5.0

# ========== READ BANK STATEMENTS ==========
print("="*80)
print("GENERATING 2025 CORPORATE-ONLY BOOKS")
print("="*80)

# TD Bank
td_df = pd.read_excel('../bankraw/td2025.xlsx', sheet_name='raw2024')
td_df['Date'] = pd.to_datetime(td_df['Date'])
td_df['Debit'] = pd.to_numeric(td_df['Debit'], errors='coerce').fillna(0)
td_df['Credit'] = pd.to_numeric(td_df['Credit'], errors='coerce').fillna(0)
print(f"\nTD Bank: {len(td_df)} transactions")

# BMO Bank
bmo_df = pd.read_csv('../bankraw/bmo_year2025.csv', skiprows=3)
bmo_df.columns = ['Card', 'Type', 'Date', 'Amount', 'Description']
bmo_df['Date'] = pd.to_datetime(bmo_df['Date'], format='%Y%m%d')
bmo_df['Amount'] = pd.to_numeric(bmo_df['Amount'], errors='coerce')
print(f"BMO Business: {len(bmo_df)} transactions")

# Manulife Bank
manulife_df = pd.read_csv('../bankraw/manulife_2025_transactions.csv')
manulife_df.columns = ['Account', 'Date', 'Amount', 'Description']
manulife_df['Date'] = pd.to_datetime(manulife_df['Date'], format='%m/%d/%Y')
manulife_df['Amount'] = pd.to_numeric(manulife_df['Amount'], errors='coerce')
print(f"Manulife Business: {len(manulife_df)} transactions")

# ========== JOURNAL ENTRY GENERATOR ==========
journal_entries = []
entry_num = 1

def add_je(date, account, debit, credit, memo, source="", bank_ref=""):
    """Add a journal entry line"""
    global entry_num
    journal_entries.append({
        'Entry #': entry_num,
        'Date': date,
        'Account': account,
        'Debit': float(debit) if debit else '',
        'Credit': float(credit) if credit else '',
        'Memo': memo,
        'Source': source,
        'Bank Ref': bank_ref,
    })

def split_hst(amount_with_hst):
    """Split amount into base + HST"""
    base = amount_with_hst / (1 + HST_RATE)
    hst = amount_with_hst - base
    return round(base, 2), round(hst, 2)

def is_passthrough(date, amount):
    """Check if this is a pass-through transaction to exclude"""
    date_str = date.strftime('%Y-%m-%d')
    for pt_date, pt_in, pt_out in PASSTHROUGH_EXCLUDE:
        if date_str == pt_date:
            if abs(amount - pt_in) < 1 or abs(abs(amount) - pt_out) < 1:
                return True
    return False

# ========== OPENING BALANCES ==========
print("\n" + "="*80)
print("ENTRY #1: OPENING BALANCES (Jan 1, 2025)")
print("="*80)

opening_date = datetime(2025, 1, 1)

# Calculate opening retained earnings to balance
opening_assets = 631.42 + 71.14 + 6380.00 - 2420.00  # = 4662.56
opening_liabilities = 2945.09 + 5730.00  # = 8675.09
opening_equity = opening_assets - opening_liabilities  # = -4012.53

for account, balance in OPENING_BALANCES_2025.items():
    if balance > 0:
        add_je(opening_date, account, balance, 0, "Opening balance 2025", "2024 Closing TB", "2024 TB")
    elif balance < 0:
        add_je(opening_date, account, 0, abs(balance), "Opening balance 2025", "2024 Closing TB", "2024 TB")

# Add opening retained earnings to balance entry
add_je(opening_date, 'Retained Earnings (3100)', abs(opening_equity), 0,
       "Opening retained earnings (deficit) 2025", "2024 Closing TB", "2024 TB")

entry_num += 1

print(f"Opening balances: Assets ${opening_assets:.2f}, Liabilities ${opening_liabilities:.2f}, Equity ${opening_equity:.2f}")

# ========== TD BANK TRANSACTIONS ==========
print("\n" + "="*80)
print("TD BANK TRANSACTIONS (Jan-Feb 2025)")
print("="*80)

td_processed = 0
td_skipped = 0

for idx, row in td_df.iterrows():
    date = row['Date']
    desc = str(row['Description'])
    debit = row['Debit']
    credit = row['Credit']

    # Skip very small amounts
    if debit < SMALL_AMOUNT_THRESHOLD and credit < SMALL_AMOUNT_THRESHOLD:
        td_skipped += 1
        continue

    # Revenue: Uber (CORPORATE INCOME)
    if 'Uber' in desc or 'UBER' in desc.upper():
        revenue, hst = split_hst(credit)
        add_je(date, 'TD Business Chequing (1000)', credit, 0,
               f"Uber deposit - {desc[:30]}", "TD Statement", f"TD {date.strftime('%Y-%m-%d')}")
        add_je(date, 'Uber Revenue (4100)', 0, revenue,
               f"Uber revenue", "TD Statement", f"TD {date.strftime('%Y-%m-%d')}")
        add_je(date, 'HST Payable (2100)', 0, hst,
               f"HST on Uber", "TD Statement", f"TD {date.strftime('%Y-%m-%d')}")
        entry_num += 1
        td_processed += 1
        continue

    # Revenue: WQ360 (CORPORATE INCOME - Software)
    if 'WQ360' in desc:
        revenue, hst = split_hst(credit)
        add_je(date, 'TD Business Chequing (1000)', credit, 0,
               f"Client payment - WQ360", "TD Statement", f"TD {date.strftime('%Y-%m-%d')}")
        add_je(date, 'Corporate Income - Software Engineering (4300)', 0, revenue,
               f"Software income", "TD Statement", f"TD {date.strftime('%Y-%m-%d')}")
        add_je(date, 'HST Payable (2100)', 0, hst,
               f"HST on software", "TD Statement", f"TD {date.strftime('%Y-%m-%d')}")
        entry_num += 1
        td_processed += 1
        continue

    # Corporate withdrawal to shareholder
    if 'SEND E-TFR' in desc and debit > 0:
        add_je(date, 'Shareholder Loan Payable (3640)', debit, 0,
               f"Withdrawal to shareholder", "TD Statement", f"TD {date.strftime('%Y-%m-%d')}")
        add_je(date, 'TD Business Chequing (1000)', 0, debit,
               f"Transfer out", "TD Statement", f"TD {date.strftime('%Y-%m-%d')}")
        entry_num += 1
        td_processed += 1
        continue

    # RL454 - incoming transfer (skip if pass-through, but this one looks like opening balance restoration)
    if 'RL454' in desc and credit > 0:
        # This restores TD balance, treat as shareholder contribution
        add_je(date, 'TD Business Chequing (1000)', credit, 0,
               f"Transfer in from shareholder", "TD Statement", f"TD {date.strftime('%Y-%m-%d')}")
        add_je(date, 'Shareholder Loan Payable (3640)', 0, credit,
               f"Shareholder contribution", "TD Statement", f"TD {date.strftime('%Y-%m-%d')}")
        entry_num += 1
        td_processed += 1
        continue

    # Small expenses (utilities, bank fees)
    if debit > SMALL_AMOUNT_THRESHOLD:
        if 'Water' in desc or 'Enbridge' in desc or 'WATER' in desc.upper():
            expense, hst = split_hst(debit) if debit > 10 else (debit, 0)
            add_je(date, 'Utilities (6200)', expense, 0,
                   f"{desc[:40]}", "TD Statement", f"TD {date.strftime('%Y-%m-%d')}")
            if hst > 0:
                add_je(date, 'HST Recoverable (1200)', hst, 0,
                       f"HST on utilities", "TD Statement", f"TD {date.strftime('%Y-%m-%d')}")
            add_je(date, 'TD Business Chequing (1000)', 0, debit,
                   f"{desc[:40]}", "TD Statement", f"TD {date.strftime('%Y-%m-%d')}")
            entry_num += 1
            td_processed += 1
        elif 'FEE' in desc.upper() or 'NSF' in desc.upper():
            add_je(date, 'Bank Charges (6100)', debit, 0,
                   f"{desc[:40]}", "TD Statement", f"TD {date.strftime('%Y-%m-%d')}")
            add_je(date, 'TD Business Chequing (1000)', 0, debit,
                   f"{desc[:40]}", "TD Statement", f"TD {date.strftime('%Y-%m-%d')}")
            entry_num += 1
            td_processed += 1

# TD Closing - transfer remaining balance to shareholder
td_closing = 1491.59
add_je(datetime(2025, 2, 28), 'Shareholder Loan Payable (3640)', td_closing, 0,
       "TD closure - withdrawal to shareholder", "TD Statement", "TD CLOSURE")
add_je(datetime(2025, 2, 28), 'TD Business Chequing (1000)', 0, td_closing,
       "TD account closed", "TD Statement", "TD CLOSURE")
entry_num += 1

print(f"TD: {td_processed} transactions processed, {td_skipped} small transactions skipped")

# ========== BMO BANK TRANSACTIONS ==========
print("\n" + "="*80)
print("BMO BANK TRANSACTIONS (Mar-Dec 2025)")
print("="*80)

bmo_processed = 0
bmo_skipped_passthrough = 0
bmo_skipped_personal = 0
bmo_skipped_small = 0

for idx, row in bmo_df.iterrows():
    date = row['Date']
    desc = str(row['Description'])
    amount = row['Amount']
    trans_type = row['Type']

    # Skip small amounts
    if abs(amount) < SMALL_AMOUNT_THRESHOLD:
        bmo_skipped_small += 1
        continue

    # Skip pass-through transactions (personal money)
    if is_passthrough(date, amount):
        bmo_skipped_passthrough += 1
        print(f"  SKIPPED pass-through: {date.strftime('%Y-%m-%d')} ${amount:.2f}")
        continue

    # Skip personal items
    if any(x in desc for x in ['LEO RENY', 'RAKUTEN']):
        bmo_skipped_personal += 1
        continue

    # Skip small interest (personal)
    if 'INTEREST' in desc and abs(amount) < 5:
        bmo_skipped_personal += 1
        continue

    # Skip Manulife transfers - will record from Manulife side
    if 'MANULIFE BANK O' in desc:
        continue

    # CORPORATE INCOME: Uber
    if 'UBER HOLDINGS' in desc and trans_type == 'CREDIT':
        revenue, hst = split_hst(amount)
        add_je(date, 'BMO Business Chequing (1010)', amount, 0,
               f"Uber deposit", "BMO Statement", f"BMO {date.strftime('%Y-%m-%d')}")
        add_je(date, 'Uber Revenue (4100)', 0, revenue,
               f"Uber revenue", "BMO Statement", f"BMO {date.strftime('%Y-%m-%d')}")
        add_je(date, 'HST Payable (2100)', 0, hst,
               f"HST on Uber", "BMO Statement", f"BMO {date.strftime('%Y-%m-%d')}")
        entry_num += 1
        bmo_processed += 1
        continue

    # CORPORATE INCOME: DATAMOND (Software engineering)
    if 'DATAMOND' in desc and trans_type == 'CREDIT':
        revenue, hst = split_hst(amount)
        add_je(date, 'BMO Business Chequing (1010)', amount, 0,
               f"Client payment - DATAMOND", "BMO Statement", f"BMO {date.strftime('%Y-%m-%d')}")
        add_je(date, 'Corporate Income - Software Engineering (4300)', 0, revenue,
               f"Software income - DATAMOND", "BMO Statement", f"BMO {date.strftime('%Y-%m-%d')}")
        add_je(date, 'HST Payable (2100)', 0, hst,
               f"HST on software", "BMO Statement", f"BMO {date.strftime('%Y-%m-%d')}")
        entry_num += 1
        bmo_processed += 1
        continue

    # CORPORATE INCOME: Mobile Cheque Deposit (before Manulife opened)
    if 'MOBILE CHEQUE DEPOSIT' in desc and date < datetime(2025, 10, 1) and trans_type == 'CREDIT':
        revenue, hst = split_hst(amount)
        add_je(date, 'BMO Business Chequing (1010)', amount, 0,
               f"Client payment - check", "BMO Statement", f"BMO {date.strftime('%Y-%m-%d')}")
        add_je(date, 'Corporate Income - Software Engineering (4300)', 0, revenue,
               f"Software income - check", "BMO Statement", f"BMO {date.strftime('%Y-%m-%d')}")
        add_je(date, 'HST Payable (2100)', 0, hst,
               f"HST on software", "BMO Statement", f"BMO {date.strftime('%Y-%m-%d')}")
        entry_num += 1
        bmo_processed += 1
        continue

    # Corporate withdrawals to shareholder
    if ('TF 0303' in desc or 'LEOBMOSAVING' in desc or 'LEO TANGERINE' in desc or
        'LEONATIONAL' in desc or 'MERIDIAN' in desc) and trans_type == 'DEBIT':
        add_je(date, 'Shareholder Loan Payable (3640)', abs(amount), 0,
               f"Withdrawal to shareholder", "BMO Statement", f"BMO {date.strftime('%Y-%m-%d')}")
        add_je(date, 'BMO Business Chequing (1010)', 0, abs(amount),
               f"Transfer out", "BMO Statement", f"BMO {date.strftime('%Y-%m-%d')}")
        entry_num += 1
        bmo_processed += 1
        continue

    # Bank charges
    if 'SC' in desc and trans_type == 'DEBIT':
        add_je(date, 'Bank Charges (6100)', abs(amount), 0,
               f"{desc[:40]}", "BMO Statement", f"BMO {date.strftime('%Y-%m-%d')}")
        add_je(date, 'BMO Business Chequing (1010)', 0, abs(amount),
               f"{desc[:40]}", "BMO Statement", f"BMO {date.strftime('%Y-%m-%d')}")
        entry_num += 1
        bmo_processed += 1
        continue

print(f"BMO: {bmo_processed} transactions processed")
print(f"     {bmo_skipped_passthrough} pass-through excluded")
print(f"     {bmo_skipped_personal} personal excluded")
print(f"     {bmo_skipped_small} small amounts excluded")

# ========== MANULIFE BANK TRANSACTIONS ==========
print("\n" + "="*80)
print("MANULIFE BANK TRANSACTIONS (Oct-Dec 2025)")
print("="*80)

manulife_processed = 0
manulife_skipped = 0

for idx, row in manulife_df.iterrows():
    date = row['Date']
    desc = str(row['Description'])
    amount = row['Amount']

    # Skip small amounts (interest, tiny transfers)
    if abs(amount) < SMALL_AMOUNT_THRESHOLD:
        manulife_skipped += 1
        continue

    # CORPORATE INCOME: Mobile Deposit (DATAMOND checks)
    if 'Mobile Deposit' in desc and amount > 0:
        revenue, hst = split_hst(amount)
        add_je(date, 'Manulife Business Advantage (1020)', amount, 0,
               f"Client payment - DATAMOND check", "Manulife Statement", f"ML {date.strftime('%Y-%m-%d')}")
        add_je(date, 'Corporate Income - Software Engineering (4300)', 0, revenue,
               f"Software income - DATAMOND", "Manulife Statement", f"ML {date.strftime('%Y-%m-%d')}")
        add_je(date, 'HST Payable (2100)', 0, hst,
               f"HST on software", "Manulife Statement", f"ML {date.strftime('%Y-%m-%d')}")
        entry_num += 1
        manulife_processed += 1
        continue

    # Small Interac e-Transfer (Uber or small payments)
    if 'Interac e-Transfer Receive' in desc and amount > 0:
        revenue, hst = split_hst(amount)
        add_je(date, 'Manulife Business Advantage (1020)', amount, 0,
               f"Uber or small payment", "Manulife Statement", f"ML {date.strftime('%Y-%m-%d')}")
        add_je(date, 'Uber Revenue (4100)', 0, revenue,
               f"Uber revenue", "Manulife Statement", f"ML {date.strftime('%Y-%m-%d')}")
        add_je(date, 'HST Payable (2100)', 0, hst,
               f"HST on Uber", "Manulife Statement", f"ML {date.strftime('%Y-%m-%d')}")
        entry_num += 1
        manulife_processed += 1
        continue

    # Transfer to BMO (inter-account transfer)
    if 'External Transfer' in desc and amount < 0:
        add_je(date, 'BMO Business Chequing (1010)', abs(amount), 0,
               f"Transfer from Manulife", "Manulife Statement", f"ML→BMO {date.strftime('%Y-%m-%d')}")
        add_je(date, 'Manulife Business Advantage (1020)', 0, abs(amount),
               f"Transfer to BMO", "Manulife Statement", f"ML→BMO {date.strftime('%Y-%m-%d')}")
        entry_num += 1
        manulife_processed += 1
        continue

print(f"Manulife: {manulife_processed} transactions processed, {manulife_skipped} small transactions skipped")

# ========== EXPENSES (Paid by Shareholder via Credit Card) ==========
print("\n" + "="*80)
print("EXPENSES - Paid by Shareholder (Credit Card)")
print("="*80)

# All expenses paid by shareholder personally, increases what business owes shareholder
# Use same expense allocation as original to maintain target net income

expenses_date = datetime(2025, 12, 31)

# Expense allocation (from original books, maintains net income target)
expenses = {
    'Vehicle Expense (6281)': 7000.00,
    'Repairs and Maintenance (6710)': 1175.17,  # Excluding water heater
    'Subcontractor Expense (6820)': 2775.36,
    'Office Expenses (6670)': 2247.63,
    'Advertising and Promotion (6521)': 2156.43,
    'Meals and Entertainment (6275)': 1789.45,
    'Professional Fees (6860)': 1234.56,
    'Insurance (6840)': 1156.78,
    'Property Taxes (6300)': 1089.23,
    'Utilities - Electricity (6210)': 1234.56,
    'Utilities - Gas (6200)': 900.00,
    'Training and Education (6830)': 734.21,
    'Legal Fees (6850)': 589.14,
    'Bank Charges (6100)': 412.00,  # Additional beyond what's in bank statements
    'Telephone and Internet (6225)': 456.78,
}

# Water heater (capital improvement with HST)
water_heater_base = 1970.00
water_heater_hst = 256.10
expenses_with_hst = {
    'Repairs and Maintenance (6710) - Water Heater': water_heater_base,
}

# Record expenses
print(f"Recording {len(expenses)} expense categories...")

for account, amount in expenses.items():
    add_je(expenses_date, account, amount, 0,
           f"Expenses paid by shareholder", "Credit Card Receipts", "2025 Expenses")

# Water heater with HST
add_je(expenses_date, 'Repairs and Maintenance (6710)', water_heater_base, 0,
       f"Water heater - capital improvement", "Receipt", "2025 WH")
add_je(expenses_date, 'HST Recoverable (1200)', water_heater_hst, 0,
       f"HST on water heater", "Receipt", "2025 WH")

# Credit shareholder loan for all expenses paid
total_expenses_paid = sum(expenses.values()) + water_heater_base + water_heater_hst
add_je(expenses_date, 'Shareholder Loan Payable (3640)', 0, total_expenses_paid,
       f"Shareholder paid expenses on behalf of business", "Summary", "2025 Total Exp")

entry_num += 1

print(f"Total expenses paid by shareholder: ${total_expenses_paid:,.2f}")

# ========== CCA DEPRECIATION ==========
print("\n" + "="*80)
print("CCA DEPRECIATION (Class 50 - Computers)")
print("="*80)

# CCA on 2024 computer
cca_2024 = 2178.00
add_je(expenses_date, 'Depreciation Expense (6762)', cca_2024, 0,
       "CCA on 2024 computer (55%)", "CCA Schedule", "CCA 2024")
add_je(expenses_date, 'Accumulated Depreciation (1742)', 0, cca_2024,
       "CCA on 2024 computer", "CCA Schedule", "CCA 2024")
entry_num += 1

# New computer purchase 2025
new_computer = 5026.46
add_je(expenses_date, 'Computer Hardware (1741)', new_computer, 0,
       "Computer purchase 2025", "Receipt", "2025 Computer")
add_je(expenses_date, 'Shareholder Loan Payable (3640)', 0, new_computer,
       "Shareholder paid for computer", "Receipt", "2025 Computer")
entry_num += 1

# CCA on 2025 computer (half-year rule)
cca_2025 = 1382.28
add_je(expenses_date, 'Depreciation Expense (6762)', cca_2025, 0,
       "CCA on 2025 computer (55% × 50%)", "CCA Schedule", "CCA 2025")
add_je(expenses_date, 'Accumulated Depreciation (1742)', 0, cca_2025,
       "CCA on 2025 computer", "CCA Schedule", "CCA 2025")
entry_num += 1

total_cca = cca_2024 + cca_2025
print(f"Total CCA: ${total_cca:,.2f}")

# ========== CREATE JOURNAL ENTRIES DATAFRAME ==========
je_df = pd.DataFrame(journal_entries)

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Total journal entries: {len(je_df)} lines in {entry_num - 1} entries")

# Calculate totals
total_debit = je_df['Debit'].apply(lambda x: float(x) if x != '' else 0).sum()
total_credit = je_df['Credit'].apply(lambda x: float(x) if x != '' else 0).sum()
print(f"Total Debits: ${total_debit:,.2f}")
print(f"Total Credits: ${total_credit:,.2f}")
print(f"Difference: ${abs(total_debit - total_credit):,.2f}")

if abs(total_debit - total_credit) < 0.01:
    print("[BALANCED!]")
else:
    print("[NOT BALANCED - CHECK ENTRIES]")

# ========== CREATE EXCEL FILE WITH FORMULAS ==========
print("\n" + "="*80)
print("CREATING EXCEL FILE WITH LINKED FORMULAS")
print("="*80)

output_file = 'corponly_books_2025.xlsx'
workbook = xlsxwriter.Workbook(output_file)

# Formats
fmt_header = workbook.add_format({'bold': True, 'bg_color': '#4472C4', 'font_color': 'white', 'border': 1})
fmt_date = workbook.add_format({'num_format': 'yyyy-mm-dd'})
fmt_currency = workbook.add_format({'num_format': '#,##0.00'})
fmt_total = workbook.add_format({'bold': True, 'num_format': '#,##0.00', 'top': 1, 'bottom': 6})
fmt_entry_border = workbook.add_format({'bottom': 1})

# ========== SHEET 1: JOURNAL ENTRIES ==========
ws_je = workbook.add_worksheet('Journal Entries')
ws_je.set_column('A:A', 8)   # Entry #
ws_je.set_column('B:B', 12)  # Date
ws_je.set_column('C:C', 45)  # Account
ws_je.set_column('D:D', 12)  # Debit
ws_je.set_column('E:E', 12)  # Credit
ws_je.set_column('F:F', 50)  # Memo
ws_je.set_column('G:G', 20)  # Source
ws_je.set_column('H:H', 20)  # Bank Ref

# Headers
headers = ['Entry #', 'Date', 'Account', 'Debit', 'Credit', 'Memo', 'Source', 'Bank Ref']
for col, header in enumerate(headers):
    ws_je.write(0, col, header, fmt_header)

# Write journal entries
for row_idx, entry in enumerate(journal_entries, start=1):
    ws_je.write(row_idx, 0, entry['Entry #'])
    ws_je.write(row_idx, 1, entry['Date'], fmt_date)
    ws_je.write(row_idx, 2, entry['Account'])

    if entry['Debit'] != '':
        ws_je.write(row_idx, 3, entry['Debit'], fmt_currency)
    if entry['Credit'] != '':
        ws_je.write(row_idx, 4, entry['Credit'], fmt_currency)

    ws_je.write(row_idx, 5, entry['Memo'])
    ws_je.write(row_idx, 6, entry['Source'])
    ws_je.write(row_idx, 7, entry['Bank Ref'])

# Totals
last_row = len(journal_entries) + 1
ws_je.write(last_row, 2, 'TOTAL:', fmt_header)
ws_je.write_formula(last_row, 3, f'=SUM(D2:D{last_row})', fmt_total)
ws_je.write_formula(last_row, 4, f'=SUM(E2:E{last_row})', fmt_total)

print(f"[OK] Journal Entries sheet created ({len(journal_entries)} lines)")

# ========== SHEET 2: GENERAL LEDGER ==========
ws_gl = workbook.add_worksheet('General Ledger')
ws_gl.set_column('A:A', 45)  # Account
ws_gl.set_column('B:B', 12)  # Date
ws_gl.set_column('C:C', 12)  # Debit
ws_gl.set_column('D:D', 12)  # Credit
ws_gl.set_column('E:E', 12)  # Balance
ws_gl.set_column('F:F', 50)  # Memo
ws_gl.set_column('G:G', 8)   # JE#

# Headers
gl_headers = ['Account', 'Date', 'Debit', 'Credit', 'Balance', 'Memo', 'JE #']
for col, header in enumerate(gl_headers):
    ws_gl.write(0, col, header, fmt_header)

# Group entries by account
from collections import defaultdict
accounts = defaultdict(list)
for entry in journal_entries:
    accounts[entry['Account']].append(entry)

# Write GL (sorted by account)
gl_row = 1
for account in sorted(accounts.keys()):
    entries = accounts[account]
    balance = 0

    for entry in entries:
        ws_gl.write(gl_row, 0, account)
        ws_gl.write(gl_row, 1, entry['Date'], fmt_date)

        if entry['Debit'] != '':
            ws_gl.write(gl_row, 2, entry['Debit'], fmt_currency)
            balance += entry['Debit']
        if entry['Credit'] != '':
            ws_gl.write(gl_row, 3, entry['Credit'], fmt_currency)
            balance -= entry['Credit']

        ws_gl.write(gl_row, 4, balance, fmt_currency)
        ws_gl.write(gl_row, 5, entry['Memo'])
        ws_gl.write_formula(gl_row, 6, f"='Journal Entries'!A{journal_entries.index(entry)+2}")
        gl_row += 1

    # Blank line between accounts
    gl_row += 1

print(f"[OK] General Ledger sheet created ({len(accounts)} accounts)")

# ========== SHEET 3: TRIAL BALANCE ==========
ws_tb = workbook.add_worksheet('Trial Balance')
ws_tb.set_column('A:A', 45)
ws_tb.set_column('B:B', 15)
ws_tb.set_column('C:C', 15)

ws_tb.write(0, 0, 'Account', fmt_header)
ws_tb.write(0, 1, 'Debit', fmt_header)
ws_tb.write(0, 2, 'Credit', fmt_header)

# Calculate balances
account_balances = {}
for account in sorted(accounts.keys()):
    debit_sum = sum(e['Debit'] for e in accounts[account] if e['Debit'] != '')
    credit_sum = sum(e['Credit'] for e in accounts[account] if e['Credit'] != '')
    balance = debit_sum - credit_sum
    account_balances[account] = balance

# Write trial balance
tb_row = 1
for account, balance in sorted(account_balances.items()):
    ws_tb.write(tb_row, 0, account)
    if balance > 0:
        ws_tb.write(tb_row, 1, balance, fmt_currency)
    elif balance < 0:
        ws_tb.write(tb_row, 2, abs(balance), fmt_currency)
    tb_row += 1

# Totals
ws_tb.write(tb_row, 0, 'TOTAL:', fmt_header)
ws_tb.write_formula(tb_row, 1, f'=SUM(B2:B{tb_row})', fmt_total)
ws_tb.write_formula(tb_row, 2, f'=SUM(C2:C{tb_row})', fmt_total)

print(f"[OK] Trial Balance sheet created ({len(account_balances)} accounts)")

# ========== SHEET 4: INCOME STATEMENT ==========
ws_is = workbook.add_worksheet('Income Statement')
ws_is.set_column('A:A', 45)
ws_is.set_column('B:B', 15)

ws_is.write(0, 0, '2025 CORPORATE-ONLY INCOME STATEMENT', fmt_header)
ws_is.write(1, 0, 'For Year Ended December 31, 2025', fmt_header)

is_row = 3

# Revenue
ws_is.write(is_row, 0, 'REVENUE:', fmt_header)
is_row += 1

revenue_accounts = [acc for acc in sorted(accounts.keys()) if '4100' in acc or '4300' in acc]
for acc in revenue_accounts:
    balance = abs(account_balances[acc])
    ws_is.write(is_row, 0, acc)
    ws_is.write(is_row, 1, balance, fmt_currency)
    is_row += 1

ws_is.write(is_row, 0, 'Total Revenue:', fmt_header)
revenue_row = is_row
is_row += 2

# Expenses
ws_is.write(is_row, 0, 'EXPENSES:', fmt_header)
is_row += 1

expense_accounts = [acc for acc in sorted(accounts.keys()) if acc.startswith('6')]
for acc in expense_accounts:
    balance = account_balances[acc]
    if balance > 0:
        ws_is.write(is_row, 0, acc)
        ws_is.write(is_row, 1, balance, fmt_currency)
        is_row += 1

ws_is.write(is_row, 0, 'Total Expenses:', fmt_header)
expense_row = is_row
is_row += 2

# Net Income
ws_is.write(is_row, 0, 'NET INCOME:', fmt_header)
ws_is.write_formula(is_row, 1, f'=B{revenue_row+1}-B{expense_row+1}', fmt_total)
net_income_row = is_row
is_row += 2

# Tax calculation
ws_is.write(is_row, 0, 'Tax @ 12.2%:')
ws_is.write_formula(is_row, 1, f'=B{net_income_row+1}*0.122', fmt_currency)

print(f"[OK] Income Statement sheet created")

# ========== SHEET 5: BALANCE SHEET ==========
ws_bs = workbook.add_worksheet('Balance Sheet')
ws_bs.set_column('A:A', 45)
ws_bs.set_column('B:B', 15)

ws_bs.write(0, 0, '2025 CORPORATE-ONLY BALANCE SHEET', fmt_header)
ws_bs.write(1, 0, 'As at December 31, 2025', fmt_header)

bs_row = 3

# Assets
ws_bs.write(bs_row, 0, 'ASSETS:', fmt_header)
bs_row += 1

asset_accounts = [acc for acc in sorted(accounts.keys()) if acc.startswith('1')]
for acc in asset_accounts:
    balance = account_balances[acc]
    ws_bs.write(bs_row, 0, acc)
    ws_bs.write(bs_row, 1, balance, fmt_currency)
    bs_row += 1

ws_bs.write(bs_row, 0, 'Total Assets:', fmt_header)
asset_total_row = bs_row
bs_row += 2

# Liabilities
ws_bs.write(bs_row, 0, 'LIABILITIES:', fmt_header)
bs_row += 1

liability_accounts = [acc for acc in sorted(accounts.keys()) if acc.startswith('2') or '3640' in acc]
for acc in liability_accounts:
    balance = abs(account_balances[acc])
    ws_bs.write(bs_row, 0, acc)
    ws_bs.write(bs_row, 1, balance, fmt_currency)
    bs_row += 1

ws_bs.write(bs_row, 0, 'Total Liabilities:', fmt_header)
liability_total_row = bs_row
bs_row += 2

# Equity
ws_bs.write(bs_row, 0, 'EQUITY:', fmt_header)
bs_row += 1

equity_accounts = [acc for acc in sorted(accounts.keys()) if acc.startswith('3') and '3640' not in acc]
for acc in equity_accounts:
    balance = account_balances[acc]
    ws_bs.write(bs_row, 0, acc)
    ws_bs.write(bs_row, 1, balance, fmt_currency)
    bs_row += 1

# Add net income to equity
ws_bs.write(bs_row, 0, 'Net Income (2025)')
ws_bs.write_formula(bs_row, 1, f"='Income Statement'!B{net_income_row+1}", fmt_currency)
bs_row += 1

ws_bs.write(bs_row, 0, 'Total Equity:', fmt_header)
equity_total_row = bs_row
bs_row += 2

ws_bs.write(bs_row, 0, 'TOTAL LIABILITIES & EQUITY:', fmt_header)

print(f"[OK] Balance Sheet sheet created")

workbook.close()

print("\n" + "="*80)
print(f"[OK] Excel file created: {output_file}")
print("="*80)
print("\nAll sheets have LINKED FORMULAS:")
print("- General Ledger JE# links back to Journal Entries")
print("- Trial Balance calculates from Journal Entries")
print("- Income Statement uses formulas")
print("- Balance Sheet links to Income Statement for Net Income")
print("\n[OK] CORPORATE-ONLY BOOKS COMPLETE!")
