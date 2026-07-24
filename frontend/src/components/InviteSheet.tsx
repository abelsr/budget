import { useEffect, useRef, useState } from "react"
import { Check, Copy, Link2, RefreshCw, Share2 } from "lucide-react"
import { motion } from "motion/react"

import { Button } from "@/components/ui/button"
import {
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer"
import { ApiError } from "@/lib/api"
import { copyText } from "@/lib/clipboard"
import { useCreateInvitation, type Invitation } from "@/lib/queries"
import { springAppear } from "@/lib/springs"

interface InviteSheetProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

/** Bottom sheet para generar y compartir un link de invitación al hogar. */
export function InviteSheet({ open, onOpenChange }: InviteSheetProps) {
  return (
    <Drawer open={open} onOpenChange={onOpenChange} showSwipeHandle>
      <DrawerContent className="mx-auto max-w-lg">
        {open && <InviteBody />}
      </DrawerContent>
    </Drawer>
  )
}

const expiryFmt = new Intl.DateTimeFormat("es-MX", {
  day: "numeric",
  month: "long",
})

function InviteBody() {
  const createInvitation = useCreateInvitation()
  const [invitation, setInvitation] = useState<Invitation | null>(null)
  const [copied, setCopied] = useState(false)
  const [copyFailed, setCopyFailed] = useState(false)
  const requested = useRef(false)

  // Un link se genera al abrir el sheet; "Generar otro" crea uno nuevo.
  useEffect(() => {
    if (requested.current) return
    requested.current = true
    createInvitation.mutate(undefined, { onSuccess: setInvitation })
  }, [createInvitation])

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

  function onRegenerate() {
    setInvitation(null)
    setCopied(false)
    setCopyFailed(false)
    createInvitation.mutate(undefined, { onSuccess: setInvitation })
  }

  const canShare = typeof navigator.share === "function"

  return (
    <div className="flex flex-col gap-5 px-5 pb-8">
      <DrawerHeader className="p-0 pt-2">
        <DrawerTitle className="text-center text-[17px] font-semibold">
          Invitar al hogar
        </DrawerTitle>
      </DrawerHeader>

      <p className="text-center text-[14px] leading-snug text-muted-foreground">
        Comparte este link con quien quieras sumar. Al abrirlo podrá crear su
        cuenta y entrar directo a tu hogar.
      </p>

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
            Válido por 7 días (hasta el {expiresLabel}) y para una sola
            persona.
          </p>
        </motion.div>
      )}

      {copyFailed && (
        <p className="rounded-xl bg-expense/10 px-3 py-2 text-center text-[13px] text-expense">
          No se pudo copiar automáticamente. Selecciona el link y cópialo a
          mano.
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
          onClick={onRegenerate}
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
