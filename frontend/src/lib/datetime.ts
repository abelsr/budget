/** Backend timestamps without an offset are UTC, not browser-local time. */
export function parseUtcDateTime(value: string): Date {
  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value)
  return new Date(hasTimezone ? value : `${value}Z`)
}

export function formatUtcDateTime(value: string, formatter: Intl.DateTimeFormat): string {
  return formatter.format(parseUtcDateTime(value))
}
