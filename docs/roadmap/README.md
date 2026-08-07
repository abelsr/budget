# 🗺️ Roadmap — budget

One file per pending item, with its why, scope, proposed design, and acceptance
criteria. When tackling one: read it in full, update its **Status** to
🚧 In progress, and when done, mark it ✅ with the date.

> **Progress:** 16 of 17 done (01–14, 16, 19) · last updated 2026-08-06

## Immediate — robustness

| # | Document | Status | Priority | Effort |
|---|---|---|---|---|
| 01 | [Alembic: migrations](01-alembic-migraciones.md) | ✅ 2026-07-24 | High | M |
| 02 | [Invitations end-to-end](02-invitaciones-end-to-end.md) | ✅ 2026-07-24 | High | S |
| 03 | [Installable PWA](03-pwa-instalable.md) | ✅ 2026-08-05 | Medium | M |
| 04 | [Backups](04-backups.md) | ✅ 2026-07-26 | Medium | S |
| 05 | [Plane-style onboarding](05-onboarding.md) | ✅ 2026-07-24 | High | M |

## Phase 2 — features

| # | Document | Status | Priority | Effort |
|---|---|---|---|---|
| 06 | [Recurring transactions](06-transacciones-recurrentes.md) | ✅ 2026-07-25 | High | M |
| 07 | [Monthly budgets](07-presupuestos-mensuales.md) | ✅ 2026-07-25 | High | M |
| 08 | [CSV import](08-importacion-csv.md) | ✅ 2026-08-06 | Medium | L |
| 09 | [Filters and search](09-filtros-busqueda.md) | ✅ 2026-08-04 | Medium | S |
| 10 | [Profile and password change](10-perfil-y-password.md) | ✅ 2026-08-04 | Medium | S |

## Phase 3 — growth

| # | Document | Status | Priority | Effort |
|---|---|---|---|---|
| 11 | [Savings goals](11-metas-de-ahorro.md) | ✅ 2026-08-05 | Medium | M |
| 12 | [Personal accounts](12-cuentas-personales.md) | ✅ 2026-08-05 | Low | M |
| 13 | [Offline-first](13-offline-first.md) | ✅ 2026-08-05 | Low | L |
| 14 | [Multi-family opening](14-multi-familia.md) | ✅ 2026-08-05 | Low | L |

## Production

| # | Document | Status | Priority | Effort |
|---|---|---|---|---|
| 16 | [CI with GitHub Actions](16-ci-github-actions.md) | ✅ 2026-07-24 | Medium | M |
| 17 | [Monitoring](17-monitoreo.md) | ⬜ | Low | S |
| 19 | [Account reconciliation](19-conciliacion-de-cuentas.md) | ✅ 2026-08-06 | High | M |

## Suggested attack order

`02 ✅ → 01 ✅ → 05 ✅ → 16 ✅ → 06 ✅ → 07 ✅ → 04 ✅ → 09 ✅ → 10 ✅ → 03 ✅ → 11 ✅ → 12 ✅ → 13 ✅ → 14 ✅ → 08 ✅ → 19 ✅`

Invitations and onboarding completed the family experience; Alembic, CI, and
backups harden it for production; recurring transactions, budgets, and filters
are the features with the most daily impact.

## Next product cycle — financial integrity and household planning

The competitive review on 2026-08-05 confirmed the product's position as a
private, self-hosted finance app for Spanish-speaking households. The next
cycle should strengthen the correctness and usefulness of the financial ledger
before adding more visual polish, bank aggregation, or generative AI.

