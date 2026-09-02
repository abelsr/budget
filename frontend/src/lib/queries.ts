import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { ApiError, apiFetch } from "@/lib/api"
import { useOffline, useOfflineTransactions } from "@/lib/offline"
import type {
  Account,
  Alert,
  Attachment,
  Budget,
  BudgetStatus,
  Category,
  Household,
  ImportBatch,
  ImportBatchDetail,
  ImportCommitResult,
  ImportDateFormat,
  ImportMapping,
  ImportPreview,
  Member,
  MerchantRule,
  NewTransaction,
  NewSplitTransaction,
  NewTransfer,
  Forecast,
  RecurringRule,
  ReconciliationDetail,
  ReconciliationSession,
  SavingsGoal,
  InstalmentPlan,
  Transaction,
} from "@/lib/types"

/**
 * Capa de datos: hooks de TanStack Query contra el backend FastAPI
 * (base `/api`, proxy de Vite en dev). Los query keys reflejan los
 * endpoints REST.
 */

export const keys = {
  accounts: ["accounts"] as const,
  alerts: ["alerts"] as const,
  categories: ["categories"] as const,
  members: ["members"] as const,
  transactions: ["transactions"] as const,
  summary: ["summary", "month"] as const,
  rangeSummary: ["summary", "range"] as const,
  forecast: ["forecast"] as const,
  household: ["household", "me"] as const,
  invitations: ["household", "invitations"] as const,
  recurringRules: ["recurring-rules"] as const,
  budgets: ["budgets"] as const,
  budgetsStatus: ["budgets", "status"] as const,
  goals: ["goals"] as const,
  importBatches: ["import", "batches"] as const,
  importBatch: (id: string) => ["import", "batches", id] as const,
  merchantRules: ["merchant-rules"] as const,
  instalmentPlans: ["instalment-plans"] as const,
  reconciliation: (accountId: string, id: string) => ["accounts", accountId, "reconciliations", id] as const,
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
  includeTransfers?: boolean
  from?: string
  to?: string
}

export interface Invitation {
  token: string
  /** Ruta relativa (`/login?invite=TOKEN`); el link absoluto se arma en la UI. */
  inviteUrl: string
  expiresAt: string
}

export interface ActiveInvitation {
  id: string
  createdAt: string
  expiresAt: string
}

/** Respuesta cruda del backend para un miembro (sin initials). */
interface MemberDto {
  id: string
  name: string
  email: string
  isOwner: boolean
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

export function useMerchantRules() {
  return useQuery({
    queryKey: keys.merchantRules,
    queryFn: () => apiFetch<MerchantRule[]>("/merchant-rules"),
  })
}

export function useCreateMerchantRule() {
  const invalidate = useInvalidator(keys.merchantRules)
  return useMutation({
    mutationFn: ({ pattern, categoryId }: { pattern: string; categoryId: string }) =>
      apiFetch<MerchantRule>("/merchant-rules", {
        method: "POST",
        body: JSON.stringify({ pattern, categoryId }),
      }),
    onSuccess: invalidate,
  })
}

export function useDeleteMerchantRule() {
  const invalidate = useInvalidator(keys.merchantRules)
  return useMutation({
    mutationFn: (id: string) => apiFetch<void>(`/merchant-rules/${id}`, { method: "DELETE" }),
    onSuccess: invalidate,
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
        email: m.email,
        isOwner: m.isOwner,
        initials: computeInitials(m.name),
      }))
    },
  })
}

export function useTransactions(filters: TransactionFilters = {}) {
  const search = new URLSearchParams({ limit: "200" })
  for (const [key, value] of Object.entries(filters)) {
    if (value) search.set(key, String(value))
  }
  const query = useQuery({
    queryKey: [...keys.transactions, filters],
    queryFn: () => apiFetch<Transaction[]>(`/transactions?${search}`),
  })
  const pending = useOfflineTransactions(filters)
  return { ...query, data: [...pending, ...(query.data ?? [])] }
}

/**
 * Issue #44: paginación "cargar más" para la lista de movimientos.
 *
 * El endpoint ya soporta `limit` (≤200) y `offset`. Cada página trae hasta
 * 200 filas; `getNextPageParam` decide que no hay más cuando el backend
 * devuelve menos de 200. Las transacciones offline pendientes se pre-pendean
 * al frente, igual que en `useTransactions`.
 */
