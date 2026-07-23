import { useState, type FormEvent } from "react"
import { useNavigate } from "react-router-dom"
import { Wallet } from "lucide-react"
import { motion } from "motion/react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useAuth } from "@/lib/auth"
import { springAppear } from "@/lib/springs"

/**
 * Login. Pública (sin app shell). Mock: acepta cualquier credencial;
 * el backend traerá email+password con JWT.
 */
export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!email || !password) return
    login(email, password)
    navigate("/", { replace: true })
  }

  return (
    <div className="flex min-h-dvh flex-col items-center justify-center px-4">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={springAppear}
        className="w-full max-w-sm"
      >
        {/* Marca */}
        <div className="mb-8 flex flex-col items-center gap-3">
          <span className="flex size-16 items-center justify-center rounded-[22px] bg-primary text-primary-foreground shadow-lg shadow-primary/30">
            <Wallet size={30} strokeWidth={2.2} />
          </span>
          <div className="text-center">
            <h1 className="text-[28px] font-bold tracking-tight">
              Finanzas Familiares
            </h1>
            <p className="mt-1 text-[15px] text-muted-foreground">
              El dinero de tu hogar, en un solo lugar
            </p>
          </div>
        </div>

        {/* Formulario */}
        <form
          onSubmit={onSubmit}
          className="flex flex-col gap-4 rounded-3xl bg-card p-6 shadow-sm"
        >
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
              autoComplete="current-password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="h-11 rounded-xl"
              required
            />
          </div>
          <Button
            type="submit"
            size="lg"
            className="pressable mt-1 h-12 rounded-2xl text-[16px] font-semibold"
          >
            Entrar
          </Button>
        </form>

        <p className="mt-4 text-center text-[13px] text-muted-foreground">
          ¿Te invitaron a un hogar? Usa el link de invitación para crear tu
          cuenta.
        </p>
        <p className="mt-2 text-center text-[12px] text-muted-foreground/70">
          Demo: cualquier correo y contraseña funcionan
        </p>
      </motion.div>
    </div>
  )
}
