# Goal Plans Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a pausable dated savings-goal plan with a calculated monthly contribution.

**Architecture:** Store only whether a plan is paused on `savings_goals`; derive the plan state and monthly requirement while serializing each goal. Contributions remain manual and do not create ledger entries.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, Alembic, React, TanStack Query, TypeScript.

---

### Task 1: Persist and expose plan state

**Files:**
- Create: `backend/alembic/versions/c7d8e9f0a1b2_planes_de_metas.py`
- Modify: `backend/app/models/planning.py`
- Modify: `backend/app/schemas/goals.py`
- Modify: `backend/app/api/routes/goals.py`
- Test: `backend/tests/test_goals.py`

- [x] Add the reversible migration and model field.
- [x] Derive active, paused, overdue, completed, and no-plan states.
- [x] Calculate monthly contributions over inclusive calendar months.
- [x] Cover the calculation and pause/resume API behavior.

### Task 2: Present and control plans

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/queries.ts`
- Modify: `frontend/src/components/SavingsGoalSheets.tsx`

- [x] Extend frontend API types with the derived plan data.
- [x] Add a pause control only when the goal has a target date.

### Task 3: Organize database models

**Files:**
- Create: `backend/app/models/`
- Delete: `backend/app/models.py`

- [x] Group ORM entities by identity, accounts, categories, transactions,
  planning, and imports.
- [x] Preserve `app.models` reexports to keep existing consumers unchanged.
