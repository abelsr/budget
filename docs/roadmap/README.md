# 🗺️ Roadmap — Finanzas Familiares

Un archivo por pendiente, con su porqué, alcance, diseño propuesto y criterios
de aceptación. Al atacar uno: léelo completo, actualiza su **Estado** a
🚧 En progreso y, al terminar, márcalo ✅ con la fecha.

> **Progreso:** 5 de 17 hechos (01, 02, 05, 06, 16) · última actualización 2026-07-25

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
| 06 | [Transacciones recurrentes](06-transacciones-recurrentes.md) | ✅ 2026-07-25 | Alta | M |
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
| 16 | [CI con GitHub Actions](16-ci-github-actions.md) | ✅ 2026-07-24 | Media | M |
| 17 | [Monitoreo](17-monitoreo.md) | ⬜ | Baja | S |

## Orden sugerido de ataque

`02 ✅ → 01 ✅ → 05 ✅ → 16 ✅ → 06 ✅ → 07 → 15 → 04`

Invitaciones y onboarding completaron la experiencia familiar; Alembic y HTTPS
endurecen para producción; recurrentes y presupuestos son las features con más
impacto diario.

**16 (CI) se hizo antes que 15** porque HTTPS está esperando una decisión de
infraestructura (dominio propio vs Tailscale) y CI no dependía de nada.
**06 también se adelantó a 15** por lo mismo: la decisión sigue pendiente y
recurrentes no dependía de nada.

**Siguiente: 07 — Presupuestos mensuales.** Es la otra feature de impacto diario
y se apoya en categorías y transacciones, ya cerradas.

**15 (HTTPS con Caddy) sigue bloqueado en una decisión, con la ruta ya elegida:
Tailscale** (`tailscale cert` sobre la tailnet, nada expuesto a internet,
funciona tras CGNAT). Falta instalarlo en el host y en los dispositivos de la
familia — hoy no hay `tailscale`, `caddy` ni `mkcert` en el host. Además de
cerrar el despliegue, habilita `navigator.clipboard` en el celular: el link de
invitación depende del fallback `document.execCommand('copy')` porque HTTP plano
por IP no es contexto seguro (ver `lib/clipboard.ts`).

## Bitácora

**2026-07-25 — 06 (recurrentes) implementado y verificado contra Postgres real.**

- **El diseño del doc perdía el día 31.** Decía "31 de enero → 28 de febrero",
  pero guardar el 28 en `next_run_date` hace que marzo parta de ahí: la renta se
  movería al 28 para siempre. Hubo que guardar el **día ancla** en la regla.
  Moraleja: al recortar una fecha, la fecha recortada no puede ser el estado.
- **La materialización lazy no puede vivir en un solo endpoint.** El doc la
  ponía en `GET /transactions`, pero el Dashboard dispara cuentas, movimientos y
  resumen **en paralelo**: el saldo salía desfasado en la primera carga. Está en
  los tres (y en el listado de reglas). El servicio es idempotente, así que no
  cuesta nada.
- **La no-duplicación necesitaba `SELECT ... FOR UPDATE`.** El doc razonaba con
  peticiones secuenciales ("releer no duplica"), y eso es cierto; el hueco eran
  las **concurrentes**, que en esta app son la norma, no la excepción — tres por
  cada carga del Dashboard. Verificado con 8 peticiones simultáneas contra
  Postgres 17: 4 ocurrencias, cero duplicados.
- **"Reanudar desde la fecha correcta" no estaba definido.** Se eligió saltar
  hacia adelante: quien pausó en marzo no quiere cuatro meses de renta de golpe
  al reanudar en julio.
- Se agregó un tope: `next_run_date` no puede estar a más de un año atrás. Sin
  él, una fecha de hace años generaba cientos de transacciones en la primera
  lectura.
- Se añadió un test de migraciones para el **backfill de `created_by_id`**: era
  la única rama que ningún test tocaba y corre en cada despliegue.
- **Desplegado y verificado en navegador.** Antes de migrar se respaldaron
  `pgdata` y `minio_data` a `./backups/` (ignorado por git) — la base real no
  tiene red de seguridad hasta que se haga el doc 04. La migración corrió sola
  en el arranque del contenedor y los datos quedaron intactos. La verificación
  usó un **hogar de prueba aparte**, borrado al terminar dejando la base con los
  mismos conteos que el respaldo. Confirmado en móvil (440px): registro con
  "Repetir", catch-up de 4 semanas atrasadas al recargar, icono en la lista,
  badge en el detalle, pausar/reanudar/eliminar, y cero duplicados tras tres
  cargas (nueve peticiones concurrentes). Sin errores de consola.
- `recurring_rules` estaba vacía en la base real, como asumía la migración.

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
- **El primer run salió rojo:** `setup-uv` no publica tag mayor más allá de
  `v7`, aunque sus releases van en `v9`. Para pinear una action hay que verificar
  el **ref del tag**, no el release. Corregido con `@v9.0.0` exacto; el segundo
  run quedó en verde en los 4 jobs y el badge responde `passing`.
- **Branch protection activa en `main` (2026-07-25)**, estricta e incluyendo al
  dueño: los 4 checks son obligatorios y ya no se puede empujar directo a
  `main`. El flujo pasa a ser rama → PR → merge en verde. Se aplicó con
  `gh api`, no por la web. Detalle y cómo revertirla en el doc 16.
