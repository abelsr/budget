import { useState } from "react"
import { Trash2, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import { CategoryIcon } from "@/components/CategoryIcon"
import { Drawer, DrawerClose, DrawerContent, DrawerHeader, DrawerTitle } from "@/components/ui/drawer"
import { DatePicker } from "@/components/ui/date-picker"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ApiError } from "@/lib/api"
import { CHART_PALETTE_LIGHT } from "@/lib/chart-colors"
import { formatMoney } from "@/lib/format"
import { useAccounts, useContributeToGoal, useCreateGoal, useDeleteGoal, useUpdateGoal } from "@/lib/queries"
import type { SavingsGoal } from "@/lib/types"

const ICONS = ["piggy-bank", "wallet", "house", "car", "heart-pulse", "gamepad-2", "banknote", "hand-coins"]
const COLORS = [...CHART_PALETTE_LIGHT, "#0e7490", "#4f46e5", "#e11d48", "#64748b"]

function errorMessage(error: unknown) {
  return error instanceof ApiError ? error.message : "Ocurrió un error. Intenta de nuevo."
}

function parseAmount(value: string) {
  return Number(value.replace(",", "."))
}

function cleanAmount(value: string) {
  return value.replace(/[^0-9.,-]/g, "")
}

export function SavingsGoalFormSheet({ open, onOpenChange, goal }: { open: boolean; onOpenChange: (open: boolean) => void; goal?: SavingsGoal }) {
  return <Drawer open={open} onOpenChange={onOpenChange} showSwipeHandle><DrawerContent className="mx-auto max-w-lg">{open && <GoalForm key={goal?.id ?? "new"} goal={goal} onDone={() => onOpenChange(false)} />}</DrawerContent></Drawer>
}

function GoalForm({ goal, onDone }: { goal?: SavingsGoal; onDone: () => void }) {
  const editing = goal !== undefined
  const { data: accounts = [] } = useAccounts()
  const createGoal = useCreateGoal()
  const updateGoal = useUpdateGoal()
  const deleteGoal = useDeleteGoal()
  const [name, setName] = useState(goal?.name ?? "")
  const [targetAmount, setTargetAmount] = useState(goal ? String(goal.targetAmount) : "")
  const [currentAmount, setCurrentAmount] = useState(goal ? String(goal.currentAmount) : "")
  const [targetDate, setTargetDate] = useState(goal?.targetDate ?? "")
  const [accountId, setAccountId] = useState(goal?.accountId ?? "")
  const [icon, setIcon] = useState(goal?.icon ?? ICONS[0])
  const [color, setColor] = useState(goal?.color ?? COLORS[0])
  const [planPaused, setPlanPaused] = useState(goal?.planPaused ?? false)
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const pending = createGoal.isPending || updateGoal.isPending || deleteGoal.isPending
  const target = parseAmount(targetAmount)
  const current = parseAmount(currentAmount || "0")
  const canSave = name.trim().length > 0 && target > 0 && Number.isFinite(target) && Number.isFinite(current) && !pending

  function save() {
    if (!canSave) return
    setError(null)
    const input = { name: name.trim(), targetAmount: target, targetDate: targetDate || null, accountId: accountId || null, icon, color, planPaused }
    if (editing) updateGoal.mutate({ id: goal.id, ...input }, { onSuccess: onDone, onError: (err) => setError(errorMessage(err)) })
    else createGoal.mutate({ ...input, currentAmount: current }, { onSuccess: onDone, onError: (err) => setError(errorMessage(err)) })
  }

  function remove() {
    if (!goal) return
    if (!confirmingDelete) return setConfirmingDelete(true)
    deleteGoal.mutate(goal.id, { onSuccess: onDone, onError: (err) => setError(errorMessage(err)) })
  }

  return <form className="flex max-h-[calc(100dvh-2rem)] flex-col gap-5 overflow-y-auto overscroll-contain px-5 pb-[max(2rem,env(safe-area-inset-bottom))]" onSubmit={(event) => { event.preventDefault(); save() }}>
    <DrawerHeader className="flex-row items-center justify-between p-0 pt-2 text-left"><DrawerTitle className="text-center text-[17px] font-semibold">{editing ? "Editar meta" : "Nueva meta de ahorro"}</DrawerTitle><DrawerClose render={<button type="button" aria-label="Cerrar formulario de meta" className="pressable flex size-9 items-center justify-center rounded-full bg-secondary"><X size={18} /></button>} /></DrawerHeader>
    <div className="flex items-center justify-center gap-3"><CategoryIcon icon={icon} color={color} size={24} className="size-12" /><span className="text-[17px] font-semibold">{name.trim() || "Sin nombre"}</span></div>
    <Field label="Nombre"><input autoFocus={!editing} value={name} onChange={(event) => setName(event.target.value)} placeholder="Ej. Vacaciones" className="w-full rounded-xl bg-secondary px-4 py-2.5 text-[15px] outline-none" /></Field>
    <div className={`grid gap-3 ${editing ? "grid-cols-1" : "grid-cols-2"}`}><Field label="Meta"><input inputMode="decimal" value={targetAmount} onChange={(event) => setTargetAmount(cleanAmount(event.target.value))} placeholder="0.00" className="tnum w-full rounded-xl bg-secondary px-4 py-2.5 text-[15px] outline-none" /></Field>{!editing && <Field label="Monto inicial"><input inputMode="decimal" value={currentAmount} onChange={(event) => setCurrentAmount(cleanAmount(event.target.value))} placeholder="0.00" className="tnum w-full rounded-xl bg-secondary px-4 py-2.5 text-[15px] outline-none" /></Field>}</div>
    <Field label="Fecha objetivo (opcional)"><DatePicker value={targetDate} onChange={setTargetDate} label="Fecha objetivo" /></Field>
    {goal?.planStatus === "active" && goal.requiredMonthlyContribution !== null && <p className="rounded-xl bg-primary-soft px-3 py-2 text-[12px] text-primary">Para llegar a tiempo, aparta {formatMoney(goal.requiredMonthlyContribution)} al mes.</p>}
    {goal?.planStatus === "overdue" && <p className="rounded-xl bg-expense/10 px-3 py-2 text-[12px] text-expense">La fecha objetivo ya pasó. Actualiza el plan para calcular una nueva cuota.</p>}
    {targetDate && <label className="flex cursor-pointer items-center justify-between gap-4 rounded-xl bg-secondary px-4 py-3 text-[13px]"><span><span className="block font-medium">Pausar plan de ahorro</span><span className="mt-0.5 block text-[11px] text-muted-foreground">Conserva la meta, pero deja de pedir una cuota mensual.</span></span><input type="checkbox" checked={planPaused} onChange={(event) => setPlanPaused(event.target.checked)} className="size-4 accent-primary" /></label>}
    <Field label="Cuenta compartida (opcional)"><Select value={accountId || "none"} onValueChange={(value) => setAccountId(value && value !== "none" ? value : "")}><SelectTrigger className="h-11 w-full rounded-xl border-0 bg-secondary px-4 text-[15px]"><SelectValue /></SelectTrigger><SelectContent className="rounded-xl p-1"><SelectItem value="none">Sin cuenta vinculada</SelectItem>{accounts.map((account) => <SelectItem key={account.id} value={account.id}>{account.name}</SelectItem>)}</SelectContent></Select></Field>
    <Picker label="Icono">{ICONS.map((value) => <button key={value} type="button" aria-label={`Icono ${value}`} aria-pressed={icon === value} onClick={() => setIcon(value)} className="pressable rounded-2xl p-1"><CategoryIcon icon={value} color={color} size={20} className={`size-10 ${icon === value ? "ring-2 ring-offset-2 ring-offset-background" : ""}`} style={{ ["--tw-ring-color" as string]: color }} /></button>)}</Picker>
    <Picker label="Color">{COLORS.map((value) => <button key={value} type="button" aria-label={`Color ${value}`} aria-pressed={color === value} onClick={() => setColor(value)} className={`pressable size-8 rounded-full ${color === value ? "ring-2 ring-offset-2 ring-offset-background" : ""}`} style={{ backgroundColor: value, ["--tw-ring-color" as string]: value }} />)}</Picker>
    {error && <p className="rounded-xl bg-expense/10 px-3 py-2 text-[13px] text-expense">{error}</p>}
    <Button size="lg" type="submit" disabled={!canSave} className="pressable h-12 rounded-2xl text-[16px] font-semibold">Guardar</Button>
    {editing && <button type="button" onClick={remove} disabled={deleteGoal.isPending} className={`pressable flex h-12 items-center justify-center gap-2 rounded-2xl text-[15px] font-semibold ${confirmingDelete ? "bg-expense text-white" : "bg-expense/10 text-expense"}`}><Trash2 size={16} />{confirmingDelete ? "¿Seguro? Toca para confirmar" : "Eliminar meta"}</button>}
  </form>
}

