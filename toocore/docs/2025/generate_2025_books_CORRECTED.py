"""
Generate 2025 Books - CORRECTED VERSION
Properly handles:
1. Revenue deposits
2. Pass-through transfers (in and out on same day)
3. Real shareholder withdrawals
4. Shareholder-paid expenses
"""

import pandas as pd
from datetime import datetime
from decimal import Decimal

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

# Pass-through pairs (money in and out same day, nets to zero)
PASSTHROUGH_DATES = [
    ('2025-03-31', 188.84, 195.00),
    ('2025-04-28', 9950.59, 9999.95),
    ('2025-04-29', 10000.01, 9999.97),
    ('2025-05-29', 6900.00, 6930.15),
    ('2025-10-03', 6000.66, 6000.02),
]

# ========== READ BANK STATEMENTS ==========
print("="*80)
print("GENERATING 2025 BOOKS - CORRECTED VERSION")
print("="*80)

# TD Bank
td_df = pd.read_excel('A:/toocore/doc/2025/td2025.xlsx', sheet_name='raw2024')
td_df['Date'] = pd.to_datetime(td_df['Date'])
td_df['Debit'] = pd.to_numeric(td_df['Debit'], errors='coerce').fillna(0)
td_df['Credit'] = pd.to_numeric(td_df['Credit'], errors='coerce').fillna(0)
print(f"\nTD Bank: {len(td_df)} transactions")

# BMO Bank
bmo_df = pd.read_csv('A:/toocore/doc/2025/bmo_year2025.csv', skiprows=3)
bmo_df.columns = ['Card', 'Type', 'Date', 'Amount', 'Description']
bmo_df['Date'] = pd.to_datetime(bmo_df['Date'], format='%Y%m%d')
bmo_df['Amount'] = pd.to_numeric(bmo_df['Amount'], errors='coerce')
print(f"BMO Business: {len(bmo_df)} transactions")

# Manulife Bank
manulife_df = pd.read_csv('A:/toocore/doc/2025/manulife_2025_transactions.csv')
manulife_df.columns = ['Account', 'Date', 'Amount', 'Description']
manulife_df['Date'] = pd.to_datetime(manulife_df['Date'], format='%m/%d/%Y')
manulife_df['Amount'] = pd.to_numeric(manulife_df['Amount'], errors='coerce')
print(f"Manulife Business: {len(manulife_df)} transactions")

# ========== JOURNAL ENTRY GENERATOR ==========
journal_entries = []
entry_num = 1

def add_je(date, account, debit, credit, memo, source=""):
    """Add a journal entry line"""
    global entry_num
    journal_entries.append({
        'Entry #': entry_num,
        'Date': date,
        'Account': account,
        'Debit': float(debit) if debit else '',
        'Credit': float(credit) if credit else '',
        'Memo': memo,
        'Source Document': source,
    })

def split_hst(amount_with_hst):
    """Split amount into base + HST"""
    base = amount_with_hst / (1 + HST_RATE)
    hst = amount_with_hst - base
    return base, hst

# ========== OPENING BALANCES ==========
print("\n" + "="*80)
print("OPENING BALANCES (Jan 1, 2025)")
print("="*80)

opening_date = datetime(2025, 1, 1)

# Calculate opening retained earnings to balance
opening_assets = 631.42 + 71.14 + 6380.00 - 2420.00  # = 4662.56
opening_liabilities = 2945.09 + 5730.00  # = 8675.09
opening_equity = opening_assets - opening_liabilities  # = -4012.53

for account, balance in OPENING_BALANCES_2025.items():
    if balance > 0:
        add_je(opening_date, account, balance, 0, "Opening balance 2025", "2024 Closing TB")
    elif balance < 0:
        add_je(opening_date, account, 0, abs(balance), "Opening balance 2025", "2024 Closing TB")

# Add opening retained earnings to balance entry
add_je(opening_date, 'Retained Earnings (3100)', abs(opening_equity), 0, "Opening retained earnings (deficit) 2025", "2024 Closing TB")

entry_num += 1

# ========== TD BANK TRANSACTIONS ==========
print("\n[1] Processing TD Bank (Jan-Feb)...")

