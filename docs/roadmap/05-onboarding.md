# 🧭 Onboarding estilo Plane (wizard inicial)

**Estado:** ✅ Implementado (2026-07-24, falta verificación manual en navegador) · **Prioridad:** Alta · **Esfuerzo:** M (1-3 días) · **Dependencias:** 02-invitaciones-end-to-end (reutiliza la generación de link), 01-alembic-migraciones (necesaria para agregar la columna nueva sin romper DBs existentes)

## Por qué
Hoy, tras registrarse, el usuario cae directo en un dashboard vacío con solo la cuenta "Efectivo" en $0 y ninguna guía. Es la fricción clásica de adopción: no sabe qué hacer primero y abandona. Plane resuelve esto con un wizard de setup (crear workspace → invitar al equipo → tour). Copiamos ese patrón adaptado a finanzas familiares: bienvenida → cuentas iniciales → invitar familia → empezar.

## Alcance
**Incluye:**
- Flag de onboarding por usuario (persistente en backend)
- Ruta `/onboarding` con wizard de 4 pasos, progreso visible y animaciones con springs
- Creación de cuentas iniciales con saldo dentro del wizard
- Generación de link de invitación dentro del wizard
- Opción de skip en todo momento

**No incluye:**
- Tour interactivo del dashboard después del wizard (fase futura)
- Importación de movimientos históricos ni plantillas de categorías en el wizard
- Onboarding para miembros que se unen por invitación (ellos entran directo)

## Diseño propuesto

### Backend
- **Decisión: el flag vive en `User`, no en `Household`.** Justificación: el wizard es una experiencia del usuario que se registra creando un hogar nuevo. Si estuviera en `Household`, un segundo miembro que se une después heredaría el estado del admin (no vería nada, correcto) pero tampoco habría forma de distinguir "quién ya pasó por aquí" si en el futuro se quiere onboarding por miembro. Con el flag en `User`, se muestra el wizard **solo a quien se registra creando hogar nuevo**; quien entra con invitación se marca como completado automáticamente al registrarse.
- Modelo `User`: agregar `onboarding_completed_at: DateTime` (nullable). `NULL` = pendiente. Requiere migración (ver dependencia con `01-alembic-migraciones.md`).
- `GET /auth/me`: incluir el flag en la respuesta (ej. `onboarding_completed: bool` derivado de `onboarding_completed_at IS NOT NULL`).
- `PATCH /auth/me/onboarding` con body `{ "completed": true }`: setea `onboarding_completed_at = now()`. Idempotente.
- Al registrar con invitación (`/auth/register` con token de invitación): marcar `onboarding_completed_at` de inmediato — no necesita el wizard.
- Tests: nuevos casos para el PATCH, el flag en `/auth/me`, y el comportamiento distinto registro normal vs. invitación.

### Frontend
- Ruta `/onboarding` protegida. En `RequireAuth` (que ya maneja `isLoading`): si el usuario autenticado tiene `onboarding_completed === false`, redirigir a `/onboarding`; al completarse, redirigir al dashboard. Evitar loop: `/onboarding` misma no redirige.
- Wizard de 4 pasos estilo Plane, con indicador de progreso (puntos o barra) y transiciones con springs (entrar/salir por el mismo camino, estilo Apple; reusar la librería de animación ya presente en el proyecto —p. ej. framer-motion/spring— y respetar `prefers-reduced-motion`):
  1. **Bienvenida:** "Bienvenido a Finanzas Familiares, \<nombre\>" + 3 bullets con iconos de qué puede hacer la app (registrar movimientos, escanear tickets, compartir con tu familia).
  2. **Tus cuentas:** lista editable de cuentas iniciales con saldo. "Efectivo" ya existe → mostrarla precargada; permitir agregar Débito / Crédito / Ahorro (u otras) con nombre y saldo inicial. Usa el hook existente `useCreateAccount`.
  3. **Invita a tu familia:** genera el link de invitación con un tap (`POST /households/me/invitations`), botones copiar/compartir (misma UI de `02-invitaciones-end-to-end.md`) y opción "Lo hago después".
  4. **Listo:** resumen breve (cuentas creadas, invitación enviada o pendiente) + botón "Empezar" que llama `PATCH /auth/me/onboarding` y navega al dashboard.
- Skip siempre visible: "Configurar después" → llama al mismo PATCH y navega al dashboard (el wizard no vuelve a aparecer).
- Compatible con modo oscuro (el wizard usa los mismos tokens de tema que el resto de la app).

