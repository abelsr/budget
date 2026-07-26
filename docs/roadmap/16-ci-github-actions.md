# ⚙️ CI with GitHub Actions

**Status:** ✅ Done and verified (2026-07-24) · **Priority:** Medium · **Effort:** S (<1 day) · **Dependencies:** None

## Why
The repo is already on GitHub and has 37 tests, but nothing runs them automatically: a push can break the backend or the frontend build without anyone noticing until the next deploy. Basic CI turns "I think it passes" into "it's green," and it's the foundation for any future collaboration (even with yourself on another machine).

## Scope
**Includes:**
- GitHub Actions workflow with 2 jobs: backend (uv + pytest) and frontend (node + build)
- *(added beyond the original scope)* a migrations job against real Postgres
- Dependency caching (uv and npm) for fast runs
- Status badge in the README
- Optional: a job that builds both Docker images without pushing (validates the Dockerfiles)

**Excludes:**
- Automatic deploy (CD) to the self-hosted server
- Strict lint/typecheck as a gate (can be added later; don't block the initial CI with existing debt)
- ~~Integration tests with real Postgres in CI~~ → **was actually included**, but only for migrations: the business logic tests remain on SQLite. See below.
- Publishing images to a registry

## Proposed design

### Backend
- `backend` job: `actions/setup-uv` (or `astral-sh/setup-uv`), `uv sync`, `uv run pytest`
- Cache: the uv action itself caches by `uv.lock`
- Tests run with in-memory SQLite (current fixture); no Postgres service needed in CI

### Frontend
- `frontend` job: `actions/setup-node` with Node 24 and `cache: npm`, `npm ci`, `npm run build`
- The build is the gate: if TypeScript/Vite fails, CI fails (equivalent to "frontend tests" for now)
- Both jobs run in parallel in the same workflow, triggers: push to `main` and pull requests

### Infra
- A single `.github/workflows/ci.yml` file
- Optional `docker` job: `docker compose build` (or two `docker build` per context) to validate that the Dockerfiles aren't broken; mark it as non-blocking at first if the build is slow, and promote it to required later
- README badge: `![CI](https://github.com/<user>/<repo>/actions/workflows/ci.yml/badge.svg)`
- Branch protection on GitHub: require the green check before merging to `main` (web configuration, one click)

## Acceptance criteria
- [x] A push to `main` triggers the workflow and finishes green (run 30137793763: all 4 jobs succeeded)
- [x] A broken test in the backend fails the job and marks the commit red (local canary: `pytest` exited with code 1)
- [x] A TypeScript/build error in the frontend fails its job (injected TS2322 error: `npm run build` exited with code 2)
- [x] Runs with cache take clearly less time than the first run (frontend: 27s cold → 19s with npm cache)
- [x] The README badge reflects the real status of the latest run on `main` (the SVG responds `passing`)

## What was implemented (2026-07-24)

- `.github/workflows/ci.yml` with 3 jobs in parallel, triggers on push to `main` and
  on pull requests, and `concurrency` with `cancel-in-progress` (a new push
  cancels the run of the commit it replaces).
  - **backend:** `astral-sh/setup-uv@v9` with cache keyed on `backend/uv.lock`,
    `uv sync --locked` and `uv run pytest -q`. `--locked` (not `--frozen`) was used
    on purpose: it fails if `uv.lock` doesn't match `pyproject.toml`, something that
    already happened once in this repo.
  - **frontend:** `actions/setup-node@v7` with Node 24 and npm cache, `npm ci`,
    `npm run lint` and `npm run build` (`tsc -b && vite build`).
  - **docker:** `docker compose build`, which covers what the other jobs don't see
    (the Dockerfile's `--frozen`, the migrations entrypoint, the nginx build).
    It's blocking; if the time becomes annoying, limit it to PRs.
  - **migrations:** a `postgres:17-alpine` service (the same version as
    production) + `pytest tests/test_migrations.py`. See the next section.
- **Lint enabled as a gate:** `oxlint` exits with code 0 (its 4 warnings are just
  warnings), so it goes in without generating red noise. Ruff wasn't added: it's
  not a project dependency and the doc left it optional.
- Action versions verified against the GitHub API, not from memory:
  checkout v7, setup-node v7, setup-uv v9, setup-buildx v4.
- **`README.md` at the root** (didn't exist before): CI badge, what the app is, the stack,
  how to start the stack and local dev, tests, and links to the documentation.
- **`.env.example` at the root** (also didn't exist, even though `plan.md` claimed it did):
  template for `JWT_SECRET`, OpenRouter, and MinIO credentials. Without it, anyone
  cloning the repo had no guidance for the `.env` compose needs.

**Verified locally with the workflow's exact commands:** `uv lock
--check` in sync, `uv sync --locked` + `pytest` → 41 pass; `npm ci` from scratch
+ `lint` + `build` clean; `docker compose build` builds both images.
Gates tested by injecting failures and reverting them.

**Branch protection active since 2026-07-25** (applied with
`gh api -X PUT repos/abelsr/budget/branches/main/protection`, no need for the
web UI). Configuration on `main`:

| Setting | Value |
|---|---|
| Required checks | `Backend (pytest)`, `Migraciones (Postgres real)`, `Frontend (typecheck + build)`, `Imágenes Docker` (by their exact `name:`) |
| `strict` (branch must be up to date before merge) | yes |
| `enforce_admins` | **yes — also applies to the repo owner** |
| Force-push and branch deletion | blocked |
| Resolve conversations before merge | yes |
| Required reviews | no (GitHub doesn't allow approving your own PRs; with 1 review required the repo would be locked for a single maintainer) |

**Practical consequence: direct pushes to `main` are over.** The flow now is
branch → push → PR → wait for the 4 checks → merge. A `git push` to `main` is
rejected with `GH006: Protected branch update failed` / `required status checks
are expected`, because the checks can't have run for a commit that
doesn't exist on the remote yet.

If the jobs are renamed in `ci.yml`, the protection's `contexts` need to be updated or
`main` will be stuck waiting on checks that never arrive. To revert it:
`gh api -X DELETE repos/abelsr/budget/branches/main/protection`.

## Notes
- Open decision: lint with ruff (backend) and eslint (frontend) as gates? Recommended to add them in the same file but as separate steps, enabled only once the codebase already passes cleanly — enabling them earlier generates noise and the temptation to ignore CI.
- The docker build job can take several minutes (Python + node images); if it becomes annoying, limit it to PRs instead of every push.
- Don't put secrets in CI: this workflow doesn't need any (no deploy or registry).
- Reference: https://docs.astral.sh/uv/guides/integration/github/

## Migration verification (added 2026-07-24)

The `docker` job builds the image but never ran a migration: the real
risk — breaking the database on deploy — was left uncovered. `tests/test_migrations.py`
closes that gap with 8 tests against real Postgres:

| Test | What it protects |
|---|---|
| `upgrade_head_crea_el_esquema_completo` | Empty database → all 8 tables + `alembic_version` at head |
| `esquema_migrado_coincide_con_los_modelos` | `alembic check`: touching `models.py` without generating the migration fails CI |
| `downgrade_base_deja_la_base_limpia` | The downgrade doesn't leave orphaned tables |
| `upgrade_downgrade_upgrade_es_reversible` | A rollback in production is not a one-way trip |
| `los_datos_sobreviven_a_las_migraciones` | Data inserted at the initial revision is still there at head, with the flag backfill applied |
| `puente_pre_alembic_no_recrea_ni_borra_nada` | The bootstrap stamps and migrates without destroying the old deployment's database |
| `bootstrap_es_idempotente` | Every container startup runs it: running it twice doesn't break anything |
| `base_vacia_no_se_confunde_con_pre_alembic` | A new database doesn't trigger the bridge |

Design details:

- **Isolation:** each test creates its own database (`CREATE DATABASE`) and drops it
  when done. The variable's URL is only the maintenance database; tests
  never write to it.
- **Skipped without Postgres**, so `uv run pytest` locally stays
  fast and offline (41 pass, 8 skipped). To run them:
  ```bash
  docker run --rm -d --name pg-migtest -p 55432:5432 \
    -e POSTGRES_USER=budget -e POSTGRES_PASSWORD=budget -e POSTGRES_DB=budget postgres:17-alpine
  MIGRATIONS_TEST_DATABASE_URL=postgresql+psycopg://budget:budget@localhost:55432/postgres \
    uv run pytest tests/test_migrations.py
  ```
  (the compose Postgres doesn't publish port 5432 to the host, hence the separate container)
- **`MIGRATIONS_TEST_REQUIRED=1` in the job:** without it, if the Postgres service
  failed to come up, the 8 tests would just be skipped and the job would end up **green without having
  tested anything**. With the variable, a missing database blows up at collection time.
- To make this possible: `backend/alembic/env.py` now accepts an `sqlalchemy.url` injected
  via Config (before it only read `settings`), and `db_bootstrap.main()` accepts an optional
  URL. The container entrypoint's behavior doesn't change.

**Verified that the gates actually catch problems, not just that they pass green:**

- A `telefono` column added to `User` without a migration → fails with the exact diff:
  `New upgrade operations detected: [('add_column', ..., 'users', Column('telefono'...))]`.
- A destructive migration (`DELETE FROM users`) chained after head → caught
  by two different tests (`los_datos_sobreviven` and `puente_pre_alembic`).

## First green run (2026-07-24)

**The first run came back red** due to a mistake on my part: I pinned `astral-sh/setup-uv@v9`
after checking via the API that the latest release was `v9.0.0`, but
**I never checked that the floating major tag `v9` actually existed**. That action only
publishes majors up to `v7`, unlike `checkout` and `setup-node`, which do go
up to v7. The two jobs using uv failed with
`Unable to resolve action astral-sh/setup-uv@v9`; frontend and docker passed.

Fixed by pinning the exact version `@v9.0.0` (with a comment explaining
why it's not a floating major, so nobody "fixes" it back). Lesson:
to pin an action you need to verify the **tag ref**, not the release.

Run 30137793763 — all 4 jobs green:

| Job | Duration |
|---|---|
| Backend (pytest) | 20s |
| Migraciones (Postgres real) | 31s |
| Frontend (typecheck + build) | 19s (27s on the run without cache) |
| Imágenes Docker | 48s |

Confirmed in the job log that the 8 migration tests **actually ran**
(`8 passed`), not that they were skipped: that was exactly the false-green risk that
`MIGRATIONS_TEST_REQUIRED=1` covers.

The run also surfaced a pre-existing lint warning (`react-hooks(exhaustive-deps)`
in `InviteLink.tsx`) that had existed locally since the wizard refactor and I hadn't
noticed because I'd filtered the output with `tail`. Fixed with `useCallback` instead
of silencing it: lint is back to the 4 pre-existing `only-export-components` warnings.
