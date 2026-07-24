# ⚙️ CI con GitHub Actions

**Estado:** 🚧 Implementado, falta el primer run en GitHub (2026-07-24) · **Prioridad:** Media · **Esfuerzo:** S (<1 día) · **Dependencias:** Ninguna

## Por qué
El repo ya está en GitHub y tiene 37 tests, pero nada los corre automáticamente: un push puede romper el backend o el build del frontend sin que nadie se entere hasta el siguiente despliegue. CI básico convierte "creo que pasa" en "está verde", y es la base para cualquier colaboración futura (incluso con uno mismo en otra máquina).

## Alcance
**Incluye:**
- Workflow de GitHub Actions con 2 jobs: backend (uv + pytest) y frontend (node + build)
- Cache de dependencias (uv y npm) para runs rápidos
- Badge de estado en el README
- Opcional: job que construye ambas imágenes Docker sin push (valida los Dockerfiles)

**No incluye:**
- Deploy automático (CD) al servidor self-hosted
- Lint/typecheck estricto como gate (puede añadirse después; no bloquear el CI inicial con deuda existente)
- Tests de integración con Postgres real en CI (los tests actuales corren con SQLite; suficiente por ahora)
- Publicación de imágenes a un registry

## Diseño propuesto

### Backend
- Job `backend`: `actions/setup-uv` (o `astral-sh/setup-uv`), `uv sync`, `uv run pytest`
- Cache: el propio action de uv cachea por `uv.lock`
- Los tests corren con SQLite en memoria (fixture actual); no se necesita servicio Postgres en CI

### Frontend
- Job `frontend`: `actions/setup-node` con Node 24 y `cache: npm`, `npm ci`, `npm run build`
- El build es el gate: si TypeScript/Vite falla, el CI falla (equivalente a "los tests del frontend" por ahora)
- Ambos jobs corren en paralelo en el mismo workflow, triggers: push a `main` y pull requests

### Infra
- Archivo `.github/workflows/ci.yml` único
- Job opcional `docker`: `docker compose build` (o dos `docker build` por contexto) para validar que los Dockerfiles no se rompen; marcarlo como no-bloqueante al inicio si el build es lento, y promoverlo a requerido después
- Badge en README: `![CI](https://github.com/<usuario>/<repo>/actions/workflows/ci.yml/badge.svg)`
- Branch protection en GitHub: exigir el check verde antes de merge a `main` (configuración web, un clic)

## Criterios de aceptación
- [ ] Un push a `main` dispara el workflow y termina en verde — **requiere push**
- [x] Un test roto en backend hace fallar el job y marca el commit en rojo (canary local: `pytest` salió con código 1)
- [x] Un error de TypeScript/build en frontend hace fallar su job (error TS2322 inyectado: `npm run build` salió con código 2)
- [ ] Los runs con cache tardan claramente menos que el primer run — requiere dos runs reales
- [ ] El badge del README refleja el estado real del último run en `main` — requiere el primer run

## Qué se implementó (2026-07-24)

- `.github/workflows/ci.yml` con 3 jobs en paralelo, triggers en push a `main` y
  en pull requests, y `concurrency` con `cancel-in-progress` (un push nuevo
  cancela el run del commit que reemplaza).
  - **backend:** `astral-sh/setup-uv@v9` con cache por `backend/uv.lock`,
    `uv sync --locked` y `uv run pytest -q`. Se usó `--locked` (no `--frozen`)
    a propósito: falla si `uv.lock` no corresponde a `pyproject.toml`, algo que
    ya pasó una vez en este repo.
  - **frontend:** `actions/setup-node@v7` con Node 24 y cache npm, `npm ci`,
    `npm run lint` y `npm run build` (`tsc -b && vite build`).
  - **docker:** `docker compose build`, que cubre lo que los otros jobs no ven
    (el `--frozen` del Dockerfile, el entrypoint de migraciones, el build nginx).
    Quedó bloqueante; si molesta el tiempo, limitarlo a PRs.
- **Lint activado como gate:** `oxlint` sale con código 0 (sus 4 avisos son
  warnings), así que entra sin generar ruido rojo. Ruff no se agregó: no es
  dependencia del proyecto y el doc lo dejaba opcional.
- Versiones de las actions verificadas contra la API de GitHub, no de memoria:
  checkout v7, setup-node v7, setup-uv v9, setup-buildx v4.
- **`README.md` en la raíz** (no existía): badge de CI, qué es la app, stack,
  cómo arrancar el stack y el dev local, tests y enlaces a la documentación.
- **`.env.example` en la raíz** (tampoco existía, y `plan.md` afirmaba que sí):
  plantilla de `JWT_SECRET`, OpenRouter y credenciales de MinIO. Sin él, quien
  clonara el repo no tenía guía para el `.env` que necesita compose.

**Verificado localmente con los comandos exactos del workflow:** `uv lock
--check` en sync, `uv sync --locked` + `pytest` → 41 pasan; `npm ci` desde cero
+ `lint` + `build` limpios; `docker compose build` construye ambas imágenes.
Gates probados inyectando fallos y revirtiéndolos.

**Pendiente:** el primer run real en GitHub (el badge queda en "no status"
hasta entonces) y, después, activar branch protection exigiendo el check verde
para merges a `main` (configuración web, un clic).

## Notas
- Decisión abierta: ¿lint con ruff (backend) y eslint (frontend) como gates? Recomendado añadirlos en el mismo archivo pero en pasos separados, activados solo cuando la base de código ya pase limpia — activarlos antes genera ruido y tentación de ignorar el CI.
- El job de docker build puede tardar varios minutos (imágenes de Python + node); si resulta molesto, limitarlo a PRs y no a cada push.
- No meter secretos en CI: este workflow no necesita ninguno (no hay deploy ni registry).
- Referencia: https://docs.astral.sh/uv/guides/integration/github/
