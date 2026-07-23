# Plan: App de Finanzas Familiares

> Documento vivo con las decisiones de diseño y arquitectura acordadas.
> Última actualización: 2026-07-22

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
| Backend | Python 3.14 + uv + **FastAPI**, SQLAlchemy + Alembic, auth email/contraseña con JWT (hash argon2/bcrypt) |
| Base de datos | **PostgreSQL**; todas las tablas con `household_id` (multi-tenant desde el día 1) |
| Frontend | **React + Vite** (TypeScript), Tailwind CSS + shadcn/ui, TanStack Query, Recharts, Motion (springs) |
| Plataforma | **Web responsive / PWA** (un solo codebase para móvil y escritorio) |
| Despliegue | **Docker Compose**: nginx (build estático) + FastAPI + PostgreSQL; HTTPS con Caddy/reverse proxy |
| Calidad | pytest para lógica de negocio y API del backend; frontend validado manualmente |

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

1. **MVP:** auth + hogares + cuentas + categorías + transacciones + dashboard.
2. **Fase 2:** recurrencia, importación CSV, presupuestos mensuales.
3. **Fase 3:** metas de ahorro, cuentas personales (privacidad entre miembros), offline-first con sincronización, apertura multi-familia.

## Estructura del repo

```
budget/
├── docs/plan.md      ← este documento
├── backend/          ← FastAPI + PostgreSQL (Python 3.14, uv)
└── frontend/         ← React + Vite PWA
```

## Estado actual (2026-07-22)

**Frontend funcional con datos mock** (`frontend/`, `npm run dev`):

- App shell responsive: tab bar translúcida en móvil / sidebar en desktop,
  indicador activo con spring compartido (`layoutId`).
- Dashboard: balance total + chips por cuenta, ingresos vs gastos del mes,
  dona por categoría (Recharts), movimientos recientes.
- Movimientos: lista completa agrupada por día con total diario.
- Cuentas: saldos por cuenta.
- Registro rápido: FAB → bottom sheet (Base UI drawer) con segmented control
  gasto/ingreso, monto protagonista, grid de categorías, selector de cuenta,
  nota opcional. Guardar actualiza balances, resumen y listas (mock en memoria).
- **Escáner de ticket con IA** (`src/components/TicketScanner.tsx`): subir/tomar
  foto (drag & drop en desktop, cámara trasera en móvil) → preview → análisis
  (línea de escaneo animada) → revisión editable (monto, comercio, categoría
  sugerida, cuenta; badge "Revisar" si la confianza es baja) → guardar como
  gasto. La capa `src/lib/scan.ts` es mock pero define el contrato del futuro
  endpoint `POST /tickets/scan` (multipart → `{ merchant, total, date,
  suggestedCategoryId, confidence }`).
  **Decisión pendiente:** proveedor del modelo de visión (GPT-4o / Claude /
  Gemini / Ollama local) — se resuelve al construir el backend.
- **Layout escritorio mejorado:** dos columnas (principal + rail lateral de
  340–380px con escáner, dona y resumen de cuentas), contenedor `max-w-6xl`
  (2xl: `max-w-7xl`), balance y tarjetas del mes comparten fila en xl.
  Movimientos agrupados por día en grid de 2–3 columnas en escritorio.
- **Modo oscuro** (`src/lib/theme.tsx`): claro/oscuro/sistema con segmented
  control en Ajustes, persistido en localStorage, script anti-FOUC en
  `index.html`, `theme-color` sincronizado, escucha cambios del SO en vivo.
- **Login + auth mock** (`src/lib/auth.tsx`, `/login`): página pública sin
  shell, guarda `RequireAuth` que redirige a /login, sesión falsa en
  localStorage (integración: `POST /auth/login` con JWT).
- **Ajustes** (`/ajustes`): cuenta, apariencia (tema), miembros del hogar
  (invitar = próximamente), preferencias (categorías, escáner IA), moneda del
  hogar, cerrar sesión. Accesible como 4º tab en móvil y en la sidebar.
