/**
 * Formato de moneda y fechas. La moneda del hogar es configurable;
 * por ahora el mock usa MXN.
 */

const MXN = new Intl.NumberFormat("es-MX", {
  style: "currency",
  currency: "MXN",
})

export function formatMoney(amount: number, compact = false): string {
  if (compact && Math.abs(amount) >= 100_000) {
    return new Intl.NumberFormat("es-MX", {
      style: "currency",
      currency: "MXN",
      notation: "compact",
      maximumFractionDigits: 1,
    }).format(amount)
  }
  return MXN.format(amount)
}

/** Monto corto para ejes y etiquetas de gráfica: `$1.2k`, `$850`. */
// `Intl.NumberFormat` es caro de construir y Recharts invoca esto muchas veces
// por render; cacheamos los dos casos (≥10k y <10k) a nivel de módulo.
const compactFmtHigh = new Intl.NumberFormat("es-MX", {
  style: "currency",
  currency: "MXN",
  notation: "compact",
  maximumFractionDigits: 0,
})
const compactFmtLow = new Intl.NumberFormat("es-MX", {
  style: "currency",
  currency: "MXN",
  notation: "compact",
  maximumFractionDigits: 1,
})

export function formatMoneyCompact(amount: number): string {
  return (Math.abs(amount) >= 10_000 ? compactFmtHigh : compactFmtLow).format(amount)
}

const dayFmt = new Intl.DateTimeFormat("es-MX", {
  weekday: "long",
  day: "numeric",
  month: "long",
})

const shortFmt = new Intl.DateTimeFormat("es-MX", {
  day: "numeric",
  month: "short",
})

const weekdayShortFmt = new Intl.DateTimeFormat("es-MX", {
  weekday: "short",
})

export function formatWeekdayShort(isoDate: string): string {
  return weekdayShortFmt.format(new Date(isoDate + "T12:00:00"))
}

export function formatDayHeader(isoDate: string): string {
  const date = new Date(isoDate + "T12:00:00")
  const today = new Date()
  const yesterday = new Date()
  yesterday.setDate(today.getDate() - 1)
  const key = isoDate
  if (key === toISODate(today)) return "Hoy"
  if (key === toISODate(yesterday)) return "Ayer"
  return capitalize(dayFmt.format(date))
}

export function formatShortDate(isoDate: string): string {
  return shortFmt.format(new Date(isoDate + "T12:00:00"))
}

export function toISODate(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, "0")
  const day = String(d.getDate()).padStart(2, "0")
  return `${y}-${m}-${day}`
}

export function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1)
}

/**
 * Parsea un monto digitado a número, o `null` si no es un monto válido.
 * Nunca devuelve 0 para entrada inválida: el llamador decide cómo tratar el
 * `null` (bloquear el guardado / mostrar error), jamás como monto cero.
 *
 * Formatos válidos:
 * - US: `1,234.56`, `1,234`, `1234.56`, `1234`
 * - MX/EU: `1.234,56`, `12,34`
 * - `0`
 *
 * Admite un signo menos inicial único (para saldos negativos); un signo en
 * otra posición o más de uno se rechaza (`1-2`, `--`).
 *
 * Desambiguación (regla consistente, documentada):
 * - Con separador de miles (coma `1,234…` o punto `1.234…`) el decimal, si
 *   hay, va con el otro separador y exige exactamente 2 dígitos
 *   (`1,234.56` ✓, `1.234,56` ✓, `1,234.5` ✗, `1.234,5` ✗).
 * - Sin separador de miles, un punto o coma seguidos de 1–2 dígitos es el
 *   decimal (`1234.56`, `12,34`, `1,23` ✓); seguidos de 3 dígitos es miles
 *   (`1.234` → 1234, `123.456` → 123456).
 *
 * Rechaza (null): `1-2`, `1.2.3`, `abc`, `""`, `--`, `1..2`, `1,2,3`,
 * `1.2345`.
 */
export function parseAmount(text: string): number | null {
  const match = text.trim().match(
    /^(?<sign>-)?(?:(?<usThousands>\d{1,3}(?:,\d{3})+)(?<usDec>\.\d{2})?|(?<euThousands>\d{1,3}(?:\.\d{3})+)(?<euDec>,\d{2})?|(?<plain>\d+)(?<plainDec>\.\d{1,2}|,\d{1,2})?)$/,
  )
  if (!match) return null
  const { sign, usThousands, usDec, euThousands, euDec, plain, plainDec } =
    match.groups ?? {}
  let value: string
  if (usThousands) {
    value = usThousands.replace(/,/g, "") + (usDec ?? "")
  } else if (euThousands) {
    value = euThousands.replace(/\./g, "") + (euDec ? `.${euDec.slice(1)}` : "")
  } else {
    value = plain + (plainDec ? `.${plainDec.slice(1)}` : "")
  }
  const parsed = Number(`${sign ?? ""}${value}`)
  return Number.isFinite(parsed) ? parsed : null
}

export function monthLabel(): string {
  return capitalize(
    new Intl.DateTimeFormat("es-MX", { month: "long", year: "numeric" }).format(
      new Date(),
    ),
  )
}
