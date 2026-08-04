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

export function monthLabel(): string {
  return capitalize(
    new Intl.DateTimeFormat("es-MX", { month: "long", year: "numeric" }).format(
      new Date(),
    ),
  )
}