export function useTransactionsPaged(filters: TransactionFilters = {}) {
  const query = useInfiniteQuery({
    queryKey: [...keys.transactions, "paged", filters],
    queryFn: ({ pageParam }) => {
      const search = new URLSearchParams({ limit: "200", offset: String(pageParam) })
      for (const [key, value] of Object.entries(filters)) {
        if (value) search.set(key, String(value))
      }
      return apiFetch<Transaction[]>(`/transactions?${search}`)
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage, pages) =>
      lastPage.length === 200 ? pages.reduce((sum, page) => sum + page.length, 0) : undefined,
  })
  const pending = useOfflineTransactions(filters)
  const serverRows = query.data?.pages.flat() ?? []
  return {
    ...query,
    data: [...pending, ...serverRows],
    hasMore: query.hasNextPage,
    loadMore: query.fetchNextPage,
    isFetchingNextPage: query.isFetchingNextPage,
  }
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

/** Cash-flow forecast (default horizon of 90 days). */
export function useForecast() {
  return useQuery({
    queryKey: keys.forecast,
    queryFn: () => apiFetch<Forecast>("/forecast"),
  })
}

export interface ImportPreviewInput {
  file: File
  accountId: string
  mapping?: ImportMapping
  dateFormat?: ImportDateFormat
}

export interface ImportCommitInput {
  file: File
  accountId: string
  mapping: ImportMapping
  dateFormat: ImportDateFormat
  selectedPositions: number[]
}

function importFormData(input: ImportPreviewInput | ImportCommitInput) {
  const formData = new FormData()
  formData.append("file", input.file)
  formData.append("accountId", input.accountId)
  if (input.mapping) formData.append("mapping", JSON.stringify(input.mapping))
  if (input.dateFormat) formData.append("dateFormat", input.dateFormat)
  if ("selectedPositions" in input) {
    formData.append("selectedPositions", JSON.stringify(input.selectedPositions))
  }
  return formData
}

function useImportInvalidator() {
  const queryClient = useQueryClient()
  return () => {
    queryClient.invalidateQueries({ queryKey: keys.transactions })
    queryClient.invalidateQueries({ queryKey: keys.accounts })
    queryClient.invalidateQueries({ queryKey: keys.summary })
    queryClient.invalidateQueries({ queryKey: keys.rangeSummary })
    queryClient.invalidateQueries({ queryKey: keys.forecast })
    queryClient.invalidateQueries({ queryKey: keys.budgets })
    queryClient.invalidateQueries({ queryKey: keys.budgetsStatus })
    queryClient.invalidateQueries({ queryKey: keys.importBatches })
  }
}

/** Previsualiza bytes locales; el archivo no se persiste hasta el commit. */
export function usePreviewImport() {
  return useMutation({
    mutationFn: (input: ImportPreviewInput) =>
      apiFetch<ImportPreview>("/import/preview", {
        method: "POST",
        body: importFormData(input),
      }),
  })
}

/** Vuelve a subir el mismo archivo para que el servidor lo reprocese al importar. */
export function useCommitImport() {
  const invalidate = useImportInvalidator()
  return useMutation({
    mutationFn: (input: ImportCommitInput) =>
      apiFetch<ImportCommitResult>("/import/commit", {
        method: "POST",
        body: importFormData(input),
      }),
    onSuccess: invalidate,
  })
}

export function useImportBatches() {
  return useQuery({
    queryKey: keys.importBatches,
    queryFn: () => apiFetch<ImportBatch[]>("/import/batches"),
  })
}

export function useImportBatch(id: string | null) {
  return useQuery({
    queryKey: keys.importBatch(id ?? "pending"),
    queryFn: () => apiFetch<ImportBatchDetail>(`/import/batches/${id}`),
    enabled: Boolean(id),
  })
}

export function useRevertImportBatch() {
  const invalidate = useImportInvalidator()
  return useMutation({
    mutationFn: (id: string) => apiFetch<ImportBatch>(`/import/${id}/revert`, { method: "POST" }),
    onSuccess: invalidate,
  })
}

export function useRestoreImportBatch() {
  const invalidate = useImportInvalidator()
  return useMutation({
    mutationFn: (id: string) => apiFetch<ImportBatch>(`/import/${id}/restore`, { method: "POST" }),
    onSuccess: invalidate,
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
  const invalidate = useInvalidator(keys.invitations)
  return useMutation({
    mutationFn: () =>
      apiFetch<Invitation>("/households/me/invitations", { method: "POST" }),
    onSuccess: invalidate,
  })
}

/** Las invitaciones activas solo son visibles para la persona propietaria. */
export function useActiveInvitations(isOwner: boolean, open: boolean) {
  const enabled = isOwner && open
  return useQuery({
    queryKey: keys.invitations,
    queryFn: () => apiFetch<ActiveInvitation[]>("/households/me/invitations"),
    enabled,
    refetchInterval: enabled ? 60_000 : false,
    refetchIntervalInBackground: true,
  })
}

export function useRevokeInvitation() {
  const invalidate = useInvalidator(keys.invitations)
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<void>(`/households/me/invitations/${id}`, { method: "DELETE" }),
    onSuccess: invalidate,
  })
}

export function useRemoveMember() {
  const invalidate = useInvalidator(keys.members, keys.household, keys.invitations)
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<void>(`/households/me/members/${id}`, { method: "DELETE" }),
    onSuccess: invalidate,
  })
}

