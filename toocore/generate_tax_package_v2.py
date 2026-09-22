import pandas as pd
from datetime import datetime

# Read existing journal entries
je_df = pd.read_excel('A:/toocore/doc/td2024_journal_entries.xlsx', sheet_name='Journal Entries')

print(f"Loaded {len(je_df)} journal entry lines")

# Convert date and amounts
je_df['Date'] = pd.to_datetime(je_df['Date'])
je_df['Debit'] = pd.to_numeric(je_df['Debit'], errors='coerce').fillna(0)
je_df['Credit'] = pd.to_numeric(je_df['Credit'], errors='coerce').fillna(0)

# Filter to 2024 only
je_df_2024 = je_df[je_df['Date'].dt.year == 2024].copy()

print(f"Filtered to {len(je_df_2024)} lines for 2024")
print(f"Date range: {je_df_2024['Date'].min()} to {je_df_2024['Date'].max()}")

# ========== GENERAL LEDGER ==========
print("\nGenerating General Ledger...")
gl_data = []

for account in sorted(je_df_2024['Account'].unique()):
    account_entries = je_df_2024[je_df_2024['Account'] == account].copy()
    account_entries = account_entries.sort_values(['Date', 'Entry #'])

    balance = 0
    for _, row in account_entries.iterrows():
        balance += row['Debit'] - row['Credit']
        gl_data.append({
            'Account': account,
            'Date': row['Date'],
            'Entry #': int(row['Entry #']),
            'Memo': row['Memo'],
            'Debit': row['Debit'] if row['Debit'] > 0 else '',
            'Credit': row['Credit'] if row['Credit'] > 0 else '',
            'Balance': balance
        })

gl_df = pd.DataFrame(gl_data)
print(f"Generated {len(gl_df)} GL lines for {len(gl_df['Account'].unique())} accounts")

# ========== TRIAL BALANCE ==========
print("\nGenerating Trial Balance...")
tb_data = []

for account in sorted(je_df_2024['Account'].unique()):
    account_entries = je_df_2024[je_df_2024['Account'] == account]
    total_debit = account_entries['Debit'].sum()
    total_credit = account_entries['Credit'].sum()
    balance = total_debit - total_credit

    # Determine account type
    if any(keyword in account for keyword in ['Chequing', 'Recoverable', 'Receivable']):
        if 'Payable' not in account:
            acct_type = 'Asset'
        else:
            acct_type = 'Liability'
    elif 'Payable' in account:
        acct_type = 'Liability'
    elif any(keyword in account for keyword in ['Revenue', 'Income']):
        acct_type = 'Revenue'
    elif any(keyword in account for keyword in ['Charges', 'Utilities', 'Tax', 'Expense']):
        acct_type = 'Expense'
    else:
        acct_type = 'Other'

    tb_data.append({
        'Account': account,
        'Type': acct_type,
        'Debit': total_debit,
        'Credit': total_credit,
        'Balance': balance
    })

tb_df = pd.DataFrame(tb_data)

# Verify trial balance
total_debits = tb_df['Debit'].sum()
total_credits = tb_df['Credit'].sum()
print(f"Trial Balance - Total Debits: ${total_debits:,.2f}")
print(f"Trial Balance - Total Credits: ${total_credits:,.2f}")
print(f"Difference: ${abs(total_debits - total_credits):.2f}")

# ========== INCOME STATEMENT ==========
print("\nGenerating Income Statement...")

# Revenue accounts (normal credit balance, show as positive)
revenue_accounts = tb_df[tb_df['Type'] == 'Revenue'].copy()
revenue_accounts['Amount'] = -revenue_accounts['Balance']  # Flip sign for display

# Expense accounts (normal debit balance, show as positive)
expense_accounts = tb_df[tb_df['Type'] == 'Expense'].copy()
expense_accounts['Amount'] = expense_accounts['Balance']

total_revenue = revenue_accounts['Amount'].sum()
total_expenses = expense_accounts['Amount'].sum()
net_income = total_revenue - total_expenses

is_data = []
is_data.append({'Section': 'REVENUE', 'Account': '', 'Amount': ''})
for _, row in revenue_accounts.iterrows():
    is_data.append({'Section': 'Revenue', 'Account': row['Account'], 'Amount': row['Amount']})
is_data.append({'Section': 'Revenue Total', 'Account': 'Total Revenue', 'Amount': total_revenue})
is_data.append({'Section': '', 'Account': '', 'Amount': ''})
is_data.append({'Section': 'EXPENSES', 'Account': '', 'Amount': ''})
for _, row in expense_accounts.iterrows():
    is_data.append({'Section': 'Expense', 'Account': row['Account'], 'Amount': row['Amount']})
is_data.append({'Section': 'Expense Total', 'Account': 'Total Expenses', 'Amount': total_expenses})
is_data.append({'Section': '', 'Account': '', 'Amount': ''})
is_data.append({'Section': 'NET INCOME', 'Account': 'Net Income for the Year', 'Amount': net_income})

