import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react"
import { useQueryClient } from "@tanstack/react-query"

import { ApiError, apiFetch, getToken, setOnUnauthorized, setToken } from "@/lib/api"

const SESSION_KEY = "ff-session"
const SESSION_TOKEN_KEY = "ff-session-token"

function getStoredSession(): Session | null {
  try {
    if (localStorage.getItem(SESSION_TOKEN_KEY) !== getToken()) return null
    return JSON.parse(localStorage.getItem(SESSION_KEY) ?? "null") as Session | null
  } catch {
    return null
  }
}

function storeSession(session: Session | null) {
  if (session) {
    localStorage.setItem(SESSION_KEY, JSON.stringify(session))
    localStorage.setItem(SESSION_TOKEN_KEY, getToken() ?? "")
  } else {
    localStorage.removeItem(SESSION_KEY)
    localStorage.removeItem(SESSION_TOKEN_KEY)
  }
}

/**
 * Autenticación contra el backend FastAPI.
 *
 * - El JWT vive en una cookie httpOnly que gestiona el backend (issue #34);
 *   api.ts solo persiste su identificador (jti) en "ff-token". Aquí se hidrata
 *   la sesión.
 * - Al montar el provider, si hay token se llama GET /auth/me; si falla
 *   se limpia el token y la app queda deslogueada.
 * - login/register/join guardan el tokenIdentifier (jti) devuelto y luego
 *   hidratan la sesión con GET /auth/me. Los ApiError se propagan para que la
 *   página los muestre.
 */

export interface Session {
  id: string
  email: string
  name: string
  householdId: string | null
  /** false → el wizard de `/onboarding` está pendiente. */
  onboardingCompleted: boolean
  sex: Sex | null
  birthDate: string | null
  hasAvatar: boolean
  avatarUpdatedAt: string | null
}

export type Sex = "female" | "male" | "non_binary" | "prefer_not_to_say"

export interface ProfileUpdate {
  name?: string
  sex?: Sex | null
  birthDate?: string | null
}

interface TokenResponse {
  tokenIdentifier: string
  tokenType: string
}

