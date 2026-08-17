# Undo for Delete and Quick Entry Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers/executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement roadmap doc 24 — manual deletions become reversible (soft delete + restore), quick entry and delete get an 8-second "Deshacer" snackbar, and old soft-deleted rows are purged lazily after 30 days.

**Architecture:** Reuses the existing soft-delete infrastructure (`deleted_at` / `delete_reason` + every `deleted_at IS NULL` filter, already in place from the CSV import work). Manual delete sets `delete_reason='manual'` instead of hard-deleting; a transfer soft-deletes both rows and keeps the `transfer_groups` row so its `client_id` guard still fires. A `POST /transactions/{id}/restore` endpoint reverses manual deletes only. A lazy purge (inside the `materialize_due` pass, once per day per process) hard-deletes rows older than 30 days with their splits, edit events, and MinIO attachments. Frontend: a global snackbar provider; undo of a synced quick entry deletes the row, undo of a still-pending outbox entry discards the outbox item.

**Tech Stack:** FastAPI, SQLAlchemy 2, pytest (SQLite in-memory); React 19 + Vite, TanStack Query, idb (IndexedDB outbox), Tailwind. Spec: `docs/roadmap/24-undo-eliminacion.md`.

**Conventions (repo):** Spanish user-facing copy; English code comments and commit messages (imperative); tests in `backend/tests/` with the `client`/`session` fixtures; no migration is needed (the columns exist).

**Known limitation (v1):** if the outbox flushes a pending quick entry during the 8-second snackbar window, the discard is a no-op and the row stays on the server (visible in the list). Acceptable: the window is tiny and the entry is the user's, not data loss.

---

## Chunk 1: Backend

### Task 1: Soft delete mechanics + restore endpoint (TDD)

**Files:**
- Modify: `backend/app/api/routes/transactions.py`
- Test: `backend/tests/test_undo.py` (new)

- [ ] **Step 1: Write the failing tests**

