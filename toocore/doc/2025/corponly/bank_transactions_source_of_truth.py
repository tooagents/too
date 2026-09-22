"""
Bank Transactions - SOURCE OF TRUTH
Start from bank statements, classify each transaction, this becomes the source for BS/IS
"""

import pandas as pd
from datetime import datetime
import xlsxwriter

print("="*80)
print("CREATING BANK TRANSACTION SOURCE OF TRUTH")
print("="*80)

# Read all 3 bank statements
print("\nReading bank statements...")

# TD Bank
td_df = pd.read_excel('../bankraw/td2025.xlsx', sheet_name='raw2024')
td_df['Date'] = pd.to_datetime(td_df['Date'])
td_df['Debit'] = pd.to_numeric(td_df['Debit'], errors='coerce').fillna(0)
td_df['Credit'] = pd.to_numeric(td_df['Credit'], errors='coerce').fillna(0)
td_df['Bank'] = 'TD'
print(f"  TD: {len(td_df)} transactions")

# BMO Bank
bmo_df = pd.read_csv('../bankraw/bmo_year2025.csv', skiprows=3)
bmo_df.columns = ['Card', 'Type', 'Date', 'Amount', 'Description']
bmo_df['Date'] = pd.to_datetime(bmo_df['Date'], format='%Y%m%d')
bmo_df['Amount'] = pd.to_numeric(bmo_df['Amount'], errors='coerce')
bmo_df['Debit'] = bmo_df['Amount'].apply(lambda x: abs(x) if x < 0 else 0)
bmo_df['Credit'] = bmo_df['Amount'].apply(lambda x: x if x > 0 else 0)
bmo_df['Bank'] = 'BMO'
bmo_df = bmo_df.rename(columns={'Description': 'Description'})
print(f"  BMO: {len(bmo_df)} transactions")

# Manulife Bank
ml_df = pd.read_csv('../bankraw/manulife_2025_transactions.csv')
ml_df.columns = ['Account', 'Date', 'Amount', 'Description']
ml_df['Date'] = pd.to_datetime(ml_df['Date'], format='%m/%d/%Y')
ml_df['Amount'] = pd.to_numeric(ml_df['Amount'], errors='coerce')
ml_df['Debit'] = ml_df['Amount'].apply(lambda x: abs(x) if x < 0 else 0)
ml_df['Credit'] = ml_df['Amount'].apply(lambda x: x if x > 0 else 0)
ml_df['Bank'] = 'MANULIFE'
print(f"  Manulife: {len(ml_df)} transactions")

# Combine all transactions
all_transactions = []

# Process TD
for idx, row in td_df.iterrows():
    all_transactions.append({
        'Date': row['Date'],
        'Bank': 'TD',
        'Description': str(row['Description']),
        'Debit': row['Debit'],
        'Credit': row['Credit'],
        'Amount': row['Credit'] - row['Debit']
    })

# Process BMO
for idx, row in bmo_df.iterrows():
    all_transactions.append({
        'Date': row['Date'],
        'Bank': 'BMO',
        'Description': str(row['Description']),
        'Debit': row['Debit'],
        'Credit': row['Credit'],
        'Amount': row['Credit'] - row['Debit']
    })

# Process Manulife
for idx, row in ml_df.iterrows():
    all_transactions.append({
        'Date': row['Date'],
        'Bank': 'MANULIFE',
        'Description': str(row['Description']),
        'Debit': row['Debit'],
        'Credit': row['Credit'],
        'Amount': row['Credit'] - row['Debit']
    })

# Sort by date
all_transactions.sort(key=lambda x: x['Date'])

print(f"\nTotal transactions: {len(all_transactions)}")

