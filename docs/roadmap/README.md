# 🗺️ Roadmap — Family Finances

One file per pending item, with its why, scope, proposed design, and acceptance
criteria. When tackling one: read it in full, update its **Status** to
🚧 In progress, and when done, mark it ✅ with the date.

> **Progress:** 5 of 17 done (01, 02, 05, 06, 16) · last updated 2026-07-25

## Immediate — robustness

| # | Document | Status | Priority | Effort |
|---|---|---|---|---|
| 01 | [Alembic: migrations](01-alembic-migraciones.md) | ✅ 2026-07-24 | High | M |
| 02 | [Invitations end-to-end](02-invitaciones-end-to-end.md) | ✅ 2026-07-24 | High | S |
| 03 | [Installable PWA](03-pwa-instalable.md) | ⬜ | Medium | M |
| 04 | [Backups](04-backups.md) | ⬜ | Medium | S |
| 05 | [Plane-style onboarding](05-onboarding.md) | ✅ 2026-07-24 | High | M |

## Phase 2 — features

| # | Document | Status | Priority | Effort |
|---|---|---|---|---|
| 06 | [Recurring transactions](06-transacciones-recurrentes.md) | ✅ 2026-07-25 | High | M |
| 07 | [Monthly budgets](07-presupuestos-mensuales.md) | ⬜ | High | M |
| 08 | [CSV import](08-importacion-csv.md) | ⬜ | Medium | L |
| 09 | [Filters and search](09-filtros-busqueda.md) | ⬜ | Medium | S |
| 10 | [Profile and password change](10-perfil-y-password.md) | ⬜ | Medium | S |

## Phase 3 — growth

| # | Document | Status | Priority | Effort |
|---|---|---|---|---|
| 11 | [Savings goals](11-metas-de-ahorro.md) | ⬜ | Medium | M |
| 12 | [Personal accounts](12-cuentas-personales.md) | ⬜ | Low | M |
| 13 | [Offline-first](13-offline-first.md) | ⬜ | Low | L |
| 14 | [Multi-family opening](14-multi-familia.md) | ⬜ | Low | L |

## Production

| # | Document | Status | Priority | Effort |
|---|---|---|---|---|
| 15 | [HTTPS with Caddy](15-https-caddy.md) | ⬜ | High | S |
| 16 | [CI with GitHub Actions](16-ci-github-actions.md) | ✅ 2026-07-24 | Medium | M |
| 17 | [Monitoring](17-monitoreo.md) | ⬜ | Low | S |

## Suggested attack order

`02 ✅ → 01 ✅ → 05 ✅ → 16 ✅ → 06 ✅ → 07 → 15 → 04`

Invitations and onboarding completed the family experience; Alembic and HTTPS
harden it for production; recurring transactions and budgets are the features with the most
daily impact.

**16 (CI) was done before 15** because HTTPS is waiting on an infrastructure
decision (custom domain vs. Tailscale) and CI didn't depend on anything.
**06 was also moved ahead of 15** for the same reason: the decision is still
pending and recurring transactions didn't depend on anything.

**Next: 07 — Monthly budgets.** It's the other feature with daily impact
and it builds on categories and transactions, already closed.

**15 (HTTPS with Caddy) is still blocked on a decision, with the path already
chosen: Tailscale** (`tailscale cert` over the tailnet, nothing exposed to the internet,
works behind CGNAT). It still needs to be installed on the host and on the
family's devices — today there's no `tailscale`, `caddy`, or `mkcert` on the host. Besides
closing out the deployment, it enables `navigator.clipboard` on mobile: the
invitation link relies on the `document.execCommand('copy')` fallback because plain HTTP
over IP is not a secure context (see `lib/clipboard.ts`).

## Log

**2026-07-25 — 06 (recurring) implemented and verified against a real Postgres.**

- **The doc's design lost track of the 31st.** It said "January 31 → February 28",
  but storing 28 in `next_run_date` makes March start from there: rent
  would move to the 28th forever. The **anchor day** had to be stored in the rule.
  Moral: when clamping a date, the clamped date can't be the stored state.
