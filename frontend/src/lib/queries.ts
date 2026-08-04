import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { apiFetch } from "@/lib/api"
import type {
  Account,
  Attachment,
  Budget,
  BudgetStatus,
  Category,
  Member,
  NewTransaction,
  RecurringRule,
  Transaction,
} from "@/lib/types"

/**
 * Capa de datos: hooks de TanStack Query contra el backend FastAPI
 * (base `/api`, proxy de Vite en dev). Los query keys reflejan los
 * endpoints REST.
 */

export const keys = {
  accounts: ["accounts"] as const,
  categories: ["categories"] as const,
  members: ["members"] as const,
  transactions: ["transactions"] as const,
  summary: ["summary", "month"] as const,
  rangeSummary: ["summary", "range"] as const,
  household: ["household", "me"] as const,
  recurringRules: ["recurring-rules"] as const,
  budgets: ["budgets"] as const,
  budgetsStatus: ["budgets", "status"] as const,
}

export interface MonthSummary {
  income: number
  expense: number
  byCategory: { categoryId: string; total: number }[]
}

export interface RangeSummary {
  monthly: { month: string; income: number; expense: number; net: number }[]
  byCategory: { categoryId: string; total: number }[]
}

export interface TransactionFilters {
  q?: string
  categoryId?: string
  accountId?: string
  memberId?: string
  type?: Transaction["type"]
  from?: string
  to?: string
}

export interface Household {
  id: string
  name: string
  currencyCode: string
}

export interface Invitation {
  token: string
  /** Ruta relativa (`/login?invite=TOKEN`); el link absoluto se arma en la UI. */
  inviteUrl: string
  expiresAt: string
}

/** Respuesta cruda del backend para un miembro (sin initials). */
interface MemberDto {
  id: string
  name: string
  email: string
}

/** Primera letra de las dos primeras palabras, en mayúsculas. */
function computeInitials(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean)
  return words
    .slice(0, 2)
    .map((w) => w[0]!.toUpperCase())
    .join("")
}

export function useAccounts() {
  return useQuery({
    queryKey: keys.accounts,
    queryFn: () => apiFetch<Account[]>("/accounts"),
  })
}

export function useCategories() {
  return useQuery({
    queryKey: keys.categories,
    queryFn: () => apiFetch<Category[]>("/categories"),
  })
}

export function useMembers() {
  return useQuery({
    queryKey: keys.members,
    queryFn: async (): Promise<Member[]> => {
      const dtos = await apiFetch<MemberDto[]>("/households/me/members")
      return dtos.map((m) => ({
        id: m.id,
        name: m.name,
        initials: computeInitials(m.name),
      }))
    },
  })
}

export function useTransactions(filters: TransactionFilters = {}) {
  const search = new URLSearchParams({ limit: "200" })
  for (const [key, value] of Object.entries(filters)) {
    if (value) search.set(key, value)
  }
  return useQuery({
    queryKey: [...keys.transactions, filters],
    queryFn: () => apiFetch<Transaction[]>(`/transactions?${search}`),
  })
}

export function useMonthSummary() {
  return useQuery({
    queryKey: keys.summary,
    queryFn: () => apiFetch<MonthSummary>("/summary/month"),
  })
}

export function useRangeSummary(from: string, to: string) {
  return useQuery({
    queryKey: [...keys.rangeSummary, from, to],
    queryFn: () => apiFetch<RangeSummary>(`/summary/range?from=${from}&to=${to}`),
    enabled: Boolean(from && to),
  })
}

export function useHousehold() {
  return useQuery({
    queryKey: keys.household,
    queryFn: () => apiFetch<Household>("/households/me"),
  })
}

/** Crea un link de invitación al hogar (válido 7 días, un solo uso). */
export function useCreateInvitation() {
  return useMutation({
    mutationFn: () =>
      apiFetch<Invitation>("/households/me/invitations", { method: "POST" }),
  })
}

export function useAddTransaction() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: NewTransaction) =>
      apiFetch<Transaction>("/transactions", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: keys.transactions })
      queryClient.invalidateQueries({ queryKey: keys.accounts })
      queryClient.invalidateQueries({ queryKey: keys.summary })
      queryClient.invalidateQueries({ queryKey: keys.budgetsStatus })
      // Con `repeat` el backend crea también la regla
      queryClient.invalidateQueries({ queryKey: keys.recurringRules })
    },
  })
}

export function useUploadAttachment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      transactionId,
      file,
    }: {
      transactionId: string
      file: File
    }) => {
      const formData = new FormData()
      formData.append("file", file)
      return apiFetch<Attachment>(`/transactions/${transactionId}/attachments`, {
        method: "POST",
        body: formData,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: keys.transactions })
    },
  })
}

// ---------------------------------------------------------------------------
// Mutaciones CRUD (cuentas, categorías, transacciones)
// ---------------------------------------------------------------------------

export interface AccountInput {
  name: string
  kind: Account["kind"]
  openingBalance?: number
  bank?: string | null
  cardBrand?: Account["cardBrand"]
  lastFour?: string | null
}

export interface CategoryInput {
  name: string
  icon: string
  color: string
  type: Category["type"]
}

function useInvalidator(...queryKeys: readonly (readonly string[])[]) {
  const queryClient = useQueryClient()
  return () => queryKeys.forEach((key) => queryClient.invalidateQueries({ queryKey: key }))
}

export function useCreateAccount() {
  const invalidate = useInvalidator(keys.accounts)
  return useMutation({
    mutationFn: (input: AccountInput) =>
      apiFetch<Account>("/accounts", { method: "POST", body: JSON.stringify(input) }),
    onSuccess: invalidate,
  })
}