export function SavingsGoalContributionSheet({ open, onOpenChange, goal }: { open: boolean; onOpenChange: (open: boolean) => void; goal?: SavingsGoal }) {
  const contribute = useContributeToGoal()
  const [amount, setAmount] = useState("")
  const [error, setError] = useState<string | null>(null)
  const parsed = parseAmount(amount)
  const canSubmit = Boolean(goal) && parsed !== 0 && Number.isFinite(parsed) && !contribute.isPending
  function submit() { if (!goal || !canSubmit) return; setError(null); contribute.mutate({ id: goal.id, amount: parsed }, { onSuccess: () => onOpenChange(false), onError: (err) => setError(errorMessage(err)) }) }
  return <Drawer open={open} onOpenChange={onOpenChange} showSwipeHandle><DrawerContent className="mx-auto max-w-lg">{open && <form className="flex flex-col gap-5 px-5 pb-8" onSubmit={(event) => { event.preventDefault(); submit() }}><DrawerHeader className="p-0 pt-2"><DrawerTitle className="text-center text-[17px] font-semibold">Aportar a {goal?.name}</DrawerTitle></DrawerHeader><p className="text-[13px] text-muted-foreground">Usa un monto negativo para retirar de la meta. Esto no crea un movimiento.</p><Field label="Monto"><input autoFocus inputMode="decimal" value={amount} onChange={(event) => setAmount(cleanAmount(event.target.value))} placeholder="0.00" className="tnum w-full rounded-xl bg-secondary px-4 py-2.5 text-[15px] outline-none" /></Field>{error && <p className="rounded-xl bg-expense/10 px-3 py-2 text-[13px] text-expense">{error}</p>}<Button size="lg" type="submit" disabled={!canSubmit} className="pressable h-12 rounded-2xl text-[16px] font-semibold">Registrar aporte</Button></form>}</DrawerContent></Drawer>
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="block"><span className="mb-2 block text-[13px] font-medium text-muted-foreground">{label}</span>{children}</label> }
function Picker({ label, children }: { label: string; children: React.ReactNode }) { return <div><p className="mb-2 text-[13px] font-medium text-muted-foreground">{label}</p><div className="flex flex-wrap gap-3">{children}</div></div> }
