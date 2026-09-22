import pandas as pd
from datetime import datetime

# UFile GIFI targets
UFILE_GIFI = {
    # Revenue
    'Revenue': 24075.00,

    # COGS
    'Cost of Goods Sold': 2178.00,

    # Expenses
    'Professional Fees': 650.00,
    'Advertising and Promotion': 2073.00,
    'Office Expenses': 1372.00,
    'Telephone and Utilities': 1397.00,
    'Meals and Entertainment': 650.00,
    'Vehicle Expense': 7755.00,
    'Repairs and Maintenance': 765.00,
    'Property Taxes': 2010.00,
    'Depreciation (CCA)': 2420.00,
    'Miscellaneous': 584.00,

    # Assets
    'Computer Hardware': 6380.00,
    'Cash': 71.00,

    # Liabilities
    'Accounts Payable': 650.00,
    'Due to Shareholders': 5730.00,

    # Net Income
    'Net Income': 71.00,
}

# Read existing TD bank journal entries (income side)
je_df_original = pd.read_excel('A:/toocore/doc/td2024_journal_entries.xlsx', sheet_name='Journal Entries')
je_df_original['Date'] = pd.to_datetime(je_df_original['Date'])
je_df_original = je_df_original[je_df_original['Date'].dt.year == 2024].copy()
je_df_original['Debit'] = pd.to_numeric(je_df_original['Debit'], errors='coerce').fillna(0)
je_df_original['Credit'] = pd.to_numeric(je_df_original['Credit'], errors='coerce').fillna(0)

print("="*80)
print("GENERATING TAX RETURN MATCHED BOOKS (OPTION 3)")
print("="*80)
print("\nStarting with TD Bank income entries...")
print(f"Original JE lines: {len(je_df_original)}")

# Calculate actual revenue from TD bank
actual_revenue = je_df_original[je_df_original['Account'].str.contains('Revenue|Income', case=False, na=False)]['Credit'].sum()
print(f"TD Bank Revenue: ${actual_revenue:,.2f}")
print(f"UFile GIFI 8000 Revenue: ${UFILE_GIFI['Revenue']:,.2f}")
print(f"Difference (unrecorded income): ${UFILE_GIFI['Revenue'] - actual_revenue:,.2f}")

# Start building complete journal entries
journal_entries = []
entry_num = 1

# Helper function
def add_je(date, account, debit, credit, memo, receipt_required="", source=""):
    global entry_num
    journal_entries.append({
        'Entry #': entry_num,
        'Date': date,
        'Account': account,
        'Debit': debit if debit else '',
        'Credit': credit if credit else '',
        'Memo': memo,
        'Receipt Required': receipt_required,
        'Source Document': source,
    })

# ========== STEP 1: Copy TD Bank Income Entries (keep original Entry #s) ==========
print("\n[1] Copying TD Bank income transactions...")
for _, row in je_df_original.iterrows():
    add_je(
        row['Date'],
        row['Account'],
        row['Debit'],
        row['Credit'],
        row['Memo'],
        row['Review Required'] if 'Review Required' in row and pd.notna(row['Review Required']) else '',
        'TD Bank Statement'
    )
    # Increment only after full entry
    if _ < len(je_df_original) - 1:
        if je_df_original.iloc[_ + 1]['Entry #'] != row['Entry #']:
            entry_num += 1
    else:
        entry_num += 1

print(f"Copied {len(journal_entries)} lines from TD bank")

# ========== STEP 2: Adjusting Entry for Unrecorded Revenue ==========
revenue_diff = UFILE_GIFI['Revenue'] - actual_revenue
if abs(revenue_diff) > 0.01:
    print(f"\n[2] Adding adjusting entry for unrecorded revenue: ${revenue_diff:,.2f}")
    add_je(
        datetime(2024, 12, 31),
        'Accounts Receivable',
        revenue_diff,
        None,
        'Year-end revenue accrual adjustment',
        'REQUIRED: Match to invoices/receipts for unrecorded 2024 revenue',
        'UFile GIFI Adjustment'
    )
    add_je(
        datetime(2024, 12, 31),
        'Corporate Income - Adjustments',
        None,
        revenue_diff,
        'Year-end revenue accrual adjustment',
        'REQUIRED: Match to invoices/receipts for unrecorded 2024 revenue',
        'UFile GIFI Adjustment'
    )
    entry_num += 1

