# Plan: Family Finance App

> Living document with agreed-upon design and architecture decisions.
> Last updated: 2026-07-25

## Vision

Web app (PWA) for a family to **record and understand their expenses and income**.
Self-hosted, but with a multi-tenant schema ready to grow into a multi-family product.

**Core MVP problem:** shared household expense/income tracking.

## Product decisions

| Topic | Decision |
|---|---|
| Core problem | Expense/income tracking (the foundation; budgets/goals come later) |
| Family model | Individual accounts per person + joining a **household** via invitation links |
| Financial accounts | With balance (cash, debit, credit, savings), **all shared** by the household; each transaction records which member made it |
| Categories | Defaults with icon/color copied when the household is created; editable (rename, add, disable); **flat list** (no subcategories in MVP) |
| Currency | **One per household**, chosen at creation; amounts in `NUMERIC(19,4)` |
| Capture | **Manual only** in MVP; fast mobile form (<10 seconds): amount, category, account, date, optional note. **Plus:** AI receipt scanning (upload/take photo → extraction → editable review → save) |
| MVP Dashboard | Total and per-account balance + income vs. expenses for the month + expense donut chart by category + recent transactions |
| Recurrence | **Done** (phase 2): weekly/monthly rules, lazy materialization on read (no scheduler: self-hosted has no guaranteed cron) |
| Offline | **Online-first**; the PWA is installable and loads its shell offline, but recording requires a connection |

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.14 + uv + **FastAPI**, SQLAlchemy, email/password auth with JWT (Argon2 + PyJWT). Migrations with Alembic |
| Database | **PostgreSQL**; all tables with `household_id` (multi-tenant from day 1) |
| Storage | **MinIO** (S3) for attached receipts |
| AI | **OpenRouter** (async OpenAI SDK) for the receipt scanner; configurable model, default `google/gemini-3.6-flash` |
| Frontend | **React + Vite** (TypeScript), Tailwind CSS + shadcn/ui, TanStack Query, Recharts, Motion (springs) |
| Platform | **Responsive web / PWA** (a single codebase for mobile and desktop) |
| Deployment | **Docker Compose**: nginx (static build) + FastAPI + PostgreSQL + MinIO; HTTPS with Caddy/reverse proxy (pending) |
| Quality | pytest for the backend (78 tests + 9 migration tests against Postgres); frontend validated with typecheck and build; CI on GitHub Actions |

## Design language (frontend)

