# 🔁 Transacciones recurrentes

**Estado:** ⬜ Pendiente · **Prioridad:** Alta · **Esfuerzo:** M (1-3 días) · **Dependencias:** Ninguna

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
- [ ] Crear una regla mensual con `next_run_date` en el pasado → al cargar Movimientos aparece la transacción materializada.
- [ ] Recargar o volver a llamar `GET /transactions` no duplica las transacciones generadas.
- [ ] Pausar una regla (`active=false`) detiene futuras materializaciones; reactivarla las reanuda desde la fecha correcta.
- [ ] Eliminar una regla no borra las transacciones ya generadas.
- [ ] Regla mensual del día 31 materializa correctamente en febrero (último día del mes).
- [ ] Tests: materialización, no-duplicación, meses cortos, pausa. (Los 37 tests actuales siguen pasando.)

## Notas
- Riesgo: la materialización lazy en `GET /transactions` añade trabajo a un endpoint caliente; si crece, mover a un endpoint dedicado `POST /recurring-rules/materialize` llamado al abrir la app.
- Decisión abierta: si el usuario edita una regla (p.ej. cambia el monto), ¿afecta solo futuras ocurrencias? Propuesta: sí, nunca retroactivo.
