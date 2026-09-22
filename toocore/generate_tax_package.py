import pandas as pd
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime

# Read source data
df = pd.read_excel('A:/toocore/doc/td2024.xlsx')

# Filter to 2024 only
df['Date'] = pd.to_datetime(df['Date'])
df = df[df['Date'].dt.year == 2024].copy()

print(f"Processing {len(df)} transactions for 2024")
print(f"Date range: {df['Date'].min()} to {df['Date'].max()}")

# Journal entries list
journal_entries = []
entry_num = 1

def split_hst(amount, has_hst=True):
    """Split amount into base and HST (13% included)"""
    if not has_hst:
        return amount, Decimal('0')
    amt = Decimal(str(amount))
    base = (amt / Decimal('1.13')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    hst = (base * Decimal('0.13')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return float(base), float(hst)

def add_entry(date, account, debit, credit, memo, review=""):
    """Add a journal entry"""
    global entry_num
    journal_entries.append({
        'Entry #': entry_num,
        'Date': date,
        'Account': account,
        'Debit': debit if debit else '',
        'Credit': credit if credit else '',
        'Memo': memo,
        'Review Required': review
    })

# Process each transaction (same logic as before)
for idx, row in df.iterrows():
    date = row['Date']
    desc = row['Description']
    debit = row['Debit'] if pd.notna(row['Debit']) else None
    credit = row['Credit'] if pd.notna(row['Credit']) else None

    if 'OPEN ACCOUNT' in desc:
        continue

    if 'Uber Holdings C MSP' in desc:
        revenue, hst = split_hst(credit, True)
        add_entry(date, 'TD Business Chequing', credit, None, desc, "")
        add_entry(date, 'Uber Revenue', None, revenue, desc, "")
        add_entry(date, 'HST Payable', None, hst, desc, "")
        entry_num += 1

    elif 'VENTURELAB INNO MSP' in desc:
        revenue, hst = split_hst(credit, True)
        add_entry(date, 'TD Business Chequing', credit, None, desc, "")
        add_entry(date, 'Corporate Income - VentureLab', None, revenue, desc, "")
        add_entry(date, 'HST Payable', None, hst, desc, "")
        entry_num += 1

    elif 'E-TRANSFER' in desc and credit:
        if credit == 5.00 or credit == 400.00:
            add_entry(date, 'TD Business Chequing', credit, None, desc, "Personal funds deposited")
            add_entry(date, 'Shareholder Loan Payable', None, credit, desc, "Personal funds deposited")
            entry_num += 1
        elif credit == 2260.00:
            revenue, hst = split_hst(credit, True)
            add_entry(date, 'TD Business Chequing', credit, None, desc, "")
            add_entry(date, 'Corporate Income - Software Engineering', None, revenue, desc, "")
            add_entry(date, 'HST Payable', None, hst, desc, "")
            entry_num += 1

    elif 'SEND E-TFR' in desc:
        add_entry(date, 'Shareholder Loan Payable', debit, None, desc, "Owner draw")
        add_entry(date, 'TD Business Chequing', None, debit, desc, "Owner draw")
        entry_num += 1

    elif 'TFR-FR' in desc:
        add_entry(date, 'TD Business Chequing', credit, None, desc, "Transfer from personal")
        add_entry(date, 'Shareholder Loan Payable', None, credit, desc, "Transfer from personal")
        entry_num += 1

    elif 'TFR-TO' in desc:
        add_entry(date, 'Shareholder Loan Payable', debit, None, desc, "Transfer to personal")
        add_entry(date, 'TD Business Chequing', None, debit, desc, "Transfer to personal")
        entry_num += 1

    elif 'Tangerine MSP' in desc and credit:
        add_entry(date, 'TD Business Chequing', credit, None, desc, "")
        add_entry(date, 'Other Income - Windfall', None, credit, desc, "")
        entry_num += 1

    elif 'Tangerine FTD' in desc:
        add_entry(date, 'Shareholder Loan Payable', debit, None, desc, "Transfer to personal savings")
        add_entry(date, 'TD Business Chequing', None, debit, desc, "Transfer to personal savings")
        entry_num += 1

    elif 'Tangerine INV' in desc:
        add_entry(date, 'TD Business Chequing', credit, None, desc, "Transfer from personal savings")
        add_entry(date, 'Shareholder Loan Payable', None, credit, desc, "Transfer from personal savings")
        entry_num += 1

    elif 'BMO VISA' in desc:
        add_entry(date, 'BMO Visa Payable', debit, None, desc, "Personal card payment")
        add_entry(date, 'TD Business Chequing', None, debit, desc, "Personal card payment")
        entry_num += 1

    elif 'CIBC VISA' in desc:
        add_entry(date, 'CIBC Visa Payable', debit, None, desc, "Personal card payment")
        add_entry(date, 'TD Business Chequing', None, debit, desc, "Personal card payment")
        entry_num += 1

    elif 'AMEX FTD' in desc:
        add_entry(date, 'AMEX Payable', debit, None, desc, "Personal card payment")
        add_entry(date, 'TD Business Chequing', None, debit, desc, "Personal card payment")
        entry_num += 1

    elif 'MBNA MSP' in desc:
        add_entry(date, 'MBNA Payable', debit, None, desc, "Personal card payment")
        add_entry(date, 'TD Business Chequing', None, debit, desc, "Personal card payment")
        entry_num += 1

    elif 'NATL BANK MC' in desc:
        add_entry(date, 'National Bank MC Payable', debit, None, desc, "Personal card payment")
        add_entry(date, 'TD Business Chequing', None, debit, desc, "Personal card payment")
        entry_num += 1

    elif 'PC MASTRCRD' in desc:
        add_entry(date, 'PC Mastercard Payable', debit, None, desc, "Personal card payment")
        add_entry(date, 'TD Business Chequing', None, debit, desc, "Personal card payment")
        entry_num += 1

    elif 'CAN TIRE MC' in desc:
        add_entry(date, 'Canadian Tire MC Payable', debit, None, desc, "Personal card payment")
        add_entry(date, 'TD Business Chequing', None, debit, desc, "Personal card payment")
        entry_num += 1

    elif 'Enbridge Gas' in desc:
        expense, hst = split_hst(debit, True)
        add_entry(date, 'Utilities - Gas', expense, None, desc, "")
        add_entry(date, 'HST Recoverable', hst, None, desc, "")
        add_entry(date, 'TD Business Chequing', None, debit, desc, "")
        entry_num += 1

    elif 'ALECTRA UTIL' in desc:
        expense, hst = split_hst(debit, True)
        add_entry(date, 'Utilities - Electricity', expense, None, desc, "")
        add_entry(date, 'HST Recoverable', hst, None, desc, "")
        add_entry(date, 'TD Business Chequing', None, debit, desc, "")
        entry_num += 1

    elif 'RHill Water' in desc:
        expense, hst = split_hst(debit, True)
        add_entry(date, 'Utilities - Water', expense, None, desc, "")
        add_entry(date, 'HST Recoverable', hst, None, desc, "")
        add_entry(date, 'TD Business Chequing', None, debit, desc, "")
        entry_num += 1

    elif 'TOR-Tax' in desc:
        add_entry(date, 'Property Tax', debit, None, desc, "")
        add_entry(date, 'TD Business Chequing', None, debit, desc, "")
        entry_num += 1

    elif 'MONTHLY PLAN FEE' in desc:
        expense, hst = split_hst(debit, True)
        add_entry(date, 'Bank Charges', expense, None, desc, "")
        add_entry(date, 'HST Recoverable', hst, None, desc, "")
        add_entry(date, 'TD Business Chequing', None, debit, desc, "")
        entry_num += 1

    elif 'SBB Offer' in desc:
        add_entry(date, 'TD Business Chequing', credit, None, desc, "")
        add_entry(date, 'Other Income - Bank Bonus', None, credit, desc, "")
        entry_num += 1

    elif 'TD ATM DEP' in desc:
        revenue, hst = split_hst(credit, True)
        add_entry(date, 'TD Business Chequing', credit, None, desc, "VentureLab cheque deposit")
        add_entry(date, 'Corporate Income - VentureLab', None, revenue, desc, "VentureLab cheque deposit")
        add_entry(date, 'HST Payable', None, hst, desc, "VentureLab cheque deposit")
        entry_num += 1

# Create Journal Entries DataFrame
je_df = pd.DataFrame(journal_entries)
je_df['Debit'] = pd.to_numeric(je_df['Debit'], errors='coerce').fillna(0)
je_df['Credit'] = pd.to_numeric(je_df['Credit'], errors='coerce').fillna(0)

print(f"\nGenerated {entry_num - 1} journal entries with {len(journal_entries)} lines")

# ========== GENERAL LEDGER ==========
gl_data = []
for account in sorted(je_df['Account'].unique()):
    account_entries = je_df[je_df['Account'] == account].copy()
    account_entries = account_entries.sort_values('Date')

    balance = 0
    for _, row in account_entries.iterrows():
        balance += row['Debit'] - row['Credit']
        gl_data.append({
            'Account': account,
            'Date': row['Date'],
            'Entry #': row['Entry #'],
            'Memo': row['Memo'],
            'Debit': row['Debit'] if row['Debit'] else '',
            'Credit': row['Credit'] if row['Credit'] else '',
            'Balance': balance
        })

gl_df = pd.DataFrame(gl_data)

# ========== TRIAL BALANCE ==========
tb_data = []
for account in sorted(je_df['Account'].unique()):
    account_entries = je_df[je_df['Account'] == account]
    total_debit = account_entries['Debit'].sum()
    total_credit = account_entries['Credit'].sum()
    balance = total_debit - total_credit

    tb_data.append({
        'Account': account,
        'Debit': total_debit,
        'Credit': total_credit,
        'Balance': balance
    })

tb_df = pd.DataFrame(tb_data)

# ========== INCOME STATEMENT ==========
# Revenue accounts (normal credit balance, show as positive)
revenue_accounts = tb_df[tb_df['Account'].str.contains('Revenue|Income', case=False, na=False)].copy()
revenue_accounts['Amount'] = -revenue_accounts['Balance']  # Flip sign

# Expense accounts (normal debit balance, show as positive)
expense_accounts = tb_df[tb_df['Account'].str.contains('Charges|Utilities|Tax', case=False, na=False)].copy()
expense_accounts['Amount'] = expense_accounts['Balance']

total_revenue = revenue_accounts['Amount'].sum()
total_expenses = expense_accounts['Amount'].sum()
net_income = total_revenue - total_expenses

is_data = []
is_data.append({'Account': 'REVENUE', 'Amount': ''})
for _, row in revenue_accounts.iterrows():
    is_data.append({'Account': f"  {row['Account']}", 'Amount': row['Amount']})
is_data.append({'Account': 'Total Revenue', 'Amount': total_revenue})
is_data.append({'Account': '', 'Amount': ''})
is_data.append({'Account': 'EXPENSES', 'Amount': ''})
for _, row in expense_accounts.iterrows():
    is_data.append({'Account': f"  {row['Account']}", 'Amount': row['Amount']})
is_data.append({'Account': 'Total Expenses', 'Amount': total_expenses})
is_data.append({'Account': '', 'Amount': ''})
is_data.append({'Account': 'NET INCOME', 'Amount': net_income})

is_df = pd.DataFrame(is_data)

# ========== BALANCE SHEET ==========
# Assets (normal debit balance)
asset_accounts = tb_df[tb_df['Account'].str.contains('Chequing|Recoverable|Receivable', case=False, na=False)].copy()
asset_accounts = asset_accounts[~asset_accounts['Account'].str.contains('Payable', case=False, na=False)]
asset_accounts['Amount'] = asset_accounts['Balance']

# Liabilities (normal credit balance, show as positive)
liability_accounts = tb_df[tb_df['Account'].str.contains('Payable', case=False, na=False)].copy()
liability_accounts['Amount'] = -liability_accounts['Balance']

total_assets = asset_accounts['Amount'].sum()
total_liabilities = liability_accounts['Amount'].sum()
retained_earnings = net_income  # For new corporation, net income = retained earnings

bs_data = []
bs_data.append({'Account': 'ASSETS', 'Amount': ''})
for _, row in asset_accounts.iterrows():
    bs_data.append({'Account': f"  {row['Account']}", 'Amount': row['Amount']})
bs_data.append({'Account': 'Total Assets', 'Amount': total_assets})
bs_data.append({'Account': '', 'Amount': ''})
bs_data.append({'Account': 'LIABILITIES', 'Amount': ''})
for _, row in liability_accounts.iterrows():
    bs_data.append({'Account': f"  {row['Account']}", 'Amount': row['Amount']})
bs_data.append({'Account': 'Total Liabilities', 'Amount': total_liabilities})
bs_data.append({'Account': '', 'Amount': ''})
bs_data.append({'Account': 'EQUITY', 'Amount': ''})
bs_data.append({'Account': '  Retained Earnings (Net Income)', 'Amount': retained_earnings})
bs_data.append({'Account': 'Total Equity', 'Amount': retained_earnings})
bs_data.append({'Account': '', 'Amount': ''})
bs_data.append({'Account': 'TOTAL LIABILITIES + EQUITY', 'Amount': total_liabilities + retained_earnings})

bs_df = pd.DataFrame(bs_data)

# ========== CHART OF ACCOUNTS ==========
coa = [
    {'Account Code': '1000', 'Account Name': 'TD Business Chequing', 'Type': 'Asset'},
    {'Account Code': '1200', 'Account Name': 'HST Recoverable', 'Type': 'Asset'},
    {'Account Code': '1400', 'Account Name': 'Shareholder Loan Receivable', 'Type': 'Asset'},
    {'Account Code': '2100', 'Account Name': 'HST Payable', 'Type': 'Liability'},
    {'Account Code': '2200', 'Account Name': 'Shareholder Loan Payable', 'Type': 'Liability'},
    {'Account Code': '2210', 'Account Name': 'BMO Visa Payable', 'Type': 'Liability'},
    {'Account Code': '2220', 'Account Name': 'CIBC Visa Payable', 'Type': 'Liability'},
    {'Account Code': '2230', 'Account Name': 'AMEX Payable', 'Type': 'Liability'},
    {'Account Code': '2240', 'Account Name': 'MBNA Payable', 'Type': 'Liability'},
    {'Account Code': '2250', 'Account Name': 'National Bank MC Payable', 'Type': 'Liability'},
    {'Account Code': '2260', 'Account Name': 'PC Mastercard Payable', 'Type': 'Liability'},
    {'Account Code': '2270', 'Account Name': 'Canadian Tire MC Payable', 'Type': 'Liability'},
    {'Account Code': '4100', 'Account Name': 'Uber Revenue', 'Type': 'Revenue'},
    {'Account Code': '4200', 'Account Name': 'Corporate Income - VentureLab', 'Type': 'Revenue'},
    {'Account Code': '4300', 'Account Name': 'Corporate Income - Software Engineering', 'Type': 'Revenue'},
    {'Account Code': '4900', 'Account Name': 'Other Income - Bank Bonus', 'Type': 'Revenue'},
    {'Account Code': '4910', 'Account Name': 'Other Income - Windfall', 'Type': 'Revenue'},
    {'Account Code': '6100', 'Account Name': 'Bank Charges', 'Type': 'Expense'},
    {'Account Code': '6200', 'Account Name': 'Utilities - Gas', 'Type': 'Expense'},
    {'Account Code': '6210', 'Account Name': 'Utilities - Electricity', 'Type': 'Expense'},
    {'Account Code': '6220', 'Account Name': 'Utilities - Water', 'Type': 'Expense'},
    {'Account Code': '6300', 'Account Name': 'Property Tax', 'Type': 'Expense'},
]
coa_df = pd.DataFrame(coa)

# ========== WRITE TO EXCEL ==========
with pd.ExcelWriter('A:/toocore/doc/td2024_tax_package.xlsx', engine='openpyxl') as writer:
    # Income Statement
    is_df.to_excel(writer, sheet_name='Income Statement', index=False)

    # Balance Sheet
    bs_df.to_excel(writer, sheet_name='Balance Sheet', index=False)

    # General Ledger
    gl_df.to_excel(writer, sheet_name='General Ledger', index=False)

    # Trial Balance
    tb_df.to_excel(writer, sheet_name='Trial Balance', index=False)

    # Journal Entries
    je_df.to_excel(writer, sheet_name='Journal Entries', index=False)

    # Chart of Accounts
    coa_df.to_excel(writer, sheet_name='Chart of Accounts', index=False)

print("\n" + "="*60)
print("TAX PACKAGE GENERATED: td2024_tax_package.xlsx")
print("="*60)
print(f"Period: 2024 Fiscal Year (Ended Dec 31, 2024)")
print(f"Total Revenue: ${total_revenue:,.2f}")
print(f"Total Expenses: ${total_expenses:,.2f}")
print(f"Net Income: ${net_income:,.2f}")
print(f"Total Assets: ${total_assets:,.2f}")
print(f"Total Liabilities: ${total_liabilities:,.2f}")
print(f"Balance Check: Assets ({total_assets:.2f}) = Liabilities + Equity ({total_liabilities + retained_earnings:.2f})")
print("="*60)
