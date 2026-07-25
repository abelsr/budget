# 🧭 Plane-style onboarding (initial wizard)

**Status:** ✅ Done and verified (2026-07-24) · **Priority:** High · **Effort:** M (1-3 days) · **Dependencies:** 02-invitaciones-end-to-end (reuses link generation), 01-alembic-migraciones (needed to add the new column without breaking existing DBs)

## Why
Today, after registering, the user lands directly on an empty dashboard with only the "Cash" account at $0 and no guidance. This is the classic adoption friction: they don't know what to do first and they abandon. Plane solves this with a setup wizard (create workspace → invite the team → tour). We copy that pattern adapted to family finances: welcome → initial accounts → invite family → get started.

## Scope
**Includes:**
- Per-user onboarding flag (persisted on the backend)
- `/onboarding` route with a 4-step wizard, visible progress and spring animations
- Creating initial accounts with a balance inside the wizard
- Generating an invitation link inside the wizard
- Skip option available at all times

**Doesn't include:**
- Interactive dashboard tour after the wizard (future phase)
- Importing historical transactions or category templates in the wizard
- Onboarding for members who join via invitation (they go straight in)

## Proposed design

### Backend
- **Decision: the flag lives on `User`, not on `Household`.** Rationale: the wizard is an experience for the user who registers by creating a new household. If it lived on `Household`, a second member who joins later would inherit the admin's state (they wouldn't see it, which is correct), but there would also be no way to distinguish "who has already been through here" if per-member onboarding is wanted in the future. With the flag on `User`, the wizard is shown **only to whoever registers by creating a new household**; whoever joins via invitation is marked as completed automatically upon registering.
- `User` model: add `onboarding_completed_at: DateTime` (nullable). `NULL` = pending. Requires a migration (see dependency on `01-alembic-migraciones.md`).
- `GET /auth/me`: include the flag in the response (e.g. `onboarding_completed: bool` derived from `onboarding_completed_at IS NOT NULL`).
- `PATCH /auth/me/onboarding` with body `{ "completed": true }`: sets `onboarding_completed_at = now()`. Idempotent.
- When registering with an invitation (`/auth/register` with an invitation token): mark `onboarding_completed_at` immediately — no need for the wizard.
- Tests: new cases for the PATCH, the flag in `/auth/me`, and the different behavior between normal registration vs. invitation.

### Frontend
- Protected `/onboarding` route. In `RequireAuth` (which already handles `isLoading`): if the authenticated user has `onboarding_completed === false`, redirect to `/onboarding`; once completed, redirect to the dashboard. Avoid a loop: `/onboarding` itself does not redirect.
- Plane-style 4-step wizard, with a progress indicator (dots or bar) and spring transitions (enter/exit along the same path, Apple-style; reuse the animation library already present in the project — e.g. framer-motion/spring — and respect `prefers-reduced-motion`):
  1. **Welcome:** "Welcome to Family Finances, \<name\>" + 3 bullets with icons about what the app can do (log transactions, scan receipts, share with your family).
  2. **Your accounts:** editable list of initial accounts with a balance. "Cash" already exists → show it pre-loaded; allow adding Debit / Credit / Savings (or others) with a name and initial balance. Uses the existing `useCreateAccount` hook.
  3. **Invite your family:** generates the invitation link with one tap (`POST /households/me/invitations`), copy/share buttons (same UI as `02-invitaciones-end-to-end.md`) and a "I'll do this later" option.
  4. **Done:** brief summary (accounts created, invitation sent or pending) + "Get started" button that calls `PATCH /auth/me/onboarding` and navigates to the dashboard.
