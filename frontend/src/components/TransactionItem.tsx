import { formatMoney, formatShortDate } from "@/lib/format"
import type { Account, Category, Member, Transaction } from "@/lib/types"
import { CategoryIcon } from "@/components/CategoryIcon"

/**
 * Fila de transacción estilo lista iOS: icono de categoría a la izquierda,
 * nota/categoría prominente, monto alineado a la derecha con cifras
 * tabulares. Verde para ingresos, color de texto normal para gastos
 * (iOS no pinta los gastos de rojo en listas; el signo basta).
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
  return (
    <li className="pressable flex items-center gap-3 px-4 py-3">
      <CategoryIcon
        icon={category?.icon ?? "wallet"}
        color={category?.color ?? "#8e8e93"}
        className="size-10 shrink-0"
      />
      <div className="min-w-0 flex-1">
        <p className="truncate text-[15px] font-medium">
          {transaction.note || category?.name || "Movimiento"}
        </p>
        <p className="truncate text-[13px] text-muted-foreground">
          {[
            transaction.note ? category?.name : undefined,
            account?.name,
            member?.name,
            showDate ? formatShortDate(transaction.date) : undefined,
          ]
            .filter(Boolean)
            .join(" · ")}
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