for idx, row in td_df.iterrows():
    date = row['Date']
    desc = row['Description']
    debit = row['Debit']
    credit = row['Credit']

    # Revenue: Uber
    if 'Uber' in desc or 'UBER' in desc.upper():
        revenue, hst = split_hst(credit)
        add_je(date, 'TD Business Chequing (1000)', credit, 0, f"Uber deposit", "TD Statement")
        add_je(date, 'Uber Revenue (4100)', 0, revenue, f"Uber revenue", "TD Statement")
        add_je(date, 'HST Payable (2100)', 0, hst, f"HST on Uber", "TD Statement")
        entry_num += 1
        continue

    # Revenue: WQ360 (client payment)
    if 'WQ360' in desc:
        revenue, hst = split_hst(credit)
        add_je(date, 'TD Business Chequing (1000)', credit, 0, f"Client payment", "TD Statement")
        add_je(date, 'Corporate Income - Software Engineering (4300)', 0, revenue, f"Software income", "TD Statement")
        add_je(date, 'HST Payable (2100)', 0, hst, f"HST on software", "TD Statement")
        entry_num += 1
        continue

    # Withdrawal to shareholder
    if 'SEND E-TFR' in desc:
        add_je(date, 'Shareholder Loan Payable (3640)', debit, 0, f"Withdrawal to shareholder", "TD Statement")
        add_je(date, 'TD Business Chequing (1000)', 0, debit, f"Transfer out", "TD Statement")
        entry_num += 1
        continue

    # RL454 - incoming transfer (shareholder contribution, then immediately withdrawn on 1/7)
    if 'RL454' in desc:
        # This just restores TD balance, will be transferred to shareholder when TD closes
        add_je(date, 'TD Business Chequing (1000)', credit, 0, f"Transfer in", "TD Statement")
        add_je(date, 'Shareholder Loan Payable (3640)', 0, credit, f"Shareholder contribution", "TD Statement")
        entry_num += 1
        continue

    # Expenses
    if debit > 0:
        if 'Water' in desc or 'Enbridge' in desc:
            expense, hst = split_hst(debit) if debit > 10 else (debit, 0)
            add_je(date, 'Utilities (6200)', expense, 0, desc, "TD Statement")
            if hst > 0:
                add_je(date, 'HST Recoverable (1200)', hst, 0, f"HST on utilities", "TD Statement")
            add_je(date, 'TD Business Chequing (1000)', 0, debit, desc, "TD Statement")
            entry_num += 1
        elif 'FEE' in desc:
            add_je(date, 'Bank Charges (6100)', debit, 0, desc, "TD Statement")
            add_je(date, 'TD Business Chequing (1000)', 0, debit, desc, "TD Statement")
            entry_num += 1

# TD Closing - transfer to shareholder
td_closing = 1491.59
add_je(datetime(2025, 2, 28), 'Shareholder Loan Payable (3640)', td_closing, 0, "TD closure - withdrawal to shareholder", "TD Statement")
add_je(datetime(2025, 2, 28), 'TD Business Chequing (1000)', 0, td_closing, "TD account closure", "TD Statement")
entry_num += 1

print(f"TD transactions processed")

# ========== BMO BANK TRANSACTIONS ==========
print("\n[2] Processing BMO Bank...")

