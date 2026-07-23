/**
 * Escaneo de tickets con IA — capa de datos.
 *
 * Llama al endpoint real del backend:
 *
 *   POST /tickets/scan   (multipart/form-data, campo "file")
 *   → 200 { merchant, total, date, suggestedCategoryId, confidence }
 *
 * El backend envía la imagen a Gemini con extracción estructurada.
 * La UI (TicketScanner) consume exactamente este contrato y maneja
 * los errores (501 sin GEMINI_API_KEY, 415 no imagen, 502 análisis
 * fallido, 413 >10MB) a través de ApiError.
 */

import { apiFetch } from "@/lib/api"

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

/** Envía la imagen al backend y devuelve los campos extraídos. */
export async function analyzeTicket(file: File): Promise<TicketScanResult> {
  const formData = new FormData()
  formData.append("file", file)
  return apiFetch<TicketScanResult>("/tickets/scan", {
    method: "POST",
    body: formData,
  })
}