| Order | Initiative | Why now | Dependency | Status |
|---|---|---|---|---|
| 1 | **Transfers between accounts** | Moving money must not distort income, expenses, budgets, or reports. | None | ✅ 2026-08-05 |
| 2 | **CSV statement import** | Removes the main adoption and migration barrier without requiring a banking-data provider. | Transfers: imported transfers must be representable correctly. | ✅ 2026-08-06 |
| 3 | **Account reconciliation** | Lets a household verify that its ledger agrees with the bank after manual entry or import. | CSV import | ✅ 2026-08-06 |
| 4 | **Merchants and categorization rules** | Prevents repetitive categorization and improves the quality of reports and budgets. | CSV import | Proposed |
| 5 | **Split transactions** | A single purchase can belong to several categories; forcing one category makes budgets inaccurate. | Transfers and report invariants | Proposed |
| 6 | **Monthly budgets and optional rollover** | Turns global category limits into a real monthly planning tool. | Transfers and split transactions excluded from budget math | Proposal A2 |
| 7 | **Alerts and cash-flow calendar** | Makes budgets, goals, recurring rules, and upcoming bills proactive. | Reliable transactions and monthly budgets | Proposal A5 + proposed forecast |
| 8 | **Goal plans** | Adds due dates, required periodic contributions, and pause/resume to the shipped manual goals. | Alerts | Proposed |
| 9 | **Mexican card and instalment support** | Track statement dates, payment dates, and months-without-interest purchases. | Transfers, recurrence, and cash-flow forecast | Proposed |

### Deliberately deferred

- **Bank aggregation:** it adds regulatory, privacy, operational, and support
  costs that conflict with the current self-hosted scope. CSV import plus
  reconciliation solves the immediate user problem first. Re-evaluate only
  after validating sustained household usage or a managed-service direction.
- **Generative financial advice:** do not generate recommendations until
  transfers, imports, merchant normalization, and reconciliation make the
  underlying data trustworthy.
- **Additional dashboard widgets:** existing reports and four export formats
  are sufficient while ledger correctness and planning features are incomplete.
- **Full zero-based/envelope budgeting:** consider it later as an advanced,
  opt-in mode; it should not replace the current low-friction monthly budget
  experience by default.

**Operational prerequisite:** complete **17 — Monitoring** before exposing a
self-hosted instance publicly. It is independent from the product sequence and
may be implemented in parallel.

### Confirmed architecture decisions

- Keep the current stack for this cycle: FastAPI, SQLAlchemy, Alembic,
  PostgreSQL, React/Vite, TanStack Query, and the existing IndexedDB outbox.
  Do not add a banking-data provider or a new service merely for these flows.
- Represent a transfer with a `transfer_groups` record and exactly two linked
  transaction rows. The UI is a single action, but each account retains one
  independently reconcilable ledger entry.
- Preserve CSV provenance through auditable import batches, deterministic row
  fingerprints, immutable normalized source snapshots, and edit history. Do
  not retain the original uploaded CSV by default; add local object storage for
  it only when a user-facing retention option is explicitly introduced.
- Keep imported and reconciled transactions editable. Changes preserve their
  provenance and mark any affected reconciliation session as stale instead of
  locking the user out.
- Revert an import batch through a shared transaction soft-delete mechanism
  (`deleted_at` plus a reason), never through hard deletes or compensating
  movements. Reversal is atomic and excluded rows remain available for audit
  and possible restoration.

## Log

**2026-08-06 — 19 (account reconciliation) completed.**

- Accounts support one open reconciliation at a time. A session compares its statement date and closing balance against the account opening balance plus every selected ledger entry, and cannot complete until the four-decimal difference is exactly zero.
- Ledger entries can be marked or unmarked while the session is open. Transfer rows remain independent, so each account side is reconciled against its own statement.
- Completed sessions become explicitly stale when an included transaction is edited, deleted, soft-deleted by an import revert, or restored. The history remains visible for review instead of silently claiming that the account is still reconciled.
- Account access uses the existing shared/personal visibility rules. Backend tests passed (173; 12 PostgreSQL-dependent migration tests skipped without a configured test database); frontend lint and production build passed.

**2026-08-06 — 08 (CSV statement import) completed.**

