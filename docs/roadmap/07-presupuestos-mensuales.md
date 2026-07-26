# 🎯 Monthly budgets

**Status:** ✅ 2026-07-25 · **Priority:** High · **Effort:** M (1-3 days) · **Dependencies:** None

## Why
After expense tracking, this is the most requested feature: per-category limits with visual alerts. It's what turns the app from a "history" into a "control tool."

## Scope
**Includes:**
- Model and CRUD for budgets per category.
- Status endpoint (spent vs limit) cross-referenced with the month's summary.
- Progress bars with traffic-light colors on the dashboard.

**Does not include:**
- Budgets per account, member, or arbitrary period.
- Push alerts/notifications when exceeding the limit.
- Income budgets.

## Proposed design
### Backend
- `budgets` model: `{id, household_id, category_id, amount NUMERIC}`, with `UNIQUE(household_id, category_id)`.
- **Recommended decision: a global budget per category** (a limit that's always active, applied every month) instead of a record per month (`YYYY-MM`). Simpler: it's defined once and reused; the monthly count is calculated from that month's transactions. No need to recreate budgets every month.
- CRUD `/budgets`: `GET` (household list), `POST`/`PATCH` (upsert by `category_id`), `DELETE /{id}`. Scoped by `household_id`.
- Endpoint `GET /budgets/status?month=YYYY-MM` → per category with a budget: `{categoryId, budget, spent, percentage}`, cross-referenced with the same logic as `/summary/month` (expenses only).
### Frontend
- "Budgets" section on the dashboard (below the donut chart): progress bars per category with traffic-light colors — green `<75%`, amber `<100%`, red `≥100%`. If it grows too much, consider a dedicated `/budgets` page.
- Create/edit limit from the same view: simple sheet with category (select) + amount. Edit = same sheet pre-loaded.
- Badge on the dashboard donut if any category exceeds its limit (red dot or counter).
- New hook in `src/lib/queries.ts` following the existing mutation pattern.
### Infra
- Alembic migration for the `budgets` table.

## Acceptance criteria
- [x] Set a limit for "Groceries", log expenses → the bar advances and changes color when crossing 75% and 100%.
- [x] When a new month starts, the count resets without recreating the budget.
- [x] A second budget cannot be created for the same category (upsert or clear error).
- [x] Deleting a category with a budget does not break `/budgets/status` (cascade or validation).
- [x] `/budgets/status` only includes expenses (`type=expense`), not income.
- [x] Tests: CRUD, `spent`/`percentage` calculation, uniqueness per household+category. (86 tests pass + 9 migration tests.)

## Notes
- Risk: duplicating the aggregation logic from `/summary/month`; reuse the same base query.
- Open decision: if different limits per month are wanted in the future, the global model can migrate to a nullable `month` without breaking existing behavior.
- UX: also show the remaining amount ("you have $1,200 left") alongside the percentage.

## How it turned out (2026-07-25)

Implemented mostly as designed, with a few deviations decided during the build:

- **Plain REST CRUD instead of a literal upsert endpoint.** Every other router
  in this codebase (`categories`, `accounts`, `recurring-rules`) does
  `POST`/`PATCH`/`DELETE`, never an upsert-by-natural-key endpoint. Kept that
  convention: `POST /budgets` 409s if a budget already exists for the
  category (backed by a DB `UNIQUE(household_id, category_id)`), and the
  frontend decides create-vs-edit the same way `CategoryFormSheet` already
  does — by checking whether a `Budget` exists for the picked category.
- **Category picker is a horizontal pill selector**, not a literal
  `<select>` — matches the account picker already in `AddTransactionSheet`
  and every other category-choosing UI in the app (none use the raw
  `ui/select.tsx`, they all use pills or an icon grid).
- **Deleting a category with a budget cascades the budget row** instead of
  blocking the delete. A budget isn't a historical movement like a
  transaction (which still blocks deletion), so there's nothing to lose by
  letting it go with the category — this is what satisfies "does not break
  `/budgets/status`."
- **The empty state has a "+" affordance**, not a bare `null` return like
  `DonutCard`. Budgets have no dedicated management page (by design, per
  scope), so without an entry point in the empty state nobody could ever
  create the first one.
- Added a `--warning` color token (`#ff9500` / dark `#ff9f0a`, iOS system
  orange) to `index.css`, matching the existing `--income`/`--expense`
  first-class-token pattern, for the 75–100% amber band.
- Migration generated against a throwaway Postgres 17 container (the local
  SQLite `dev.db` can't replay migration `8c41b0e7d2a9`'s `ALTER COLUMN`
  outside batch mode — a pre-existing limitation, not something this item
  introduced); verified upgrade + downgrade + upgrade again, and the 9
  `test_migrations.py` cases pass against real Postgres.
- **Deployed and verified in the browser** against the real database: two
  disposable test households (one for the CRUD/bar/cascade flow, one
  isolated just for the donut-badge check), both deleted afterward via a
  transactional `DELETE` matching household row counts before/after exactly.
  Confirmed: bar color at 73% (green), 80% (amber), 110% (red, width capped
  at 100%); editing an existing budget (category locked, amount editable);
  a budgeted category disappearing from the create-picker; deleting a
  category with a budget but no transactions succeeding and clearing its
  budget; the red count badge on the donut card heading when a category
  goes over 100%; mobile (390px) and desktop (1280px) layouts.
