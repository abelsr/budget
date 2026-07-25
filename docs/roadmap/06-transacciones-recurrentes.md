# 🔁 Transacciones recurrentes

**Estado:** ✅ Hecho 2026-07-25 · **Prioridad:** Alta · **Esfuerzo:** M (1-3 días) · **Dependencias:** Ninguna

## Por qué
Renta, sueldo y suscripciones son la columna vertebral de las finanzas familiares, y capturarlos a mano cada mes es la fricción #1 del día a día. La tabla `recurring_rules` ya existe en el esquema — falta exponerla y materializarla.

## Alcance
**Incluye:**
- CRUD de reglas recurrentes con scoping por hogar.
- Materialización de transacciones pendientes (lazy, al leer).
- Opción "Repetir" en el sheet de registro.
- Sección para listar/pausar/eliminar reglas.

**No incluye:**
- Frecuencias adicionales (quincenal, anual, personalizada).
- Edición retroactiva de transacciones ya generadas.
- Notificaciones de "se generó una transacción".

## Diseño propuesto
### Backend
- Endpoints `/recurring-rules`: `GET` (lista del hogar), `POST` (crear), `PATCH /{id}` (pausar/editar `amount`, `note`, `active`), `DELETE /{id}`. Todos filtrados por `household_id`.
- Materialización **lazy** (decisión recomendada para MVP self-hosted, sin scheduler): al llamar `GET /transactions`, antes de responder, generar las transacciones pendientes de reglas `active` con `next_run_date <= hoy` y avanzar `next_run_date`.
  - `weekly`: `+7 días`.
  - `monthly`: mismo día del mes siguiente, cuidando meses cortos (p.ej. 31 de enero → 28/29 de febrero, usando el último día del mes si el día no existe).
  - Una regla puede materializar varias ocurrencias atrasadas en un solo paso (loop hasta `next_run_date > hoy`).
- **Evitar duplicados**: el avance de `next_run_date` y la inserción ocurren en la misma transacción de DB; al ser lazy e idempotente por fecha, releer no duplica.
- **Decisión propuesta**: agregar `recurring_rule_id` nullable a `transactions` para soportar el badge en frontend y futura trazabilidad. Las transacciones manuales quedan en `NULL`.
- Documentar en el endpoint por qué lazy y no job: en self-hosted no hay scheduler garantizado; lazy garantiza consistencia sin infra extra.
### Frontend
- En el sheet de registro rápido: selector "Repetir" con opciones **No repetir / Semanal / Mensual**. Si se elige una frecuencia, se crea la regla (con `next_run_date` = fecha de la transacción + frecuencia) y la transacción actual queda como la primera ocurrencia.
- Sección "Recurrentes" en Ajustes (o en Movimientos): lista de reglas con monto, categoría, frecuencia y próxima fecha; acciones pausar/reanudar y eliminar.
- Badge sutil ("Recurrente") en transacciones generadas, visible en la lista y en el sheet de detalle, usando `recurring_rule_id`.
### Infra
- Sin cambios (la tabla ya existe; solo migración menor si se agrega `recurring_rule_id` a `transactions`).

## Criterios de aceptación
- [x] Crear una regla mensual con `next_run_date` en el pasado → al cargar Movimientos aparece la transacción materializada.
- [x] Recargar o volver a llamar `GET /transactions` no duplica las transacciones generadas.
- [x] Pausar una regla (`active=false`) detiene futuras materializaciones; reactivarla las reanuda desde la fecha correcta.
- [x] Eliminar una regla no borra las transacciones ya generadas.
- [x] Regla mensual del día 31 materializa correctamente en febrero (último día del mes).
- [x] Tests: materialización, no-duplicación, meses cortos, pausa. (65 tests pasan + 9 de migraciones.)

## Notas
- Riesgo: la materialización lazy en `GET /transactions` añade trabajo a un endpoint caliente; si crece, mover a un endpoint dedicado `POST /recurring-rules/materialize` llamado al abrir la app.
- Decisión abierta: si el usuario edita una regla (p.ej. cambia el monto), ¿afecta solo futuras ocurrencias? Propuesta: sí, nunca retroactivo.

## Cómo quedó (2026-07-25)

Implementado con cuatro desvíos del diseño de arriba, todos por problemas que
aparecieron al escribirlo:

1. **Materializa en tres endpoints, no en uno.** El Dashboard es la pantalla de
   entrada y dispara `/accounts`, `/transactions` y `/summary/month` **en
   paralelo**: enganchar solo el de movimientos dejaba el saldo y el resumen
   desfasados en la primera carga tras vencer una regla. El servicio es
   idempotente, así que llamarlo desde los tres es seguro; `GET
   /recurring-rules` también lo llama, o la pantalla mostraría una "próxima
   fecha" ya pasada.
2. **Día ancla guardado en la regla** (`anchor_day`). El diseño decía "31 de
   enero → 28 de febrero", pero guardando el 28 en `next_run_date` marzo partía
   de ahí y la renta se movía al 28 **para siempre**. Con el ancla la secuencia
   real es 31 ene → 28 feb → 31 mar → 30 abr → 31 may → 30 jun.
3. **`repeat` en `POST /transactions`** en vez de dos llamadas desde el
   frontend. Crea transacción y regla ligadas en una sola operación atómica; en
   dos pasos, si la segunda falla queda una transacción huérfana o una regla sin
   primera ocurrencia.
4. **`created_by_id` en la regla.** `transactions.member_id` es NOT NULL y
   atribuir lo generado a quien casualmente abrió la app haría que el mismo
   gasto cambiara de miembro según quién entrara primero.

**Cómo se garantiza la no-duplicación.** La lectura de reglas vencidas toma
`SELECT ... FOR UPDATE`, y la inserción y el avance de `next_run_date` van en la
misma transacción de DB. Si dos peticiones llegan juntas, la segunda se bloquea;
al liberarse, Postgres re-evalúa el `WHERE` contra la fila ya actualizada, la
regla no califica y se va sin generar nada. Verificado con 8 peticiones
concurrentes contra Postgres 17 real: 4 ocurrencias, cero duplicados. En SQLite
—los tests— el `FOR UPDATE` no se renderiza, pero ahí no hay concurrencia.

**Semántica de pausar/reanudar.** El criterio decía "reanudarla las reanuda
desde la fecha correcta" sin definir cuál. Se eligió **saltar hacia adelante**:
quien apagó la regla en marzo no quiere que al prenderla en julio le caigan
cuatro meses de renta. Reanudar una regla que no venció no mueve su fecha.

**Tope de atraso.** `next_run_date` no puede estar a más de un año en el pasado
(422). Sin tope, una fecha de hace años materializaría cientos de transacciones
en la primera lectura.

**PATCH solo toca `amount`, `note` y `active`.** Cambiar categoría, cuenta o
frecuencia es otra regla: mejor borrar y crear que reescribir la historia.

Borrar una regla suelta el enlace de sus transacciones (`recurring_rule_id` a
NULL) en vez de borrarlas: son dinero que se movió. Pierden el badge, que es la
única información que se va.
