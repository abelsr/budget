import { useEffect, useRef, useState } from "react"
import { ArrowLeft, Camera, KeyRound, Trash2, X } from "lucide-react"

import { ProfileAvatar } from "@/components/ProfileAvatar"
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer"
import { ApiError } from "@/lib/api"
import { type Sex, useAuth } from "@/lib/auth"

interface ProfileSettingsSheetProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

const sexOptions: Array<{ value: Sex; label: string }> = [
  { value: "female", label: "Mujer" },
  { value: "male", label: "Hombre" },
  { value: "non_binary", label: "No binario" },
  { value: "prefer_not_to_say", label: "Prefiero no indicarlo" },
]

function errorMessage(error: unknown) {
  return error instanceof ApiError ? error.message : "Ocurrió un error inesperado"
}

function ageFromBirthDate(value: string) {
  if (!value) return null
  const birthDate = new Date(`${value}T00:00:00`)
  if (Number.isNaN(birthDate.getTime())) return null
  const today = new Date()
  let age = today.getFullYear() - birthDate.getFullYear()
  const hasHadBirthday =
    today.getMonth() > birthDate.getMonth() ||
    (today.getMonth() === birthDate.getMonth() && today.getDate() >= birthDate.getDate())
  if (!hasHadBirthday) age -= 1
  return age >= 0 ? `${age} años` : null
}

function localIsoDate(date = new Date()) {
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  return `${date.getFullYear()}-${month}-${day}`
}

/** Sheet compacto para el perfil y la contraseña, sin exponer el avatar por URL. */
export function ProfileSettingsSheet({ open, onOpenChange }: ProfileSettingsSheetProps) {
  const [view, setView] = useState<"profile" | "password">("profile")
  const [busy, setBusy] = useState(false)
  const busyRef = useRef(false)

  async function runExclusive(task: () => Promise<void>) {
    if (busyRef.current) return false
    busyRef.current = true
    setBusy(true)
    try {
      await task()
      return true
    } finally {
      busyRef.current = false
      setBusy(false)
    }
  }

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen) setView("profile")
    onOpenChange(nextOpen)
  }

  return (
    <Drawer open={open} onOpenChange={handleOpenChange} showSwipeHandle>
      <DrawerContent className="mx-auto max-w-lg">
        {open && (view === "profile" ? (
          <ProfileForm busy={busy} runExclusive={runExclusive} onPassword={() => setView("password")} />
        ) : (
          <PasswordForm busy={busy} runExclusive={runExclusive} onBack={() => setView("profile")} />
        ))}
      </DrawerContent>
    </Drawer>
  )
}

function SheetHeader({ title, back }: { title: string; back?: () => void }) {
  return (
    <DrawerHeader className="flex-row items-center justify-between px-5 pt-2 pb-3 text-left">
      {back ? (
        <button type="button" onClick={back} aria-label="Volver a mi cuenta" className="pressable flex size-9 items-center justify-center rounded-full bg-secondary">
          <ArrowLeft size={18} aria-hidden="true" />
        </button>
      ) : <span className="size-9" aria-hidden="true" />}
      <DrawerTitle className="text-[17px] font-semibold">{title}</DrawerTitle>
      <DrawerClose render={<button type="button" aria-label="Cerrar" className="pressable flex size-9 items-center justify-center rounded-full bg-secondary"><X size={18} aria-hidden="true" /></button>} />
    </DrawerHeader>
  )
}

