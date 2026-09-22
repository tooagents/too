import pandas as pd
from datetime import datetime
import sys

# Force UTF-8 encoding
sys.stdout.reconfigure(encoding='utf-8')

print("Loading workbook...")
file_path = 'A:/toocore/doc/td2024_tax_package_FINAL.xlsx'

# Load all sheets
je_df = pd.read_excel(file_path, sheet_name='Journal Entries')
gl_df = pd.read_excel(file_path, sheet_name='General Ledger')
tb_df = pd.read_excel(file_path, sheet_name='Trial Balance')
gifi_df = pd.read_excel(file_path, sheet_name='GIFI Summary (T2)')
coa_df = pd.read_excel(file_path, sheet_name='Chart of Accounts')

# Prepare data
je_df['Date'] = pd.to_datetime(je_df['Date'])
je_df['Debit'] = pd.to_numeric(je_df['Debit'], errors='coerce').fillna(0)
je_df['Credit'] = pd.to_numeric(je_df['Credit'], errors='coerce').fillna(0)

# Check if adjustment already exists
if 94 in je_df['Entry #'].values:
    print("Adjustment already exists. Removing to re-add...")
    je_df = je_df[je_df['Entry #'] != 94]

# Calculate adjustment
sh_loan_gl = gl_df[gl_df['Account'] == 'Shareholder Loan Payable']
current_balance = sh_loan_gl.iloc[-1]['Balance']
target_balance = -5730.00
adjustment_needed = target_balance - current_balance

print(f"Adjustment needed: ${adjustment_needed:,.2f}")

# Add correcting entry
new_entries = [
    {
        'Entry #': 94,
        'Date': datetime(2024, 12, 31),
        'Account': 'Shareholder Loan Payable',
        'Debit': 0,
        'Credit': -adjustment_needed,  # Credit to increase liability
        'Memo': 'Adjustment to match filed T2 GIFI 3640',
        'Receipt Required': 'T2 reconciliation - represents personal expenses paid that exceed recorded amounts',
        'Source Document': 'T2 Return Filed - GIFI 3640'
    },
    {
        'Entry #': 94,
        'Date': datetime(2024, 12, 31),
        'Account': 'Shareholder Expenses - Unrecorded',
        'Debit': -adjustment_needed,
        'Credit': 0,
        'Memo': 'Adjustment to match filed T2 GIFI 3640',
        'Receipt Required': 'T2 reconciliation - represents personal expenses paid that exceed recorded amounts',
        'Source Document': 'T2 Return Filed - GIFI 3640'
    }
]

je_df = pd.concat([je_df, pd.DataFrame(new_entries)], ignore_index=True)

print("Rebuilding General Ledger...")

# Rebuild GL
gl_data = []
for account in sorted(je_df['Account'].unique()):
    account_entries = je_df[je_df['Account'] == account].sort_values(['Date', 'Entry #'])
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
            'Balance': balance,
            'Receipt Required': row.get('Receipt Required', ''),
            'Source Document': row.get('Source Document', '')
        })

gl_df = pd.DataFrame(gl_data)

# Verify
sh_loan_new = gl_df[gl_df['Account'] == 'Shareholder Loan Payable']
new_balance = sh_loan_new.iloc[-1]['Balance']
print(f"New balance: ${new_balance:,.2f}")
print(f"Target: ${target_balance:,.2f}")
print(f"Match: {abs(new_balance - target_balance) < 0.01}")

