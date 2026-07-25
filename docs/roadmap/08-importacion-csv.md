# 📥 CSV import

**Status:** ⬜ Pending · **Priority:** Medium · **Effort:** L (3+ days) · **Dependencies:** None

## Why
Populate the history from bank statements without manual entry. Without this, migrating to the app means weeks of lost data or tedious data entry.

## Scope
**Includes:**
- CSV preview with suggested column mapping and duplicate detection.
- Batch commit of selected rows.
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
- [ ] A real bank CSV imports N rows as transactions with correct date, amount, and note.
- [ ] Duplicates are detected in the preview and can be excluded with a global or per-row checkbox.
- [ ] Retrying the same import does not duplicate transactions (duplicates appear flagged on the second attempt).
- [ ] A CSV with more than 1000 rows is rejected with a clear message.
- [ ] Imported transactions appear with the "Unclassified" category and the chosen destination account.
- [ ] Tests: parsing, duplicate detection, idempotent commit, row limit.

## Notes
- Risk: ambiguous date formats (DD/MM vs MM/DD) — the mapping in step 2 must let the user choose the format explicitly.
- Risk: amounts with thousands separators or currency symbols ("$1,234.56") — normalize during parsing.
- Open decision: store a row hash (`date+amount+note`) for more robust dedupe in the future; for the MVP, a direct comparison is enough.