```python
from datetime import date, datetime, timedelta, timezone

import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Account, Attachment, Category, Household, Transaction, TransferGroup, User


def _headers(user: User) -> dict[str, str]:
    token = jwt.encode(
        {"sub": user.id, "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return {"Authorization": f"Bearer {token}"}


def _setup(session: Session) -> tuple[dict, str, str, str]:
    """Household + user + shared cash account + an expense on it."""
    user = User(email="owner@example.com", hashed_password="x", name="Owner")
    session.add(user)
    session.flush()
    household = Household(name="Casa", owner_id=user.id)
    session.add(household)
    session.flush()
    user.household_id = household.id
    category = Category(household_id=household.id, name="Comida", icon="x", color="#000000", type="expense")
    account = Account(household_id=household.id, name="Efectivo", kind="cash", opening_balance=1000)
    session.add_all([category, account])
    session.flush()
    session.add(
        Transaction(household_id=household.id, type="expense", amount=100,
                    category_id=category.id, account_id=account.id,
                    member_id=user.id, date=date.today())
    )
    session.commit()
    tx = session.query(Transaction).one()
    return _headers(user), account.id, tx.id, household.id


def test_delete_is_soft_delete(client, session):
    headers, account_id, tx_id, _ = _setup(session)
    assert client.delete(f"/transactions/{tx_id}", headers=headers).status_code == 204
    # hidden everywhere
    assert client.get(f"/transactions/{tx_id}", headers=headers).status_code == 404
    assert client.get("/transactions", headers=headers).json() == []
    assert client.get("/summary/month", headers=headers).json()["expense"] == 0.0
    # but the row still exists, soft-deleted with reason manual
    row = session.get(Transaction, tx_id)
    assert row.deleted_at is not None
    assert row.delete_reason == "manual"
    # account balance reflects the deletion
    accounts = client.get("/accounts", headers=headers).json()
    assert accounts[0]["balance"] == 1000.0


def test_delete_transfer_soft_deletes_both_rows_and_keeps_group(client, session):
    headers, account_id, tx_id, household_id = _setup(session)
    session.add(Account(household_id=household_id, name="Débito", kind="debit", opening_balance=0))
    session.commit()
    debit_id = session.query(Account).filter_by(name="Débito").one().id
    res = client.post("/transactions", json={
        "type": "transfer", "amount": 50, "sourceAccountId": account_id,
        "destinationAccountId": debit_id, "date": date.today().isoformat(),
    }, headers=headers)
    assert res.status_code == 201, res.text
    assert client.delete(f"/transactions/{res.json()['id']}", headers=headers).status_code == 204
    rows = session.query(Transaction).filter_by(transfer_group_id=res.json()['transferGroupId']).all()
    assert len(rows) == 2
    assert all(row.deleted_at is not None and row.delete_reason == "manual" for row in rows)
    assert session.get(TransferGroup, res.json()['transferGroupId']) is not None  # kept: client_id guard
    balances = {row["id"]: row["balance"] for row in client.get("/accounts", headers=headers).json()}
    assert balances[account_id] == 1000.0 and balances[debit_id] == 0.0


def test_restore_one_off(client, session):
    headers, _, tx_id, _ = _setup(session)
    client.delete(f"/transactions/{tx_id}", headers=headers)
    res = client.post(f"/transactions/{tx_id}/restore", headers=headers)
    assert res.status_code == 200, res.text
    assert res.json()["id"] == tx_id
    assert client.get(f"/transactions/{tx_id}", headers=headers).status_code == 200
    assert client.get("/summary/month", headers=headers).json()["expense"] == 100.0
    row = session.get(Transaction, tx_id)
    assert row.deleted_at is None and row.delete_reason is None


def test_restore_transfer_restores_both_rows(client, session):
    # ... transfer created and deleted; restore one side; both visible again


def test_restore_guards(client, session):
    headers, _, tx_id, _ = _setup(session)
    # not deleted -> 404
    assert client.post(f"/transactions/{tx_id}/restore", headers=headers).status_code == 404
    # import-reverted row -> 409 (simulate by setting the flags directly)
    client.delete(f"/transactions/{tx_id}", headers=headers)
    row = session.get(Transaction, tx_id)
    row.delete_reason = "import_revert"
    session.commit()
    assert client.post(f"/transactions/{tx_id}/restore", headers=headers).status_code == 409
    # other household -> 404
    other = User(email="other@example.com", hashed_password="x", name="Other")
    session.add(other); session.flush()
    other_hh = Household(name="Otra", owner_id=other.id)
    session.add(other_hh); session.flush()
    other.household_id = other_hh.id; session.commit()
    assert client.post(f"/transactions/{tx_id}/restore", headers=_headers(other)).status_code == 404


def test_client_id_replay_after_soft_delete_still_409(client, session):
    headers, account_id, tx_id, _ = _setup(session)
    # create with an explicit clientId
    res = client.post("/transactions", json={
        "type": "expense", "amount": 10, "categoryId": session.query(Category).one().id,
        "accountId": account_id, "date": date.today().isoformat(), "clientId": "abc-123",
    }, headers=headers)
    assert res.status_code == 201
    client.delete(f"/transactions/{res.json()['id']}", headers=headers)
    replay = client.post("/transactions", json={
        "type": "expense", "amount": 10, "categoryId": session.query(Category).one().id,
        "accountId": account_id, "date": date.today().isoformat(), "clientId": "abc-123",
    }, headers=headers)
    assert replay.status_code == 409


def test_restore_invalidates_completed_reconciliation(client, session):
    # complete a session over the tx, delete the tx (session -> stale),
    # restore the tx -> session stays stale (not re-completed)
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && uv run pytest tests/test_undo.py -q`
Expected: FAIL (delete hard-deletes today; restore route missing)

- [ ] **Step 3: Rewrite the delete mechanics**

In `app/api/routes/transactions.py` `delete_transaction`, replace the hard-delete branches:

```python
    if tx.type == "transfer":
        if tx.transfer_group_id is None:
            raise HTTPException(status_code=409, detail="La transferencia está incompleta")
        rows = _transfer_rows(db, tx.transfer_group_id)
        _assert_transfer_access(rows, household_id, user.id, db)
        now = datetime.now(timezone.utc)
        for row in rows:
            invalidate_completed_reconciliation(db, row)
            row.deleted_at = now
            row.delete_reason = "manual"
        # The group is kept on purpose: its client_id must keep blocking replays.
        db.commit()
        return
    invalidate_completed_reconciliation(db, tx)
    tx.deleted_at = datetime.now(timezone.utc)
    tx.delete_reason = "manual"
    db.commit()
```