export function useAddTransaction() {
  const queryClient = useQueryClient()
  const { queue } = useOffline()
  return useMutation({
    mutationFn: async (input: (NewTransaction | NewTransfer | NewSplitTransaction) & { offlineEligible?: boolean }) => {
      const { offlineEligible = true, ...payload } = input
      const offlinePayload = { ...payload, clientId: crypto.randomUUID() }
      if (!("repeat" in payload && payload.repeat) && offlineEligible && !navigator.onLine) return queue(offlinePayload as Parameters<typeof queue>[0])
      try {
        return await apiFetch<Transaction>("/transactions", {
          method: "POST",
          body: JSON.stringify(offlinePayload),
        })
      } catch (error) {
        // Error de red (no ApiError) o 5xx del servidor → transitorio: se
        // encola offline (issue #35 punto 2). Los 4xx son definitivos y se
        // relanzan al usuario.
        const transient = error instanceof ApiError ? error.status >= 500 : true
        if (!("repeat" in payload && payload.repeat) && offlineEligible && transient) return queue(offlinePayload as Parameters<typeof queue>[0])
        throw error
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: keys.transactions })
      queryClient.invalidateQueries({ queryKey: keys.accounts })
      queryClient.invalidateQueries({ queryKey: keys.summary })
      queryClient.invalidateQueries({ queryKey: keys.budgetsStatus })
      queryClient.invalidateQueries({ queryKey: keys.rangeSummary })
      queryClient.invalidateQueries({ queryKey: keys.forecast })
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
  isPersonal?: boolean
  statementDay?: number | null
  paymentDueDays?: number | null
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
  const invalidate = useInvalidator(keys.accounts, keys.forecast)
  return useMutation({
    mutationFn: (input: AccountInput) =>
      apiFetch<Account>("/accounts", { method: "POST", body: JSON.stringify(input) }),
    onSuccess: invalidate,
  })
}

export function useUpdateAccount() {
  const invalidate = useInvalidator(keys.accounts, keys.forecast)
  return useMutation({
    mutationFn: ({ id, ...input }: Partial<AccountInput> & { id: string }) =>
      apiFetch<Account>(`/accounts/${id}`, { method: "PATCH", body: JSON.stringify(input) }),
    onSuccess: invalidate,
  })
}

export function useDeleteAccount() {
  const invalidate = useInvalidator(keys.accounts, keys.forecast)
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
    keys.rangeSummary,
    keys.forecast,
  )
  return useMutation({
    mutationFn: ({ id, ...input }: { id: string } & Record<string, unknown>) =>
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
    keys.rangeSummary,
    keys.forecast,
  )
  return useMutation({
    mutationFn: (id: string) => apiFetch<void>(`/transactions/${id}`, { method: "DELETE" }),
    onSuccess: invalidate,
  })
}

export function useRestoreTransaction() {
  const invalidate = useInvalidator(
    keys.transactions,
    keys.accounts,
    keys.summary,
    keys.budgetsStatus,
    keys.rangeSummary,
    keys.forecast,
  )
  return useMutation({
    mutationFn: (id: string) => apiFetch<Transaction>(`/transactions/${id}/restore`, { method: "POST" }),
    onSuccess: invalidate,
  })
}

export function useCreateReconciliation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ accountId, statementDate, statementBalance }: { accountId: string; statementDate: string; statementBalance: number }) =>
      apiFetch<ReconciliationSession>(`/accounts/${accountId}/reconciliations`, {
        method: "POST", body: JSON.stringify({ statementDate, statementBalance }),
      }),
    onSuccess: (session) => queryClient.invalidateQueries({ queryKey: keys.reconciliation(session.accountId, session.id) }),
  })
}

