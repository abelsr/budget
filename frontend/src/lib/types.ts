/**
 * Tipos del dominio — espejo del futuro esquema PostgreSQL.
 * Todas las entidades pertenecen a un hogar (multi-tenant desde el día 1).
 */

export type TransactionType = "expense" | "income"

export type AccountKind = "cash" | "debit" | "credit" | "savings"

/** Cada cuánto se repite una regla recurrente. */
export type Frequency = "weekly" | "monthly"

export interface Member {
  id: string
  name: string
  initials: string
}

export interface Account {
  id: string
  householdId: string
  name: string
  kind: AccountKind
  openingBalance: number
  balance: number
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
