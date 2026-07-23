import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { apiFetch } from "@/lib/api"
import type {
  Account,
  Category,
  Member,
  NewTransaction,
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
  household: ["household", "me"] as const,
}

export interface MonthSummary {
  income: number
  expense: number
  byCategory: { categoryId: string; total: number }[]
}

export interface Household {
  id: string
  name: string
  currencyCode: string
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

export function useTransactions() {
  return useQuery({
    queryKey: keys.transactions,
    queryFn: () => apiFetch<Transaction[]>("/transactions?limit=200"),
  })
}

export function useMonthSummary() {
  return useQuery({
    queryKey: keys.summary,
    queryFn: () => apiFetch<MonthSummary>("/summary/month"),
  })
}

export function useHousehold() {
  return useQuery({
    queryKey: keys.household,
    queryFn: () => apiFetch<Household>("/households/me"),
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
    },
  })
}
