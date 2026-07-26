# 🔁 Recurring transactions

**Status:** ✅ Done 2026-07-25 · **Priority:** High · **Effort:** M (1-3 days) · **Dependencies:** None

## Why
Rent, salary and subscriptions are the backbone of family finances, and capturing them by hand every month is the #1 day-to-day friction. The `recurring_rules` table already exists in the schema — it's just missing being exposed and materialized.

## Scope
**Includes:**
- CRUD for recurring rules scoped by household.
- Materialization of pending transactions (lazy, on read).
- "Repeat" option in the entry sheet.
- Section to list/pause/delete rules.

**Doesn't include:**
- Additional frequencies (biweekly, yearly, custom).
- Retroactive editing of already-generated transactions.
- "A transaction was generated" notifications.

## Proposed design
### Backend
- `/recurring-rules` endpoints: `GET` (household list), `POST` (create), `PATCH /{id}` (pause/edit `amount`, `note`, `active`), `DELETE /{id}`. All filtered by `household_id`.
- **Lazy** materialization (recommended decision for a self-hosted MVP, no scheduler): when `GET /transactions` is called, before responding, generate the pending transactions for `active` rules with `next_run_date <= today` and advance `next_run_date`.
  - `weekly`: `+7 days`.
  - `monthly`: same day of the following month, being careful with short months (e.g. January 31 → February 28/29, using the last day of the month if the day doesn't exist).
  - A single rule can materialize several overdue occurrences in one pass (loop until `next_run_date > today`).
- **Avoiding duplicates**: advancing `next_run_date` and the insert happen in the same DB transaction; being lazy and idempotent by date, re-reading doesn't duplicate.
- **Proposed decision**: add a nullable `recurring_rule_id` to `transactions` to support the frontend badge and future traceability. Manual transactions stay `NULL`.
- Document in the endpoint why lazy and not a job: in self-hosted there's no guaranteed scheduler; lazy guarantees consistency without extra infra.
### Frontend
- In the quick entry sheet: a "Repeat" selector with **No repeat / Weekly / Monthly** options. If a frequency is chosen, the rule is created (with `next_run_date` = transaction date + frequency) and the current transaction becomes the first occurrence.
- "Recurring" section in Settings (or in Transactions): list of rules with amount, category, frequency and next date; pause/resume and delete actions.
- Subtle badge ("Recurring") on generated transactions, visible in the list and in the detail sheet, using `recurring_rule_id`.
### Infra
- No changes (the table already exists; only a minor migration if `recurring_rule_id` is added to `transactions`).

## Acceptance criteria
- [x] Creating a monthly rule with `next_run_date` in the past → the materialized transaction appears when loading Transactions.
- [x] Reloading or calling `GET /transactions` again doesn't duplicate the generated transactions.
- [x] Pausing a rule (`active=false`) stops future materializations; reactivating it resumes them from the correct date.
- [x] Deleting a rule doesn't delete the already-generated transactions.
- [x] A monthly rule on the 31st materializes correctly in February (last day of the month).
- [x] Tests: materialization, non-duplication, short months, pausing. (65 tests pass + 9 migration tests.)

## Notes
- Risk: lazy materialization in `GET /transactions` adds work to a hot endpoint; if it grows, move it to a dedicated `POST /recurring-rules/materialize` endpoint called when the app opens.
- Open decision: if the user edits a rule (e.g. changes the amount), does it affect only future occurrences? Proposal: yes, never retroactive.

## How it turned out (2026-07-25)

Implemented with four deviations from the design above, all due to problems that
came up while writing it.

1. **Materializes in three endpoints, not one.** The Dashboard is the entry
   screen and it fires `/accounts`, `/transactions` and `/summary/month` **in
   parallel**: hooking only the transactions one left the balance and the summary
   out of sync on the first load after a rule came due. The service is
   idempotent, so calling it from all three is safe; `GET
   /recurring-rules` also calls it, otherwise the screen would show a "next
   date" already in the past.
2. **Anchor day stored on the rule** (`anchor_day`). The design said "January 31
   → February 28", but storing the 28 in `next_run_date` meant March started
   from there and rent moved to the 28th **forever**. With the anchor, the
   real sequence is Jan 31 → Feb 28 → Mar 31 → Apr 30 → May 31 → Jun 30.
3. **`repeat` in `POST /transactions`** instead of two calls from the
   frontend. It creates the transaction and the linked rule in a single atomic
   operation; in two steps, if the second one fails you end up with an orphaned
   transaction or a rule without a first occurrence.
4. **`created_by_id` on the rule.** `transactions.member_id` is NOT NULL, and
   attributing what was generated to whoever happened to open the app would make
   the same expense change member depending on who logged in first.

**How non-duplication is guaranteed.** Reading overdue rules uses
`SELECT ... FOR UPDATE`, and the insert and the advance of `next_run_date` are in
the same DB transaction. If two requests arrive together, the second one blocks;
once released, Postgres re-evaluates the `WHERE` against the already-updated row,
the rule no longer qualifies and it exits without generating anything. Verified with 8
concurrent requests against real Postgres 17: 4 occurrences, zero duplicates. In SQLite
— the tests — `FOR UPDATE` isn't rendered, but there's no concurrency there.

**Pause/resume semantics.** The criteria said "resuming it resumes them from the
correct date" without defining which one. **Jumping forward** was chosen:
whoever turned off the rule in March doesn't want four months of rent to hit
when they turn it on in July. Resuming a rule that hasn't come due doesn't move its date.

**Backlog cap.** `next_run_date` can't be more than a year in the past (422).
Without a cap, a date from years ago would materialize hundreds of transactions
on the first read.

**PATCH only touches `amount`, `note` and `active`.** Changing category, account or
frequency is a different rule: better to delete and create than to rewrite history.

Deleting a rule unlinks its transactions (`recurring_rule_id` set to
NULL) instead of deleting them: that's money that moved. They lose the badge, which is the
only information that goes away.
