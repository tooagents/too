import pandas as pd
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime

# Read source data
df = pd.read_excel('A:/toocore/doc/td2024.xlsx')

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

# Process each transaction
for idx, row in df.iterrows():
    date = row['Date']
    desc = row['Description']
    debit = row['Debit'] if pd.notna(row['Debit']) else None
    credit = row['Credit'] if pd.notna(row['Credit']) else None

    # Skip opening entry
    if 'OPEN ACCOUNT' in desc:
        continue

    # Uber Holdings C MSP - Revenue with HST
    if 'Uber Holdings C MSP' in desc:
        revenue, hst = split_hst(credit, True)
        add_entry(date, 'TD Business Chequing', credit, None, desc, "")
        add_entry(date, 'Uber Revenue', None, revenue, desc, "")
        add_entry(date, 'HST Payable', None, hst, desc, "")
        entry_num += 1

    # VENTURELAB INNO MSP - Corporate Income with HST
    elif 'VENTURELAB INNO MSP' in desc:
        revenue, hst = split_hst(credit, True)
        add_entry(date, 'TD Business Chequing', credit, None, desc, "")
        add_entry(date, 'Corporate Income - VentureLab', None, revenue, desc, "")
        add_entry(date, 'HST Payable', None, hst, desc, "")
        entry_num += 1

    # E-TRANSFER received
    elif 'E-TRANSFER' in desc and credit:
        if credit == 5.00 or credit == 400.00:
            # Shareholder contribution
            add_entry(date, 'TD Business Chequing', credit, None, desc, "Personal funds deposited")
            add_entry(date, 'Shareholder Loan Payable', None, credit, desc, "Personal funds deposited")
            entry_num += 1
        elif credit == 2260.00:
            # Software engineering revenue with HST
            revenue, hst = split_hst(credit, True)
            add_entry(date, 'TD Business Chequing', credit, None, desc, "")
            add_entry(date, 'Corporate Income - Software Engineering', None, revenue, desc, "")
            add_entry(date, 'HST Payable', None, hst, desc, "")
            entry_num += 1

    # SEND E-TFR - Owner draw
    elif 'SEND E-TFR' in desc:
        add_entry(date, 'Shareholder Loan Payable', debit, None, desc, "Owner draw")
        add_entry(date, 'TD Business Chequing', None, debit, desc, "Owner draw")
        entry_num += 1

    # TFR-FR - Transfer FROM personal (shareholder loan)
    elif 'TFR-FR' in desc:
        add_entry(date, 'TD Business Chequing', credit, None, desc, "Transfer from personal")
        add_entry(date, 'Shareholder Loan Payable', None, credit, desc, "Transfer from personal")
        entry_num += 1

    # TFR-TO - Transfer TO personal (shareholder loan)
    elif 'TFR-TO' in desc:
        add_entry(date, 'Shareholder Loan Payable', debit, None, desc, "Transfer to personal")
        add_entry(date, 'TD Business Chequing', None, debit, desc, "Transfer to personal")
        entry_num += 1

    # Tangerine MSP - Small windfall amounts
    elif 'Tangerine MSP' in desc and credit:
        add_entry(date, 'TD Business Chequing', credit, None, desc, "")
        add_entry(date, 'Other Income - Windfall', None, credit, desc, "")
        entry_num += 1

    # Tangerine FTD - Transfer to personal savings
    elif 'Tangerine FTD' in desc:
        add_entry(date, 'Shareholder Loan Payable', debit, None, desc, "Transfer to personal savings")
        add_entry(date, 'TD Business Chequing', None, debit, desc, "Transfer to personal savings")
        entry_num += 1

    # Tangerine INV - Transfer from personal savings
    elif 'Tangerine INV' in desc:
        add_entry(date, 'TD Business Chequing', credit, None, desc, "Transfer from personal savings")
        add_entry(date, 'Shareholder Loan Payable', None, credit, desc, "Transfer from personal savings")
        entry_num += 1

    # BMO VISA - Credit card payment
    elif 'BMO VISA' in desc:
        add_entry(date, 'BMO Visa Payable', debit, None, desc, "Personal card payment")
        add_entry(date, 'TD Business Chequing', None, debit, desc, "Personal card payment")
        entry_num += 1

    # CIBC VISA - Credit card payment
    elif 'CIBC VISA' in desc:
        add_entry(date, 'CIBC Visa Payable', debit, None, desc, "Personal card payment")
        add_entry(date, 'TD Business Chequing', None, debit, desc, "Personal card payment")
        entry_num += 1

    # AMEX FTD - Credit card payment
    elif 'AMEX FTD' in desc:
        add_entry(date, 'AMEX Payable', debit, None, desc, "Personal card payment")
        add_entry(date, 'TD Business Chequing', None, debit, desc, "Personal card payment")
        entry_num += 1

    # MBNA MSP - Credit card payment
    elif 'MBNA MSP' in desc:
        add_entry(date, 'MBNA Payable', debit, None, desc, "Personal card payment")
        add_entry(date, 'TD Business Chequing', None, debit, desc, "Personal card payment")
        entry_num += 1

    # NATL BANK MC - Credit card payment
    elif 'NATL BANK MC' in desc:
        add_entry(date, 'National Bank MC Payable', debit, None, desc, "Personal card payment")
        add_entry(date, 'TD Business Chequing', None, debit, desc, "Personal card payment")
        entry_num += 1

    # PC MASTRCRD - Credit card payment
    elif 'PC MASTRCRD' in desc:
        add_entry(date, 'PC Mastercard Payable', debit, None, desc, "Personal card payment")
        add_entry(date, 'TD Business Chequing', None, debit, desc, "Personal card payment")
        entry_num += 1

    # CAN TIRE MC - Credit card payment
    elif 'CAN TIRE MC' in desc:
        add_entry(date, 'Canadian Tire MC Payable', debit, None, desc, "Personal card payment")
        add_entry(date, 'TD Business Chequing', None, debit, desc, "Personal card payment")
        entry_num += 1

    # Enbridge Gas - Utility with HST
    elif 'Enbridge Gas' in desc:
        expense, hst = split_hst(debit, True)
        add_entry(date, 'Utilities - Gas', expense, None, desc, "")
        add_entry(date, 'HST Recoverable', hst, None, desc, "")
        add_entry(date, 'TD Business Chequing', None, debit, desc, "")
        entry_num += 1

    # ALECTRA UTIL - Electricity with HST
    elif 'ALECTRA UTIL' in desc:
        expense, hst = split_hst(debit, True)
        add_entry(date, 'Utilities - Electricity', expense, None, desc, "")
        add_entry(date, 'HST Recoverable', hst, None, desc, "")
        add_entry(date, 'TD Business Chequing', None, debit, desc, "")
        entry_num += 1

    # RHill Water - Water utility with HST
    elif 'RHill Water' in desc:
        expense, hst = split_hst(debit, True)
        add_entry(date, 'Utilities - Water', expense, None, desc, "")
        add_entry(date, 'HST Recoverable', hst, None, desc, "")
        add_entry(date, 'TD Business Chequing', None, debit, desc, "")
        entry_num += 1

    # TOR-Tax - Property tax (no HST)
    elif 'TOR-Tax' in desc:
        add_entry(date, 'Property Tax', debit, None, desc, "")
        add_entry(date, 'TD Business Chequing', None, debit, desc, "")
        entry_num += 1

    # MONTHLY PLAN FEE - Bank charges with HST
    elif 'MONTHLY PLAN FEE' in desc:
        expense, hst = split_hst(debit, True)
        add_entry(date, 'Bank Charges', expense, None, desc, "")
        add_entry(date, 'HST Recoverable', hst, None, desc, "")
        add_entry(date, 'TD Business Chequing', None, debit, desc, "")
        entry_num += 1

    # SBB Offer - Bank bonus
    elif 'SBB Offer' in desc:
        add_entry(date, 'TD Business Chequing', credit, None, desc, "")
        add_entry(date, 'Other Income - Bank Bonus', None, credit, desc, "")
        entry_num += 1

    # TD ATM DEP - VentureLab cheque deposit (treated as corporate income)
    elif 'TD ATM DEP' in desc:
        revenue, hst = split_hst(credit, True)
        add_entry(date, 'TD Business Chequing', credit, None, desc, "VentureLab cheque deposit")
        add_entry(date, 'Corporate Income - VentureLab', None, revenue, desc, "VentureLab cheque deposit")
        add_entry(date, 'HST Payable', None, hst, desc, "VentureLab cheque deposit")
        entry_num += 1

# Create DataFrame
je_df = pd.DataFrame(journal_entries)

# Create Chart of Accounts
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

# Write to Excel
with pd.ExcelWriter('A:/toocore/doc/td2024_journal_entries.xlsx', engine='openpyxl') as writer:
    je_df.to_excel(writer, sheet_name='Journal Entries', index=False)
    coa_df.to_excel(writer, sheet_name='Chart of Accounts', index=False)

print("Journal entries created successfully!")
print(f"Total entries: {entry_num - 1}")
print(f"Total journal lines: {len(journal_entries)}")
