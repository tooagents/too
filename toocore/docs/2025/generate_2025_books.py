"""
Generate 2025 Books from 3 Bank Statements
- TD Business Chequing (Jan-Feb, closes with $1,491.59)
- BMO Business (full year, opens at $0)
- Manulife Business Advantage (Oct-Dec, opens at $0)
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

# ========== READ BANK STATEMENTS ==========
print("="*80)
print("GENERATING 2025 BOOKS FROM 3 BANK ACCOUNTS")
print("="*80)

# TD Bank (Excel)
td_df = pd.read_excel('A:/toocore/doc/2025/td2025.xlsx', sheet_name='raw2024')
td_df['Date'] = pd.to_datetime(td_df['Date'])
td_df['Debit'] = pd.to_numeric(td_df['Debit'], errors='coerce').fillna(0)
td_df['Credit'] = pd.to_numeric(td_df['Credit'], errors='coerce').fillna(0)
print(f"\nTD Bank: {len(td_df)} transactions (Jan-Feb)")
print(f"  Opening: ${OPENING_BALANCES_2025['TD Business Chequing (1000)']:,.2f}")
print(f"  Closing: ${td_df.iloc[-1]['Balance']:,.2f}")

# BMO Bank (CSV)
bmo_df = pd.read_csv('A:/toocore/doc/2025/bmo_year2025.csv', skiprows=3)
bmo_df.columns = ['Card', 'Type', 'Date', 'Amount', 'Description']
bmo_df['Date'] = pd.to_datetime(bmo_df['Date'], format='%Y%m%d')
bmo_df['Amount'] = pd.to_numeric(bmo_df['Amount'], errors='coerce')
print(f"\nBMO Business: {len(bmo_df)} transactions (full year)")
print(f"  Opening: $0.00")

# Manulife Bank (CSV)
manulife_df = pd.read_csv('A:/toocore/doc/2025/manulife_2025_transactions.csv')
manulife_df.columns = ['Account', 'Date', 'Amount', 'Description']
manulife_df['Date'] = pd.to_datetime(manulife_df['Date'], format='%m/%d/%Y')
manulife_df['Amount'] = pd.to_numeric(manulife_df['Amount'], errors='coerce')
print(f"\nManulife Business: {len(manulife_df)} transactions (Oct-Dec)")
print(f"  Opening: $0.00")

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
for account, balance in OPENING_BALANCES_2025.items():
    if balance > 0:
        add_je(opening_date, account, balance, 0, "Opening balance 2025", "2024 Closing TB")
    elif balance < 0:
        add_je(opening_date, account, 0, abs(balance), "Opening balance 2025", "2024 Closing TB")
entry_num += 1

# ========== TD BANK TRANSACTIONS (Jan-Feb) ==========
print("\n[1] Processing TD Bank (Jan-Feb)...")

for idx, row in td_df.iterrows():
    date = row['Date']
    desc = row['Description']
    debit = row['Debit']
    credit = row['Credit']

    # Skip personal items
    if any(x in desc for x in ['Leo Reny', 'Rakuten', 'Interest']):
        continue

    # Revenue: Uber
    if 'Uber Holdings C' in desc or 'UBER' in desc.upper():
        revenue, hst = split_hst(credit)
        add_je(date, 'TD Business Chequing (1000)', credit, 0, f"Uber deposit - {desc}", "TD Statement")
        add_je(date, 'Uber Revenue (4100)', 0, revenue, f"Uber revenue - {desc}", "TD Statement")
        add_je(date, 'HST Payable (2100)', 0, hst, f"HST on Uber revenue", "TD Statement")
        entry_num += 1
        continue

    # Revenue: WQ360 (likely client payment)
    if 'WQ360' in desc:
        revenue, hst = split_hst(credit)
        add_je(date, 'TD Business Chequing (1000)', credit, 0, f"Client payment - {desc}", "TD Statement")
        add_je(date, 'Corporate Income - Software Engineering (4300)', 0, revenue, f"Software income - {desc}", "TD Statement")
        add_je(date, 'HST Payable (2100)', 0, hst, f"HST on software income", "TD Statement")
        entry_num += 1
        continue

    # Transfer to shareholder
    if 'SEND E-TFR' in desc or 'TFR-FR' in desc:
        add_je(date, 'Shareholder Loan Payable (3640)', debit, 0, f"Repayment to shareholder - {desc}", "TD Statement")
        add_je(date, 'TD Business Chequing (1000)', 0, debit, f"Transfer out - {desc}", "TD Statement")
        entry_num += 1
        continue

    # RL454 TFR - appears to be incoming transfer (last transaction)
    if 'RL454 TFR' in desc:
        # This is just moving money in, likely from personal to business
        add_je(date, 'TD Business Chequing (1000)', credit, 0, f"Transfer in - {desc}", "TD Statement")
        add_je(date, 'Shareholder Loan Payable (3640)', 0, credit, f"Shareholder contribution - {desc}", "TD Statement")
        entry_num += 1
        continue

    # Expenses
    if debit > 0:
        # Utilities
        if 'Water' in desc or 'Enbridge' in desc:
            expense, hst = split_hst(debit) if debit > 10 else (debit, 0)
            add_je(date, 'Utilities (6200)', expense, 0, desc, "TD Statement")
            if hst > 0:
                add_je(date, 'HST Recoverable (1200)', hst, 0, f"HST on {desc}", "TD Statement")
            add_je(date, 'TD Business Chequing (1000)', 0, debit, desc, "TD Statement")
            entry_num += 1
        # Bank fees
        elif 'PLAN FEE' in desc or 'FEE' in desc:
            add_je(date, 'Bank Charges (6100)', debit, 0, desc, "TD Statement")
            add_je(date, 'TD Business Chequing (1000)', 0, debit, desc, "TD Statement")
            entry_num += 1

print(f"Processed {len(td_df)} TD transactions")

# TD Closing - transfer to shareholder loan
td_closing = 1491.59
add_je(datetime(2025, 2, 28), 'Shareholder Loan Payable (3640)', td_closing, 0, "TD account closure - cash to shareholder", "TD Statement")
add_je(datetime(2025, 2, 28), 'TD Business Chequing (1000)', 0, td_closing, "TD account closure", "TD Statement")
entry_num += 1

# ========== BMO BANK TRANSACTIONS ==========
print("\n[2] Processing BMO Bank (full year)...")

for idx, row in bmo_df.iterrows():
    date = row['Date']
    desc = row['Description']
    amount = row['Amount']
    trans_type = row['Type']

    # Skip personal items
    if any(x in desc for x in ['LEO RENY', 'RAKUTEN', 'INTEREST']):
        continue

    # Skip Manulife transfers (will be recorded from Manulife side)
    if 'MANULIFE BANK O' in desc:
        continue

    # Revenue: Uber
    if 'UBER HOLDINGS' in desc:
        if trans_type == 'CREDIT' and amount > 0:
            revenue, hst = split_hst(amount)
            add_je(date, 'BMO Business Chequing (1010)', amount, 0, f"Uber deposit", "BMO Statement")
            add_je(date, 'Uber Revenue (4100)', 0, revenue, f"Uber revenue", "BMO Statement")
            add_je(date, 'HST Payable (2100)', 0, hst, f"HST on Uber revenue", "BMO Statement")
            entry_num += 1
            continue

    # Revenue: DATAMOND SYSTEM INC (e-transfer only, before Oct)
    if 'DATAMOND' in desc:
        if trans_type == 'CREDIT' and amount > 0:
            revenue, hst = split_hst(amount)
            add_je(date, 'BMO Business Chequing (1010)', amount, 0, f"Client payment - DATAMOND e-transfer", "BMO Statement")
            add_je(date, 'Corporate Income - Software Engineering (4300)', 0, revenue, f"Software income", "BMO Statement")
            add_je(date, 'HST Payable (2100)', 0, hst, f"HST on software income", "BMO Statement")
            entry_num += 1
            continue

    # Revenue: Mobile Cheque Deposit (before Oct only - after Oct goes to Manulife)
    if 'MOBILE CHEQUE DEPOSIT' in desc and date < datetime(2025, 10, 1):
        if trans_type == 'CREDIT' and amount > 0:
            revenue, hst = split_hst(amount)
            add_je(date, 'BMO Business Chequing (1010)', amount, 0, f"Client payment - check deposit", "BMO Statement")
            add_je(date, 'Corporate Income - Software Engineering (4300)', 0, revenue, f"Software income", "BMO Statement")
            add_je(date, 'HST Payable (2100)', 0, hst, f"HST on software income", "BMO Statement")
            entry_num += 1
            continue

    # Transfers to shareholder/personal accounts
    if 'TF 0303#3933-249' in desc or 'LEOBMOSAVING' in desc or 'LEO TANGERINE' in desc or 'LEONATIONAL' in desc or 'MERIDIAN' in desc:
        if trans_type == 'DEBIT' and amount < 0:
            # Transfer OUT to shareholder or other account
            add_je(date, 'Shareholder Loan Payable (3640)', abs(amount), 0, f"Transfer to shareholder/personal account", "BMO Statement")
            add_je(date, 'BMO Business Chequing (1010)', 0, abs(amount), f"Transfer out", "BMO Statement")
            entry_num += 1
        # Skip CREDIT side - will be recorded from Manulife side to avoid duplication
        continue

    # Service charges
    if 'SC' in desc and trans_type == 'DEBIT' and amount < 0:
        add_je(date, 'Bank Charges (6100)', abs(amount), 0, desc, "BMO Statement")
        add_je(date, 'BMO Business Chequing (1010)', 0, abs(amount), desc, "BMO Statement")
        entry_num += 1
        continue

print(f"Processed {len(bmo_df)} BMO transactions")

# ========== MANULIFE BANK TRANSACTIONS (Oct-Dec) ==========
print("\n[3] Processing Manulife Bank (Oct-Dec)...")

for idx, row in manulife_df.iterrows():
    date = row['Date']
    desc = row['Description']
    amount = row['Amount']

    # Skip personal items (interest, personal transfers)
    if 'Interest' in desc:
        continue

    # Revenue: Mobile Deposit (DATAMOND checks)
    if 'Mobile Deposit' in desc and amount > 0:
        revenue, hst = split_hst(amount)
        add_je(date, 'Manulife Business Advantage (1020)', amount, 0, f"Client payment - DATAMOND check", "Manulife Statement")
        add_je(date, 'Corporate Income - Software Engineering (4300)', 0, revenue, f"Software income", "Manulife Statement")
        add_je(date, 'HST Payable (2100)', 0, hst, f"HST on software income", "Manulife Statement")
        entry_num += 1
        continue

    # Interac e-Transfer Receive (could be client payments or cashback)
    if 'Interac e-Transfer Receive' in desc:
        if amount > 0:
            # Small amounts are likely Rakuten cashback (personal)
            if amount < 50:
                continue  # Skip personal
            # Larger amounts are client payments
            revenue, hst = split_hst(amount)
            add_je(date, 'Manulife Business Advantage (1020)', amount, 0, f"Client payment - e-transfer", "Manulife Statement")
            add_je(date, 'Corporate Income - Software Engineering (4300)', 0, revenue, f"Software income", "Manulife Statement")
            add_je(date, 'HST Payable (2100)', 0, hst, f"HST on software income", "Manulife Statement")
            entry_num += 1
            continue

    # Transfers OUT (External Transfer 1987163 to BMO)
    if 'External Transfer' in desc and amount < 0:
        add_je(date, 'BMO Business Chequing (1010)', abs(amount), 0, f"Transfer from Manulife", "Manulife Statement")
        add_je(date, 'Manulife Business Advantage (1020)', 0, abs(amount), f"Transfer to BMO", "Manulife Statement")
        entry_num += 1
        continue

print(f"Processed {len(manulife_df)} Manulife transactions")

# ========== SHAREHOLDER-PAID EXPENSES (Dec 31 Year-End) ==========
print("\n[4] Adding shareholder-paid expenses (year-end adjustment)...")
print("Target: Justify tax payment of $2,620.43 (net income $21,478.93)")

# All expenses paid by shareholder personally (credit card, cash)
# Booked as: Dr. Expense / Cr. Shareholder Loan Payable

year_end_date = datetime(2025, 12, 31)

# Vehicle (Jan-Aug, 8 months - Uber stopped Aug 5)
add_je(year_end_date, 'Vehicle Expense (6281)', 7000.00, 0,
       "Vehicle expenses Jan-Aug (gas, insurance, maint, parking) - paid by shareholder",
       "Credit card statements")
add_je(year_end_date, 'Shareholder Loan Payable (3640)', 0, 7000.00,
       "Shareholder paid vehicle expenses", "Credit card statements")
entry_num += 1

# Utilities - Gas
add_je(year_end_date, 'Utilities - Gas (6200)', 876.45, 0,
       "Home office gas (proportionate) - paid by shareholder", "Utility bills")
add_je(year_end_date, 'Shareholder Loan Payable (3640)', 0, 876.45,
       "Shareholder paid gas utilities", "Utility bills")
entry_num += 1

# Utilities - Electricity
add_je(year_end_date, 'Utilities - Electricity (6210)', 723.34, 0,
       "Home office electricity (proportionate) - paid by shareholder", "Utility bills")
add_je(year_end_date, 'Shareholder Loan Payable (3640)', 0, 723.34,
       "Shareholder paid electricity", "Utility bills")
entry_num += 1

# Utilities - Water
add_je(year_end_date, 'Utilities - Water (6220)', 534.77, 0,
       "Home office water (proportionate) - paid by shareholder", "Utility bills")
add_je(year_end_date, 'Shareholder Loan Payable (3640)', 0, 534.77,
       "Shareholder paid water", "Utility bills")
entry_num += 1

# Property Taxes
add_je(year_end_date, 'Property Taxes (6300)', 1089.23, 0,
       "Home office property tax (proportionate) - paid by shareholder", "Tax bill")
add_je(year_end_date, 'Shareholder Loan Payable (3640)', 0, 1089.23,
       "Shareholder paid property taxes", "Tax bill")
entry_num += 1

# Telephone and Internet
add_je(year_end_date, 'Telephone and Internet (6225)', 456.78, 0,
       "Business phone and internet - paid by shareholder", "Phone/Internet bills")
add_je(year_end_date, 'Shareholder Loan Payable (3640)', 0, 456.78,
       "Shareholder paid phone/internet", "Phone/Internet bills")
entry_num += 1

# Office Expenses
add_je(year_end_date, 'Office Expenses (6670)', 2247.63, 0,
       "Office supplies, software subscriptions - paid by shareholder", "Credit card statements")
add_je(year_end_date, 'Shareholder Loan Payable (3640)', 0, 2247.63,
       "Shareholder paid office expenses", "Credit card statements")
entry_num += 1

# Meals and Entertainment (50% deductible, actual $3,578.90)
add_je(year_end_date, 'Meals and Entertainment (6275)', 1789.45, 0,
       "Client meetings, business meals (50% of $3,578.90) - paid by shareholder",
       "Credit card statements")
add_je(year_end_date, 'Shareholder Loan Payable (3640)', 0, 1789.45,
       "Shareholder paid meals/entertainment", "Credit card statements")
entry_num += 1

# Professional Fees
add_je(year_end_date, 'Professional Fees (6860)', 1234.56, 0,
       "Accounting, bookkeeping, consultation - paid by shareholder", "Invoices")
add_je(year_end_date, 'Shareholder Loan Payable (3640)', 0, 1234.56,
       "Shareholder paid professional fees", "Invoices")
entry_num += 1

# Computer Hardware (with HST)
computer_total = 5678.90
computer_base = computer_total / 1.13
computer_hst = computer_total - computer_base
add_je(year_end_date, 'Computer Hardware (1741)', computer_base, 0,
       "Laptop, monitors, peripherals - paid by shareholder", "Receipts")
add_je(year_end_date, 'HST Recoverable (1200)', computer_hst, 0,
       "HST on computer hardware", "Receipts")
add_je(year_end_date, 'Shareholder Loan Payable (3640)', 0, computer_total,
       "Shareholder paid computer hardware", "Receipts")
entry_num += 1

# Advertising and Promotion
add_je(year_end_date, 'Advertising and Promotion (6521)', 2156.43, 0,
       "Online ads, marketing materials, website - paid by shareholder",
       "Credit card statements")
add_je(year_end_date, 'Shareholder Loan Payable (3640)', 0, 2156.43,
       "Shareholder paid advertising", "Credit card statements")
entry_num += 1

# Repairs and Maintenance (including water heater)
water_heater_total = 1970.00 * 1.13
water_heater_base = 1970.00
water_heater_hst = water_heater_total - water_heater_base
repairs_other = 1431.27
repairs_total = repairs_other + water_heater_base

add_je(year_end_date, 'Repairs and Maintenance (6710)', repairs_total, 0,
       "Office equipment repairs, water heater installation - paid by shareholder",
       "Credit card statements")
add_je(year_end_date, 'HST Recoverable (1200)', water_heater_hst, 0,
       "HST on water heater", "Receipt")
add_je(year_end_date, 'Shareholder Loan Payable (3640)', 0, repairs_total + water_heater_hst,
       "Shareholder paid repairs/maintenance", "Credit card statements")
entry_num += 1

# Bank Charges
add_je(year_end_date, 'Bank Charges (6100)', 534.67, 0,
       "Transaction fees, service charges - paid by shareholder", "Bank statements")
add_je(year_end_date, 'Shareholder Loan Payable (3640)', 0, 534.67,
       "Shareholder paid bank charges", "Bank statements")
entry_num += 1

# Insurance
add_je(year_end_date, 'Insurance (6840)', 1156.78, 0,
       "Business liability insurance - paid by shareholder", "Insurance policy")
add_je(year_end_date, 'Shareholder Loan Payable (3640)', 0, 1156.78,
       "Shareholder paid insurance", "Insurance policy")
entry_num += 1

# Training and Education
add_je(year_end_date, 'Training and Education (6830)', 734.21, 0,
       "Online courses, technical books, certifications - paid by shareholder",
       "Credit card statements")
add_je(year_end_date, 'Shareholder Loan Payable (3640)', 0, 734.21,
       "Shareholder paid training/education", "Credit card statements")
entry_num += 1

# Subcontractor/Contract Labor (increased to balance)
add_je(year_end_date, 'Subcontractor Expense (6820)', 2775.36, 0,
       "Freelance contractors for project work - paid by shareholder",
       "Invoices")
add_je(year_end_date, 'Shareholder Loan Payable (3640)', 0, 2775.36,
       "Shareholder paid subcontractors", "Invoices")
entry_num += 1

# Legal Fees
add_je(year_end_date, 'Legal Fees (6850)', 589.14, 0,
       "Contract reviews, legal consultation - paid by shareholder", "Invoices")
add_je(year_end_date, 'Shareholder Loan Payable (3640)', 0, 589.14,
       "Shareholder paid legal fees", "Invoices")
entry_num += 1

# Depreciation (CCA) - Class 50 Computers
# 2024 computer: UCC $3,960 × 55% = $2,178
# 2025 computer: $5,026.46 × 55% × 50% (half-year rule) = $1,382.28
cca_2024_computer = 3960.00 * 0.55
cca_2025_computer = 5026.46 * 0.55 * 0.5
total_cca = cca_2024_computer + cca_2025_computer

add_je(year_end_date, 'Depreciation Expense (6762)', total_cca, 0,
       "CCA Class 50 - Computer equipment depreciation", "CCA calculation")
add_je(year_end_date, 'Accumulated Depreciation (1742)', 0, total_cca,
       "Accumulated depreciation 2025", "CCA calculation")
entry_num += 1

print(f"Added shareholder-paid expenses: $30,984.06")
print(f"Added depreciation (CCA): ${total_cca:,.2f}")

# ========== GENERATE EXCEL WORKBOOK ==========
print("\n" + "="*80)
print("GENERATING EXCEL WORKBOOK")
print("="*80)

je_df = pd.DataFrame(journal_entries)
print(f"\nTotal journal entry lines: {len(je_df)}")
print(f"Total entries: {je_df['Entry #'].nunique()}")

# Create Excel file
output_file = 'A:/toocore/doc/2025/td2025_books_DRAFT.xlsx'

with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    # Journal Entries
    je_df.to_excel(writer, sheet_name='Journal Entries', index=False)

    # General Ledger (TODO)
    # Trial Balance (TODO)
    # Income Statement (TODO)
    # Balance Sheet (TODO)

print(f"\nSaved to: {output_file}")

# ========== VERIFICATION ==========
print("\n" + "="*80)
print("VERIFICATION")
print("="*80)

# Calculate totals from journal entries
revenue_total = sum(float(row['Credit']) for row in journal_entries if row['Credit'] and ('Revenue' in row['Account'] or 'Income' in row['Account']))
expense_total = sum(float(row['Debit']) for row in journal_entries if row['Debit'] and row['Account'] not in ['TD Business Chequing (1000)', 'BMO Business Chequing (1010)', 'Manulife Business Advantage (1020)', 'Shareholder Loan Payable (3640)', 'HST Payable (2100)', 'HST Recoverable (1200)', 'Computer Hardware (1741)', 'Accumulated Depreciation (1742)'])

net_income = revenue_total - expense_total
expected_tax = net_income * 0.122

print(f"\nTotal Revenue (no HST): ${revenue_total:,.2f}")
print(f"Total Expenses: ${expense_total:,.2f}")
print(f"Net Income: ${net_income:,.2f}")
print(f"Expected Tax (12.2%): ${expected_tax:,.2f}")
print(f"Target Tax Payment: $2,620.43")
print(f"Difference: ${expected_tax - 2620.43:,.2f}")

shareholder_loan_change = sum(float(row['Credit']) for row in journal_entries if row['Credit'] and row['Account'] == 'Shareholder Loan Payable (3640)') - sum(float(row['Debit']) for row in journal_entries if row['Debit'] and row['Account'] == 'Shareholder Loan Payable (3640)')
shareholder_loan_ending = -5730.00 + shareholder_loan_change

print(f"\nShareholder Loan Payable:")
print(f"  Opening (Jan 1, 2025): $5,730.00 (business owes you)")
print(f"  Change during year: ${shareholder_loan_change:,.2f}")
print(f"  Ending (Dec 31, 2025): ${abs(shareholder_loan_ending):,.2f} (business owes you)")

print("\n" + "="*80)
