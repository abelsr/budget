# Mexican card and instalment support

**Status:** ✅ 2026-08-16 · **Priority:** High · **Effort:** L · **Dependencies:**
transfers ✅, recurring transactions ✅, [19 — account reconciliation](19-conciliacion-de-cuentas.md) ✅,
[22 — cash-flow forecast](22-cash-flow-forecast.md) ✅

## Why

A credit card is the primary vehicle for large purchases in a Mexican
household. Today the app can record a card purchase, but it cannot express the
three questions that follow every card cycle:

1. **When is the cut (statement date)?** Reconciliation ([19]) against a card
   statement forces the user to remember which period the statement covers.
2. **When is payment due?** The forecast ([22]) projects the household balance
   from recurring rules, but a card payment is a transfer (cash → card) and
   transfers net to zero — the projection never warns that the household needs
   to move ~$X from cash to the card by the due date.
3. **How many interest-free instalments remain?** An MSI (meses sin intereses)
   purchase is spread over 3–24 monthly payments. As of today the plan exists
   only in the family's memory; the app has no way to show "4 of 6 paid, next
   due August 31".

The ledger semantics are already correct: a purchase is an expense on the card
account in the month of purchase (matching what the bank statement shows), and
paying the card is a transfer that does not pollute income/expense. What is
missing is the *calendar layer* over that ledger.

## Scope

- Per-card cycle metadata (statement day, days-to-payment-due) with derived
  next statement and payment dates, shown on the account.
- Card payment due dates and unpaid MSI instalment dates in the forecast
  `upcoming` list, as advisory liquidity events.
- In-app alerts ([20]) for the upcoming card payment due date and each unpaid
  MSI instalment due date.
- MSI plans: created from a card purchase, an advisory month-by-month schedule
  (never creates ledger movements), progress tracking, pause/resume, and
  cancel — with "record payment now" creating a normal cash → card transfer.
- Small reconciliation helper: derived statement period as a prefill for card
  account sessions.

Not in scope (see below): interest modelling, bank data, auto-matching
transfers to instalments, multi-currency.

## Design — backend

### Card cycle dates (`accounts`)

- Add two nullable columns to `accounts`:
  - `statement_day INTEGER CHECK (statement_day BETWEEN 1 AND 28)`
  - `payment_due_days INTEGER CHECK (payment_due_days BETWEEN 1 AND 60)`
- Both are only meaningful for `kind = 'credit'`. The API rejects them on any
  other kind (`422`) and `AccountOut` always returns `null` for non-credit
  accounts.
- **Derived, never stored** — a pure helper shared by the API, forecast, and
  alerts so the three can never drift (same lesson as the `account_balances.py`
  extraction in [22]):
  - `next_statement_date` = next occurrence of `statement_day` after today,
    using the anchor-day clamp already implemented in `advance()`
    (statement on the 31st: Jan 31 → Feb 28/29 → Mar 31).
  - `next_payment_due_date` = `next_statement_date + payment_due_days`.
- `AccountOut` gains `nextStatementDate` / `nextPaymentDueDate` (both `null`
  unless the two fields are set). Editing either field updates both derived
  dates immediately; no migration of derived state exists to stale.

### MSI plans (`instalment_plans`)

New table:

| Column | Type | Notes |
|---|---|---|
| `id` | String(32) PK | `new_id` |
| `household_id` | FK, indexed | |
| `account_id` | FK `accounts` | must be a **shared credit** account |
| `source_transaction_id` | FK `transactions` | the purchase: expense, on that account, not soft-deleted, not a transfer |
| `months` | Integer, 2–48 | |
| `monthly_amount` | Numeric(19,4) | `round(total / months, 4)` |
| `first_due_date` | Date | first instalment due date |
| `paid_count` | Integer, default 0 | |
| `status` | String | `active` \| `paused` \| `completed` \| `cancelled` |
| `created_by_id` | FK `users` | |
| `created_at` / `updated_at` | DateTime | |

Constraints and invariants:

