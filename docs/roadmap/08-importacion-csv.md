# 📥 CSV import

**Status:** ✅ 2026-08-06 · **Priority:** Medium · **Effort:** L (3+ days) · **Dependencies:** None

## Why
Populate the history from bank statements without manual entry. Without this, migrating to the app means weeks of lost data or tedious data entry.

## Scope
**Includes:**
- CSV preview with suggested column mapping and duplicate detection.
- Batch commit of selected rows.
- An auditable import batch, its normalized source rows, and the transactions it
  created, so an import can be retried safely and investigated or reverted.
- 3-step wizard on the frontend.

**Does not include:**
- Formats other than CSV (OFX, QIF, Excel, PDF).
- Automatic category mapping by description (classification rules).
- Recurring/scheduled import.

## Proposed design
### Backend
- `POST /import/preview` (multipart CSV) → parses and returns:
  - Detected rows with suggested column mapping (date / amount / description) via header and data-type heuristics.
  - Possible duplicates flagged: same date + amount + note as an existing transaction in the household.
- `POST /import/commit` with the confirmed mapping, destination `accountId`, and selected rows → bulk insert of transactions (`type` inferred from the amount's sign: negative = `expense`, positive = `income`).
- Every commit creates an `import_batches` row with the target account, source
  filename, mapping, import timestamp, and outcome counters. Every selected
  normalized row has a deterministic fingerprint, immutable `source_snapshot`,
  and every created transaction references its batch. Enforce the fingerprint's
  uniqueness per household and target account so retrying a file is idempotent
  even if the original transaction is later edited.
- Imported transactions remain editable. Their source snapshot is never
  overwritten; editing them records an audit event and may mark an associated
  reconciliation session as stale rather than blocking the user.
- `POST /import/{batch_id}/revert` reverses only transactions still attributable
  to that batch through the shared soft-delete mechanism (`deleted_at` and
  `delete_reason = 'import_revert'`). It must run atomically and return a
  conflict with the affected rows when a later operation has changed a
  transaction and explicit user review is required.
- **Recommended decision**: create a default "Unclassified" category per household for imported rows, instead of allowing a null `categoryId` — keeps schema and summary invariants intact.
- Limit of 1000 rows per import (reject with a clear error if exceeded).
- The whole commit runs within a single DB transaction.
### Frontend
- `/import` page (accessible from Settings and/or Transactions) with a 3-step wizard:
  1. **Upload file**: file input, destination account selection.
  2. **Review**: column mapping (editable), row table with checkboxes, duplicates pre-marked for exclusion.
  3. **Result**: imported/skipped count, link to Transactions.
- Loading and error states per step (invalid file, undetectable columns).
### Infra
- No changes (in-memory parsing; the CSV is not stored).

## Acceptance criteria
- [x] A real bank CSV imports N rows as transactions with correct date, amount, and note.
- [x] Duplicates are detected in the preview and can be excluded with a global or per-row checkbox.
- [x] Retrying the same import does not duplicate transactions (duplicates appear flagged on the second attempt).
- [x] A CSV with more than 1000 rows is rejected with a clear message.
- [x] Imported transactions appear with the "Unclassified" category and the chosen destination account.
- [x] Re-importing a file creates no duplicate transactions, including after a
  user has edited the note of a previously imported transaction.
- [x] An import batch exposes its source file metadata, counts, and created
  transactions; an unchanged batch can be soft-deleted atomically and restored
  without losing its provenance.
- [x] Tests: parsing, duplicate detection, idempotent commit, row limit.

## Notes
- Risk: ambiguous date formats (DD/MM vs MM/DD) — the mapping in step 2 must let the user choose the format explicitly.
- Risk: amounts with thousands separators or currency symbols ("$1,234.56") — normalize during parsing.
- Open decision: store a row hash (`date+amount+note`) for more robust dedupe in the future; for the MVP, a direct comparison is enough.
