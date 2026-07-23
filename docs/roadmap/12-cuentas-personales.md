# 👤 Cuentas personales vs compartidas

**Estado:** ⬜ Pendiente · **Prioridad:** Baja · **Esfuerzo:** M (1-3 días) · **Dependencias:** 01-alembic (migración real sobre datos existentes)

## Por qué
La decisión original del producto fue "todas las cuentas son del hogar, con trazabilidad de quién registró cada movimiento". Eso funciona para gastos comunes, pero choca con casos reales: la cuenta personal de nómina, una tarjeta que uno no quiere compartir, un ahorro privado. Sin cuentas personales, los usuarios terminan no registrando esos movimientos y la app pierde valor. Es un cambio de modelo, no una feature más.

## Alcance
**Incluye:**
- Campo `owner_id` (nullable) en `accounts`: `NULL` = compartida (comportamiento actual), con valor = personal de ese usuario
- Visibilidad: cuentas personales solo visibles para su dueño; saldos y reportes del hogar excluyen cuentas personales ajenas
- Vista de usuario: "Mis cuentas" (personales propias + compartidas) y resumen del hogar solo con compartidas
- Migración de datos: todas las cuentas existentes quedan compartidas (`owner_id = NULL`)
- UI: toggle "Personal" al crear/editar cuenta; secciones separadas en la página de Cuentas

**No incluye:**
- Permisos granulares (compartir una cuenta con algunos miembros y no otros)
- Mover transacciones existentes entre cuentas al cambiar visibilidad
- Cuentas personales con moneda distinta (la moneda sigue siendo una por hogar, MXN)

## Diseño propuesto

### Backend
- Migración Alembic: `ALTER TABLE accounts ADD COLUMN owner_id UUID NULL REFERENCES users(id)`
- Data migration en la misma revisión: no-op (las existentes ya quedan en `NULL` = compartidas por defecto)
- Query de listado de cuentas: `WHERE household_id = :hid AND (owner_id IS NULL OR owner_id = :current_user)`
- Totales del hogar (dashboard, resumen, reportes): `WHERE household_id = :hid AND owner_id IS NULL` — solo compartidas
- Totales personales del usuario: compartidas + personales propias
- Transacciones en cuentas personales: solo visibles para el dueño (mismo filtro por `owner_id` de la cuenta al listar movimientos); no aparecen en el feed/reportes del hogar para los demás
- Regla de escritura: cualquier miembro puede crear cuenta personal o compartida; solo el dueño puede editar/eliminar una personal
- Tests: visibilidad cruzada (A no ve la personal de B), totales del hogar sin personales, total personal de A incluye ambas

### Frontend
- Formulario de cuenta: toggle "Personal" (explicación: "solo tú la verás; no suma al total del hogar")
- Página de Cuentas con dos secciones: "Del hogar" y "Personales" (esta última vacía con CTA si no hay)
- Dashboard: el total del hogar sigue igual (compartidas); opcional una línea secundaria "Tu total personal" que incluye personales
- Badge sutil "Personal" en las tarjetas de cuenta propias para recordar la visibilidad
- Al cambiar una cuenta de compartida a personal (o viceversa): confirmación explicando el efecto en saldos y visibilidad

### Infra
- Sin cambios (la migración corre con el entrypoint de Alembic de 01)

## Criterios de aceptación
- [ ] La cuenta personal de A es invisible para B en listados, movimientos y saldos
- [ ] El total del hogar solo incluye cuentas compartidas
- [ ] El total personal de A incluye sus personales + las compartidas
- [ ] Las cuentas existentes antes de la migración siguen visibles para todos (compartidas)
- [ ] Se puede convertir una cuenta compartida en personal y viceversa sin perder transacciones
- [ ] Los tests nuevos y existentes pasan

## Notas
- Riesgo principal: queries existentes que hoy asumen "todas las cuentas del hogar son de todos". Auditar TODOS los endpoints que tocan `accounts` o agregan saldos antes de darlo por cerrado.
- Decisión abierta: ¿una cuenta personal puede recibir transacciones registradas por otro miembro? Recomendado: no, el dueño es el único que opera su cuenta personal.
- Este cambio revisita una decisión documentada ("todas compartidas"); actualizar esa nota de decisión donde viva para que no quede contradictoria.
