/**
 * Tipos del dominio — espejo del futuro esquema PostgreSQL.
 * Todas las entidades pertenecen a un hogar (multi-tenant desde el día 1).
 */

export type TransactionType = "expense" | "income" | "transfer"

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
  isPersonal: boolean
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
  clientId?: string | null
  householdId: string
  type: TransactionType
  amount: number
  categoryId: string | null
  accountId: string
  memberId: string
  /** Immutable historical author name; available even after household removal. */
  authorName?: string
  /** ISO date: YYYY-MM-DD */
  date: string
  note?: string
  /** Regla que la generó; null si se capturó a mano. */
  recurringRuleId?: string | null
  transferGroupId?: string | null
  transferDirection?: "outflow" | "inflow" | null
  counterpartyAccountId?: string | null
  counterpartyAccountName?: string | null
  attachments: Attachment[]
  /** Local-only state for an outbox record; it is never sent to the API. */
  syncStatus?: "pending" | "failed"
  syncError?: string
}

export interface NewTransaction {
  type: "expense" | "income"
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

export interface NewTransfer {
  type: "transfer"
  amount: number
  sourceAccountId: string
  destinationAccountId: string
  date: string
  note?: string
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

/** Meta de ahorro manual. Sus contribuciones no crean movimientos financieros. */
export interface SavingsGoal {
  id: string
  householdId: string
  name: string
  targetAmount: number
  currentAmount: number
  targetDate: string | null
  accountId: string | null
  icon: string
  color: string
  archived: boolean
  progressPct: number
  remaining: number
  isCompleted: boolean
}

export type ImportDateFormat = "DD/MM/YYYY" | "MM/DD/YYYY"
export type ImportDuplicateReason = "household" | "fingerprint" | "file"

export interface ImportMapping {
  date: string
  amount: string
  description: string
}

export interface ImportPreviewRow {
  sourcePosition: number
  date: string
  amount: number
  description: string | null
  duplicateReasons: ImportDuplicateReason[]
  selected: boolean
}

export interface ImportPreview {
  headers: string[]
  suggestedMapping: ImportMapping
  mapping: ImportMapping
  dateFormat: ImportDateFormat
  rows: ImportPreviewRow[]
}

export interface ImportBatch {
  id: string
  accountId: string
  sourceFilename: string
  mapping: ImportMapping
  selectedCount: number
  importedCount: number
  skippedCount: number
  createdAt: string
}

export interface ImportCommitResult {
  batch: ImportBatch
  selectedCount: number
  importedCount: number
  skippedCount: number
}

export interface ImportTransactionState {
  id: string
  type: TransactionType
  amount: number
  categoryId: string | null
  accountId: string
  date: string
  note: string | null
  deletedAt: string | null
  deleteReason: string | null
}

export interface TransactionEditEvent {
  id: string
  transactionId: string
  editedById: string
  beforeSnapshot: Record<string, unknown>
  afterSnapshot: Record<string, unknown>
  createdAt: string
}

export interface ImportRow {
  id: string
  sourcePosition: number
  sourceSnapshot: Record<string, unknown>
  transactionBaseline: Record<string, unknown>
  advisoryReasons: ImportDuplicateReason[]
  status: string
  transactionId: string | null
  currentTransaction: ImportTransactionState | null
  editEvents: TransactionEditEvent[]
}

export interface ImportBatchDetail extends ImportBatch {
  rows: ImportRow[]
  editEvents: TransactionEditEvent[]
}

export interface ImportRevertConflict {
  rowId: string
  transactionId: string
}

export interface ImportRevertConflictDetail {
  conflicts: ImportRevertConflict[]
}