# ========== STEP 3: Cost of Goods Sold ==========
print(f"\n[3] Recording COGS: ${UFILE_GIFI['Cost of Goods Sold']:,.2f}")
add_je(
    datetime(2024, 12, 31),
    'Cost of Goods Sold',
    UFILE_GIFI['Cost of Goods Sold'],
    None,
    'COGS for 2024',
    'REQUIRED: Match to purchase invoices, inventory records',
    'Personal CC / Cash - TO RECONCILE'
)
add_je(
    datetime(2024, 12, 31),
    'Shareholder Loan Payable',
    None,
    UFILE_GIFI['Cost of Goods Sold'],
    'COGS paid from personal funds',
    'REQUIRED: Match to purchase invoices, inventory records',
    'Personal CC / Cash - TO RECONCILE'
)
entry_num += 1

# ========== STEP 4: Computer Hardware Asset ==========
print(f"\n[4] Recording Computer Hardware: ${UFILE_GIFI['Computer Hardware']:,.2f}")
add_je(
    datetime(2024, 12, 31),
    'Computer Hardware (Class 50)',
    UFILE_GIFI['Computer Hardware'],
    None,
    'Computer purchase 2024',
    'REQUIRED: Match to purchase invoice, include specs & date',
    'Personal CC - TO RECONCILE'
)
add_je(
    datetime(2024, 12, 31),
    'Shareholder Loan Payable',
    None,
    UFILE_GIFI['Computer Hardware'],
    'Computer paid from personal funds',
    'REQUIRED: Match to purchase invoice, include specs & date',
    'Personal CC - TO RECONCILE'
)
entry_num += 1

# ========== STEP 5: Operating Expenses (from personal CC) ==========
print(f"\n[5] Recording Operating Expenses from Personal CC...")

expenses = [
    ('Professional Fees', 'Professional Fees', 'REQUIRED: Match to invoices from accountant, lawyer, consultants'),
    ('Advertising and Promotion', 'Advertising and Promotion', 'REQUIRED: Match to online ads, marketing expenses'),
    ('Office Expenses', 'Office Expenses', 'REQUIRED: Match to office supplies, software subscriptions'),
    ('Telephone and Utilities', 'Telephone and Utilities', 'REQUIRED: Match to phone/internet bills with business %'),
    ('Meals and Entertainment', 'Meals and Entertainment (50% deductible)', 'REQUIRED: Match to receipts with business purpose notes'),
    ('Vehicle Expense', 'Vehicle Expense', 'REQUIRED: Match to gas, insurance, repairs, CCA. Need logbook for business %'),
    ('Repairs and Maintenance', 'Repairs and Maintenance', 'REQUIRED: Match to repair invoices'),
    ('Property Taxes', 'Property Taxes', 'REQUIRED: Match to property tax bills with business use %'),
    ('Miscellaneous', 'Miscellaneous Expenses', 'REQUIRED: Match to other business receipts'),
]

for gifi_name, account_name, receipt_note in expenses:
    amount = UFILE_GIFI[gifi_name]
    print(f"  - {account_name}: ${amount:,.2f}")
    add_je(
        datetime(2024, 12, 31),
        account_name,
        amount,
        None,
        f'{gifi_name} for 2024',
        receipt_note,
        'Personal CC - TO RECONCILE'
    )
    add_je(
        datetime(2024, 12, 31),
        'Shareholder Loan Payable',
        None,
        amount,
        f'{gifi_name} paid from personal funds',
        receipt_note,
        'Personal CC - TO RECONCILE'
    )
    entry_num += 1

# ========== STEP 6: Depreciation (non-cash) ==========
print(f"\n[6] Recording Depreciation: ${UFILE_GIFI['Depreciation (CCA)']:,.2f}")
add_je(
    datetime(2024, 12, 31),
    'Depreciation Expense (CCA)',
    UFILE_GIFI['Depreciation (CCA)'],
    None,
    'CCA for 2024 per Schedule 8',
    'Non-cash expense. Match to CCA schedule',
    'T2 Schedule 8'
)
add_je(
    datetime(2024, 12, 31),
    'Accumulated Depreciation',
    None,
    UFILE_GIFI['Depreciation (CCA)'],
    'CCA for 2024 per Schedule 8',
    'Non-cash expense. Match to CCA schedule',
    'T2 Schedule 8'
)
entry_num += 1