# CLASSIFICATION RULES
def classify_transaction(row):
    """Classify each transaction based on description and amount"""
    desc = row['Description'].upper()
    amount = row['Amount']
    date = row['Date']

    # IGNORE: Small amounts (< $5)
    if abs(amount) < 5.0:
        return 'IGNORE', 'Small amount < $5'

    # IGNORE: Pass-through same day pairs
    # Check if this is one of the known pass-through dates
    date_str = date.strftime('%Y-%m-%d')
    passthrough_dates = {
        '2025-03-31': [188.84, -195.00],
        '2025-04-28': [9950.59, -9999.95],
        '2025-04-29': [10000.01, -9999.97],
        '2025-05-29': [6900.00, -6930.15],
        '2025-10-03': [6000.66, -6000.02],
    }
    if date_str in passthrough_dates:
        for pt_amount in passthrough_dates[date_str]:
            if abs(amount - pt_amount) < 1:
                return 'IGNORE', 'Pass-through (same day personal)'

    # INCOME: UBER
    if 'UBER' in desc:
        return 'INCOME', 'UBER driving revenue'

    # INCOME: DATAMOND
    if 'DATAMOND' in desc:
        return 'INCOME', 'DATAMOND software revenue'

    # INCOME: WQ360 (client)
    if 'WQ360' in desc:
        return 'INCOME', 'Client software revenue'

    # INCOME: Mobile deposit (likely DATAMOND checks)
    if 'MOBILE CHEQUE DEPOSIT' in desc or 'MOBILE DEPOSIT' in desc:
        return 'INCOME', 'DATAMOND check deposit'

    # INCOME: Small Interac receive (likely Uber)
    if 'INTERAC E-TRANSFER RECEIVE' in desc and amount > 0:
        return 'INCOME', 'Uber or small payment'

    # IGNORE: Personal items
    if any(x in desc for x in ['LEO RENY', 'RAKUTEN', 'INTEREST']):
        return 'IGNORE', 'Personal transaction'

    # IGNORE: Transfer between corporate accounts
    if 'MANULIFE BANK O' in desc:
        return 'IGNORE', 'Inter-account transfer (recorded from ML side)'

    if 'EXTERNAL TRANSFER' in desc and amount < 0:
        return 'TRANSFER', 'Transfer from Manulife to BMO'

    # SHAREHOLDER WITHDRAWAL: E-transfers out
    if amount < 0 and any(x in desc for x in [
        'SEND E-TFR', 'INTERAC ETRNSFR SENT',
        'TF 0303', 'LEOBMOSAVING', 'LEO TANGERINE',
        'LEONATIONAL', 'MERIDIAN'
    ]):
        return 'WITHDRAWAL', 'Shareholder withdrawal (reduces loan)'

    # SHAREHOLDER CONTRIBUTION: Incoming transfers (not revenue)
    if amount > 0 and 'RL454' in desc:
        return 'CONTRIBUTION', 'Shareholder contribution (increases loan)'

    # EXPENSE: Bank fees
    if 'FEE' in desc or 'SC' in desc or 'NSF' in desc:
        return 'EXPENSE', 'Bank charges'

    # EXPENSE: Utilities
    if any(x in desc for x in ['WATER', 'ENBRIDGE', 'GAS']):
        return 'EXPENSE', 'Utilities'

    # DEFAULT: Need manual review
    return 'REVIEW', 'Needs manual classification'

# Classify all transactions
print("\nClassifying transactions...")
for txn in all_transactions:
    category, note = classify_transaction(txn)
    txn['Category'] = category
    txn['Note'] = note

# Summary by category
print("\n" + "="*80)
print("TRANSACTION SUMMARY BY CATEGORY")
print("="*80)

category_summary = {}
for txn in all_transactions:
    cat = txn['Category']
    if cat not in category_summary:
        category_summary[cat] = {'count': 0, 'total': 0}
    category_summary[cat]['count'] += 1
    category_summary[cat]['total'] += txn['Amount']

for cat in sorted(category_summary.keys()):
    count = category_summary[cat]['count']
    total = category_summary[cat]['total']
    print(f"{cat:15} {count:3} transactions  ${total:12,.2f}")

# Calculate key totals
income_total = sum(t['Amount'] for t in all_transactions if t['Category'] == 'INCOME')
withdrawal_total = abs(sum(t['Amount'] for t in all_transactions if t['Category'] == 'WITHDRAWAL'))
contribution_total = sum(t['Amount'] for t in all_transactions if t['Category'] == 'CONTRIBUTION')
expense_total = abs(sum(t['Amount'] for t in all_transactions if t['Category'] == 'EXPENSE'))

print("\n" + "="*80)
print("KEY TOTALS (from bank statements):")
print("="*80)
print(f"Total INCOME (with HST):                ${income_total:,.2f}")
print(f"Total WITHDRAWALS:                       ${withdrawal_total:,.2f}")
print(f"Total CONTRIBUTIONS (shareholder paid): ${contribution_total:,.2f}")
print(f"Total EXPENSES (from bank):             ${expense_total:,.2f}")

# Calculate shareholder loan from BANK STATEMENTS
opening_loan = 5730.00  # Business owes shareholder
print("\n" + "="*80)
print("SHAREHOLDER LOAN (from bank statements):")
print("="*80)
print(f"Opening (Jan 1): Business owes shareholder   ${opening_loan:,.2f}")
print(f"Shareholder contributions (from bank):      +${contribution_total:,.2f}")
print(f"Shareholder withdrawals (from bank):        -${withdrawal_total:,.2f}")
print(f"Net bank activity:                           ${contribution_total - withdrawal_total:,.2f}")

# Note: Expenses paid by shareholder via credit card are NOT in bank statements
# They increase what business owes shareholder but don't show in bank
print(f"\nNote: Expenses paid by shareholder via CREDIT CARD")
print(f"      (not in bank statements) will be added separately")

# Create Excel file
print("\n" + "="*80)
print("CREATING EXCEL FILE")
print("="*80)

