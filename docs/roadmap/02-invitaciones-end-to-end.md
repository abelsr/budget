# ✉️ Invitations end-to-end

**Status:** ✅ Done and verified (2026-07-24) · **Priority:** High · **Effort:** S (<1 day) · **Dependencies:** None

## Why
This is a **family** finance app, but today there's no way to add members from the UI: the "Invite member" button in Settings is disabled with the text "Coming soon". However the API (`POST /households/me/invitations`) and the join screen (`/login?invite=TOKEN`) already exist and work. All that's missing is connecting the dots on the frontend.

## Scope
> **Superseded administration policy (2026-08-05):** invitations and membership
> administration are now owner-only. The owner can create, list, and revoke
> active invitations and can remove another member; all active members can view
> the member directory. The historical scope below describes the original
> invitation-link delivery work.

**Includes:**
- Enable the "Invite member" button in Settings > Household
- Show the full invitation link with copy and share buttons
- Indicate the link's expiration (7 days)

**Doesn't include:**
- Revoking active invitations *(at the time; superseded by the owner policy above)*
- Roles/permissions per member *(at the time, everyone was equal; superseded by
  the owner policy above)*
- Sending the link by email (self-hosted without SMTP; the user shares the link through their own channel)

## Proposed design

### Backend
- No mandatory changes: `POST /households/me/invitations` already creates the invitation and returns the token
- *(Optional)* `GET /households/me/invitations` to list active invitations (useful for showing "pending links" in the UI). If implemented, mark expired and used ones in the response

### Frontend
- Settings > Household: enable the "Invite member" button (remove the disabled state and the "Coming soon" text)
- On click: call `POST /households/me/invitations`, build the full link `https://<host>/login?invite=<TOKEN>` using `window.location.origin`
- Show the link in a read-only field with:
  - **Copy** button (`navigator.clipboard.writeText`) with visual feedback ("Copied")
  - **Share** button if `navigator.share` exists (mobile); hide it otherwise
- Show expiration text: "Valid for 7 days"
- Verify that the existing `/login?invite=TOKEN` flow ("Join" mode) still works without changes

### Infra
- No changes

## Acceptance criteria
- [x] From Settings > Household you can generate an invitation link with one click
- [x] The link gets copied to the clipboard (on desktop; the Share button only appears if `navigator.share` exists, not verified on a real mobile device)
- [x] Opening the link in an incognito window lets you register a second user
- [x] Settings > Household shows the 2 members after registration
- [x] Reusing an already-consumed link shows the user a clear error ("Invalid or expired invitation")

## What was implemented (2026-07-24)

Frontend only; the backend (`POST /households/me/invitations`, `POST /auth/join`)
was already complete and had tests.

- `frontend/src/lib/queries.ts`: `Invitation` type + `useCreateInvitation` hook.
- `frontend/src/lib/clipboard.ts`: `copyText()` with a fallback to
  `document.execCommand('copy')` for plain HTTP over IP (no secure context).
- `frontend/src/components/InviteSheet.tsx`: a bottom sheet that generates the link
  when opened, shows it in a read-only field (select-all on focus),
  **Copy** button (2s "Copied" feedback), **Share** button (only if
  `navigator.share` exists), and **Generate another link**; expiration text with the
  real date derived from `expiresAt`; skeleton while loading and error message.
- `frontend/src/pages/SettingsPage.tsx`: "Invite member" button enabled
  (`disabled` and "Coming soon" removed) opening the sheet.

**Verified:** `tsc -b && vite build` clean, `oxlint` with no new warnings, the
37 pytest tests still pass. Browser walkthrough with the stack in Docker
(see detail in `05-onboarding.md`): link generated from Settings, copied to the
clipboard, second user registered in an isolated context, 2 members shown in
Settings, and a clear error when reusing the link.

**Note:** in step 05 this content was extracted into `frontend/src/components/InviteLink.tsx`
to reuse it in the wizard; `InviteSheet` now just wraps it in the drawer.

## Implementation and verification (2026-08-05)

- **Endpoints and policy:** `GET /households/me/members` is available to every
  active household member as a read-only directory. Only the owner may use
  `POST`/`GET /households/me/invitations`, `DELETE
  /households/me/invitations/{invitation_id}`, and `DELETE
  /households/me/members/{member_id}`. The owner cannot remove themself.
- **UI:** Settings exposes a Household Members drawer to all active members.
  It shows the directory to everyone and shows invitation creation, active
  invitation listing/revocation, and removal controls only to the owner.
- **Invitation lifecycle:** creation, listing, consumption, and revocation
  apply the active-invitation rules (unused and unexpired); consumption and
  revocation serialize their state transition by locking the invitation row.
- **Removal and history:** removing a member detaches their household
  membership without changing the transaction author, so historical records
  retain their attribution.
- **Verification:** backend coverage verifies the owner-only API policy,
  directory access, self-removal rejection, invitation lifecycle lock intent
  and state transitions, and retained transaction attribution after removal.
  Real concurrent PostgreSQL behavior remains CI/deployment verification
  pending.

## Notes
- Registration via invitation already exists on the login screen ("Join" mode reading `?invite=TOKEN`); this task is mostly UI.
- Minor risk: `navigator.clipboard` requires a secure context (HTTPS or localhost); over plain HTTP by IP it may fail. Provide a fallback with `document.execCommand('copy')` or manual selection of the field.
- This functionality is reused in step 3 of the onboarding wizard (see `05-onboarding.md`).
