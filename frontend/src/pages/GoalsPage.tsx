import { useState } from "react"
import { MoreHorizontal, PiggyBank, Plus } from "lucide-react"

import { CategoryIcon } from "@/components/CategoryIcon"
import { SavingsGoalContributionSheet, SavingsGoalFormSheet } from "@/components/SavingsGoalSheets"
import { Card, EmptyState, IconButton, PageHeader } from "@/components/ui/surface"
import { formatMoney } from "@/lib/format"
import { useAccounts, useGoals, useUpdateGoal } from "@/lib/queries"
import type { SavingsGoal } from "@/lib/types"

export function GoalsPage() {
  const [showArchived, setShowArchived] = useState(false)
  const [formOpen, setFormOpen] = useState(false)
  const [contributionOpen, setContributionOpen] = useState(false)
  const [editing, setEditing] = useState<SavingsGoal | undefined>()
  const [contributing, setContributing] = useState<SavingsGoal | undefined>()
  const { data: goals = [], isLoading } = useGoals()
  const { data: accounts = [] } = useAccounts()
  const updateGoal = useUpdateGoal()
  const visibleGoals = goals.filter((goal) => showArchived || !goal.archived)
  function edit(goal?: SavingsGoal) { setEditing(goal); setFormOpen(true) }

  return <div className="flex max-w-4xl flex-col gap-5">
    <PageHeader title="Metas de ahorro" eyebrow="Aportes manuales, independientes de tus movimientos." action={<IconButton label="Crear meta de ahorro" variant="primary" onClick={() => edit()}><Plus size={20} strokeWidth={2.5} /></IconButton>} />
    {goals.some((goal) => goal.archived) && <label className="flex w-fit cursor-pointer items-center gap-2 px-1 text-[12px] text-muted-foreground"><input type="checkbox" checked={showArchived} onChange={(event) => setShowArchived(event.target.checked)} /> Mostrar archivadas</label>}
    {isLoading ? <Card className="py-12 text-center text-[13px] text-muted-foreground">Cargando metas...</Card> : visibleGoals.length === 0 ? <Card><EmptyState icon={<PiggyBank size={26} />} title="Sin metas de ahorro" hint="Define lo que quieres alcanzar y registra tus aportes manuales." action={<button onClick={() => edit()} className="pressable rounded-full bg-primary px-5 py-2.5 text-[14px] font-semibold text-primary-foreground">Crear meta</button>} /></Card> : <div className="grid gap-4 md:grid-cols-2">{visibleGoals.map((goal) => <GoalCard key={goal.id} goal={goal} accountName={accounts.find((account) => account.id === goal.accountId)?.name} onEdit={() => edit(goal)} onContribute={() => { setContributing(goal); setContributionOpen(true) }} onArchive={() => updateGoal.mutate({ id: goal.id, archived: !goal.archived })} />)}</div>}
    <SavingsGoalFormSheet open={formOpen} onOpenChange={setFormOpen} goal={editing} />
    <SavingsGoalContributionSheet open={contributionOpen} onOpenChange={setContributionOpen} goal={contributing} />
  </div>
}

function GoalCard({ goal, accountName, onEdit, onContribute, onArchive }: { goal: SavingsGoal; accountName?: string; onEdit: () => void; onContribute: () => void; onArchive: () => void }) {
  const planText = goal.planStatus === "active" && goal.requiredMonthlyContribution !== null ? `Aparta ${formatMoney(goal.requiredMonthlyContribution)} al mes` : goal.planStatus === "paused" ? "Plan pausado" : goal.planStatus === "overdue" ? "Objetivo vencido" : null
  return <Card className={`p-5 ${goal.archived ? "opacity-60" : ""}`}><div className="flex items-start gap-3"><CategoryIcon icon={goal.icon} color={goal.color} className="size-11" size={21} /><div className="min-w-0 flex-1"><div className="flex items-start justify-between gap-2"><div className="min-w-0"><h2 className="truncate text-[16px] font-semibold">{goal.name}</h2><p className="mt-0.5 text-[12px] text-muted-foreground">{accountName ?? (goal.targetDate ? `Para ${new Date(`${goal.targetDate}T12:00:00`).toLocaleDateString("es-MX", { month: "long", year: "numeric" })}` : "Sin cuenta vinculada")}</p></div><button onClick={onEdit} aria-label={`Editar ${goal.name}`} className="pressable rounded-full p-1.5 text-muted-foreground"><MoreHorizontal size={18} /></button></div></div></div><div className="mt-5 h-2 overflow-hidden rounded-full bg-secondary"><div className="h-full rounded-full transition-[width] duration-500" style={{ width: `${goal.progressPct}%`, backgroundColor: goal.color }} /></div><div className="mt-2 flex items-end justify-between gap-3"><p className="tnum text-[18px] font-bold">{formatMoney(goal.currentAmount)} <span className="text-[12px] font-medium text-muted-foreground">de {formatMoney(goal.targetAmount)}</span></p><span className="tnum text-[13px] font-semibold text-muted-foreground">{goal.progressPct}%</span></div><p className="mt-1 text-[12px] text-muted-foreground">Faltan {formatMoney(goal.remaining)}{planText ? ` · ${planText}` : ""}</p><div className="mt-4 flex gap-2"><button onClick={onContribute} disabled={goal.archived} className="pressable flex-1 rounded-xl bg-primary py-2.5 text-[13px] font-semibold text-primary-foreground disabled:opacity-50">Aportar</button><button onClick={onArchive} className="pressable rounded-xl bg-secondary px-4 py-2.5 text-[13px] font-semibold">{goal.archived ? "Reactivar" : "Archivar"}</button></div></Card>
}
