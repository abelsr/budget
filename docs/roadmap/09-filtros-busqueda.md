# 🔍 Filtros y búsqueda en Movimientos

**Estado:** ⬜ Pendiente · **Prioridad:** Media · **Esfuerzo:** S (<1 día) · **Dependencias:** Ninguna

## Por qué
La lista de Movimientos crece cada día y hoy no hay forma de encontrar nada: ni buscar por nota, ni filtrar por categoría o cuenta. Es la carencia más visible de la página.

## Alcance
**Incluye:**
- Parámetros de filtro/búsqueda en `GET /transactions`.
- Barra de búsqueda con debounce y chips de filtro en Movimientos.
- Filtros reflejados en la URL (compartibles).

**No incluye:**
- Búsqueda full-text avanzada (ranking, fuzzy).
- Filtros guardados o vistas personalizadas.
- Filtrado en el dashboard.

## Diseño propuesto
### Backend
- Extender `GET /transactions` con query params:
  - `q`: busca en `note` con `ILIKE '%q%'`.
  - `categoryId`, `accountId`, `memberId`, `type` (`expense|income`).
  - `from`, `to`: rango de fechas (ISO).
- Mantener compatibilidad total con los params actuales (`month`, `limit`, `offset`); si vienen `from`/`to` junto con `month`, `month` tiene precedencia o se documenta la combinación (decidir y documentar).
- Índice en `transactions(household_id, date)` si no existe ya, para sostener los filtros con paginación.
### Frontend
- Barra de búsqueda en Movimientos: input con icono `Search`, debounce de 300ms, ligada al param `q`.
- Fila de chips de filtro debajo: categoría, cuenta, tipo (gasto/ingreso). Si crecen, mover a un sheet de filtros.
- Estado vacío amable: "Sin resultados para estos filtros" con botón para limpiar.
- Filtros sincronizados con query params de la URL (`?q=sams&categoryId=…`) usando el router, para URLs compartibles.
- Actualizar el hook de `src/lib/queries.ts` para pasar los params a TanStack Query (query key incluye los filtros).
### Infra
- Sin cambios (índice vía migración si aplica).

## Criterios de aceptación
- [ ] Escribir "sams" filtra la lista a transacciones cuya nota contiene "sams" (case-insensitive).
- [ ] Combinar categoría + cuenta funciona (intersección).
- [ ] Limpiar filtros restaura la lista completa.
- [ ] Copiar la URL con filtros y abrirla en otra pestaña conserva los filtros aplicados.
- [ ] Los params existentes (`month`, `limit`, `offset`) siguen funcionando igual.
- [ ] Tests: cada param individual, combinaciones, búsqueda `ILIKE` case-insensitive.

## Notas
- Riesgo bajo; el principal es la interacción `month` vs `from`/`to` — resolverlo con una regla explícita documentada.
- El debounce y la query key correcta evitan refetches innecesarios al teclear.
