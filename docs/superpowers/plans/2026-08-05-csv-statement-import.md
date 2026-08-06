# CSV Statement Import Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Import selected rows from a bank CSV as auditable, idempotent account transactions through a three-step UI.

**Architecture:** A new FastAPI `/import` router parses CSV bytes in memory and persists only normalized source rows, fingerprints, audit events, and batch metadata. Preview is advisory: commit uploads the file again and server-side reparses it using the submitted mapping, date format, account, and row positions, so a manipulated client preview never becomes provenance. A fingerprint registry supplies idempotency while per-batch source rows retain each attempt; soft deletion enables atomic reversion and restoration without losing history.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Python standard-library `csv`, React, TypeScript, TanStack Query, Vite.

---

## File Structure

- Create `backend/app/api/routes/imports.py`: bounded CSV parsing, duplicate preview, atomic commit, batch history/inspection, revert, and restoration endpoints.
- Create `backend/app/schemas/imports.py`: camelCase request and response contracts for the import workflow.
- Modify `backend/app/models.py`: import batch/source-row provenance, fingerprint registry, edit audit events, and transaction import/soft-delete fields.
- Create `backend/alembic/versions/b2c3d4e5f6a7_importacion_csv.py`: reversible database migration from transfer head.
- Modify `backend/app/api/routes/transactions.py`, `accounts.py`, `attachments.py`, `summary.py`, `budgets.py`, and `services/range_summary.py`: hide soft-deleted transactions from normal reads, mutations, and aggregates while retaining deliberate historical deletion guards.
- Modify `backend/app/main.py`: register the import router.
- Create `backend/tests/test_imports.py`: route-level parsing, privacy, idempotency, atomicity, revert, and restore coverage.
- Modify `backend/tests/test_migrations.py`: include new tables in schema/migration assertions.
- Create `frontend/src/pages/ImportPage.tsx`: three-step import workflow plus batch history, detail, revert, and restore controls.
- Modify `frontend/src/App.tsx`, `frontend/src/pages/SettingsPage.tsx`, `frontend/src/lib/queries.ts`, and `frontend/src/lib/types.ts`: route, entry point, import hooks, and API types.

## Chunk 1: Durable Import Model

### Task 1: Define models and migration coverage together

**Files:**
- Modify: `backend/app/models.py`
- Modify: `backend/tests/test_migrations.py`
- Test: `backend/tests/test_migrations.py`

- [ ] **Step 1: Add metadata for `ImportBatch`, per-attempt `ImportRow`, unique `ImportFingerprint`, append-only `TransactionEditEvent`, and transaction `import_batch_id`, `deleted_at`, and `delete_reason`.**
- [ ] **Step 2: Add all four tables to the expected application-table set and run `uv run pytest tests/test_migrations.py -v` to confirm metadata needs a migration.**
- [ ] **Step 3: Add the reversible Alembic migration.**
  - Create `import_batches` with household, target account, creator, sanitized filename, mapping JSON, outcome counters, and timestamps.
  - Create `import_rows`, unique by `(batch_id, source_position)`, with immutable source snapshot, normalized transaction baseline, status, and optional transaction ID.
  - Create `import_fingerprints`, unique by `(household_id, account_id, fingerprint)`, referencing the originating source row/transaction; create edit events; add indexed transaction import and soft-delete columns.
- [ ] **Step 4: Run `uv run pytest tests/test_migrations.py -v`; verify upgrade, downgrade, upgrade, and `alembic check` pass with models and migration aligned.**
- [ ] **Step 5: Commit the migration and its test update.**

### Task 2: Exclude reverted rows and audit imported edits

**Files:**
- Modify: `backend/app/models.py`
- Modify: `backend/app/api/routes/transactions.py`
- Modify: `backend/app/api/routes/accounts.py`
- Modify: `backend/app/api/routes/attachments.py`
- Modify: `backend/app/api/routes/categories.py`
- Modify: `backend/app/api/routes/summary.py`
- Modify: `backend/app/api/routes/budgets.py`
- Modify: `backend/app/services/range_summary.py`
- Test: `backend/tests/test_imports.py`

