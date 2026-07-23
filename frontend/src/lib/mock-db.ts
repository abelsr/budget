import { toISODate } from "@/lib/format"
import type {
  Account,
  Category,
  Member,
  NewTransaction,
  Transaction,
} from "@/lib/types"

/**
 * Base de datos mock en memoria. Imita la forma de la futura API REST:
 * la capa de queries (TanStack Query) solo habla con estas funciones,
 * así reemplazarlas por `fetch` al backend será un cambio localizado.
 */

const HOUSEHOLD_ID = "hh-1"

export const members: Member[] = [
  { id: "m-1", name: "Abel", initials: "AB" },
  { id: "m-2", name: "Mariana", initials: "MA" },
]

export const accounts: Account[] = [
  { id: "a-1", householdId: HOUSEHOLD_ID, name: "Efectivo", kind: "cash", balance: 3250 },
  { id: "a-2", householdId: HOUSEHOLD_ID, name: "Débito BBVA", kind: "debit", balance: 24890.5 },
  { id: "a-3", householdId: HOUSEHOLD_ID, name: "Crédito Nu", kind: "credit", balance: -4120.75 },
  { id: "a-4", householdId: HOUSEHOLD_ID, name: "Ahorro", kind: "savings", balance: 58300 },
]

export const categories: Category[] = [
  { id: "c-1", householdId: HOUSEHOLD_ID, name: "Supermercado", icon: "shopping-cart", color: "#30b0c7", type: "expense", active: true },
  { id: "c-2", householdId: HOUSEHOLD_ID, name: "Comida fuera", icon: "utensils", color: "#ff9f0a", type: "expense", active: true },
  { id: "c-3", householdId: HOUSEHOLD_ID, name: "Transporte", icon: "car", color: "#0a84ff", type: "expense", active: true },
  { id: "c-4", householdId: HOUSEHOLD_ID, name: "Vivienda", icon: "house", color: "#bf5af2", type: "expense", active: true },
  { id: "c-5", householdId: HOUSEHOLD_ID, name: "Servicios", icon: "zap", color: "#ffd60a", type: "expense", active: true },
  { id: "c-6", householdId: HOUSEHOLD_ID, name: "Salud", icon: "heart-pulse", color: "#ff375f", type: "expense", active: true },
  { id: "c-7", householdId: HOUSEHOLD_ID, name: "Ocio", icon: "gamepad-2", color: "#ff6482", type: "expense", active: true },
  { id: "c-8", householdId: HOUSEHOLD_ID, name: "Suscripciones", icon: "repeat", color: "#ac8e68", type: "expense", active: true },
  { id: "c-9", householdId: HOUSEHOLD_ID, name: "Sueldo", icon: "banknote", color: "#30d158", type: "income", active: true },
  { id: "c-10", householdId: HOUSEHOLD_ID, name: "Otros ingresos", icon: "hand-coins", color: "#64d2ff", type: "income", active: true },
]

function daysAgo(n: number): string {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return toISODate(d)
}

let seq = 0
function tx(partial: Omit<Transaction, "id" | "householdId">): Transaction {
  seq += 1
  return { id: `t-${seq}`, householdId: HOUSEHOLD_ID, ...partial }
}

export const transactions: Transaction[] = [
  tx({ type: "expense", amount: 847.2, categoryId: "c-1", accountId: "a-2", memberId: "m-1", date: daysAgo(0), note: "Súper de la semana" }),
  tx({ type: "expense", amount: 320, categoryId: "c-2", accountId: "a-3", memberId: "m-2", date: daysAgo(0), note: "Tacos con amigos" }),
  tx({ type: "expense", amount: 280, categoryId: "c-3", accountId: "a-1", memberId: "m-1", date: daysAgo(1), note: "Gasolina" }),
  tx({ type: "expense", amount: 199, categoryId: "c-8", accountId: "a-3", memberId: "m-1", date: daysAgo(1), note: "Netflix" }),
  tx({ type: "expense", amount: 1450, categoryId: "c-1", accountId: "a-2", memberId: "m-2", date: daysAgo(2), note: "Costco" }),
  tx({ type: "expense", amount: 620, categoryId: "c-5", accountId: "a-2", memberId: "m-1", date: daysAgo(3), note: "Luz" }),
  tx({ type: "expense", amount: 189.5, categoryId: "c-2", accountId: "a-1", memberId: "m-2", date: daysAgo(3) }),
  tx({ type: "income", amount: 18500, categoryId: "c-9", accountId: "a-2", memberId: "m-1", date: daysAgo(4), note: "Quincena Abel" }),
  tx({ type: "expense", amount: 480, categoryId: "c-6", accountId: "a-2", memberId: "m-2", date: daysAgo(5), note: "Farmacia" }),
  tx({ type: "expense", amount: 9500, categoryId: "c-4", accountId: "a-2", memberId: "m-1", date: daysAgo(6), note: "Renta" }),
  tx({ type: "expense", amount: 356.8, categoryId: "c-1", accountId: "a-1", memberId: "m-2", date: daysAgo(6) }),
  tx({ type: "expense", amount: 760, categoryId: "c-7", accountId: "a-3", memberId: "m-1", date: daysAgo(7), note: "Cine y cena" }),
  tx({ type: "income", amount: 17200, categoryId: "c-9", accountId: "a-2", memberId: "m-2", date: daysAgo(8), note: "Quincena Mariana" }),
  tx({ type: "expense", amount: 420, categoryId: "c-3", accountId: "a-2", memberId: "m-2", date: daysAgo(9), note: "Uber" }),
  tx({ type: "expense", amount: 1290, categoryId: "c-1", accountId: "a-2", memberId: "m-1", date: daysAgo(10) }),
  tx({ type: "expense", amount: 550, categoryId: "c-5", accountId: "a-2", memberId: "m-1", date: daysAgo(11), note: "Internet" }),
  tx({ type: "income", amount: 1500, categoryId: "c-10", accountId: "a-1", memberId: "m-2", date: daysAgo(12), note: "Venta de mueble" }),
]

// ---- "API" mock ----

export function addTransaction(input: NewTransaction, memberId = "m-1"): Transaction {
  const created = tx({
    ...input,
    memberId,
  })
  transactions.unshift(created)
  const account = accounts.find((a) => a.id === input.accountId)
  if (account) {
    account.balance += input.type === "income" ? input.amount : -input.amount
  }
  return created
}

export interface MonthSummary {
  income: number
  expense: number
  byCategory: { categoryId: string; total: number }[]
}

export function getMonthSummary(): MonthSummary {
  const now = new Date()
  const prefix = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`
  const monthTx = transactions.filter((t) => t.date.startsWith(prefix))
  const byCategory = new Map<string, number>()
  let income = 0
  let expense = 0
  for (const t of monthTx) {
    if (t.type === "income") income += t.amount
    else {
      expense += t.amount
      byCategory.set(t.categoryId, (byCategory.get(t.categoryId) ?? 0) + t.amount)
    }
  }
  return {
    income,
    expense,
    byCategory: [...byCategory.entries()]
      .map(([categoryId, total]) => ({ categoryId, total }))
      .sort((a, b) => b.total - a.total),
  }
}
