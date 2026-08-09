import { useState } from "react"
import { Plus, WalletCards } from "lucide-react"

import { BudgetBar } from "@/components/BudgetBar"
import { BudgetFormSheet } from "@/components/BudgetFormSheet"
import { CategoryIcon } from "@/components/CategoryIcon"
import { MonthPicker } from "@/components/ui/month-picker"
import { Card, EmptyState, IconButton, PageHeader } from "@/components/ui/surface"
import { formatMoney } from "@/lib/format"
import { useBudgets, useBudgetsStatus, useCategories } from "@/lib/queries"
import type { Budget, BudgetStatus, Category } from "@/lib/types"

export function BudgetsPage() {
  const [month, setMonth] = useState(currentMonth())
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Budget | undefined>()
  const { data: budgets = [] } = useBudgets()
  const { data: categories = [] } = useCategories()
  const { data: statuses = [], isLoading } = useBudgetsStatus(month)
  const monthName = new Intl.DateTimeFormat("es-MX", { month: "long", year: "numeric" }).format(new Date(`${month}-01T12:00:00`))

  function edit(budget?: Budget) { setEditing(budget); setFormOpen(true) }
  function effectiveBudget(categoryId: string) {
    return budgets.find((budget) => budget.categoryId === categoryId && budget.month?.slice(0, 7) === month)
      ?? budgets.find((budget) => budget.categoryId === categoryId && budget.month === null)
  }

  return <div className="flex max-w-3xl flex-col gap-5">
    <PageHeader title="Presupuestos" eyebrow="Planifica por categoría, mes a mes." action={<IconButton label="Crear presupuesto" variant="primary" onClick={() => edit()}><Plus size={20} strokeWidth={2.5} /></IconButton>} />
    <Card className="p-4 sm:p-5">
      <div className="flex items-center justify-between gap-3"><div><h2 className="capitalize text-[16px] font-semibold">{monthName}</h2><p className="mt-0.5 text-[12px] text-muted-foreground">Elige un mes para consultar o ajustar sus límites.</p></div><MonthPicker value={month} onChange={setMonth} label="Mes de presupuestos" /></div>
      {isLoading ? <p className="py-12 text-center text-[13px] text-muted-foreground">Cargando presupuestos...</p> : statuses.length === 0 ? <EmptyState icon={<WalletCards size={26} />} title="Sin presupuestos para este mes" hint="Crea un límite por categoría para ver cuánto puedes gastar." action={<button onClick={() => edit()} className="pressable rounded-full bg-primary px-5 py-2.5 text-[14px] font-semibold text-primary-foreground">Crear presupuesto</button>} /> : <ul className="mt-5 divide-y divide-border">{statuses.map((status) => <BudgetRow key={status.categoryId} status={status} category={categories.find((category) => category.id === status.categoryId)} onEdit={() => edit(effectiveBudget(status.categoryId))} />)}</ul>}
    </Card>
    <p className="px-2 text-[12px] leading-relaxed text-muted-foreground">Los límites predeterminados se aplican cuando no existe uno para el mes elegido. El sobrante solo se arrastra cuando activas esa opción.</p>
    <BudgetFormSheet open={formOpen} onOpenChange={setFormOpen} budget={editing} defaultMonth={month} />
  </div>
}

function BudgetRow({ status, category, onEdit }: { status: BudgetStatus; category?: Category; onEdit: () => void }) {
  const carries = status.available > status.budget
  return <li><button type="button" onClick={onEdit} className="pressable w-full px-1 py-4 text-left"><div className="mb-2 flex items-center justify-between gap-3"><span className="flex min-w-0 items-center gap-3"><CategoryIcon icon={category?.icon ?? "tag"} color={category?.color ?? "#64748b"} size={17} className="size-9" /><span className="min-w-0"><span className="block truncate text-[14px] font-semibold">{category?.name ?? "Categoría"}</span><span className="mt-0.5 block text-[12px] text-muted-foreground">{formatMoney(status.spent)} gastados de {formatMoney(status.available)}</span></span></span><span className={`tnum shrink-0 text-[13px] font-semibold ${status.percentage >= 100 ? "text-expense" : ""}`}>{Math.round(status.percentage)}%</span></div><BudgetBar percentage={status.percentage} />{carries && <p className="mt-1.5 text-[11px] text-muted-foreground">Incluye {formatMoney(status.available - status.budget)} acumulados.</p>}</button></li>
}

function currentMonth() { const today = new Date(); return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}` }
