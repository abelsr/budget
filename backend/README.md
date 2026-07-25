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
uv run pytest               # 65 tests, SQLite en memoria
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
│                      # Transaction, Attachment, RecurringRule
├── seed.py            # categorías por defecto de cada hogar nuevo
├── core/security.py   # Argon2 + JWT
├── api/
│   ├── deps.py        # get_db, get_current_user (Bearer JWT)
│   └── routes/        # auth, households, accounts, categories,
│                      # transactions, recurring, attachments,
│                      # summary, tickets
├── services/
│   ├── vision.py      # escáner de tickets (OpenRouter vía SDK OpenAI
│   │                  # async; sin OPENROUTER_API_KEY → 501)
│   ├── storage.py     # comprobantes en MinIO (S3)
│   └── recurring.py   # materialización lazy de reglas recurrentes
└── schemas/           # Pydantic, respuestas camelCase
```

## Recurrentes: materialización lazy

Las transacciones de una regla recurrente **no** las genera un cron: se
materializan al leer. Cualquiera de `GET /transactions`, `/accounts`,
`/summary/month` y `/recurring-rules` llama a
`services.recurring.materialize_due()` antes de responder, que crea las
ocurrencias pendientes (`active` y `next_run_date <= hoy`) y avanza la fecha.

Por qué así:

- **Sin scheduler.** En self-hosted no hay cron garantizado, y un contenedor
  apagado tres días no debe perder la renta. El catch-up genera todas las
  ocurrencias atrasadas de golpe, cada una con su propia fecha.
- **En cuatro endpoints, no en uno.** El Dashboard dispara cuentas, movimientos
  y resumen en paralelo: si solo materializara uno, los otros responderían con
  datos desfasados en la primera carga tras vencer una regla.
- **`SELECT ... FOR UPDATE` para no duplicar.** La lectura de reglas vencidas
  toma el lock y la inserción va en la misma transacción de DB. Con peticiones
  concurrentes la segunda se bloquea; al liberarse, Postgres re-evalúa el `WHERE`
  contra la fila ya avanzada, la regla no califica y no genera nada. En SQLite
  (tests) el `FOR UPDATE` no se renderiza, pero ahí no hay concurrencia.
- **`anchor_day` guarda el día que la regla quiere.** Una regla del 31 se recorta
  a 28 en febrero pero vuelve al 31 en marzo; sin el ancla se quedaría en 28.

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
| GET/POST/PATCH/DELETE | `/transactions` | CRUD movimientos (`?month=YYYY-MM`). `POST` acepta `repeat: weekly\|monthly` y crea la regla ligada |
| GET/POST/PATCH/DELETE | `/recurring-rules` | CRUD reglas recurrentes. `PATCH` solo `amount`, `note` y `active`; `DELETE` conserva las transacciones ya generadas |
| GET | `/summary/month` | Ingresos/gastos/dona del mes |
| POST/GET/DELETE | `/transactions/{id}/attachments`, `/attachments/{id}` | Comprobantes (máx 10MB) |
| POST | `/tickets/scan` | Análisis de ticket con IA (multipart) |
