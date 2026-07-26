# 👤 Personal vs shared accounts

**Status:** ⬜ Pending · **Priority:** Low · **Effort:** M (1-3 days) · **Dependencies:** 01-alembic ✅ (done)

## Why
The product's original decision was "all accounts belong to the household, with traceability of who logged each transaction." That works for shared expenses, but clashes with real cases: a personal payroll account, a card one doesn't want to share, a private savings account. Without personal accounts, users end up not logging those transactions and the app loses value. This is a model change, not just another feature.

## Scope
**Includes:**
- `owner_id` field (nullable) on `accounts`: `NULL` = shared (current behavior), with a value = personal to that user
- Visibility: personal accounts are only visible to their owner; household balances and reports exclude other members' personal accounts
- User view: "My accounts" (own personal + shared) and household summary with shared only
- Data migration: all existing accounts remain shared (`owner_id = NULL`)
- UI: "Personal" toggle when creating/editing an account; separate sections on the Accounts page

**Does not include:**
- Granular permissions (sharing an account with some members but not others)
- Moving existing transactions between accounts when visibility changes
- Personal accounts with a different currency (the currency remains one per household, MXN)

## Proposed design

### Backend
- Alembic migration: `ALTER TABLE accounts ADD COLUMN owner_id UUID NULL REFERENCES users(id)`
- Data migration in the same revision: no-op (existing accounts already default to `NULL` = shared)
- Account listing query: `WHERE household_id = :hid AND (owner_id IS NULL OR owner_id = :current_user)`
- Household totals (dashboard, summary, reports): `WHERE household_id = :hid AND owner_id IS NULL` — shared only
- User's personal totals: shared + own personal
- Transactions on personal accounts: only visible to the owner (same filter by the account's `owner_id` when listing transactions); they don't appear in the household feed/reports for others
- Write rule: any member can create a personal or shared account; only the owner can edit/delete a personal one
- Tests: cross visibility (A can't see B's personal account), household totals without personals, A's personal total includes both

### Frontend
- Account form: "Personal" toggle (explanation: "only you will see it; it doesn't add to the household total")
- Accounts page with two sections: "Household" and "Personal" (the latter empty with a CTA if there are none)
- Dashboard: the household total stays the same (shared); optional secondary line "Your personal total" that includes personals
- Subtle "Personal" badge on own account cards as a visibility reminder
- When switching an account from shared to personal (or vice versa): confirmation explaining the effect on balances and visibility

### Infra
- No changes: the migration runs via the Alembic entrypoint (01, already done)

## Acceptance criteria
- [ ] A's personal account is invisible to B in listings, transactions, and balances
- [ ] The household total only includes shared accounts
- [ ] A's personal total includes their personals + the shared ones
- [ ] Accounts existing before the migration remain visible to everyone (shared)
- [ ] A shared account can be converted to personal and vice versa without losing transactions
- [ ] New and existing tests pass

## Notes
- Main risk: existing queries that today assume "all household accounts belong to everyone." Audit ALL endpoints that touch `accounts` or aggregate balances before considering this closed.
- Open decision: can a personal account receive transactions logged by another member? Recommended: no, the owner is the only one who operates their personal account.
- This change revisits a documented decision ("all shared"); update that decision note wherever it lives so it isn't left contradictory.
