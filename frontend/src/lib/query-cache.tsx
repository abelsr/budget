import { useEffect, useRef, useState } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { persistQueryClient } from "@tanstack/react-query-persist-client"
import type { Persister, PersistedClient } from "@tanstack/query-persist-client-core"
import { openDB } from "idb"

import { useAuth } from "@/lib/auth"

const CACHE_MAX_AGE = 24 * 60 * 60 * 1000

const DB_NAME = "budget-query-cache"
const STORE = "cache"

let dbPromise: ReturnType<typeof openDB> | null = null
function cacheDB() {
  if (!dbPromise) {
    dbPromise = openDB(DB_NAME, 1, {
      upgrade(db) {
        db.createObjectStore(STORE, { keyPath: "key" })
      },
    })
  }
  return dbPromise
}

/**
 * Persister asíncrono sobre IndexedDB (issue #43, punto 1). Sustituye el
 * persister síncrono de `localStorage`: el cache completo (hasta 200
 * transacciones + adjuntos) ya no se serializa en el main thread en cada
 * mutación, no hay riesgo de `QuotaExceededError` (la cuota de localStorage es
 * ~5 MB, la de IndexedDB de cientos de MB) y los datos financieros sensibles
 * salen de `localStorage`, donde un XSS podría leerlos.
 */
function createIdbPersister(key: string): Persister {
  return {
    async restoreClient() {
      const db = await cacheDB()
      const record = (await db.get(STORE, key)) as
        | { key: string; data: PersistedClient }
        | undefined
      return record?.data
    },
    async persistClient(client) {
      const db = await cacheDB()
      await db.put(STORE, { key, data: client })
    },
    async removeClient() {
      const db = await cacheDB()
      await db.delete(STORE, key)
    },
  }
}

/** Restores and saves only the cache belonging to the authenticated identity. */
export function AuthenticatedQueryCache({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient()
  const { session } = useAuth()
  const previousUserId = useRef<string | null>(null)
  const [restoredUserId, setRestoredUserId] = useState<string | null>(null)

  useEffect(() => {
    const userId = session?.id ?? null
    const previous = previousUserId.current
    if (previous && previous !== userId) {
      // Borra el cache del usuario saliente (su identidad ya no es válida).
      void createIdbPersister(`budget-query-cache:${previous}`).removeClient()
    }
    previousUserId.current = userId
    setRestoredUserId(null)
    if (!userId) return

    const persister = createIdbPersister(`budget-query-cache:${userId}`)
    const [unsubscribe, restored] = persistQueryClient({ queryClient, persister, maxAge: CACHE_MAX_AGE })
    let cancelled = false
    void restored.then(() => {
      if (!cancelled) setRestoredUserId(userId)
    }, () => {
      if (!cancelled) setRestoredUserId(userId)
    })
    return () => {
      cancelled = true
      unsubscribe()
    }
  }, [queryClient, session?.id])

  if (session && restoredUserId !== session.id) return null
  return children
}
