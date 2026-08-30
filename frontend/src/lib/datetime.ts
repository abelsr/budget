/** Backend timestamps without an offset are UTC, not browser-local time. */
export function parseUtcDateTime(value: string): Date {
  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value)
  return new Date(hasTimezone ? value : `${value}Z`)
}

/**
 * Add months to a date, clamping the day to the last day of the target month.
 * `2026-01-31 + 1 month` → `2026-02-28`, not `2026-03-03` (the overflow you
 * get from a bare `setMonth(getMonth() + n)`).
 */
export function addMonthsClamped(iso: string, months: number): string {
  const [year, month, day] = iso.split("-").map(Number)
  const target = new Date(Date.UTC(year, month - 1 + months, 1))
  const lastDay = new Date(Date.UTC(target.getUTCFullYear(), target.getUTCMonth() + 1, 0)).getUTCDate()
  const clampedDay = Math.min(day, lastDay)
  const y = target.getUTCFullYear()
  const m = String(target.getUTCMonth() + 1).padStart(2, "0")
  const d = String(clampedDay).padStart(2, "0")
  return `${y}-${m}-${d}`
}

export function formatUtcDateTime(value: string, formatter: Intl.DateTimeFormat): string {
  return formatter.format(parseUtcDateTime(value))
}
