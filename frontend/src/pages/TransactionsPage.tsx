import { motion } from "motion/react"

import { formatDayHeader, formatMoney } from "@/lib/format"
import {
  useAccounts,
  useCategories,
  useMembers,
  useTransactions,
} from "@/lib/queries"
import { springAppear } from "@/lib/springs"
import { TransactionItem } from "@/components/TransactionItem"

/** Lista completa de movimientos, agrupada por día (estilo iOS). */
export function TransactionsPage() {
  const { data: accounts = [] } = useAccounts()
  const { data: categories = [] } = useCategories()
  const { data: members = [] } = useMembers()
  const { data: transactions = [] } = useTransactions()

  const byDay = new Map<string, typeof transactions>()
  for (const t of transactions) {
    const list = byDay.get(t.date) ?? []
    list.push(t)
    byDay.set(t.date, list)
  }

  return (
    <div className="flex flex-col gap-4">
      <header className="px-1">
        <h1 className="text-[34px] leading-tight font-bold tracking-tight">
          Movimientos
        </h1>
      </header>

      <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-2 xl:grid-cols-3">
        {[...byDay.entries()].map(([date, txs], i) => {
        const dayTotal = txs.reduce(
          (sum, t) => sum + (t.type === "income" ? t.amount : -t.amount),
          0,
        )
        return (
          <motion.section
            key={date}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ ...springAppear, delay: Math.min(i * 0.05, 0.3) }}
            className="rounded-3xl bg-card shadow-sm"
          >
            <div className="flex items-baseline justify-between px-4 pt-3 pb-1">
              <h2 className="text-[13px] font-semibold text-muted-foreground">
                {formatDayHeader(date)}
              </h2>
              <span
                className={`tnum text-[13px] font-medium ${
                  dayTotal >= 0 ? "text-income" : "text-muted-foreground"
                }`}
              >
                {dayTotal >= 0 ? "+" : "−"}
                {formatMoney(Math.abs(dayTotal))}
              </span>
            </div>
            <ul className="divide-y divide-border/60 pb-2">
              {txs.map((t) => (
                <TransactionItem
                  key={t.id}
                  transaction={t}
                  category={categories.find((c) => c.id === t.categoryId)}
                  account={accounts.find((a) => a.id === t.accountId)}
                  member={members.find((m) => m.id === t.memberId)}
                />
              ))}
            </ul>
          </motion.section>
        )
        })}
      </div>
    </div>
  )
}
