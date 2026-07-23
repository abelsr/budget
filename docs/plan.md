# Plan: App de Finanzas Familiares

> Documento vivo con las decisiones de diseño y arquitectura acordadas.
> Última actualización: 2026-07-23

## Visión

App web (PWA) para que una familia **registre y entienda sus gastos e ingresos**.
Self-hosted, pero con esquema multi-tenant preparado para crecer a producto multi-familia.

**Problema central del MVP:** registro de gastos/ingresos compartido por el hogar.

## Decisiones de producto

| Tema | Decisión |
|---|---|
| Problema central | Registro de gastos/ingresos (la base; presupuestos/metas vienen después) |
| Modelo familiar | Cuentas individuales por persona + unión a un **hogar** vía links de invitación |
| Cuentas financieras | Con saldo (efectivo, débito, crédito, ahorro), **todas compartidas** por el hogar; cada transacción registra qué miembro la hizo |
| Categorías | Defaults con icono/color copiados al crear el hogar; editables (renombrar, agregar, desactivar); **lista plana** (sin subcategorías en MVP) |
| Moneda | **Una por hogar**, elegida al crearlo; montos en `NUMERIC(19,4)` |
| Captura | **Solo manual** en MVP; formulario móvil rápido (<10 segundos): monto, categoría, cuenta, fecha, nota opcional. **Más:** escaneo de ticket con IA (subir/tomar foto → extracción → revisión editable → guardar) |
| Dashboard MVP | Saldo total y por cuenta + ingresos vs gastos del mes + dona de gastos por categoría + transacciones recientes |
| Recurrencia | **Fase 2**; el esquema incluye tabla de reglas recurrentes desde el inicio |
| Offline | **Online-first**; la PWA es instalable y carga su shell offline, pero registrar requiere conexión |

## Stack técnico

| Capa | Tecnología |
|---|---|
| Backend | Python 3.14 + uv + **FastAPI**, SQLAlchemy, auth email/contraseña con JWT (Argon2 + PyJWT). Migraciones con Alembic: pendiente (hoy `create_all`) |
| Base de datos | **PostgreSQL**; todas las tablas con `household_id` (multi-tenant desde el día 1) |
| Storage | **MinIO** (S3) para comprobantes adjuntos |
| IA | **OpenRouter** (SDK OpenAI async) para el escáner de tickets; modelo configurable, default `google/gemini-3.6-flash` |
| Frontend | **React + Vite** (TypeScript), Tailwind CSS + shadcn/ui, TanStack Query, Recharts, Motion (springs) |
| Plataforma | **Web responsive / PWA** (un solo codebase para móvil y escritorio) |
| Despliegue | **Docker Compose**: nginx (build estático) + FastAPI + PostgreSQL + MinIO; HTTPS con Caddy/reverse proxy (pendiente) |
| Calidad | pytest para el backend (37 tests); frontend validado manualmente |

## Lenguaje de diseño (frontend)

Basado en la skill **Apple Design** (WWDC *Designing Fluid Interfaces* y principios de diseño de Apple):

- **Respuesta inmediata:** feedback en pointer-down, nunca esperar al click.
- **Springs, no duraciones:** animaciones con `motion`, critically-damped por defecto (`bounce: 0`, ~0.4s); bounce solo cuando el gesto trae momentum.
- **Interrumpibilidad:** toda animación parte del valor actual en pantalla; nunca bloquear input durante transiciones.
- **Materiales translúcidos:** barras/sheets con `backdrop-filter: blur()` y contenido scrollando debajo; el peso del material codifica jerarquía.
- **Tipografía con tracking por tamaño:** display con tracking negativo (`-0.02em`), body cerca de 0; system font stack.
- **Consistencia espacial:** entrar y salir por el mismo camino; sheets/popovers anclados a su origen.
- **Accesibilidad:** `prefers-reduced-motion` → cross-fades; `prefers-reduced-transparency` → superficies sólidas.
- **Principios guía:** propósito, agencia (undo fácil, confirmaciones solo para destructivo), familiaridad, simplicidad (no minimalismo), craft, delight.

## Roadmap

1. **MVP:** auth + hogares + cuentas + categorías + transacciones + dashboard. ✅ **HECHO** (+ escáner IA, adjuntos, modo oscuro)
2. **Fase 2:** recurrencia, importación CSV, presupuestos mensuales. ⬜ Siguiente
3. **Fase 3:** metas de ahorro, cuentas personales (privacidad entre miembros), offline-first con sincronización, apertura multi-familia. ⬜