### Infra
- Sin cambios (la columna nueva llega vía migración de Alembic)

## Criterios de aceptación

> Los de backend están cubiertos por tests; los de UI son de recorrido manual y
> quedan por confirmar con el stack levantado.

- [ ] Un usuario nuevo que crea hogar ve el wizard la primera vez; recargar la página no lo repite ni lo rompe
- [ ] En el paso 2 puede crear al menos 1 cuenta con saldo inicial y aparece luego en Cuentas
- [ ] En el paso 3 puede generar y copiar el link de invitación (mismo comportamiento que en Ajustes)
- [ ] El skip ("Configurar después") está disponible en todos los pasos y marca el flag
- [x] Un usuario que se registra con link de invitación NO ve el wizard (entra directo al dashboard) — cubierto por `test_join_flow`
- [ ] El modo oscuro se respeta en los 4 pasos
- [ ] Con `prefers-reduced-motion` activo, las transiciones se reducen/eliminan
- [x] Los tests nuevos del backend pasan y los 37 existentes siguen pasando (41 en total)

## Qué se implementó (2026-07-24)

**Backend**
- `User.onboarding_completed_at` (nullable; NULL = pendiente) + migración
  `673ed5f3d911`. La migración **hace backfill**: los usuarios que ya existían
  se marcan como completados, porque su hogar ya está configurado y no les toca
  wizard al desplegar.
- `GET /auth/me` devuelve `onboardingCompleted` (derivado de la fecha).
- `PATCH /auth/me/onboarding` con `{completed}`: idempotente (repetir no mueve la
  fecha guardada) y acepta `false` para reabrirlo.
- `POST /auth/join` marca el flag al crear al miembro: quien llega por
  invitación entra directo al dashboard.
- 4 tests nuevos (41 en total): registro deja pendiente, PATCH idempotente,
  reabrir, y 401 sin token. `test_join_flow` cubre el caso de la invitación.

**Frontend**
- `pages/OnboardingPage.tsx`: wizard de 4 pasos (bienvenida → cuentas → familia
  → listo), barra de progreso de 4 segmentos, transición horizontal
  direccional (entra y sale por el mismo camino) con `AnimatePresence` y
  springs, "Configurar después" siempre visible en el header.
  - Paso 2 lee las cuentas del backend (`useAccounts`), así que "Efectivo" ya
    aparece y recargar a mitad del wizard no duplica nada; el formulario inline
    crea con `useCreateAccount`.
  - Paso 4 resume cuentas creadas e invitación generada o pendiente.
- `components/InviteLink.tsx`: se extrajo el contenido del `InviteSheet` de la
  tarea 02 para reusarlo. `autoGenerate` distingue los dos usos: en el sheet
  abrir ya es el gesto, en el wizard hay botón explícito para no dejar
  invitaciones sueltas al pasar por el paso.
- `lib/auth.tsx`: `Session.onboardingCompleted` + `completeOnboarding()`.
- `App.tsx`: ruta `/onboarding` fuera del `AppShell` (pantalla completa) y
  guard en `RequireAuth` en ambos sentidos — sin flag completado todo redirige
  al wizard, con el flag completado `/onboarding` redirige al dashboard. Nada
  se decide antes de que `/auth/me` resuelva, así que no hay loop ni parpadeo.
- Modo oscuro y `prefers-reduced-motion` salen gratis: solo tokens de tema y el
  `MotionConfig reducedMotion="user"` que ya envuelve la app.

**Verificado:** 41 tests pasan, `tsc -b && vite build` limpio, `oxlint` sin
warnings nuevos, migración con `upgrade`/`downgrade`/`check` en SQLite.
**Pendiente:** recorrido manual de los 4 pasos en navegador.

## Notas
- Inspiración de UX: wizard de setup de Plane (https://plane.so) — progreso lineal, un paso a la vez, skip siempre disponible.
- Riesgo: redirección en `RequireAuth` mal hecha puede crear loops o parpadeos; apoyarse en el `isLoading` existente y no decidir la ruta hasta tener `/auth/me` resuelto.
- Decisión abierta: ¿permitir re-abrir el wizard desde Ajustes ("Repetir configuración inicial")? No incluido en el alcance; si surge, es un botón que resetea el flag.
- Si el paso 2 crea cuentas y el usuario recarga a mitad del wizard, las cuentas ya creadas no deben duplicarse al volver (cargar las cuentas existentes al entrar al paso 2 en lugar de asumir estado vacío).