(`datetime`/`timezone` imports already exist in the file; verify.)

- [ ] **Step 4: Add the restore endpoint** (right after `delete_transaction`)

```python
@router.post("/{transaction_id}/restore")
def restore_transaction(transaction_id: str, db: DbDep, user: CurrentUserDep) -> TransactionOut:
    household_id = _household_id(user)
    # Unlike the normal read, restore must see soft-deleted rows.
    tx = db.scalar(select(Transaction).join(Account).where(
        Transaction.id == transaction_id,
        Transaction.household_id == household_id,
        Transaction.deleted_at.is_not(None),
        visible_accounts(user.id),
    ).with_for_update(of=Transaction))
    if tx is None:
        raise HTTPException(status_code=404, detail="No hay ningún movimiento eliminado que restaurar")
    if tx.delete_reason == "import_revert":
        raise HTTPException(status_code=409, detail="Los movimientos importados se restauran desde el lote de importación")
    rows = [tx]
    if tx.type == "transfer":
        if tx.transfer_group_id is None:
            raise HTTPException(status_code=409, detail="La transferencia está incompleta")
        rows = _transfer_rows(db, tx.transfer_group_id)
    for row in rows:
        invalidate_completed_reconciliation(db, row)
        row.deleted_at = None
        row.delete_reason = None
    db.commit()
    db.refresh(tx)
    return _tx_out(tx, db, user.id)
```

Note: `_transfer_rows` must accept soft-deleted rows — verify its predicate does NOT filter `deleted_at` (the import-revert flow already restores transfer rows through it). If it filters, add a `include_deleted=True` path or query the group rows directly.

- [ ] **Step 5: Run tests**

Run: `cd backend && uv run pytest tests/test_undo.py -q` → Expected: PASS
Run: `cd backend && uv run pytest -q` → Expected: all pass (existing delete tests must still pass — check `tests/test_offline_transactions.py` and any transfer-delete test that asserted hard deletion; update their assertions to the soft-delete reality if they checked row absence).

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/routes/transactions.py backend/tests/test_undo.py
git commit -m "Make manual deletions reversible with a restore endpoint"
```

### Task 2: Lazy purge housekeeping (TDD)

**Files:**
- Create: `backend/app/services/housekeeping.py`
- Modify: `backend/app/services/recurring.py` (call site)
- Test: `backend/tests/test_purge.py` (new)

- [ ] **Step 1: Write the failing tests**

```python
def _soft_delete_aged(session, tx, days_ago: int):
    tx.deleted_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    tx.delete_reason = "manual"

def test_purge_removes_rows_older_than_retention(client, session, monkeypatch):
    # two soft-deleted expenses: 31 and 29 days old
    # monkeypatch app.services.housekeeping.last_purge_day so the guard runs
    # call GET /transactions (triggers materialize_due -> maybe_purge)
    # -> 31d row hard-deleted (session.get is None), 29d row still soft-deleted

def test_purge_removes_dependents(client, session, monkeypatch):
    # soft-deleted (31d) split transaction + transaction with edit event + attachment row
    # monkeypatch app.services.housekeeping.delete_attachment (storage) and assert called with the object key
    # after a read: splits, edit events, attachment rows and MinIO object all gone

def test_purge_keeps_transfer_group_until_both_rows_gone(client, session, monkeypatch):
    # 31d soft-deleted transfer pair -> group removed after purge
    # (and a 29d pair keeps its group)

def test_purge_runs_at_most_once_per_day(client, session, monkeypatch):
    # force the guard: two reads in a row -> the purge query runs once

def test_purge_failure_never_breaks_reads(client, session, monkeypatch):
    # monkeypatch the purge inner to raise; GET /transactions still 200
