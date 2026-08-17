import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react"
import { openDB } from "idb"
import { useQueryClient } from "@tanstack/react-query"

import { ApiError, apiFetch, getToken } from "@/lib/api"
import { useAuth } from "@/lib/auth"
import type { NewTransaction, NewTransfer, Transaction } from "@/lib/types"

type SimpleTransaction = (Omit<NewTransaction, "repeat"> | NewTransfer) & { clientId: string }

export type PendingTransaction = {
  clientId: string
  userId: string
  payload: SimpleTransaction
  createdAt: number
  attempts: number
  lastError?: string
}

type OfflineState = {
  online: boolean
  pending: PendingTransaction[]
  queue: (input: SimpleTransaction) => Promise<Transaction>
  flush: () => Promise<void>
  discard: (clientId: string) => Promise<void>
  cacheUpdatedAt: number
}

const OfflineContext = createContext<OfflineState | null>(null)
const DB_NAME = "budget-offline"
const STORE = "pending_transactions"

const dbPromise = openDB(DB_NAME, 1, {
  upgrade(db) {
    const store = db.createObjectStore(STORE, { keyPath: "clientId" })
    store.createIndex("createdAt", "createdAt")
  },
})

async function readPending(): Promise<PendingTransaction[]> {
  const db = await dbPromise
  return (await db.getAllFromIndex(STORE, "createdAt")) as PendingTransaction[]
}

function pendingAsTransaction(entry: PendingTransaction): Transaction {
  return {
    id: `pending:${entry.clientId}`,
    clientId: entry.clientId,
    householdId: "",
    type: entry.payload.type,
    amount: entry.payload.amount,
    categoryId: "categoryId" in entry.payload ? entry.payload.categoryId : null,
    accountId: "accountId" in entry.payload ? entry.payload.accountId : entry.payload.sourceAccountId,
    memberId: "",
    date: entry.payload.date,
    note: entry.payload.note,
    transferDirection: entry.payload.type === "transfer" ? "outflow" : null,
    counterpartyAccountId: entry.payload.type === "transfer" ? entry.payload.destinationAccountId : null,
    reconciliationStatus: "pending",
    isSplit: false,
    splits: [],
    attachments: [],
    syncStatus: entry.lastError ? "failed" : "pending",
    syncError: entry.lastError,
  }
}

function isMatchingFilter(entry: PendingTransaction, filters: Record<string, string | undefined>) {
  const { payload } = entry
  if (filters.type && payload.type !== filters.type) return false
  if (filters.categoryId && (!("categoryId" in payload) || payload.categoryId !== filters.categoryId)) return false
  if (filters.accountId && (("accountId" in payload ? payload.accountId : payload.sourceAccountId) !== filters.accountId)) return false
  if (filters.memberId) return false
  if (filters.from && payload.date < filters.from) return false
  if (filters.to && payload.date > filters.to) return false
  if (filters.q && !payload.note?.toLocaleLowerCase().includes(filters.q.toLocaleLowerCase())) return false
  return true
}

export function useOfflineTransactions(filters: Partial<Record<"q" | "categoryId" | "accountId" | "memberId" | "type" | "from" | "to", string | undefined>> = {}) {
  const { pending } = useOffline()
  return pending.filter((entry) => isMatchingFilter(entry, filters)).map(pendingAsTransaction)
}

export function OfflineProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient()
  const { session } = useAuth()
  const userIdRef = useRef(session?.id)
  userIdRef.current = session?.id
  const [online, setOnline] = useState(() => navigator.onLine)
  const [pending, setPending] = useState<PendingTransaction[]>([])
  const [cacheUpdatedAt, setCacheUpdatedAt] = useState(0)

  const refreshPending = useCallback(async () => {
    const userId = userIdRef.current
    setPending(userId ? (await readPending()).filter((entry) => entry.userId === userId) : [])
  }, [])

  const refreshCacheAge = useCallback(() => {
    setCacheUpdatedAt(Math.max(0, ...queryClient.getQueryCache().getAll().map((query) => query.state.dataUpdatedAt)))
  }, [queryClient])

  const flush = useCallback(async () => {
    const userId = userIdRef.current
    const token = getToken()
    if (!navigator.onLine || !userId || !token) return
    for (const entry of await readPending()) {
      // Never submit an old user's mutation with a replacement token.
      if (userIdRef.current !== userId || getToken() !== token) return
      if (entry.userId !== userId) continue
      if (entry.lastError) continue
      try {
        await apiFetch<Transaction>("/transactions", {
          method: "POST",
          body: JSON.stringify(entry.payload),
        })
        if (userIdRef.current !== userId || getToken() !== token) return
        const db = await dbPromise
        await db.delete(STORE, entry.clientId)
        queryClient.invalidateQueries({ queryKey: ["transactions"] })
        queryClient.invalidateQueries({ queryKey: ["accounts"] })
        queryClient.invalidateQueries({ queryKey: ["summary"] })
        queryClient.invalidateQueries({ queryKey: ["budgets", "status"] })
      } catch (error) {
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
          const db = await dbPromise
          await db.put(STORE, {
            ...entry,
            attempts: entry.attempts + 1,
            lastError: error.message,
          } satisfies PendingTransaction)
          // A permanently invalid record must not prevent later records syncing.
          continue
        }
        // Preserve ordering when the connection or server is unavailable.
        break
      }
    }
    await refreshPending()
  }, [queryClient, refreshPending])

  const queue = useCallback(async (input: SimpleTransaction) => {
    const userId = userIdRef.current
    if (!userId) throw new Error("No hay una sesión activa para guardar el movimiento")
    const entry: PendingTransaction = {
      clientId: input.clientId,
      userId,
      payload: input,
      createdAt: Date.now(),
      attempts: 0,
    }
    const db = await dbPromise
    await db.put(STORE, entry)
    await refreshPending()
    return pendingAsTransaction(entry)
  }, [refreshPending])

  const discard = useCallback(async (clientId: string) => {
    const db = await dbPromise
    const existing = await db.get(STORE, clientId)
    if (existing) {
      await db.delete(STORE, clientId)
      await refreshPending()
    }
  }, [refreshPending])

  useEffect(() => {
    void refreshPending()
    refreshCacheAge()
    const unsubscribe = queryClient.getQueryCache().subscribe(refreshCacheAge)
    const interval = window.setInterval(() => {
      refreshCacheAge()
      void flush()
    }, 30_000)
    const handleOnline = () => {
      setOnline(true)
      void flush()
    }
    const handleOffline = () => setOnline(false)
    const handleFocus = () => {
      if (navigator.onLine) void flush()
    }
    window.addEventListener("online", handleOnline)
    window.addEventListener("offline", handleOffline)
    window.addEventListener("focus", handleFocus)
    return () => {
      unsubscribe()
      window.clearInterval(interval)
      window.removeEventListener("online", handleOnline)
      window.removeEventListener("offline", handleOffline)
      window.removeEventListener("focus", handleFocus)
    }
  }, [flush, queryClient, refreshCacheAge, refreshPending])

  useEffect(() => {
    void refreshPending()
    if (session?.id) void flush()
  }, [flush, refreshPending, session?.id])

  return <OfflineContext value={{ online, pending, queue, flush, discard, cacheUpdatedAt }}>{children}</OfflineContext>
}

export function useOffline() {
  const context = useContext(OfflineContext)
  if (!context) throw new Error("useOffline must be used inside OfflineProvider")
  return context
}
