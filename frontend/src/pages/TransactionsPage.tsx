import { motion } from "motion/react"
import { Filter, Receipt, Search } from "lucide-react"

import { formatDayHeader, formatMoney } from "@/lib/format"
import {
  useAccounts,
  useCategories,
  useMembers,
  useTransactions,
} from "@/lib/queries"
import { springAppear } from "@/lib/springs"
import { TransactionItem } from "@/components/TransactionItem"
import { Card, EmptyState, PageHeader } from "@/components/ui/surface"

/**
 * Lista completa de movimientos: un solo libro, agrupado por día.
 *
 * Antes era una rejilla de tarjetas (una por día), que con un movimiento al
 * día se leía como confeti; el ledger de una columna deja comparar montos
 * verticalmente, que es para lo que sirve la pantalla.
 */
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
  const days = [...byDay.entries()]

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springAppear}
      className="flex max-w-3xl flex-col gap-4 lg:max-w-5xl"
    >
      <div className="hidden md:block">
        <PageHeader
          title="Movimientos"
          eyebrow={
            transactions.length > 0 &&
            `${transactions.length} ${transactions.length === 1 ? "registro" : "registros"}`
          }
        />
      </div>

      {/* Referencia visual hasta que el roadmap defina búsqueda y filtros. No son
          botones: así no sugieren una acción que todavía no existe. */}
      <header className="space-y-2 px-1 md:hidden">
        <h1 className="text-[18px] leading-tight font-bold tracking-[-0.02em]">
          Movimientos
        </h1>
        <div className="flex items-center gap-2" aria-hidden="true">
          <div className="flex h-8 min-w-0 flex-1 items-center gap-2 rounded-lg bg-secondary px-2.5 text-[11px] text-muted-foreground">
            <Search size={14} strokeWidth={2} />
            <span>Buscar movimientos</span>
          </div>
          <span className="flex size-8 items-center justify-center text-muted-foreground">
            <Filter size={15} strokeWidth={2} />
          </span>
        </div>
        <p className="sr-only">
          La búsqueda y los filtros estarán disponibles próximamente.
        </p>
      </header>

      {days.length === 0 ? (
        <Card>
          <EmptyState
            icon={<Receipt size={26} />}
            title="Todavía no hay movimientos"
            hint="Registra tu último gasto con el botón + y aparecerá aquí, agrupado por día."
          />
        </Card>
      ) : (
        <Card>
          {/* Cabecera de columnas, solo escritorio.
              `rounded-t-3xl` empareja con la esquina del Card; sin esto y sin
              `overflow-hidden`, el fondo se sale por arriba. */}
          <div className="hidden items-center gap-4 rounded-t-3xl border-b border-border px-4 py-2 text-[11px] font-semibold tracking-wide text-muted-foreground uppercase md:grid md:grid-cols-[minmax(0,1fr)_10rem_auto]">
            <span>Movimiento</span>
            <span className="text-right">Cuenta</span>
            <span className="text-right">Importe</span>
          </div>
          {days.map(([date, txs], dayIdx) => {
            const dayTotal = txs.reduce(
              (sum, t) => sum + (t.type === "income" ? t.amount : -t.amount),
              0,
            )
            return (
              <section key={date}>
                {/* Cabecera de día: se queda pegada mientras se recorre el día.
                    En móvil el primer día es el primer hijo visible del Card,
                    así que necesita `rounded-t-3xl` para no salirse por arriba
                    (no usamos `overflow-hidden` porque rompería `position: sticky`). */}
                <div
                  className={`sticky top-0 z-10 flex items-baseline justify-between border-y border-border bg-secondary/60 px-4 py-1.5 backdrop-blur-sm ${
                    dayIdx === 0 ? "rounded-t-3xl md:rounded-t-none" : ""
                  }`}
                >
                  <h2 className="text-[12px] font-semibold tracking-wide text-muted-foreground">
                    {formatDayHeader(date)}
                  </h2>
                  <span
                    className={`tnum text-[12px] font-semibold ${
                      dayTotal >= 0 ? "text-income" : "text-muted-foreground"
                    }`}
                  >
                    {dayTotal >= 0 ? "+" : "−"}
                    {formatMoney(Math.abs(dayTotal))}
                  </span>
                </div>
                <ul className="divide-y divide-border">
                  {txs.map((t) => (
                    <TransactionItem
                      key={t.id}
                      transaction={t}
                      category={categories.find((c) => c.id === t.categoryId)}
                      account={accounts.find((a) => a.id === t.accountId)}
                      member={members.find((m) => m.id === t.memberId)}
                      ledger
                    />
                  ))}
                </ul>
              </section>
            )
          })}
        </Card>
      )}
    </motion.div>
  )
}