```

- [ ] **Step 2: Run to verify failure** → Expected: FAIL (module missing)

- [ ] **Step 3: Implement `app/services/housekeeping.py`**

```python
"""Lazy housekeeping for self-hosted deployments: no scheduler.

Purges soft-deleted transactions older than the retention window. Runs
inside the `materialize_due` read pass, at most once per day per process,
and a failing purge must never break a read endpoint.
"""

import logging

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Attachment, InstalmentPlan, Transaction, TransactionEditEvent, TransferGroup
from app.services.storage import delete_attachment

logger = logging.getLogger(__name__)

#: How long a soft-deleted row is kept before hard purge.
RETENTION_DAYS = 30

_last_purge_day: date | None = None


def maybe_purge(db: Session) -> int:
    """Purge once per day per process; returns rows purged (0 when skipped)."""
    global _last_purge_day
    today = datetime.now(timezone.utc).date()
    if _last_purge_day == today:
        return 0
    _last_purge_day = today
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    try:
        rows = db.scalars(select(Transaction).where(Transaction.deleted_at < cutoff)).all()
        purged = 0
        for tx in rows:
            try:
                with db.begin_nested():
                    _purge_one(db, tx)
                db.commit()
                purged += 1
            except Exception:
                db.rollback()
                logger.exception("Purge failed for transaction %s; skipping", tx.id)
        return purged
    except Exception:
        db.rollback()
        logger.exception("Purge pass failed; skipping")
        return 0


def _purge_one(db: Session, tx: Transaction) -> None:
    for attachment in db.scalars(select(Attachment).where(Attachment.transaction_id == tx.id)).all():
        try:
            delete_attachment(attachment.storage_path)
        except Exception:
            logger.exception("Failed to delete attachment object %s", attachment.storage_path)
        db.delete(attachment)
    db.execute(delete(TransactionEditEvent).where(TransactionEditEvent.transaction_id == tx.id))
    db.execute(delete(TransactionSplit).where(TransactionSplit.transaction_id == tx.id))
    if tx.transfer_group_id is not None:
        sibling = db.scalar(select(Transaction.id).where(
            Transaction.transfer_group_id == tx.transfer_group_id,
            Transaction.id != tx.id,
        ))
        if sibling is None:
            group = db.get(TransferGroup, tx.transfer_group_id)
            if group is not None:
                db.delete(group)
    db.delete(tx)
```

(Import `delete` from sqlalchemy; `InstalmentPlan` is NOT touched by the purge — a plan on a purged purchase keeps referencing the transaction id... **decide and document**: plans on soft-deleted purchases. Check: can a purchase with an active plan be soft-deleted? No — the guard 409s. A CANCELLED/completed plan may reference a deleted purchase; purging the purchase row would break the FK (`source_transaction_id` → transactions.id, no ondelete). **Therefore the purge must skip transactions referenced by any instalment plan** — add a `db.scalar(select(InstalmentPlan.id).where(source_transaction_id == tx.id))` check and skip (log) when referenced. Add a test for that.)

- [ ] **Step 4: Hook into `materialize_due`**

At the end of `materialize_due` in `app/services/recurring.py`, after the commit logic:

```python
    from app.services.housekeeping import maybe_purge
    maybe_purge(db)
    return created
```

- [ ] **Step 5: Run tests**

Run: `cd backend && uv run pytest tests/test_purge.py -q` → Expected: PASS
Run: `cd backend && uv run pytest -q` → Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/housekeeping.py backend/app/services/recurring.py backend/tests/test_purge.py
git commit -m "Add lazy purge of soft-deleted transactions"
```

---

## Chunk 2: Frontend

### Task 3: Snackbar provider + outbox discard

**Files:**
- Create: `frontend/src/components/ui/snackbar.tsx`
- Modify: `frontend/src/lib/offline.tsx`
- Modify: `frontend/src/components/layout/AppShell.tsx`

- [ ] **Step 1: `ui/snackbar.tsx`**

A `SnackbarProvider` that renders a fixed bottom-center snackbar (single instance, 8 s auto-dismiss, one optional action, `aria-live="polite"`, spring/cross-fade respecting `prefers-reduced-motion` via the app-level `MotionConfig`). Exposes:

```tsx
export interface SnackbarOptions {
  message: string
  action?: { label: string; onClick: () => void }
}
export function useSnackbar(): (options: SnackbarOptions) => void
```

