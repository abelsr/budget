# 🎯 Monthly budgets

**Status:** ⬜ Pending · **Priority:** High · **Effort:** M (1-3 days) · **Dependencies:** None

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
- [ ] Set a limit for "Groceries", log expenses → the bar advances and changes color when crossing 75% and 100%.
- [ ] When a new month starts, the count resets without recreating the budget.
- [ ] A second budget cannot be created for the same category (upsert or clear error).
- [ ] Deleting a category with a budget does not break `/budgets/status` (cascade or validation).
- [ ] `/budgets/status` only includes expenses (`type=expense`), not income.
- [ ] Tests: CRUD, `spent`/`percentage` calculation, uniqueness per household+category.

## Notes
- Risk: duplicating the aggregation logic from `/summary/month`; reuse the same base query.
- Open decision: if different limits per month are wanted in the future, the global model can migrate to a nullable `month` without breaking existing behavior.
- UX: also show the remaining amount ("you have $1,200 left") alongside the percentage.
