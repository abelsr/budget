import { NavLink, Outlet } from "react-router-dom"
import { LayoutDashboard, ArrowLeftRight, Wallet, Settings } from "lucide-react"
import { motion } from "motion/react"

import { springIndicator } from "@/lib/springs"
import { useHousehold, useMembers } from "@/lib/queries"
import { AddTransactionButton } from "@/components/AddTransactionSheet"
import { TicketScannerButton } from "@/components/TicketScanner"

const tabs = [
  { to: "/", label: "Resumen", icon: LayoutDashboard },
  { to: "/transacciones", label: "Movimientos", icon: ArrowLeftRight },
  { to: "/cuentas", label: "Cuentas", icon: Wallet },
  { to: "/ajustes", label: "Ajustes", icon: Settings },
]

/**
 * App shell.
 * - Móvil: tab bar inferior flotante con material translúcido; el
 *   contenido scrollea debajo (scroll edge, sin bordes duros).
 * - Desktop: sidebar lateral con el mismo material.
 * El indicador del tab activo usa un layoutId compartido con spring,
 * para que se deslice de forma interrumpible entre tabs.
 */
export function AppShell() {
  const { data: members = [] } = useMembers()
  const { data: household, isError: householdError } = useHousehold()
  const householdName = householdError
    ? "Mi hogar"
    : (household?.name ?? "…")
  return (
    <div className="min-h-dvh">
      {/* Sidebar (desktop) */}
      <aside className="material-bar fixed inset-y-0 left-0 z-40 hidden w-60 flex-col border-r md:flex">
        {/* Isólogo de marca: isotipo + wordmark, y debajo el hogar activo */}
        <div className="flex items-center gap-2.5 px-6 pt-8 pb-6">
          <img
            src="/budget/isotipo.svg"
            alt=""
            aria-hidden="true"
            className="size-8 shrink-0 object-contain"
          />
          <div className="min-w-0">
            <h1 className="text-xl leading-none font-bold tracking-[-0.02em]">
              budget
            </h1>
            <p className="mt-1 truncate text-[13px] font-medium text-muted-foreground">
              {householdName}
            </p>
          </div>
        </div>
        <nav className="flex flex-col gap-1 px-3">
          {tabs.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `pressable relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-[15px] font-medium transition-colors ${
                  isActive
                    ? "text-primary"
                    : "text-foreground/70 hover:bg-black/5 dark:hover:bg-white/10"
                }`
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <motion.span
                      layoutId="sidebar-active"
                      transition={springIndicator}
                      className="absolute inset-0 rounded-xl bg-primary/10"
                    />
                  )}
                  <Icon size={20} className="relative" />
                  <span className="relative">{label}</span>
                </>
              )}
            </NavLink>
          ))}
          <div className="mx-3 my-2 h-px bg-border" />
          <TicketScannerButton variant="nav" />
        </nav>

        {/* Footer: miembros del hogar */}
        <div className="mt-auto flex items-center gap-3 px-6 py-5">
          <div className="flex -space-x-2">
            {members.map((m) => (
              <span
                key={m.id}
                title={m.name}
                className="flex size-8 items-center justify-center rounded-full bg-primary/10 text-[11px] font-semibold text-primary ring-2 ring-background"
              >
                {m.initials}
              </span>
            ))}
          </div>
          <div className="min-w-0">
            <p className="truncate text-[13px] font-medium">
              {members.map((m) => m.name).join(" y ")}
            </p>
            <p className="text-[11px] text-muted-foreground">Hogar compartido</p>
          </div>
        </div>
      </aside>

      {/* Contenido */}
      <main className="pb-28 md:pb-10 md:pl-60">
        <div className="mx-auto w-full max-w-2xl px-4 pt-6 md:max-w-3xl md:pt-10 lg:max-w-6xl lg:px-8 2xl:max-w-7xl">
          <Outlet />
        </div>
      </main>

      {/* Botón flotante: registrar */}
      <AddTransactionButton />

      {/* Tab bar (móvil) */}
      <nav className="material-bar fixed inset-x-0 bottom-0 z-40 border-t pb-[env(safe-area-inset-bottom)] md:hidden">
        <div className="mx-auto flex max-w-md items-stretch justify-around">
          {tabs.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `relative flex flex-1 flex-col items-center gap-0.5 py-2 text-[10px] font-medium transition-colors ${
                  isActive ? "text-primary" : "text-muted-foreground"
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <span className="relative px-4 py-0.5">
                    {isActive && (
                      <motion.span
                        layoutId="tab-active"
                        transition={springIndicator}
                        className="absolute inset-0 rounded-full bg-primary/12"
                      />
                    )}
                    <Icon size={22} className="relative" strokeWidth={isActive ? 2.4 : 2} />
                  </span>
                  {label}
                </>
              )}
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  )
}
