import { useCallback, useEffect, useRef, useState } from "react"
import { Check, Copy, Link2, RefreshCw, Share2, UserPlus } from "lucide-react"
import { motion } from "motion/react"

import { Button } from "@/components/ui/button"
import { ApiError } from "@/lib/api"
import { copyText } from "@/lib/clipboard"
import { useCreateInvitation, type Invitation } from "@/lib/queries"
import { springAppear } from "@/lib/springs"

const expiryFmt = new Intl.DateTimeFormat("es-MX", {
  day: "numeric",
  month: "long",
})

interface InviteLinkProps {
  /** Genera el link al montar. En el sheet, abrirlo ya es el gesto del usuario;
   *  en el wizard preferimos un botón explícito para no crear invitaciones
   *  sueltas cada vez que se pasa por el paso. */
  autoGenerate?: boolean
  /** Se llama cuando hay un link disponible (para resúmenes en el wizard). */
  onGenerated?: () => void
}

/**
 * Genera un link de invitación al hogar y ofrece copiarlo o compartirlo.
 * Compartido por Ajustes (dentro de `InviteSheet`) y el wizard de onboarding.
 */
export function InviteLink({ autoGenerate = false, onGenerated }: InviteLinkProps) {
  const createInvitation = useCreateInvitation()
  const { mutate: createInvite } = createInvitation
  const [invitation, setInvitation] = useState<Invitation | null>(null)
  const [copied, setCopied] = useState(false)
  const [copyFailed, setCopyFailed] = useState(false)
  const autoRequested = useRef(false)

  const generate = useCallback(() => {
    setCopied(false)
    setCopyFailed(false)
    createInvite(undefined, {
      onSuccess: (created) => {
        setInvitation(created)
        onGenerated?.()
      },
    })
  }, [createInvite, onGenerated])

  // El ref evita un segundo POST, tanto con el doble montaje de StrictMode como
  // si `generate` cambia de identidad porque el padre pasa un `onGenerated` nuevo.
  useEffect(() => {
    if (!autoGenerate || autoRequested.current) return
    autoRequested.current = true
    generate()
  }, [autoGenerate, generate])

  const inviteLink = invitation
    ? new URL(invitation.inviteUrl, window.location.origin).toString()
    : null
  const expiresLabel = invitation
    ? expiryFmt.format(new Date(invitation.expiresAt))
    : null

  const errorMessage =
    createInvitation.error instanceof ApiError
      ? createInvitation.error.message
      : createInvitation.error
        ? "No se pudo generar el link de invitación"
        : null

  async function onCopy() {
    if (!inviteLink) return
    const ok = await copyText(inviteLink)
    setCopyFailed(!ok)
    if (!ok) return
    setCopied(true)
    window.setTimeout(() => setCopied(false), 2000)
  }

  async function onShare() {
    if (!inviteLink) return
    try {
      await navigator.share({
        title: "Únete a nuestro hogar",
        text: "Te invito a llevar las finanzas de la casa conmigo:",
        url: inviteLink,
      })
    } catch {
      // el usuario canceló el sheet nativo: no es un error
    }
  }

  const canShare = typeof navigator.share === "function"

  // Estado inicial sin autoGenerate: un solo botón.
  if (!inviteLink && !createInvitation.isPending && !errorMessage) {
    return (
      <Button
        size="lg"
        onClick={generate}
        className="pressable h-12 w-full rounded-2xl text-[15px] font-semibold"
      >
        <UserPlus size={17} />
        Generar link de invitación
      </Button>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      {errorMessage ? (
        <p className="rounded-xl bg-expense/10 px-3 py-2 text-center text-[13px] text-expense">
          {errorMessage}
        </p>
      ) : !inviteLink ? (
        <div className="h-[46px] animate-pulse rounded-xl bg-secondary" />
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={springAppear}
          className="flex flex-col gap-2"
        >
          <div className="flex items-center gap-2 rounded-xl bg-secondary px-3 py-3">
            <Link2 size={16} className="shrink-0 text-muted-foreground" />
            <input
              readOnly
              value={inviteLink}
              onFocus={(e) => e.currentTarget.select()}
              className="w-full bg-transparent text-[13px] outline-none"
              aria-label="Link de invitación"
            />
          </div>
          <p className="px-1 text-[12px] text-muted-foreground">
            Válido por 7 días (hasta el {expiresLabel}) y para una sola persona.
          </p>
        </motion.div>
      )}

      {copyFailed && (
        <p className="rounded-xl bg-expense/10 px-3 py-2 text-center text-[13px] text-expense">
          No se pudo copiar automáticamente. Selecciona el link y cópialo a mano.
        </p>
      )}

      <div className="flex flex-col gap-2">
        <Button
          size="lg"
          disabled={!inviteLink}
          onClick={onCopy}
          className="pressable h-12 rounded-2xl text-[16px] font-semibold"
        >
          {copied ? <Check size={18} /> : <Copy size={18} />}
          {copied ? "Copiado" : "Copiar link"}
        </Button>

        {canShare && (
          <Button
            size="lg"
            variant="secondary"
            disabled={!inviteLink}
            onClick={onShare}
            className="pressable h-12 rounded-2xl text-[15px] font-semibold"
          >
            <Share2 size={17} />
            Compartir
          </Button>
        )}

        <button
          type="button"
          onClick={generate}
          disabled={createInvitation.isPending}
          className="pressable flex h-11 items-center justify-center gap-2 rounded-2xl text-[14px] font-medium text-muted-foreground disabled:opacity-50"
        >
          <RefreshCw size={15} />
          {createInvitation.isPending ? "Generando…" : "Generar otro link"}
        </button>
      </div>
    </div>
  )
}
