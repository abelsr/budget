import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from "react"

/**
 * Auth mock. Persiste una sesión falsa en localStorage para desarrollar
 * la UI completa (login, guarda de rutas, cerrar sesión).
 *
 * INTEGRACIÓN BACKEND: reemplazar login/logout por llamadas a
 * POST /auth/login (email+password → JWT) y guardar el token; la UI
 * no cambia.
 */

export interface Session {
  email: string
  name: string
}

const STORAGE_KEY = "ff-session"

const AuthContext = createContext<{
  session: Session | null
  login: (email: string, password: string) => void
  logout: () => void
} | null>(null)

function readSession(): Session | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as Session) : null
  } catch {
    return null
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(readSession)

  const login = useCallback((email: string, _password: string) => {
    const name = email.split("@")[0]
    const s: Session = {
      email,
      name: name.charAt(0).toUpperCase() + name.slice(1),
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(s))
    setSession(s)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY)
    setSession(null)
  }, [])

  return (
    <AuthContext.Provider value={{ session, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth debe usarse dentro de AuthProvider")
  return ctx
}
