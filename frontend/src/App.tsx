import { BrowserRouter, Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom"
import { MotionConfig } from "motion/react"

import { useAuth } from "@/lib/auth"
import { LandingI18nProvider } from "@/lib/landing-i18n"
import { AppShell } from "@/components/layout/AppShell"
import { DashboardPage } from "@/pages/DashboardPage"
import { TransactionsPage } from "@/pages/TransactionsPage"
import { AccountsPage } from "@/pages/AccountsPage"
import { SettingsPage } from "@/pages/SettingsPage"
import { CategoriesPage } from "@/pages/CategoriesPage"
import { RecurringPage } from "@/pages/RecurringPage"
import { LoginPage } from "@/pages/LoginPage"
import { OnboardingPage } from "@/pages/OnboardingPage"
import { LandingPage } from "@/pages/LandingPage"
import { ReportsPage } from "@/pages/ReportsPage"
import { PrivacyPage } from "@/pages/PrivacyPage"

const ONBOARDING_PATH = "/onboarding"
/** La app vive bajo /app; / es la landing pública. */
const APP_ROOT = "/app"

/**
 * Rutas que requieren sesión; redirige a /login recordando el destino.
 * Además encamina el wizard inicial: sin onboarding completado, todo lleva a
 * `/onboarding`; ya completado, `/onboarding` deja de existir. Ninguna decisión
 * se toma antes de que `/auth/me` resuelva, así no hay loops ni parpadeos.
 */
function RequireAuth() {
  const { session, isLoading } = useAuth()
  const location = useLocation()
  // Espera la restauración de sesión (/auth/me) antes de decidir
  if (isLoading) {
    return <div className="min-h-dvh" aria-label="Cargando" />
  }
  if (!session) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }
  const onOnboarding = location.pathname === ONBOARDING_PATH
  if (!session.onboardingCompleted && !onOnboarding) {
    return <Navigate to={ONBOARDING_PATH} replace />
  }
  if (session.onboardingCompleted && onOnboarding) {
    return <Navigate to={APP_ROOT} replace />
  }
  return <Outlet />
}

/** Si ya hay sesión, /login no tiene sentido. */
function RedirectIfAuthed({ children }: { children: React.ReactNode }) {
  const { session, isLoading } = useAuth()
  if (isLoading) {
    return <div className="min-h-dvh" aria-label="Cargando" />
  }
  if (session) return <Navigate to={APP_ROOT} replace />
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
          {/* La landing siempre es la página de entrada, con su i18n ES/EN. */}
          <Route
            path="/"
            element={
              <LandingI18nProvider>
                <LandingPage />
              </LandingI18nProvider>
            }
          />
          <Route path="/privacy" element={<PrivacyPage />} />
          <Route element={<RequireAuth />}>
            {/* Fuera del AppShell: el wizard ocupa la pantalla completa */}
            <Route path="onboarding" element={<OnboardingPage />} />
            <Route path={APP_ROOT} element={<AppShell />}>
              <Route index element={<DashboardPage />} />
              <Route path="transacciones" element={<TransactionsPage />} />
              <Route path="cuentas" element={<AccountsPage />} />
              <Route path="reportes" element={<ReportsPage />} />
              <Route path="ajustes" element={<SettingsPage />} />
              <Route path="ajustes/categorias" element={<CategoriesPage />} />
              <Route path="ajustes/recurrentes" element={<RecurringPage />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </MotionConfig>
  )
}

export default App