- `UNIQUE (household_id, source_transaction_id)` — one plan per purchase.
- **Exact-sum rule:** the last instalment absorbs the rounding remainder,
  `final = total − (months − 1) × monthly_amount`, so instalments always sum
  to the purchase amount at four decimals. Example: $5,101 / 6 → 850.1667 × 5
  + 850.1665.
- **The schedule is derived, never stored.** The k-th due date is
  `first_due_date` advanced monthly with `advance(frequency='monthly',
  anchor_day=first_due_date.day)` — the same anchor-day rule as recurring
  rules. No stored rows means no drift and no catch-up bugs (lesson from 06).
- **Advisory, like goal plans ([21]):** the plan never creates a ledger
  movement. Payments are normal transactions the household records.
  - *Mark as paid* increments `paid_count`; at `paid_count == months` the
    status becomes `completed`.
  - *Record payment now* creates a standard cash → card **transfer**
    (`transfer_groups` pair, no category, excluded from income/expense/
    budgets/donut everywhere — the ledger-correct representation of paying a
    card) and then marks the instalment paid. Source account defaults to the
    household's main cash/debit account and is editable in the sheet.
- **Why not extend `recurring_rules`:** a rule materializes income/expense with
  a mandatory `category_id` (enforced by `ck_transactions_transfer_shape`),
  while MSI payments are transfers without a category. The dedicated table
  also carries the contract attributes (months, `paid_count`, link to the
  purchase) that a generic rule cannot express.

Guards:

- Deleting the source transaction while a plan is `active` or `paused` →
  `409` (cancel the plan first). Restore is unaffected.
- Editing the purchase amount (or type/account) while a plan is active → `409`
  with a "cancel and recreate the plan" detail: the contract changed and the
  plan is not silently recomputed.
- Deleting the card account while an active/paused plan exists → `409`
  (same pattern as deleting an account with transactions).
- Personal accounts are rejected: plans are a household planning feature and
  only shared cards qualify (same boundary as goals and budgets).
- `paid_count` advances by explicit user action only. No auto-matching of
  recorded transfers to instalments: matching is ambiguous and a wrong guess
  corrupts the plan's progress.

### Forecast integration ([22])

- **The balance series is unchanged.** A card payment is a transfer and nets
  to zero in the shared household balance, exactly as today's transfers do.
- `upcoming` (30-day window) gains two advisory event sources:
  - `card_due`: one per derived payment due date in the window, per credit
    account that has a cycle configured. `estimatedAmount` = outstanding
    `max(0, −card balance)`. The balance formula is not filtered by date, so
    inflow transfers already recorded to the card (e.g. a scheduled payment)
    reduce the estimate by construction — no separate deduction is made.
    Label: `Pago tarjeta {name}`.
  - `instalment_due`: the next unpaid due date of each active plan in the
    window, with the instalment amount (last instalment uses the remainder).
  - Both are liquidity events: they tell the household how much it must move,
    not how much household cash will change. The UI renders them with the
    existing signed-amount treatment.

### Alerts integration ([20])

Two new kinds on the existing lazy, idempotent pass (no scheduler):

| Kind | Fires | Dedupe key |
|---|---|---|
| `card_payment_due` | 3 days before a derived payment due date, with the estimated outstanding amount | `card_due:{account_id}:{due_date}` |
| `instalment_due` | 3 days before each unpaid instalment due date of an active plan | `instalment_due:{plan_id}:{due_date}` |

- Paused plans emit no alerts; `completed`/`cancelled` emit nothing.
- The unique `(household_id, dedupe_key)` constraint and household isolation
  rules are reused as-is. The 3-day lead is a named constant for v1.

### Reconciliation helper (small)

For a credit account with `statement_day` set, the reconciliation form
prefills `statement_date` with the last derived statement date and shows the
derived period (previous cut → next cut) as a hint. The user still enters the
real `statement_balance` from the bank; nothing is computed on its behalf.

## Design — frontend

- **Account form:** for kind = credit, an optional "Card cycle" section —
  statement day (1–28) and days-to-payment-due (default 20). The card widget
  and account detail show `Corte: 15 · Pago: 05` plus the next payment date
  when both are set.
