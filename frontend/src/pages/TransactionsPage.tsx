import { motion } from "motion/react"
import { Receipt, Search, X } from "lucide-react"
import { useSearchParams } from "react-router-dom"
import { useEffect, useState } from "react"

import { formatDayHeader, formatMoney } from "@/lib/format"
import {
  useAccounts,
  useCategories,
  useMembers,
  useTransactions,
} from "@/lib/queries"
import type { TransactionFilters } from "@/lib/queries"
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
  const [searchParams, setSearchParams] = useSearchParams()
  const [searchQuery, setSearchQuery] = useState(() => searchParams.get("q") ?? "")
  const { data: accounts = [] } = useAccounts()
  const { data: categories = [] } = useCategories()
  const { data: members = [] } = useMembers()
  const filters: TransactionFilters = {
    q: searchParams.get("q") ?? undefined,
    categoryId: searchParams.get("categoryId") ?? undefined,
    accountId: searchParams.get("accountId") ?? undefined,
    memberId: searchParams.get("memberId") ?? undefined,
    type: (searchParams.get("type") as TransactionFilters["type"]) ?? undefined,
    from: searchParams.get("from") ?? undefined,
    to: searchParams.get("to") ?? undefined,
  }
  const { data: transactions = [] } = useTransactions(filters)
  const hasFilters = Object.values(filters).some(Boolean)
  useEffect(() => {
    if (searchQuery === (filters.q ?? "")) return
    const timeout = window.setTimeout(() => {
      setSearchParams((current) => {
        const next = new URLSearchParams(current)
        if (searchQuery) next.set("q", searchQuery)
        else next.delete("q")
        return next
      })
    }, 300)
    return () => window.clearTimeout(timeout)
  }, [filters.q, searchQuery, setSearchParams])
  const setFilter = (name: keyof TransactionFilters, value: string) => {
    setSearchParams((current) => {
      const next = new URLSearchParams(current)
      if (value) next.set(name, value)
      else next.delete(name)
      return next
    })
  }
  const clearFilters = () => {
    setSearchQuery("")
    setSearchParams((current) => {
      const next = new URLSearchParams(current)
      for (const name of ["q", "categoryId", "accountId", "memberId", "type", "from", "to"]) next.delete(name)
      return next
    })
  }

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

      <header className="space-y-2 px-1 md:hidden">
        <h1 className="text-[18px] leading-tight font-bold tracking-[-0.02em]">
          Movimientos
        </h1>
      </header>

      <section aria-label="Buscar y filtrar movimientos" className="rounded-2xl border border-border bg-card p-2.5 shadow-sm">
        <div className="flex items-center gap-2">
          <label className="flex min-w-0 flex-1 items-center gap-2 rounded-lg bg-secondary px-2.5 text-muted-foreground">
            <Search size={14} aria-hidden="true" />
            <span className="sr-only">Buscar en notas</span>
            <input
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="Buscar en notas"
              className="h-8 min-w-0 flex-1 bg-transparent text-[12px] text-foreground outline-none placeholder:text-muted-foreground"
            />
          </label>
          {hasFilters && <button onClick={clearFilters} className="pressable flex h-8 items-center gap-1 rounded-lg px-2 text-[11px] font-medium text-primary hover:bg-primary-soft"><X size={14} />Limpiar</button>}
        </div>
        <div className="mt-2 grid grid-cols-2 gap-1.5 sm:grid-cols-3 lg:grid-cols-6">
          <FilterSelect label="Tipo" value={filters.type ?? ""} onChange={(value) => setFilter("type", value)} options={[["expense", "Gastos"], ["income", "Ingresos"]]} />
          <FilterSelect label="Categoría" value={filters.categoryId ?? ""} onChange={(value) => setFilter("categoryId", value)} options={categories.map((category) => [category.id, category.name])} />
          <FilterSelect label="Cuenta" value={filters.accountId ?? ""} onChange={(value) => setFilter("accountId", value)} options={accounts.map((account) => [account.id, account.name])} />
          <FilterSelect label="Miembro" value={filters.memberId ?? ""} onChange={(value) => setFilter("memberId", value)} options={members.map((member) => [member.id, member.name])} />
          <label className="relative"><span className="sr-only">Desde</span><input type="date" value={filters.from ?? ""} onChange={(event) => setFilter("from", event.target.value)} className="h-8 w-full rounded-lg border border-input bg-background px-2 text-[11px] outline-none focus:ring-2 focus:ring-ring/30" /></label>
          <label className="relative"><span className="sr-only">Hasta</span><input type="date" value={filters.to ?? ""} onChange={(event) => setFilter("to", event.target.value)} className="h-8 w-full rounded-lg border border-input bg-background px-2 text-[11px] outline-none focus:ring-2 focus:ring-ring/30" /></label>
        </div>
      </section>

      {days.length === 0 ? (
        <Card>
          <EmptyState
            icon={<Receipt size={26} />}
            title={hasFilters ? "No encontramos movimientos" : "Todavía no hay movimientos"}
            hint={hasFilters ? "Prueba con otros filtros o vuelve a ver todos tus movimientos." : "Registra tu último gasto con el botón + y aparecerá aquí, agrupado por día."}
            action={hasFilters ? <button onClick={clearFilters} className="pressable rounded-lg bg-primary px-3 py-2 text-[12px] font-medium text-primary-foreground">Limpiar filtros</button> : undefined}
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

function FilterSelect({ label, value, onChange, options }: { label: string; value: string; onChange: (value: string) => void; options: string[][] }) {
  return <label><span className="sr-only">{label}</span><select value={value} onChange={(event) => onChange(event.target.value)} className="h-8 w-full rounded-lg border border-input bg-background px-2 text-[11px] text-foreground outline-none focus:ring-2 focus:ring-ring/30"><option value="">{label}</option>{options.map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label>
}
