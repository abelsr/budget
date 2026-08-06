# 🔍 Filters and search in Transactions

**Status:** ✅ 2026-08-04 · **Priority:** Medium · **Effort:** S (<1 day) · **Dependencies:** None

## Why
The Transactions list grows every day and today there's no way to find anything: no searching by note, no filtering by category or account. It's the most visible gap on the page.

## Scope
**Includes:**
- Filter/search parameters on `GET /transactions`.
- Search bar with debounce and filter chips in Transactions.
- Filters reflected in the URL (shareable).

**Does not include:**
- Advanced full-text search (ranking, fuzzy matching).
- Saved filters or custom views.
- Filtering on the dashboard.

## Proposed design
### Backend
- Extend `GET /transactions` with query params:
  - `q`: searches `note` with `ILIKE '%q%'`.
  - `categoryId`, `accountId`, `memberId`, `type` (`expense|income`).
  - `from`, `to`: date range (ISO).
- Maintain full compatibility with the current params (`month`, `limit`, `offset`); `month` cannot be combined with `from` or `to` and returns `422` to avoid an ambiguous range.
- Index on `transactions(household_id, date)` to support filters with pagination.
### Frontend
- Search bar in Transactions: input with `Search` icon, 300ms debounce, bound to the `q` param.
- Filter chip row below: category, account, type (expense/income). If they grow, move to a filter sheet.
- Friendly empty state: "No results for these filters" with a clear button.
- Filters synced with URL query params (`?q=sams&categoryId=…`) using the router, for shareable URLs.
- Update the hook in `src/lib/queries.ts` to pass the params to TanStack Query (query key includes the filters).
### Infra
- No changes (index via migration if applicable).

## Acceptance criteria
- [x] Typing "sams" filters the list to transactions whose note contains "sams" (case-insensitive).
- [x] Combining category + account works (intersection).
- [x] Clearing filters restores the full list.
- [x] Copying the URL with filters and opening it in another tab preserves the applied filters.
- [x] The existing params (`month`, `limit`, `offset`) keep working the same way.
- [x] Tests cover combinations, case-insensitive `ILIKE` search, and the `month`/range conflict.

## Notes
- `month` and `from`/`to` are mutually exclusive. The API rejects their combination with `422` instead of silently discarding a filter.
- Debounce and the correct query key prevent unnecessary refetches while typing.
