import { useMemo, useRef, useState } from "react"
import { CalendarDays, ChevronDown, FileText, Paperclip, Plus, Repeat, X } from "lucide-react"
import { motion } from "motion/react"

import { Button } from "@/components/ui/button"
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from "@/components/ui/drawer"
import { CategoryIcon } from "@/components/CategoryIcon"
import {
  useAccounts,
  useAddTransaction,
  useCategories,
  useUploadAttachment,
} from "@/lib/queries"
import { springIndicator } from "@/lib/springs"
import { toISODate } from "@/lib/format"
import type { Frequency, TransactionType } from "@/lib/types"

/** Opciones del selector "Repetir". `null` = movimiento de una sola vez. */
const repeatOptions: { value: Frequency | null; label: string }[] = [
  { value: null, label: "No repetir" },
  { value: "weekly", label: "Semanal" },
  { value: "monthly", label: "Mensual" },
]

/**
 * Registro rápido: la interacción más importante de la app.
 * Objetivo: <10 segundos. Monto → categoría → guardar.
 * Cuenta precargada con la más usada (débito), fecha = hoy.
 */
export function AddTransactionButton() {
  const [open, setOpen] = useState(false)
  return (
    <Drawer open={open} onOpenChange={setOpen} showSwipeHandle>
      <DrawerTrigger
        render={
          <button
            aria-label="Registrar movimiento"
            className="pressable fixed right-5 bottom-24 z-50 flex size-14 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg shadow-primary/30 md:hidden"
          >
            <Plus size={28} strokeWidth={2.5} />
          </button>
        }
      />
      <DrawerTrigger
        render={
          <button
            aria-label="Registrar movimiento"
            className="pressable fixed top-3 right-8 z-50 hidden items-center gap-1.5 rounded-md bg-primary px-3 py-2 text-xs font-medium text-primary-foreground shadow-sm shadow-primary/25 hover:bg-primary-strong md:flex"
          >
            <Plus size={15} strokeWidth={2.5} />
            + Registrar
          </button>
        }
      />
      <DrawerContent className="mx-auto h-[calc(100dvh-1rem)] max-h-[calc(100dvh-1rem)] max-w-lg md:h-auto md:max-h-[calc(100dvh-6rem)]">
        {open && <AddTransactionForm onDone={() => setOpen(false)} />}
      </DrawerContent>
    </Drawer>
  )
}

