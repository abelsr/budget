# 💡 Feature & UI/UX proposals — beyond the current roadmap

**Status:** 🗣 Proposal · **Author:** opencode + abel · **Last updated:** 2026-08-05

This file collects the features and UI/UX work discussed in the chat. Each
item follows the roadmap convention (why, scope, design, acceptance criteria)
so it can be promoted to its own `docs/roadmap/XX-*.md` file and implemented
the moment it is approved.

## Product direction

The product is not aiming to reproduce a managed banking aggregator. Its
competitive position is a **private, self-hosted, collaborative household
ledger** for Spanish-speaking families, with fast mobile capture and ownership
of their financial data. This favors correctness, importability, planning, and
privacy over feature breadth.

The next implementations must follow this dependency order:

1. Transfers between accounts (A1).
2. CSV statement import ([08](08-importacion-csv.md)), adapted to preserve
   import provenance and idempotency.
3. Account reconciliation.
4. Merchant normalization and categorization rules.
5. Split transactions.
6. Monthly budgets with optional rollover (A2).
7. Alerts (A5) and a cash-flow calendar/forecast.
8. Dated, planned savings goals.
9. Mexican credit-card statement dates, due dates, and months-without-interest
   instalments.

Do not prioritize bank aggregation or generative financial advice until the
ledger can correctly represent transfers, imported movements, merchants, and
reconciled balances. Do not make zero-based budgeting the default experience;
evaluate it later as an advanced opt-in mode.

**Context.** The current roadmap (see `docs/roadmap/README.md`) already covers
PWA (03), CSV import (08), filters/search (09), profile/password (10), savings
goals (11), personal accounts (12), offline-first (13), multi-family (14), and
monitoring (17). The proposals below fill gaps that are
**not** in that roadmap, plus the UI/UX batch the user asked about.

---

## Batch A — Core data features (recommended first)

### A1. Transfers between accounts

**Why.** Moving money between accounts (cash → card, card → savings) is a
daily action for a family. Today there is no way to express it: any record is
either income or expense, so a transfer pollutes the income/expense reports
and the donut. This is the biggest functional gap in the app.

**Scope.**
- New `type = "transfer"` on `transactions`; `category_id` becomes nullable.
- Transfers excluded from income/expense/donut everywhere; still reflected in
  account balances (one account up, one down) and in the ledger.
- Transfer persisted as **two linked transactions**, one debit in the source
  account and one credit in the destination account. The UI presents them as
  one action, while each account retains a complete independently reconcilable
  ledger.

**Design — backend.**
- `transfer_groups` stores the household, creation metadata, and optional
  future transfer-level attributes such as a fee or exchange-rate context.
- `transactions`:
  - `category_id` becomes nullable for transfer rows (migration + data-safe:
    existing rows untouched);
  - a nullable `transfer_group_id` references `transfer_groups` and links the
    two sides;
  - both rows have `type = 'transfer'`, opposite signed balance effects, no
    category, and distinct account IDs;
  - create, update, and delete always operate on the group atomically. The
    service validates that a group has exactly two rows with equal amounts.
- Balance computation (`opening_balance + inflows − outflows`) gains:
  - outflows include source account transfers;
  - inflows include destination account transfers.
- `GET /transactions` filters `type == 'transfer'` by default in the ledger
  but with a `includeTransfers` param; summary endpoints (`/summary`,
  `/budgets/status`) ignore transfers for income/expense math.
- Balance sheet for a household stays consistent: total across accounts is
  unchanged by a transfer.

**Design — frontend.**
- Quick entry: a "Transfer" mode (from account, to account, amount, date,
  optional note). Shown as a segmented control: Expense / Income / Transfer.
- Ledger rows show `→ account` for transfers; detail sheet shows both ends.
  Each account's ledger includes its own side so it can later be reconciled
  against that account's statement.
- Transfer never offers a category picker.

**Acceptance criteria.**
- Moving $500 cash → savings updates both balances and changes neither
  income, expense, nor the donut.
- Each account ledger shows one side; the all-accounts view groups the linked
  pair as one transfer action.
- Summary/dashboard totals ignore transfers; total household balance is
  invariant under a transfer.
- Deleting a transfer reverses both balances.
- Tests: transfer validation, balance math, summary exclusion, isolation.

**Effort:** M (1–3 days). **Risk:** the balance queries and summary endpoints
are touched everywhere — audit every place that sums `income − expense`
before closing (same risk class as 12-personal-accounts, but smaller). The
group-and-pair invariant must be database-backed where possible and covered by
transactional tests.

