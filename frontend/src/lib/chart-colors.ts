/**
 * Color de series para gráficas — ver docs/design-guidelines.md §4.
 *
 * Las categorías guardan **un** hex (el paso claro). En modo oscuro ese paso
 * pierde contraste sobre la superficie #121a2b, así que:
 *
 *  1. si el color es uno de los ocho documentados, se usa su gemelo oscuro
 *     (pasos *elegidos* y validados, no un flip automático);
 *  2. si el usuario eligió un color propio, se ajusta su luminosidad OKLCH
 *     dentro de la banda oscura (0.48–0.67) conservando tono y croma.
 *
 * Validación (skill dataviz, OKLab ΔE ×100, Machado 2009 @1.0):
 *   claro sobre #ffffff — CVD 10.3 · visión normal 19.6 · contraste ≥3:1
 *   oscuro sobre #121a2b — CVD 10.5 · visión normal 18.2 · contraste ≥3:1
 */

/** Paleta categórica, orden fijo. Nunca se cicla: la novena serie es "Otros". */
export const CHART_PALETTE_LIGHT = [
  "#2563eb", // 1 azul de marca
  "#ea580c", // 2 naranja
  "#0d9488", // 3 verde azulado
  "#b77c05", // 4 ámbar
  "#db2777", // 5 rosa
  "#4d7c0f", // 6 oliva
  "#7c3aed", // 7 violeta
  "#9a5b26", // 8 café
] as const

export const CHART_PALETTE_DARK = [
  "#5b8def",
  "#e06a33",
  "#2aa79b",
  "#b98b22",
  "#de5a93",
  "#74992f",
  "#9b7bf0",
  "#b4763b",
] as const

/** Gris para el segmento "Otros" (no es una novena identidad). */
export const CHART_OTHER = { light: "#94a3b8", dark: "#64748b" } as const

const DARK_BAND = { min: 0.48, max: 0.67 }

const documented = new Map(
  CHART_PALETTE_LIGHT.map((hex, i) => [hex, CHART_PALETTE_DARK[i]]),
)

// ── conversión sRGB ↔ OKLab (Björn Ottosson) ────────────────────────────────

function srgbToLinear(c: number): number {
  return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
}

function linearToSrgb(c: number): number {
  return c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055
}

function hexToRgb(hex: string): [number, number, number] | null {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex.trim())
  if (!m) return null
  const n = parseInt(m[1], 16)
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255]
}

function rgbToHex(r: number, g: number, b: number): string {
  const to = (c: number) =>
    Math.round(Math.min(1, Math.max(0, c)) * 255)
      .toString(16)
      .padStart(2, "0")
  return `#${to(r)}${to(g)}${to(b)}`
}

function rgbToOklab(r: number, g: number, b: number) {
  const lr = srgbToLinear(r)
  const lg = srgbToLinear(g)
  const lb = srgbToLinear(b)
  const l = Math.cbrt(0.4122214708 * lr + 0.5363325363 * lg + 0.0514459929 * lb)
  const m = Math.cbrt(0.2119034982 * lr + 0.6806995451 * lg + 0.1073969566 * lb)
  const s = Math.cbrt(0.0883024619 * lr + 0.2817188376 * lg + 0.6299787005 * lb)
  return {
    L: 0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s,
    a: 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s,
    b: 0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s,
  }
}

function oklabToHex(L: number, a: number, bb: number): string {
  const l = (L + 0.3963377774 * a + 0.2158037573 * bb) ** 3
  const m = (L - 0.1055613458 * a - 0.0638541728 * bb) ** 3
  const s = (L - 0.0894841775 * a - 1.291485548 * bb) ** 3
  return rgbToHex(
    linearToSrgb(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s),
    linearToSrgb(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s),
    linearToSrgb(-0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s),
  )
}

/**
 * Color de una serie en el modo activo.
 * Colores documentados → su paso oscuro; el resto → luminosidad ajustada
 * a la banda oscura conservando tono y croma.
 */
export function seriesColor(hex: string, isDark: boolean): string {
  if (!isDark) return hex
  const mapped = documented.get(hex.toLowerCase() as (typeof CHART_PALETTE_LIGHT)[number])
  if (mapped) return mapped
  const rgb = hexToRgb(hex)
  if (!rgb) return hex
  const { L, a, b } = rgbToOklab(...rgb)
  const clamped = Math.min(DARK_BAND.max, Math.max(DARK_BAND.min, L))
  if (clamped === L) return hex
  return oklabToHex(clamped, a, b)
}

/** Lee un token CSS del tema activo (para pasar colores a Recharts). */
export function cssVar(name: string): string {
  if (typeof window === "undefined") return ""
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}