- [ ] **Step 1: Write tests proving a soft-deleted transaction disappears from ledger, direct read/mutation, attachments, account balance (including account PATCH), month/budget/range summaries, reports, and client-ID replay. Assert category/account deletion guards remain historically inclusive and direct deletion of imported transactions is rejected to preserve provenance and reversibility.**
- [ ] **Step 2: Run the focused tests and confirm they fail with the pre-import model.**
- [ ] **Step 3: Add `Transaction.deleted_at.is_(None)` to every normal transaction read, aggregate, attachment, and idempotency lookup. Return 404 for normal reads/mutations of reverted rows, return 409 for direct delete of an imported transaction, and keep category/account reference guards inclusive.**
- [ ] **Step 4: Append `TransactionEditEvent` for any material edit to an imported transaction without changing its immutable source snapshot or baseline.**
- [ ] **Step 5: Run focused tests, then `uv run pytest`.**
- [ ] **Step 6: Commit the model and soft-delete query slice.**

## Chunk 2: Import API

### Task 3: Add bounded CSV parsing and preview API

**Files:**
- Create: `backend/app/schemas/imports.py`
- Create: `backend/app/api/routes/imports.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_imports.py`

- [ ] **Step 1: Write preview tests for UTF-8 CSV headers, mapping suggestions, currency normalization, explicit date formats, household direct duplicates, selected-account fingerprints, duplicate file rows, zero amounts, invalid CSV, byte-size/field-size limits, and more than 1,000 rows.**
- [ ] **Step 2: Run `uv run pytest tests/test_imports.py -v` and confirm the endpoint is absent.**
- [ ] **Step 3: Add camelCase schemas and `POST /import/preview` multipart endpoint.**
  - Require multipart `accountId`, validate it with `can_operate`, decode UTF-8 with BOM support, and reject over-limit bytes/headers/fields, missing headers, empty rows, invalid values, and zero values with generic 422 errors that never echo source values.
  - Accept optional mapping/date-format multipart fields to re-preview user edits. Return source positions, suggested mapping, normalized preview values, and duplicate reasons. Direct household matches and account-scoped fingerprints are warnings, preselected for exclusion rather than blocked client choices.
  - Do not persist file bytes or preview-only data.
- [ ] **Step 4: Register the router in `backend/app/main.py`.**
- [ ] **Step 5: Run preview tests and backend lint.**
- [ ] **Step 6: Commit preview endpoint, schemas, and tests.**

### Task 4: Reparse and commit safely and idempotently

**Files:**
- Modify: `backend/app/api/routes/imports.py`
- Modify: `backend/app/schemas/imports.py`
- Test: `backend/tests/test_imports.py`

- [ ] **Step 1: Write failing tests proving commit reparses uploaded bytes rather than trusting preview values, validates selected source positions against recomputed mapping, enforces account ownership, converts signed amounts, creates exactly one per-type Unclassified category under concurrent first imports, rejects invalid selections atomically, records advisory direct duplicates, skips fingerprint retries after note edits, and returns batch counters.**
- [ ] **Step 2: Run focused commit tests and confirm failure.**
- [ ] **Step 3: Implement `POST /import/commit`.**
  - Validate a user-operable destination account before writing.
  - Accept multipart CSV plus JSON mapping/date format/selected source positions, then reparse all bytes server-side and revalidate positions and row/byte limits.
  - Canonicalize date, signed amount at four decimals, and whitespace-normalized note before SHA-256 fingerprinting.
  - Lock the household row before finding/creating active per-type `Unclassified` categories, serializing first-import provisioning without an unsafe global category-name constraint; create one batch and one `ImportRow` per selected source position in the same DB transaction.
  - Create ordinary transactions only for rows whose `ImportFingerprint` does not exist, link every created transaction directly to its batch, and convert concurrent unique conflicts through a savepoint into skipped rows without aborting the batch.
- [ ] **Step 4: Run `uv run pytest tests/test_imports.py -v`, then the full backend test suite.**
- [ ] **Step 5: Commit the commit endpoint and tests.**