export function useReconciliation(accountId: string | null, id: string | null) {
  return useQuery({
    queryKey: keys.reconciliation(accountId ?? "pending", id ?? "pending"),
    queryFn: () => apiFetch<ReconciliationDetail>(`/accounts/${accountId}/reconciliations/${id}`),
    enabled: Boolean(accountId && id),
  })
}

export function useToggleReconciliation() {
  return useMutation({
    mutationFn: ({ transactionId, reconciled }: { transactionId: string; reconciled: boolean }) =>
      apiFetch(`/transactions/${transactionId}/reconciliation`, { method: "POST", body: JSON.stringify({ reconciled }) }),
  })
}

export function useCompleteReconciliation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ accountId, id }: { accountId: string; id: string }) =>
      apiFetch<ReconciliationSession>(`/accounts/${accountId}/reconciliations/${id}/complete`, { method: "POST" }),
    onSuccess: (session) => {
      queryClient.invalidateQueries({ queryKey: keys.reconciliation(session.accountId, session.id) })
      queryClient.invalidateQueries({ queryKey: keys.transactions })
    },
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
    keys.forecast,
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
    keys.forecast,
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
// Alertas
// ---------------------------------------------------------------------------

export function useAlerts() {
  return useQuery({
    queryKey: keys.alerts,
    queryFn: () => apiFetch<Alert[]>("/alerts"),
    refetchInterval: 60_000,
  })
}

export function useReadAlerts() {
  const invalidate = useInvalidator(keys.alerts)
  return useMutation({
    mutationFn: (alertId?: string) => apiFetch<void>("/alerts/read", {
      method: "POST",
      body: JSON.stringify(alertId ? { alertId } : {}),
    }),
    onSuccess: invalidate,
  })
}

export function useGenerateAlertRecurring() {
  const invalidate = useInvalidator(
    keys.alerts,
    keys.recurringRules,
    keys.transactions,
    keys.accounts,
    keys.summary,
    keys.budgetsStatus,
  )
  return useMutation({
    mutationFn: (id: string) => apiFetch<{ generated: number }>(`/alerts/${id}/generate`, { method: "POST" }),
    onSuccess: invalidate,
  })
}

// ---------------------------------------------------------------------------
// Presupuestos
// ---------------------------------------------------------------------------

export interface BudgetInput {
  categoryId: string
  amount: number
  month?: string | null
  rollover?: boolean
}

export function useBudgets() {
  return useQuery({
    queryKey: keys.budgets,
    queryFn: () => apiFetch<Budget[]>("/budgets"),
  })
}

