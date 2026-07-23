# Backend — Finanzas Familiares

API REST en FastAPI + SQLAlchemy (sync) + PostgreSQL (SQLite en dev/tests).
Multi-tenant: todos los datos se aíslan por `household_id`.

## Desarrollo local

```bash
uv sync
uv run fastapi dev          # http://127.0.0.1:8000 (docs en /docs)
```

Por defecto usa SQLite (`dev.db`). Para Postgres local, copia `.env.example`
a `.env` y ajusta `DATABASE_URL`.

## Tests

```bash
uv run pytest               # 26 tests, SQLite en memoria
```

## Docker (stack completo desde la raíz del repo)

```bash
docker compose up --build   # frontend :8080, backend :8000, postgres :5432
```

## Estructura

```
app/
├── main.py            # app factory, CORS, routers
├── config.py          # settings vía env (pydantic-settings)
├── database.py        # engine, sesión, Base
├── models.py          # Household, User, Invitation, Account, Category,
│                      # Transaction, RecurringRule (fase 2, sin endpoints)
├── seed.py            # categorías por defecto de cada hogar nuevo
├── core/security.py   # Argon2 + JWT
├── api/
│   ├── deps.py        # get_db, get_current_user (Bearer JWT)
│   └── routes/        # auth, households, accounts, categories,
│                      # transactions, summary, tickets
├── services/vision.py # escáner de tickets (OpenRouter vía SDK OpenAI
│                      # async; sin OPENROUTER_API_KEY → 501)
└── schemas/           # Pydantic, respuestas camelCase
```

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/auth/register` | Crea usuario + hogar (siembra categorías default) |
| POST | `/auth/login` | Login email+password → JWT |
| GET | `/auth/me` | Usuario actual |
| POST | `/auth/join` | Registro con token de invitación |
| GET | `/households/me` | Hogar actual |
| GET | `/households/me/members` | Miembros del hogar |
| POST | `/households/me/invitations` | Crea invitación (7 días) |
| GET/POST/PATCH/DELETE | `/accounts` | CRUD cuentas (balance calculado) |
| GET/POST/PATCH/DELETE | `/categories` | CRUD categorías |
| GET/POST/PATCH/DELETE | `/transactions` | CRUD movimientos (`?month=YYYY-MM`) |
| GET | `/summary/month` | Ingresos/gastos/dona del mes |
| POST | `/tickets/scan` | Análisis de ticket con IA (multipart) |

## Pendiente (siguientes iteraciones)

- Alembic para migraciones (hoy: `create_all` al arrancar, solo dev)
- RecurringRule: endpoints de transacciones recurrentes (fase 2)
- Conectar frontend a `/api` (hoy el frontend usa mocks)
