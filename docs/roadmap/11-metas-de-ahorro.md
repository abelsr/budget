# 🎯 Metas de ahorro

**Estado:** ⬜ Pendiente · **Prioridad:** Media · **Esfuerzo:** M (1-3 días) · **Dependencias:** 01-alembic ✅ (hecho: la tabla nueva entra por migración)

## Por qué
Las familias ahorran para cosas concretas ("vacaciones $30,000 para diciembre", "el enganche del coche") y hoy ese dinero se pierde dentro del saldo de la cuenta de ahorro: no hay visibilidad de cuánto falta ni de si van en ritmo. Una meta con progreso visible convierte el ahorro en algo accionable y motiva a seguir aportando.

## Alcance
**Incluye:**
- Modelo `savings_goals` y CRUD completo (crear, editar, archivar, eliminar)
- Aportación manual del monto actual (MVP simple, ver decisión abajo)
- Tarjetas de metas en el dashboard con progreso (barra o anillo), % y restante
- Estado "cumplida" con celebración sutil y archivado
- Icono y color por meta para distinguirlas de un vistazo

**No incluye:**
- Aportaciones automáticas programadas (eso sería integración con transacciones recurrentes, fase futura)
- Metas multi-cuenta o con reglas complejas de asignación
- Proyecciones de "a este ritmo llegas en X meses" (nice-to-have posterior)

## Diseño propuesto

### Backend
- Modelo `SavingsGoal`: `id`, `household_id` (multi-tenant, como todo), `name`, `target_amount`, `current_amount`, `target_date` (nullable), `account_id` (nullable, FK a `accounts` para vincular la meta a la cuenta donde vive el dinero), `icon`, `color`, `archived` (bool), timestamps
- Endpoints bajo `/goals`: `GET/POST /goals`, `PATCH/DELETE /goals/{id}`, `POST /goals/{id}/contribute` (ajusta `current_amount` con delta positivo o negativo)
- **Decisión sobre aportaciones (recomendada para MVP):** `current_amount` es un campo manual que se actualiza con `/contribute`; la opción "apartar" desde una transacción NO crea una transacción real en el MVP (evita doble conteo: el dinero ya salió como expense o ya está en la cuenta de ahorro). El vínculo con `account_id` es solo informativo ("este ahorro vive en esta cuenta")
- Respuesta de `GET /goals` incluye campos calculados: `progress_pct`, `remaining`, `is_completed` (`current_amount >= target_amount`)
- Tests: CRUD, contribute con delta negativo, completado, aislamiento por `household_id`

### Frontend
- Sección "Metas" en el dashboard: tarjetas con icono/color, barra de progreso (o anillo circular), monto actual / objetivo, % y restante
- Modal/página de crear/editar meta: nombre, objetivo, fecha opcional, cuenta vinculada (select de cuentas), icono y color
- Botón "Aportar" en cada tarjeta con input de monto (soporta retirar con monto negativo)
- Al cumplirse una meta: animación sutil (confeti CSS o transición) y opción de archivar; las archivadas se ocultan por defecto con toggle para verlas
- TanStack Query: invalidar `goals` tras contribute/edit

### Infra
- Sin cambios: la tabla nueva entra por migración de Alembic
  (`uv run alembic revision --autogenerate`), que el entrypoint aplica al
  arrancar. Ya no existe `create_all` en producción.

## Criterios de aceptación
- [ ] Se puede crear una meta con nombre, monto objetivo y fecha opcional
- [ ] Se puede aportar (sumar/restar) y el `current_amount` persiste
- [ ] El dashboard muestra progreso en % y monto restante por meta
- [ ] Al llegar al 100% se muestra la celebración y la meta se puede archivar
- [ ] Las metas de un hogar no son visibles para otro hogar
- [ ] Los tests de pytest nuevos pasan junto con los existentes

## Notas
- Riesgo de doble conteo si más adelante se ligan aportaciones a transacciones reales: documentar desde ya que `current_amount` es el estado de la meta, independiente del flujo de transacciones.
- Decisión abierta: ¿qué pasa con la meta si se elimina la cuenta vinculada? Recomendado: `ON DELETE SET NULL`, la meta sobrevive.
- La celebración debe ser sutil y dismissible: es una app de uso diario, no un juego.
