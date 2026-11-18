# Conversation Log — 2025 T2 Defensible Books (Review & Rebuild)

**Date:** 2026-06-30
**Project:** Review the 2025 corporate books, audit expense categories for credibility, and rebuild a defensible T2 filing package.
**Outcome:** New defensible package produced. Tax top-up of **$2,432.63** owing to CRA. All figures reconciled to bank + filed GST return.

**Key deliverables (in `doc/2025/corponly/basedonfixed/`):**
- `2025_T2_DEFENSIBLE.xlsx` — the books (Journal Entries, Trial Balance, Income Statement, Balance Sheet, GIFI 100/125)
- `2025_T2_FILING_MEMO.md` — one-page filing memo
- `build_defensible_package.py` — regenerates the workbook
- This log

---

## Starting point

- Prior session (logged in `../../CONVERSATION_LOG_2025_Books.md`) had built books to justify a **$2,620.43** CRA tax instalment (RC0001), using reverse-engineered expenses of ~$33,101 to hit net income $21,479 → tax $2,620.43.
- User flagged: bank statements (`../../bankraw/`) are the only source of truth; `fixed_donotchange/` files are settled and not to be changed; `basedonfixed/2025package.xlsx` was the latest middle-way.
- `fixed_donotchange/fixed_number.md` fixed income at $61,675.60 and a "first-stage shareholder loan" of $51,074.92.

## What we verified early

- The `fixed_donotchange` journal entries balanced (Dr=Cr $163,614.85), net income $21,478.94, tax **$2,620.43 exact**.
- Income $61,675.60 traced to raw bank statements (DATAMOND e-transfers + mobile cheques + Uber + small Interac). Real.
- Clarified: $51,074.92 was a cash-flow figure (bank in − out, adjusted for opening balance + contributions), **not** the GL shareholder loan balance.

## The pivot — expense credibility audit

User asked for an audit of expense **categories** from the viewpoint of the real business: **solo IT consultant (one client, DATAMOND, paid by e-transfer, work-from-home) + part-year Uber Eats driver.**

Findings that drove the rebuild:
1. **60% expense ratio** ($33,101 / $54,580) is too high for a low-overhead solo consultant.
2. **Home block (~$6,444)** booked at ~100% — a corporation cannot deduct 100% of the owner's *personal* home costs. Must be prorated to business-use %. Water heater (~$2,226) is a **personal capital cost**, not a corporate repair.
3. **Vehicle + travel (~$11k)** vs only ~$4k Uber revenue — disproportionate; vehicle and "business travel" overlapped (double-count risk).
4. **Subcontractor $2,680** — would require a T4A; user confirmed **no one was paid** → removed.
5. **Advertising $2,156** — one client by e-transfer, nothing to advertise → removed.

## User's answers that set the defensible numbers

- Home: **owned**, business use **~20%**.
- Insurance line was **auto** insurance → folded into vehicle pool.
- Vehicle: Uber had a **mileage log**; since Uber revenue was only ~$4k, vehicle brought down to a normal level. Agreed **50% business use** of the $8,085 pool (gas/maint/lease $6,928.41 + auto insurance $1,156.78).
- **Business travel = real air travel to NY** → kept, separate from vehicle.
- **Subcontractor = none** → removed.
- Cloud/software (AWS + Azure + subs) = **$1,361.28** (real).
- Meals = **$729.22 total** spend → 50% = $364.61.
- User AGREED to the principle: build expenses from what's documentable, accept the higher tax, and **pay the difference to CRA voluntarily** rather than risk reassessment.

## The GST / Quick Method discovery (major)

User provided the **filed GST return** as a hard source of truth:
- Line 101 (tax-included sales) = **$62,971**; Line 109/115 remitted/paid = **$5,241.43**; ITCs (Line 106) = $0.
- Effective HST rate ~8.3%, not 13% → because GST was filed under the **Quick Method**.

True revenue breakdown (user-confirmed, ties to GST return exactly):
- DATAMOND: $52,200.00 net + $6,786.00 HST
- Uber: $3,754.27 net + $230.50 HST
- **Net revenue $55,954.27 + HST charged $7,016.50 = $62,970.77** (= Line 101). Quick Method check: $62,971 × 8.8% − $300 = $5,241.43 ✓.

