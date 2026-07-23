/**
 * Escaneo de tickets con IA — capa de datos.
 *
 * INTEGRACIÓN BACKEND (pendiente): reemplazar `analyzeTicket` por una
 * llamada real:
 *
 *   POST /tickets/scan   (multipart/form-data, campo "file")
 *   → 200 { merchant, total, date, suggestedCategoryId, confidence }
 *
 * El backend enviará la imagen a un modelo de visión (por definir:
 * GPT-4o, Claude, Gemini u Ollama local) con extracción estructurada.
 * La UI (TicketScanner) ya consume exactamente este contrato.
 */

export interface TicketScanResult {
  /** Comercio detectado (va a la nota del gasto) */
  merchant: string
  total: number
  /** ISO date YYYY-MM-DD */
  date: string
  suggestedCategoryId: string
  /** 0–1; la UI avisa si es baja para revisar con cuidado */
  confidence: number
}

const MOCK_RESULTS: Omit<TicketScanResult, "date">[] = [
  { merchant: "Walmart", total: 1234.56, suggestedCategoryId: "c-1", confidence: 0.96 },
  { merchant: "Starbucks", total: 145.0, suggestedCategoryId: "c-2", confidence: 0.93 },
  { merchant: "Oxxo Gas", total: 500.0, suggestedCategoryId: "c-3", confidence: 0.91 },
  { merchant: "Farmacia Guadalajara", total: 389.9, suggestedCategoryId: "c-6", confidence: 0.88 },
  { merchant: "Cinépolis", total: 320.0, suggestedCategoryId: "c-7", confidence: 0.85 },
]

/** Simula la latencia y el resultado del análisis de visión. */
export async function analyzeTicket(_file: File): Promise<TicketScanResult> {
  await new Promise((resolve) => setTimeout(resolve, 1600))
  const pick = MOCK_RESULTS[Math.floor(Math.random() * MOCK_RESULTS.length)]
  const now = new Date()
  const date = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`
  return { ...pick, date }
}
