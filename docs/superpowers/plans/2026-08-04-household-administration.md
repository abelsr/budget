# Household Administration Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every household a single owner who can administer membership while every active member can view the member directory and transactions retain their immutable author.

**Architecture:** Store the owner as `households.owner_id`, backfill existing households to their earliest member, and enforce ownership at every administration endpoint. Membership removal only nulls `users.household_id`; it never deletes the user or rewrites `transactions.member_id`, which is the immutable transaction author assigned by the backend.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, Alembic, pytest, React 19, TanStack Query, Motion, Tailwind CSS.

---

## Chunk 1: Ownership And Administration API

### Task 1: Persist household ownership and enforce permissions

**Files:**
- Modify: `backend/app/models.py`
- Modify: `backend/app/api/routes/auth.py`
- Modify: `backend/app/api/routes/households.py`
- Modify: `backend/app/schemas/households.py`
- Create: `backend/alembic/versions/<revision>_propietario_hogar.py`
- Test: `backend/tests/test_households_summary.py`
- Test: `backend/tests/test_auth.py`

- [x] **Step 1: Write failing owner and member permission tests.**
  - Registering a household assigns its creator as owner.
  - Existing households backfill their earliest user as owner through the migration.
  - Every active member can list all active members, including an `isOwner` marker.
  - Only the owner can create/list/revoke invitations or remove another active member.
  - A non-owner receives `403`; an owner cannot remove themselves; foreign/not-found IDs receive `404`.
- [x] **Step 2: Run the targeted tests and confirm they fail.**
- [x] **Step 3: Add nullable-then-backfilled-and-non-null `owner_id` to households.**
  - Add the foreign key after backfill in a deployment-safe migration.
  - Chain from `e52fa631c4bd` so Alembic retains one head.
- [x] **Step 4: Add owner-only administration endpoints.**
  - `GET /households/me/invitations` returns active invitations without exposing their tokens.
  - `DELETE /households/me/invitations/{id}` revokes an active invitation.
  - `DELETE /households/me/members/{id}` detaches the user (`household_id = NULL`), preserving their user and transaction records.
- [x] **Step 5: Run targeted tests and Alembic heads.**

### Task 2: Preserve and prove transaction authorship

**Files:**
- Modify: `backend/app/models.py`
- Modify: `backend/app/schemas/transactions.py`
- Modify: `backend/app/api/routes/transactions.py`
- Test: `backend/tests/test_core.py`
- Test: `backend/tests/test_households_summary.py`

- [x] **Step 1: Write tests that a supplied `memberId` cannot impersonate another member and removal preserves existing `memberId`.**
- [x] **Step 2: Run the focused tests and confirm the missing assertion fails.**
- [x] **Step 3: Clarify `member_id` as the immutable author in model/schema/API comments without accepting it as writable input.**
- [x] **Step 4: Run targeted tests.**

## Chunk 2: Member Directory Interface

### Task 3: Replace invitation-only Settings row with a member directory

**Files:**
- Create: `frontend/src/components/HouseholdMembersSheet.tsx`
- Modify: `frontend/src/pages/SettingsPage.tsx`
- Modify: `frontend/src/lib/queries.ts`
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/auth.tsx` if the owner marker belongs in session

- [x] **Step 1: Add typed queries/mutations for members and active invitations.**
- [x] **Step 2: Build the responsive members sheet.**
  - All members see the active directory with self and owner labels but no destructive controls.
  - Owner sees invite action, active invitations with revoke controls, and a confirmation before removing another member.
  - Owner has no control to remove themselves.
- [x] **Step 3: Invalidate member/invitation queries after each owner mutation and show inline API errors.**
- [x] **Step 4: Run `npm run build` and inspect the mobile sheet and desktop layout.**

## Chunk 3: Documentation And Verification

### Task 4: Record administration semantics

**Files:**
- Modify: `docs/roadmap/02-invitaciones-end-to-end.md`
- Modify: `docs/plan.md`

- [x] **Step 1: Update invitation documentation to supersede “everyone is equal” with the owner policy.**
- [x] **Step 2: Run `uv run pytest`, `uv run alembic heads`, `npm run build`, and `npm run lint`.**
- [x] **Step 3: Verify no migration branch or documentation contradiction remains.**
