import { useMemo, useRef, useState } from "react"
import { FileText, Paperclip, Plus, Repeat, X } from "lucide-react"
import { motion } from "motion/react"

import { Button } from "@/components/ui/button"
import {
  Drawer,
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
            className="pressable fixed right-5 bottom-24 z-50 flex size-14 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg shadow-primary/30 md:right-8 md:bottom-8"
          >
            <Plus size={28} strokeWidth={2.5} />
          </button>
        }
      />
      <DrawerContent className="mx-auto max-w-lg">
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
    <div className="flex flex-col gap-5 px-5 pb-8">
      <DrawerHeader className="p-0 pt-2">
        <DrawerTitle className="sr-only">Registrar movimiento</DrawerTitle>
        {/* Segmented control estilo iOS */}
        <div className="mx-auto flex rounded-xl bg-secondary p-1">
          {(["expense", "income"] as const).map((t) => (
            <button
              key={t}
              onClick={() => {
                setType(t)
                setCategoryId(null)
              }}
              className="relative rounded-lg px-6 py-1.5 text-[14px] font-medium"
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
      </DrawerHeader>

      {/* Monto: protagonista, tracking cerrado, cifras tabulares */}
      <div className="flex items-baseline justify-center gap-1">
        <span className="text-2xl font-semibold text-muted-foreground">$</span>
        <input
          autoFocus
          inputMode="decimal"
          placeholder="0"
          value={amountText}
          onChange={(e) => setAmountText(e.target.value.replace(/[^0-9.,]/g, ""))}
          className="tnum w-48 bg-transparent text-center text-5xl font-bold tracking-tight outline-none placeholder:text-muted-foreground/40"
          aria-label="Monto"
        />
      </div>

      {/* Categorías */}
      <div>
        <p className="mb-2 text-[13px] font-medium text-muted-foreground">
          Categoría
        </p>
        <div className="grid grid-cols-4 gap-2">
          {visibleCategories.map((c) => {
            const selected = categoryId === c.id
            return (
              <button
                key={c.id}
                onClick={() => setCategoryId(c.id)}
                className="pressable flex flex-col items-center gap-1.5 rounded-2xl py-2"
              >
                <CategoryIcon
                  icon={c.icon}
                  color={c.color}
                  size={22}
                  className={`size-12 transition-shadow ${
                    selected ? "ring-2 ring-offset-2 ring-offset-background" : ""
                  }`}
                  style={{ ["--tw-ring-color" as string]: c.color }}
                />
                <span className="max-w-full truncate text-[11px] font-medium">
                  {c.name}
                </span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Cuenta */}
      <div>
        <p className="mb-2 text-[13px] font-medium text-muted-foreground">
          Cuenta
        </p>
        <div className="flex gap-2 overflow-x-auto pb-1">
          {accounts.map((a) => (
            <button
              key={a.id}
              onClick={() => setAccountId(a.id)}
              className={`pressable shrink-0 rounded-full px-4 py-1.5 text-[13px] font-medium transition-colors ${
                effectiveAccountId === a.id
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-secondary-foreground"
              }`}
            >
              {a.name}
            </button>
          ))}
        </div>
      </div>

      {/* Fecha: hoy por defecto, editable para gastos de días anteriores */}
      <div>
        <p className="mb-2 text-[13px] font-medium text-muted-foreground">
          Fecha
        </p>
        <input
          type="date"
          value={date}
          max={toISODate(new Date())}
          onChange={(e) => e.target.value && setDate(e.target.value)}
          className="tnum w-full rounded-xl bg-secondary px-4 py-2.5 text-[15px] outline-none [color-scheme:light] dark:[color-scheme:dark]"
          aria-label="Fecha del movimiento"
        />
      </div>

      {/* Repetir: renta, sueldo y suscripciones se capturan una vez */}
      <div>
        <p className="mb-2 text-[13px] font-medium text-muted-foreground">
          Repetir
        </p>
        <div className="flex gap-2">
          {repeatOptions.map((option) => (
            <button
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

      {/* Comprobante opcional */}
      <div>
        <p className="mb-2 text-[13px] font-medium text-muted-foreground">
          Comprobante (opcional)
        </p>
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

      {/* Nota opcional */}
      <input
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="Nota (opcional)"
        className="rounded-xl bg-secondary px-4 py-2.5 text-[15px] outline-none placeholder:text-muted-foreground"
      />

      {/* Acción principal siempre visible: el sheet scrollea debajo de ella */}
      <div className="sticky bottom-0 -mx-5 -mb-8 border-t border-border bg-card px-5 pt-3 pb-[max(1rem,env(safe-area-inset-bottom))]">
        <Button
          size="lg"
          disabled={!canSave || isSaving}
          onClick={save}
          className="pressable h-12 w-full rounded-2xl text-[16px] font-semibold"
        >
          Guardar
        </Button>
      </div>
    </div>
  )
}

/** Tamaño legible: KB/MB con 1 decimal. */
function formatFileSize(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / 1024).toFixed(1)} KB`
}
