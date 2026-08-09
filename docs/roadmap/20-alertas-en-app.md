# In-app alerts

**Status:** ✅ 2026-08-08
**Priority:** Medium
**Effort:** M
**Dependency:** monthly budgets, savings goals, and recurring transactions

## Why

Budgets and goals only help when somebody opens the relevant screen. Alerts make financial risks and progress visible from anywhere in the app without requiring a server-side scheduler, which is important for self-hosted deployments.

## Scope

- Persist idempotent alerts generated lazily by `GET /alerts`.
- Surface a notification bell with an unread badge and a responsive alerts sheet.
- Cover 75% and 100% budget thresholds, overdue recurring rules, reached goals, and negative account balances.
- Let a user mark one or all visible alerts as read. A recurring alert can materialize its due movement immediately.

## Design

- `alerts` uses a household-scoped unique dedupe key, so concurrent reads cannot create duplicates. Household alerts are shared; alerts for personal accounts and their recurring rules are visible only to that account owner.
- Budget alerts are scoped to category, threshold, and month. Negative-balance and goal-reached alerts are scoped to the account or goal. An overdue rule is scoped to its pending run date, preserving a new alert if it becomes overdue again after a later edit.
- No scheduler is introduced. Generation happens on the alerts read endpoint; the existing recurring materializer remains the only code that creates recurring transactions.

## Acceptance criteria

- [x] A budget threshold produces one alert and never reappears after it is read.
- [x] An overdue recurring rule shows a `Generar ahora` action.
- [x] Goal and negative-balance alerts are generated and household data remains isolated.
- [x] Tests cover generation idempotency, read/unread, isolation, and recurring generation.