export function useBudgetsStatus(month?: string) {
  return useQuery({
    queryKey: [...keys.budgetsStatus, month],
    queryFn: () =>
      apiFetch<BudgetStatus[]>(`/budgets/status${month ? `?month=${month}` : ""}`),
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
    mutationFn: ({ id, amount, rollover }: { id: string; amount: number; rollover: boolean }) =>
      apiFetch<Budget>(`/budgets/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ amount, rollover }),
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

// ---------------------------------------------------------------------------
// Metas de ahorro
// ---------------------------------------------------------------------------

export interface SavingsGoalInput {
  name: string
  targetAmount: number
  currentAmount?: number
  targetDate?: string | null
  accountId?: string | null
  icon: string
  color: string
  planPaused?: boolean
}

export function useGoals() {
  return useQuery({
    queryKey: keys.goals,
    queryFn: () => apiFetch<SavingsGoal[]>("/goals"),
  })
}

export function useCreateGoal() {
  const invalidate = useInvalidator(keys.goals)
  return useMutation({
    mutationFn: (input: SavingsGoalInput) =>
      apiFetch<SavingsGoal>("/goals", { method: "POST", body: JSON.stringify(input) }),
    onSuccess: invalidate,
  })
}

export function useUpdateGoal() {
  const invalidate = useInvalidator(keys.goals)
  return useMutation({
    mutationFn: ({ id, ...input }: Partial<SavingsGoalInput & { archived: boolean }> & { id: string }) =>
      apiFetch<SavingsGoal>(`/goals/${id}`, { method: "PATCH", body: JSON.stringify(input) }),
    onSuccess: invalidate,
  })
}

export function useContributeToGoal() {
  const invalidate = useInvalidator(keys.goals)
  return useMutation({
    mutationFn: ({ id, amount }: { id: string; amount: number }) =>
      apiFetch<SavingsGoal>(`/goals/${id}/contribute`, {
        method: "POST",
        body: JSON.stringify({ amount }),
      }),
    onSuccess: invalidate,
  })
}

export function useDeleteGoal() {
  const invalidate = useInvalidator(keys.goals)
  return useMutation({
    mutationFn: (id: string) => apiFetch<void>(`/goals/${id}`, { method: "DELETE" }),
    onSuccess: invalidate,
  })
}


// ---------- Instalment plans (MSI) ----------

export function useInstalmentPlans(sourceTransactionId?: string) {
  return useQuery({
    queryKey: sourceTransactionId
      ? [keys.instalmentPlans, "by-transaction", sourceTransactionId]
      : keys.instalmentPlans,
    queryFn: () =>
      apiFetch<InstalmentPlan[]>(
        sourceTransactionId
          ? `/instalment-plans?sourceTransactionId=${encodeURIComponent(sourceTransactionId)}`
          : "/instalment-plans",
      ),
  })
}

export function useInstalmentPlan(id: string | undefined) {
  return useQuery({
    queryKey: ["instalment-plans", id] as const,
    enabled: !!id,
    queryFn: () => apiFetch<InstalmentPlan>(`/instalment-plans/${id}`),
  })
}

function useInstalmentInvalidate() {
  // Plans never move balances by themselves, but "record payment now"
  // creates a transfer, so accounts, transactions and the forecast
  // (which lists instalment due dates) are invalidated as well.
  return useInvalidator(
    keys.instalmentPlans,
    keys.accounts,
    keys.transactions,
    keys.forecast,
    keys.alerts,
    keys.summary,
  )
}

export function useCreateInstalmentPlan() {
  const invalidate = useInstalmentInvalidate()
  return useMutation({
    mutationFn: (input: { sourceTransactionId: string; months: number; firstDueDate: string }) =>
      apiFetch<InstalmentPlan>("/instalment-plans", { method: "POST", body: JSON.stringify(input) }),
    onSuccess: invalidate,
  })
}

export function usePayInstalmentPlan() {
  const invalidate = useInstalmentInvalidate()
  return useMutation({
    mutationFn: ({ id, sourceAccountId, date }: { id: string; sourceAccountId?: string; date?: string }) =>
      apiFetch<InstalmentPlan>(`/instalment-plans/${id}/pay`, {
        method: "POST",
        body: JSON.stringify({ sourceAccountId: sourceAccountId ?? null, date: date ?? null }),
      }),
    onSuccess: invalidate,
  })
}

export function usePauseInstalmentPlan() {
  const invalidate = useInstalmentInvalidate()
  return useMutation({
    mutationFn: (id: string) => apiFetch<InstalmentPlan>(`/instalment-plans/${id}/pause`, { method: "POST" }),
    onSuccess: invalidate,
  })
}

export function useResumeInstalmentPlan() {
  const invalidate = useInstalmentInvalidate()
  return useMutation({
    mutationFn: (id: string) => apiFetch<InstalmentPlan>(`/instalment-plans/${id}/resume`, { method: "POST" }),
    onSuccess: invalidate,
  })
}

export function useCancelInstalmentPlan() {
  const invalidate = useInstalmentInvalidate()
  return useMutation({
    mutationFn: (id: string) => apiFetch<void>(`/instalment-plans/${id}`, { method: "DELETE" }),
    onSuccess: invalidate,
  })
}