- CSV imports use a three-step upload, review, and result flow. The server reparses the uploaded file on commit, so user-approved previews cannot be tampered with client-side.
- Import batches keep normalized source rows, immutable transaction baselines, advisory duplicate reasons, edit events, deterministic account-scoped fingerprints, and reversible soft deletion. Uploaded CSV bytes are never stored.
- A reverted import is excluded from balances, reports, budgets, attachments, and normal transaction access. Revert is atomic, conflicts when an imported movement changed, and restore preserves the original provenance.
- PostgreSQL is now the only runtime and Alembic migration target. SQLite remains limited to in-memory `create_all` unit tests.
- Backend tests passed (168; 12 PostgreSQL-dependent migration tests skipped when no test database URL is configured); CSV import tests passed (18). Frontend lint and production build passed; Fast Refresh and bundle-size warnings predate this work.

**2026-08-05 — 03 and Phase 3 (11–14) completed.**

- **03 PWA:** added an installable manifest, generated 192/512/maskable and Apple icons, an auto-updating service worker that precaches only the shell, and nginx headers that revalidate `sw.js`. `/api` is explicitly excluded from the navigation cache.
- **11 Goals:** household-scoped manual savings goals now support CRUD, atomic positive or negative contributions, capped progress, account unlinking on deletion, and a dismissible completion state. Goals only link shared accounts, so they cannot disclose a member's personal account.
- **12 Personal accounts:** accounts can be shared or personal. Visibility, transactions, attachments, recurring rules, budgets, summaries, exports, and category deletion all enforce the account boundary; the household owner controls shared-to-personal conversion and the personal owner controls the reverse.
- **13 Offline-first:** simple one-time transactions use a user-scoped IndexedDB outbox and an idempotent `clientId`; automatic retries flush on reconnection, focus, and interval. Query snapshots are persisted per authenticated user, and failed 4xx items remain visible without blocking later entries.
- **14 Self-host scope:** selected self-hosted hardening rather than a public managed service. It adds configurable member/invitation caps, process-local auth and scanner limits, `email_verified` for future activation, a public privacy page, and deployment guidance for HTTPS, CORS, and JWT secrets.
- Backend tests passed (145); frontend build and lint, Docker Compose validation, and diff validation passed. Android/iOS installation, Lighthouse, and real HTTPS/offline-device validation remain deployment checks, not unmet implementation work.

**2026-08-04 — 10 (profile and password change) completed.**

- Profile editing now includes optional sex and birth date (with client-side age calculation), plus authenticated avatar upload, replacement, and removal.
- Avatar blobs stay private in MinIO: uploads are normalized to WebP, use immutable object keys, and avatar writes are serialized to avoid concurrent replacement races.
- An incorrect current password returns `401` without closing the session; existing stateless JWTs intentionally remain valid after a password change.

**2026-08-04 — 09 (filters and search) completed.**

- The feature was already present in the application; the roadmap had not been
  updated after its implementation.
- `GET /transactions` combines note search, category, account, member, type,
  and date-range filters. The UI debounces note search by 300 ms, synchronizes
  every filter with the URL, and exposes removable active-filter chips.
- `month` and `from`/`to` are now explicitly incompatible (`422`), rather than
  silently giving `month` precedence. A composite
  `transactions(household_id, date)` index was added for the filtered ledger.

**2026-07-26 — 04 (backups) implemented, and the restore verified end to end.**

- **The doc's own definition of "clean stack" was wrong**, and it mattered:
  the backend runs Alembic on startup, so a fresh deployment already has the
  schema at head and a plain `pg_dump` restore fails. The dump needed
  `--clean --if-exists`. Found by actually building the clean stack first and
  looking at it, instead of trusting the phrase.
- **A bind mount for the MinIO tar is a docker-in-docker trap.** `-v
  ./backups:/backup` is resolved by the host daemon, so the doc's command would
  have written nowhere useful when run from the optional `backup` compose
  service. Streaming `tar cz` to stdout makes one code path correct in both
  contexts. Moral: a path handed to `docker run` and a path the script writes to
  are not the same namespace.
