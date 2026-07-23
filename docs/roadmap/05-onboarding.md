# 🧭 Onboarding estilo Plane (wizard inicial)

**Estado:** ⬜ Pendiente · **Prioridad:** Alta · **Esfuerzo:** M (1-3 días) · **Dependencias:** 02-invitaciones-end-to-end (reutiliza la generación de link), 01-alembic-migraciones (necesaria para agregar la columna nueva sin romper DBs existentes)

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
- [ ] Un usuario nuevo que crea hogar ve el wizard la primera vez; recargar la página no lo repite ni lo rompe
- [ ] En el paso 2 puede crear al menos 1 cuenta con saldo inicial y aparece luego en Cuentas
- [ ] En el paso 3 puede generar y copiar el link de invitación (mismo comportamiento que en Ajustes)
- [ ] El skip ("Configurar después") está disponible en todos los pasos y marca el flag
- [ ] Un usuario que se registra con link de invitación NO ve el wizard (entra directo al dashboard)
- [ ] El modo oscuro se respeta en los 4 pasos
- [ ] Con `prefers-reduced-motion` activo, las transiciones se reducen/eliminan
- [ ] Los tests nuevos del backend pasan y los 37 existentes siguen pasando

## Notas
- Inspiración de UX: wizard de setup de Plane (https://plane.so) — progreso lineal, un paso a la vez, skip siempre disponible.
- Riesgo: redirección en `RequireAuth` mal hecha puede crear loops o parpadeos; apoyarse en el `isLoading` existente y no decidir la ruta hasta tener `/auth/me` resuelto.
- Decisión abierta: ¿permitir re-abrir el wizard desde Ajustes ("Repetir configuración inicial")? No incluido en el alcance; si surge, es un botón que resetea el flag.
- Si el paso 2 crea cuentas y el usuario recarga a mitad del wizard, las cuentas ya creadas no deben duplicarse al volver (cargar las cuentas existentes al entrar al paso 2 en lugar de asumir estado vacío).
