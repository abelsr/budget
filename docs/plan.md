# Plan: Family Finance App

> Living document with agreed-upon design and architecture decisions.
> Last updated: 2026-08-04

## Vision

Web app (PWA) for a family to **record and understand their expenses and income**.
Self-hosted, but with a multi-tenant schema ready to grow into a multi-family product.

**Core MVP problem:** shared household expense/income tracking.

## Product decisions

| Topic | Decision |
|---|---|
| Core problem | Expense/income tracking (the foundation; budgets/goals come later) |
| Family model | Individual accounts per person + joining a **household** via invitation links |
| Financial accounts | With balance (cash, debit, credit, savings). Shared accounts belong to the household; personal accounts belong to one current household member and are visible and operable only by that member. Household balances, budgets, summaries, reports, and goals use shared accounts only; each transaction records which member made it |
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
| Deployment | **Docker Compose**: nginx (static build) + FastAPI + PostgreSQL + MinIO |
| Quality | pytest for the backend (78 tests + 9 migration tests against Postgres); frontend validated with typecheck and build; CI on GitHub Actions |

## Design language (frontend)

> **Full spec: [docs/design-guidelines.md](design-guidelines.md)** — tokens,
> validated chart palette, component rules and the dashboard layout. It is the
> document of record; the summary below is the interaction half of it.

Colour follows the **brand system** (`#2563EB` blue, one hero surface per
screen, semantic green/red reserved for money flow). Interaction follows the
**Apple Design** skill (WWDC *Designing Fluid Interfaces* and Apple's design principles):

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
2. **Robustness:** migrations, invitations from the UI, onboarding, PWA, backups. ✅ **DONE**
3. **Phase 2:** recurrence, CSV import, monthly budgets. ✅ **DONE**
4. **Phase 3:** savings goals, personal accounts (privacy between members), offline-first with sync, multi-family opening. ✅ **DONE**
5. **Next cycle:** financial integrity and household planning. Transfers, CSV
   import, reconciliation, merchant rules, split transactions, monthly rollover
   budgets, in-app alerts, and the cash-flow forecast are complete. See
   [docs/roadmap/README.md](roadmap/README.md).

**Concrete next step:** Mexican card and instalment support (item 9 in the
[roadmap index](roadmap/README.md); design in
[docs/roadmap/23-tarjetas-mx-e-instalados.md](roadmap/23-tarjetas-mx-e-instalados.md)).
Details and log in [docs/roadmap/](roadmap/README.md).

## Repo structure

```
budget/
├── docs/plan.md        ← this document
├── docker-compose.yml  ← db + backend + frontend + minio (+ optional `backup` profile)
├── .env                ← compose secrets (ignored by git)
├── scripts/backup.sh   ← Postgres dump + MinIO archive into backups/
├── backups/            ← backup artifacts (ignored by git, not off-site)
├── backend/            ← FastAPI + PostgreSQL + MinIO (Python 3.14, uv)
└── frontend/           ← React + Vite PWA (nginx in prod)
```

## Current status (2026-08-16)

**Repo published on GitHub.** Full stack running on Docker Compose
(frontend nginx :8081, backend :8000, Postgres 17, MinIO S3 API internal on
the Compose network, console localhost-only on :9001) and
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
  (verified). Each household has an owner; all active members can view the
  directory, while only the owner can create, list, and revoke invitations or
  remove other members. Detaching a member preserves the author attribution of
   their historical transactions. Existing households are backfilled with an
   owner, except legacy zero-member households, which can remain ownerless;
   all newly created and active households have an owner. A composite database
   invariant keeps the owner in their own
  household. Invitations are managed from the UI (Settings > Household → link
  with copy/share, valid 7 days, single use).
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

**Next cycle (financial integrity, complete):**

- ✅ **Transfers between accounts:** a `transfer_groups` pair of two linked
  rows, excluded from income/expense, donut, budgets, and reports everywhere,
  each side independently reconcilable (2026-08-05).
- ✅ **Reports and exports:** range summaries plus CSV, XLSX, DOCX, and PDF
  exports (2026-08-04).
- ✅ **Merchants and categorization rules:** normalized merchant patterns
  auto-categorize CSV imports (2026-08-08).
- ✅ **Split transactions:** one movement, several category allocations;
  budgets, reports, and filters are allocation-aware (2026-08-08).
- ✅ **Monthly budgets with optional rollover:** explicit per-month budgets
  over the backwards-compatible global default, surplus carry opt-in
  (2026-08-08).
- ✅ **In-app alerts:** lazy, idempotent budget-threshold, overdue-rule,
  reached-goal, and negative-balance notifications with a desktop bell
  (2026-08-08).
- ✅ **Goal plans:** advisory monthly contribution requirement with
  pause/resume on dated goals; never creates ledger movements (2026-08-08).
- ✅ **Cash-flow forecast:** `GET /forecast` daily balance projection plus a
  30-day upcoming list, rendered on the dashboard (2026-08-15).
- ✅ **Mexican cards and instalments:** per-card cycle dates (statement day +
  days-to-payment-due, derived not stored), MSI plans with an anchor-day
  schedule that sums exactly to the purchase, payment-due forecast events and
  alerts, and cash→card payment transfers (2026-08-16).

**Infrastructure:**

- ✅ Multi-tenant FastAPI backend (241 pytest tests, in-memory SQLite).
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
> log of what's already done. Open: 24 (undo for delete and quick entry), proposed.

**Immediate (robustness):**

- ✅ [Installable PWA](roadmap/03-pwa-instalable.md): manifest, service worker, and offline shell (2026-08-05).

**Phase 2 (features):**

- ✅ [CSV import](roadmap/08-importacion-csv.md) of account statements (2026-08-06).
- ✅ [Filters and search](roadmap/09-filtros-busqueda.md) in Transactions (2026-08-04).
- ✅ [Profile and password change](roadmap/10-perfil-y-password.md) (2026-08-04).

**Phase 3 (growth):**

- ✅ [Savings goals](roadmap/11-metas-de-ahorro.md) with progress tracking (2026-08-05).
- ✅ [Personal accounts](roadmap/12-cuentas-personales.md) (privacy between members) (2026-08-05).
- ✅ [Offline-first](roadmap/13-offline-first.md) with sync queue (2026-08-05).
- ✅ [Self-host scope](roadmap/14-multi-familia.md) with security hardening (2026-08-05).

**Production:**

- ✅ [CI with GitHub Actions](roadmap/16-ci-github-actions.md): pytest + lint + build + docker build + **migrations against a real Postgres** on every push and PR, passing (2026-07-24). Strict branch protection on `main` since 2026-07-25: the 4 checks are required (including for the owner), so changes now go through branch + PR.
- ✅ [Monitoring](roadmap/17-monitoreo.md): JSON logs with request ids, `/health` database check, optional Uptime Kuma profile, and a disk-check cron script (2026-08-08).
- ✅ [Account reconciliation](roadmap/19-conciliacion-de-cuentas.md): statement-balance sessions, movement states, and stale-session review after edits or import reversals (2026-08-06).
- ✅ [In-app alerts](roadmap/20-alertas-en-app.md): bell with real unread count and a responsive alert sheet (2026-08-08).

**Proposed (next up):**

- 📄 [Undo for delete and quick entry](roadmap/24-undo-eliminacion.md): soft delete for manual deletions, restore endpoint, Deshacer snackbar, 30-day purge (2026-08-16).
