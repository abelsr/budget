import { useMemo, useState } from "react"
import { ArrowLeftRight, CreditCard, Eye, FileText, Image as ImageIcon, Repeat, Trash2 } from "lucide-react"
import { motion } from "motion/react"

import { InstalmentPlanCreateSheet, InstalmentPlanSheet } from "@/components/InstalmentPlanSheets"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer"
import { CategoryIcon } from "@/components/CategoryIcon"
import { CHART_OTHER } from "@/lib/chart-colors"
import { apiFetchBlob, ApiError } from "@/lib/api"
import { formatMoney, toISODate } from "@/lib/format"
import {
  useAccounts,
  useCategories,
  useDeleteAttachment,
  useDeleteTransaction,
  useInstalmentPlans,
  useRestoreTransaction,
  useUpdateTransaction,
} from "@/lib/queries"
import { springIndicator } from "@/lib/springs"
import { useSnackbar } from "@/components/ui/snackbar"
import type {
  Account,
  Attachment,
  Category,
  Member,
  Transaction,
  TransactionSplit,
  TransactionType,
} from "@/lib/types"

const longDateFmt = new Intl.DateTimeFormat("es-MX", {
  weekday: "long",
  day: "numeric",
  month: "long",
  year: "numeric",
})

/**
 * Sheet de detalle/edición de un movimiento. Dos modos:
 *  - Vista: monto protagonista, filas de detalle estilo iOS, comprobantes
 *    (ver/eliminar) y borrado del movimiento en dos pasos.
 *  - Edición: mismo patrón visual que AddTransactionSheet, prellenado.
 */
export function TransactionDetailSheet({
  open,
  onOpenChange,
  transaction,
  category,
  account,
  member,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  transaction: Transaction
  category?: Category
  account?: Account
  member?: Member
}) {
  return (
    <Drawer open={open} onOpenChange={onOpenChange} showSwipeHandle>
      <DrawerContent className="mx-auto max-w-lg">
        {open && (
          <SheetBody
            transaction={transaction}
            category={category}
            account={account}
            member={member}
            onClose={() => onOpenChange(false)}
          />
        )}
      </DrawerContent>
    </Drawer>
  )
}

function SheetBody({
  transaction,
  category,
  account,
  member,
  onClose,
}: {
  transaction: Transaction
  category?: Category
  account?: Account
  member?: Member
  onClose: () => void
}) {
  const [mode, setMode] = useState<"view" | "edit">("view")

  if (mode === "edit") {
    return (
      <EditForm
        transaction={transaction}
        onCancel={() => setMode("view")}
        onDone={() => setMode("view")}
      />
    )
  }

  return (
    <ViewMode
      transaction={transaction}
      category={category}
      account={account}
      member={member}
      onEdit={() => setMode("edit")}
      onClose={onClose}
    />
  )
}

// ---------------------------------------------------------------------------
// Modo vista
// ---------------------------------------------------------------------------

