"""
Generate Complete 2025 Accounting Package
- General Ledger
- Trial Balance
- Income Statement
- Balance Sheet
- GIFI Summary (for T2)
"""

import pandas as pd
from datetime import datetime
from collections import defaultdict

print("="*80)
print("GENERATING 2025 COMPLETE ACCOUNTING PACKAGE")
print("="*80)

# Read journal entries
je_df = pd.read_excel('A:/toocore/doc/2025/td2025_books_DRAFT.xlsx', sheet_name='Journal Entries')
je_df['Date'] = pd.to_datetime(je_df['Date'])
je_df['Debit'] = pd.to_numeric(je_df['Debit'], errors='coerce').fillna(0)
je_df['Credit'] = pd.to_numeric(je_df['Credit'], errors='coerce').fillna(0)

print(f"\nLoaded {len(je_df)} journal entry lines")
print(f"Date range: {je_df['Date'].min().strftime('%Y-%m-%d')} to {je_df['Date'].max().strftime('%Y-%m-%d')}")

# ========== GENERAL LEDGER ==========
print("\n[1] Generating General Ledger...")

gl_data = []
accounts = je_df['Account'].unique()

for account in sorted(accounts):
    account_entries = je_df[je_df['Account'] == account].sort_values('Date')

    balance = 0
    for _, row in account_entries.iterrows():
        balance += row['Debit'] - row['Credit']

        gl_data.append({
            'Account': account,
            'Entry #': row['Entry #'],
            'Date': row['Date'],
            'Memo': row['Memo'],
            'Debit': row['Debit'] if row['Debit'] > 0 else '',
            'Credit': row['Credit'] if row['Credit'] > 0 else '',
            'Balance': balance,
            'Source Document': row['Source Document'],
        })

gl_df = pd.DataFrame(gl_data)
print(f"Generated General Ledger with {len(gl_df)} lines across {len(accounts)} accounts")

# ========== TRIAL BALANCE ==========
print("\n[2] Generating Trial Balance...")

tb_data = []
for account in sorted(accounts):
    account_entries = je_df[je_df['Account'] == account]

    total_debit = account_entries['Debit'].sum()
    total_credit = account_entries['Credit'].sum()
    balance = total_debit - total_credit

    tb_data.append({
        'Account': account,
        'Debit': total_debit if total_debit > 0 else '',
        'Credit': total_credit if total_credit > 0 else '',
        'Balance (Dr/Cr)': balance,
    })

tb_df = pd.DataFrame(tb_data)

# Add totals row
totals = {
    'Account': 'TOTAL',
    'Debit': tb_df['Debit'].apply(lambda x: float(x) if x != '' else 0).sum(),
    'Credit': tb_df['Credit'].apply(lambda x: float(x) if x != '' else 0).sum(),
    'Balance (Dr/Cr)': tb_df['Balance (Dr/Cr)'].sum(),
}
tb_df = pd.concat([tb_df, pd.DataFrame([totals])], ignore_index=True)

print(f"Trial Balance: {len(tb_df)-1} accounts")
print(f"  Total Debits: ${totals['Debit']:,.2f}")
print(f"  Total Credits: ${totals['Credit']:,.2f}")
print(f"  Difference: ${abs(totals['Debit'] - totals['Credit']):,.2f}")

# ========== INCOME STATEMENT ==========
print("\n[3] Generating Income Statement...")

# Revenue
revenue_accounts = tb_df[tb_df['Account'].str.contains('Revenue|Income', case=False, na=False) & (tb_df['Account'] != 'TOTAL')]
total_revenue = revenue_accounts['Credit'].apply(lambda x: float(x) if x != '' else 0).sum()

# Expenses
expense_accounts = tb_df[tb_df['Account'].str.contains(r'\(6\d{3}\)|\(5\d{3}\)', regex=True, na=False)]
expense_data = []
for _, row in expense_accounts.iterrows():
    debit = float(row['Debit']) if row['Debit'] != '' else 0
    expense_data.append({
        'Account': row['Account'],
        'Amount': debit,
    })

expense_df = pd.DataFrame(expense_data)
total_expenses = expense_df['Amount'].sum()
net_income = total_revenue - total_expenses

is_data = []
is_data.append({'Section': 'REVENUE', 'Account': '', 'Amount': ''})
for _, row in revenue_accounts.iterrows():
    credit = float(row['Credit']) if row['Credit'] != '' else 0
    is_data.append({'Section': '', 'Account': row['Account'], 'Amount': credit})