# ========== STEP 7: Accounts Payable Year-End ==========
if UFILE_GIFI['Accounts Payable'] > 0:
    print(f"\n[7] Recording Accounts Payable: ${UFILE_GIFI['Accounts Payable']:,.2f}")
    add_je(
        datetime(2024, 12, 31),
        'Operating Expenses - Accrued',
        UFILE_GIFI['Accounts Payable'],
        None,
        'Accrued expenses at year-end',
        'REQUIRED: Match to unpaid invoices as at Dec 31, 2024',
        'Year-end accrual'
    )
    add_je(
        datetime(2024, 12, 31),
        'Accounts Payable',
        None,
        UFILE_GIFI['Accounts Payable'],
        'Accrued expenses at year-end',
        'REQUIRED: Match to unpaid invoices as at Dec 31, 2024',
        'Year-end accrual'
    )
    entry_num += 1

print(f"\nTotal journal entries created: {entry_num - 1}")
print(f"Total journal lines: {len(journal_entries)}")

# Create DataFrame
je_df = pd.DataFrame(journal_entries)
je_df['Debit'] = pd.to_numeric(je_df['Debit'], errors='coerce').fillna(0)
je_df['Credit'] = pd.to_numeric(je_df['Credit'], errors='coerce').fillna(0)

# ========== GENERATE GENERAL LEDGER ==========
print("\nGenerating General Ledger...")
gl_data = []
for account in sorted(je_df['Account'].unique()):
    account_entries = je_df[je_df['Account'] == account].copy()
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
            'Balance': balance,
            'Receipt Required': row['Receipt Required'],
            'Source Document': row['Source Document']
        })

gl_df = pd.DataFrame(gl_data)

# ========== GENERATE TRIAL BALANCE WITH GIFI MAPPING ==========
print("Generating Trial Balance with GIFI codes...")

# GIFI mapping
GIFI_MAP = {
    # Revenue
    'Uber Revenue': ('8000', 'Revenue'),
    'Corporate Income - VentureLab': ('8000', 'Revenue'),
    'Corporate Income - Software Engineering': ('8000', 'Revenue'),
    'Corporate Income - Adjustments': ('8000', 'Revenue'),
    'Other Income - Bank Bonus': ('8000', 'Revenue'),
    'Other Income - Windfall': ('8000', 'Revenue'),

    # COGS
    'Cost of Goods Sold': ('8518', 'Cost of Goods Sold'),

    # Expenses
    'Professional Fees': ('8860', 'Professional Fees'),
    'Advertising and Promotion': ('8521', 'Advertising and Promotion'),
    'Office Expenses': ('8670', 'Office Expenses'),
    'Telephone and Utilities': ('9225', 'Telephone and Utilities'),
    'Meals and Entertainment (50% deductible)': ('9275', 'Meals and Entertainment'),
    'Vehicle Expense': ('9281', 'Vehicle Expense'),
    'Repairs and Maintenance': ('8710', 'Repairs and Maintenance'),
    'Property Taxes': ('8760', 'Property Taxes'),
    'Property Tax': ('8760', 'Property Taxes'),
    'Depreciation Expense (CCA)': ('8762', 'Depreciation (CCA)'),
    'Miscellaneous Expenses': ('9970', 'Miscellaneous'),
    'Bank Charges': ('9970', 'Miscellaneous'),
    'Utilities - Gas': ('9225', 'Telephone and Utilities'),
    'Utilities - Electricity': ('9225', 'Telephone and Utilities'),
    'Utilities - Water': ('9225', 'Telephone and Utilities'),
    'Operating Expenses - Accrued': ('9970', 'Miscellaneous'),

    # Assets
    'TD Business Chequing': ('1001', 'Cash'),
    'Computer Hardware (Class 50)': ('1741', 'Computer Hardware'),
    'HST Recoverable': ('1200', 'Other Assets'),
    'Accounts Receivable': ('1061', 'Accounts Receivable'),

    # Liabilities
    'HST Payable': ('2170', 'GST/HST Payable'),
    'Accounts Payable': ('2620', 'Accounts Payable'),
    'Shareholder Loan Payable': ('3640', 'Due to Shareholders'),
    'BMO Visa Payable': ('3640', 'Due to Shareholders'),
    'CIBC Visa Payable': ('3640', 'Due to Shareholders'),
    'AMEX Payable': ('3640', 'Due to Shareholders'),
    'MBNA Payable': ('3640', 'Due to Shareholders'),
    'National Bank MC Payable': ('3640', 'Due to Shareholders'),
    'PC Mastercard Payable': ('3640', 'Due to Shareholders'),
    'Canadian Tire MC Payable': ('3640', 'Due to Shareholders'),

    # Contra-asset
    'Accumulated Depreciation': ('1741', 'Computer Hardware (contra)'),
}

