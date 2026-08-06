import { useEffect, useRef, useState } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { persistQueryClient } from "@tanstack/react-query-persist-client"
import { createSyncStoragePersister } from "@tanstack/query-sync-storage-persister"

import { useAuth } from "@/lib/auth"

const CACHE_MAX_AGE = 24 * 60 * 60 * 1000

function cacheKey(userId: string) {
  return `budget-query-cache:${userId}`
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
      void createSyncStoragePersister({ storage: window.localStorage, key: cacheKey(previous) }).removeClient()
    }
    previousUserId.current = userId
    setRestoredUserId(null)
    if (!userId) return

    const persister = createSyncStoragePersister({ storage: window.localStorage, key: cacheKey(userId) })
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
