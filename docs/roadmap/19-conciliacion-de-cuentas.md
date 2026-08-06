# Account reconciliation

**Status:** ⬜ Pending · **Priority:** High · **Effort:** M · **Dependencies:**
[08 — CSV import](08-importacion-csv.md)

## Why

Manual capture and statement imports are only useful when a household can
confirm that the account ledger agrees with the bank. Reconciliation turns a
calculated balance into a verifiable one and exposes missing or duplicated
movements before they compromise reports and budgets.

## Product decision

The first release uses transaction states, not immutable locks. A transaction
is `pending` or `reconciled`; an account reconciliation session records the
statement date and expected closing balance. Users may still edit a reconciled
transaction, but the application must flag the affected session as stale and
show that it needs review. Hard locking and a formal audit log are deferred
until the workflow proves necessary.

Transactions created by an import remain editable too. Their immutable import
source snapshot and an edit-history event preserve provenance; no workflow
blocks the user merely because a movement originated in a statement file.

## Scope

- Reconcile one accessible account against a statement balance and date.
- Mark individual transactions as reconciled from the account ledger.
- Show pending total, reconciled total, expected statement balance, and the
  remaining difference while a session is open.
- Complete a session only when its reconciled balance equals the supplied
  statement balance.
- Mark a completed session stale if an included transaction is edited, deleted,
  soft-deleted, moved to another account, or reversed.
- Personal-account visibility rules remain unchanged: only its owner can view
  or reconcile it; shared-account reconciliation remains visible to eligible
  household members.

## Non-goals

- Locking transactions after reconciliation.
- Automatic bank synchronization or matching transactions to a bank feed.
- Reconciliation of an account that does not retain a transaction ledger.

## Proposed design

### Data model

- Add `transactions.reconciliation_status` with `pending` as the default and
  nullable `reconciled_at`.
- Add `reconciliation_sessions`: `id`, `account_id`, `household_id`,
  `statement_date`, `statement_balance`, `status` (`open`, `completed`,
  `stale`), `completed_at`, `created_by_id`, and timestamps.
- Add a relation from reconciled transactions to their completed session. A
  transaction belongs to at most one completed session. Transfer sides remain
  independent: each one is reconciled from its own account statement.
- Store immutable import source snapshots and minimal append-only edit-history
  events independently of reconciliation. A complete, cross-entity audit ledger
  remains deferred. Editing or soft-deleting an included transaction changes a
  completed session to `stale`; it does not erase the import provenance.

### API

- `POST /accounts/{account_id}/reconciliations` creates an open session with a
  statement date and balance.
- `GET /accounts/{account_id}/reconciliations/{id}` returns the session,
  account totals, included transactions, and current difference.
- `POST /transactions/{id}/reconciliation` marks or unmarks a movement while
  validating account access and the active session.
- `POST /accounts/{account_id}/reconciliations/{id}/complete` completes only
  when the difference is zero.

### UI

- The account ledger exposes a reconciliation entry point, statement balance
  input, pending/reconciled toggle, difference, and completion state.
- A stale session has an explicit warning and a review action; it never
  silently reports the account as reconciled.

## Acceptance criteria

- [ ] A user can reconcile a shared or owned personal account to a supplied
  statement balance without seeing inaccessible accounts or transactions.
- [ ] A session cannot complete while the calculated difference is non-zero.
- [ ] Editing a transaction in a completed session marks that session stale.
- [ ] The debit and credit sides of a transfer can be reconciled independently.
- [ ] Tests cover account visibility, arithmetic, session completion, stale
  invalidation, and transfer behavior.
