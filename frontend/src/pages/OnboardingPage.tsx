import { useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  ArrowLeft,
  ArrowRight,
  Check,
  CreditCard,
  Landmark,
  PartyPopper,
  PiggyBank,
  Plus,
  ScanLine,
  Users,
  Wallet,
} from "lucide-react"
import { AnimatePresence, motion } from "motion/react"

import { InviteLink } from "@/components/InviteLink"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/lib/auth"
import { formatMoney } from "@/lib/format"
import { useAccounts, useCreateAccount } from "@/lib/queries"
import { springAppear, springDefault } from "@/lib/springs"
import type { AccountKind } from "@/lib/types"

/**
 * Wizard inicial (estilo Plane): bienvenida → cuentas → invitar → listo.
 * Solo lo ve quien se registra creando un hogar nuevo; al terminar (o saltar)
 * se marca el flag en el backend y no vuelve a aparecer.
 */
const STEPS = ["Bienvenida", "Cuentas", "Familia", "Listo"] as const

export function OnboardingPage() {
  const { session, completeOnboarding } = useAuth()
  const navigate = useNavigate()

  const [step, setStep] = useState(0)
  /** Dirección del último movimiento: entrar y salir por el mismo camino. */
  const [direction, setDirection] = useState(1)
  const [invited, setInvited] = useState(false)
  const [finishing, setFinishing] = useState(false)

  const { data: accounts = [] } = useAccounts()

  function go(next: number) {
    setDirection(next > step ? 1 : -1)
    setStep(next)
  }

  async function finish() {
    setFinishing(true)
    try {
      await completeOnboarding()
      navigate("/", { replace: true })
    } catch {
      // Si falla el PATCH, dejamos al usuario reintentar en vez de encerrarlo
      setFinishing(false)
    }
  }

  return (
    <div className="flex min-h-dvh flex-col px-4 py-6">
      {/* Progreso + salir */}
      <header className="mx-auto flex w-full max-w-md items-center gap-3">
        <div className="flex flex-1 items-center gap-1.5">
          {STEPS.map((label, i) => (
            <span
              key={label}
              aria-label={label}
              aria-current={i === step ? "step" : undefined}
              className="relative h-1 flex-1 overflow-hidden rounded-full bg-secondary"
            >
              <motion.span
                initial={false}
                animate={{ scaleX: i <= step ? 1 : 0 }}
                transition={springDefault}
                style={{ originX: 0 }}
                className="absolute inset-0 rounded-full bg-primary"
              />
            </span>
          ))}
        </div>
        <button
          onClick={finish}
          disabled={finishing}
          className="pressable shrink-0 text-[13px] font-medium text-muted-foreground disabled:opacity-50"
        >
          Configurar después
        </button>
      </header>

      {/* Paso actual */}
      <div className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center py-8">
        <AnimatePresence mode="wait" initial={false} custom={direction}>
          <motion.div
            key={step}
            custom={direction}
            initial={{ opacity: 0, x: direction * 24 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: direction * -24 }}
            transition={springAppear}
          >
            {step === 0 && <WelcomeStep name={session?.name ?? ""} />}
            {step === 1 && <AccountsStep />}
            {step === 2 && (
              <InviteStep onGenerated={() => setInvited(true)} />
            )}
            {step === 3 && (
              <DoneStep accountCount={accounts.length} invited={invited} />
            )}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Navegación */}
      <footer className="mx-auto flex w-full max-w-md items-center gap-3">
        {step > 0 && (
          <Button
            variant="secondary"
            size="lg"
            onClick={() => go(step - 1)}
            aria-label="Paso anterior"
            className="pressable h-12 w-12 shrink-0 rounded-2xl"
          >
            <ArrowLeft size={18} />
          </Button>
        )}
        {step < STEPS.length - 1 ? (
          <Button
            size="lg"
            onClick={() => go(step + 1)}
            className="pressable h-12 flex-1 rounded-2xl text-[16px] font-semibold"
          >
            Continuar
            <ArrowRight size={18} />
          </Button>
        ) : (
          <Button
            size="lg"
            onClick={finish}
            disabled={finishing}
            className="pressable h-12 flex-1 rounded-2xl text-[16px] font-semibold"
          >
            {finishing ? "Un momento…" : "Empezar"}
          </Button>
        )}
      </footer>
    </div>
  )
}

