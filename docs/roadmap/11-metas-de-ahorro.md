# 🎯 Savings goals

**Status:** ✅ 2026-08-05 · **Priority:** Medium · **Effort:** M (1-3 days) · **Dependencies:** 01-alembic ✅ (done: the new table comes in via migration)

## Why
Families save for specific things ("vacation, $30,000 by December", "the car down payment"), and today that money gets lost inside the savings account balance: there's no visibility into how much is left or whether they're on pace. A goal with visible progress turns saving into something actionable and motivates continued contributions.

## Scope
**Includes:**
- `savings_goals` model and full CRUD (create, edit, archive, delete)
- Manual contribution of the current amount (simple MVP, see decision below)
- Goal cards on the dashboard with progress (bar or ring), % and remaining amount
- "Completed" state with a subtle celebration and archiving
- Icon and color per goal to tell them apart at a glance

**Does not include:**
- Automatic scheduled contributions (that would be integration with recurring transactions, a future phase)
- Multi-account goals or complex allocation rules
- "At this pace you'll reach it in X months" projections (a later nice-to-have)

## Proposed design

### Backend
- `SavingsGoal` model: `id`, `household_id` (multi-tenant, like everything else), `name`, `target_amount`, `current_amount`, `target_date` (nullable), `account_id` (nullable, FK to `accounts` to link the goal to the account where the money lives), `icon`, `color`, `archived` (bool), timestamps
- Endpoints under `/goals`: `GET/POST /goals`, `PATCH/DELETE /goals/{id}`, `POST /goals/{id}/contribute` (adjusts `current_amount` by a positive or negative delta)
- **Decision on contributions (recommended for MVP):** `current_amount` is a manual field updated via `/contribute`; the "set aside" option from a transaction does NOT create a real transaction in the MVP (avoids double counting: the money already left as an expense or is already in the savings account). The link with `account_id` is informational only ("this savings lives in this account")
- The `GET /goals` response includes computed fields: `progress_pct`, `remaining`, `is_completed` (`current_amount >= target_amount`)
- Tests: CRUD, contribute with a negative delta, completion, isolation per `household_id`

### Frontend
- "Goals" section on the dashboard: cards with icon/color, progress bar (or circular ring), current amount / target, % and remaining
- Create/edit goal modal/page: name, target, optional date, linked account (account select), icon and color
- "Contribute" button on each card with an amount input (supports withdrawing with a negative amount)
- When a goal is reached: subtle animation (CSS confetti or transition) and an option to archive; archived goals are hidden by default with a toggle to view them
- TanStack Query: invalidate `goals` after contribute/edit

### Infra
- No changes: the new table comes in via an Alembic migration
  (`uv run alembic revision --autogenerate`), applied by the entrypoint on
  startup. `create_all` no longer exists in production.

## Acceptance criteria
- [x] A goal can be created with a name, target amount, and optional date.
- [x] Contributions persist independently from transactions and support subtraction.
- [x] The dashboard shows progress, remaining amount, icons, colors, archive controls, and a dismissible completion notice.
- [x] Goals are isolated by household; linked accounts must be shared and are unlinked, not deleted, with account removal.
- [x] Backend tests cover CRUD, money validation, contributions, completion, account unlinking, and isolation.

## Notes
- Risk of double counting if contributions get linked to real transactions later: document now that `current_amount` is the goal's own state, independent of the transaction flow.
- Open decision: what happens to the goal if the linked account is deleted? Recommended: `ON DELETE SET NULL`, the goal survives.
- The celebration must be subtle and dismissible: this is a daily-use app, not a game.