function AddTransactionForm({ onDone }: { onDone: () => void }) {
  const { data: accounts = [] } = useAccounts()
  const { data: categories = [] } = useCategories()
  const addTransaction = useAddTransaction()
  const uploadAttachment = useUploadAttachment()

  const [type, setType] = useState<TransactionType>("expense")
  const [amountText, setAmountText] = useState("")
  const [categoryId, setCategoryId] = useState<string | null>(null)
  const [accountId, setAccountId] = useState<string | null>(null)
  const [date, setDate] = useState(() => toISODate(new Date()))
  const [note, setNote] = useState("")
  const [repeat, setRepeat] = useState<Frequency | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const amount = Number(amountText.replace(",", ".")) || 0
  const visibleCategories = useMemo(
    () => categories.filter((c) => c.type === type && c.active),
    [categories, type],
  )
  const effectiveAccountId = accountId ?? accounts.find((a) => a.kind === "debit")?.id ?? accounts[0]?.id
  const selectedCategory = visibleCategories.find((c) => c.id === categoryId)
  const selectedAccount = accounts.find((a) => a.id === effectiveAccountId)
  const canSave = amount > 0 && categoryId !== null && effectiveAccountId && date
  const isSaving = addTransaction.isPending || uploadAttachment.isPending

  function save() {
    if (!canSave || !categoryId || !effectiveAccountId) return
    addTransaction.mutate(
      {
        type,
        amount,
        categoryId,
        accountId: effectiveAccountId,
        date,
        note: note.trim() || undefined,
        repeat: repeat ?? undefined,
      },
      {
        onSuccess: (created) => {
          if (file) {
            uploadAttachment.mutate(
              { transactionId: created.id, file },
              {
                onError: (err) => {
                  // La transacción ya quedó guardada; solo falló el adjunto.
                  console.error("Error al subir el comprobante:", err)
                },
                onSettled: () => {
                  navigator.vibrate?.(10)
                  onDone()
                },
              },
            )
          } else {
            navigator.vibrate?.(10)
            onDone()
          }
        },
      },
    )
  }

  return (
    <div className="flex h-full min-h-0 flex-col md:h-auto">
      <DrawerHeader className="flex-row items-center justify-between border-b border-border px-5 pt-2 pb-3 text-left">
        <DrawerTitle className="text-[16px] font-semibold">Registrar</DrawerTitle>
        <DrawerClose
          render={
            <button
              type="button"
              aria-label="Cerrar registro de movimiento"
              className="pressable flex size-9 items-center justify-center rounded-full bg-secondary text-secondary-foreground"
            >
              <X size={18} />
            </button>
          }
        />
      </DrawerHeader>

      <form
        className="flex min-h-0 flex-1 flex-col overflow-y-auto overscroll-contain"
        onSubmit={(event) => {
          event.preventDefault()
          save()
        }}
      >
        <div className="flex flex-col gap-5 px-5 pt-4 pb-5">
          <div className="grid grid-cols-2 rounded-lg border border-border bg-secondary p-0.5" role="group" aria-label="Tipo de movimiento">
          {(["expense", "income"] as const).map((t) => (
            <button
              type="button"
              key={t}
              onClick={() => {
                setType(t)
                setCategoryId(null)
              }}
              aria-pressed={type === t}
              className="relative rounded-md py-2 text-[13px] font-medium"
            >
              {type === t && (
                <motion.span
                  layoutId="tx-type"
                  transition={springIndicator}
                  className="absolute inset-0 rounded-lg bg-card shadow-sm"
                />
              )}
              <span
                className={`relative ${
                  type === t ? "text-foreground" : "text-muted-foreground"
                }`}
              >
                {t === "expense" ? "Gasto" : "Ingreso"}
              </span>
            </button>
          ))}
          </div>

          <div className="flex items-baseline justify-center gap-1 py-2">
            <span className="text-2xl font-semibold text-muted-foreground">$</span>
            <input
              autoFocus
              inputMode="decimal"
              placeholder="0.00"
              value={amountText}
              onChange={(e) => setAmountText(e.target.value.replace(/[^0-9.,]/g, ""))}
              className="tnum w-56 bg-transparent text-center text-5xl font-bold tracking-tight outline-none placeholder:text-muted-foreground/40"
              aria-label="Monto"
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="transaction-category" className="block text-[12px] font-semibold text-muted-foreground">
              Categoría
            </label>
            <div className="relative flex h-12 items-center gap-3 rounded-xl border border-border bg-card px-3">
              {selectedCategory ? (
                <CategoryIcon
                  icon={selectedCategory.icon}
                  color={selectedCategory.color}
                  size={18}
                  className="size-7 shrink-0"
                />
              ) : (
                <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-secondary text-muted-foreground">?</span>
              )}
              <select
                id="transaction-category"
                value={categoryId ?? ""}
                onChange={(e) => setCategoryId(e.target.value || null)}
                className="min-w-0 flex-1 appearance-none rounded-sm bg-transparent pr-7 text-[14px] font-medium outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-card"
              >
                <option value="">Selecciona una categoría</option>
                {visibleCategories.map((category) => (
                  <option key={category.id} value={category.id}>{category.name}</option>
                ))}
              </select>
              <ChevronDown
                size={16}
                aria-hidden="true"
                className="pointer-events-none absolute right-3 text-muted-foreground"
              />
            </div>
          </div>

          <div className="space-y-2">
            <label htmlFor="transaction-account" className="block text-[12px] font-semibold text-muted-foreground">
              Cuenta
            </label>
            <div className="relative flex h-12 items-center gap-3 rounded-xl border border-border bg-card px-3">
              <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary-soft text-[12px] font-semibold text-primary">
                {selectedAccount?.name.slice(0, 1).toUpperCase() ?? "?"}
              </span>
              <select
                id="transaction-account"
                value={effectiveAccountId ?? ""}
                onChange={(e) => setAccountId(e.target.value || null)}
                className="min-w-0 flex-1 appearance-none rounded-sm bg-transparent pr-7 text-[14px] font-medium outline-none focus-visible:outline-2 focus-visible:outline-ring focus-visible:outline-offset-2 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-card"
              >
                {accounts.length === 0 && <option value="">No hay cuentas disponibles</option>}
                {accounts.map((account) => (
                  <option key={account.id} value={account.id}>{account.name}</option>
                ))}
              </select>
              <ChevronDown
                size={16}
                aria-hidden="true"
                className="pointer-events-none absolute right-3 text-muted-foreground"
              />
            </div>
          </div>

          <div className="space-y-2">
            <label htmlFor="transaction-date" className="block text-[12px] font-semibold text-muted-foreground">Fecha</label>
            <div className="flex h-12 items-center gap-3 rounded-xl border border-border bg-card px-3">
              <CalendarDays size={18} className="shrink-0 text-muted-foreground" aria-hidden="true" />
              <input
                id="transaction-date"
                type="date"
                value={date}
                max={toISODate(new Date())}
                onChange={(e) => e.target.value && setDate(e.target.value)}
                className="tnum min-w-0 flex-1 bg-transparent text-[14px] font-medium outline-none [color-scheme:light] dark:[color-scheme:dark]"
              />
            </div>
          </div>

          <div className="space-y-2">
            <label htmlFor="transaction-note" className="block text-[12px] font-semibold text-muted-foreground">Nota <span className="font-normal">(opcional)</span></label>
            <input
              id="transaction-note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Ej. Despensa de la semana"
              className="h-12 w-full rounded-xl border border-border bg-card px-3 text-[14px] outline-none placeholder:text-muted-foreground"
            />
          </div>

          <details className="rounded-xl border border-border bg-secondary/40 px-3">
            <summary className="flex h-11 cursor-pointer list-none items-center gap-2 text-[13px] font-medium text-muted-foreground">
              <Repeat size={15} aria-hidden="true" />
              Opciones adicionales
            </summary>
            <div className="space-y-4 border-t border-border py-4">
              <div>
                <p className="mb-2 text-[12px] font-semibold text-muted-foreground">Repetir</p>
                <div className="flex gap-2">
          {repeatOptions.map((option) => (
            <button
              type="button"
              key={option.label}
              onClick={() => setRepeat(option.value)}
              aria-pressed={repeat === option.value}
              className={`pressable flex-1 rounded-full px-3 py-1.5 text-[13px] font-medium transition-colors ${
                repeat === option.value
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-secondary-foreground"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
        {repeat && (
          <p className="mt-1.5 flex items-center gap-1.5 px-1 text-[12px] text-muted-foreground">
            <Repeat size={12} className="shrink-0" />
            Este movimiento es el primero; el siguiente se generará solo.
          </p>
        )}
              </div>

              <div>
                <p className="mb-2 text-[12px] font-semibold text-muted-foreground">Comprobante <span className="font-normal">(opcional)</span></p>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,.pdf,.doc,.docx"
          className="hidden"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
                {file ? (
          <div className="flex items-center gap-2 rounded-xl bg-secondary px-3 py-2">
            <FileText size={16} className="shrink-0 text-muted-foreground" />
            <span className="min-w-0 flex-1 truncate text-[13px] font-medium">
              {file.name}
            </span>
            <span className="tnum shrink-0 text-[12px] text-muted-foreground">
              {formatFileSize(file.size)}
            </span>
            <button
              type="button"
              onClick={() => {
                setFile(null)
                if (fileInputRef.current) fileInputRef.current.value = ""
              }}
              className="pressable shrink-0 rounded-full bg-muted p-1 text-muted-foreground"
              aria-label="Quitar comprobante"
            >
              <X size={12} />
            </button>
          </div>
                ) : (
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="pressable flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-border py-2.5 text-[13px] font-medium text-muted-foreground"
          >
            <Paperclip size={14} />
            Adjuntar foto, PDF o doc
          </button>
                )}
              </div>
            </div>
          </details>
        </div>

        <div className="sticky bottom-0 mt-auto border-t border-border bg-popover px-5 pt-3 pb-[max(1rem,env(safe-area-inset-bottom))]">
        <Button
          size="lg"
          type="submit"
          disabled={!canSave || isSaving}
          className="pressable h-12 w-full rounded-2xl text-[16px] font-semibold"
        >
          {isSaving ? "Guardando..." : "Guardar"}
        </Button>
        </div>
      </form>
      </div>
  )
}

/** Tamaño legible: KB/MB con 1 decimal. */
function formatFileSize(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / 1024).toFixed(1)} KB`
}
