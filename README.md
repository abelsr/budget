<p>
  <center>
    <img src="docs/brand/isologo-isotipo-no-bg.png" alt="budget isotipo" height="100">
  </center>
</p>

# budget

[![CI](https://github.com/abelsr/budget/actions/workflows/ci.yml/badge.svg)](https://github.com/abelsr/budget/actions/workflows/ci.yml)
[![Python 3.14](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Vite](https://img.shields.io/badge/Vite-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)

> **Your household's money, in one place.**

Self-hosted web app (PWA) for a family to track and understand their expenses
and income. Individual accounts per person that join a **household** via an
invitation link; the whole household shares accounts, categories, and
transactions.

- **Quick entry:** amount, category, account, and date in under 10 seconds.
- **AI receipt scanner:** photo → extraction → editable review → expense.
- **Recurring transactions:** rent, salary, or subscriptions are captured once
  (weekly or monthly) and generate themselves when the app is opened.
- **Attachments** per transaction (MinIO).
- **Monthly budgets:** a limit per expense category with traffic-light
  progress bars.
- **Dashboard:** balance per account, monthly income vs. expenses, category
  donut chart.
- **Guided onboarding** when creating the household, plus light/dark mode.

## Brand

| Asset | File |
|---|---|
| Isotipo (mark) | [`docs/brand/isotipo.png`](docs/brand/isotipo.png) |
| Isólogo (mark + wordmark) | [`docs/brand/isologo.png`](docs/brand/isologo.png) |
| Brand sheet | [`docs/brand/imagen-de-marca.png`](docs/brand/imagen-de-marca.png) |
| Reference screens | [`docs/brand/pantallas-referencia.png`](docs/brand/pantallas-referencia.png) |

Design tokens and usage rules live in
[`docs/design-guidelines.md`](docs/design-guidelines.md).

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.14 + uv, FastAPI, SQLAlchemy, Alembic, JWT (Argon2) |
| Database | PostgreSQL (multi-tenant via `household_id`) |
| Storage | MinIO (S3) for attachments |
| AI | OpenRouter (async OpenAI SDK) for the receipt scanner |
| Frontend | React + Vite (TypeScript), Tailwind, TanStack Query, Recharts, Motion |
| Deployment | Docker Compose: nginx + FastAPI + PostgreSQL + MinIO |

## Starting the stack

```bash
cp .env.example .env        # define JWT_SECRET, MinIO and OPENROUTER_API_KEY
docker compose up -d --build
```

- Frontend: http://localhost:8081
- API (docs at `/docs`): http://localhost:8000
- MinIO console: http://localhost:9001

The backend applies Alembic migrations on startup (`backend/entrypoint.sh`), so an
empty database is ready to go on its own.

## Security configuration

This compose file is for a single-process self-host. Keep the backend and
database off the public network and terminate HTTPS at a reverse proxy before
exposing the frontend. Do not publish registration on plain HTTP.

- Set `JWT_SECRET` to a unique random value of at least 32 bytes, for example
  `openssl rand -hex 32`. It must never use the compose development default or
  be committed. Changing it signs out every user.
- Set `CORS_ORIGINS` to a JSON list containing only the exact HTTPS frontend
  origins, such as `["https://budget.example.com"]`. Do not use `*`: requests
  include credentials.
- Auth and ticket scanning are protected by process-local rate limits. Tune
  `AUTH_*_LIMIT`, `AUTH_*_WINDOW_SECONDS`, `TICKET_SCAN_LIMIT`, and
  `TICKET_SCAN_WINDOW_SECONDS` in `.env` if needed. They are not shared among
  multiple backend replicas; add a shared limiter before scaling horizontally.
- `MAX_MEMBERS_PER_HOUSEHOLD` and
  `MAX_ACTIVE_INVITATIONS_PER_HOUSEHOLD` default to 10 and 5. Checks are
  serialized with the household row, so concurrent invitations or joins cannot
  exceed them.
- User email addresses are stored with `email_verified=false`. There is no mail
  provider or verification flow in this self-host scope.

## Local development

```bash
cd backend  && uv sync && uv run alembic upgrade head && uv run fastapi dev
cd frontend && npm install && npm run dev
```

PostgreSQL is mandatory for local backend runtime and Alembic migrations. Set
`DATABASE_URL` in `backend/.env` from `backend/.env.example`; Vite proxies
`/api` to :8000. SQLite is used only by fast `create_all` unit tests.

## Tests and CI

```bash
cd backend  && uv run pytest      # 78 tests (in-memory SQLite)
cd frontend && npm run build      # tsc -b + vite build
```

Migration tests need Postgres and are skipped without it:

```bash
docker run --rm -d --name pg-migtest -p 55432:5432 \
  -e POSTGRES_USER=budget -e POSTGRES_PASSWORD=budget -e POSTGRES_DB=budget postgres:17-alpine
cd backend && MIGRATIONS_TEST_DATABASE_URL=postgresql+psycopg://budget:budget@localhost:55432/postgres \
  uv run pytest tests/test_migrations.py
```

Every push to `main` and every pull request runs everything in GitHub Actions,
across 4 jobs: backend tests, frontend typecheck + build, `docker compose
build`, and migrations against real Postgres (schema == models, reversibility,
and that data survives the upgrade). See
[.github/workflows/ci.yml](.github/workflows/ci.yml).

## Backups

All household data lives in two Docker volumes. Losing them means losing
everything, with no third-party recourse:

| Volume | Contents | Backup artifact |
|---|---|---|
| `pgdata` | users, households, accounts, transactions, budgets | `backups/pg-<timestamp>.sql.gz` |
| `minio_data` | attachment files (receipt photos) | `backups/minio-<timestamp>.tar.gz` |

```bash
./scripts/backup.sh          # requires the `db` service to be running
```

The script dumps Postgres with `pg_dump --clean --if-exists`, archives the
MinIO volume with `tar`, and then deletes `*.gz` files older than 30 days.
Artifacts are written as `*.part` and renamed only on success, so an
interrupted run never leaves a truncated file that looks usable. Override
`BACKUP_DIR`, `RETENTION_DAYS`, or `MINIO_VOLUME` via the environment.

`backups/` is in `.gitignore`. It is **not** off-site: copy or `rsync` it to
another machine, and keep a copy of `.env` somewhere safe too (it holds
`JWT_SECRET` and the MinIO credentials, and neither is in any backup artifact).

### Automating it

**Host cron (recommended).** Nothing new to install, backups are owned by your
user, and you get a real wall-clock schedule:

```bash
crontab -e
# every day at 03:00
0 3 * * * /path/to/budget/scripts/backup.sh >> /path/to/budget/backups/backup.log 2>&1
```

**Compose service (alternative).** A `backup` profile service that never
starts by default:

```bash
docker compose --profile backup up -d backup
docker compose logs -f backup
```

It runs one backup on startup and then every `BACKUP_INTERVAL_SECONDS`
(default 86400), so it cannot target a wall-clock hour the way cron does. It
also mounts the host Docker socket — any process in that container can control
Docker on the host — and its artifacts are owned by `root`. Prefer host cron
unless you specifically want the backup to travel with the compose stack.

### Restoring a backup

Verified end to end on 2026-07-26 against a throwaway stack with empty volumes.
Steps 1–2 assume you are starting from a fresh deployment; skip them to restore
over an existing one.

```bash
# 1. Bring up the stack. The backend applies Alembic migrations on startup, so
#    a "clean" stack already has the schema — this is why the dump is taken
#    with --clean --if-exists.
docker compose up -d --build

# 2. Pick the pair of artifacts to restore (both must share a timestamp).
TS=20260726-161247

# 3. Stop the services holding the data open.
docker compose stop backend minio

# 4. Restore Postgres.
gunzip -c "backups/pg-$TS.sql.gz" \
  | docker compose exec -T db psql -U budget -d budget -v ON_ERROR_STOP=1

# 5. Replace the MinIO volume contents. `budget_` is the compose project name;
#    it defaults to the directory name.
docker run --rm -i -v budget_minio_data:/data alpine \
  sh -c 'find /data -mindepth 1 -delete && tar xz -C /data' \
  < "backups/minio-$TS.tar.gz"

# 6. Start everything back up.
docker compose start minio backend
```

Then log in and confirm the dashboard shows the expected balances, the
transaction list is populated, and a receipt attachment opens.

## Monitoring

The backend emits JSON logs to stdout. Every completed request includes a UUID
in both the log's `request_id` field and the response's `X-Request-ID` header;
use it to correlate a reported failure without logging request bodies. Keep
`LOG_LEVEL=INFO` in production. Set `LOG_LEVEL=DEBUG` only while diagnosing an
issue.

`/health` checks both the API and its PostgreSQL connection. Start the optional
local Uptime Kuma dashboard with:

```bash
docker compose --profile monitoring up -d uptime-kuma
```

Open `http://localhost:3001`, complete Kuma's initial setup, then create an
HTTP(s) monitor for `http://backend:8000/health` with a 60-second interval and
configure a notification provider (Telegram, Discord, or email). The port is
bound to localhost deliberately; access it through the host LAN, a reverse
proxy with authentication, or Tailscale. Verify it alerts after:

```bash
docker compose stop backend
```

Kuma cannot detect a full host or disk failure. Run the disk check from host
cron, pointing `DISK_PATH` at the mount that holds the Docker volumes when it
is not `/`. `DISK_ALERT_WEBHOOK` must accept a JSON POST, such as a Discord
webhook:

```bash
crontab -e
# every 15 minutes; alert when the filesystem is at least 85% full
*/15 * * * * DISK_ALERT_WEBHOOK=https://example.invalid/webhook /path/to/budget/scripts/check-disk.sh >> /path/to/budget/backups/disk-check.log 2>&1
```

Test the notification safely by lowering the threshold temporarily:

```bash
DISK_THRESHOLD_PERCENT=1 DISK_ALERT_WEBHOOK=https://example.invalid/webhook \
  ./scripts/check-disk.sh
```

For alerts when the entire host is unavailable, also configure an external
monitor such as Better Stack against the public HTTPS `/health` endpoint.

## Documentation

- **[docs/plan.md](docs/plan.md)** — product and architecture decisions, current status.
- **[docs/roadmap/](docs/roadmap/README.md)** — one file per pending item with scope, design, and acceptance criteria.
- **[backend/README.md](backend/README.md)** — endpoints, migration workflow, and structure.

## Contributing

All commits, pull requests, issues, and other repository communication
(titles, descriptions, comments, code comments) must be written in **English**,
using an **LLM-friendly format**:

- Clear, literal, unambiguous language — avoid idioms, sarcasm, or slang that
  don't translate well for automated tooling or code-review agents.
- Commit messages: imperative mood, concise summary line, optional body
  explaining the *why* rather than the *what*.
- PRs and issues: structured with explicit sections (e.g. `Summary`,
  `Changes`, `Test plan`) instead of free-form prose, so both humans and
  agents can parse them quickly.
