/**
 * Tipos del dominio — espejo del futuro esquema PostgreSQL.
 * Todas las entidades pertenecen a un hogar (multi-tenant desde el día 1).
 */

export type TransactionType = "expense" | "income"

export type AccountKind = "cash" | "debit" | "credit" | "savings"

/** Emisor de la tarjeta (widget tipo wallet). */
export type CardBrand = "visa" | "mastercard" | "amex" | "other"

/** Cada cuánto se repite una regla recurrente. */
export type Frequency = "weekly" | "monthly"

export interface Member {
  id: string
  name: string
  email: string
  isOwner: boolean
  initials: string
}

export interface Household {
  id: string
  name: string
  currencyCode: string
  isOwner: boolean
}

export interface Account {
  id: string
  householdId: string
  name: string
  kind: AccountKind
  openingBalance: number
  balance: number
  /** Banco (texto libre, ej. "BBVA"). Si se define con `lastFour`, la cuenta
   *  se dibuja como tarjeta tipo wallet. */
  bank?: string | null
  /** Emisor de la tarjeta, cuando aplica. */
  cardBrand?: CardBrand | null
  /** Últimos 4 dígitos del número de tarjeta (nunca el número completo). */
  lastFour?: string | null
}

export interface Category {
  id: string
  householdId: string
  name: string
  /** Nombre de icono Lucide */
  icon: string
  /** Color hex de la categoría (chip, dona) */
  color: string
  type: TransactionType
  active: boolean
}

/** Comprobante adjunto a una transacción (foto, PDF, doc). */
export interface Attachment {
  id: string
  transactionId: string
  filename: string
  contentType: string
  sizeBytes: number
  createdAt: string
}

export interface Transaction {
  id: string
  householdId: string
  type: TransactionType
  amount: number
  categoryId: string
  accountId: string
  memberId: string
  /** Immutable historical author name; available even after household removal. */
  authorName?: string
  /** ISO date: YYYY-MM-DD */
  date: string
  note?: string
  /** Regla que la generó; null si se capturó a mano. */
  recurringRuleId?: string | null
  attachments: Attachment[]
}

export interface NewTransaction {
  type: TransactionType
  amount: number
  categoryId: string
  accountId: string
  date: string
  note?: string
  /**
   * Si viene, el backend crea además la regla recurrente y liga esta
   * transacción como su primera ocurrencia (una sola operación atómica).
   */
  repeat?: Frequency
}

/**
 * Plantilla de un movimiento que se repite.
 *
 * Para reglas activas, el backend materializa las transacciones pendientes al leer,
 * así que `nextRunDate` queda en el futuro después de cualquier lectura.
 * En reglas pausadas puede quedar en el pasado hasta reanudarlas.
 */
export interface RecurringRule {
  id: string
  householdId: string
  type: TransactionType
  amount: number
  categoryId: string
  accountId: string
  createdById: string
  frequency: Frequency
  /** ISO date: YYYY-MM-DD */
  nextRunDate: string
  note: string | null
  active: boolean
}

/** Límite de gasto por categoría. Global (no por mes): ver `budgets/status`. */
export interface Budget {
  id: string
  householdId: string
  categoryId: string
  amount: number
}

/** Gasto del mes vs. límite para una categoría con presupuesto. */
export interface BudgetStatus {
  categoryId: string
  budget: number
  spent: number
  percentage: number
}