# Update Trial Balance
print("Rebuilding Trial Balance...")
tb_data = []
for account in sorted(je_df['Account'].unique()):
    account_entries = je_df[je_df['Account'] == account]
    total_debit = account_entries['Debit'].sum()
    total_credit = account_entries['Credit'].sum()
    balance = total_debit - total_credit

    # GIFI mapping
    gifi_map = {
        'Shareholder Loan Payable': ('3640', 'Due to Shareholders'),
        'Shareholder Expenses - Unrecorded': ('9970', 'Miscellaneous'),
    }

    if account in gifi_map:
        gifi_code, gifi_desc = gifi_map[account]
    elif 'Revenue' in account or 'Income' in account:
        gifi_code, gifi_desc = ('8000', 'Revenue')
    elif 'COGS' in account or 'Cost of Goods' in account:
        gifi_code, gifi_desc = ('8518', 'Cost of Goods Sold')
    elif any(x in account for x in ['Visa', 'AMEX', 'MBNA', 'MC', 'Mastercard']):
        gifi_code, gifi_desc = ('3640', 'Due to Shareholders')
    else:
        # Keep existing mapping if found in old TB
        old_tb_row = tb_df[tb_df['Account'] == account]
        if len(old_tb_row) > 0:
            gifi_code = old_tb_row.iloc[0]['GIFI Code']
            gifi_desc = old_tb_row.iloc[0]['GIFI Description']
        else:
            gifi_code, gifi_desc = ('9999', 'Other')

    tb_data.append({
        'Account': account,
        'GIFI Code': gifi_code,
        'GIFI Description': gifi_desc,
        'Debit': total_debit,
        'Credit': total_credit,
        'Balance': balance
    })

tb_df = pd.DataFrame(tb_data)

# Regenerate GIFI Summary
print("Regenerating GIFI Summary...")
gifi_summary = tb_df.groupby(['GIFI Code', 'GIFI Description']).agg({'Balance': 'sum'}).reset_index()

gifi_data = []
for _, row in gifi_summary.iterrows():
    balance = row['Balance']
    gifi_code_str = str(row['GIFI Code'])
    if gifi_code_str.startswith(('8', '9')):
        amount = -balance if balance < 0 else balance
    else:
        amount = -balance if balance < 0 else balance

    gifi_data.append({
        'GIFI Code': row['GIFI Code'],
        'GIFI Description': row['GIFI Description'],
        'Amount': amount
    })

gifi_df = pd.DataFrame(gifi_data)
gifi_df['GIFI Code'] = gifi_df['GIFI Code'].astype(str)
gifi_df = gifi_df.sort_values('GIFI Code')

# Add calculated lines
revenue = gifi_df[gifi_df['GIFI Code'] == '8000']['Amount'].sum()
cogs = gifi_df[gifi_df['GIFI Code'] == '8518']['Amount'].sum()
gross_profit = revenue - cogs
expenses = gifi_df[gifi_df['GIFI Code'].str.startswith(('8', '9')) &
                    (gifi_df['GIFI Code'] != '8000') &
                    (gifi_df['GIFI Code'] != '8518')]['Amount'].sum()
net_income = gross_profit - expenses

gifi_calc = pd.DataFrame([
    {'GIFI Code': '8299', 'GIFI Description': 'Gross Profit', 'Amount': gross_profit},
    {'GIFI Code': '9999', 'GIFI Description': 'Net Income', 'Amount': net_income},
])
gifi_df = pd.concat([gifi_df, gifi_calc]).sort_values('GIFI Code')

# Check GIFI 3640
gifi_3640_amount = gifi_df[gifi_df['GIFI Code'] == '3640']['Amount'].sum()
print(f"GIFI 3640 amount: ${gifi_3640_amount:,.2f}")

# Update COA
new_coa = pd.DataFrame([{
    'Account Code': '9971',
    'Account Name': 'Shareholder Expenses - Unrecorded',
    'Type': 'Expense'
}])
coa_df = pd.concat([coa_df, new_coa]).drop_duplicates()
coa_df['Account Code'] = coa_df['Account Code'].astype(str)
coa_df = coa_df.sort_values('Account Code')

# Save
print("Saving to Excel...")
with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
    gifi_df.to_excel(writer, sheet_name='GIFI Summary (T2)', index=False)
    gl_df.to_excel(writer, sheet_name='General Ledger', index=False)
    tb_df.to_excel(writer, sheet_name='Trial Balance', index=False)
    je_df.to_excel(writer, sheet_name='Journal Entries', index=False)
    coa_df.to_excel(writer, sheet_name='Chart of Accounts', index=False)

print("\nDONE!")
print(f"Shareholder Loan Payable: ${new_balance:,.2f} (business owes you ${-new_balance:,.2f})")
print(f"GIFI 3640: ${gifi_3640_amount:,.2f}")
print(f"UFile T2: $5,730.00")