export function useUpdateAccount() {
  const invalidate = useInvalidator(keys.accounts)
  return useMutation({
    mutationFn: ({ id, ...input }: Partial<AccountInput> & { id: string }) =>
      apiFetch<Account>(`/accounts/${id}`, { method: "PATCH", body: JSON.stringify(input) }),
    onSuccess: invalidate,
  })
}

export function useDeleteAccount() {
  const invalidate = useInvalidator(keys.accounts)
  return useMutation({
    mutationFn: (id: string) => apiFetch<void>(`/accounts/${id}`, { method: "DELETE" }),
    onSuccess: invalidate,
  })
}

export function useCreateCategory() {
  const invalidate = useInvalidator(keys.categories)
  return useMutation({
    mutationFn: (input: CategoryInput) =>
      apiFetch<Category>("/categories", { method: "POST", body: JSON.stringify(input) }),
    onSuccess: invalidate,
  })
}

export function useUpdateCategory() {
  const invalidate = useInvalidator(keys.categories)
  return useMutation({
    mutationFn: ({ id, ...input }: Partial<CategoryInput & { active: boolean }> & { id: string }) =>
      apiFetch<Category>(`/categories/${id}`, { method: "PATCH", body: JSON.stringify(input) }),
    onSuccess: invalidate,
  })
}

export function useDeleteCategory() {
  const invalidate = useInvalidator(keys.categories)
  return useMutation({
    mutationFn: (id: string) => apiFetch<void>(`/categories/${id}`, { method: "DELETE" }),
    onSuccess: invalidate,
  })
}

export function useUpdateTransaction() {
  const invalidate = useInvalidator(
    keys.transactions,
    keys.accounts,
    keys.summary,
    keys.budgetsStatus,
  )
  return useMutation({
    mutationFn: ({ id, ...input }: Partial<NewTransaction> & { id: string }) =>
      apiFetch<Transaction>(`/transactions/${id}`, { method: "PATCH", body: JSON.stringify(input) }),
    onSuccess: invalidate,
  })
}

export function useDeleteTransaction() {
  const invalidate = useInvalidator(
    keys.transactions,
    keys.accounts,
    keys.summary,
    keys.budgetsStatus,
  )
  return useMutation({
    mutationFn: (id: string) => apiFetch<void>(`/transactions/${id}`, { method: "DELETE" }),
    onSuccess: invalidate,
  })
}

// ---------------------------------------------------------------------------
// Reglas recurrentes
// ---------------------------------------------------------------------------

/**
 * Lista las reglas del hogar. Ojo: el GET materializa las transacciones
 * pendientes en el backend, así que puede cambiar saldos y movimientos.
 */
export function useRecurringRules() {
  return useQuery({
    queryKey: keys.recurringRules,
    queryFn: () => apiFetch<RecurringRule[]>("/recurring-rules"),
  })
}

/**
 * Pausar/reanudar o corregir monto y nota. Reanudar mueve `nextRunDate` hacia
 * adelante en el backend, y borrar/pausar cambia lo que se materializa: de ahí
 * que también se invaliden movimientos, saldos y resumen.
 */
export function useUpdateRecurringRule() {
  const invalidate = useInvalidator(
    keys.recurringRules,
    keys.transactions,
    keys.accounts,
    keys.summary,
  )
  return useMutation({
    mutationFn: ({
      id,
      ...input
    }: Partial<Pick<RecurringRule, "amount" | "note" | "active">> & {
      id: string
    }) =>
      apiFetch<RecurringRule>(`/recurring-rules/${id}`, {
        method: "PATCH",
        body: JSON.stringify(input),
      }),
    onSuccess: invalidate,
  })
}

/** Borra la regla. Las transacciones ya generadas se quedan, sin el badge. */
export function useDeleteRecurringRule() {
  const invalidate = useInvalidator(
    keys.recurringRules,
    keys.transactions,
    keys.accounts,
    keys.summary,
  )
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<void>(`/recurring-rules/${id}`, { method: "DELETE" }),
    onSuccess: invalidate,
  })
}

export function useDeleteAttachment() {
  const invalidate = useInvalidator(keys.transactions)
  return useMutation({
    mutationFn: (id: string) => apiFetch<void>(`/attachments/${id}`, { method: "DELETE" }),
    onSuccess: invalidate,
  })
}

// ---------------------------------------------------------------------------
// Presupuestos
// ---------------------------------------------------------------------------

export interface BudgetInput {
  categoryId: string
  amount: number
}

export function useBudgets() {
  return useQuery({
    queryKey: keys.budgets,
    queryFn: () => apiFetch<Budget[]>("/budgets"),
  })
}

export function useBudgetsStatus() {
  return useQuery({
    queryKey: keys.budgetsStatus,
    queryFn: () => apiFetch<BudgetStatus[]>("/budgets/status"),
  })
}

export function useCreateBudget() {
  const invalidate = useInvalidator(keys.budgets, keys.budgetsStatus)
  return useMutation({
    mutationFn: (input: BudgetInput) =>
      apiFetch<Budget>("/budgets", { method: "POST", body: JSON.stringify(input) }),
    onSuccess: invalidate,
  })
}

export function useUpdateBudget() {
  const invalidate = useInvalidator(keys.budgets, keys.budgetsStatus)
  return useMutation({
    mutationFn: ({ id, amount }: { id: string; amount: number }) =>
      apiFetch<Budget>(`/budgets/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ amount }),
      }),
    onSuccess: invalidate,
  })
}

export function useDeleteBudget() {
  const invalidate = useInvalidator(keys.budgets, keys.budgetsStatus)
  return useMutation({
    mutationFn: (id: string) => apiFetch<void>(`/budgets/${id}`, { method: "DELETE" }),
    onSuccess: invalidate,
  })
}
