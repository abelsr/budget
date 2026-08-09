# Planes de metas

**Status:** ✅ 2026-08-08 · **Priority:** Medium · **Effort:** S ·
**Dependencies:** 20-alertas-en-app ✅

## Why

Una meta manual con fecha no indica qué aporte hace falta para llegar a tiempo.
El plan convierte su saldo y fecha en una cuota clara sin crear movimientos ni
mezclar el ahorro con el libro mayor.

## Scope

- Cuota mensual derivada de una meta con fecha objetivo.
- Pausa y reanudación del plan conservando el monto manual, la fecha y la meta.
- Estado visible de plan activo, pausado, vencido, completado o sin plan.

No incluye aportes automáticos, transacciones ni historial de ritmo de ahorro.

## Design

- `savings_goals.plan_paused` conserva solamente la decisión de pausa.
- La cuota mensual divide el monto restante entre los meses calendario que
  faltan, incluido el mes actual, y se redondea hacia arriba a cuatro decimales.
- El plan solo está activo si la meta no está archivada ni completada, tiene una
  fecha futura o del mes actual y no está pausada.
- El formulario recibe los datos derivados mediante `GET /goals`, muestra la
  cuota o el vencimiento y permite pausar y reanudar cuando existe fecha objetivo.

## Acceptance criteria

- [x] La API calcula la cuota para meses inclusivos y no altera movimientos.
- [x] Pausar y reanudar persiste el estado sin cambiar el monto de la meta.
- [x] Metas archivadas, completadas o vencidas no exigen una cuota activa.
- [x] Tests cubren el cálculo, pausa, reanudación, finalización y vencimiento.
