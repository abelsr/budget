import { useState } from "react"
import { AlertCircle, ArrowLeftRight, CloudUpload, Paperclip, Repeat } from "lucide-react"

import { formatMoney, formatShortDate } from "@/lib/format"
import type { Account, Category, Member, Transaction } from "@/lib/types"
import { CategoryIcon } from "@/components/CategoryIcon"
import { BrandMedallion } from "@/components/BrandMedallion"
import { matchBrand } from "@/lib/brands"
import { CHART_OTHER } from "@/lib/chart-colors"
import { TransactionDetailSheet } from "@/components/TransactionDetailSheet"

/**
 * Fila de transacción estilo lista iOS: icono de categoría a la izquierda,
 * nota/categoría prominente, monto alineado a la derecha con cifras
 * tabulares. Verde para ingresos, color de texto normal para gastos
 * (iOS no pinta los gastos de rojo en listas; el signo basta).
 * Click → abre el sheet de detalle/edición (los comprobantes se
 * ven y eliminan desde ahí; el clip solo es indicador visual).
 */
export function TransactionItem({
  transaction,
  category,
  account,
  member,
  showDate = false,
  ledger = false,
  hideAmount = false,
}: {
  transaction: Transaction
  category?: Category
  account?: Account
  member?: Member
  showDate?: boolean
  ledger?: boolean
  /** Dashboard privacy control; the transaction remains actionable. */
  hideAmount?: boolean
}) {
  const [open, setOpen] = useState(false)
  const isIncome = transaction.type === "income"
  const isTransfer = transaction.type === "transfer"
  const isInflow = transaction.transferDirection === "inflow"
  const hasAttachments = transaction.attachments.length > 0
  const isRecurring = Boolean(transaction.recurringRuleId)
  const authorName = transaction.authorName ?? member?.name
  const syncLabel = transaction.syncStatus === "failed" ? transaction.syncError ?? "No se pudo subir" : "Pendiente de subir"

  // Comercio reconocido por la nota → medallón de marca (fallback: categoría).
  const brand = matchBrand(transaction.note)

  // La cuenta es una columna propia en el ledger de escritorio; fuera de él va
  // en la línea de metadatos. En móvil (donde la columna está oculta) vuelve a
  // los metadatos. Nunca en ambas, §9.
  const meta = [
    isTransfer ? transaction.counterpartyAccountName && `→ ${transaction.counterpartyAccountName}` : transaction.note ? category?.name : undefined,
    ledger ? undefined : account?.name,
    authorName,
    showDate ? formatShortDate(transaction.date) : undefined,
  ]
    .filter(Boolean)
    .join(" · ")

  return (
    <>
      <li
        className={`pressable flex cursor-pointer items-center gap-3 px-4 py-3 ${
          ledger ? "md:grid md:grid-cols-[minmax(0,1fr)_10rem_auto] md:gap-4" : ""
        }`}
        role="button"
        onClick={() => !transaction.syncStatus && setOpen(true)}
      >
        {brand ? (
          <BrandMedallion brand={brand} className="size-10 shrink-0" />
        ) : (
          isTransfer ? <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-primary-soft text-primary"><ArrowLeftRight size={19} /></span> : <CategoryIcon icon={category?.icon ?? "wallet"} color={category?.color ?? CHART_OTHER.light} className="size-10 shrink-0" />
        )}
        <div className="min-w-0 flex-1">
          <p className="truncate text-[15px] font-medium">
            {transaction.note || (isTransfer ? "Transferencia" : category?.name) || "Movimiento"}
          </p>
          <p className="flex items-center gap-1 truncate text-[13px] text-muted-foreground">
            <span className="truncate">
              {meta}
              {ledger && (
                <>
                  {meta && <span aria-hidden="true"> · </span>}
                  <span className="md:hidden">{account?.name ?? "—"}</span>
                </>
              )}
            </span>
            {isRecurring && (
              <Repeat
                size={13}
                className="shrink-0"
                aria-label="Movimiento recurrente"
              />
            )}
            {hasAttachments && <Paperclip size={13} className="shrink-0" />}
            {transaction.syncStatus && (
              <span
                title={syncLabel}
                className={`inline-flex shrink-0 items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium ${
                  transaction.syncStatus === "failed" ? "bg-destructive/10 text-destructive" : "bg-primary-soft text-primary"
                }`}
              >
                {transaction.syncStatus === "failed" ? <AlertCircle size={11} /> : <CloudUpload size={11} />}
                {transaction.syncStatus === "failed" ? "Error al subir" : "Pendiente"}
              </span>
            )}
          </p>
          {transaction.syncStatus === "failed" && <p className="mt-0.5 truncate text-[11px] text-destructive">No se subió: {syncLabel}</p>}
        </div>
        {ledger && (
          <span className="hidden min-w-0 truncate text-right text-[13px] text-muted-foreground md:block">
            {account?.name ?? "—"}
          </span>
        )}
        <span
          className={`tnum shrink-0 text-[15px] font-semibold ${
            isIncome ? "text-income" : ""
          }`}
        >
          {hideAmount ? "••••••" : <>{isTransfer ? (isInflow ? "+" : "−") : isIncome ? "+" : "−"}{formatMoney(transaction.amount)}</>}
        </span>
      </li>
      {!transaction.syncStatus && <TransactionDetailSheet open={open} onOpenChange={setOpen} transaction={transaction} category={category} account={account} member={member} />}
    </>
  )
}