---

### A2. Monthly budgets with optional rollover — ✅ 2026-08-08

**Why.** Today `budgets` is a single global limit per category (a fixed
amount, spend recalculated each month). Real families budget per month, and
many like unused money to roll into the next month (or not). The current
model cannot express either.

**Scope.**
- Budgets become per-month, with the current global row kept as a fallback
  default for months without an explicit entry.
- A `rollover` flag per budget: unspent balance carries into the next month.
- The traffic-light progress bars and donut badge keep working, now per month.

**Design — backend.**
- `budgets`: add `month DATE NULL` (NULL = global default) and `rollover
  BOOL default FALSE`. Unique constraint becomes
  `(household_id, category_id, month)` with NULLs allowed (Postgres treats
  NULLs as distinct, so enforce the global-once rule in the service).
- `GET /budgets/status?month=YYYY-MM`:
  - effective limit per category = explicit row for the month, else global;
  - with `rollover`, available = limit + `max(0, limit − spent_prev)` from
    the previous month's surplus;
  - spent and % computed as today.
- Decision recommended: **default rollover OFF** (reset each month), matching
  the "traffic light is about this month" mental model. Rollover is opt-in
  per budget.

**Design — frontend.**
- Budget form sheet gains a month picker (defaults to current) and a
  "carry surplus to next month" toggle.
- Dashboard bars label the month and, when rollover is on, show available vs
  spent (e.g. "$6,000 disponibles · $3,200 gastados").
- Editing a past month's budget is allowed (audit view).

**Acceptance criteria.**
- A budget defined without a month still applies to all months (backwards
  compatible).
- A budget with rollover carries unused money; without it, resets.
- Bars/badge reflect the selected month.
- Tests: explicit-over-global precedence, rollover math, no rollover default.

**Effort:** M. **Risk:** the existing `Budget` rows keep working unchanged;
the migration only adds columns.

---

### A3. Reports and trends

**Why.** The dashboard answers "how is *this* month going?" but nothing asks
"are we spending more than last quarter?" or "what did the year look like?".
Without trends the app describes the present but not the direction.

**Scope.**
- A new `/informes` (Reports) page: month-over-month income/expense/net bars,
  a 12-month area/line view, and a category breakdown over a chosen range.
- Month/range selector; all charts follow the validated palette and hover
  tooltips in `design-guidelines.md §4`.

**Design — backend.**
- New endpoint `GET /summary/range?from=YYYY-MM-DD&to=YYYY-MM-DD` returning:
  - per-month totals `[{month, income, expense, net}]`;
  - category breakdown for the range `[{categoryId, name, color, total}]`;
  - daily series for a single-month view.
- Reuses the existing summary logic; transfers excluded.

**Design — frontend.**
- New page + nav entry. Recharts (already a dependency): grouped bars for
  income vs expense, a line for net, donut/bars for category mix.
- Empty state and skeleton loading consistent with the rest of the app.

**Acceptance criteria.**
- Selecting a 6-month range renders 6 correct monthly bars.
- Category breakdown sums to expense for the range.
- Charts pass the §4 rules (no dual axis, legend present, hover tooltips).
- Tests: range summary math, month boundaries.

**Effort:** M. **Risk:** low; mostly new read paths.

---

### A4. Data export (CSV / household)

**Why.** Self-hosting means the family owns the data — they should be able to
leave (or just back up) without the dev running `pg_dump`. A one-click CSV of
transactions is the minimum, and it doubles as a human-readable audit.

**Scope.**
- `GET /export/transactions.csv`: all household transactions (or filtered by
  the same params as the list), streaming, UTF-8 with BOM so Excel opens it
  correctly.
- Optional full-household export (transactions + accounts + categories +
  budgets + recurring rules as a JSON blob).

**Design — backend.**
- Streaming `StreamingResponse` with `text/csv`; columns: date, type, amount,
  category, account, member, note, recurring flag, attachments.
- Respect the same permission model as the list endpoint.

**Design — frontend.**
- Buttons in Settings (and/or the Reports page): "Export CSV", "Export full
  JSON".

**Acceptance criteria.**
- The CSV opens in Excel/Sheets with correct accented characters and numbers.
- Export reflects only the current household's data.
- Tests: header row, row count, BOM, isolation.

**Effort:** S–M. **Risk:** none.

---

### A5. In-app alerts (budget overrun, overdue rules, goal reached, negative balance)

