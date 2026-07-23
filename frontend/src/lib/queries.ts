import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import {
  accounts,
  addTransaction,
  categories,
  getMonthSummary,
  members,
  transactions,
} from "@/lib/mock-db"
import type { NewTransaction } from "@/lib/types"

/**
 * Capa de datos. Hoy habla con el mock en memoria; cuando exista el
 * backend FastAPI, solo cambian estas funciones por llamadas `fetch`.
 * Los query keys ya están pensados como endpoints REST.
 */

export const keys = {
  accounts: ["accounts"] as const,
  categories: ["categories"] as const,
  members: ["members"] as const,
  transactions: ["transactions"] as const,
  summary: ["summary", "month"] as const,
}

export function useAccounts() {
  return useQuery({ queryKey: keys.accounts, queryFn: () => [...accounts] })
}

export function useCategories() {
  return useQuery({ queryKey: keys.categories, queryFn: () => [...categories] })
}

export function useMembers() {
  return useQuery({ queryKey: keys.members, queryFn: () => [...members] })
}

export function useTransactions() {
  return useQuery({
    queryKey: keys.transactions,
    queryFn: () => [...transactions],
  })
}

export function useMonthSummary() {
  return useQuery({ queryKey: keys.summary, queryFn: () => getMonthSummary() })
}

export function useAddTransaction() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: NewTransaction) => Promise.resolve(addTransaction(input)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: keys.transactions })
      queryClient.invalidateQueries({ queryKey: keys.accounts })
      queryClient.invalidateQueries({ queryKey: keys.summary })
    },
  })
}
