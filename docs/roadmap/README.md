# 🗺️ Roadmap — Finanzas Familiares

Un archivo por pendiente, con su porqué, alcance, diseño propuesto y criterios
de aceptación. Al atacar uno: léelo completo, actualiza su **Estado** a
🚧 En progreso y, al terminar, márcalo ✅ con la fecha.

> **Progreso:** 3 de 17 hechos (01, 02, 05) · 16 en vuelo · última actualización 2026-07-24

## Inmediato — robustez

| # | Documento | Estado | Prioridad | Esfuerzo |
|---|---|---|---|---|
| 01 | [Alembic: migraciones](01-alembic-migraciones.md) | ✅ 2026-07-24 | Alta | M |
| 02 | [Invitaciones end-to-end](02-invitaciones-end-to-end.md) | ✅ 2026-07-24 | Alta | S |
| 03 | [PWA instalable](03-pwa-instalable.md) | ⬜ | Media | M |
| 04 | [Backups](04-backups.md) | ⬜ | Media | S |
| 05 | [Onboarding estilo Plane](05-onboarding.md) | ✅ 2026-07-24 | Alta | M |

## Fase 2 — features

| # | Documento | Estado | Prioridad | Esfuerzo |
|---|---|---|---|---|
| 06 | [Transacciones recurrentes](06-transacciones-recurrentes.md) | ⬜ | Alta | M |
| 07 | [Presupuestos mensuales](07-presupuestos-mensuales.md) | ⬜ | Alta | M |
| 08 | [Importación CSV](08-importacion-csv.md) | ⬜ | Media | L |
| 09 | [Filtros y búsqueda](09-filtros-busqueda.md) | ⬜ | Media | S |
| 10 | [Perfil y cambio de contraseña](10-perfil-y-password.md) | ⬜ | Media | S |

## Fase 3 — crecimiento

| # | Documento | Estado | Prioridad | Esfuerzo |
|---|---|---|---|---|
| 11 | [Metas de ahorro](11-metas-de-ahorro.md) | ⬜ | Media | M |
| 12 | [Cuentas personales](12-cuentas-personales.md) | ⬜ | Baja | M |
| 13 | [Offline-first](13-offline-first.md) | ⬜ | Baja | L |
| 14 | [Apertura multi-familia](14-multi-familia.md) | ⬜ | Baja | L |

## Producción

| # | Documento | Estado | Prioridad | Esfuerzo |
|---|---|---|---|---|
| 15 | [HTTPS con Caddy](15-https-caddy.md) | ⬜ | Alta | S |
| 16 | [CI con GitHub Actions](16-ci-github-actions.md) | 🚧 falta el 1er run | Media | M |
| 17 | [Monitoreo](17-monitoreo.md) | ⬜ | Baja | S |

## Orden sugerido de ataque

`02 ✅ → 01 ✅ → 05 ✅ → 15 → 06 → 07`

Invitaciones y onboarding completaron la experiencia familiar; Alembic y HTTPS
endurecen para producción; recurrentes y presupuestos son las features con más
impacto diario.

**16 (CI) se hizo antes que 15** porque HTTPS está esperando una decisión de
infraestructura (dominio propio vs Tailscale) y CI no dependía de nada.

**Siguiente: 15 — HTTPS con Caddy.** Además de cerrar el despliegue, habilita
`navigator.clipboard` en el celular: hoy el link de invitación depende del
fallback `document.execCommand('copy')` porque HTTP plano por IP no es contexto
seguro (ver `lib/clipboard.ts`). **Bloqueado en una decisión:** dominio propio
con Let's Encrypt (requiere DNS + puertos 80/443 abiertos, imposible tras CGNAT)
o Tailscale con `tailscale cert` (nada expuesto, ninguno de los dos está
instalado en el host hoy).

## Bitácora

**2026-07-24 — 01, 02 y 05 hechos y verificados en navegador.**

- **02** era casi todo UI: el backend de invitaciones ya existía con tests. Su
  contenido terminó extraído en `components/InviteLink.tsx` para reusarlo en el
  wizard, con `InviteSheet` como envoltorio del drawer.
- **01 se adelantó a 05.** El wizard agrega una columna a `users` y `create_all`
  no altera tablas existentes: sin migraciones, la base del despliegue se habría
  quedado sin la columna. El doc 05 ya listaba 01 como dependencia, pero el orden
  sugerido de este índice no lo reflejaba.
- Como ya existía una base creada con `create_all`, `app/db_bootstrap.py` la
  detecta (tablas sin `alembic_version`) y hace `stamp` en vez de re-crearla.
  **Ese puente es temporal**: se borra cuando no queden bases pre-Alembic.
- La migración de la columna hace **backfill** de los usuarios existentes; si no,
  quien ya tenía su hogar armado vería un wizard que no le toca.

**Lo único que quedó sin verificar:** `prefers-reduced-motion` en el wizard (doc
05). Sale del `MotionConfig reducedMotion="user"` que ya envuelve la app, pero no
se pudo emular la media query; conviene confirmarlo a mano en el sistema.

**2026-07-24 (cont.) — 16 (CI) implementado, esperando el primer run.**

- Aparecieron dos huecos al escribir el README: no había README en la raíz ni
  `.env.example` en la raíz (y `plan.md` afirmaba que sí). Ambos creados.
- `backend/.env` tiene un `JWT_SECRET` de 20 caracteres: es el origen del
  `InsecureKeyLengthWarning` en los tests. Solo afecta al dev local (Docker usa
  el de la raíz, de 41), y endurecerlo entra en el alcance de **15**.
- Se añadió al CI un **job de migraciones contra Postgres real** (8 tests) que
  no estaba en el alcance del doc 16: el job de docker construía la imagen pero
  nadie corría una migración, y ese es justo el riesgo de romper la base al
  desplegar. Incluye que los datos sobrevivan al upgrade y que el puente
  pre-Alembic no re-cree tablas. Por eso 16 pasó de esfuerzo S a M.
