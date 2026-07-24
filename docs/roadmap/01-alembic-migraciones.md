# 🗄️ Migraciones con Alembic

**Estado:** ✅ Implementado (2026-07-24) · **Prioridad:** Alta · **Esfuerzo:** M (1-3 días) · **Dependencias:** Ninguna

## Por qué
Hoy el esquema se crea con `Base.metadata.create_all` al arrancar el backend. Eso no versiona nada: cualquier cambio en los modelos (una columna nueva, un índice, un rename) no se aplica a bases de datos ya existentes y rompe despliegues reales. Sin migraciones no hay producción seria ni evolución segura del esquema.

## Alcance
**Incluye:**
- Inicializar Alembic con `env.py` apuntando a `app.database.Base.metadata` y `settings.database_url`
- Migración inicial autogenerada del esquema actual (households, users, invitations, accounts, categories, transactions, attachments, recurring_rules)
- Quitar `create_all` de `main.py` en producción (o dejarlo solo para tests)
- Migraciones automáticas al arrancar el backend en Docker (entrypoint o comando)
- Documentar el flujo de trabajo (`uv run alembic revision --autogenerate`, `uv run alembic upgrade head`)

**No incluye:**
- Migración de datos (data migrations) más allá del esquema inicial
- Soporte para downgrade en producción como flujo normal (se implementa, pero no se automatiza)
- Herramientas de branching/merging de migraciones para múltiples desarrolladores

## Diseño propuesto

### Backend
- `uv add alembic` y `alembic init alembic`
- `alembic/env.py`: importar `Base` desde `app.database` y leer la URL desde `app.core.config.settings.database_url` (no hardcodear en `alembic.ini`)
- Generar migración inicial: `uv run alembic revision --autogenerate -m "initial schema"` contra una DB vacía; revisar a mano que las 8 tablas queden correctas
- Eliminar `Base.metadata.create_all(bind=engine)` del arranque en `main.py` (lifespan/startup)
- Tests: mantener `create_all` en el fixture de tests (SQLite en memoria, más rápido y aislado); no tocar los 37 tests existentes

### Frontend
- Sin cambios

### Infra
- Backend en `docker-compose.yml`: cambiar el comando a algo como `sh -c "alembic upgrade head && uvicorn app.main:app ..."` o un `entrypoint.sh` que corra migraciones antes de levantar uvicorn
- Verificar que el orden con `depends_on: db` siga siendo suficiente (la migración debe esperar a que Postgres esté listo; reusar el mecanismo de espera actual si existe)
- Documentar en README: cómo crear una migración nueva tras tocar modelos y cómo aplicarla en el stack self-hosted

## Criterios de aceptación
- [x] `uv run alembic upgrade head` sobre una base vacía crea las 8 tablas correctamente
- [x] `uv run alembic downgrade base` revierte la migración inicial sin errores
- [x] Tras un cambio de prueba en un modelo, `alembic revision --autogenerate` detecta el diff y genera la migración (comprobado con la columna de onboarding, doc 05)
- [ ] El stack Docker arranca con DB vacía y aplica migraciones solo (sin `create_all`) — falta correr el stack
- [x] Los 37 tests de pytest siguen pasando sin modificaciones de lógica

## Qué se implementó (2026-07-24)

- `alembic/env.py`: lee `Base.metadata` de `app.database` e importa `app.models`;
  la URL sale de `settings.database_url` (`alembic.ini` queda con
  `sqlalchemy.url` vacío, el archivo se commitea). `render_as_batch` solo en SQLite.
- `alembic/versions/5d15cfc79c35_esquema_inicial.py`: las 8 tablas. Revisada a
  mano: autogenerate había renderizado los `created_at` como
  `sa.text('(CURRENT_TIMESTAMP)')` (literal del dialecto con el que se generó) y
  los índices en modo batch; se cambiaron a `sa.func.now()` y `op.create_index`
  para que el resultado sea idéntico en Postgres y SQLite.
- `app/main.py`: fuera `create_all`.
- `app/db_bootstrap.py` + `entrypoint.sh`: el contenedor migra antes de uvicorn.
  **Puente para bases pre-Alembic:** si encuentra las tablas sin
  `alembic_version` (las creó el viejo `create_all`), hace `stamp` de la
  migración inicial en vez de re-crearlas — sin esto, la base actual del
  despliegue tronaría con "table households already exists". Idempotente.
- `Dockerfile`: copia `alembic/`, `alembic.ini` y `entrypoint.sh`.
- `backend/README.md`: flujo de trabajo documentado.

**Verificado en SQLite:** `upgrade head` → 8 tablas + `alembic_version`;
`alembic check` → sin diff contra los modelos; `downgrade base` → limpio;
bootstrap sobre base nueva, sobre base legacy hecha con `create_all` (stampea,
no re-crea) y en un segundo arranque (no-op). Los 37 tests pasan.
**Pendiente:** correrlo contra Postgres real levantando el stack.

## Notas
- Riesgo principal: que la migración inicial autogenerada no coincida exactamente con lo que `create_all` producía (índices, constraints). Revisar el diff a mano antes de commitearla.
- Decisión abierta: ¿entrypoint con retry a Postgres o depender de healthchecks en compose? Preferir healthcheck + `condition: service_healthy` si ya está disponible en la versión de compose usada.
- Referencia: https://alembic.sqlalchemy.org/en/latest/autogenerate.html
