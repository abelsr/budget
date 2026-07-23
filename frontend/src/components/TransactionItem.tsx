import { Paperclip } from "lucide-react"

import { formatMoney, formatShortDate } from "@/lib/format"
import { apiFetchBlob } from "@/lib/api"
import type { Account, Category, Member, Transaction } from "@/lib/types"
import { CategoryIcon } from "@/components/CategoryIcon"

/**
 * Fila de transacción estilo lista iOS: icono de categoría a la izquierda,
 * nota/categoría prominente, monto alineado a la derecha con cifras
 * tabulares. Verde para ingresos, color de texto normal para gastos
 * (iOS no pinta los gastos de rojo en listas; el signo basta).
 * Si hay comprobantes adjuntos, la fila los abre en una pestaña nueva.
 */
export function TransactionItem({
  transaction,
  category,
  account,
  member,
  showDate = false,
}: {
  transaction: Transaction
  category?: Category
  account?: Account
  member?: Member
  showDate?: boolean
}) {
  const isIncome = transaction.type === "income"
  const hasAttachments = transaction.attachments.length > 0

  async function openFirstAttachment() {
    const first = transaction.attachments[0]
    if (!first) return
    try {
      const blob = await apiFetchBlob(`/attachments/${first.id}`)
      const url = URL.createObjectURL(blob)
      window.open(url, "_blank")
    } catch (err) {
      console.error("Error al abrir el comprobante:", err)
    }
  }

  return (
    <li
      className={`pressable flex items-center gap-3 px-4 py-3 ${
        hasAttachments ? "cursor-pointer" : ""
      }`}
      role={hasAttachments ? "button" : undefined}
      onClick={hasAttachments ? openFirstAttachment : undefined}
    >
      <CategoryIcon
        icon={category?.icon ?? "wallet"}
        color={category?.color ?? "#8e8e93"}
        className="size-10 shrink-0"
      />
      <div className="min-w-0 flex-1">
        <p className="truncate text-[15px] font-medium">
          {transaction.note || category?.name || "Movimiento"}
        </p>
        <p className="flex items-center gap-1 truncate text-[13px] text-muted-foreground">
          <span className="truncate">
            {[
              transaction.note ? category?.name : undefined,
              account?.name,
              member?.name,
              showDate ? formatShortDate(transaction.date) : undefined,
            ]
              .filter(Boolean)
              .join(" · ")}
          </span>
          {hasAttachments && <Paperclip size={13} className="shrink-0" />}
        </p>
      </div>
      <span
        className={`tnum shrink-0 text-[15px] font-semibold ${
          isIncome ? "text-income" : ""
        }`}
      >
        {isIncome ? "+" : "−"}
        {formatMoney(transaction.amount)}
      </span>
    </li>
  )
}
