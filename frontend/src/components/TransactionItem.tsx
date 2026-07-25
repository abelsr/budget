import { useState } from "react"
import { Paperclip, Repeat } from "lucide-react"

import { formatMoney, formatShortDate } from "@/lib/format"
import type { Account, Category, Member, Transaction } from "@/lib/types"
import { CategoryIcon } from "@/components/CategoryIcon"
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
}: {
  transaction: Transaction
  category?: Category
  account?: Account
  member?: Member
  showDate?: boolean
}) {
  const [open, setOpen] = useState(false)
  const isIncome = transaction.type === "income"
  const hasAttachments = transaction.attachments.length > 0
  const isRecurring = Boolean(transaction.recurringRuleId)

  return (
    <>
      <li
        className="pressable flex cursor-pointer items-center gap-3 px-4 py-3"
        role="button"
        onClick={() => setOpen(true)}
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
            {isRecurring && (
              <Repeat
                size={13}
                className="shrink-0"
                aria-label="Movimiento recurrente"
              />
            )}
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
      <TransactionDetailSheet
        open={open}
        onOpenChange={setOpen}
        transaction={transaction}
        category={category}
        account={account}
        member={member}
      />
    </>
  )
}
