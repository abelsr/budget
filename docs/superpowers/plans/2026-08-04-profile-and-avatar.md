# Profile And Avatar Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an authenticated member manage their name, optional sex and birth date, private avatar, and password from Settings.

**Architecture:** Extend `users` with optional profile fields and expose them through the existing `/auth/me` session response. Store a normalized avatar object in the existing MinIO bucket, but serve it through an authenticated endpoint so it is never public. The frontend session remains the single source of truth after profile mutations, and an avatar component fetches the protected image as a blob.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, Alembic, MinIO, Pillow, React 19, TypeScript, TanStack Query, Motion, Tailwind CSS.

---

## Chunk 1: Profile API And Storage

### Task 1: Persist and expose optional profile data

**Files:**
- Modify: `backend/app/models.py`
- Create: `backend/alembic/versions/<revision>_perfil_usuario.py`
- Modify: `backend/app/schemas/auth.py`
- Modify: `backend/app/api/routes/auth.py`
- Test: `backend/tests/test_auth.py`

- [x] **Step 1: Write failing API tests**
  - Patch `/auth/me` changes name, sex, and birth date for the authenticated user.
  - Invalid sex, future birth date, and empty update return `422`.
  - `POST /auth/change-password` accepts the current password and rejects an incorrect or short replacement password while the existing token still accesses `/auth/me`.
- [x] **Step 2: Run `uv run pytest tests/test_auth.py -v` and confirm the new tests fail.**
- [x] **Step 3: Add the `sex`, `birth_date`, `avatar_path`, and `avatar_updated_at` nullable columns plus an Alembic migration.**
- [x] **Step 4: Add typed request models and authenticated profile/password endpoints.**
  - `sex` accepts `female`, `male`, `non_binary`, or `prefer_not_to_say`.
  - Birth date cannot be future or older than 120 years.
  - Password changes rehash with the existing hasher and do not invalidate existing stateless JWTs.
- [x] **Step 5: Run `uv run pytest tests/test_auth.py -v`.**

### Task 2: Manage a protected normalized avatar

**Files:**
- Modify: `backend/app/services/storage.py`
- Modify: `backend/app/api/routes/auth.py`
- Test: `backend/tests/test_auth.py`

- [x] **Step 1: Write failing tests with storage mocked.**
  - An image upload is converted to a 512 px WebP avatar and reflected in `/auth/me`.
  - Unsupported, malformed, and oversized input return a clear 4xx response.
  - Avatar download requires authentication; delete clears both object and profile field.
- [x] **Step 2: Run the targeted tests and confirm they fail.**
- [x] **Step 3: Implement upload, authenticated download, and deletion.**
  - Limit raw input to 2 MB and accept images only.
  - Decode with Pillow, fit to a square, encode WebP, and use a stable per-user object key.
  - On storage failure, retain the existing DB record and report `502`.
- [x] **Step 4: Run `uv run pytest tests/test_auth.py -v`.**

## Chunk 2: Account Settings Interface

### Task 3: Add profile and password management sheets

**Files:**
- Create: `frontend/src/components/ProfileAvatar.tsx`
- Modify: `frontend/src/lib/auth.tsx`
- Modify: `frontend/src/pages/SettingsPage.tsx`
- Modify: `frontend/src/components/layout/AppShell.tsx`
- Modify: `frontend/src/lib/api.ts`
- Modify: `docs/roadmap/10-perfil-y-password.md`
- Modify: `docs/roadmap/README.md`

- [x] **Step 1: Extend the session type and auth context with profile update, avatar upload/delete, and password-change operations.**
- [x] **Step 2: Build the Account sheet.**
  - Display protected avatar or initials, allow replacement/removal, name editing, sex selection, and birth-date editing.
  - Calculate and show age locally from the birth date; do not send an age field to the API.
  - Show upload and API failures beside their relevant controls.
- [x] **Step 3: Build the password sheet.**
  - Require current password, replacement, and confirmation.
  - Validate match and eight-character minimum before submission and show server failures in context.
- [x] **Step 4: Replace Settings' “Próximamente” account row and sidebar initial with the current session/avatar.**
- [x] **Step 5: Run `npm run build` and manually verify mobile and desktop layouts.**

## Chunk 3: End-To-End Verification And Documentation

### Task 4: Validate migrations and close the roadmap item

**Files:**
- Modify: `docs/roadmap/10-perfil-y-password.md`
- Modify: `docs/roadmap/README.md`

- [x] **Step 1: Run `uv run pytest tests/test_auth.py tests/test_migrations.py`.**
- [x] **Step 2: Run `uv run alembic heads` and confirm exactly one head.**
- [x] **Step 3: Run `npm run build`.**
- [x] **Step 4: Mark item 10 complete only after every acceptance criterion has been verified.**