- **Transaction detail (a card purchase):** a "Set up MSI plan" action opens a
  sheet with months (2–48) and first due date (default: next derived payment
  date, or purchase date + 1 month when no cycle is configured), with the
  monthly amount and the remainder-on-last instalment computed live.
- **Plan badge on the purchase:** `MSI · $850 × 6 · 3 pagados · próx. 31 ago`
  opening the plan sheet: progress, the derived schedule with paid/pending
  state, and the actions *Marcar pagado* / *Registrar pago ahora* (creates the
  transfer) / *Pausar* / *Cancelar*.
- **Dashboard forecast card:** `card_due` and `instalment_due` events render
  in the existing upcoming list (4 items + "N más" overflow); no new chart.
- **Alerts sheet:** the two new kinds link to the account (cycle) or the plan.
- All amounts honor the balance-concealment toggle (masked values,
  figure-free `aria-label`); Spanish copy; mobile-first sheets; mutations
  invalidate accounts, forecast, and alerts queries.

## Out of scope

- **Interest / minimum-payment / cash-advance modelling.** The outstanding
  estimate comes from the card's own ledger balance. If the household pays
  only the minimum or incurs interest, it records what actually happened; the
  app does not model bank charges.
- **Bank data aggregation** (already deferred at roadmap level).
- **Auto-matching** recorded transfers to MSI instalments.
- **Multi-currency and cross-card instalments** (paying an MSI from another
  card).
- Zero-based budgeting.

## Acceptance criteria

- A credit account with `statement_day=15`, `payment_due_days=20` returns both
  derived dates in `AccountOut`; a non-credit account rejects the fields with
  `422` and always returns `null`; clearing either field clears both derived
  dates.
- Derived dates cross months with the anchor-day clamp: statement on the 31st
  yields Feb 28/29 (leap-year aware) between Jan 31 and Mar 31.
- A card with balance −$12,000 and a payment due date inside the window adds
  a `card_due` `upcoming` event of ≈ $12,000 (reduced by already-recorded
  future inflows to the card); the forecast balance series is byte-identical
  to the pre-feature one for the same inputs.
- `card_payment_due` is created exactly once per account per due date under
  concurrent reads (unique dedupe key), is visible from 3 days before the due
  date, and marking it read never re-creates it for that key.
- A $5,100 purchase on a card, 6 months → `monthly_amount` 850.0000 and six
  due dates following the anchor-day clamp; $5,101 / 6 → 850.1667 × 5 +
  850.1665, summing exactly to the purchase.
- "Record payment now" creates a valid `transfer_groups` pair (no category,
  excluded from income/expense/donut/budgets/summary) and advances the plan
  progress; at `paid_count == months` the plan is `completed` and emits no
  further events.
- Pausing suppresses alerts and `upcoming` events without moving any calendar
  date; resuming re-enables them.
- Deleting the purchase (active plan) → 409; deleting the card account (active
  plan) → 409; editing the purchase amount (active plan) → 409 with the
  cancel-and-recreate instruction.
- One plan per purchase (`409` on a second attempt); personal accounts are
  rejected; all endpoints and events are household-isolated.
- Backend tests cover: derived-date math (including the 31st and leap years),
  instalment sum exactness, schedule derivation, alert idempotency and lead
  time, forecast inclusion with the series-unchanged invariant, all guards
  above, and isolation. Frontend production build and lint pass.

## Open questions

1. **Default `payment_due_days`:** a single default of 20 (typical in MX),
   recommended, versus per-bank presets (20/25/…). The field is always
   editable per card either way.
2. **`card_due` when the payment source is a personal account:** a payment out
   of a personal account *does* reduce shared household cash. v1 keeps the
   series shared-account-only and the events advisory; revisiting would mean
   surfacing a per-account liquidity view, which is a separate feature.

## Effort

L (3–5 days): one migration (`accounts` columns + `instalment_plans`), the
pure date/schedule helpers, plan CRUD + guards, forecast and alert integration,
three frontend sheets plus the badge, and the test set above.
