# 👤 Profile and password change

**Status:** ⬜ Pending · **Priority:** Medium · **Effort:** S (<1 day) · **Dependencies:** None

## Why
Today the user's name and password are immutable from the UI. This is the bare minimum expected of any account, and its absence forces manual DB edits.

## Scope
**Includes:**
- Editing the user's display name.
- Password change with verification of the current one.

**Does not include:**
- Email change (it's the login identity; out of scope for now — documented below).
- Forgotten password recovery (email flow).
- Profile photo or avatar.

## Proposed design
### Backend
- `PATCH /auth/me` with `{name}` → updates the authenticated user's name.
  - **Documented decision: do not include email.** Email is the login identity; changing it implies re-verification and edge cases (collisions across households). Out of scope.
- `POST /auth/change-password` with `{currentPassword, newPassword}`:
  - Verifies `currentPassword`; if it fails, respond `401` (or `400` with a clear code) without revealing more.
  - Validates `newPassword` with a minimum of 8 characters.
  - Re-hashes with the same current hasher.
  - **Recommended decision: existing JWT tokens remain valid** (stateless, no revocation list). Simplicity for a self-hosted family app; invalidating would require a token store or versioning.
### Frontend
- In Settings > Account:
  - Edit name: inline or simple sheet with one field; on save it's reflected in the sidebar/detail view.
  - "Change password": sheet with 3 fields (current, new, confirm new); local validation of match and minimum length; server errors shown in the sheet (e.g. "Current password is incorrect"); haptic feedback on success.
- Invalidate/refetch the user query after both changes (existing pattern in `src/lib/queries.ts`).
### Infra
- No changes.

## Acceptance criteria
- [ ] Changing the name is immediately reflected in the sidebar and account detail view.
- [ ] After changing the password, login with the new one works and the old one is rejected.
- [ ] Incorrect current password returns a clear error shown in the sheet.
- [ ] A new password under 8 characters is rejected with a message.
- [ ] Active tokens keep working after the password change (the session is not closed).
- [ ] Tests: PATCH name, successful change, incorrect current password, length validation.

## Notes
- Risk: none relevant; these are standard endpoints on top of existing auth.
- Open future decision: if password recovery is added, email sending is needed — there is no mail infra today.
- If sessions should be invalidated on password change in the future, add `password_version` to the user and include it in the JWT payload.