is_data.append({'Section': '', 'Account': 'Total Revenue', 'Amount': total_revenue})
is_data.append({'Section': '', 'Account': '', 'Amount': ''})

is_data.append({'Section': 'EXPENSES', 'Account': '', 'Amount': ''})
for _, row in expense_df.iterrows():
    is_data.append({'Section': '', 'Account': row['Account'], 'Amount': row['Amount']})
is_data.append({'Section': '', 'Account': 'Total Expenses', 'Amount': total_expenses})
is_data.append({'Section': '', 'Account': '', 'Amount': ''})

is_data.append({'Section': 'NET INCOME', 'Account': '', 'Amount': net_income})

is_df = pd.DataFrame(is_data)

print(f"Income Statement:")
print(f"  Revenue: ${total_revenue:,.2f}")
print(f"  Expenses: ${total_expenses:,.2f}")
print(f"  Net Income: ${net_income:,.2f}")
print(f"  Tax (12.2%): ${net_income * 0.122:,.2f}")

# ========== BALANCE SHEET ==========
print("\n[4] Generating Balance Sheet...")

# Assets
asset_accounts = tb_df[tb_df['Account'].str.contains(r'\(1\d{3}\)', regex=True, na=False)]
assets_data = []
total_assets = 0
for _, row in asset_accounts.iterrows():
    balance = row['Balance (Dr/Cr)']
    assets_data.append({'Account': row['Account'], 'Amount': balance})
    total_assets += balance

# Liabilities
liability_accounts = tb_df[tb_df['Account'].str.contains(r'\(2\d{3}\)|\(3\d{3}\)', regex=True, na=False)]
liabilities_data = []
total_liabilities = 0
for _, row in liability_accounts.iterrows():
    balance = -row['Balance (Dr/Cr)']  # Flip sign for liabilities
    liabilities_data.append({'Account': row['Account'], 'Amount': balance})
    total_liabilities += balance

# Equity = Net Income
equity_data = []
equity_data.append({'Account': 'Retained Earnings (Net Income 2025)', 'Amount': net_income})
total_equity = net_income

bs_data = []
bs_data.append({'Section': 'ASSETS', 'Account': '', 'Amount': ''})
for item in assets_data:
    bs_data.append({'Section': '', 'Account': item['Account'], 'Amount': item['Amount']})
bs_data.append({'Section': '', 'Account': 'Total Assets', 'Amount': total_assets})
bs_data.append({'Section': '', 'Account': '', 'Amount': ''})

bs_data.append({'Section': 'LIABILITIES', 'Account': '', 'Amount': ''})
for item in liabilities_data:
    bs_data.append({'Section': '', 'Account': item['Account'], 'Amount': item['Amount']})
bs_data.append({'Section': '', 'Account': 'Total Liabilities', 'Amount': total_liabilities})
bs_data.append({'Section': '', 'Account': '', 'Amount': ''})

bs_data.append({'Section': 'EQUITY', 'Account': '', 'Amount': ''})
for item in equity_data:
    bs_data.append({'Section': '', 'Account': item['Account'], 'Amount': item['Amount']})
bs_data.append({'Section': '', 'Account': 'Total Equity', 'Amount': total_equity})
bs_data.append({'Section': '', 'Account': '', 'Amount': ''})

bs_data.append({'Section': '', 'Account': 'Total Liabilities + Equity', 'Amount': total_liabilities + total_equity})

bs_df = pd.DataFrame(bs_data)

print(f"Balance Sheet:")
print(f"  Total Assets: ${total_assets:,.2f}")
print(f"  Total Liabilities: ${total_liabilities:,.2f}")
print(f"  Total Equity: ${total_equity:,.2f}")
print(f"  Difference: ${abs(total_assets - (total_liabilities + total_equity)):,.2f}")

# ========== GIFI SUMMARY (for T2) ==========
print("\n[5] Generating GIFI Summary...")