## Estructura del repo

```
budget/
├── docs/plan.md        ← este documento
├── docker-compose.yml  ← db + backend + frontend + minio
├── .env                ← secretos de compose (ignorado por git)
├── backend/            ← FastAPI + PostgreSQL + MinIO (Python 3.14, uv)
└── frontend/           ← React + Vite PWA (nginx en prod)
```

## Estado actual (2026-07-23)

**Repo publicado en GitHub.** Stack completo corriendo en Docker Compose
(frontend nginx :8081, backend :8000, Postgres 17, MinIO :9000/:9001) y
verificado de punta a punta, incluyendo acceso desde celular por IP local.

### Avance — qué ya está construido y verificado

**Producto (MVP completo + extras):**

- ✅ **Auth real:** registro (crea hogar + 10 categorías default + cuenta
  Efectivo), login JWT (Argon2), restauración de sesión, unirse con
  invitación (`/login?invite=TOKEN`), cerrar sesión.
- ✅ **Transacciones:** registro rápido (<10s) con monto, categoría, cuenta,
  **fecha editable** (default hoy) y nota; lista agrupada por día; detalle
  con edición completa y borrado en dos pasos.
- ✅ **Escáner de tickets con IA:** foto/archivo → análisis con OpenRouter
  (gemini-3.6-flash) → revisión editable → gasto. Normalización EXIF +
  downscale (fotos de celular rotadas funcionan: ticket real de Sam's Club
  extraído exacto: comercio, $1,014.99, fecha 19/07, categoría, conf. 0.98).
- ✅ **Comprobantes adjuntos** (MinIO): foto/pdf/doc por movimiento (máx
  10MB), ver/eliminar desde el detalle; paperclip en las listas.
- ✅ **CRUD cuentas:** crear/editar/eliminar (nombre, tipo, saldo inicial),
  balances calculados en vivo; 409 "tiene movimientos" manejado.
- ✅ **CRUD categorías:** página de gestión con toggles activo/inactivo,
  picker de icono y color, preview en vivo.
- ✅ **Dashboard:** balance total y por cuenta, ingresos vs gastos del mes,
  dona por categoría, movimientos recientes; layout de 2 columnas en desktop.
- ✅ **Hogar multi-miembro:** aislamiento estricto por `household_id`
  (verificado), miembros en sidebar/ajustes, invitaciones por API.
- ✅ **UX Apple Design:** modo oscuro (claro/oscuro/sistema, anti-FOUC),
  materiales translúcidos, springs, feedback en pointer-down,
  `prefers-reduced-motion`, español.

**Infraestructura:**

- ✅ Backend FastAPI multi-tenant (37 tests pytest, SQLite en memoria).
- ✅ Respuestas camelCase end-to-end; proxy `/api` en Vite (dev) y nginx (prod).
- ✅ Secretos en `.env` (raíz y backend/, ignorados por git; plantillas en
  `.env.example`).
- ✅ Dockerfiles limpios (lock regenerado tras fix de `pyproject.toml`).

### Pendientes

**Inmediato (robustez):**

- ⬜ **Alembic:** migraciones formales (hoy `Base.metadata.create_all`).
- ⬜ **Invitaciones end-to-end en UI:** generar link desde Ajustes (la API
  y la pantalla de unirse ya existen; falta el botón + copiar link).
- ⬜ **PWA real:** manifest + service worker (instalable, shell offline).
- ⬜ Backups de Postgres y MinIO (cron + script).

**Fase 2 (features):**

- ⬜ **Transacciones recurrentes** (tabla `recurring_rules` ya en esquema):
  reglas semanales/mensuales que materializan movimientos.
- ⬜ **Presupuestos mensuales** por categoría con alertas de progreso.
- ⬜ **Importación CSV** de estados de cuenta (mapeo de columnas, dedupe).
- ⬜ Filtros/búsqueda en Movimientos (por categoría, cuenta, miembro, texto).
- ⬜ Edición de perfil y cambio de contraseña.

**Fase 3 (crecimiento):**

- ⬜ Metas de ahorro con seguimiento de progreso.
- ⬜ Cuentas personales (privacidad entre miembros del hogar).
- ⬜ Offline-first con cola de sincronización.
- ⬜ Apertura multi-familia (signup público, emails transaccionales).

**Producción:**

- ⬜ HTTPS con Caddy + dominio propio.
- ⬜ CI (GitHub Actions): pytest + build de frontend en cada push.
- ⬜ Monitoreo básico (logs estructurados, healthchecks externos).
