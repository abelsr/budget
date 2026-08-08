import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import {
  BadgeDollarSign,
  FileUp,
  ChevronRight,
  LogOut,
  Monitor,
  Moon,
  Palette,
  Repeat,
  Sun,
  Tags,
  UserRound,
  Users,
} from "lucide-react"
import { motion } from "motion/react"

import { HouseholdMembersSheet } from "@/components/HouseholdMembersSheet"
import { ProfileAvatar } from "@/components/ProfileAvatar"
import { ProfileSettingsSheet } from "@/components/ProfileSettingsSheet"
import { useAuth } from "@/lib/auth"
import { useHousehold, useMembers } from "@/lib/queries"
import { useTheme, type Theme } from "@/lib/theme"
import { springAppear, springIndicator } from "@/lib/springs"
import { SectionTitle } from "@/components/ui/surface"

/** Nombre largo de las monedas que ya soporta el hogar; si no, se usa el código. */
const currencyNames: Record<string, string> = {
  MXN: "Peso mexicano",
  USD: "Dólar estadounidense",
  EUR: "Euro",
}

const themeOptions: { value: Theme; label: string; icon: typeof Sun }[] = [
  { value: "light", label: "Claro", icon: Sun },
  { value: "dark", label: "Oscuro", icon: Moon },
  { value: "system", label: "Sistema", icon: Monitor },
]

/** Ajustes: acciones soportadas agrupadas en una lista compacta. */
export function SettingsPage() {
  const { session, logout } = useAuth()
  const { theme, setTheme } = useTheme()
  const { data: members = [] } = useMembers()
  const { data: household } = useHousehold()
  const navigate = useNavigate()
  const [membersOpen, setMembersOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)

  function onLogout() {
    logout()
    navigate("/login", { replace: true })
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springAppear}
      className="mx-auto flex w-full max-w-xl flex-col gap-5 pb-4"
    >
      <header className="flex min-h-11 items-center justify-center px-1">
        <h1 className="text-xl font-bold tracking-tight sm:text-[28px]">Ajustes</h1>
      </header>

      <Section>
        <div className="flex items-center gap-3 px-4 py-3.5">
          <ProfileAvatar name={session?.name ?? "Mi perfil"} hasAvatar={session?.hasAvatar ?? false} avatarUpdatedAt={session?.avatarUpdatedAt ?? null} className="size-11 rounded-full bg-primary/10 text-[15px] font-semibold text-primary" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-[15px] font-semibold">{session?.name}</p>
            <p className="truncate text-[12px] text-muted-foreground">{session?.email}</p>
          </div>
        </div>
        <Row icon={<UserRound size={16} />} label="Mi cuenta" onClick={() => setProfileOpen(true)} />
        <Row
          icon={<Users size={16} />}
          label="Miembros del hogar"
          value={members.length ? `${members.length}` : undefined}
          onClick={() => setMembersOpen(true)}
        />
        <Row icon={<Tags size={16} />} label="Categorías" to="/app/ajustes/categorias" />
        <Row icon={<Tags size={16} />} label="Reglas de comercios" to="/app/ajustes/reglas-de-comercios" />
        <Row icon={<Repeat size={16} />} label="Recurrentes" to="/app/ajustes/recurrentes" />
        <Row icon={<FileUp size={16} />} label="Importar movimientos" to="/app/importar" />
        <ThemeRow theme={theme} setTheme={setTheme} />
        <Row
          icon={<BadgeDollarSign size={16} />}
          label="Moneda del hogar"
          value={household?.currencyCode ?? "—"}
          detail={currencyNames[household?.currencyCode ?? ""]}
          last
        />
      </Section>

      <Section>
        <button
          onClick={onLogout}
          className="pressable flex w-full items-center justify-center gap-2 px-4 py-3.5 text-[15px] font-semibold text-expense"
        >
          <LogOut size={16} />
          Cerrar sesión
        </button>
      </Section>

      <p className="text-center text-[12px] text-muted-foreground">
        budget · v0.1.0 · autohospedado
      </p>

      <HouseholdMembersSheet open={membersOpen} onOpenChange={setMembersOpen} />
      <ProfileSettingsSheet open={profileOpen} onOpenChange={setProfileOpen} />
    </motion.div>
  )
}

function Section({
  title,
  children,
}: {
  title?: string
  children: React.ReactNode
}) {
  return (
    <section>
      {title && <SectionTitle>{title}</SectionTitle>}
      <div className="overflow-hidden rounded-3xl border border-border bg-card shadow-sm">
        {children}
      </div>
    </section>
  )
}

function Row({
  icon,
  label,
  value,
  disabled,
  last,
  to,
  onClick,
  detail,
}: {
  icon: React.ReactNode
  label: string
  value?: string
  disabled?: boolean
  last?: boolean
  to?: string
  onClick?: () => void
  detail?: string
}) {
  const className = `flex w-full items-center gap-3 px-4 py-3 text-left ${
    !last ? "border-b border-border" : ""
  } ${disabled ? "opacity-50" : "pressable"}`
  const content = (
    <>
      <span className="flex size-9 items-center justify-center rounded-full bg-secondary text-secondary-foreground">
        {icon}
      </span>
      <span className="flex min-w-0 flex-1 flex-col">
        <span className="text-[15px] font-medium">{label}</span>
        {detail && <span className="text-[11px] text-muted-foreground">{detail}</span>}
      </span>
      {value && <span className="tnum text-[13px] text-muted-foreground">{value}</span>}
      {(to || onClick) && <ChevronRight size={16} className="text-muted-foreground/50" />}
    </>
  )
  if (to) {
    return (
      <Link to={to} className={className}>
        {content}
      </Link>
    )
  }
  if (!onClick && !disabled) {
    return <div className={className}>{content}</div>
  }
  return (
    <button type="button" disabled={disabled} onClick={onClick} className={className}>
      {content}
    </button>
  )
}

function ThemeRow({
  theme,
  setTheme,
}: {
  theme: Theme
  setTheme: (theme: Theme) => void
}) {
  return (
    <div className="border-b border-border px-4 py-3">
      <div className="flex items-center gap-3">
        <span className="flex size-9 items-center justify-center rounded-full bg-secondary text-secondary-foreground">
          <Palette size={16} />
        </span>
        <span className="flex-1 text-[15px] font-medium">Preferencias</span>
      </div>
      <div className="mt-3 flex rounded-xl bg-secondary p-1" aria-label="Tema de la aplicación">
        {themeOptions.map(({ value, label, icon: Icon }) => {
          const active = theme === value
          return (
            <button
              key={value}
              type="button"
              onClick={() => setTheme(value)}
              aria-pressed={active}
              className="relative flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2 text-[12px] font-medium"
            >
              {active && (
                <motion.span
                  layoutId="theme-segment"
                  transition={springIndicator}
                  className="absolute inset-0 rounded-lg bg-card shadow-sm"
                />
              )}
              <Icon size={14} className={`relative ${active ? "text-foreground" : "text-muted-foreground"}`} />
              <span className={`relative ${active ? "text-foreground" : "text-muted-foreground"}`}>{label}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
