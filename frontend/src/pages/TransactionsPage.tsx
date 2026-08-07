import { motion } from "motion/react"
import { CalendarDays, Landmark, Receipt, Search, SlidersHorizontal, X } from "lucide-react"
import { useSearchParams } from "react-router-dom"
import { useEffect, useState } from "react"

import { formatDayHeader, formatMoney, toISODate } from "@/lib/format"
import {
  useAccounts,
  useCategories,
  useMembers,
  useTransactions,
} from "@/lib/queries"
import type { TransactionFilters } from "@/lib/queries"
import { springAppear } from "@/lib/springs"
import { TransactionItem } from "@/components/TransactionItem"
import { ReconciliationSheet } from "@/components/ReconciliationSheet"
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
  const [advancedFiltersOpen, setAdvancedFiltersOpen] = useState(() =>
    Boolean(
      searchParams.get("categoryId") ||
        searchParams.get("accountId") ||
        searchParams.get("memberId") ||
        searchParams.get("from") ||
        searchParams.get("to"),
    ),
  )
  const [reconciliationOpen, setReconciliationOpen] = useState(false)
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
  // A complete pair is one user action in the household ledger. When a member
  // can only see one side (for example, another member's personal account),
  // retain that independently reconcilable row instead.
  const visibleTransactions = transactions.filter((transaction) => {
    if (transaction.type !== "transfer" || transaction.transferDirection !== "inflow" || !transaction.transferGroupId) return true
    return transactions.filter((candidate) => candidate.transferGroupId === transaction.transferGroupId).length !== 2
  })
  const hasFilters = Object.values(filters).some(Boolean)
  const quickPeriods = getQuickPeriods()
  const activePeriod = quickPeriods.find(
    (period) => filters.from === period.from && filters.to === period.to,
  )?.id
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
  const setPeriod = (period: QuickPeriod | null) => {
    setSearchParams((current) => {
      const next = new URLSearchParams(current)
      if (period) {
        next.set("from", period.from)
        next.set("to", period.to)
      } else {
        next.delete("from")
        next.delete("to")
      }
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
  for (const t of visibleTransactions) {
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
            visibleTransactions.length > 0 &&
            `${visibleTransactions.length} ${visibleTransactions.length === 1 ? "registro" : "registros"}`
          }
        />
      </div>

      <header className="space-y-2 px-1 md:hidden">
        <h1 className="text-[18px] leading-tight font-bold tracking-[-0.02em]">
          Movimientos
        </h1>
      </header>

      <section aria-label="Buscar y filtrar movimientos" className="rounded-2xl border border-border bg-card p-3 shadow-sm sm:p-3.5">
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
          {hasFilters && <button type="button" onClick={clearFilters} className="pressable flex h-9 shrink-0 items-center gap-1 rounded-lg px-2 text-[11px] font-medium text-primary hover:bg-primary-soft"><X size={14} aria-hidden="true" />Limpiar</button>}
        </div>

        <div className="mt-3 flex items-center gap-2 overflow-x-auto pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden" role="group" aria-label="Tipo de movimiento">
          {(["", "expense", "income", "transfer"] as const).map((type) => {
            const label = type === "expense" ? "Gastos" : type === "income" ? "Ingresos" : type === "transfer" ? "Transferencias" : "Todos"
            return <button key={label} type="button" onClick={() => setFilter("type", type)} aria-pressed={(filters.type ?? "") === type} className={`pressable h-8 shrink-0 rounded-full px-3 text-[12px] font-medium transition-colors ${(filters.type ?? "") === type ? "bg-primary text-primary-foreground" : "bg-secondary text-secondary-foreground hover:bg-muted"}`}>{label}</button>
          })}
        </div>

        <div className="mt-2 flex items-center gap-2 overflow-x-auto pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden" role="group" aria-label="Periodo">
          <CalendarDays size={15} className="shrink-0 text-muted-foreground" aria-hidden="true" />
          {quickPeriods.map((period) => <button key={period.id} type="button" onClick={() => setPeriod(activePeriod === period.id ? null : period)} aria-pressed={activePeriod === period.id} className={`pressable h-8 shrink-0 rounded-full border px-3 text-[11px] font-medium transition-colors ${activePeriod === period.id ? "border-primary bg-primary-soft text-primary" : "border-border bg-background text-muted-foreground hover:bg-secondary"}`}>{period.label}</button>)}
          <button type="button" onClick={() => setAdvancedFiltersOpen((open) => !open)} aria-expanded={advancedFiltersOpen} aria-controls="advanced-transaction-filters" className={`pressable flex h-8 shrink-0 items-center gap-1 rounded-full border px-3 text-[11px] font-medium transition-colors ${advancedFiltersOpen ? "border-primary bg-primary-soft text-primary" : "border-border bg-background text-muted-foreground hover:bg-secondary"}`}><SlidersHorizontal size={14} aria-hidden="true" />Más filtros</button>
        </div>

        {hasFilters && <ActiveFilterChips filters={filters} categories={categories} accounts={accounts} members={members} activePeriod={activePeriod} onRemove={(name) => {
          if (name === "period") setPeriod(null)
          else {
            if (name === "q") setSearchQuery("")
            setFilter(name, "")
          }
        }} />}

        {advancedFiltersOpen && (
          <div id="advanced-transaction-filters" className="mt-3 grid grid-cols-1 gap-2 border-t border-border pt-3 sm:grid-cols-2 lg:grid-cols-5">
            <FilterSelect label="Categoría" value={filters.categoryId ?? ""} onChange={(value) => setFilter("categoryId", value)} options={categories.map((category) => [category.id, category.name])} />
            <FilterSelect label="Cuenta" value={filters.accountId ?? ""} onChange={(value) => setFilter("accountId", value)} options={accounts.map((account) => [account.id, account.name])} />
            <FilterSelect label="Miembro" value={filters.memberId ?? ""} onChange={(value) => setFilter("memberId", value)} options={members.map((member) => [member.id, member.name])} />
            <DateFilter label="Desde" value={filters.from ?? ""} onChange={(value) => setFilter("from", value)} />
            <DateFilter label="Hasta" value={filters.to ?? ""} onChange={(value) => setFilter("to", value)} />
          </div>
        )}
        {filters.accountId && accounts.find((account) => account.id === filters.accountId) && <button type="button" onClick={() => setReconciliationOpen(true)} className="pressable mt-3 flex h-8 items-center gap-1.5 rounded-lg bg-primary-soft px-3 text-[11px] font-semibold text-primary"><Landmark size={14} />Conciliar esta cuenta</button>}
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
              (sum, t) => sum + (t.type === "income" ? t.amount : t.type === "expense" ? -t.amount : 0),
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
      {filters.accountId && accounts.find((account) => account.id === filters.accountId) && <ReconciliationSheet account={accounts.find((account) => account.id === filters.accountId)!} open={reconciliationOpen} onOpenChange={setReconciliationOpen} />}
    </motion.div>
  )
}

function FilterSelect({ label, value, onChange, options }: { label: string; value: string; onChange: (value: string) => void; options: string[][] }) {
  return <label className="flex min-w-0 flex-col gap-1"><span className="text-[11px] font-medium text-muted-foreground">{label}</span><select value={value} onChange={(event) => onChange(event.target.value)} className="h-9 w-full rounded-lg border border-input bg-background px-2 text-[12px] text-foreground outline-none focus:ring-2 focus:ring-ring/30"><option value="">Todas</option>{options.map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label>
}

function DateFilter({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return <label className="flex min-w-0 flex-col gap-1"><span className="text-[11px] font-medium text-muted-foreground">{label}</span><input type="date" value={value} onChange={(event) => onChange(event.target.value)} className="h-9 w-full rounded-lg border border-input bg-background px-2 text-[12px] outline-none focus:ring-2 focus:ring-ring/30" /></label>
}

type QuickPeriod = { id: "month" | "30d"; label: string; from: string; to: string }

function getQuickPeriods(): QuickPeriod[] {
  const today = new Date()
  const fromMonth = new Date(today.getFullYear(), today.getMonth(), 1)
  const fromThirtyDays = new Date(today)
  fromThirtyDays.setDate(today.getDate() - 29)
  return [
    { id: "month", label: "Este mes", from: toISODate(fromMonth), to: toISODate(today) },
    { id: "30d", label: "Últimos 30 días", from: toISODate(fromThirtyDays), to: toISODate(today) },
  ]
}

function ActiveFilterChips({ filters, categories, accounts, members, activePeriod, onRemove }: { filters: TransactionFilters; categories: { id: string; name: string }[]; accounts: { id: string; name: string }[]; members: { id: string; name: string }[]; activePeriod?: QuickPeriod["id"]; onRemove: (name: keyof TransactionFilters | "period") => void }) {
  const periodLabel = activePeriod === "month" ? "Este mes" : activePeriod === "30d" ? "Últimos 30 días" : filters.from || filters.to ? "Fechas personalizadas" : null
  const chips: { name: keyof TransactionFilters | "period"; label: string }[] = [
    filters.q ? { name: "q", label: `Búsqueda: ${filters.q}` } : null,
    filters.type ? { name: "type", label: filters.type === "expense" ? "Gastos" : filters.type === "income" ? "Ingresos" : "Transferencias" } : null,
    filters.categoryId ? { name: "categoryId", label: categories.find((category) => category.id === filters.categoryId)?.name ?? "Categoría" } : null,
    filters.accountId ? { name: "accountId", label: accounts.find((account) => account.id === filters.accountId)?.name ?? "Cuenta" } : null,
    filters.memberId ? { name: "memberId", label: members.find((member) => member.id === filters.memberId)?.name ?? "Miembro" } : null,
    periodLabel ? { name: "period", label: periodLabel } : null,
  ].filter((chip): chip is { name: keyof TransactionFilters | "period"; label: string } => chip !== null)

  return <div className="mt-3 flex flex-wrap gap-1.5" aria-label="Filtros activos">{chips.map((chip) => <button key={`${chip.name}-${chip.label}`} type="button" onClick={() => onRemove(chip.name)} className="pressable inline-flex h-7 max-w-full items-center gap-1 rounded-full bg-primary-soft px-2 text-[11px] font-medium text-primary"><span className="truncate">{chip.label}</span><X size={13} aria-hidden="true" /></button>)}</div>
}