is_df = pd.DataFrame(is_data)

# ========== BALANCE SHEET ==========
print("\nGenerating Balance Sheet...")

# Assets (normal debit balance)
asset_accounts = tb_df[tb_df['Type'] == 'Asset'].copy()
asset_accounts['Amount'] = asset_accounts['Balance']

# Liabilities (normal credit balance, show as positive)
liability_accounts = tb_df[tb_df['Type'] == 'Liability'].copy()
liability_accounts['Amount'] = -liability_accounts['Balance']

total_assets = asset_accounts['Amount'].sum()
total_liabilities = liability_accounts['Amount'].sum()
retained_earnings = net_income  # For new corporation, net income = retained earnings

bs_data = []
bs_data.append({'Section': 'ASSETS', 'Account': '', 'Amount': ''})
for _, row in asset_accounts.iterrows():
    bs_data.append({'Section': 'Asset', 'Account': row['Account'], 'Amount': row['Amount']})
bs_data.append({'Section': 'Asset Total', 'Account': 'Total Assets', 'Amount': total_assets})
bs_data.append({'Section': '', 'Account': '', 'Amount': ''})
bs_data.append({'Section': 'LIABILITIES', 'Account': '', 'Amount': ''})
for _, row in liability_accounts.iterrows():
    bs_data.append({'Section': 'Liability', 'Account': row['Account'], 'Amount': row['Amount']})
bs_data.append({'Section': 'Liability Total', 'Account': 'Total Liabilities', 'Amount': total_liabilities})
bs_data.append({'Section': '', 'Account': '', 'Amount': ''})
bs_data.append({'Section': 'EQUITY', 'Account': '', 'Amount': ''})
bs_data.append({'Section': 'Equity', 'Account': 'Retained Earnings (Net Income)', 'Amount': retained_earnings})
bs_data.append({'Section': 'Equity Total', 'Account': 'Total Equity', 'Amount': retained_earnings})
bs_data.append({'Section': '', 'Account': '', 'Amount': ''})
bs_data.append({'Section': 'Total', 'Account': 'TOTAL LIABILITIES + EQUITY', 'Amount': total_liabilities + retained_earnings})
bs_data.append({'Section': '', 'Account': '', 'Amount': ''})
bs_data.append({'Section': 'Check', 'Account': 'Balance Check (should be 0)', 'Amount': total_assets - (total_liabilities + retained_earnings)})

bs_df = pd.DataFrame(bs_data)

# ========== READ CHART OF ACCOUNTS FROM ORIGINAL ==========
coa_df = pd.read_excel('A:/toocore/doc/td2024_journal_entries.xlsx', sheet_name='Chart of Accounts')

# ========== WRITE TO EXCEL ==========
print("\nWriting to Excel...")
with pd.ExcelWriter('A:/toocore/doc/td2024_tax_package.xlsx', engine='openpyxl') as writer:
    # Income Statement
    is_df[['Account', 'Amount']].to_excel(writer, sheet_name='Income Statement', index=False)

    # Balance Sheet
    bs_df[['Account', 'Amount']].to_excel(writer, sheet_name='Balance Sheet', index=False)

    # General Ledger
    gl_df.to_excel(writer, sheet_name='General Ledger', index=False)

    # Trial Balance
    tb_df.to_excel(writer, sheet_name='Trial Balance', index=False)

    # Journal Entries (from source, 2024 only)
    je_df_2024.to_excel(writer, sheet_name='Journal Entries', index=False)

    # Chart of Accounts
    coa_df.to_excel(writer, sheet_name='Chart of Accounts', index=False)

print("\n" + "="*70)
print("TAX PACKAGE GENERATED: td2024_tax_package.xlsx")
print("="*70)
print(f"Corporation Tax Year: 2024 (Jan 1 - Dec 31, 2024)")
print(f"Fiscal Year End: December 31, 2024")
print("")
print("INCOME STATEMENT:")
print(f"  Total Revenue:          ${total_revenue:>15,.2f}")
print(f"  Total Expenses:         ${total_expenses:>15,.2f}")
print(f"  Net Income:             ${net_income:>15,.2f}")
print("")
print("BALANCE SHEET:")
print(f"  Total Assets:           ${total_assets:>15,.2f}")
print(f"  Total Liabilities:      ${total_liabilities:>15,.2f}")
print(f"  Retained Earnings:      ${retained_earnings:>15,.2f}")
print(f"  Total Liab + Equity:    ${(total_liabilities + retained_earnings):>15,.2f}")
print(f"  Balance Check:          ${abs(total_assets - (total_liabilities + retained_earnings)):>15,.2f}")
print("")
print("SHEETS INCLUDED:")
print("  1. Income Statement     - For T2 Schedule 125")
print("  2. Balance Sheet        - For T2 Schedule 100")
print("  3. General Ledger       - With Entry # links to JE")
print("  4. Trial Balance        - Account totals")
print("  5. Journal Entries      - Complete audit trail")
print("  6. Chart of Accounts    - Account structure")
print("="*70)