### Task 5: Expose batches and implement safe revert/restore

**Files:**
- Modify: `backend/app/api/routes/imports.py`
- Modify: `backend/app/schemas/imports.py`
- Test: `backend/tests/test_imports.py`

- [ ] **Step 1: Write failing tests for batch history/detail metadata, created transactions and edit-event visibility, cross-household/personal-account protection, unchanged revert, changed-row conflict, and restoration preserving source-row and transaction IDs.**
- [ ] **Step 2: Run the focused tests and confirm failure.**
- [ ] **Step 3: Implement `GET /import/batches`, batch detail, `POST /import/{batch_id}/revert`, and `POST /import/{batch_id}/restore`.**
  - Restrict batch access through its account with `can_operate`.
  - Compare each current transaction against the immutable imported baseline before reverting.
  - On any changed row, return `409` with affected row/transaction IDs and change nothing.
  - On success, atomically set `deleted_at`/`delete_reason='import_revert'`; restoration clears only those markers for the batch.
- [ ] **Step 4: Run focused and full backend tests.**
- [ ] **Step 5: Commit batch lifecycle implementation and tests.**

## Chunk 3: Import UI

### Task 6: Add typed import hooks, batch lifecycle, and route entry point

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/queries.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/pages/SettingsPage.tsx`
- Test: frontend build and lint

- [ ] **Step 1: Add API DTOs and hooks for preview, multipart re-upload commit, batch history/detail, revert, and restore. Invalidate transactions, accounts, month/range summaries, budgets, and batch queries after lifecycle mutations.**
- [ ] **Step 2: Add protected `/app/importar` route and an “Importar movimientos” Settings row.**
- [ ] **Step 3: Run `npm run lint` and `npm run build` in `frontend`.**
- [ ] **Step 4: Commit query/type/routing changes.**

### Task 7: Build the three-step import wizard and batch lifecycle UI

**Files:**
- Create: `frontend/src/pages/ImportPage.tsx`
- Modify: `frontend/src/App.tsx`
- Test: frontend build and lint

- [ ] **Step 1: Implement upload step with CSV file selection, accessible account picker, and inline backend errors. Do not submit until both values exist.**
- [ ] **Step 2: Implement review step with editable mapping/date format that re-previews the retained file, normalized row table, select-all/select-none, and per-row checkboxes. Duplicate warnings start excluded but can be individually included or excluded; fingerprint rows remain safely skipped by the server. Commit resubmits the retained `File`, never client-normalized values.**
- [ ] **Step 3: Implement result step with imported/skipped counts, batch ID, ledger link, and batch-detail/history control.**
- [ ] **Step 4: Implement history/detail with source metadata/counts, created transactions, revert confirmation, changed-row conflict display, and restoration action.**
- [ ] **Step 5: Check mobile (390px) and desktop layouts, keyboard operation, mapping/date re-preview, global and per-row duplicate selection, invalid-file handling, and revert/restore feedback in the browser.**
- [ ] **Step 6: Run `npm run lint` and `npm run build` in `frontend`.**
- [ ] **Step 7: Commit the wizard and batch lifecycle UI.**

## Final Verification

### Task 8: Validate the complete feature and update roadmap status

**Files:**
- Modify: `docs/roadmap/08-importacion-csv.md`
- Modify: `docs/roadmap/README.md`

- [ ] **Step 1: Run `uv run pytest` from `backend` and record the passing test count.**
- [ ] **Step 2: Run `npm run lint` and `npm run build` from `frontend`.**
- [ ] **Step 3: Run migration upgrade/downgrade verification against the configured PostgreSQL test workflow.**
- [ ] **Step 4: Manually verify real CSV upload, duplicate retry after note edit, batch revert/restore, and account privacy in the browser.**
- [ ] **Step 5: Mark roadmap item 08 complete with date and summarize implementation/verification in the roadmap log.**
- [ ] **Step 6: Inspect `git status` and `git diff`; commit only feature files.**
