import { Suspense, lazy } from "react"
import { BrowserRouter, Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom"
import { MotionConfig } from "motion/react"

import { useAuth } from "@/lib/auth"
import { LandingI18nProvider } from "@/lib/landing-i18n"
import { AppShell } from "@/components/layout/AppShell"

// Code-splitting (issue #44): cada página es un chunk que Vite carga bajo
// demanda. Los bundles pesados (recharts en Dashboard/Reports, motion,
// react-day-picker) solo se descargan al visitar la página que los usa.
const DashboardPage = lazy(() => import("@/pages/DashboardPage").then((m) => ({ default: m.DashboardPage })))
const TransactionsPage = lazy(() => import("@/pages/TransactionsPage").then((m) => ({ default: m.TransactionsPage })))
const AccountsPage = lazy(() => import("@/pages/AccountsPage").then((m) => ({ default: m.AccountsPage })))
const SettingsPage = lazy(() => import("@/pages/SettingsPage").then((m) => ({ default: m.SettingsPage })))
const CategoriesPage = lazy(() => import("@/pages/CategoriesPage").then((m) => ({ default: m.CategoriesPage })))
const RecurringPage = lazy(() => import("@/pages/RecurringPage").then((m) => ({ default: m.RecurringPage })))
const LoginPage = lazy(() => import("@/pages/LoginPage").then((m) => ({ default: m.LoginPage })))
const OnboardingPage = lazy(() => import("@/pages/OnboardingPage").then((m) => ({ default: m.OnboardingPage })))
const LandingPage = lazy(() => import("@/pages/LandingPage").then((m) => ({ default: m.LandingPage })))
const ReportsPage = lazy(() => import("@/pages/ReportsPage").then((m) => ({ default: m.ReportsPage })))
const PrivacyPage = lazy(() => import("@/pages/PrivacyPage").then((m) => ({ default: m.PrivacyPage })))
const ImportPage = lazy(() => import("@/pages/ImportPage").then((m) => ({ default: m.ImportPage })))
const MerchantRulesPage = lazy(() => import("@/pages/MerchantRulesPage").then((m) => ({ default: m.MerchantRulesPage })))
const BudgetsPage = lazy(() => import("@/pages/BudgetsPage").then((m) => ({ default: m.BudgetsPage })))
const GoalsPage = lazy(() => import("@/pages/GoalsPage").then((m) => ({ default: m.GoalsPage })))

function PageFallback() {
  return <div className="min-h-dvh" aria-label="Cargando" />
}

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
        <Suspense fallback={<PageFallback />}>
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
              <Route path="presupuestos" element={<BudgetsPage />} />
              <Route path="metas" element={<GoalsPage />} />
              <Route path="reportes" element={<ReportsPage />} />
              <Route path="ajustes" element={<SettingsPage />} />
              <Route path="ajustes/categorias" element={<CategoriesPage />} />
              <Route path="ajustes/recurrentes" element={<RecurringPage />} />
              <Route path="ajustes/reglas-de-comercios" element={<MerchantRulesPage />} />
              <Route path="importar" element={<ImportPage />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        </Suspense>
      </BrowserRouter>
    </MotionConfig>
  )
}

export default App
