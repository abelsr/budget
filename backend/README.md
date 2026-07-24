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

## Migraciones (Alembic)

El esquema **no** se crea al arrancar: lo gestiona Alembic. La URL sale de
`settings.database_url` (o sea `DATABASE_URL`), no de `alembic.ini`.

```bash
uv run alembic upgrade head                          # poner la base al día
uv run alembic revision --autogenerate -m "mensaje"  # tras tocar models.py
uv run alembic check                                 # ¿hay diff sin migrar?
uv run alembic downgrade -1                          # revertir la última
uv run alembic history                               # historial
```

Flujo al cambiar `models.py`: autogenerate → **revisar la migración a mano**
(autogenerate no detecta renames ni cambios de tipo sutiles, y renderiza los
`server_default` con el literal del dialecto en uso) → `upgrade head` → commit
del archivo en `alembic/versions/`.

En Docker el `entrypoint.sh` corre `python -m app.db_bootstrap` antes de
uvicorn: aplica las migraciones y, si encuentra una base creada con el viejo
`create_all` (tablas sin `alembic_version`), la marca con `stamp` en la
migración inicial en vez de re-crear nada. Ese puente es temporal y se puede
borrar cuando no queden bases pre-Alembic.

Los tests no usan Alembic: crean el esquema con `create_all` sobre SQLite en
memoria (más rápido y aislado).

## Tests

```bash
uv run pytest               # 37 tests, SQLite en memoria
```

## Docker (stack completo desde la raíz del repo)

```bash
docker compose up --build   # frontend :8081, backend :8000, minio :9000/:9001
```

## Estructura

```
alembic/               # migraciones (env.py lee Base y DATABASE_URL de la app)
app/
├── main.py            # app factory, CORS, routers
├── config.py          # settings vía env (pydantic-settings)
├── database.py        # engine, sesión, Base
├── db_bootstrap.py    # migra al arrancar (+ puente para bases pre-Alembic)
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
| GET | `/auth/me` | Usuario actual (incluye `onboardingCompleted`) |
| PATCH | `/auth/me/onboarding` | Marca/reabre el wizard inicial (idempotente) |
| POST | `/auth/join` | Registro con token de invitación (sin wizard) |
| GET | `/households/me` | Hogar actual |
| GET | `/households/me/members` | Miembros del hogar |
| POST | `/households/me/invitations` | Crea invitación (7 días) |
| GET/POST/PATCH/DELETE | `/accounts` | CRUD cuentas (balance calculado) |
| GET/POST/PATCH/DELETE | `/categories` | CRUD categorías |
| GET/POST/PATCH/DELETE | `/transactions` | CRUD movimientos (`?month=YYYY-MM`) |
| GET | `/summary/month` | Ingresos/gastos/dona del mes |
| POST | `/tickets/scan` | Análisis de ticket con IA (multipart) |

## Pendiente (siguientes iteraciones)

- RecurringRule: endpoints de transacciones recurrentes (fase 2)
