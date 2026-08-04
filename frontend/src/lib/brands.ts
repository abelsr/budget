/**
 * Registro de marcas (bancos, comercios, servicios) para el app.
 *
 * - `BRANDS` es la fuente de verdad: keywords para reconocer el comercio en la
 *   nota de una transacción, color de marca (paso claro, para el medallón
 *   tintado), monograma de respaldo cuando no hay SVG, y el slug del logo.
 * - El path SVG viene de `brand-logos.generated.ts` (generado por
 *   scripts/build-brand-logos.mjs a partir de frontend/public/brands/).
 * - Convenciones (docs/design-guidelines.md §7): el medallón es un círculo con
 *   el color de la marca al 12% de fondo + la marca coloreada, igual que los
 *   medallones de categoría. En dark mode el color se mapea con `seriesColor`.
 *
 * Si no hay logo: se muestra el monograma sobre el color de marca (nunca se
 * bloquea una fila por no tener SVG). Lista de logos pendientes:
 * frontend/public/brands/README.md
 */

export type BrandCategory = "banks" | "shops" | "services"

export interface Brand {
  /** Slug único (también el nombre de archivo del logo). */
  id: string
  name: string
  category: BrandCategory
  /** Fragmentos normalizados que se buscan en la nota de la transacción. */
  keywords: string[]
  /** Paso claro del color de marca (para medallón y monograma). */
  color: string
  /** Letras de respaldo cuando `logo` no existe. */
  monogram: string
  /** Slug en BRAND_LOGOS; undefined → monograma. */
  logo?: string
}

