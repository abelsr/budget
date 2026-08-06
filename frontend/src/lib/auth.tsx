import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react"
import { useQueryClient } from "@tanstack/react-query"

import { apiFetch, getToken, setToken } from "@/lib/api"

/**
 * Autenticación contra el backend FastAPI.
 *
 * - El JWT lo persiste api.ts ("ff-token"); aquí solo se hidrata la sesión.
 * - Al montar el provider, si hay token se llama GET /auth/me; si falla
 *   se limpia el token y la app queda deslogueada.
 * - login/register/join guardan el accessToken y luego hidratan la sesión
 *   con GET /auth/me. Los ApiError se propagan para que la página los muestre.
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
  accessToken: string
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

  // Restaurar sesión inicial
  useEffect(() => {
    if (!getToken()) {
      setIsLoading(false)
      return
    }
    let cancelled = false
    fetchMe()
      .then((me) => {
        if (!cancelled) setSession(me)
      })
      .catch(() => {
        // 401 u otro error: token inválido/expirado → limpiar
        setToken(null)
        if (!cancelled) setSession(null)
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
      const { accessToken } = await tokenRequest()
      setToken(accessToken)
      const me = await fetchMe()
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
    setSession(me)
  }, [])

  const updateProfile = useCallback(async (profile: ProfileUpdate) => {
    const me = await apiFetch<Session>("/auth/me", {
      method: "PATCH",
      body: JSON.stringify(profile),
    })
    setSession(me)
  }, [])

  const uploadAvatar = useCallback(async (file: File) => {
    const formData = new FormData()
    formData.append("file", file)
    const me = await apiFetch<Session>("/auth/me/avatar", {
      method: "POST",
      body: formData,
    })
    setSession(me)
  }, [])

  const removeAvatar = useCallback(async () => {
    await apiFetch<void>("/auth/me/avatar", { method: "DELETE" })
    setSession((current) =>
      current ? { ...current, hasAvatar: false, avatarUpdatedAt: null } : null,
    )
  }, [])

  const changePassword = useCallback(
    (currentPassword: string, newPassword: string) =>
      apiFetch<void>("/auth/change-password", {
        method: "POST",
        body: JSON.stringify({ currentPassword, newPassword }),
        clearTokenOnUnauthorized: false,
      }),
    [],
  )

  const logout = useCallback(() => {
    void queryClient.cancelQueries()
    queryClient.clear()
    setToken(null)
    setSession(null)
  }, [queryClient])

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