**Why.** Budgets and goals only inform when the user opens the right screen.
A budget that silently ran out at 80% loses its point. Alerts turn the app
from a ledger into a small safety net.

**Scope.**
- `alerts` table + endpoint; bell icon with unread badge in the nav; alerts
  sheet listing them, each opening the relevant screen.
- Alert kinds: budget ≥ 100% (and ≥ 75% once), recurring rule overdue (> N
  days past `next_run_date`), account balance negative, savings goal reached.
- Generated lazily on read (same philosophy as recurring materialization: no
  scheduler in self-hosted). Idempotent — an alert is created once.

**Design — backend.**
- `alerts`: `id`, `household_id`, `user_id NULL` (NULL = household-wide),
  `kind`, `message`, `payload` (JSON: e.g. category id), `transaction_id
  NULL`, `read_at NULL`, `created_at`, unique key on
  `(kind, household_id, period)` to avoid duplicates.
- `GET /alerts` computes pending ones and stores them in one pass, then
  returns the list; `POST /alerts/read` marks all (or one) as read.
- Budget alert de-duplicated per `(category, month)`.

**Design — frontend.**
- Bell `IconButton` with a red count badge; sheet with grouped alerts; tapping
  an alert navigates (e.g. to the budget edit, the transaction, the goal).
- Marking read on open.

**Acceptance criteria.**
- A category over its monthly budget produces exactly one alert that does not
  re-appear after being read.
- An overdue recurring rule surfaces an alert with a "generate now" action.
- Tests: generation idempotency, read/unread, isolation, each kind.

**Effort:** M. **Risk:** the lazy generation must be a single code path
(concurrent requests → duplicates), same lesson as recurring (06).

---

### A6. Undo for delete and quick entry

**Why.** The design guidelines promise *agency* ("easy undo"). Today the only
destructive path is a two-step confirm and then it's gone forever. A short
"Deshacer" window after delete (and after a mistaken quick entry) matches the
interaction language of the app.

**Scope.**
- Soft delete on `transactions` (`deleted_at` and `delete_reason`), restore endpoint, and a
  toast/snackbar with "Deshacer" after delete and after quick entry.
- Hard purge of soft-deleted rows after 30 days (housekeeping).

**Design — backend.**
- `transactions.deleted_at NULL` and `delete_reason NULL`; all list/detail/summary queries add
  `deleted_at IS NULL`.
- Import batch reverts use the same mechanism with
  `delete_reason = 'import_revert'`, rather than hard-deleting financial
  history or generating compensating movements.
- `POST /transactions/{id}/restore` sets it back to NULL (only if it was
  soft-deleted).
- Housekeeping in the lazy-materialization pass (or entrypoint) deletes rows
  with `deleted_at < now() − 30d` (and their attachments from MinIO).

**Design — frontend.**
- After delete: snackbar "Movimiento eliminado — Deshacer" (8s); the two-step
  confirm stays.
- After creating from quick entry: "Movimiento creado — Deshacer" reverts by
  deleting the created row (also soft).

**Acceptance criteria.**
- Deleting then tapping Deshacer restores the transaction and its balances.
- A restored transaction is invisible to nothing: list, dashboard, budgets all
  agree.
- Purged rows (past 30d) and their attachments are gone from DB and MinIO.
- Tests: soft-delete visibility, restore, purge.

**Effort:** S–M. **Risk:** the `deleted_at IS NULL` filter must be added to
*every* transaction read — grep-audit before closing (same as A1).

---

## Batch B — UI/UX (what the user asked for)

### B1. Account card widgets (credit/debit look)

**Why.** Accounts are just rows with a name and balance. The household uses
real cards; showing them as cards gives the "where is the money" screen
immediate recognition, uses the brand-blue gradient correctly, and makes the
dashboard feel like a product instead of a table.

**Scope.**
- `accounts` gains optional cosmetic fields: `bank` (string), `last_four`
  (string), `card_brand` (`visa | mastercard | amex | other | null`).
- Accounts page and dashboard hero render card-like widgets for
  debit/credit/savings accounts with `last_four`; cash and accounts without
  `last_four` keep the list-row / chip treatment.

**Design — backend.**
- Migration adds 3 nullable columns; `AccountOut` includes them.
- No behavioural change — pure metadata. Edit allowed through the existing
  account form.

**Design — frontend.**
- `components/AccountCard.tsx`: gradient surface derived from the account
  brand or the account's own colour; card chip, masked number (`•••• 4321`),
  brand mark, name, balance with `.tnum`. On the brand system: the hero card
  is the only blue surface on the dashboard — the widgets use the account's
  colour at low saturation or the dark navy card, not `--primary` (keeps
  §8 "one hero" rule intact).
