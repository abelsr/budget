# Calendario de flujo de efectivo y proyección de saldo

**Status:** ✅ 2026-08-15 · **Priority:** High · **Effort:** M ·
**Dependencies:** transfers, transacciones recurrentes (ambas ✅)

## Why

El registro responde "¿dónde está el dinero hoy?", pero nadie sabe "¿cómo
 estará el 30?" con lo que ya está comprometido: renta próxima, suscripciones,
nómina que entra. La alerta (item 7a) avisa a destiempo; la proyección lo hace
proactivo con datos que ya existen y son confiables (libro mayor + reglas
recurrentes). Es una segunda mitad del item 7 del roadmap y un prerrequisito
declarado del item 9 (tarjetas MX e instalados).

## Scope

- `GET /forecast?days=90`: proyección diaria del saldo del hogar para los
  próximos `days` días (14–180, default 90), más la lista de próximos
  movimientos previstos (ventana fija de 30 días).
- Entrada de la proyección, en este orden:
  1. Saldo actual del hogar (solo cuentas compartidas, misma fórmula que
     `GET /accounts`), llamado *opening balance*. Esa fórmula **no filtra por
     fecha**: un movimiento registrado con fecha futura ya está incluido aquí.
  2. Ocurrencias futuras de reglas recurrentes activas en cuentas
     compartidas, proyectadas con `advance()` **sin materializar** (lectura
     puramente derivada; el estado vive en `next_run_date`). Son lo único que
     mueve la serie diaria, porque es lo único que **aún no** está en el
     opening.
- Consecuencia: los movimientos registrados con fecha futura no se repiten
  como delta (los aplicaría dos veces); solo aparecen en la lista `upcoming`.
  La serie parte del mismo número que la card "Saldo del hogar", sin
  saltos.
- La proyección llama a `materialize_due` al inicio (convención de todos los
  endpoints de lectura): garantiza que el opening balance sea actual y que no
  falte occurrencia vencida. Es idempotente.

**Excluido deliberadamente** (no es flujo programable, es suposición):
- Presupuestos: son topes de gasto, no flujos previstos.
- Metas de ahorro: sus aportes son manuales y no crean movimientos; el plan es
  advisory. Incluirlo mezclaría proyección con intención.
- Transfer en la columna income/expense: sigue excluido de los reportes
  income/expense igual que en todo el resto de la app; **sí** cuenta en el
  saldo, porque mover de una cuenta compartida a una personal reduce el dinero
  del hogar compartido.

## Design

### Backend

- `app/services/forecast.py`:
  - `build_forecast(db, household_id, as_of, days) -> ForecastResult`
  - Saldo inicial: agregación idéntica a `list_accounts`
    (`opening_balance + income + inflow − expense − outflow` por cuenta
    compartida, `deleted_at IS NULL`, sin filtro de fecha). Extraer la
    fórmula en un helper compartido con `accounts.py` para que no se
    desincronicen.
  - Los movimientos registrados quedan fuera del walk por la misma razón:
    ya están en el opening. Repetirlos lo contaría dos veces.
  - Delta por regla recurrente: desde `next_run_date` (siempre `> as_of` tras
    `materialize_due`) aplicando `advance(next, rule.frequency, rule.anchor_day)`
    hasta pasar el horizonte. Prohibido reimplementar el calendario: el clamp
    mensual de `anchor_day` (ene 31 → feb 28 → mar 31) debe venir de `advance`.
  - Serie: `days + 1` filas desde `as_of`, la primera con `delta = 0` y
    `balance = opening`. El `balance` va sumando; redondear a 2 decimales por
    fila. Invariante de test: `balance[-1] == opening + Σ delta`.
  - `upcoming`: eventos con `as_of < date <= as_of + 30`, máx. 20, ordenados
    por fecha: movimientos registrados futuros (label = nota o categoría) y
    occurrencias proyectadas (label = nota de la regla o categoría).
- `app/schemas/forecast.py`: `ForecastPoint`, `ForecastUpcoming`,
  `ForecastResponse` (fields: `asOf`, `days`, `openingBalance`, `balance[]`,
  `upcoming[]`).
- `GET /forecast` en `app/api/routes/forecast.py`: `days: int = Query(90,
  ge=14, le=180)` → 422 fuera de rango; 400 si el usuario no tiene hogar;
  registra el router en `main.py`.

### Frontend

- Tipos en `lib/types.ts` (`Forecast`, `ForecastPoint`, `ForecastUpcoming`);
  `useForecast()` en `lib/queries.ts` con `keys.forecast`. El invalidador debe
  incluir `keys.forecast` en todas las mutaciones que toca movimientos,
  recurrentes, cuentas o imports (mismo patrón que `keys.summary` hoy).
- `ForecastCard` nuevo en el Dashboard (fila propia, `lg:col-span-12`), dos
  zonas:
  - **Proyección**: AreaChart de `balance` (una sola serie, "Saldo
    proyectado"), gradiente del color primario, `ReferenceLine` punteada en
    0, tooltip con fecha + saldo. Reglas de `docs/design-guidelines.md §4`:
    sin dual axis, leyenda presente, `role="img"` + `aria-label`.
  - **Próximos movimientos**: lista de hasta 4 de `upcoming` (+ "N más"):
    día de la semana abreviado, label, monto con signo en `--income`/
    `--expense` y `.tnum`.
  - Respeta `concealed`: montos enmascarados y `aria-label` sin cifras, igual
    que el resto de cards. Empty state cuando no hay `upcoming`: "Sin
    movimientos previstos para los próximos 30 días" (la ventana de
    `upcoming` es fija de 30 días, aunque la serie proyecte más).
  - Sin nav item nuevo, sin cambio de hero (`§8`): la card usa `dashboard-card`
    y no introduce una superficie azul hero.

## Acceptance criteria

- [x] Opening balance coincide con la suma de saldos de las cuentas
      compartidas en `GET /accounts` en el mismo instante.
- [x] Una regla recurrente cae en su fecha exacta; un movimiento registrado a
      futuro NO repite su efecto en la serie (ya viene en el opening, que
      coincide con `/accounts`) y aparece en `upcoming`; en toda serie
      `balance[-1] == opening + Σ delta`.
- [x] Regla mensual con `anchor_day=31` cruza febrero en 28/29 y vuelve a 31
      (usa `advance`, no matemática propia).
- [x] Regla pausada no proyecta; transfer compartido→compartido no mueve el
      saldo neto; transfer compartido→personal ya reduce el opening (igual que
      `/accounts`) sin doble dip; transacciones de cuenta personal y
      soft-deleted quedan fuera.
- [x] `days` fuera de 14–180 responde 422; default 90 devuelve 91 filas.
- [x] El endpoint no inserta: conteo de transacciones y `next_run_date` de las
      reglas invariables después del `GET`.
- [x] Aislamiento por hogar: ningún dato de otro hogar en la respuesta.
- [x] Card del dashboard respeta paleta (§4), `concealed`, `prefers-reduced-motion`
      y vacía elegante; `npm run build` y `npm run lint` pasan.

## Effort y riesgo

**M.** Riesgos: (1) formular el opening balance distinto al de `/accounts` —
mitigado extrayendo el helper compartido; (2) reimplementar el clamp mensual —
mitigado reutilizando `advance()`; (3) la llamada a `materialize_due` muta el
libro (ocurrencias vencidas) — igual que todos los read endpoints, idempotente
y con `FOR UPDATE`.
