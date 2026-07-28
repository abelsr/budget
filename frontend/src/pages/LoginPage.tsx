import { useState, type FormEvent } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { motion } from "motion/react"

import { BrandMark } from "@/components/BrandMark"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ApiError } from "@/lib/api"
import { useAuth } from "@/lib/auth"
import { springAppear, springIndicator } from "@/lib/springs"

type Mode = "login" | "register"

const modes: { value: Mode; label: string }[] = [
  { value: "login", label: "Entrar" },
  { value: "register", label: "Crear cuenta" },
]

/**
 * Acceso. Pública (sin app shell). Tres flujos contra el backend:
 * - Entrar: email + password (POST /auth/login)
 * - Crear cuenta: nombre, email, password y nombre del hogar (POST /auth/register)
 * - Unirse al hogar: solo con ?invite=TOKEN en la URL (POST /auth/join)
 */
export function LoginPage() {
  const { login, register, join } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const inviteToken = searchParams.get("invite")

  const [mode, setMode] = useState<Mode>("login")
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [householdName, setHouseholdName] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [isPending, setIsPending] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setIsPending(true)
    try {
      if (inviteToken) {
        await join(inviteToken, email, password, name)
      } else if (mode === "login") {
        await login(email, password)
      } else {
        await register(email, password, name, householdName)
      }
      navigate("/", { replace: true })
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "No se pudo conectar con el servidor",
      )
      setIsPending(false)
    }
  }

  const isJoin = Boolean(inviteToken)
  const submitLabel = isPending
    ? "Un momento…"
    : isJoin
      ? "Unirme al hogar"
      : mode === "login"
        ? "Entrar"
        : "Crear cuenta"

  return (
    <div className="flex min-h-dvh flex-col items-center justify-center px-4">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={springAppear}
        className="w-full max-w-sm"
      >
        {/* Marca */}
        <div className="mb-8 flex flex-col items-center gap-4">
          <BrandMark size={56} showWordmark={false} />
          <div className="text-center">
            <h1 className="text-[30px] leading-none font-bold tracking-[-0.03em]">
              budget
            </h1>
            <p className="mt-2 text-[15px] text-muted-foreground">
              El dinero de tu hogar, en un solo lugar
            </p>
          </div>
        </div>

        {/* Formulario */}
        <form
          onSubmit={onSubmit}
          className="flex flex-col gap-4 rounded-3xl border border-border bg-card p-6 shadow-sm"
        >
          {/* Segmented control estilo iOS (oculto en modo invitación) */}
          {!isJoin ? (
            <div className="flex rounded-xl bg-secondary p-1">
              {modes.map(({ value, label }) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => {
                    setMode(value)
                    setError(null)
                  }}
                  className="relative flex-1 rounded-lg px-4 py-1.5 text-[14px] font-medium"
                >
                  {mode === value && (
                    <motion.span
                      layoutId="auth-mode"
                      transition={springIndicator}
                      className="absolute inset-0 rounded-lg bg-card shadow-sm"
                    />
                  )}
                  <span
                    className={`relative ${
                      mode === value
                        ? "text-foreground"
                        : "text-muted-foreground"
                    }`}
                  >
                    {label}
                  </span>
                </button>
              ))}
            </div>
          ) : (
            <p className="rounded-xl bg-primary/10 px-3 py-2 text-center text-[13px] font-medium text-primary">
              Te unirás al hogar con tu invitación
            </p>
          )}

          {(mode === "register" || isJoin) && (
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="name" className="text-[13px]">
                Nombre
              </Label>
              <Input
                id="name"
                type="text"
                autoComplete="name"
                placeholder="Tu nombre"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="h-11 rounded-xl"
                required
              />
            </div>
          )}
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="email" className="text-[13px]">
              Correo electrónico
            </Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              placeholder="tú@familia.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="h-11 rounded-xl"
              required
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="password" className="text-[13px]">
              Contraseña
            </Label>
            <Input
              id="password"
              type="password"
              autoComplete={
                mode === "login" && !isJoin
                  ? "current-password"
                  : "new-password"
              }
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="h-11 rounded-xl"
              minLength={mode === "login" && !isJoin ? undefined : 8}
              required
            />
          </div>
          {mode === "register" && !isJoin && (
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="household" className="text-[13px]">
                Nombre del hogar
              </Label>
              <Input
                id="household"
                type="text"
                placeholder="Casa de los Pérez"
                value={householdName}
                onChange={(e) => setHouseholdName(e.target.value)}
                className="h-11 rounded-xl"
                required
              />
            </div>
          )}

          {error && (
            <p className="rounded-xl bg-expense/10 px-3 py-2 text-[13px] text-expense">
              {error}
            </p>
          )}

          <Button
            type="submit"
            size="lg"
            disabled={isPending}
            className="pressable mt-1 h-12 rounded-2xl text-[16px] font-semibold"
          >
            {submitLabel}
          </Button>
        </form>

        {!isJoin && (
          <p className="mt-4 text-center text-[13px] text-muted-foreground">
            ¿Te invitaron a un hogar? Usa el link de invitación para crear tu
            cuenta.
          </p>
        )}
      </motion.div>
    </div>
  )
}