- Accounts page: a horizontally scrollable row of card widgets; edit opens the
  existing `AccountFormSheet` with the new fields.
- Fields are optional and hidden behind a small "card details" section so a
  user who only has cash is not forced to fill them.

**Acceptance criteria.**
- A debit account with `last_four` renders as a card widget; a cash account
  without it keeps today's treatment.
- Fields persist through edit; no account breaks if they are all empty.
- The dashboard hero still has exactly one blue surface.
- Tests: schema round-trip, absent fields fine.

**Effort:** M. **Risk:** styling only; the hero-card rule in §8 must be
respected.

---

### B2. Bank and merchant logos

**Why.** Rows gain identity. A transaction whose note contains "Walmart" or
"SAM'S" showing the merchant's mark makes scanning a list much faster than
reading every note; the same applies to banks on account cards. Fully
self-hosted: no external logo CDN, no third-party tracking.

**Scope.**
- A curated, offline brand registry in the frontend:
  - **Merchants** (a few dozen common ones in the family's reality: Walmart,
    Sam's Club, Costco, OXXO, Amazon, Netflix, Spotify, Telcel, CFE, etc.):
    normalized name patterns → { brand color, Lucide icon, letter monogram }.
  - **Banks** (MX context, currency is MXN): BBVA, Banorte, Santander, HSBC,
    Banco Azteca, Nu, etc. → { color, monogram / simplified glyph }.
- Unknown merchants fall back to the existing category icon medallion — the
  registry is an *enhancement layer*, never a blocker.

**Design — backend.**
- No schema change needed: merchant recognition is purely frontend, from the
  transaction `note` (normalized: lowercase, strip accents). Bank comes from
  the new `accounts.bank` field (B1).

**Design — frontend.**
- `lib/brands.ts`: `{ pattern, name, color, icon }` tables + `matchMerchant(note)`
  and `matchBank(bank)` helpers returning a `BrandMatch | null`.
- `components/BrandMedallion.tsx`: used in transaction rows (replaces the
  category icon when a merchant matches) and in account card widgets (bank
  mark).
- Colors come from a fixed brand palette **registered in `index.css` tokens**
  or resolved via `lib/brands.ts` with documented light/dark steps — following
  §11, brand colors are the one place a component may know a hex, but they
  must live in a single module, never inline.

**Acceptance criteria.**
- "compra en walmart" → Walmart mark; "sams" → Sam's Club mark; unknown note →
  category medallion (no regression).
- Works offline (no network requests for logos).
- Bank on an account card shows the bank mark.
- Registry is data-only: adding a merchant is one table row.

**Effort:** S–M. **Risk:** low; must not regress the category-icon path.

---

### B3. Quick polish tied to the batch (small)

- Transactions list: merchant name gets slightly more weight than metadata so
  the new medallion reads (already the §8 recent-rows rule).
- Account detail: a mini card widget preview before saving in the form sheet.
- Dashboard hero: keep as-is (one hero, §8) — the card widgets live on
  Accounts and as a compact rail on the dashboard if and only if they don't
  compete with the hero.

---

## Suggested order

1. **A1 Transfers** — the biggest data gap; everything else aggregates on top.
2. **A6 Undo** — cheap, high UX value, teaches the `deleted_at` pattern.
3. **A2 Monthly budgets + rollover** — extends the already-shipped budgets.
4. **B1 Card widgets + B2 Logos** — the UI/UX batch; both touch the account
   and transaction rows, so doing them together avoids two passes.
5. **A3 Reports** — reads the summary paths hardened by A1.
6. **A5 Alerts** — rides on budgets/goals/recurring that already exist.
7. **A4 Export** — quick win, can slot in anywhere after A1.

The unblocked roadmap items (09 filters/search, 10 profile/password, 03 PWA)
remain small and can interleave — none of the batches above conflict with
them.

---

## Questions for the user

1. **Transfers:** single-line (one ledger row, my recommendation) vs
   two-row double entry? Single-line is simpler and matches "one movement,
   one line" today.
2. **Rollover default:** off (reset monthly) or on? I recommend **off**.
3. **Card widgets:** also on the dashboard, or only on the Accounts screen?
4. **Logos:** OK with a curated self-hosted registry (SVG/monogram + color)
   instead of pulling real brand logos? Real logos mean licensing and a CDN.
5. **Export scope:** CSV of transactions only, or also the full-household JSON?