function ViewMode({
  transaction,
  category,
  account,
  member,
  onEdit,
  onClose,
}: {
  transaction: Transaction
  category?: Category
  account?: Account
  member?: Member
  onEdit: () => void
  onClose: () => void
}) {
  const deleteTransaction = useDeleteTransaction()
  const restoreTransaction = useRestoreTransaction()
  const showSnackbar = useSnackbar()
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [planSheetPlanId, setPlanSheetPlanId] = useState<string | null>(null)
  const [createPlanOpen, setCreatePlanOpen] = useState(false)
  const isIncome = transaction.type === "income"
  const isTransfer = transaction.type === "transfer"
  const isInflow = transaction.transferDirection === "inflow"
  const { data: categories = [] } = useCategories()
  const { data: plans = [] } = useInstalmentPlans()
  const plan = plans.find((item) => item.sourceTransactionId === transaction.id)
  const msiEligible =
    !isTransfer && !isIncome && account?.kind === "credit" && !account.isPersonal
  const authorName = transaction.authorName ?? member?.name

  function remove() {
    const deletedId = transaction.id
    deleteTransaction.mutate(deletedId, {
      onSuccess: () => {
        navigator.vibrate?.(10)
        showSnackbar({
          message: "Movimiento eliminado",
          action: { label: "Deshacer", onClick: () => restoreTransaction.mutate(deletedId) },
        })
        onClose()
      },
    })
  }

  return (
    <div className="flex flex-col gap-5 px-5 pb-8">
      <DrawerHeader className="p-0 pt-2">
        <DrawerTitle className="sr-only">Detalle del movimiento</DrawerTitle>
        <div className="flex justify-end">
          {!isTransfer && <button
            onClick={onEdit}
            className="pressable text-[15px] font-medium text-primary"
          >
            Editar
          </button>}
        </div>
      </DrawerHeader>

      {/* Header: icono, monto protagonista, título */}
      <div className="flex flex-col items-center gap-2">
        {isTransfer ? <span className="flex size-12 items-center justify-center rounded-full bg-primary-soft text-primary"><ArrowLeftRight size={24} /></span> : <CategoryIcon
          icon={category?.icon ?? "wallet"}
          color={category?.color ?? CHART_OTHER.light}
          size={26}
          className="size-12"
        />}
        <span
          className={`tnum text-4xl font-bold tracking-tight ${
            isIncome ? "text-income" : ""
          }`}
        >
          {isTransfer ? (isInflow ? "+" : "−") : isIncome ? "+" : "−"}
          {formatMoney(transaction.amount)}
        </span>
        <p className="text-[15px] font-medium text-muted-foreground">
          {transaction.note || (isTransfer ? "Transferencia" : category?.name) || "Movimiento"}
        </p>
        {transaction.recurringRuleId && (
          <Badge variant="secondary" className="gap-1">
            <Repeat aria-hidden="true" />
            Recurrente
          </Badge>
        )}
        {plan && (
          <button
            type="button"
            onClick={() => setPlanSheetPlanId(plan.id)}
            aria-label="Ver plan de instalados de esta compra"
            className="pressable rounded-full bg-primary/12 px-2.5 py-1 text-[11px] font-semibold text-primary"
          >
            MSI · {plan.paidCount}/{plan.months}
          </button>
        )}
      </div>

      {/* Filas de detalle estilo lista iOS */}
      <div className="divide-y divide-border/50 overflow-hidden rounded-2xl bg-secondary">
        {isTransfer ? <>
          <DetailRow label={isInflow ? "Desde cuenta" : "A cuenta"} value={transaction.counterpartyAccountName ?? "—"} />
          <DetailRow label="Cuenta" value={account?.name ?? "—"} />
        </> : transaction.isSplit ? <>
          <DetailRow label="Asignaciones" value={`${transaction.splits.length} categorías`} />
          {transaction.splits.map((split) => <DetailRow key={split.categoryId} label={categories.find((item) => item.id === split.categoryId)?.name ?? "Categoría"} value={formatMoney(split.amount)} />)}
          <DetailRow label="Cuenta" value={account?.name ?? "—"} />
        </> : <>
          <DetailRow label="Categoría" value={category?.name ?? "—"} />
          <DetailRow label="Cuenta" value={account?.name ?? "—"} />
        </>}
        <DetailRow
          label="Fecha"
          value={longDateFmt.format(new Date(transaction.date + "T12:00:00"))}
        />
        <DetailRow label="Miembro" value={authorName ?? "—"} />
      </div>

      {/* Plan MSI para compras en tarjeta compartida */}
      {msiEligible && !plan && (
        <button
          type="button"
          onClick={() => setCreatePlanOpen(true)}
          className="pressable flex w-full items-center justify-center gap-2 rounded-2xl bg-primary/12 px-4 py-3 text-[14px] font-semibold text-primary"
        >
          <CreditCard size={16} aria-hidden="true" />
          Crear plan MSI
        </button>
      )}

      {/* Comprobantes */}
      {transaction.attachments.length > 0 && (
        <div>
          <p className="mb-2 text-[13px] font-medium text-muted-foreground">
            Comprobantes
          </p>
          <div className="divide-y divide-border/50 overflow-hidden rounded-2xl bg-secondary">
            {transaction.attachments.map((att) => (
              <AttachmentRow key={att.id} attachment={att} />
            ))}
          </div>
        </div>
      )}

      {/* Eliminar movimiento: dos pasos */}
      {confirmDelete ? (
        <div className="rounded-2xl bg-expense/10 p-4">
          <p className="text-center text-[13px] font-medium text-expense">
            ¿Eliminar esta {isTransfer ? "transferencia" : "movimiento"}? Podrás deshacerlo unos segundos.
          </p>
          <div className="mt-3 flex gap-2">
            <button
              onClick={() => setConfirmDelete(false)}
              className="pressable h-10 flex-1 rounded-xl bg-card text-[14px] font-semibold"
            >
              Cancelar
            </button>
            <button
              onClick={remove}
              disabled={deleteTransaction.isPending}
              className="pressable h-10 flex-1 rounded-xl bg-expense text-[14px] font-semibold text-white disabled:opacity-50"
            >
              Eliminar
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setConfirmDelete(true)}
          className="pressable w-full py-3 text-[15px] font-semibold text-expense"
        >
          Eliminar {isTransfer ? "transferencia" : "movimiento"}
        </button>
      )}

      <InstalmentPlanSheet
        open={planSheetPlanId !== null}
        onOpenChange={(open) => {
          if (!open) setPlanSheetPlanId(null)
        }}
        planId={planSheetPlanId}
      />
      <InstalmentPlanCreateSheet
        open={createPlanOpen}
        onOpenChange={setCreatePlanOpen}
        transaction={transaction}
        account={account}
      />
    </div>
  )
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 px-4 py-3">
      <span className="shrink-0 text-[14px] text-muted-foreground">
        {label}
      </span>
      <span className="truncate text-[14px] font-medium">{value}</span>
    </div>
  )
}

