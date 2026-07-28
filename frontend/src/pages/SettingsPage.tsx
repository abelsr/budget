import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import {
  ChevronRight,
  LogOut,
  Monitor,
  Moon,
  Repeat,
  ScanLine,
  Sun,
  Tags,
  UserPlus,
} from "lucide-react"
import { motion } from "motion/react"

import { InviteSheet } from "@/components/InviteSheet"
import { useAuth } from "@/lib/auth"
import { useHousehold, useMembers } from "@/lib/queries"
import { useTheme, type Theme } from "@/lib/theme"
import { springAppear, springIndicator } from "@/lib/springs"
import { PageHeader, SectionTitle } from "@/components/ui/surface"

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

/** Ajustes: cuenta, apariencia, hogar y preferencias. Estilo lista iOS. */
export function SettingsPage() {
  const { session, logout } = useAuth()
  const { theme, setTheme } = useTheme()
  const { data: members = [] } = useMembers()
  const { data: household } = useHousehold()
  const navigate = useNavigate()
  const [inviteOpen, setInviteOpen] = useState(false)

  function onLogout() {
    logout()
    navigate("/login", { replace: true })
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springAppear}
      className="flex max-w-2xl flex-col gap-5"
    >
      <PageHeader title="Ajustes" />

      {/* Cuenta */}
      <Section>
        <div className="flex items-center gap-3 px-4 py-3.5">
          <span className="flex size-12 items-center justify-center rounded-full bg-primary/10 text-[15px] font-semibold text-primary">
            {session?.name.charAt(0).toUpperCase() ?? "?"}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-[16px] font-semibold">{session?.name}</p>
            <p className="truncate text-[13px] text-muted-foreground">
              {session?.email}
            </p>
          </div>
        </div>
      </Section>

      {/* Apariencia */}
      <Section title="Apariencia">
        <div className="px-4 py-3.5">
          <div className="flex rounded-xl bg-secondary p-1">
            {themeOptions.map(({ value, label, icon: Icon }) => {
              const active = theme === value
              return (
                <button
                  key={value}
                  onClick={() => setTheme(value)}
                  className="relative flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2 text-[13px] font-medium"
                >
                  {active && (
                    <motion.span
                      layoutId="theme-segment"
                      transition={springIndicator}
                      className="absolute inset-0 rounded-lg bg-card shadow-sm"
                    />
                  )}
                  <Icon
                    size={15}
                    className={`relative ${active ? "text-foreground" : "text-muted-foreground"}`}
                  />
                  <span
                    className={`relative ${active ? "text-foreground" : "text-muted-foreground"}`}
                  >
                    {label}
                  </span>
                </button>
              )
            })}
          </div>
        </div>
      </Section>

      {/* Hogar */}
      <Section title="Hogar">
        {members.map((m, i) => (
          <div
            key={m.id}
            className={`flex items-center gap-3 px-4 py-3 ${
              i > 0 ? "border-t border-border" : ""
            }`}
          >
            <span className="flex size-9 items-center justify-center rounded-full bg-primary/10 text-[12px] font-semibold text-primary">
              {m.initials}
            </span>
            <p className="flex-1 text-[15px] font-medium">{m.name}</p>
            <span className="text-[12px] text-muted-foreground">
              {i === 0 ? "Administrador" : "Miembro"}
            </span>
          </div>
        ))}
        <button
          onClick={() => setInviteOpen(true)}
          className="pressable flex w-full items-center gap-3 border-t border-border px-4 py-3 text-left"
        >
          <span className="flex size-9 items-center justify-center rounded-full bg-primary/10 text-primary">
            <UserPlus size={16} />
          </span>
          <p className="flex-1 text-[15px] font-medium">Invitar miembro</p>
          <ChevronRight size={16} className="text-muted-foreground/50" />
        </button>
      </Section>

      {/* Preferencias */}
      <Section title="Preferencias">
        <Row
          icon={<Tags size={16} />}
          label="Categorías"
          to="/ajustes/categorias"
        />
        <Row
          icon={<Repeat size={16} />}
          label="Recurrentes"
          to="/ajustes/recurrentes"
        />
        <Row
          icon={<ScanLine size={16} />}
          label="Escáner con IA"
          value="Activo"
          disabled
          last
        />
      </Section>

      {/* Moneda */}
      <Section title="Moneda del hogar">
        <div className="flex items-center px-4 py-3.5">
          <p className="flex-1 text-[15px] font-medium">
            {currencyNames[household?.currencyCode ?? ""] ??
              household?.currencyCode ??
              "—"}
          </p>
          <span className="tnum text-[14px] text-muted-foreground">
            {household?.currencyCode ?? ""}
          </span>
        </div>
      </Section>

      {/* Cerrar sesión */}
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

      <InviteSheet open={inviteOpen} onOpenChange={setInviteOpen} />
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
}: {
  icon: React.ReactNode
  label: string
  value?: string
  disabled?: boolean
  last?: boolean
  to?: string
}) {
  const className = `flex w-full items-center gap-3 px-4 py-3 text-left ${
    !last ? "border-b border-border" : ""
  } ${disabled ? "opacity-50" : "pressable"}`
  const content = (
    <>
      <span className="flex size-9 items-center justify-center rounded-full bg-secondary text-secondary-foreground">
        {icon}
      </span>
      <p className="flex-1 text-[15px] font-medium">{label}</p>
      {value && <span className="text-[13px] text-muted-foreground">{value}</span>}
      {to && <ChevronRight size={16} className="text-muted-foreground/50" />}
    </>
  )
  if (to) {
    return (
      <Link to={to} className={className}>
        {content}
      </Link>
    )
  }
  return (
    <button disabled={disabled} className={className}>
      {content}
    </button>
  )
}