tb_data = []
for account in sorted(je_df['Account'].unique()):
    account_entries = je_df[je_df['Account'] == account]
    total_debit = account_entries['Debit'].sum()
    total_credit = account_entries['Credit'].sum()
    balance = total_debit - total_credit

    gifi_code, gifi_desc = GIFI_MAP.get(account, ('9999', 'Unmapped'))

    tb_data.append({
        'Account': account,
        'GIFI Code': gifi_code,
        'GIFI Description': gifi_desc,
        'Debit': total_debit,
        'Credit': total_credit,
        'Balance': balance
    })

tb_df = pd.DataFrame(tb_data)

# ========== GENERATE GIFI SUMMARY (matches UFile) ==========
print("Generating GIFI Summary...")

gifi_summary = tb_df.groupby(['GIFI Code', 'GIFI Description']).agg({
    'Balance': 'sum'
}).reset_index()

# Format for GIFI
gifi_data = []
for _, row in gifi_summary.iterrows():
    balance = row['Balance']
    # Revenue/liabilities are negative balance (credit), show as positive
    # Expenses/assets are positive balance (debit), show as positive
    if row['GIFI Code'].startswith('8') or row['GIFI Code'].startswith('9'):  # IS accounts
        if balance < 0:  # Revenue
            amount = -balance
        else:  # Expenses
            amount = balance
    else:  # BS accounts
        if balance < 0:  # Liabilities
            amount = -balance
        elif row['GIFI Description'] == 'Computer Hardware (contra)':
            amount = balance  # Keep negative for contra
        else:  # Assets
            amount = balance

    gifi_data.append({
        'GIFI Code': row['GIFI Code'],
        'GIFI Description': row['GIFI Description'],
        'Amount': amount
    })

gifi_df = pd.DataFrame(gifi_data).sort_values('GIFI Code')

# Calculate totals
revenue = gifi_df[gifi_df['GIFI Code'] == '8000']['Amount'].sum()
cogs = gifi_df[gifi_df['GIFI Code'] == '8518']['Amount'].sum()
gross_profit = revenue - cogs
expenses = gifi_df[gifi_df['GIFI Code'].str.startswith(('8', '9')) &
                    (gifi_df['GIFI Code'] != '8000') &
                    (gifi_df['GIFI Code'] != '8518')]['Amount'].sum()
net_income = gross_profit - expenses

# Add calculated rows
gifi_calc = pd.DataFrame([
    {'GIFI Code': '8299', 'GIFI Description': 'Gross Profit', 'Amount': gross_profit},
    {'GIFI Code': '9999', 'GIFI Description': 'Net Income', 'Amount': net_income},
])
gifi_df = pd.concat([gifi_df, gifi_calc]).sort_values('GIFI Code')

# ========== CHART OF ACCOUNTS ==========
coa_original = pd.read_excel('A:/toocore/doc/td2024_journal_entries.xlsx', sheet_name='Chart of Accounts')

