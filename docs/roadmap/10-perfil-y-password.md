# 👤 Profile and password change

**Status:** ✅ 2026-08-04 · **Priority:** Medium · **Effort:** S (<1 day) · **Dependencies:** None

## Why
Today the user's name and password are immutable from the UI. This is the bare minimum expected of any account, and its absence forces manual DB edits.

## Scope
**Includes:**
- Editing the display name and optional profile fields: sex and birth date.
- Optional sex values: `female` (Mujer), `male` (Hombre), `non_binary` (No binario), and `prefer_not_to_say` (Prefiero no indicarlo). Either sex or birth date can be cleared and neither is required.
- Client-side age calculation from the optional birth date; age is displayed but not stored.
- Authenticated avatar upload, replacement, viewing, and removal, stored privately in MinIO.
- Password change with verification of the current password.

**Does not include:**
- Email change (it's the login identity; out of scope for now — documented below).
- Forgotten password recovery (email flow).

## Implemented design
### Backend
- `PATCH /auth/me` updates `name`, optional `sex`, and optional `birthDate` for the authenticated user.
  - **Documented decision: do not include email.** Email is the login identity; changing it implies re-verification and edge cases (collisions across households). Out of scope.
- `sex` accepts only `female`, `male`, `non_binary`, or `prefer_not_to_say` when supplied; `null` clears it.
- `birthDate` is optional and may be cleared. When supplied, it cannot be in the future or more than 120 years ago.
- `POST /auth/change-password` with `{currentPassword, newPassword}`:
  - Verifies `currentPassword`; an incorrect password returns `401` without ending the current session.
  - Validates `newPassword` with a minimum of 8 characters.
  - Re-hashes with the same current hasher.
  - **Intentional decision: existing JWT tokens remain valid** (stateless, no revocation list). Simplicity for a self-hosted family app; invalidating would require a token store or versioning.
- `POST /auth/me/avatar`, `GET /auth/me/avatar`, and `DELETE /auth/me/avatar` require authentication. The blob is not exposed by a public URL; reads return `Cache-Control: private, no-store`.
- Avatar input must be an image no larger than 2 MiB, 8,192 pixels per dimension, and 16 megapixels. Valid images are decoded, RGB-converted, center-cropped/resized to 512×512, and stored as WebP.
- Each upload uses a new immutable MinIO object key. Avatar writes and removals lock the user row, serializing concurrent changes; after the database pointer changes, the previous object is removed best-effort.
### Frontend
- In Settings > Account:
  - Edit name, optional sex, and optional birth date; calculate and show the age locally from the selected date.
  - Upload, replace, or remove an avatar. The UI applies the same image type and 2 MiB checks before upload.
  - "Change password": sheet with current, new, and confirmation fields; local matching and minimum-length validation; a `401` current-password error is shown in the sheet while the session remains active.
- Refresh the authenticated user state after profile and avatar changes.

## Acceptance criteria
- [x] Changing the name is immediately reflected in the sidebar and account detail view.
- [x] Sex and birth date are optional, can be cleared, and validate the accepted sex values and birth-date range; the displayed age is calculated client-side.
- [x] An authenticated user can upload, replace, view, and remove a private MinIO avatar; invalid, oversized, or excessive-dimension images are rejected and accepted images are stored as normalized WebP.
- [x] Concurrent avatar updates are serialized and each replacement uses a new immutable object key.
- [x] After changing the password, login with the new one works and the old one is rejected.
- [x] Incorrect current password returns `401`, is shown clearly in the sheet, and keeps the current session active.
- [x] A new password under 8 characters is rejected with a message; active JWTs intentionally remain valid after the change.
- [x] Tests cover profile fields and validation, the avatar lifecycle and failure cases, password changes, incorrect current passwords, and password length validation.

## Notes
- Avatar objects are private blobs rather than public URLs, preventing unauthenticated object access through the application.
- Open future decision: if password recovery is added, email sending is needed — there is no mail infra today.
- If sessions should be invalidated on password change in the future, add `password_version` to the user and include it in the JWT payload.
