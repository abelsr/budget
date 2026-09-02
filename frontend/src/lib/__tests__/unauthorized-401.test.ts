import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

import { ApiError, apiFetch, getToken, setOnUnauthorized, setToken } from "@/lib/api"

beforeEach(() => {
  localStorage.clear()
  setOnUnauthorized(null)
})
afterEach(() => vi.restoreAllMocks())

function notOk(status: number): Response {
  return { status, ok: false, json: async () => ({ detail: "err" }) } as Response
}
function ok<T>(body: T): Response {
  return { status: 200, ok: true, json: async () => body } as Response
}

describe("#41 — 401: deslogueo y race condition", () => {
  it("no borra el token nuevo cuando un 401 en vuelo de la sesión anterior responde tras un re-login", async () => {
    // Sesión vieja vigente, con una petición en vuelo que usa ese token.
    setToken("old")
    const unauthorized = vi.fn()
    setOnUnauthorized(unauthorized)

    const fetchMock = vi.fn()
    fetchMock
      // 1) /auth/me con el token viejo → 401
      .mockResolvedValueOnce(notOk(401))
      // 2) /auth/refresh (fetch directo): el re-login completa EN ESTE INSTANTE
      //    (cookie nueva) y el refresh con el token viejo ya no sirve → 401.
      .mockImplementationOnce(() => {
        setToken("new")
        return Promise.resolve(notOk(401))
      })
    vi.spyOn(globalThis, "fetch").mockImplementation(fetchMock as never)

    const status = await apiFetch("/auth/me", { timeoutMs: 0 }).then(
      () => "ok",
      (e) => (e instanceof ApiError ? e.status : "unknown"),
    )

    // El 401 de la sesión vieja NO borró el token del re-login…
    expect(getToken()).toBe("new")
    // …ni deslogueó la UI.
    expect(unauthorized).not.toHaveBeenCalled()
    // La petición /auth/me (de la sesión vieja) falló con 401, que es correcto.
    expect(status).toBe(401)
  })

  it("SÍ desloguea la UI cuando el 401 es del token vigente y no se puede renovar", async () => {
    setToken("current")
    const unauthorized = vi.fn()
    setOnUnauthorized(unauthorized)

    const fetchMock = vi.fn()
    fetchMock
      .mockResolvedValueOnce(notOk(401)) // la petición
      .mockResolvedValueOnce(notOk(401)) // refresh: revocado, no renueva
    vi.spyOn(globalThis, "fetch").mockImplementation(fetchMock as never)

    await apiFetch("/auth/me", { timeoutMs: 0 }).catch(() => {})

    expect(getToken()).toBeNull()
    expect(unauthorized).toHaveBeenCalledTimes(1)
  })

  it("renueva silenciosamente y reenvía la petición cuando el 401 es por caducidad", async () => {
    setToken("stale")
    const unauthorized = vi.fn()
    setOnUnauthorized(unauthorized)

    const fetchMock = vi.fn()
    fetchMock
      .mockResolvedValueOnce(notOk(401)) // petición → 401 (caducada)
      .mockResolvedValueOnce(ok({ tokenIdentifier: "fresh" })) // refresh ok → nuevo jti
      .mockResolvedValueOnce(ok({ id: "u1" })) // reenvío → 200
    vi.spyOn(globalThis, "fetch").mockImplementation(fetchMock as never)

    const data = await apiFetch<{ id: string }>("/auth/me", { timeoutMs: 0 })

    expect(data).toEqual({ id: "u1" })
    expect(getToken()).toBe("fresh") // adoptó el jti del refresh
    expect(unauthorized).not.toHaveBeenCalled()
    expect(fetchMock).toHaveBeenCalledTimes(3)
  })
})
