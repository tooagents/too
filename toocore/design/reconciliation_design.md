# Bank Statement Reconciliation — Design

_Recorded 2026-09-07. Design intent + rationale for how bank-statement reconciliation
should work. This is the "why"; treat it as the spec the code should converge to._

## Who this is for

A small-business owner / one-person company. They do **not** keep formal books or
think in ledgers and trial balances. They think in **documents**:

- Money-in → **invoices** they sent: _"did this get paid?"_
- Money-out → **bills / receipts** they owe: _"did I pay this?"_

So reconciliation is **not** a books-vs-bank audit. It is: _attach each real bank line
to the document it belongs to, so the owner can see which documents are settled._
The bank statement is the **evidence**; the document is the **thing they care about**.

## Purpose

The formal purpose of reconciliation has two directions:

1. **"Is every dollar the bank saw explained?"** — YES, we keep this. Every bank line
   must be attributable (an invoice, a bill/receipt, a transfer, etc.). Nothing
   unexplained sitting in the account.
2. **"Does every dollar in our books exist at the bank?"** — DROP this. It only matters
   if you keep double-entry books, which this user does not. There is no ledger to
   reconcile back against.

What replaces direction (2) for this user: **"is every invoice paid / every bill paid?"**
— answered document-first, driven off whether a bank line is attached.

## Core model

Reconciliation is a direct link:

```
bank_txn  <-->  document   (document = invoice today; bills/receipts later)
```

- **Work is bank-line-first:** the owner sits with "here's what hit my account this
  month — what was each one?" and attaches each line to a document.
- **Payoff is document-first:** the useful views are "unpaid invoices", "unpaid bills",
  and "bank lines not yet attached to anything".
- **Store the match once (the link); derive both views from it.** Do not maintain two
  independently-set flags that can drift.

### Reconciliation vs. payment status — two layers

- **Layer 1 — Reconciliation (source of truth):** the `bank_txn ↔ invoice` link + the
  reconciled state. This is invoice-level and authoritative.
- **Layer 2 — Payment (side-work):** `invoice_payment` rows / `inv_payment_status` are
  the money view. They may be written as a side effect of reconciling, but they are
  **not** the reconciliation record.

For this user, **"reconciled" ≈ "really paid"**, and the bank is the source of truth for
it. They won't diligently record manual payments, so an invoice is paid *because the
deposit showed up*. Matching a deposit to an unpaid invoice **is** the act of marking it
paid — payment status becomes a *result* of reconciliation, not a separate thing to
maintain.

## Current implementation (what exists as of this note)

The link today runs entirely through payments:

```
bank_txn  →  invoice_payment (bank_txn_id)  →  invoice (inv_id)
```

- `reconcile_deposit` creates one `invoice_payment` row per invoice, stamped with
  `bank_txn_id`. That payment row **is** the only reconciliation record.
- `o_bank_txn.is_reconciled` exists (deposit-level, set true only when fully applied by
  amount). The **invoice has no reconcile state at all**.
- Candidate invoices are selected by `_still_owes` = `inv_balance_due > 0` (payment axis).

### The core defect

Candidacy is gated on **payment status** (`balance > 0`), not **reconcile status**. So a
**paid-but-unreconciled** invoice is never a candidate — you cannot attach a real deposit
to an invoice that's already marked paid, and there is no "just match, no money moved"
path. The thing that should be side-work (payments) is currently the only source of truth,
and the invoice — where the truth should live — holds nothing.

## Target design

1. **Move the truth to the invoice level.** Add `invoice.is_reconciled` and a link to the
   deposit. Candidate pool becomes `!is_reconciled` (minus void/cancelled), independent of
   balance owed. This fixes the core defect: paid, partial, and unpaid invoices are all
   matchable; fully-reconciled ones drop out.
2. **Reconcile sets the link + flags first (truth); payment write is optional side-work.**
   "Just match" a fully-paid invoice = link only, touch nothing in payments.
3. **Payment status logic is untouched** — `recalculate_invoice_payment_summary` keeps
   owning `inv_payment_status` and never writes `is_reconciled`. The two axes stay clean.
4. **Worklists:** unpaid invoices (AR), unpaid bills/receipts (AP, later), and unattached
   bank lines. AI + human both pick from `!is_reconciled`.

### Cardinality

- **One deposit → many invoices:** real (e.g. Stripe/PayPal batch payout). Must be
  supported. A single FK on the invoice (`invoice.reconciled_bank_txn_id`, many invoices
  pointing at one deposit) covers this.
- **One invoice → many deposits** (installments): rare for this user. Skip for now; would
  need a join table `(bank_txn_id, inv_id, applied_amount)` if it becomes real.

### Amounts — the deposit is reconciled only when fully explained

Reconciliation's purpose is "every dollar the bank saw is explained," so a **deposit is
reconciled only when its full amount is attributed** to invoices. A partially-applied
deposit still has unexplained money → it stays **not reconciled** (shows the unapplied
remainder). This is amount-aware at the deposit level; a bare match is NOT enough for the
deposit flag.

**Amounts are backend-owned; the client sends only the matched invoice ids.** Reconcile
is a match. On save the backend spreads the deposit FIFO across the matched invoices,
keeping two amounts distinct per invoice:

- **attribution** — how much of the deposit this invoice *explains* (its balance owing,
  or its full total if already paid). Drives the deposit's "fully explained" flag.
- **payment** — how much to actually pay down: only the outstanding balance. Written as
  an `invoice_payment`, then the existing payment logic derives paid/partial.

This keeps the two cases correct without double-paying: an **unpaid** invoice gets a
payment = the deposit amount (up to its balance); an **already-paid** invoice is a "just
match" — linked, and it explains the deposit, but **no** payment is written (so
`paid_total` is never inflated). The frontend never computes or sends amounts; any per-row
"will apply" it shows is a display-only preview.

## Guiding principle

Build "attach bank lines to documents; paid/unpaid falls out." Do **not** build a
dual-axis, double-entry reconciliation engine. Simpler, and closer to how the owner
actually thinks.