# Add new accounts
new_accounts = [
    {'Account Code': '1061', 'Account Name': 'Accounts Receivable', 'Type': 'Asset'},
    {'Account Code': '1741', 'Account Name': 'Computer Hardware (Class 50)', 'Type': 'Asset'},
    {'Account Code': '1742', 'Account Name': 'Accumulated Depreciation', 'Type': 'Asset'},
    {'Account Code': '2620', 'Account Name': 'Accounts Payable', 'Type': 'Liability'},
    {'Account Code': '4400', 'Account Name': 'Corporate Income - Adjustments', 'Type': 'Revenue'},
    {'Account Code': '5100', 'Account Name': 'Cost of Goods Sold', 'Type': 'Expense'},
    {'Account Code': '6860', 'Account Name': 'Professional Fees', 'Type': 'Expense'},
    {'Account Code': '6521', 'Account Name': 'Advertising and Promotion', 'Type': 'Expense'},
    {'Account Code': '6670', 'Account Name': 'Office Expenses', 'Type': 'Expense'},
    {'Account Code': '6225', 'Account Name': 'Telephone and Utilities', 'Type': 'Expense'},
    {'Account Code': '6275', 'Account Name': 'Meals and Entertainment (50% deductible)', 'Type': 'Expense'},
    {'Account Code': '6281', 'Account Name': 'Vehicle Expense', 'Type': 'Expense'},
    {'Account Code': '6710', 'Account Name': 'Repairs and Maintenance', 'Type': 'Expense'},
    {'Account Code': '6760', 'Account Name': 'Property Taxes', 'Type': 'Expense'},
    {'Account Code': '6762', 'Account Name': 'Depreciation Expense (CCA)', 'Type': 'Expense'},
    {'Account Code': '6970', 'Account Name': 'Miscellaneous Expenses', 'Type': 'Expense'},
    {'Account Code': '6971', 'Account Name': 'Operating Expenses - Accrued', 'Type': 'Expense'},
]
coa_df = pd.concat([coa_original, pd.DataFrame(new_accounts)]).drop_duplicates()
coa_df['Account Code'] = coa_df['Account Code'].astype(str)
coa_df = coa_df.sort_values('Account Code')

# ========== WRITE TO EXCEL ==========
print("\nWriting to Excel...")
with pd.ExcelWriter('A:/toocore/doc/td2024_tax_package_FINAL.xlsx', engine='openpyxl') as writer:
    # GIFI Summary (matches UFile)
    gifi_df.to_excel(writer, sheet_name='GIFI Summary (T2)', index=False)

    # General Ledger
    gl_df.to_excel(writer, sheet_name='General Ledger', index=False)

    # Trial Balance with GIFI
    tb_df.to_excel(writer, sheet_name='Trial Balance', index=False)

    # Journal Entries
    je_df.to_excel(writer, sheet_name='Journal Entries', index=False)

    # Chart of Accounts
    coa_df.to_excel(writer, sheet_name='Chart of Accounts', index=False)

print("\n" + "="*80)
print("TAX RETURN MATCHED BOOKS GENERATED")
print("="*80)
print(f"File: td2024_tax_package_FINAL.xlsx")
print("")
print("VERIFICATION - Comparing to UFile GIFI:")
print("-"*80)
print(f"Revenue (8000):          UFile ${UFILE_GIFI['Revenue']:>12,.2f}  vs  Books ${revenue:>12,.2f}")
print(f"COGS (8518):             UFile ${UFILE_GIFI['Cost of Goods Sold']:>12,.2f}  vs  Books ${cogs:>12,.2f}")
print(f"Gross Profit:            UFile ${UFILE_GIFI['Revenue'] - UFILE_GIFI['Cost of Goods Sold']:>12,.2f}  vs  Books ${gross_profit:>12,.2f}")
print(f"Net Income (9999):       UFile ${UFILE_GIFI['Net Income']:>12,.2f}  vs  Books ${net_income:>12,.2f}")
print("")
print("RECEIPT MATCHING STATUS:")
print("-"*80)
total_receipts_needed = je_df[je_df['Receipt Required'].str.len() > 0].shape[0]
print(f"Journal lines requiring receipts: {total_receipts_needed}")
print("")
print("NEXT STEPS:")
print("1. Review 'Journal Entries' sheet - all placeholder entries marked")
print("2. Collect receipts for items marked 'Receipt Required'")
print("3. Update 'Source Document' column with actual receipt/invoice numbers")
print("4. Reconcile personal CC statements to expense entries")
print("5. Attach supporting documents to each journal entry")
print("="*80)
