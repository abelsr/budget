# 💸 Finanzas Familiares

[![CI](https://github.com/abelsr/budget/actions/workflows/ci.yml/badge.svg)](https://github.com/abelsr/budget/actions/workflows/ci.yml)

App web (PWA) self-hosted para que una familia registre y entienda sus gastos e
ingresos. Cuentas individuales por persona que se unen a un **hogar** por link de
invitación; todo el hogar comparte cuentas, categorías y movimientos.

- **Registro rápido:** monto, categoría, cuenta y fecha en menos de 10 segundos.
- **Escáner de tickets con IA:** foto → extracción → revisión editable → gasto.
- **Comprobantes adjuntos** por movimiento (MinIO).
- **Dashboard:** balance por cuenta, ingresos vs gastos del mes, dona por categoría.
- **Onboarding** guiado al crear el hogar y modo claro/oscuro.

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.14 + uv, FastAPI, SQLAlchemy, Alembic, JWT (Argon2) |
| Base de datos | PostgreSQL (multi-tenant por `household_id`) |
| Storage | MinIO (S3) para comprobantes |
| IA | OpenRouter (SDK OpenAI async) para el escáner de tickets |
| Frontend | React + Vite (TypeScript), Tailwind, TanStack Query, Recharts, Motion |
| Despliegue | Docker Compose: nginx + FastAPI + PostgreSQL + MinIO |

## Arrancar el stack

```bash
cp .env.example .env        # define JWT_SECRET, MinIO y OPENROUTER_API_KEY
docker compose up -d --build
```

- Frontend: http://localhost:8081
- API (docs en `/docs`): http://localhost:8000
- Consola de MinIO: http://localhost:9001

El backend aplica las migraciones de Alembic al arrancar (`entrypoint.sh`), así
que una base vacía queda lista sola.

## Desarrollo local

```bash
cd backend  && uv sync && uv run alembic upgrade head && uv run fastapi dev
cd frontend && npm install && npm run dev
```

El backend usa SQLite (`dev.db`) por defecto; Vite proxifica `/api` al :8000.

## Tests y CI

```bash
cd backend  && uv run pytest      # 41 tests (SQLite en memoria)
cd frontend && npm run build      # tsc -b + vite build
```

Cada push a `main` y cada pull request corre lo mismo en GitHub Actions, más un
`docker compose build` que valida los Dockerfiles. Ver
[.github/workflows/ci.yml](.github/workflows/ci.yml).

## Documentación

- **[docs/plan.md](docs/plan.md)** — decisiones de producto y arquitectura, estado actual.
- **[docs/roadmap/](docs/roadmap/README.md)** — un archivo por pendiente con alcance, diseño y criterios de aceptación.
- **[backend/README.md](backend/README.md)** — endpoints, flujo de migraciones y estructura.