function ProfileForm({
  busy,
  runExclusive,
  onPassword,
}: {
  busy: boolean
  runExclusive: (task: () => Promise<void>) => Promise<boolean>
  onPassword: () => void
}) {
  const { session, updateProfile, uploadAvatar, removeAvatar } = useAuth()
  const inputRef = useRef<HTMLInputElement>(null)
  const [name, setName] = useState(session?.name ?? "")
  const [sex, setSex] = useState<Sex | "">(session?.sex ?? "")
  const [birthDate, setBirthDate] = useState(session?.birthDate ?? "")
  const [formError, setFormError] = useState<string | null>(null)
  const [avatarError, setAvatarError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const age = ageFromBirthDate(birthDate)

  useEffect(() => {
    if (!session) return
    setName((current) => current === session.name ? current : session.name)
    setSex((current) => current === session.sex ? current : (session.sex ?? ""))
    setBirthDate((current) => current === session.birthDate ? current : (session.birthDate ?? ""))
  }, [session])

  if (!session) return null

  async function save(event: React.FormEvent) {
    event.preventDefault()
    if (busy) return
    if (!name.trim()) {
      setFormError("Escribe tu nombre.")
      return
    }
    setFormError(null)
    setSuccess(null)
    await runExclusive(async () => {
      try {
        await updateProfile({ name: name.trim(), sex: sex || null, birthDate: birthDate || null })
        setSuccess("Cambios guardados.")
      } catch (error) {
        setFormError(errorMessage(error))
      }
    })
  }

  async function selectAvatar(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ""
    if (busy) return
    if (!file) return
    if (!file.type.startsWith("image/")) {
      setAvatarError("El archivo debe ser una imagen.")
      return
    }
    if (file.size > 2 * 1024 * 1024) {
      setAvatarError("La imagen no puede superar 2 MiB.")
      return
    }
    setAvatarError(null)
    setSuccess(null)
    await runExclusive(async () => {
      try {
        await uploadAvatar(file)
        setSuccess("Avatar actualizado.")
      } catch (error) {
        setAvatarError(errorMessage(error))
      }
    })
  }

  async function deleteAvatar() {
    if (busy) return
    setAvatarError(null)
    setSuccess(null)
    await runExclusive(async () => {
      try {
        await removeAvatar()
        setSuccess("Avatar eliminado.")
      } catch (error) {
        setAvatarError(errorMessage(error))
      }
    })
  }

  return (
    <form onSubmit={save} aria-busy={busy} className="flex max-h-[calc(100dvh-2rem)] flex-col overflow-hidden">
      <SheetHeader title="Mi cuenta" />
      <div className="min-h-0 flex-1 space-y-5 overflow-y-auto overscroll-contain px-5 py-2">
        {busy && <p role="status" aria-live="polite" className="sr-only">Operación en curso. Puedes cerrar esta ventana.</p>}
        <div className="flex flex-col items-center gap-2">
          <ProfileAvatar name={session.name} hasAvatar={session.hasAvatar} avatarUpdatedAt={session.avatarUpdatedAt} className="size-20 rounded-full bg-primary/10 text-xl font-semibold text-primary" />
          <div className="flex items-center gap-2">
            <button type="button" onClick={() => inputRef.current?.click()} disabled={busy} className="pressable inline-flex items-center gap-1.5 rounded-xl bg-secondary px-3 py-2 text-[12px] font-medium disabled:opacity-50">
              <Camera size={15} aria-hidden="true" /> {session.hasAvatar ? "Reemplazar" : "Subir foto"}
            </button>
            {session.hasAvatar && <button type="button" onClick={deleteAvatar} disabled={busy} className="pressable inline-flex items-center gap-1.5 rounded-xl px-3 py-2 text-[12px] font-medium text-expense disabled:opacity-50"><Trash2 size={15} aria-hidden="true" /> Quitar</button>}
          </div>
          <input ref={inputRef} type="file" accept="image/*" onChange={selectAvatar} disabled={busy} className="sr-only" aria-label="Elegir imagen de perfil" />
          {avatarError && <p role="alert" className="text-[12px] text-expense">{avatarError}</p>}
        </div>

        <div>
          <label htmlFor="profile-name" className="mb-2 block text-[13px] font-medium text-muted-foreground">Nombre</label>
          <input id="profile-name" value={name} onChange={(event) => setName(event.target.value)} disabled={busy} autoComplete="name" aria-invalid={Boolean(formError && !name.trim())} className="w-full rounded-xl bg-secondary px-4 py-2.5 text-[15px] outline-none disabled:opacity-50" />
        </div>
        <div>
          <label htmlFor="profile-sex" className="mb-2 block text-[13px] font-medium text-muted-foreground">Sexo <span className="font-normal">(opcional)</span></label>
          <select id="profile-sex" value={sex} onChange={(event) => setSex(event.target.value as Sex | "")} disabled={busy} className="w-full rounded-xl bg-secondary px-4 py-2.5 text-[15px] outline-none disabled:opacity-50">
            <option value="">Sin indicar</option>
            {sexOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="profile-birth-date" className="mb-2 block text-[13px] font-medium text-muted-foreground">Fecha de nacimiento <span className="font-normal">(opcional)</span></label>
          <input id="profile-birth-date" type="date" value={birthDate} max={localIsoDate()} onChange={(event) => setBirthDate(event.target.value)} disabled={busy} className="w-full rounded-xl bg-secondary px-4 py-2.5 text-[15px] outline-none disabled:opacity-50" />
          {age && <p className="mt-1.5 text-[12px] text-muted-foreground">{age}</p>}
        </div>
        <button type="button" onClick={onPassword} className="pressable flex w-full items-center gap-3 rounded-2xl bg-secondary px-4 py-3 text-left">
          <span className="flex size-9 items-center justify-center rounded-full bg-card"><KeyRound size={16} aria-hidden="true" /></span>
          <span><span className="block text-[14px] font-medium">Contraseña</span><span className="block text-[12px] text-muted-foreground">Cambiar contraseña</span></span>
        </button>
        {formError && <p role="alert" className="rounded-xl bg-expense/10 px-3 py-2 text-[13px] text-expense">{formError}</p>}
        {success && <p role="status" className="rounded-xl bg-income/10 px-3 py-2 text-[13px] text-income">{success}</p>}
      </div>
      <div className="shrink-0 p-5 pt-3"><button type="submit" disabled={busy} className="pressable w-full rounded-xl bg-primary px-4 py-3 text-[14px] font-semibold text-primary-foreground disabled:opacity-50">{busy ? "Guardando…" : "Guardar cambios"}</button></div>
    </form>
  )
}

function PasswordForm({
  busy,
  runExclusive,
  onBack,
}: {
  busy: boolean
  runExclusive: (task: () => Promise<void>) => Promise<boolean>
  onBack: () => void
}) {
  const { changePassword } = useAuth()
  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmation, setConfirmation] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    if (busy) return
    if (newPassword.length < 8) return setError("La nueva contraseña debe tener al menos 8 caracteres.")
    if (newPassword !== confirmation) return setError("Las contraseñas no coinciden.")
    setError(null)
    setSuccess(false)
    await runExclusive(async () => {
      try {
        await changePassword(currentPassword, newPassword)
        setCurrentPassword("")
        setNewPassword("")
        setConfirmation("")
        setSuccess(true)
      } catch (requestError) {
        setError(errorMessage(requestError))
      }
    })
  }

  return <form onSubmit={submit} aria-busy={busy} className="flex max-h-[calc(100dvh-2rem)] flex-col overflow-hidden">
    <SheetHeader title="Cambiar contraseña" back={onBack} />
    <div className="min-h-0 flex-1 space-y-4 overflow-y-auto overscroll-contain px-5 py-2">
      {busy && <p role="status" aria-live="polite" className="sr-only">Operación en curso. Puedes cerrar esta ventana.</p>}
      <PasswordField id="current-password" label="Contraseña actual" value={currentPassword} onChange={setCurrentPassword} autoComplete="current-password" disabled={busy} />
      <PasswordField id="new-password" label="Nueva contraseña" value={newPassword} onChange={setNewPassword} autoComplete="new-password" disabled={busy} />
      <PasswordField id="confirm-password" label="Confirmar nueva contraseña" value={confirmation} onChange={setConfirmation} autoComplete="new-password" disabled={busy} />
      {error && <p role="alert" className="rounded-xl bg-expense/10 px-3 py-2 text-[13px] text-expense">{error}</p>}
      {success && <p role="status" className="rounded-xl bg-income/10 px-3 py-2 text-[13px] text-income">Contraseña actualizada.</p>}
    </div>
    <div className="shrink-0 p-5 pt-3"><button type="submit" disabled={busy} className="pressable w-full rounded-xl bg-primary px-4 py-3 text-[14px] font-semibold text-primary-foreground disabled:opacity-50">{busy ? "Actualizando…" : "Actualizar contraseña"}</button></div>
  </form>
}

function PasswordField({ id, label, value, onChange, autoComplete, disabled }: { id: string; label: string; value: string; onChange: (value: string) => void; autoComplete: string; disabled: boolean }) {
  return <div><label htmlFor={id} className="mb-2 block text-[13px] font-medium text-muted-foreground">{label}</label><input id={id} type="password" value={value} onChange={(event) => onChange(event.target.value)} disabled={disabled} autoComplete={autoComplete} required className="w-full rounded-xl bg-secondary px-4 py-2.5 text-[15px] outline-none disabled:opacity-50" /></div>
}
