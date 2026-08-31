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
  if (res.status === 401 && clearTokenOnUnauthorized) handleUnauthorized(token)
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
  if (res.status === 401) handleUnauthorized(token)
  if (!res.ok) throw await parseError(res)
  return res.blob()
}