export const BRANDS: Brand[] = [
  // ── bancos ────────────────────────────────────────────────────────────────
  { id: "visa", name: "Visa", category: "banks", keywords: ["visa"], color: "#1a1f71", monogram: "V", logo: "visa" },
  { id: "mastercard", name: "Mastercard", category: "banks", keywords: ["mastercard"], color: "#eb001b", monogram: "M", logo: "mastercard" },
  { id: "american-express", name: "American Express", category: "banks", keywords: ["american express", "amex"], color: "#2e77bc", monogram: "AE", logo: "american-express" },
  { id: "discover", name: "Discover", category: "banks", keywords: ["discover"], color: "#ff6000", monogram: "D", logo: "discover" },
  { id: "paypal", name: "PayPal", category: "banks", keywords: ["paypal"], color: "#00457c", monogram: "P", logo: "paypal" },
  { id: "mercado-pago", name: "Mercado Pago", category: "banks", keywords: ["mercado pago", "mercadopago"], color: "#009ee3", monogram: "MP", logo: "mercado-pago" },
  { id: "hsbc", name: "HSBC", category: "banks", keywords: ["hsbc"], color: "#db0011", monogram: "H", logo: "hsbc" },
  { id: "nubank", name: "Nu", category: "banks", keywords: ["nubank", "nu bank"], color: "#820ad1", monogram: "N", logo: "nubank" },
  { id: "bbva", name: "BBVA", category: "banks", keywords: ["bbva", "bancomer"], color: "#004481", monogram: "B", logo: "bbva" },
  { id: "santander", name: "Santander", category: "banks", keywords: ["santander"], color: "#ec0000", monogram: "S", logo: "santander" },
  { id: "scotiabank", name: "Scotiabank", category: "banks", keywords: ["scotiabank"], color: "#d6001c", monogram: "S", logo: "scotiabank" },
  { id: "banorte", name: "Banorte", category: "banks", keywords: ["banorte"], color: "#003a70", monogram: "B", logo: "banorte" },
  { id: "citibanamex", name: "Citibanamex", category: "banks", keywords: ["citibanamex", "banamex"], color: "#006847", monogram: "B", logo: "citibanamex" },
  { id: "banco-azteca", name: "Banco Azteca", category: "banks", keywords: ["banco azteca", "bancoazteca"], color: "#e4002b", monogram: "A", logo: "banco-azteca" },
  { id: "klar", name: "Klar", category: "banks", keywords: ["klar"], color: "#00a960", monogram: "K", logo: "klar" },
  { id: "stp", name: "STP", category: "banks", keywords: ["stp"], color: "#f58220", monogram: "S" },

  // ── comercios ─────────────────────────────────────────────────────────────
  { id: "sams-club", name: "Sam's Club", category: "shops", keywords: ["sams club", "samsclub", "sams"], color: "#0067a0", monogram: "S", logo: "sams-club" },
  { id: "chedraui", name: "Chedraui", category: "shops", keywords: ["chedraui"], color: "#e0832f", monogram: "C", logo: "chedraui" },
  { id: "coppel", name: "Coppel", category: "shops", keywords: ["coppel", "bancoppel"], color: "#0266ae", monogram: "C", logo: "coppel" },
  { id: "soriana", name: "Soriana", category: "shops", keywords: ["soriana"], color: "#d52b1e", monogram: "S", logo: "soriana" },
  { id: "starbucks", name: "Starbucks", category: "shops", keywords: ["starbucks", "star"], color: "#00704a", monogram: "S", logo: "starbucks" },
  { id: "mcdonalds", name: "McDonald's", category: "shops", keywords: ["mcdonalds", "mc donalds", "donalds"], color: "#f7b731", monogram: "M", logo: "mcdonalds" },
  { id: "burger-king", name: "Burger King", category: "shops", keywords: ["burger king", "burgerking"], color: "#d62300", monogram: "B", logo: "burger-king" },
  { id: "kfc", name: "KFC", category: "shops", keywords: ["kfc"], color: "#f40027", monogram: "K", logo: "kfc" },
  { id: "walmart", name: "Walmart", category: "shops", keywords: ["walmart"], color: "#0071ce", monogram: "W", logo: "walmart" },
  { id: "oxxo", name: "OXXO", category: "shops", keywords: ["oxxo"], color: "#e51b24", monogram: "O", logo: "oxxo" },
  { id: "costco", name: "Costco", category: "shops", keywords: ["costco"], color: "#e31837", monogram: "C", logo: "costco" },
  { id: "amazon", name: "Amazon", category: "shops", keywords: ["amazon"], color: "#ff9900", monogram: "A", logo: "amazon" },
  { id: "la-comer", name: "La Comer", category: "shops", keywords: ["la comer", "lacomer"], color: "#d00027", monogram: "LC" },
  { id: "liverpool", name: "Liverpool", category: "shops", keywords: ["liverpool"], color: "#e00000", monogram: "L", logo: "liverpool" },
  { id: "el-palacio-de-hierro", name: "El Palacio de Hierro", category: "shops", keywords: ["palacio de hierro", "el palacio"], color: "#1b1b1b", monogram: "P", logo: "el-palacio-de-hierro" },
  { id: "bodega-aurrera", name: "Bodega Aurrerá", category: "shops", keywords: ["bodega aurrera", "aurrera"], color: "#e8700c", monogram: "BA", logo: "bodega-aurrera" },
  { id: "farmacias-del-ahorro", name: "Farmacias del Ahorro", category: "shops", keywords: ["farmacias del ahorro", "del ahorro"], color: "#e87722", monogram: "F", logo: "farmacias-del-ahorro" },
  { id: "farmacias-guadalajara", name: "Farmacias Guadalajara", category: "shops", keywords: ["farmacias guadalajara", "farmacias gdl"], color: "#005da3", monogram: "FG", logo: "farmacias-guadalajara" },
  { id: "sanborns", name: "Sanborns", category: "shops", keywords: ["sanborns"], color: "#e21a22", monogram: "S", logo: "sanborns" },
  { id: "dominos-pizza", name: "Domino's", category: "shops", keywords: ["dominos", "domino"], color: "#e31837", monogram: "D", logo: "dominos-pizza" },
  { id: "cinepolis", name: "Cinépolis", category: "shops", keywords: ["cinepolis"], color: "#d70017", monogram: "C", logo: "cinepolis" },
  { id: "mercado-libre", name: "Mercado Libre", category: "shops", keywords: ["mercado libre", "mercadolibre"], color: "#002e9c", monogram: "M", logo: "mercado-libre" },

  // ── servicios ─────────────────────────────────────────────────────────────
  { id: "airbnb", name: "Airbnb", category: "services", keywords: ["airbnb"], color: "#ff5a5f", monogram: "A", logo: "airbnb" },
  { id: "at-and-t", name: "AT&T", category: "services", keywords: ["atandt", "at&t", "att"], color: "#009fdb", monogram: "AT", logo: "at-and-t" },
  { id: "movistar", name: "Movistar", category: "services", keywords: ["movistar"], color: "#00a6d6", monogram: "M", logo: "movistar" },
  { id: "uber", name: "Uber", category: "services", keywords: ["uber"], color: "#000000", monogram: "U", logo: "uber" },
  { id: "netflix", name: "Netflix", category: "services", keywords: ["netflix"], color: "#e50914", monogram: "N", logo: "netflix" },
  { id: "spotify", name: "Spotify", category: "services", keywords: ["spotify"], color: "#1db954", monogram: "S", logo: "spotify" },
  { id: "youtube", name: "YouTube", category: "services", keywords: ["youtube", "youtube premium", "youtube tv"], color: "#ff0000", monogram: "YT", logo: "youtube" },
  { id: "max", name: "Max", category: "services", keywords: ["hbo max", "hbomax", "hbo"], color: "#525252", monogram: "M", logo: "max" },
  { id: "steam", name: "Steam", category: "services", keywords: ["steam"], color: "#171a21", monogram: "S", logo: "steam" },
  { id: "playstation", name: "PlayStation", category: "services", keywords: ["playstation", "ps plus", "playstation plus"], color: "#003791", monogram: "PS", logo: "playstation" },
  { id: "epic-games", name: "Epic Games", category: "services", keywords: ["epic games", "epicgames", "fortnite"], color: "#313131", monogram: "E", logo: "epic-games" },
  { id: "cfe", name: "CFE", category: "services", keywords: ["cfe", "comision federal", "luz"], color: "#00a651", monogram: "CFE", logo: "cfe" },
  { id: "telmex", name: "Telmex", category: "services", keywords: ["telmex", "infinitum"], color: "#e2001a", monogram: "T", logo: "telmex" },
  { id: "telcel", name: "Telcel", category: "services", keywords: ["telcel"], color: "#e2001a", monogram: "T", logo: "telcel" },
  { id: "izzi", name: "Izzi", category: "services", keywords: ["izzi"], color: "#e6007e", monogram: "I", logo: "izzi" },
  { id: "totalplay", name: "Totalplay", category: "services", keywords: ["totalplay", "total play"], color: "#5e2c97", monogram: "T", logo: "totalplay" },
  { id: "megacable", name: "Megacable", category: "services", keywords: ["megacable"], color: "#0072bc", monogram: "M", logo: "megacable" },
  { id: "pemex", name: "Pemex", category: "services", keywords: ["pemex", "gasolina", "gasolinera"], color: "#00843d", monogram: "P", logo: "pemex" },
  { id: "rappi", name: "Rappi", category: "services", keywords: ["rappi"], color: "#ff5522", monogram: "R", logo: "rappi" },
  { id: "disneyplus", name: "Disney+", category: "services", keywords: ["disney plus", "disneyplus", "disney+"], color: "#113ccf", monogram: "D", logo: "disneyplus" },
  { id: "prime-video", name: "Prime Video", category: "services", keywords: ["prime video", "primevideo", "amazon prime"], color: "#00a8e1", monogram: "PV", logo: "prime-video" },
  { id: "xbox", name: "Xbox", category: "services", keywords: ["xbox", "game pass", "xbox game"], color: "#107c10", monogram: "X", logo: "xbox" },
  { id: "nintendo", name: "Nintendo", category: "services", keywords: ["nintendo", "switch"], color: "#e60012", monogram: "N", logo: "nintendo" },
]

