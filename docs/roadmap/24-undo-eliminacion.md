# Undo for delete and quick entry

**Status:** ✅ 2026-08-16 · **Priority:** Medium · **Effort:** S–M ·
**Dependencies:** none (the soft-delete infrastructure already exists from
[19 — reconciliation](19-conciliacion-de-cuentas.md) and the CSV import work)

Promoted from [A6 in the feature proposals](18-features-y-uiux-propuestas.md).

## Why

The design guidelines promise *agency*: "easy undo, confirmations only for
destructive actions". Today the only destructive path is a two-step confirm
and then it is gone forever — a hard delete with no recovery. The quick-entry
flow is designed to take under 10 seconds, which makes it the most
mistake-prone flow in the app (wrong amount, wrong account, duplicate
re-entry), and a mistake can only be fixed by deleting and re-entering.

The soft-delete infrastructure already exists and is battle-tested:
`transactions.deleted_at` / `delete_reason`, every normal read, aggregate,
attachment, and idempotency lookup already filters `deleted_at IS NULL`, and
import batch revert/restore already implements the full soft-delete → restore
cycle. Manual deletion is the one destructive path that still bypasses it.

## Scope

- Manual deletion of one-off transactions and transfers becomes a soft delete
  (`delete_reason = 'manual'`); a transfer soft-deletes its two rows together.
- `POST /transactions/{id}/restore` restores manually soft-deleted rows.
- A snackbar with "Deshacer" (8 s) after delete and after quick entry.
- Housekeeping: hard purge of soft-deleted rows older than 30 days, including
  their splits, edit events, and MinIO attachment objects — run lazily, no
  scheduler.
- The two-step confirm stays; undo complements it, it does not replace it.

Not in scope: undo for categories, accounts, budgets, goals, or invitations;
a "trash" UI listing soft-deleted rows; configurable retention.

## Design — backend

### Delete

`DELETE /transactions/{id}` keeps its current guards (imported rows → `409`)
and changes only the mechanics:

- **One-off transaction:** set `deleted_at = now()` and
  `delete_reason = 'manual'` instead of `db.delete`.
- **Transfer:** set both `deleted_at` and `delete_reason` on the two rows of
  the group (same timestamp) instead of deleting the rows and the group.
  The `transfer_groups` row is **kept**: it holds the `client_id`, so a
  replay of that client id keeps hitting the existing `409` guard instead of
  silently creating a second transfer.
- `invalidate_completed_reconciliation` is called exactly as it is today for
  hard deletes.

### Restore

`POST /transactions/{id}/restore` → `TransactionOut`:

- `404` when the row is not soft-deleted (or not visible to the household —
  isolation is enforced through the same access helpers as every other
  endpoint).
- `409` when `delete_reason == 'import_revert'`: import rows are restored
  through the batch flow only, which preserves batch counters and baselines.
- Clears `deleted_at` / `delete_reason`; for a transfer, restores **both**
  rows atomically.
- Calls `invalidate_completed_reconciliation`: a session that completed while
  the row was gone must become stale again, same rule as import restore.

No other schema change: the columns, the unique constraints, and every
`deleted_at IS NULL` filter already exist (audit-verified across
`transactions`, `accounts`, `budgets`, `summary`, `reports`, `forecast`,
`alerts`, and `reconciliation`).

### Client-id idempotency — unchanged

A replay of a `client_id` whose row is soft-deleted already returns `409`
("El clientId ya se usó con una transacción revertida"). That behavior is
kept as-is: the client id of a manually soft-deleted row can never be reused,
exactly like an import-reverted row. The outbox must therefore treat the
delete + undo of a synced entry as "the client id is consumed" — which is the
correct semantics for a financial ledger.

### Housekeeping purge

`purge_old_deletes(db)` — new service function, no schema change:

- Candidates: `deleted_at < now() − 30 days` (30 days is a named constant).
- For each candidate, in one transaction per row group: delete edit events,
  split rows, attachment rows, then the transaction row; delete the MinIO
  objects with the existing idempotent `delete_attachment`.
- Runs **lazily inside the `materialize_due` pass** (the same "no scheduler in
  self-hosted" philosophy as recurring materialization and alert generation),
  at most **once per day per process** via a module-level timestamp guard.
- A purge failure is logged and skipped — it must never break a read
  endpoint. The pass is idempotent by construction.
- Applies to both reasons (`manual` and `import_revert`): an import-reverted
  row keeps its provenance in the batch metadata (`import_rows` baselines),
  so the transaction row itself can be purged.

## Design — frontend

- New `components/ui/snackbar.tsx`: small, fixed bottom, auto-dismiss at 8 s,
  one action button, `aria-live="polite"`, spring enter/exit consistent with
  the existing sheets. No amount is shown in the copy, so the balance
  concealment toggle needs no special handling.
- **After a successful delete:** "Movimiento eliminado — Deshacer". The
  action calls `restore` (via the normal mutation path), then invalidates the
  transactions, accounts, summary, budgets, forecast, and alerts queries.
- **After a successful quick entry** (one-off or transfer):
  "Movimiento creado — Deshacer". The action deletes the created row through
  the same delete flow (i.e. the undo lands in the same snackbar pattern).
- **Offline outbox:** undo of an entry that is still pending in the outbox
  discards the outbox item locally (no server call, client id never sent).
  Undo of a synced entry uses the restore endpoint. The snackbar is offered
  in both cases; only the mechanism differs.
- The two-step confirm for delete is unchanged.

## Acceptance criteria

- Deleting a one-off transaction sets `deleted_at` / `delete_reason='manual'`;
  the row disappears from list, detail (404), summary, budgets, forecast,
  reports, and reconciliation; account balances recompute.
- Deleting a transfer soft-deletes both rows with the same timestamp, keeps
  the group row, and reverts both account balances; the transfer is
  invisible everywhere.
- Restore (endpoint and snackbar) returns the row to full visibility and all
  aggregates agree with the pre-delete state, including for transfers.
- `restore` on a non-deleted row → 404; on an import-reverted row → 409;
  household isolation → 404 for another household's row.
- A reconciliation session that completed while the row was soft-deleted is
  invalidated (stale) when the row is restored.
- Replaying the client id of a manually soft-deleted row → 409 (no behavior
  change from today's guard).
- Offline: undo of a pending outbox entry re-adds it locally without any
  server call; undo of a synced entry calls restore.
- Purge: rows deleted more than 30 days ago are hard-deleted with their
  splits, edit events, attachment rows, and MinIO objects; younger rows are
  untouched; the pass runs at most once per day per process, is idempotent,
  and a failing purge never breaks a read endpoint.
- Tests cover: delete/restore round-trip (one-off and transfer), all guards,
  client-id replay, reconciliation invalidation, purge with time travel, and
  isolation. Frontend lint and production build pass.

## Open questions

1. **Retention configurability:** v1 hard-codes 30 days as a constant;
   exposing an env var is trivial later if a household wants a longer window.
2. **Undo for other entities** (categories, accounts, budgets, goals,
   invitations): deliberately out of scope; revisit only if manual
   transactions prove the pattern first.

## Effort

S–M (1–2 days): the backend is mostly rewiring the existing delete path, the
restore endpoint, and the purge pass; the frontend is one small component and
two call sites.
