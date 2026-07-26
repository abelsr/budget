# 💸 Family Finances

[![CI](https://github.com/abelsr/budget/actions/workflows/ci.yml/badge.svg)](https://github.com/abelsr/budget/actions/workflows/ci.yml)

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

## Local development

```bash
cd backend  && uv sync && uv run alembic upgrade head && uv run fastapi dev
cd frontend && npm install && npm run dev
```

The backend uses SQLite (`dev.db`) by default; Vite proxies `/api` to :8000.

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