function StepHeader({
  icon,
  title,
  subtitle,
}: {
  icon: React.ReactNode
  title: string
  subtitle: string
}) {
  return (
    <div className="mb-6 flex flex-col items-center gap-3 text-center">
      <span className="surface-brand flex size-16 items-center justify-center rounded-[22px] shadow-lg">
        {icon}
      </span>
      <div>
        <h1 className="text-[26px] leading-tight font-bold tracking-tight">
          {title}
        </h1>
        <p className="mt-1.5 text-[15px] leading-snug text-muted-foreground">
          {subtitle}
        </p>
      </div>
    </div>
  )
}

function WelcomeStep({ name }: { name: string }) {
  const firstName = name.trim().split(/\s+/)[0] ?? ""
  const bullets = [
    {
      icon: <Wallet size={18} />,
      title: "Registra en segundos",
      text: "Monto, categoría y cuenta. Nada más.",
    },
    {
      icon: <ScanLine size={18} />,
      title: "Escanea tus tickets",
      text: "Toma la foto y la IA llena el gasto por ti.",
    },
    {
      icon: <Users size={18} />,
      title: "Todo el hogar, junto",
      text: "Cada quien registra y todos ven lo mismo.",
    },
  ]

  return (
    <div>
      <StepHeader
        icon={<PartyPopper size={30} strokeWidth={2.2} />}
        title={firstName ? `Bienvenido, ${firstName}` : "Bienvenido"}
        subtitle="Vamos a dejar tu hogar listo en menos de un minuto."
      />
      <ul className="flex flex-col gap-2">
        {bullets.map((b) => (
          <li
            key={b.title}
            className="flex items-start gap-3 rounded-2xl border border-border bg-card p-4 shadow-sm"
          >
            <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
              {b.icon}
            </span>
            <div className="min-w-0">
              <p className="text-[15px] font-semibold">{b.title}</p>
              <p className="text-[13px] text-muted-foreground">{b.text}</p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}

const kindOptions: { kind: AccountKind; label: string; icon: typeof Wallet }[] = [
  { kind: "cash", label: "Efectivo", icon: Wallet },
  { kind: "debit", label: "Débito", icon: Landmark },
  { kind: "credit", label: "Crédito", icon: CreditCard },
  { kind: "savings", label: "Ahorro", icon: PiggyBank },
]

function AccountsStep() {
  // Se leen las cuentas del backend, así que recargar a mitad del wizard no
  // duplica nada: "Efectivo" (creada al registrarse) aparece ya en la lista.
  const { data: accounts = [] } = useAccounts()
  const createAccount = useCreateAccount()

  const [adding, setAdding] = useState(false)
  const [name, setName] = useState("")
  const [kind, setKind] = useState<AccountKind>("debit")
  const [balanceText, setBalanceText] = useState("0")

  function reset() {
    setAdding(false)
    setName("")
    setKind("debit")
    setBalanceText("0")
  }

  function save() {
    if (!name.trim() || createAccount.isPending) return
    createAccount.mutate(
      {
        name: name.trim(),
        kind,
        openingBalance: Number(balanceText.replace(",", ".")) || 0,
      },
      { onSuccess: reset },
    )
  }

  return (
    <div>
      <StepHeader
        icon={<Wallet size={30} strokeWidth={2.2} />}
        title="Tus cuentas"
        subtitle="¿Dónde está tu dinero? Agrega tu débito, crédito o ahorro con su saldo actual."
      />

      <ul className="mb-2 flex flex-col gap-2">
        {accounts.map((account) => {
          const meta =
            kindOptions.find((k) => k.kind === account.kind) ?? kindOptions[0]!
          const Icon = meta.icon
          return (
            <motion.li
              key={account.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={springAppear}
              className="flex items-center gap-3 rounded-2xl border border-border bg-card p-3.5 shadow-sm"
            >
              <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-secondary text-secondary-foreground">
                <Icon size={17} />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-[15px] font-medium">{account.name}</p>
                <p className="text-[12px] text-muted-foreground">{meta.label}</p>
              </div>
              <p className="tnum text-[15px] font-semibold">
                {formatMoney(account.balance)}
              </p>
            </motion.li>
          )
        })}
      </ul>

      {adding ? (
        <div className="flex flex-col gap-3 rounded-2xl border border-border bg-card p-4 shadow-sm">
          <input
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Nombre (ej. Nómina BBVA)"
            className="w-full rounded-xl bg-secondary px-4 py-2.5 text-[15px] outline-none placeholder:text-muted-foreground"
            aria-label="Nombre de la cuenta"
          />
          <div className="grid grid-cols-2 gap-2">
            {kindOptions.map(({ kind: k, label, icon: Icon }) => (
              <button
                key={k}
                type="button"
                onClick={() => setKind(k)}
                className={`pressable flex items-center gap-2 rounded-xl px-3 py-2.5 text-[14px] font-medium transition-colors ${
                  kind === k
                    ? "bg-primary text-primary-foreground"
                    : "bg-secondary text-secondary-foreground"
                }`}
              >
                <Icon size={17} />
                {label}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[13px] text-muted-foreground">Saldo</span>
            <input
              inputMode="decimal"
              value={balanceText}
              onChange={(e) =>
                setBalanceText(e.target.value.replace(/[^0-9.,-]/g, ""))
              }
              className="tnum flex-1 rounded-xl bg-secondary px-4 py-2.5 text-[15px] outline-none"
              aria-label="Saldo inicial"
            />
          </div>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              onClick={reset}
              className="pressable h-11 flex-1 rounded-xl text-[15px] font-medium"
            >
              Cancelar
            </Button>
            <Button
              onClick={save}
              disabled={!name.trim() || createAccount.isPending}
              className="pressable h-11 flex-1 rounded-xl text-[15px] font-semibold"
            >
              {createAccount.isPending ? "Guardando…" : "Agregar"}
            </Button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setAdding(true)}
          className="pressable flex w-full items-center justify-center gap-2 rounded-2xl border border-dashed border-border py-3.5 text-[15px] font-medium text-muted-foreground"
        >
          <Plus size={17} />
          Agregar cuenta
        </button>
      )}
    </div>
  )
}

function InviteStep({ onGenerated }: { onGenerated: () => void }) {
  return (
    <div>
      <StepHeader
        icon={<Users size={30} strokeWidth={2.2} />}
        title="Invita a tu familia"
        subtitle="Comparte un link para que se unan a este hogar. También puedes hacerlo después desde Ajustes."
      />
      <InviteLink onGenerated={onGenerated} />
    </div>
  )
}

function DoneStep({
  accountCount,
  invited,
}: {
  accountCount: number
  invited: boolean
}) {
  const items = [
    `${accountCount} ${accountCount === 1 ? "cuenta lista" : "cuentas listas"}`,
    "10 categorías para clasificar tus gastos",
    invited ? "Invitación lista para compartir" : "Invitación pendiente (Ajustes > Hogar)",
  ]

  return (
    <div>
      <StepHeader
        icon={<Check size={30} strokeWidth={2.6} />}
        title="Todo listo"
        subtitle="Tu hogar ya puede registrar movimientos."
      />
      <ul className="flex flex-col gap-2">
        {items.map((item) => (
          <li
            key={item}
            className="flex items-center gap-3 rounded-2xl border border-border bg-card p-3.5 shadow-sm"
          >
            <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-income/15 text-income">
              <Check size={15} strokeWidth={2.6} />
            </span>
            <p className="text-[15px] font-medium">{item}</p>
          </li>
        ))}
      </ul>
      <p className="mt-5 text-center text-[13px] text-muted-foreground">
        Empieza registrando tu último gasto con el botón + del dashboard.
      </p>
    </div>
  )
}
