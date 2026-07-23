/**
 * Tipos del dominio — espejo del futuro esquema PostgreSQL.
 * Todas las entidades pertenecen a un hogar (multi-tenant desde el día 1).
 */

export type TransactionType = "expense" | "income"

export type AccountKind = "cash" | "debit" | "credit" | "savings"

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
}

export interface NewTransaction {
  type: TransactionType
  amount: number
  categoryId: string
  accountId: string
  date: string
  note?: string
}