- Skip always visible: "Set up later" → calls the same PATCH and navigates to the dashboard (the wizard doesn't show again).
- Compatible with dark mode (the wizard uses the same theme tokens as the rest of the app).

### Infra
- No changes (the new column arrives via an Alembic migration)

## Acceptance criteria
- [x] A new user who creates a household sees the wizard the first time; reloading the page doesn't repeat it or break it
- [x] In step 2 they can create at least 1 account with an initial balance and it later shows up in Accounts
- [x] In step 3 they can generate and copy the invitation link (same behavior as in Settings)
- [x] Skip ("Set up later") is available on all steps and marks the flag
- [x] A user who registers with an invitation link does NOT see the wizard (goes straight to the dashboard)
- [x] Dark mode is respected across all 4 steps
- [ ] With `prefers-reduced-motion` enabled, transitions are reduced/removed — **not tested**: it relies on the `MotionConfig reducedMotion="user"` that already wraps the whole app, but the media query could not be emulated with the tools used
- [x] The new backend tests pass and the 37 existing ones keep passing (41 total)

## What was implemented (2026-07-24)

**Backend**
- `User.onboarding_completed_at` (nullable; NULL = pending) + migration
  `673ed5f3d911`. The migration **backfills**: users who already existed
  are marked as completed, because their household is already set up and they
  don't need the wizard on deploy.
- `GET /auth/me` returns `onboardingCompleted` (derived from the date).
- `PATCH /auth/me/onboarding` with `{completed}`: idempotent (repeating it doesn't
  move the stored date) and accepts `false` to reopen it.
- `POST /auth/join` sets the flag when creating the member: whoever arrives via
  invitation goes straight to the dashboard.
- 4 new tests (41 total): registration leaves it pending, PATCH idempotent,
  reopening, and 401 without a token. `test_join_flow` covers the invitation case.

**Frontend**
- `frontend/src/pages/OnboardingPage.tsx`: 4-step wizard (welcome → accounts → family
  → done), 4-segment progress bar, directional horizontal transition
  (enters and exits along the same path) with `AnimatePresence` and
  springs, "Set up later" always visible in the header.
  - Step 2 reads accounts from the backend (`useAccounts`), so "Cash" already
    shows up and reloading mid-wizard doesn't duplicate anything; the inline form
    creates via `useCreateAccount`.
  - Step 4 summarizes accounts created and invitation generated or pending.
- `components/InviteLink.tsx`: the content of task 02's `InviteSheet` was
  extracted to reuse it. `autoGenerate` distinguishes the two uses: in the sheet,
  opening it is already the gesture, in the wizard there's an explicit button so
  as not to leave stray invitations when passing through the step.
- `lib/auth.tsx`: `Session.onboardingCompleted` + `completeOnboarding()`.
- `App.tsx`: `/onboarding` route outside the `AppShell` (full screen) and
  a guard in `RequireAuth` in both directions — without the flag completed everything
  redirects to the wizard, with the flag completed `/onboarding` redirects to the dashboard. Nothing
  is decided before `/auth/me` resolves, so there's no loop or flicker.
- Dark mode and `prefers-reduced-motion` come for free: just theme tokens and the
  `MotionConfig reducedMotion="user"` that already wraps the app.

**Verified:** 41 tests pass, `tsc -b && vite build` clean, `oxlint` with no
new warnings, migration with `upgrade`/`downgrade`/`check` on SQLite and Postgres.

**Browser walkthrough (2026-07-24, stack in Docker, 430×900 viewport):**
- New registration → redirects to `/onboarding` with "Welcome, Sofía".
- Step 2: "Cash" pre-loaded; "Nómina BBVA" was created with $15,750.50.
- Reload mid-wizard: stays in the wizard, restarts at step 1 and the
  accounts remain at 2 (no duplicates).
- Step 3: link generated with an absolute URL and the correct expiration ("July 31");
  "Copy link" → button shows "Copied" and `navigator.clipboard.readText()`
  returned the exact link. "Share" doesn't render on desktop (no
  `navigator.share`), as designed.
- Step 4: "2 accounts ready" / "Invitation ready to share" → "Get started" →
  dashboard with a $15,750.50 balance (the wizard's account persisted).
- `/onboarding` visited manually after completing it → redirects to the dashboard. With onboarding
  pending, going to `/accounts` redirects to the wizard. No loops or flicker.
- "Set up later" on step 1 → dashboard, and `/onboarding` no longer opens.
- Invitation end-to-end in an isolated context: a second user registered with the
  link and went **straight to the dashboard, no wizard**; Settings > Household shows the
  2 members. Reusing the consumed link → "Invalid or expired invitation".
- Themes: steps 1 and 4 in dark mode, 2 and 3 in light mode; the Settings sheet in light mode with
  its translucent material. No errors or warnings in the console.

## Notes
- UX inspiration: Plane's setup wizard (https://plane.so) — linear progress, one step at a time, skip always available.
- Risk: a poorly implemented redirect in `RequireAuth` can create loops or flicker; rely on the existing `isLoading` and don't decide the route until `/auth/me` has resolved.
- Open decision: allow re-opening the wizard from Settings ("Repeat initial setup")? Not included in scope; if it comes up, it's a button that resets the flag.
- If step 2 creates accounts and the user reloads mid-wizard, the already-created accounts must not get duplicated on return (load existing accounts when entering step 2 instead of assuming empty state).