- Lenguaje Apple Design aplicado: tokens en `src/index.css` (paleta iOS,
  materiales `backdrop-filter`, `.pressable` con feedback en pointer-down),
  presets de springs en `src/lib/springs.ts`, `MotionConfig reducedMotion="user"`,
  tipografía system stack con tracking por tamaño y cifras tabulares.
- Capa de datos (`src/lib/queries.ts`) con TanStack Query sobre mock
  (`src/lib/mock-db.ts`); al existir el backend solo cambian esas funciones
  por `fetch`.

**Backend implementado** (`backend/`, 26 tests pasando, smoke test E2E OK):

- FastAPI + SQLAlchemy sync + Pydantic v2; multi-tenant por `household_id`.
- Auth: register (crea hogar + siembra 10 categorías default), login JWT
  (Argon2 + PyJWT), `/auth/me`, `/auth/join` con invitaciones.
- CRUD completo: cuentas (balance calculado = opening + ingresos − gastos),
  categorías, transacciones (filtro `?month=`, orden desc, aislamiento por hogar).
- `/summary/month`: ingresos, gastos y dona por categoría.
- `/tickets/scan`: servicio de visión **async** con SDK de OpenAI apuntado a
  **OpenRouter** (`AsyncOpenAI`, modelo configurable vía `OPENROUTER_MODEL`,
  default `openai/gpt-4o-mini`); sin `OPENROUTER_API_KEY` → 501.
  Contrato idéntico al del frontend. Config vía `backend/.env` (no commiteado;
  plantilla en `.env.example`).
- Respuestas camelCase (alias Pydantic), path ops sync, estilo `Annotated`.
- Docker: `docker-compose.yml` raíz (db Postgres 17 + backend + frontend/nginx
  con proxy `/api`), Dockerfiles de backend y frontend, `.env.example`.
- Tests: SQLite en memoria vía override de `get_db` (26 tests).

**Frontend conectado al backend real** (E2E verificado: registro → ingreso →
gasto → persistencia tras recarga → error 501 del escáner sin API key):

- `src/lib/api.ts`: cliente HTTP (base `/api`, Bearer token en localStorage,
  ApiError con detalle del servidor, limpia token en 401).
- Proxy de Vite: `/api` → `127.0.0.1:8000` en dev (nginx en prod).
- `auth.tsx` real: restauración de sesión vía `/auth/me` con `isLoading`,
  login/registro/join; LoginPage con segmented control Entrar/Crear cuenta
  y modo invitación vía `?invite=TOKEN`.
- `queries.ts` real: mismos hooks contra la API (mock-db eliminado);
  `useHousehold` alimenta el nombre del hogar en la sidebar.
- `scan.ts` real: POST multipart a `/tickets/scan`; TicketScanner con
  estado de error + reintento.
- Register del backend crea cuenta inicial "Efectivo" (hogar no arranca vacío).

**Stack dockerizado verificado E2E** (7/7 pruebas PASS):

- `docker compose up` levanta db (Postgres 17) + backend + frontend/nginx.
- Frontend servido en **:8081** (el 8080 del host está ocupado por otro
  contenedor del usuario; revertir el puerto en compose si se libera).
- Escáner con IA real verificado contra OpenRouter: el ticket de prueba
  devolvió `{merchant: "Walmart Supercenter Mexico", total: 1234.56,
  suggestedCategoryId: <Supermercado real>, confidence: 1.0}`.
- Persistencia en Postgres confirmada vía psql; aislamiento multi-hogar OK.
- Config de secretos: `.env` raíz (docker-compose) y `backend/.env` (dev
  local), ambos ignorados por git; plantillas en `.env.example`.

**Pendiente inmediato:** Alembic (hoy `create_all`), CRUD de cuentas/categorías
en la UI (la API ya existe), recurring rules (fase 2), HTTPS con Caddy.