interface AuthContextValue {
  session: Session | null
  /** true mientras se restaura la sesión inicial (GET /auth/me). */
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (
    email: string,
    password: string,
    name: string,
    householdName: string,
  ) => Promise<void>
  join: (
    inviteToken: string,
    email: string,
    password: string,
    name: string,
  ) => Promise<void>
  /** Marca el wizard inicial como terminado (o saltado). */
  completeOnboarding: () => Promise<void>
  updateProfile: (profile: ProfileUpdate) => Promise<void>
  uploadAvatar: (file: File) => Promise<void>
  removeAvatar: () => Promise<void>
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

function fetchMe(): Promise<Session> {
  return apiFetch<Session>("/auth/me")
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [session, setSession] = useState<Session | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const logout = useCallback(() => {
    void queryClient.cancelQueries()
    queryClient.clear()
    // Borra la cookie httpOnly en el servidor (issue #34): el SPA no puede
    // eliminarla solo. Fire-and-forget: aunque falle (offline), setToken(null)
    // deja la UI deslogueada y el token expira en 15 min de todos modos.
    void apiFetch<void>("/auth/logout", { method: "POST", clearTokenOnUnauthorized: false }).catch(
      () => {},
    )
    setToken(null)
    storeSession(null)
    setSession(null)
  }, [queryClient])

  // Un 401 con token vigente desloguea la UI (limpieza de estado +
  // redirección a /login vía RequireAuth). logout() es idempotente: si api.ts
  // ya borró el token, repetir setToken(null) no hace nada, y el callback
  // solo se dispara una vez por 401 (guarda de token obsoleto en api.ts).
  useEffect(() => {
    setOnUnauthorized(logout)
    return () => setOnUnauthorized(null)
  }, [logout])

  // Restaurar sesión inicial
  useEffect(() => {
    if (!getToken()) {
      setIsLoading(false)
      return
    }
    let cancelled = false
    fetchMe()
      .then((me) => {
        storeSession(me)
        if (!cancelled) setSession(me)
      })
      .catch((error) => {
        // Un 401 ya deslogueó la UI vía onUnauthorized (api.ts: token + sesión
        // + redirección a /login), así que aquí solo queda cerrar el loading.
        // Un error de red NO debe desloguear una app instalada: sus datos en
        // cache siguen legibles hasta que el servidor rechace el token.
        if (!(error instanceof ApiError && error.status === 401) && !cancelled) {
          setSession(getStoredSession())
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  /** Guarda el token del endpoint y luego hidrata la sesión con /auth/me. */
  const authenticate = useCallback(
    async (tokenRequest: () => Promise<TokenResponse>) => {
      // Never expose the previous account's cached data under a new token.
      await queryClient.cancelQueries()
      queryClient.clear()
      storeSession(null)
      setSession(null)
      const { tokenIdentifier } = await tokenRequest()
      setToken(tokenIdentifier)
      const me = await fetchMe()
      storeSession(me)
      setSession(me)
    },
    [queryClient],
  )

  const login = useCallback(
    (email: string, password: string) =>
      authenticate(
        () => apiFetch<TokenResponse>("/auth/login", {
          method: "POST",
          body: JSON.stringify({ email, password }),
        }),
      ),
    [authenticate],
  )

  const register = useCallback(
    (email: string, password: string, name: string, householdName: string) =>
      authenticate(
        () => apiFetch<TokenResponse>("/auth/register", {
          method: "POST",
          body: JSON.stringify({ email, password, name, householdName }),
        }),
      ),
    [authenticate],
  )

  const join = useCallback(
    (inviteToken: string, email: string, password: string, name: string) =>
      authenticate(
        () => apiFetch<TokenResponse>("/auth/join", {
          method: "POST",
          body: JSON.stringify({
            token: inviteToken,
            email,
            password,
            name,
          }),
        }),
      ),
    [authenticate],
  )

  const completeOnboarding = useCallback(async () => {
    const me = await apiFetch<Session>("/auth/me/onboarding", {
      method: "PATCH",
      body: JSON.stringify({ completed: true }),
    })
    storeSession(me)
    setSession(me)
  }, [])

  const updateProfile = useCallback(async (profile: ProfileUpdate) => {
    const me = await apiFetch<Session>("/auth/me", {
      method: "PATCH",
      body: JSON.stringify(profile),
    })
    storeSession(me)
    setSession(me)
  }, [])

  const uploadAvatar = useCallback(async (file: File) => {
    const formData = new FormData()
    formData.append("file", file)
    const me = await apiFetch<Session>("/auth/me/avatar", {
      method: "POST",
      body: formData,
    })
    storeSession(me)
    setSession(me)
  }, [])

  const removeAvatar = useCallback(async () => {
    await apiFetch<void>("/auth/me/avatar", { method: "DELETE" })
    setSession((current) => {
      const next = current ? { ...current, hasAvatar: false, avatarUpdatedAt: null } : null
      storeSession(next)
      return next
    })
  }, [])

  const changePassword = useCallback(
    async (currentPassword: string, newPassword: string) => {
      await apiFetch<void>("/auth/change-password", {
        method: "POST",
        body: JSON.stringify({ currentPassword, newPassword }),
        clearTokenOnUnauthorized: false,
      })
      // El cambio de contraseña revoca TODAS las sesiones (incluida esta) y
      // borra la cookie httpOnly (issue #34): la sesión actual queda muerta,
      // así que se desloguea para forzar un re-login con la nueva clave.
      logout()
    },
    [logout],
  )

  return (
    <AuthContext.Provider
      value={{
        session,
        isLoading,
        login,
        register,
        join,
        completeOnboarding,
        updateProfile,
        uploadAvatar,
        removeAvatar,
        changePassword,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth debe usarse dentro de AuthProvider")
  return ctx
}