- **Lazy materialization can't live in a single endpoint.** The doc put it
  in `GET /transactions`, but the Dashboard fires accounts, transactions, and
  summary **in parallel**: the balance came out stale on first load. It's now in
  all three (and in the rule listing). The service is idempotent, so it
  costs nothing.
- **Avoiding duplication needed `SELECT ... FOR UPDATE`.** The doc reasoned about
  sequential requests ("re-reading doesn't duplicate"), and that's true; the gap was
  **concurrent** requests, which in this app are the norm, not the exception — three per
  Dashboard load. Verified with 8 simultaneous requests against
  Postgres 17: 4 occurrences, zero duplicates.
- **"Resuming from the correct date" wasn't defined.** Jumping forward was
  the choice made: someone who paused in March doesn't want four months of rent
  all at once when resuming in July.
- A cap was added: `next_run_date` can't be more than a year in the past. Without
  it, a date from years ago would generate hundreds of transactions on the first
  read.
- A migration test was added for the **`created_by_id` backfill**: it was
  the only branch no test touched, and it runs on every deployment.
- **Deployed and verified in the browser.** Before migrating, `pgdata` and
  `minio_data` were backed up to `./backups/` (ignored by git) — the real database has
  no safety net until doc 04 is done. The migration ran on its own
  at container startup and the data remained intact. Verification
  used a **separate test household**, deleted afterward, leaving the database with the
  same counts as the backup. Confirmed on mobile (440px): entry with
  "Repeat", catch-up of 4 overdue weeks on reload, icon in the list,
  badge in the detail view, pause/resume/delete, and zero duplicates after three
  loads (nine concurrent requests). No console errors.
- `recurring_rules` was empty in the real database, as the migration assumed.

**2026-07-24 — 01, 02, and 05 done and verified in the browser.**

- **02** was almost entirely UI: the invitations backend already existed with tests. Its
  content ended up extracted into `components/InviteLink.tsx` to reuse in the
  wizard, with `InviteSheet` as the drawer wrapper.
- **01 was moved ahead of 05.** The wizard adds a column to `users` and `create_all`
  doesn't alter existing tables: without migrations, the deployment's database would have
  ended up without the column. Doc 05 already listed 01 as a dependency, but the suggested
  order in this index didn't reflect it.
- Since a database created with `create_all` already existed, `app/db_bootstrap.py`
  detects it (tables without `alembic_version`) and stamps it instead of re-creating it.
  **This bridge is temporary**: it will be removed once no pre-Alembic databases remain.
- The column migration **backfills** existing users; otherwise,
  anyone who already had their household set up would see a wizard that doesn't apply to them.

**The only thing left unverified:** `prefers-reduced-motion` in the wizard (doc
05). It comes from the `MotionConfig reducedMotion="user"` that already wraps the app, but the
media query couldn't be emulated; it's worth confirming manually on the system.

**2026-07-24 (cont.) — 16 (CI) implemented, awaiting the first run.**

- Two gaps showed up while writing the README: there was no README at the root nor
  a root `.env.example` (and `plan.md` claimed there was). Both were created.
- `backend/.env` has a 20-character `JWT_SECRET`: that's the source of the
  `InsecureKeyLengthWarning` in the tests. It only affects local dev (Docker uses
  the root one, which is 41 characters), and hardening it falls within the scope of **15**.
- A **migrations-against-real-Postgres job** (8 tests) was added to CI that
  wasn't in doc 16's scope: the docker job built the image but
  no one ran a migration, and that's exactly the risk of breaking the database when
  deploying. It includes verifying data survives the upgrade and that the
  pre-Alembic bridge doesn't re-create tables. That's why 16 went from effort S to M.
- **The first run failed:** `setup-uv` doesn't publish a major tag beyond
  `v7`, even though its releases are up to `v9`. To pin an action you have to check
  the **tag ref**, not the release. Fixed with the exact `@v9.0.0`; the second
  run passed all 4 jobs and the badge reads `passing`.
- **Branch protection active on `main` (2026-07-25)**, strict and including the
  owner: the 4 checks are required and it's no longer possible to push directly to
  `main`. The workflow is now branch → PR → merge when green. It was applied with
  `gh api`, not via the web UI. Details and how to revert it are in doc 16.