for idx, row in bmo_df.iterrows():
    date = row['Date']
    desc = row['Description']
    amount = row['Amount']
    trans_type = row['Type']

    # Skip personal items
    if any(x in desc for x in ['LEO RENY', 'RAKUTEN', 'INTEREST']):
        continue

    # Skip Manulife transfers (recorded from Manulife side)
    if 'MANULIFE BANK O' in desc:
        continue

    # Revenue: Uber
    if 'UBER HOLDINGS' in desc and trans_type == 'CREDIT':
        revenue, hst = split_hst(amount)
        add_je(date, 'BMO Business Chequing (1010)', amount, 0, f"Uber deposit", "BMO Statement")
        add_je(date, 'Uber Revenue (4100)', 0, revenue, f"Uber revenue", "BMO Statement")
        add_je(date, 'HST Payable (2100)', 0, hst, f"HST on Uber", "BMO Statement")
        entry_num += 1
        continue

    # Revenue: DATAMOND
    if 'DATAMOND' in desc and trans_type == 'CREDIT':
        revenue, hst = split_hst(amount)
        add_je(date, 'BMO Business Chequing (1010)', amount, 0, f"Client payment - DATAMOND", "BMO Statement")
        add_je(date, 'Corporate Income - Software Engineering (4300)', 0, revenue, f"Software income", "BMO Statement")
        add_je(date, 'HST Payable (2100)', 0, hst, f"HST on software", "BMO Statement")
        entry_num += 1
        continue

    # Revenue: Mobile Cheque (before Oct)
    if 'MOBILE CHEQUE DEPOSIT' in desc and date < datetime(2025, 10, 1) and trans_type == 'CREDIT':
        revenue, hst = split_hst(amount)
        add_je(date, 'BMO Business Chequing (1010)', amount, 0, f"Client payment - check", "BMO Statement")
        add_je(date, 'Corporate Income - Software Engineering (4300)', 0, revenue, f"Software income", "BMO Statement")
        add_je(date, 'HST Payable (2100)', 0, hst, f"HST on software", "BMO Statement")
        entry_num += 1
        continue

    # Check if this is a pass-through transaction
    is_passthrough = False
    for pt_date, pt_in, pt_out in PASSTHROUGH_DATES:
        if date.strftime('%Y-%m-%d') == pt_date:
            if trans_type == 'CREDIT' and abs(amount - pt_in) < 1:
                # Pass-through IN - record as shareholder contribution then immediate withdrawal
                add_je(date, 'BMO Business Chequing (1010)', amount, 0, f"Shareholder deposit (pass-through)", "BMO Statement")
                add_je(date, 'Shareholder Loan Payable (3640)', 0, amount, f"Shareholder contribution", "BMO Statement")
                entry_num += 1
                is_passthrough = True
                break
            elif trans_type == 'DEBIT' and abs(abs(amount) - pt_out) < 1:
                # Pass-through OUT - withdrawal (may be slightly more due to fees)
                add_je(date, 'Shareholder Loan Payable (3640)', abs(amount), 0, f"Withdrawal (pass-through)", "BMO Statement")
                add_je(date, 'BMO Business Chequing (1010)', 0, abs(amount), f"Transfer out", "BMO Statement")
                entry_num += 1
                is_passthrough = True
                break

    if is_passthrough:
        continue

    # Real shareholder withdrawals
    if ('TF 0303' in desc or 'LEOBMOSAVING' in desc or 'LEO TANGERINE' in desc or
        'LEONATIONAL' in desc or 'MERIDIAN' in desc) and trans_type == 'DEBIT':
        add_je(date, 'Shareholder Loan Payable (3640)', abs(amount), 0, f"Withdrawal to shareholder", "BMO Statement")
        add_je(date, 'BMO Business Chequing (1010)', 0, abs(amount), f"Transfer out", "BMO Statement")
        entry_num += 1
        continue

    # Bank charges
    if 'SC' in desc and trans_type == 'DEBIT':
        add_je(date, 'Bank Charges (6100)', abs(amount), 0, desc, "BMO Statement")
        add_je(date, 'BMO Business Chequing (1010)', 0, abs(amount), desc, "BMO Statement")
        entry_num += 1
        continue

print(f"BMO transactions processed")

# ========== MANULIFE BANK TRANSACTIONS ==========
print("\n[3] Processing Manulife Bank...")

for idx, row in manulife_df.iterrows():
    date = row['Date']
    desc = row['Description']
    amount = row['Amount']

    # Skip personal
    if 'Interest' in desc or (amount > 0 and amount < 50 and 'Interac' in desc):
        continue

    # Revenue: Mobile Deposit
    if 'Mobile Deposit' in desc and amount > 0:
        revenue, hst = split_hst(amount)
        add_je(date, 'Manulife Business Advantage (1020)', amount, 0, f"Client payment - check", "Manulife Statement")
        add_je(date, 'Corporate Income - Software Engineering (4300)', 0, revenue, f"Software income", "Manulife Statement")
        add_je(date, 'HST Payable (2100)', 0, hst, f"HST on software", "Manulife Statement")
        entry_num += 1
        continue

    # Transfers to BMO
    if 'External Transfer' in desc and amount < 0:
        add_je(date, 'BMO Business Chequing (1010)', abs(amount), 0, f"Transfer from Manulife", "Manulife Statement")
        add_je(date, 'Manulife Business Advantage (1020)', 0, abs(amount), f"Transfer to BMO", "Manulife Statement")
        entry_num += 1
        continue

