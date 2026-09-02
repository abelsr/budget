/**
 * Cliente HTTP para la API FastAPI.
 *
 * - Base URL `/api`: en dev el proxy de Vite lo reenvía a :8000;
 *   en prod nginx lo proxifica al contenedor backend.
 * - Autenticación por cookie httpOnly `ff_token` (issue #34): el JWT lo setea
 *   el backend en login/register/join/refresh y lo envía el navegador solo;
 *   JS no puede leerlo, así que este módulo NO envía `Authorization: Bearer`.
 * - `getToken`/`setToken` guardan el *identificador* del token (jti, expuesto
 *   como `tokenIdentifier` en la respuesta), no el JWT: solo se usa para
 *   detectar token obsoleto (rotación por refresh / cambio de usuario) en
 *   las flush offline y la hidratación de sesión.
 * - Errores: ApiError con status y detail del servidor.
 */

const TOKEN_KEY = "ff-token"

/** Identificador (jti) del token vigente, o null si no hay sesión. */
export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

/** Guarda el identificador (jti) del token, o null para desloguear. */
export function setToken(tokenIdentifier: string | null) {
  if (tokenIdentifier) localStorage.setItem(TOKEN_KEY, tokenIdentifier)
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
 * (`POST /auth/refresh`). El backend toma el token de la cookie httpOnly (JS
 * no puede leerlo) y, si lo rota, devuelve el nuevo token + su jti; se guarda
 * el jti nuevo y la cookie queda actualizada por la propia respuesta.
 *
 * Usa `fetch` directo (no `apiFetch`) para no recursar: el refresh es el único
 * 401 que se gestiona sin pasar por esta lógica. Una promesa compartida
 * deduplica los 401 simultáneos (varias peticiones en vuelo caducan a la vez
 * y solo dispara un refresh).
 */
let inFlightRefresh: Promise<string | null> | null = null

function silentRefresh(sentToken: string): Promise<string | null> {
  if (inFlightRefresh) return inFlightRefresh
  inFlightRefresh = (async () => {
    try {
      // Sin body: el token lo envía la cookie httpOnly (issue #34).
      const res = await fetch("/api/auth/refresh", { method: "POST" })
      if (res.status !== 200) return null
      const body = (await res.json()) as { tokenIdentifier?: string }
      const fresh = body.tokenIdentifier
      if (!fresh) return null
      // Solo adopta el jti nuevo si sigue siendo el de la sesión vigente:
      // si hubo un login/logout en paralelo, no pisar su estado.
      if (getToken() === sentToken) setToken(fresh)
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
  /** Timeout en ms del request. Por defecto 30_000 (issue #43). */
  timeoutMs?: number
}

const DEFAULT_TIMEOUT_MS = 30_000

function buildHeaders(fetchOptions: RequestInit): Headers {
  const headers = new Headers(fetchOptions.headers)
  // Sin Bearer: la cookie httpOnly `ff_token` (credentials same-origin) lleva
  // el JWT y el backend lo lee. (issue #34)
  // FormData (multipart) define su propio Content-Type con boundary
  if (fetchOptions.body && !(fetchOptions.body instanceof FormData)) {
    headers.set("Content-Type", "application/json")
  }
  return headers
}

export async function apiFetch<T>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<T> {
  const {
    clearTokenOnUnauthorized = true,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    ...fetchOptions
  } = options
  const sentToken = getToken()
  const headers = buildHeaders(fetchOptions)
  // Timeout por defecto: un request colgado (escaneo IA, imports grandes) no
  // debe dejar la mutación pendiente indefinidamente (issue #43). Si el
  // caller ya pasó un signal (ej. AbortController de un hook), se combina.
  if (timeoutMs > 0) {
    const timeoutSignal = AbortSignal.timeout(timeoutMs)
    fetchOptions.signal =
      fetchOptions.signal && typeof AbortSignal.any === "function"
        ? AbortSignal.any([fetchOptions.signal, timeoutSignal])
        : fetchOptions.signal ?? timeoutSignal
  }

  const res = await fetch(`/api${path}`, { ...fetchOptions, headers })
  if (res.status === 401 && clearTokenOnUnauthorized) {
    // Renovación silenciosa: un token caducado pero no revocado se renueva y
    // la petición se reenvía UNA vez (la cookie ya lleva el token nuevo).
    if (sentToken) {
      const fresh = await silentRefresh(sentToken)
      if (fresh && getToken() === fresh) {
        const retried = await fetch(`/api${path}`, { ...fetchOptions, headers })
        if (retried.status === 401) {
          handleUnauthorized(fresh) // el token nuevo tampoco pasó: sesión muerta
        }
        if (!retried.ok) throw await parseError(retried)
        if (retried.status === 204) return undefined as T
        return retried.json() as Promise<T>
      }
    }
    handleUnauthorized(sentToken) // sin renovar (revocado/legacy/fallo) → desloguear
  }
  if (!res.ok) throw await parseError(res)
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

/** Como apiFetch pero devuelve el cuerpo binario (para descargar adjuntos). */
export async function apiFetchBlob(path: string): Promise<Blob> {
  const sentToken = getToken()
  const headers = buildHeaders({})

  const res = await fetch(`/api${path}`, { headers })
  if (res.status === 401) {
    if (sentToken) {
      const fresh = await silentRefresh(sentToken)
      if (fresh && getToken() === fresh) {
        const retried = await fetch(`/api${path}`, { headers })
        if (retried.status === 401) handleUnauthorized(fresh)
        if (!retried.ok) throw await parseError(retried)
        return retried.blob()
      }
    }
    handleUnauthorized(sentToken)
  }
  if (!res.ok) throw await parseError(res)
  return res.blob()
}