**Quick Method spread is taxable income.** User pushed back (thought regular method would net the same, so why add the spread). Verified online (CRA RC4058 + **Canadian Tax Foundation** article): the spread between HST collected and HST remitted **is taxable** (CRA basis: ITA 248(16)/12(1)(x)). The offset is that expenses are deducted **GST-included** (no ITCs) — both halves required, can't take only the favourable one. Our books already book expenses gross, so treatment is consistent.
- Spread = $7,016.50 − $5,241.43 = **$1,775.07** → added to revenue.
- **T2 revenue = $55,954.27 + $1,775.07 = $57,729.34.**

Decision: T2 revenue uses **GST truth** (overrides bank), so T2 and GST agree on revenue (no cross-match risk).

## Reconciliation — closed to the penny

GST Line 101 $62,970.77 = DATAMOND $58,986.00 + Uber $3,984.77 (100% corporate; **no employee/third-party amount** — an earlier theory of an "employee amount" was wrong and was retracted).

Bank-to-GST bridge:
- Bank income (as classified) $61,675.60
- **− WQ360 $3,000.00**: same-day in/out pass-through from user's own account 6210446 (the same account that sent the $936.05 shareholder contribution) — **not a client, not income**.
- **− Uber $450.83**: reimbursement of personal grocery funds spent on deliveries — **not income** (and the grocery purchase is not a corporate expense). Net zero.
- **+ DATAMOND A/R $4,746.00**: ~2 invoices invoiced in 2025, received in 2026 → **Accounts Receivable** at Dec 31.
- = **$62,970.77** = GST Line 101 exactly.

(Bank DATAMOND receipts were exactly 24 × $2,260; billing schedule had ~26 invoices → the unpaid ones are the year-end ones.)

## Final numbers (in `2025_T2_DEFENSIBLE.xlsx`)

| Item | Amount |
|---|---|
| Sales net of HST | $55,954.27 |
| Quick Method spread (taxable) | $1,775.07 |
| **Total revenue** | **$57,729.34** |
| Total expenses (gross/GST-incl) | $16,310.79 |
| **Net income** | **$41,418.55** |
| Tax @ 12.2% | $5,053.06 |
| Already paid (RC0001) | ($2,620.43) |
| **Top-up owing to CRA** | **$2,432.63** |
| Accounts Receivable (Dec 31) | $4,746.00 |
| Shareholder loan — due from shareholder | $35,809.63 |

Defensible expense set (GIFI / amount):
9281 Motor vehicle (50%) 4,042.59 · 8670 CCA 3,560.28 · 9200 NY travel 2,967.65 · 8811 Cloud/software 1,361.28 · 8860 Professional+legal 1,778.81 · 9210 Training 763.33 · 9225 Telephone/internet 447.41 · 9180 Property tax (20%) 217.85 · 9220 Utilities (20%) 396.27 · 8960 Repairs (20%, water heater excl) 229.42 · 8523 Meals (50%) 364.61 · 8714 Bank charges 181.29 → **Total 16,310.79**.

Integrity: Trial balance Dr=Cr **$71,896.14**; Balance sheet check **$0.00**; cash ending **$4,566.05** (TD 631.42 + BMO 3,932.68 + ML 1.95, matches bank).

## Decisions / rationale to remember

- **Revenue source of truth = filed GST return**, not bank (bank understated due to A/R and overstated due to pass-throughs).
- **Quick Method spread IS taxable** — confirmed via CRA/CTF, not assumed.
- **Home at 20%**, water heater excluded as personal capital; the % barely moves tax (~$77 between 15–30%), so kept conservative 20%.
- **Vehicle at 50%** of $8,085 pool — proportionate to ~$4k Uber, logbook-backed.
- **WQ360 and Uber reimbursement excluded** as non-income pass-throughs.
- **GST return left as filed** — correct, reconciles to T2, no amendment.
- **`fixed_donotchange/` never modified.**

## Open / to-do before filing

1. Insert the corporation's **legal name** in the memo header.
2. Confirm the **50% vehicle** figure against the actual mileage log (and total car costs if recomputing).
3. **Remit $2,432.63** to CRA (2025 income tax, RC0001).
4. **Repay $35,809.63** shareholder loan by **Dec 31, 2026** (s.15(2)); user plans July 2026.
5. 2026 onward: clear shareholder withdrawals via an **annual dividend + T5**; keep corporate/personal accounts separate; no pass-throughs through business accounts.

## Caveats

- These figures assume the user can produce the supporting records listed in the memo §7 (especially the mileage log and NY trip receipts). The numbers are defensible *if documented*; the risk lives in documentation, not the arithmetic.
- This is bookkeeping/tax-preparation support, not professional tax advice; a CPA should review before filing given the amounts and the s.15(2) exposure.
