import { useMemo, useState } from "react"
import { Plus } from "lucide-react"
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
import { useAccounts, useAddTransaction, useCategories } from "@/lib/queries"
import { springIndicator } from "@/lib/springs"
import { toISODate } from "@/lib/format"
import type { TransactionType } from "@/lib/types"

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

  const [type, setType] = useState<TransactionType>("expense")
  const [amountText, setAmountText] = useState("")
  const [categoryId, setCategoryId] = useState<string | null>(null)
  const [accountId, setAccountId] = useState<string | null>(null)
  const [note, setNote] = useState("")

  const amount = Number(amountText.replace(",", ".")) || 0
  const visibleCategories = useMemo(
    () => categories.filter((c) => c.type === type && c.active),
    [categories, type],
  )
  const effectiveAccountId = accountId ?? accounts.find((a) => a.kind === "debit")?.id ?? accounts[0]?.id
  const canSave = amount > 0 && categoryId !== null && effectiveAccountId

  function save() {
    if (!canSave || !categoryId || !effectiveAccountId) return
    addTransaction.mutate(
      {
        type,
        amount,
        categoryId,
        accountId: effectiveAccountId,
        date: toISODate(new Date()),
        note: note.trim() || undefined,
      },
      {
        onSuccess: () => {
          navigator.vibrate?.(10)
          onDone()
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

      {/* Nota opcional */}
      <input
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="Nota (opcional)"
        className="rounded-xl bg-secondary px-4 py-2.5 text-[15px] outline-none placeholder:text-muted-foreground"
      />

      <Button
        size="lg"
        disabled={!canSave}
        onClick={save}
        className="pressable h-12 rounded-2xl text-[16px] font-semibold"
      >
        Guardar
      </Button>
    </div>
  )
}