output_file = 'bank_transactions_SOURCE.xlsx'
workbook = xlsxwriter.Workbook(output_file)

# Formats
fmt_header = workbook.add_format({'bold': True, 'bg_color': '#4472C4', 'font_color': 'white', 'border': 1})
fmt_date = workbook.add_format({'num_format': 'yyyy-mm-dd'})
fmt_currency = workbook.add_format({'num_format': '#,##0.00'})
fmt_income = workbook.add_format({'bg_color': '#C6EFCE', 'num_format': '#,##0.00'})
fmt_withdrawal = workbook.add_format({'bg_color': '#FFC7CE', 'num_format': '#,##0.00'})
fmt_ignore = workbook.add_format({'font_color': '#999999', 'num_format': '#,##0.00'})

# Sheet 1: All Transactions
ws = workbook.add_worksheet('All Transactions')
ws.set_column('A:A', 12)  # Date
ws.set_column('B:B', 10)  # Bank
ws.set_column('C:C', 60)  # Description
ws.set_column('D:D', 12)  # Debit
ws.set_column('E:E', 12)  # Credit
ws.set_column('F:F', 12)  # Amount
ws.set_column('G:G', 15)  # Category
ws.set_column('H:H', 40)  # Note

# Headers
headers = ['Date', 'Bank', 'Description', 'Debit', 'Credit', 'Amount', 'Category', 'Note']
for col, header in enumerate(headers):
    ws.write(0, col, header, fmt_header)

# Write all transactions
for row_idx, txn in enumerate(all_transactions, start=1):
    ws.write(row_idx, 0, txn['Date'], fmt_date)
    ws.write(row_idx, 1, txn['Bank'])
    ws.write(row_idx, 2, txn['Description'])

    if txn['Debit'] > 0:
        ws.write(row_idx, 3, txn['Debit'], fmt_currency)
    if txn['Credit'] > 0:
        ws.write(row_idx, 4, txn['Credit'], fmt_currency)

    # Color-code based on category
    cat = txn['Category']
    if cat == 'INCOME':
        ws.write(row_idx, 5, txn['Amount'], fmt_income)
    elif cat == 'WITHDRAWAL':
        ws.write(row_idx, 5, txn['Amount'], fmt_withdrawal)
    elif cat == 'IGNORE':
        ws.write(row_idx, 5, txn['Amount'], fmt_ignore)
    else:
        ws.write(row_idx, 5, txn['Amount'], fmt_currency)

    ws.write(row_idx, 6, cat)
    ws.write(row_idx, 7, txn['Note'])

# Sheet 2: Summary by Category
ws_summary = workbook.add_worksheet('Summary')
ws_summary.set_column('A:A', 20)
ws_summary.set_column('B:B', 12)
ws_summary.set_column('C:C', 15)

ws_summary.write(0, 0, 'Category', fmt_header)
ws_summary.write(0, 1, 'Count', fmt_header)
ws_summary.write(0, 2, 'Total Amount', fmt_header)

row = 1
for cat in sorted(category_summary.keys()):
    ws_summary.write(row, 0, cat)
    ws_summary.write(row, 1, category_summary[cat]['count'])
    ws_summary.write(row, 2, category_summary[cat]['total'], fmt_currency)
    row += 1

# Sheet 3: Key Totals
ws_totals = workbook.add_worksheet('Key Totals')
ws_totals.set_column('A:A', 40)
ws_totals.set_column('B:B', 15)

ws_totals.write(0, 0, 'INCOME (from bank statements)', fmt_header)
ws_totals.write(1, 0, 'Total INCOME (with HST):')
ws_totals.write(1, 1, income_total, fmt_currency)

ws_totals.write(3, 0, 'SHAREHOLDER LOAN (from bank)', fmt_header)
ws_totals.write(4, 0, 'Opening: Business owes shareholder')
ws_totals.write(4, 1, opening_loan, fmt_currency)
ws_totals.write(5, 0, 'Contributions from bank:')
ws_totals.write(5, 1, contribution_total, fmt_currency)
ws_totals.write(6, 0, 'Withdrawals from bank:')
ws_totals.write(6, 1, -withdrawal_total, fmt_currency)
ws_totals.write(7, 0, 'Net from bank activity:')
ws_totals.write(7, 1, contribution_total - withdrawal_total, fmt_currency)

ws_totals.write(9, 0, 'Note: Expenses paid by shareholder via credit card')
ws_totals.write(10, 0, '      (not in bank) need to be added separately')

workbook.close()

print(f"[OK] Excel created: {output_file}")
print("\nThis is now the SOURCE OF TRUTH for:")
print("  - Income Statement (income from bank)")
print("  - Balance Sheet (shareholder loan from bank withdrawals)")
print("  - All other accounting flows from this foundation")
