import { useEffect, useRef, useState, type RefObject } from "react"
import { Check, Trash2, UserPlus, Users, X } from "lucide-react"

import { InviteLink } from "@/components/InviteLink"
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer"
import { ApiError } from "@/lib/api"
import { useAuth } from "@/lib/auth"
import { formatUtcDateTime } from "@/lib/datetime"
import {
  useActiveInvitations,
  useHousehold,
  useMembers,
  useRemoveMember,
  useRevokeInvitation,
} from "@/lib/queries"

interface HouseholdMembersSheetProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

type Confirmation = { type: "invitation" | "member"; id: string }

const dateFormat = new Intl.DateTimeFormat("es-MX", {
  day: "numeric",
  month: "short",
  year: "numeric",
})

function messageFor(error: unknown, fallback: string) {
  return error instanceof ApiError ? error.message : fallback
}

/** Directorio del hogar y, para su propietario/a, controles de administración. */
export function HouseholdMembersSheet({ open, onOpenChange }: HouseholdMembersSheetProps) {
  const { session } = useAuth()
  const householdQuery = useHousehold()
  const membersQuery = useMembers()
  const { data: household } = householdQuery
  const {
    data: members = [],
    isLoading: membersLoading,
    error: membersError,
  } = membersQuery
  const isOwner = household?.isOwner === true
  const invitations = useActiveInvitations(isOwner, open)
  const revokeInvitation = useRevokeInvitation()
  const removeMember = useRemoveMember()
  const [showInvite, setShowInvite] = useState(false)
  const [confirming, setConfirming] = useState<Confirmation | null>(null)
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null)
  const confirmationCancelRef = useRef<HTMLButtonElement>(null)
  const restoreFocusRef = useRef<HTMLButtonElement | null>(null)
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const destructivePending = revokeInvitation.isPending || removeMember.isPending

  useEffect(() => {
    if (!open) return
    void householdQuery.refetch()
    void membersQuery.refetch()
    // Opening the drawer is the explicit refresh gesture for the directory.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  useEffect(() => {
    if (open && isOwner) void invitations.refetch()
    // The owner value can arrive after the household refresh above.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, isOwner])

  useEffect(() => {
    if (confirming) confirmationCancelRef.current?.focus()
  }, [confirming])

  function restoreFocus() {
    window.requestAnimationFrame(() => {
      const trigger = restoreFocusRef.current
      if (trigger?.isConnected) trigger.focus()
      else closeButtonRef.current?.focus()
      restoreFocusRef.current = null
    })
  }

  function startConfirmation(type: Confirmation["type"], id: string, trigger: HTMLButtonElement) {
    setFeedback(null)
    restoreFocusRef.current = trigger
    setConfirming({ type, id })
  }

  function cancelConfirmation() {
    setConfirming(null)
    restoreFocus()
  }

  function close(nextOpen: boolean) {
    if (!nextOpen) {
      setShowInvite(false)
      setConfirming(null)
      setFeedback(null)
      restoreFocusRef.current = null
    }
    onOpenChange(nextOpen)
  }

  function confirmRevoke(id: string) {
    setFeedback(null)
    revokeInvitation.mutate(id, {
      onSuccess: () => {
        setConfirming(null)
        setFeedback({ type: "success", text: "Invitación revocada." })
        restoreFocusRef.current = null
        restoreFocus()
      },
      onError: (error) => {
        setConfirming(null)
        setFeedback({ type: "error", text: messageFor(error, "No se pudo revocar la invitación.") })
        restoreFocus()
      },
    })
  }

  function confirmRemove(id: string) {
    setFeedback(null)
    removeMember.mutate(id, {
      onSuccess: () => {
        setConfirming(null)
        setFeedback({ type: "success", text: "Miembro eliminado del hogar." })
        restoreFocusRef.current = null
        restoreFocus()
      },
      onError: (error) => {
        setConfirming(null)
        setFeedback({ type: "error", text: messageFor(error, "No se pudo eliminar a esta persona.") })
        restoreFocus()
      },
    })
  }

  const invitationError = invitations.error instanceof ApiError && invitations.error.status === 403
    ? "No tienes permiso para ver las invitaciones activas."
    : invitations.error
      ? messageFor(invitations.error, "No se pudieron cargar las invitaciones.")
      : null

  return (
    <Drawer open={open} onOpenChange={close} showSwipeHandle>
      <DrawerContent className="mx-auto max-w-lg">
        {open && (
          <div className="flex max-h-[calc(100dvh-2rem)] flex-col overflow-hidden">
            <DrawerHeader className="flex-row items-center justify-between px-5 pt-2 pb-3 text-left">
              <span className="flex size-9 items-center justify-center rounded-full bg-secondary" aria-hidden="true">
                <Users size={17} />
              </span>
              <DrawerTitle className="text-[17px] font-semibold">Miembros del hogar</DrawerTitle>
              <DrawerClose render={<button ref={closeButtonRef} type="button" aria-label="Cerrar miembros del hogar" className="pressable flex size-9 items-center justify-center rounded-full bg-secondary"><X size={18} aria-hidden="true" /></button>} />
            </DrawerHeader>

            <div className="min-h-0 flex-1 space-y-4 overflow-y-auto overscroll-contain px-5 pb-7">
              {!isOwner && (
                <p className="rounded-xl bg-secondary px-3 py-2.5 text-[13px] leading-snug text-muted-foreground">
                  Solo la persona propietaria administra los miembros y las invitaciones del hogar.
                </p>
              )}
              {feedback && (
                <p role={feedback.type === "error" ? "alert" : "status"} aria-live="polite" className={`rounded-xl px-3 py-2 text-[13px] ${feedback.type === "error" ? "bg-expense/10 text-expense" : "bg-income/10 text-income"}`}>
                  {feedback.type === "success" && <Check size={14} className="mr-1 inline" aria-hidden="true" />}
                  {feedback.text}
                </p>
              )}

              {isOwner && (
                <section aria-labelledby="invite-title" className="rounded-2xl bg-secondary p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <h2 id="invite-title" className="text-[14px] font-semibold">Invitar al hogar</h2>
                      <p className="mt-0.5 text-[12px] text-muted-foreground">El link es válido por 7 días y para una persona.</p>
                    </div>
                    {!showInvite && <button type="button" onClick={() => { setFeedback(null); setShowInvite(true) }} className="pressable inline-flex shrink-0 items-center gap-1.5 rounded-xl bg-primary px-3 py-2 text-[13px] font-semibold text-primary-foreground"><UserPlus size={15} aria-hidden="true" />Invitar</button>}
                  </div>
                  {showInvite && <div className="mt-3"><InviteLink autoGenerate onGenerated={() => setFeedback({ type: "success", text: "Link de invitación generado." })} /></div>}
                </section>
              )}

              <section aria-labelledby="members-title">
                <div className="mb-2 flex items-baseline justify-between">
                  <h2 id="members-title" className="text-[13px] font-semibold text-muted-foreground">Personas</h2>
                  {!membersLoading && <span className="text-[12px] text-muted-foreground">{members.length}</span>}
                </div>
                {membersLoading ? <div className="h-16 animate-pulse rounded-2xl bg-secondary" /> : membersError ? <p role="alert" className="rounded-xl bg-expense/10 px-3 py-2 text-[13px] text-expense">{messageFor(membersError, "No se pudieron cargar los miembros.")}</p> : (
                  <ul className="overflow-hidden rounded-2xl border border-border bg-card" aria-label="Miembros activos">
                    {members.map((member) => {
                      const isSelf = member.id === session?.id
                      const isConfirming = confirming?.type === "member" && confirming.id === member.id
                      const isPending = removeMember.isPending && removeMember.variables === member.id
                      return <li key={member.id} className="border-b border-border last:border-b-0">
                        <div className="flex items-center gap-3 px-3 py-3">
                          <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[12px] font-semibold text-primary">{member.initials}</span>
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-center gap-1.5"><span className="text-[14px] font-medium">{member.name}</span>{isSelf && <Tag>Tú</Tag>}{member.isOwner && <Tag>Propietario/a</Tag>}</div>
                            <p className="truncate text-[12px] text-muted-foreground">{member.email}</p>
                          </div>
                          {isOwner && !isSelf && !member.isOwner && !isConfirming && <button type="button" disabled={destructivePending} onClick={(event) => startConfirmation("member", member.id, event.currentTarget)} className="pressable rounded-lg p-2 text-expense disabled:opacity-50" aria-label={`Eliminar a ${member.name}`}><Trash2 size={16} aria-hidden="true" /></button>}
                        </div>
                        {isConfirming && <ConfirmAction label={`¿Eliminar a ${member.name} del hogar?`} pending={isPending} disabled={destructivePending} actionLabel="Eliminar" cancelRef={confirmationCancelRef} onCancel={cancelConfirmation} onConfirm={() => confirmRemove(member.id)} />}
                      </li>
                    })}
                  </ul>
                )}
              </section>

              {isOwner && (
                <section aria-labelledby="invitations-title">
                  <h2 id="invitations-title" className="mb-2 text-[13px] font-semibold text-muted-foreground">Invitaciones activas</h2>
                  {invitations.isLoading ? <div className="h-14 animate-pulse rounded-2xl bg-secondary" /> : invitationError ? <p role="alert" className="rounded-xl bg-expense/10 px-3 py-2 text-[13px] text-expense">{invitationError}</p> : invitations.data?.length ? (
                    <ul className="overflow-hidden rounded-2xl border border-border bg-card">
                      {invitations.data.map((invitation) => {
                        const isConfirming = confirming?.type === "invitation" && confirming.id === invitation.id
                        const isPending = revokeInvitation.isPending && revokeInvitation.variables === invitation.id
                        return <li key={invitation.id} className="border-b border-border last:border-b-0">
                          <div className="flex items-center justify-between gap-3 px-3 py-3">
                            <div><p className="text-[13px] font-medium">Vence el {formatUtcDateTime(invitation.expiresAt, dateFormat)}</p><p className="text-[12px] text-muted-foreground">Creada el {formatUtcDateTime(invitation.createdAt, dateFormat)}</p></div>
                            {!isConfirming && <button type="button" disabled={destructivePending} onClick={(event) => startConfirmation("invitation", invitation.id, event.currentTarget)} className="pressable rounded-lg px-2 py-1.5 text-[12px] font-medium text-expense disabled:opacity-50">Revocar</button>}
                          </div>
                          {isConfirming && <ConfirmAction label="¿Revocar esta invitación? El link dejará de funcionar." pending={isPending} disabled={destructivePending} actionLabel="Revocar" cancelRef={confirmationCancelRef} onCancel={cancelConfirmation} onConfirm={() => confirmRevoke(invitation.id)} />}
                        </li>
                      })}
                    </ul>
                  ) : <p className="rounded-xl bg-secondary px-3 py-2.5 text-[13px] text-muted-foreground">No hay invitaciones activas.</p>}
                </section>
              )}
            </div>
          </div>
        )}
      </DrawerContent>
    </Drawer>
  )
}

function Tag({ children }: { children: React.ReactNode }) {
  return <span className="rounded-full bg-secondary px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">{children}</span>
}

function ConfirmAction({ label, pending, disabled, actionLabel, cancelRef, onCancel, onConfirm }: { label: string; pending: boolean; disabled: boolean; actionLabel: string; cancelRef: RefObject<HTMLButtonElement | null>; onCancel: () => void; onConfirm: () => void }) {
  return <div className="flex flex-wrap items-center gap-2 border-t border-border bg-expense/5 px-3 py-2.5" role="group" aria-label={label}><p className="mr-auto text-[12px] text-foreground">{label}</p><button ref={cancelRef} type="button" onClick={onCancel} className="pressable rounded-lg px-2.5 py-1.5 text-[12px] font-medium">Cancelar</button><button type="button" disabled={disabled} onClick={onConfirm} className="pressable rounded-lg bg-expense px-2.5 py-1.5 text-[12px] font-semibold text-white disabled:opacity-50">{pending ? "Procesando…" : actionLabel}</button></div>
}