gifi_mapping = {
    # Assets
    '1001': {'name': 'Cash', 'accounts': ['TD Business Chequing (1000)', 'BMO Business Chequing (1010)', 'Manulife Business Advantage (1020)']},
    '1200': {'name': 'HST Recoverable', 'accounts': ['HST Recoverable (1200)']},
    '1741': {'name': 'Computer Hardware (net)', 'accounts': ['Computer Hardware (1741)', 'Accumulated Depreciation (1742)']},

    # Liabilities
    '2100': {'name': 'HST Payable', 'accounts': ['HST Payable (2100)']},
    '3640': {'name': 'Due to Shareholders', 'accounts': ['Shareholder Loan Payable (3640)']},

    # Revenue
    '8000': {'name': 'Revenue', 'accounts': ['Uber Revenue (4100)', 'Corporate Income - Software Engineering (4300)']},

    # Expenses
    '8518': {'name': 'Cost of Goods Sold', 'accounts': []},  # None for 2025
    '8860': {'name': 'Professional Fees', 'accounts': ['Professional Fees (6860)']},
    '8521': {'name': 'Advertising and Promotion', 'accounts': ['Advertising and Promotion (6521)']},
    '8670': {'name': 'Office Expenses', 'accounts': ['Office Expenses (6670)']},
    '9225': {'name': 'Telephone and Utilities', 'accounts': ['Telephone and Internet (6225)', 'Utilities - Gas (6200)', 'Utilities - Electricity (6210)', 'Utilities - Water (6220)', 'Utilities (6200)']},
    '9275': {'name': 'Meals and Entertainment', 'accounts': ['Meals and Entertainment (6275)']},
    '9281': {'name': 'Vehicle Expense', 'accounts': ['Vehicle Expense (6281)']},
    '8710': {'name': 'Repairs and Maintenance', 'accounts': ['Repairs and Maintenance (6710)']},
    '8760': {'name': 'Property Taxes', 'accounts': ['Property Taxes (6300)']},
    '8762': {'name': 'Depreciation (CCA)', 'accounts': ['Depreciation Expense (6762)']},
    '9970': {'name': 'Miscellaneous', 'accounts': ['Bank Charges (6100)', 'Insurance (6840)', 'Legal Fees (6850)', 'Training and Education (6830)', 'Subcontractor Expense (6820)']},
}

gifi_data = []
for gifi_code, info in sorted(gifi_mapping.items()):
    amount = 0
    for account in info['accounts']:
        account_row = tb_df[tb_df['Account'] == account]
        if not account_row.empty:
            balance = account_row.iloc[0]['Balance (Dr/Cr)']

            # For revenue/liabilities, use credit balance (flip sign)
            if gifi_code.startswith('8') or gifi_code.startswith('2') or gifi_code == '3640':
                amount -= balance
            else:
                amount += balance

    gifi_data.append({
        'GIFI Code': gifi_code,
        'Description': info['name'],
        'Amount': amount,
    })

gifi_df = pd.DataFrame(gifi_data)

print("GIFI Summary for T2:")
for _, row in gifi_df.iterrows():
    if row['Amount'] != 0:
        print(f"  {row['GIFI Code']} - {row['Description']:<40} ${row['Amount']:>12,.2f}")

# ========== SAVE TO EXCEL ==========
print("\n" + "="*80)
print("SAVING TO EXCEL")
print("="*80)

output_file = 'A:/toocore/doc/2025/td2025_books_CORRECTED.xlsx'

with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    je_df.to_excel(writer, sheet_name='Journal Entries', index=False)
    gl_df.to_excel(writer, sheet_name='General Ledger', index=False)
    tb_df.to_excel(writer, sheet_name='Trial Balance', index=False)
    is_df.to_excel(writer, sheet_name='Income Statement', index=False)
    bs_df.to_excel(writer, sheet_name='Balance Sheet', index=False)
    gifi_df.to_excel(writer, sheet_name='GIFI Summary', index=False)

print(f"\nSaved to: {output_file}")
print("\nSheets created:")
print("  1. Journal Entries ({} lines)".format(len(je_df)))
print("  2. General Ledger ({} lines)".format(len(gl_df)))
print("  3. Trial Balance ({} accounts)".format(len(tb_df)-1))
print("  4. Income Statement")
print("  5. Balance Sheet")
print("  6. GIFI Summary")

print("\n" + "="*80)
print("2025 BOOKS COMPLETE!")
print("="*80)
print(f"Net Income: ${net_income:,.2f}")
print(f"Tax Payable (12.2%): ${net_income * 0.122:,.2f}")
print(f"Shareholder Loan Ending: ${abs(tb_df[tb_df['Account'] == 'Shareholder Loan Payable (3640)']['Balance (Dr/Cr)'].iloc[0]):,.2f}")
