import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { act, render, waitFor } from "@testing-library/react"
import { openDB } from "idb"

// El provider necesita una sesión; mockeamos useAuth para no montar el AuthProvider.
vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ session: { id: "user-1" } }),
}))

// Mantenemos ApiError y getToken reales, pero stubiamos apiFetch para controlar el servidor.
vi.mock("@/lib/api", async (importOriginal) => {
  const mod = await importOriginal<typeof import("@/lib/api")>()
  return { ...mod, apiFetch: vi.fn(), getToken: () => "tok" }
})

import { OfflineProvider, useOffline } from "@/lib/offline"
import { useAddTransaction } from "@/lib/queries"
import { apiFetch, ApiError } from "@/lib/api"

const DB_NAME = "budget-offline"
const STORE = "pending_transactions"
const USER = "user-1"

const apiMock = apiFetch as unknown as ReturnType<typeof vi.fn>

// apiFetch devuelve Promise<Transaction> (ya parsea), el mock resuelve un objeto.
function ok(): unknown {
  return { id: "tx-1" }
}

async function putEntry(overrides: Partial<{ attempts: number; permanent: boolean; retryAfter: number; clientId: string }> = {}) {
  const db = await openDB(DB_NAME, 1)
  const clientId = overrides.clientId ?? "client-1"
  await db.put(STORE, {
    clientId,
    userId: USER,
    payload: { type: "expense", amount: 10, categoryId: "c1", accountId: "a1", date: "2026-09-01", clientId },
    createdAt: Date.now(),
    attempts: overrides.attempts ?? 0,
    permanent: overrides.permanent,
    retryAfter: overrides.retryAfter,
  })
  await db.close()
}

async function entries() {
  const db = await openDB(DB_NAME, 1)
  const all = (await db.getAllFromIndex(STORE, "createdAt")) as Array<{ clientId: string; permanent?: boolean; attempts: number }>
  await db.close()
  return all
}

function mount() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  type AddInput = Parameters<ReturnType<typeof useAddTransaction>["mutate"]>[0]
  const utils: { flush: () => void; add: (v: AddInput) => void } = { flush: () => {}, add: () => {} }
  const Harness = () => {
    const { flush } = useOffline()
    const add = useAddTransaction()
    utils.flush = () => void flush()
    utils.add = (v) => void add.mutate(v)
    return null
  }
  return { utils, unmount: render(
    <QueryClientProvider client={qc}>
      <OfflineProvider>
        <Harness />
      </OfflineProvider>
    </QueryClientProvider>,
  ).unmount }
}

beforeEach(async () => {
  // No usar deleteDB: offline.tsx abre openDB a nivel de módulo (conexión
  // global) y deleteDB colgaría esperando que se libere. Vaciamos el store.
  const db = await openDB(DB_NAME, 1)
  await db.clear(STORE)
  await db.close()
  apiMock.mockReset()
  Object.defineProperty(window.navigator, "onLine", { value: true, configurable: true })
})
afterEach(() => vi.restoreAllMocks())

describe("offline outbox integridad (#35)", () => {
  it("flush concurrente no duplica: el mutex evita re-submitir la misma entrada", async () => {
    await putEntry({})
    apiMock.mockResolvedValue(ok())
    const { utils, unmount } = mount()

    // Tres flush simultáneos: sin mutex harían 3 POST de la misma entrada.
    await act(async () => {
      utils.flush()
      utils.flush()
      utils.flush()
    })

    await waitFor(async () => {
      expect((await entries()).length).toBe(0)
    })
    expect(apiMock).toHaveBeenCalledTimes(1)
    unmount()
  })

  it("5xx del servidor encola el movimiento en el outbox", async () => {
    apiMock.mockRejectedValue(new ApiError(500, "servicio caído"))
    const { utils, unmount } = mount()

    await act(async () => {
      utils.add({ type: "expense", amount: 5, categoryId: "c1", accountId: "a1", date: "2026-09-01" })
    })

    await waitFor(async () => {
      const all = await entries()
      expect(all).toHaveLength(1)
      expect(all[0].attempts).toBe(0)
    })
    unmount()
  })

  it("4xx no se reintenta en bucle: la entrada queda permanent y se omite", async () => {
    await putEntry({})
    apiMock.mockRejectedValue(new ApiError(400, "inválido"))
    const { utils, unmount } = mount()

    await act(async () => {
      utils.flush()
    })
    await waitFor(async () => {
      const e = await entries()
      expect(e[0].permanent).toBe(true)
    })

    // Un segundo flush NO vuelve a POSTear la entrada permanente.
    apiMock.mockClear()
    await act(async () => {
      utils.flush()
    })
    await new Promise((r) => setTimeout(r, 20))
    expect(apiMock).not.toHaveBeenCalled()
    unmount()
  })
})
