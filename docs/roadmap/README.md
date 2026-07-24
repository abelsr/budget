# 🗺️ Roadmap — Finanzas Familiares

Un archivo por pendiente, con su porqué, alcance, diseño propuesto y criterios
de aceptación. Al atacar uno: léelo completo, actualiza su **Estado** a
🚧 En progreso y, al terminar, márcalo ✅ con la fecha.

## Inmediato — robustez

| # | Documento | Prioridad | Esfuerzo |
|---|---|---|---|
| 01 | [Alembic: migraciones](01-alembic-migraciones.md) ✅ | Alta | M |
| 02 | [Invitaciones end-to-end](02-invitaciones-end-to-end.md) ✅ | Alta | S |
| 03 | [PWA instalable](03-pwa-instalable.md) | Media | M |
| 04 | [Backups](04-backups.md) | Media | S |
| 05 | [Onboarding estilo Plane](05-onboarding.md) | Alta | M |

## Fase 2 — features

| # | Documento | Prioridad | Esfuerzo |
|---|---|---|---|
| 06 | [Transacciones recurrentes](06-transacciones-recurrentes.md) | Alta | M |
| 07 | [Presupuestos mensuales](07-presupuestos-mensuales.md) | Alta | M |
| 08 | [Importación CSV](08-importacion-csv.md) | Media | L |
| 09 | [Filtros y búsqueda](09-filtros-busqueda.md) | Media | S |
| 10 | [Perfil y cambio de contraseña](10-perfil-y-password.md) | Media | S |

## Fase 3 — crecimiento

| # | Documento | Prioridad | Esfuerzo |
|---|---|---|---|
| 11 | [Metas de ahorro](11-metas-de-ahorro.md) | Media | M |
| 12 | [Cuentas personales](12-cuentas-personales.md) | Baja | M |
| 13 | [Offline-first](13-offline-first.md) | Baja | L |
| 14 | [Apertura multi-familia](14-multi-familia.md) | Baja | L |

## Producción

| # | Documento | Prioridad | Esfuerzo |
|---|---|---|---|
| 15 | [HTTPS con Caddy](15-https-caddy.md) | Alta | S |
| 16 | [CI con GitHub Actions](16-ci-github-actions.md) | Media | S |
| 17 | [Monitoreo](17-monitoreo.md) | Baja | S |

## Orden sugerido de ataque

`02 ✅ → 01 ✅ → 05 → 15 → 06 → 07` (invitaciones y onboarding completan la
experiencia familiar; Alembic y HTTPS endurecen para producción; recurrentes
y presupuestos son las features con más impacto diario).

**Nota de orden:** 01 se adelantó a 05 porque el wizard de onboarding agrega
una columna a `users` y `create_all` no altera tablas existentes: sin
migraciones, la base del despliegue actual se habría quedado sin la columna.
El propio doc 05 ya listaba 01 como dependencia.

**Siguiente:** 05 — onboarding estilo Plane (reusa el sheet de invitación
construido en 02).