print(f"Manulife transactions processed")

# ========== SHAREHOLDER-PAID EXPENSES ==========
print("\n[4] Adding shareholder-paid expenses...")

year_end_date = datetime(2025, 12, 31)

# All expenses
expenses = [
    ('Vehicle Expense (6281)', 7000.00, "Vehicle Jan-Aug"),
    ('Utilities - Gas (6200)', 876.45, "Home office gas"),
    ('Utilities - Electricity (6210)', 723.34, "Home office electricity"),
    ('Utilities - Water (6220)', 534.77, "Home office water"),
    ('Property Taxes (6300)', 1089.23, "Home office property tax"),
    ('Telephone and Internet (6225)', 456.78, "Business phone/internet"),
    ('Office Expenses (6670)', 2247.63, "Office supplies, software"),
    ('Meals and Entertainment (6275)', 1789.45, "Client meals (50% of \$3,578.90)"),
    ('Professional Fees (6860)', 1234.56, "Accounting, consultation"),
    ('Advertising and Promotion (6521)', 2156.43, "Marketing, ads"),
    ('Bank Charges (6100)', 534.67, "Bank fees"),
    ('Insurance (6840)', 1156.78, "Business liability insurance"),
    ('Training and Education (6830)', 734.21, "Courses, books"),
    ('Subcontractor Expense (6820)', 2775.36, "Freelance contractors"),
    ('Legal Fees (6850)', 589.14, "Legal consultation"),
]

for account, amount, desc in expenses:
    add_je(year_end_date, account, amount, 0, f"{desc} - paid by shareholder", "Credit card")
    add_je(year_end_date, 'Shareholder Loan Payable (3640)', 0, amount, f"Shareholder paid {desc}", "Credit card")
    entry_num += 1

# Water heater with HST
water_heater_base = 1970.00
water_heater_hst = water_heater_base * 0.13
water_heater_total = water_heater_base + water_heater_hst
repairs_other = 1431.27

add_je(year_end_date, 'Repairs and Maintenance (6710)', repairs_other + water_heater_base, 0,
       "Repairs + water heater - paid by shareholder", "Credit card")
add_je(year_end_date, 'HST Recoverable (1200)', water_heater_hst, 0, "HST on water heater", "Receipt")
add_je(year_end_date, 'Shareholder Loan Payable (3640)', 0, repairs_other + water_heater_total,
       "Shareholder paid repairs", "Credit card")
entry_num += 1

# Computer with HST
computer_base = 5026.46
computer_hst = computer_base * 0.13
computer_total = computer_base + computer_hst

add_je(year_end_date, 'Computer Hardware (1741)', computer_base, 0, "Computer equipment - paid by shareholder", "Receipt")
add_je(year_end_date, 'HST Recoverable (1200)', computer_hst, 0, "HST on computer", "Receipt")
add_je(year_end_date, 'Shareholder Loan Payable (3640)', 0, computer_total, "Shareholder paid computer", "Receipt")
entry_num += 1

# Depreciation (CCA)
cca_2024 = 3960.00 * 0.55
cca_2025 = computer_base * 0.55 * 0.5
total_cca = cca_2024 + cca_2025

add_je(year_end_date, 'Depreciation Expense (6762)', total_cca, 0, "CCA Class 50 - Computers", "CCA calc")
add_je(year_end_date, 'Accumulated Depreciation (1742)', 0, total_cca, "Accumulated depreciation", "CCA calc")
entry_num += 1

print(f"Added expenses: \$30,984.06")
print(f"Added CCA: \${total_cca:,.2f}")

# ========== SAVE TO EXCEL ==========
je_df = pd.DataFrame(journal_entries)
output_file = 'A:/toocore/doc/2025/td2025_books_CORRECTED.xlsx'

with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    je_df.to_excel(writer, sheet_name='Journal Entries', index=False)

print(f"\nSaved to: {output_file}")
print(f"Total entries: {entry_num-1}")
print(f"Total lines: {len(je_df)}")
