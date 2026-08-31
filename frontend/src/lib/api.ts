/**
 * Cliente HTTP para la API FastAPI.
 *
 * - Base URL `/api`: en dev el proxy de Vite lo reenvía a :8000;
 *   en prod nginx lo proxifica al contenedor backend.
 * - Token JWT en localStorage ("ff-token"); se adjunta como Bearer.
 * - Errores: ApiError con status y detail del servidor.
 */

const TOKEN_KEY = "ff-token"

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

/**
 * Callback de no-autorización: se invoca cuando una respuesta 401 corresponde
 * al token vigente (ver la guarda de token obsoleto en `apiFetch`). El
 * AuthProvider lo registra para desloguear la UI (limpieza de estado +
 * redirección a /login); sin él el token se limpiaba en silencio y la app
 * seguía mostrando sesión activa con un token muerto.
 */
let onUnauthorizedCallback: (() => void) | null = null

export function setOnUnauthorized(callback: (() => void) | null) {
  onUnauthorizedCallback = callback
}

/**
 * Limpia el token y notifica al AuthProvider SOLO si el 401 corresponde a la
 * sesión vigente: la petición debe haber enviado un token y ese token debe
 * seguir siendo el actual. Así un 401 en vuelo de la sesión anterior (p. ej.
 * /auth/me con token caducado) o de una petición sin token no borra el token
 * de un re-login que acabe de completar.
 */
function handleUnauthorized(sentToken: string | null) {
  if (sentToken === null || getToken() !== sentToken) return
  setToken(null)
  onUnauthorizedCallback?.()
}

/**
 * Renovación silenciosa: a un 401 con token vigente se le intenta UN refresh
 * (`POST /auth/refresh` con el token ya caducado pero no revocado). Si el
 * backend lo rota, se guarda el token nuevo y la petición original se reenvía
 * una sola vez; si no (revocado / sin jti / sin red), se desloguea.
 *
 * Usa `fetch` directo (no `apiFetch`) para no recursar: el refresh es el único
 * 401 que se gestiona sin pasar por esta lógica. Una promesa compartida
 * deduplica los 401 simultáneos (varias peticiones en vuelo caducan a la vez
 * y solo dispara un refresh).
 */
let inFlightRefresh: Promise<string | null> | null = null

function silentRefresh(expiredToken: string): Promise<string | null> {
  if (inFlightRefresh) return inFlightRefresh
  inFlightRefresh = (async () => {
    try {
      const res = await fetch("/api/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ accessToken: expiredToken }),
      })
      if (res.status !== 200) return null
      const body = (await res.json()) as { accessToken?: string }
      const fresh = body.accessToken
      if (!fresh) return null
      // Solo adopta el token nuevo si sigue siendo el de la sesión vigente:
      // si hubo un login/logout en paralelo, no pisar su estado.
      if (getToken() === expiredToken) setToken(fresh)
      return fresh
    } catch {
      return null // sin red / fallo de parseo → tratar como no renovable
    } finally {
      inFlightRefresh = null
    }
  })()
  return inFlightRefresh
}

export class ApiError extends Error {
  status: number
  detail: unknown

  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : `Error ${status}`)
    this.name = "ApiError"
    this.status = status
    this.detail = detail
  }
}

async function parseError(res: Response): Promise<ApiError> {
  try {
    const body = await res.json()
    return new ApiError(res.status, body.detail ?? `Error ${res.status}`)
  } catch {
    return new ApiError(res.status, `Error ${res.status}`)
  }
}

export interface ApiFetchOptions extends RequestInit {
  /** Conserva el token cuando un 401 es un error esperado de la operación. */
  clearTokenOnUnauthorized?: boolean
}

export async function apiFetch<T>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<T> {
  const { clearTokenOnUnauthorized = true, ...fetchOptions } = options
  const token = getToken()
  const headers = new Headers(fetchOptions.headers)
  if (token) headers.set("Authorization", `Bearer ${token}`)
  // FormData (multipart) define su propio Content-Type con boundary
  if (fetchOptions.body && !(fetchOptions.body instanceof FormData)) {
    headers.set("Content-Type", "application/json")
  }

  const res = await fetch(`/api${path}`, { ...fetchOptions, headers })
  if (res.status === 401 && clearTokenOnUnauthorized) {
    // Renovación silenciosa: un token caducado pero no revocado se renueva y
    // la petición se reenvía UNA vez con el token nuevo.
    if (token) {
      const fresh = await silentRefresh(token)
      if (fresh && getToken() === fresh) {
        headers.set("Authorization", `Bearer ${fresh}`)
        const retried = await fetch(`/api${path}`, { ...fetchOptions, headers })
        if (retried.status === 401) {
          handleUnauthorized(fresh) // el token nuevo tampoco pasó: sesión muerta
        }
        if (!retried.ok) throw await parseError(retried)
        if (retried.status === 204) return undefined as T
        return retried.json() as Promise<T>
      }
    }
    handleUnauthorized(token) // sin renovar (revocado/legacy/fallo) → desloguear
  }
  if (!res.ok) throw await parseError(res)
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

/** Como apiFetch pero devuelve el cuerpo binario (para descargar adjuntos). */
export async function apiFetchBlob(path: string): Promise<Blob> {
  const token = getToken()
  const headers = new Headers()
  if (token) headers.set("Authorization", `Bearer ${token}`)

  const res = await fetch(`/api${path}`, { headers })
  if (res.status === 401) {
    if (token) {
      const fresh = await silentRefresh(token)
      if (fresh && getToken() === fresh) {
        headers.set("Authorization", `Bearer ${fresh}`)
        const retried = await fetch(`/api${path}`, { headers })
        if (retried.status === 401) handleUnauthorized(fresh)
        if (!retried.ok) throw await parseError(retried)
        return retried.blob()
      }
    }
    handleUnauthorized(token)
  }
  if (!res.ok) throw await parseError(res)
  return res.blob()
}
