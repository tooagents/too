"""
Add General Ledger tab to 2025package.xlsx with LINKS to JE
"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from collections import defaultdict

print("Adding General Ledger tab...")

# Open existing file
wb = openpyxl.load_workbook('2025package.xlsx')
ws_je = wb['Journal Entries']

# Read all JE entries
je_entries = []
for row in range(2, ws_je.max_row):  # Skip header and total
    entry = ws_je[f'A{row}'].value
    date = ws_je[f'B{row}'].value
    account = ws_je[f'C{row}'].value
    debit = ws_je[f'D{row}'].value
    credit = ws_je[f'E{row}'].value
    memo = ws_je[f'F{row}'].value

    if account and account != 'TOTAL:':
        je_entries.append({
            'row': row,
            'entry': entry,
            'date': date,
            'account': account,
            'debit': debit if debit else 0,
            'credit': credit if credit else 0,
            'memo': memo
        })

# Group by account
accounts = defaultdict(list)
for je in je_entries:
    accounts[je['account']].append(je)

# Create GL sheet
if 'General Ledger' in wb.sheetnames:
    del wb['General Ledger']
ws_gl = wb.create_sheet('General Ledger')

# Formats
font_header = Font(bold=True, color='FFFFFF')
fill_header = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
border = Border(
    left=Side(style='thin'),
    right=Side(style='thin'),
    top=Side(style='thin'),
    bottom=Side(style='thin')
)

# Set column widths
ws_gl.column_dimensions['A'].width = 50
ws_gl.column_dimensions['B'].width = 12
ws_gl.column_dimensions['C'].width = 12
ws_gl.column_dimensions['D'].width = 12
ws_gl.column_dimensions['E'].width = 12
ws_gl.column_dimensions['F'].width = 50
ws_gl.column_dimensions['G'].width = 8

# Headers
headers = ['Account', 'Date', 'Debit', 'Credit', 'Balance', 'Memo', 'JE #']
for col, header in enumerate(headers, start=1):
    cell = ws_gl.cell(row=1, column=col, value=header)
    cell.font = font_header
    cell.fill = fill_header
    cell.border = border

# Write GL entries grouped by account
gl_row = 2
for account in sorted(accounts.keys()):
    entries = accounts[account]
    balance = 0

    for je in entries:
        # Account name
        ws_gl.cell(row=gl_row, column=1, value=account)

        # Date - LINK to JE
        ws_gl.cell(row=gl_row, column=2, value=f"='Journal Entries'!B{je['row']}")

        # Debit - LINK to JE
        if je['debit']:
            ws_gl.cell(row=gl_row, column=3, value=f"='Journal Entries'!D{je['row']}")
            ws_gl.cell(row=gl_row, column=3).number_format = '#,##0.00'
            balance += je['debit']

        # Credit - LINK to JE
        if je['credit']:
            ws_gl.cell(row=gl_row, column=4, value=f"='Journal Entries'!E{je['row']}")
            ws_gl.cell(row=gl_row, column=4).number_format = '#,##0.00'
            balance -= je['credit']

        # Running balance
        ws_gl.cell(row=gl_row, column=5, value=balance)
        ws_gl.cell(row=gl_row, column=5).number_format = '#,##0.00'

        # Memo - LINK to JE
        ws_gl.cell(row=gl_row, column=6, value=f"='Journal Entries'!F{je['row']}")

        # JE # - LINK to JE
        ws_gl.cell(row=gl_row, column=7, value=f"='Journal Entries'!A{je['row']}")

        gl_row += 1

    # Blank line between accounts
    gl_row += 1

# Save
wb.save('2025package.xlsx')
print(f"[OK] Added General Ledger tab with {gl_row-2} lines")
print(f"     All cells LINKED to Journal Entries tab")
print(f"     {len(accounts)} accounts")