/** Nombres de bancos reconocidos, para el datalist del formulario de cuentas. */
export const BANK_SUGGESTIONS = BRANDS.filter((b) => b.category === "banks").map(
  (b) => b.name,
)

/** Busca una marca por id (bancos en tarjetas de cuenta, etc.). */
export function getBrand(id: string | undefined | null): Brand | undefined {
  if (!id) return undefined
  return BRANDS.find((b) => b.id === id)
}

/** Normaliza texto para comparar marcas: minúsculas, sin acentos, & → and. */
export function normalizeText(s: string): string {
  return s
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/&/g, " and ")
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim()
}

/**
 * Matchers precomputados: cada keyword se normaliza **una sola vez** al cargar
 * el módulo (no por llamada), y se ordena de mayor a menor longitud para que
 * `matchBrand` pueda devolver el primer match y salir temprano. El sort es
 * estable: empates entre keywords del mismo largo conservan el orden de BRANDS,
 * igual que la búsqueda original de "el más largo gana".
 */
interface BrandMatcher {
  brand: Brand
  kw: string
}

const MATCHERS: BrandMatcher[] = BRANDS.flatMap((brand) =>
  brand.keywords
    .map((raw) => ({ brand, kw: normalizeText(raw) }))
    .filter((m) => m.kw.length > 0),
).sort((a, b) => b.kw.length - a.kw.length)

/**
 * Reconocimiento de comercio por la nota de la transacción. Devuelve la marca
 * cuyo keyword más largo coincida; reglas:
 * - keywords de ≥4 caracteres matchean como substring de la nota normalizada;
 * - keywords cortos (3) solo como palabra completa (evita "nu"/"stp" falsos);
 * - gana el keyword más largo (especificidad), no el orden del arreglo.
 */
export function matchBrand(note: string | null | undefined): Brand | null {
  const n = normalizeText(note ?? "")
  if (!n) return null
  const words = new Set(n.split(" "))
  for (const { brand, kw } of MATCHERS) {
    const ok = kw.length >= 4 ? n.includes(kw) : words.has(kw)
    if (ok) return brand
  }
  return null
}
