import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react"

export type Theme = "light" | "dark" | "system"

const STORAGE_KEY = "ff-theme"

const ThemeContext = createContext<{
  theme: Theme
  setTheme: (t: Theme) => void
} | null>(null)

function resolveDark(theme: Theme): boolean {
  if (theme === "dark") return true
  if (theme === "light") return false
  return window.matchMedia("(prefers-color-scheme: dark)").matches
}

function applyTheme(theme: Theme) {
  const dark = resolveDark(theme)
  document.documentElement.classList.toggle("dark", dark)
  // theme-color: pinta la barra del sistema en la PWA
  document
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute("content", dark ? "#000000" : "#f2f2f7")
}

/**
 * Tema claro/oscuro/sistema. Persiste en localStorage; el script inline
 * en index.html aplica la clase antes del primer paint (sin flash).
 * En "system" escucha cambios del SO en vivo.
 */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored === "light" || stored === "dark" || stored === "system"
      ? stored
      : "system"
  })

  useEffect(() => {
    applyTheme(theme)
    if (theme !== "system") return
    const mq = window.matchMedia("(prefers-color-scheme: dark)")
    const onChange = () => applyTheme("system")
    mq.addEventListener("change", onChange)
    return () => mq.removeEventListener("change", onChange)
  }, [theme])

  const setTheme = useCallback((t: Theme) => {
    localStorage.setItem(STORAGE_KEY, t)
    setThemeState(t)
  }, [])

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error("useTheme debe usarse dentro de ThemeProvider")
  return ctx
}
