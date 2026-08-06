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
  if (res.status === 401 && clearTokenOnUnauthorized) setToken(null) // sesión expirada
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
  if (res.status === 401) setToken(null) // sesión expirada
  if (!res.ok) throw await parseError(res)
  return res.blob()
}
