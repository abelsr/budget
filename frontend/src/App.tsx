import { BrowserRouter, Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom"
import { MotionConfig } from "motion/react"

import { useAuth } from "@/lib/auth"
import { AppShell } from "@/components/layout/AppShell"
import { DashboardPage } from "@/pages/DashboardPage"
import { TransactionsPage } from "@/pages/TransactionsPage"
import { AccountsPage } from "@/pages/AccountsPage"
import { SettingsPage } from "@/pages/SettingsPage"
import { LoginPage } from "@/pages/LoginPage"

/** Rutas que requieren sesión; redirige a /login recordando el destino. */
function RequireAuth() {
  const { session } = useAuth()
  const location = useLocation()
  if (!session) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }
  return <Outlet />
}

/** Si ya hay sesión, /login no tiene sentido. */
function RedirectIfAuthed({ children }: { children: React.ReactNode }) {
  const { session } = useAuth()
  if (session) return <Navigate to="/" replace />
  return children
}

function App() {
  // reducedMotion="user": respeta prefers-reduced-motion en TODAS
  // las animaciones de Motion (springs → cross-fades instantáneos).
  return (
    <MotionConfig reducedMotion="user">
      <BrowserRouter>
        <Routes>
          <Route
            path="/login"
            element={
              <RedirectIfAuthed>
                <LoginPage />
              </RedirectIfAuthed>
            }
          />
          <Route element={<RequireAuth />}>
            <Route element={<AppShell />}>
              <Route index element={<DashboardPage />} />
              <Route path="transacciones" element={<TransactionsPage />} />
              <Route path="cuentas" element={<AccountsPage />} />
              <Route path="ajustes" element={<SettingsPage />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </MotionConfig>
  )
}

export default App
