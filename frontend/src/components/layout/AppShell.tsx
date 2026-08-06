import { Link, NavLink, Outlet } from "react-router-dom"
import {
  ArrowLeftRight,
  Bell,
  ChevronsUpDown,
  FolderCog,
  LayoutDashboard,
  Settings,
  Tags,
  UserRound,
  Wallet,
} from "lucide-react"
import type { LucideIcon } from "lucide-react"
import { motion } from "motion/react"

import { springIndicator } from "@/lib/springs"
import { useHousehold, useMembers } from "@/lib/queries"
import { useAuth } from "@/lib/auth"
import { AddTransactionButton } from "@/components/AddTransactionSheet"
import { BrandMark } from "@/components/BrandMark"
import { ProfileAvatar } from "@/components/ProfileAvatar"
import { useOffline } from "@/lib/offline"

type NavigationItem = {
  label: string
  icon: LucideIcon
  to?: string
  disabled?: boolean
}

const mobileTabs: Array<NavigationItem & { to: string }> = [
  { to: "/app", label: "Resumen", icon: LayoutDashboard },
  { to: "/app/transacciones", label: "Movimientos", icon: ArrowLeftRight },
  { to: "/app/cuentas", label: "Cuentas", icon: Wallet },
  { to: "/app/ajustes", label: "Ajustes", icon: Settings },
]

const desktopTabs: NavigationItem[] = [
  ...mobileTabs.slice(0, 3),
  { to: "/app/ajustes/categorias", label: "Categorías", icon: Tags },
  { to: "/app/reportes", label: "Reportes", icon: FolderCog },
  mobileTabs[3]!,
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
  const { session } = useAuth()
  const { online, pending, cacheUpdatedAt } = useOffline()
  const householdName = householdError
    ? "Mi hogar"
    : (household?.name ?? "…")
  const profileName = session?.name ?? members[0]?.name ?? "Mi perfil"
  const profileEmail = session?.email ?? ""
  return (
    <div className="min-h-dvh">
      {/* Sidebar (desktop) */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-52 flex-col border-r bg-sidebar md:flex">
        <div className="px-6 pt-5">
          <BrandMark size={28} />
        </div>
        <nav aria-label="Navegación principal" className="mt-5 flex flex-col gap-1 px-3">
          {desktopTabs.map(({ to, label, icon: Icon, disabled }) =>
            disabled ? (
              <span
                key={label}
                aria-disabled="true"
                className="flex cursor-not-allowed items-center gap-3 rounded-md px-3 py-2 text-[12px] font-medium text-muted-foreground/60"
              >
                <Icon size={16} />
                {label}
              </span>
            ) : (
              <NavLink
                key={to}
                to={to!}
                end={to === "/app" || to === "/app/ajustes"}
                className={({ isActive }) =>
                  `pressable relative flex items-center gap-3 rounded-md px-3 py-2 text-[12px] font-medium transition-colors ${
                    isActive
                      ? "text-primary"
                      : "text-sidebar-foreground/80 hover:bg-sidebar-accent"
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    {isActive && (
                      <motion.span
                        layoutId="sidebar-active"
                        transition={springIndicator}
                        className="absolute inset-0 rounded-md bg-primary-soft"
                      />
                    )}
                    <Icon size={16} className="relative" />
                    <span className="relative">{label}</span>
                  </>
                )}
              </NavLink>
            ),
          )}
        </nav>

        <div className="mt-auto border-t px-3 py-4">
          <div
            className="pressable flex w-full items-center gap-2 rounded-md border bg-card px-3 py-2 text-left text-[11px] font-medium text-sidebar-foreground shadow-sm"
            aria-label={`Hogar activo: ${householdName}`}
          >
            <span className="flex size-5 items-center justify-center rounded bg-primary-soft text-primary">
              <UserRound size={13} />
            </span>
            <span className="min-w-0 flex-1 truncate">{householdName}</span>
            <ChevronsUpDown size={14} className="text-muted-foreground" aria-hidden="true" />
          </div>
          <Link to="/app/ajustes" className="pressable mt-5 flex items-center gap-2 rounded-md px-2 py-1" aria-label="Abrir ajustes de mi cuenta">
            <ProfileAvatar name={profileName} hasAvatar={session?.hasAvatar ?? false} avatarUpdatedAt={session?.avatarUpdatedAt ?? null} className="size-7 shrink-0 rounded-full bg-secondary text-[10px] font-semibold text-secondary-foreground" />
            <div className="min-w-0">
              <p className="truncate text-[11px] font-medium">{profileName}</p>
              {profileEmail && (
                <p className="truncate text-[10px] text-muted-foreground">{profileEmail}</p>
              )}
            </div>
          </Link>
        </div>
      </aside>

      {/* Contenido */}
      <main className="pb-28 md:pb-10 md:pl-52">
        {(!online || pending.length > 0) && <OfflineBanner online={online} pending={pending.length} cacheUpdatedAt={cacheUpdatedAt} />}
        <header className="hidden h-15 items-center justify-end border-b bg-card/80 px-8 backdrop-blur-sm md:flex">
          <span
            role="status"
            aria-label="Notificaciones pendientes"
            className="pressable relative mr-28 flex size-8 items-center justify-center rounded-full text-muted-foreground hover:bg-secondary hover:text-foreground"
          >
            <Bell size={18} />
            <span className="absolute right-1 top-1 size-1.5 rounded-full bg-destructive" aria-hidden="true" />
          </span>
        </header>
        <div className="mx-auto w-full max-w-2xl px-4 pt-6 md:max-w-3xl md:pt-7 lg:max-w-6xl lg:px-8 2xl:max-w-7xl">
          <Outlet />
        </div>
      </main>

      {/* Un solo drawer conserva el estado entre los triggers móvil y desktop. */}
      <AddTransactionButton />

      {/* Tab bar (móvil) */}
      <nav className="material-bar fixed inset-x-0 bottom-0 z-40 border-t pb-[env(safe-area-inset-bottom)] md:hidden">
        <div className="mx-auto flex max-w-md items-stretch justify-around">
          {mobileTabs.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/app" || to === "/app/ajustes"}
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

function OfflineBanner({ online, pending, cacheUpdatedAt }: { online: boolean; pending: number; cacheUpdatedAt: number }) {
  const age = cacheUpdatedAt ? Math.max(0, Math.floor((Date.now() - cacheUpdatedAt) / 60_000)) : null
  const ageLabel = age === null ? "sin datos guardados" : age < 1 ? "datos actualizados ahora" : `datos de hace ${age} min`
  return <div role="status" className="sticky top-0 z-30 border-b border-amber-500/30 bg-amber-50 px-4 py-2 text-center text-[12px] font-medium text-amber-950 dark:bg-amber-950/40 dark:text-amber-100">{!online ? `Sin conexión${pending ? ` · ${pending} ${pending === 1 ? "movimiento pendiente" : "movimientos pendientes"}` : ""} · ${ageLabel}` : `${pending} ${pending === 1 ? "movimiento pendiente de subir" : "movimientos pendientes de subir"}`}</div>
}