function AttachmentRow({ attachment }: { attachment: Attachment }) {
  const deleteAttachment = useDeleteAttachment()
  const [confirming, setConfirming] = useState(false)
  const isImage = attachment.contentType.startsWith("image/")
  const Icon = isImage ? ImageIcon : FileText

  async function view() {
    try {
      const blob = await apiFetchBlob(`/attachments/${attachment.id}`)
      const url = URL.createObjectURL(blob)
      window.open(url, "_blank")
    } catch (err) {
      console.error("Error al abrir el comprobante:", err)
    }
  }

  function remove() {
    if (!confirming) {
      setConfirming(true)
      return
    }
    deleteAttachment.mutate(attachment.id, {
      onSettled: () => setConfirming(false),
    })
  }

  return (
    <div className="flex items-center gap-3 px-4 py-2.5">
      <Icon size={18} className="shrink-0 text-muted-foreground" />
      <span className="min-w-0 flex-1 truncate text-[13px] font-medium">
        {attachment.filename}
      </span>
      <span className="tnum shrink-0 text-[12px] text-muted-foreground">
        {formatFileSize(attachment.sizeBytes)}
      </span>
      <button
        onClick={view}
        className="pressable shrink-0 rounded-full p-1.5 text-primary"
        aria-label="Ver comprobante"
      >
        <Eye size={16} />
      </button>
      <button
        onClick={remove}
        disabled={deleteAttachment.isPending}
        className={`pressable shrink-0 rounded-full p-1.5 text-expense transition-colors ${
          confirming ? "bg-expense/10" : ""
        }`}
        aria-label={
          confirming ? "¿Seguro? Toca para confirmar" : "Eliminar comprobante"
        }
      >
        <Trash2 size={16} />
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Modo edición
// ---------------------------------------------------------------------------

function EditForm({
  transaction,
  onCancel,
  onDone,
}: {
  transaction: Transaction
  onCancel: () => void
  onDone: () => void
}) {
  const { data: accounts = [] } = useAccounts()
  const { data: categories = [] } = useCategories()
  const updateTransaction = useUpdateTransaction()

  const [type, setType] = useState<TransactionType>(transaction.type)
  const [amountText, setAmountText] = useState(String(transaction.amount))
  const [categoryId, setCategoryId] = useState<string | null>(
    transaction.categoryId,
  )
  const [splitMode, setSplitMode] = useState(transaction.isSplit)
  const [splits, setSplits] = useState<Array<{ categoryId: string; amountText: string }>>(
    transaction.splits.map((split) => ({ categoryId: split.categoryId, amountText: String(split.amount) })),
  )
  const [accountId, setAccountId] = useState<string | null>(
    transaction.accountId,
  )
  const [date, setDate] = useState(transaction.date)
  const [note, setNote] = useState(transaction.note ?? "")

  const amount = Number(amountText.replace(",", ".")) || 0
  const visibleCategories = useMemo(
    () =>
      categories.filter(
        (c) => c.type === type && (c.active || c.id === categoryId),
      ),
    [categories, type, categoryId],
  )
  const effectiveAccountId =
    accountId ?? accounts.find((a) => a.kind === "debit")?.id ?? accounts[0]?.id
  const splitValues: TransactionSplit[] = splits
    .filter((split) => split.categoryId && Number(split.amountText.replace(",", ".")) > 0)
    .map((split) => ({ categoryId: split.categoryId, amount: Number(split.amountText.replace(",", ".")) }))
  const remaining = Math.round((amount - splitValues.reduce((total, split) => total + split.amount, 0)) * 10_000) / 10_000
  const canSave = amount > 0 && effectiveAccountId && date && (splitMode ? splitValues.length >= 2 && splitValues.length === splits.length && remaining === 0 : categoryId !== null)

  function save() {
    if (!canSave || !categoryId || !effectiveAccountId) return
    updateTransaction.mutate(
      {
        id: transaction.id,
        type,
        amount,
        categoryId: splitMode ? null : categoryId,
        accountId: effectiveAccountId,
        date,
        note: note.trim() || undefined,
        splits: splitMode ? splitValues : transaction.isSplit ? [] : undefined,
      },
      {
        onSuccess: () => {
          navigator.vibrate?.(10)
          onDone()
        },
      },
    )
  }

  const errorMessage =
    updateTransaction.error instanceof ApiError
      ? updateTransaction.error.message
      : updateTransaction.isError
        ? "No se pudieron guardar los cambios"
        : null

  return (
    <div className="flex flex-col gap-5 px-5 pb-8">
      <DrawerHeader className="p-0 pt-2">
        <DrawerTitle className="sr-only">Editar movimiento</DrawerTitle>
        <div className="flex items-center justify-between">
          <button
            onClick={onCancel}
            className="pressable text-[15px] font-medium text-muted-foreground"
          >
            Cancelar
          </button>
          {/* Segmented control estilo iOS */}
          <div className="flex rounded-xl bg-secondary p-1">
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
                    layoutId="detail-tx-type"
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
          <span className="w-14" aria-hidden="true" />
        </div>
      </DrawerHeader>

      {/* Monto */}
      <div className="flex items-baseline justify-center gap-1">
        <span className="text-2xl font-semibold text-muted-foreground">$</span>
        <input
          inputMode="decimal"
          placeholder="0"
          value={amountText}
          onChange={(e) =>
            setAmountText(e.target.value.replace(/[^0-9.,]/g, ""))
          }
          className="tnum w-48 bg-transparent text-center text-5xl font-bold tracking-tight outline-none placeholder:text-muted-foreground/40"
          aria-label="Monto"
        />
      </div>

      {/* Categorías */}
      <div>
        <p className="mb-2 text-[13px] font-medium text-muted-foreground">
          Categoría
        </p>
        <button type="button" onClick={() => {
          setSplitMode((value) => !value)
          if (!splitMode) setSplits([{ categoryId: "", amountText: "" }, { categoryId: "", amountText: "" }])
        }} className={`mb-3 rounded-full px-3 py-1.5 text-[12px] font-semibold ${splitMode ? "bg-primary text-primary-foreground" : "bg-secondary text-secondary-foreground"}`}>
          Dividir por categorías
        </button>
        {splitMode ? <div className="space-y-2 rounded-xl bg-secondary p-3">
          {splits.map((split, index) => <div key={index} className="flex gap-2">
            <select value={split.categoryId} onChange={(event) => setSplits((current) => current.map((row, rowIndex) => rowIndex === index ? { ...row, categoryId: event.target.value } : row))} className="min-w-0 flex-1 rounded-lg bg-card px-2 text-[13px]">
              <option value="">Categoría</option>
              {visibleCategories.filter((item) => item.id === split.categoryId || !splits.some((row, rowIndex) => rowIndex !== index && row.categoryId === item.id)).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
            <input inputMode="decimal" value={split.amountText} onChange={(event) => setSplits((current) => current.map((row, rowIndex) => rowIndex === index ? { ...row, amountText: event.target.value.replace(/[^0-9.,]/g, "") } : row))} className="tnum w-24 rounded-lg bg-card px-2 text-[13px]" aria-label={`Monto de asignación ${index + 1}`} />
            {splits.length > 2 && <button type="button" onClick={() => setSplits((current) => current.filter((_, rowIndex) => rowIndex !== index))} aria-label="Quitar asignación">×</button>}
          </div>)}
          <div className="flex justify-between text-[12px]"><button type="button" onClick={() => setSplits((current) => [...current, { categoryId: "", amountText: "" }])} className="font-semibold text-primary">+ Añadir categoría</button><span className={remaining === 0 ? "text-income" : "text-muted-foreground"}>Restante: {remaining.toFixed(2)}</span></div>
        </div> : <>
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
        </>}
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

      {/* Fecha */}
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

      {/* Nota opcional */}
      <input
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="Nota (opcional)"
        className="rounded-xl bg-secondary px-4 py-2.5 text-[15px] outline-none placeholder:text-muted-foreground"
      />

      {errorMessage && (
        <p className="rounded-xl bg-expense/10 px-3 py-2 text-[13px] text-expense">
          {errorMessage}
        </p>
      )}

      <Button
        size="lg"
        disabled={!canSave || updateTransaction.isPending}
        onClick={save}
        className="pressable h-12 rounded-2xl text-[16px] font-semibold"
      >
        Guardar cambios
      </Button>
    </div>
  )
}

/** Tamaño legible: KB/MB con 1 decimal. */
function formatFileSize(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / 1024).toFixed(1)} KB`
}
