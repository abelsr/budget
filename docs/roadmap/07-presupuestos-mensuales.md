# 🎯 Presupuestos mensuales

**Estado:** ⬜ Pendiente · **Prioridad:** Alta · **Esfuerzo:** M (1-3 días) · **Dependencias:** Ninguna

## Por qué
Después del registro de gastos, la feature más pedida: límites por categoría con alertas visuales. Es lo que convierte la app de "historial" en "herramienta de control".

## Alcance
**Incluye:**
- Modelo y CRUD de presupuestos por categoría.
- Endpoint de estado (gastado vs límite) cruzado con el summary del mes.
- Barras de progreso con semáforo en el dashboard.

**No incluye:**
- Presupuestos por cuenta, miembro o período arbitrario.
- Alertas push/notificaciones al exceder.
- Presupuestos de ingresos.

## Diseño propuesto
### Backend
- Modelo `budgets`: `{id, household_id, category_id, amount NUMERIC}`, con `UNIQUE(household_id, category_id)`.
- **Decisión recomendada: presupuesto global por categoría** (un límite vigente siempre, aplicado cada mes) en lugar de un registro por mes (`YYYY-MM`). Más simple: se define una vez y se reutiliza; el conteo mensual se calcula con las transacciones del mes. No hay que recrear presupuestos cada mes.
- CRUD `/budgets`: `GET` (lista del hogar), `POST`/`PATCH` (upsert por `category_id`), `DELETE /{id}`. Scoping por `household_id`.
- Endpoint `GET /budgets/status?month=YYYY-MM` → por categoría con presupuesto: `{categoryId, budget, spent, percentage}`, cruzando con la misma lógica de `/summary/month` (solo gastos).
### Frontend
- Sección "Presupuestos" en el dashboard (debajo de la dona): barras de progreso por categoría con color semáforo — verde `<75%`, ámbar `<100%`, rojo `≥100%`. Si crece mucho, evaluar página propia `/presupuestos`.
- Crear/editar límite desde la misma vista: sheet simple con categoría (select) + monto. Editar = mismo sheet precargado.
- Badge en la dona del dashboard si alguna categoría supera su límite (punto rojo o contador).
- Hook nuevo en `src/lib/queries.ts` siguiendo el patrón de mutaciones existente.
### Infra
- Migración Alembic para la tabla `budgets`.

## Criterios de aceptación
- [ ] Definir límite a "Supermercado", registrar gastos → la barra avanza y cambia de color al cruzar 75% y 100%.
- [ ] Al empezar un mes nuevo, el conteo se reinicia sin recrear el presupuesto.
- [ ] No se puede crear un segundo presupuesto para la misma categoría (upsert o error claro).
- [ ] Eliminar una categoría con presupuesto no rompe `/budgets/status` (cascade o validación).
- [ ] `/budgets/status` solo incluye gastos (`type=expense`), no ingresos.
- [ ] Tests: CRUD, cálculo de `spent`/`percentage`, unicidad por hogar+categoría.

## Notas
- Riesgo: duplicar la lógica de agregación de `/summary/month`; reutilizar la misma query base.
- Decisión abierta: si en el futuro se quieren límites distintos por mes, el modelo global migra a `month` nullable sin romper lo existente.
- UX: mostrar también el monto restante ("te quedan $1,200") junto al porcentaje.