Based on the **Apple Design** skill (WWDC *Designing Fluid Interfaces* and Apple's design principles):

- **Immediate response:** feedback on pointer-down, never wait for click.
- **Springs, not durations:** animations with `motion`, critically-damped by default (`bounce: 0`, ~0.4s); bounce only when the gesture carries momentum.
- **Interruptibility:** every animation starts from the current on-screen value; never block input during transitions.
- **Translucent materials:** bars/sheets with `backdrop-filter: blur()` and content scrolling underneath; the material's weight encodes hierarchy.
- **Typography with size-based tracking:** display with negative tracking (`-0.02em`), body near 0; system font stack.
- **Spatial consistency:** enter and exit along the same path; sheets/popovers anchored to their origin.
- **Accessibility:** `prefers-reduced-motion` → cross-fades; `prefers-reduced-transparency` → solid surfaces.
- **Guiding principles:** purpose, agency (easy undo, confirmations only for destructive actions), familiarity, simplicity (not minimalism), craft, delight.

## Roadmap

1. **MVP:** auth + households + accounts + categories + transactions + dashboard. ✅ **DONE** (+ AI scanner, attachments, dark mode)
2. **Robustness:** migrations, invitations from the UI, onboarding, PWA, backups. 🚧 **In progress** — Alembic, invitations, and onboarding done; PWA and backups pending
3. **Phase 2:** recurrence, CSV import, monthly budgets. 🚧 **In progress** — recurrence and budgets done; CSV, filters, and profile pending
4. **Phase 3:** savings goals, personal accounts (privacy between members), offline-first with sync, multi-family opening. ⬜

**Concrete next step:** HTTPS with Caddy
([15](roadmap/15-https-caddy.md)), still blocked on installing Tailscale on the
host (path already chosen) — or backups ([04](roadmap/04-backups.md)), which
has no pending decision and is overdue given how much real household data now
lives in Postgres. Details and log in [docs/roadmap/](roadmap/README.md).

## Repo structure

```
budget/
├── docs/plan.md        ← this document
├── docker-compose.yml  ← db + backend + frontend + minio
├── .env                ← compose secrets (ignored by git)
├── backend/            ← FastAPI + PostgreSQL + MinIO (Python 3.14, uv)
└── frontend/           ← React + Vite PWA (nginx in prod)
```

## Current status (2026-07-24)

**Repo published on GitHub.** Full stack running on Docker Compose
(frontend nginx :8081, backend :8000, Postgres 17, MinIO :9000/:9001) and
verified end-to-end, including access from a phone over the local IP.

### Progress — what's already built and verified

**Product (complete MVP + extras):**

- ✅ **Real auth:** registration (creates household + 10 default categories + Cash
  account), JWT login (Argon2), session restoration, joining via
  invitation (`/login?invite=TOKEN`), logout.
- ✅ **Transactions:** quick entry (<10s) with amount, category, account,
  **editable date** (defaults to today), and note; list grouped by day; detail
  view with full editing and two-step delete.
- ✅ **AI receipt scanner:** photo/file → analysis with OpenRouter
  (gemini-3.6-flash) → editable review → expense. EXIF normalization +
  downscaling (rotated phone photos work: a real Sam's Club receipt
  extracted exactly: merchant, $1,014.99, date 07/19, category, conf. 0.98).
- ✅ **Attached receipts** (MinIO): photo/pdf/doc per transaction (max
  10MB), view/delete from the detail view; paperclip icon in the lists.
- ✅ **Account CRUD:** create/edit/delete (name, type, initial balance),
  live-calculated balances; 409 "has transactions" handled.
- ✅ **Category CRUD:** management page with active/inactive toggles,
  icon and color picker, live preview.
- ✅ **Dashboard:** total and per-account balance, income vs. expenses for the month,
  category donut chart, recent transactions; 2-column layout on desktop.
- ✅ **Multi-member household:** strict isolation by `household_id`
  (verified), members in sidebar/settings, and **invitations from the UI**
  (Settings > Household → link with copy/share, valid 7 days, single use).
- ✅ **Onboarding:** 4-step wizard after registering (welcome → accounts
  → invite family → done), with skip always available; those who join via
  invitation don't see it.
- ✅ **Recurring transactions:** "Repeat" selector (weekly/monthly) in the
  quick entry form, which creates the linked rule in a single operation; management
  page in Settings (pause/resume/delete) and a badge on generated
  transactions. **Lazy materialization on read** (no scheduler), with an anchor day
  so a monthly rule on the 31st doesn't get stuck on 28 when passing through February, and
  `SELECT ... FOR UPDATE` to avoid duplicates from concurrent requests.
- ✅ **Monthly budgets:** global limit per expense category (not per month),
  traffic-light progress bars on the Dashboard (green/amber/red at 75%/100%),
  create/edit sheet, and a count badge on the donut card when a category
  goes over its limit.
- ✅ **Apple Design UX:** dark mode (light/dark/system, anti-FOUC),
  translucent materials, springs, pointer-down feedback,
  `prefers-reduced-motion`, Spanish.

**Infrastructure:**

- ✅ Multi-tenant FastAPI backend (78 pytest tests, in-memory SQLite).
- ✅ camelCase responses end-to-end; `/api` proxy in Vite (dev) and nginx (prod).
- ✅ Secrets in `.env` (root and backend/, ignored by git; templates in
  `.env.example` in both).
- ✅ CI on GitHub Actions (4 jobs, passing): pytest, frontend lint + build,
  `docker compose build`, and **migrations against a real Postgres 17** (schema ==
  models, reversibility, data surviving the upgrade, and the pre-Alembic bridge
  not re-creating tables).
- ✅ Clean Dockerfiles (lockfile regenerated after fixing `pyproject.toml`).
- ✅ **Migrations with Alembic:** the container runs `alembic upgrade head`
  before uvicorn (`backend/entrypoint.sh` → `backend/app/db_bootstrap.py`); there's no more
  `create_all` in production. The bootstrap includes a temporary bridge that
  stamps databases created with the old `create_all`.

### Pending

> Full details in **[docs/roadmap/](roadmap/README.md)** — one file per
> pending item with why, scope, design, and acceptance criteria, plus the
> log of what's already done. Closed: 01 (Alembic), 02 (invitations),
> 05 (onboarding), 06 (recurring), 07 (budgets), 16 (CI).

**Immediate (robustness):**

- ⬜ [Real PWA](roadmap/03-pwa-instalable.md): manifest + service worker (installable, offline shell).
- ⬜ [Backups](roadmap/04-backups.md) of Postgres and MinIO. **Next.**

**Phase 2 (features):**

- ⬜ [CSV import](roadmap/08-importacion-csv.md) of account statements.
- ⬜ [Filters and search](roadmap/09-filtros-busqueda.md) in Transactions.
- ⬜ [Profile and password change](roadmap/10-perfil-y-password.md).

**Phase 3 (growth):**

- ⬜ [Savings goals](roadmap/11-metas-de-ahorro.md) with progress tracking.
- ⬜ [Personal accounts](roadmap/12-cuentas-personales.md) (privacy between members).
- ⬜ [Offline-first](roadmap/13-offline-first.md) with sync queue.
- ⬜ [Multi-family opening](roadmap/14-multi-familia.md) (public signup).

**Production:**

- ⬜ [HTTPS with Caddy](roadmap/15-https-caddy.md) + custom domain. **Next.**
  Also enables `navigator.clipboard` on mobile (today the invitation link
  uses the `execCommand` fallback because HTTP over IP is not a secure context).
- ✅ [CI with GitHub Actions](roadmap/16-ci-github-actions.md): pytest + lint + build + docker build + **migrations against a real Postgres** on every push and PR, passing (2026-07-24). Strict branch protection on `main` since 2026-07-25: the 4 checks are required (including for the owner), so changes now go through branch + PR.
- ⬜ [Monitoring](roadmap/17-monitoreo.md): JSON logs, downtime and disk alerts.