- **Postgres credentials come from the running container, not `.env`.** The doc
  said `.env`; the compose file sets them literally and `.env` never had them.
- Artifacts are written as `*.part` and renamed only on success, so an
  interrupted run cannot leave a truncated file that passes for a backup.
- **Restore verified against a throwaway compose project**
  (`-p budget-restoretest`, its own volumes, ports 18000/18081) running beside
  the real stack, which was never touched. After restoring: all seven table
  counts identical, `alembic_version` at head with nothing to migrate, and both
  MinIO volumes byte-identical file by file. Then logged into the restored app
  in the browser at 440px — balances ($17,652.50 / $23,985.01), income/expense,
  donut, all three transactions, and the 7.4 MB receipt opening and decoding at
  full resolution. Only console output was a pre-existing Recharts mount
  warning.
- To log in, a password was reset **on the disposable copy only**; the real
  hash was confirmed afterwards to still match the one in the pre-test dump.
  The test project, its volumes, and its images were all removed.
- Left alone deliberately: `.env.example` is still in Spanish (the
  translate-to-english pass missed it) and one of the two `attachments` rows has
  no object in MinIO — a pre-existing orphan, present identically in the real
  volume and therefore not caused by the backup.

**2026-07-25 — 07 (monthly budgets) implemented and verified against a real Postgres.**

- **Plain CRUD instead of a literal upsert endpoint.** The doc suggested
  `POST`/`PATCH` "upsert by category_id", but every other router in this app
  (`categories`, `accounts`, `recurring-rules`) does plain
  `POST`/`PATCH`/`DELETE` and relies on a DB unique constraint + a 409 for
  duplicates. Kept that convention instead of inventing a new pattern.
- **Category picker is a pill selector, not a literal `<select>`.** Nothing
  in the app uses the raw `ui/select.tsx` for choosing a category — pills
  (accounts) and icon grids (categories) are the established idiom.
- **Deleting a category with a budget now cascades the budget row**, instead
  of blocking the delete the way it blocks deletion when transactions exist.
  A budget isn't a historical movement; there's nothing to preserve.
- **The empty state needed a "+" affordance.** A bare `null` return (like
  `DonutCard` when there's no data) would have left no way to ever create the
  first budget, since this feature has no dedicated management page.
- Added a `--warning` (iOS system orange) token to `index.css`, matching the
  existing `--income`/`--expense` first-class-token pattern, for the
  75–100% amber band — and a small red count badge on the donut card's
  heading when any category goes over 100%, which was in the original scope
  but easy to miss since it's not part of the new `BudgetsCard` itself.
- **Migrations target PostgreSQL only.** Generated and verified the new
  migration against a throwaway Postgres 17 container: upgrade, downgrade,
  upgrade again, plus all 9 `test_migrations.py` cases. SQLite remains for
  fast `create_all` unit tests only.
- **Verified in the browser against the real database**, using two
  disposable test households (deleted afterward via a transactional
  `DELETE` that left household/user/category/transaction counts identical to
  before). Confirmed bar colors at 73%/80%/110%, the duplicate-category
  guard in the create picker, editing an existing budget, deleting a
  budgeted-but-transaction-free category, the donut badge, and both mobile
  (390px) and desktop (1280px) layouts.

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
  content ended up extracted into `frontend/src/components/InviteLink.tsx` to reuse in the
  wizard, with `InviteSheet` as the drawer wrapper.
- **01 was moved ahead of 05.** The wizard adds a column to `users` and `create_all`
  doesn't alter existing tables: without migrations, the deployment's database would have
  ended up without the column. Doc 05 already listed 01 as a dependency, but the suggested
  order in this index didn't reflect it.
- Since a database created with `create_all` already existed, `backend/app/db_bootstrap.py`
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
  the root one, which is 41 characters); harden it before any public deployment.
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