- [ ] **Step 2: `offline.tsx`**

Add `discard(clientId: string): Promise<void>` to the context: deletes the store entry (no-op when absent) and calls `refreshPending()`.

- [ ] **Step 3: Wire the provider** in `AppShell` around the root `<div>`.

- [ ] **Step 4: Verify** — `cd frontend && npx tsc -b` → no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ui/snackbar.tsx frontend/src/lib/offline.tsx frontend/src/components/layout/AppShell.tsx
git commit -m "Add snackbar provider and outbox discard"
```

### Task 4: Undo call sites

**Files:**
- Modify: `frontend/src/lib/queries.ts` (`useRestoreTransaction`)
- Modify: `frontend/src/components/AddTransactionSheet.tsx`
- Modify: `frontend/src/components/TransactionDetailSheet.tsx`

- [ ] **Step 1: `useRestoreTransaction`** in `queries.ts` (same invalidation set as `useDeleteTransaction`):

```ts
export function useRestoreTransaction() {
  const invalidate = useInvalidator(keys.transactions, keys.accounts, keys.summary, keys.budgetsStatus, keys.rangeSummary, keys.forecast)
  return useMutation({
    mutationFn: (id: string) => apiFetch<Transaction>(`/transactions/${id}/restore`, { method: "POST" }),
    onSuccess: invalidate,
  })
}
```

- [ ] **Step 2: Quick entry undo** in `AddTransactionSheet.tsx` `save()` success path:

```tsx
const showSnackbar = useSnackbar()
const deleteTransaction = useDeleteTransaction()
const { discard } = useOffline()
// in onSuccess(created):
const undo = () => {
  if (created.id.startsWith("pending:")) {
    void discard(created.id.slice("pending:".length))
  } else {
    deleteTransaction.mutate(created.id)
  }
}
showSnackbar({ message: "Movimiento creado", action: { label: "Deshacer", onClick: undo } })
```

Apply to both branches (with file: show it after `onSettled` of the attachment upload; without file: in the plain `onSuccess`).

- [ ] **Step 3: Delete undo** in `TransactionDetailSheet.tsx` `remove()`:

```tsx
const showSnackbar = useSnackbar()
const restoreTransaction = useRestoreTransaction()
// in deleteTransaction.mutate onSuccess:
showSnackbar({ message: "Movimiento eliminado", action: { label: "Deshacer", onClick: () => restoreTransaction.mutate(deletedId) } })
```

Capture `deletedId = transaction.id` before `onClose()`.

- [ ] **Step 4: Verify**

Run: `cd frontend && npm run lint && npx tsc -b && npm run build` → Expected: pass (pre-existing chunk-size warning acceptable)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/queries.ts frontend/src/components/AddTransactionSheet.tsx frontend/src/components/TransactionDetailSheet.tsx
git commit -m "Add Deshacer snackbars for delete and quick entry"
```

---

## Chunk 3: Verification and docs

### Task 5: Full verification + roadmap update

**Files:**
- Modify: `docs/roadmap/README.md`, `docs/roadmap/24-undo-eliminacion.md`, `docs/plan.md`

- [ ] **Step 1: Backend** — `cd backend && uv run pytest -q` → all pass.
- [ ] **Step 2: Frontend** — `cd frontend && npm run lint && npm run build` → pass.
- [ ] **Step 3: Manual browser pass** (stack up): delete a movement → snackbar → Deshacer restores it; quick entry → Deshacer removes it; delete an offline (airplane mode) entry → Deshacer removes it locally; a soft-deleted row stays restorable; imported rows still 409 on direct delete/restore.
- [ ] **Step 4: Docs** — doc 24 header `✅ 2026-08-16`; README row 24 → ✅, progress → `24 of 24 done`, dated log entry; plan.md: 24 moves from Proposed to Progress. Mark all plan checkboxes done.
- [ ] **Step 5: Commit + push + PR**

```bash
git add docs/
git commit -m "Mark roadmap 24 (undo for delete and quick entry) done"
git push -u origin feat/undo-delete-quick-entry
gh pr create  # Summary / Changes / Test plan per repo convention
```
