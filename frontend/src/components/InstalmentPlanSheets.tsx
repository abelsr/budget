import { useMemo, useState } from "react"
import { CalendarClock, CreditCard, Pause, Play, Trash2, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ApiError } from "@/lib/api"
import { formatMoney } from "@/lib/format"
import {
  useAccounts,
  useCancelInstalmentPlan,
  useCreateInstalmentPlan,
  useInstalmentPlan,
  usePayInstalmentPlan,
  usePauseInstalmentPlan,
  useResumeInstalmentPlan,
} from "@/lib/queries"
import type { Account, Transaction } from "@/lib/types"

function formatDueDate(iso: string) {
  return new Date(`${iso}T12:00:00`).toLocaleDateString("es-MX", {
    day: "numeric",
    month: "short",
  })
}

/** Default first due date: the card's next payment date, or purchase + 1 month. */
function defaultFirstDueDate(account: Account | undefined, transaction: Transaction) {
  if (account?.nextPaymentDueDate) return account.nextPaymentDueDate
  const base = new Date(`${transaction.date}T12:00:00`)
  base.setMonth(base.getMonth() + 1)
  return base.toISOString().slice(0, 10)
}

export function InstalmentPlanCreateSheet({
  open,
  onOpenChange,
  transaction,
  account,
  concealed,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  transaction: Transaction
  account?: Account
  concealed?: boolean
}) {
  return (
    <Drawer open={open} onOpenChange={onOpenChange} showSwipeHandle>
      <DrawerContent className="mx-auto max-w-lg">
        {open && (
          <CreateForm
            key={`${transaction.id}-${account?.id ?? "none"}`}
            transaction={transaction}
            account={account}
            concealed={concealed}
            onDone={() => onOpenChange(false)}
          />
        )}
      </DrawerContent>
    </Drawer>
  )
}

function CreateForm({
  transaction,
  account,
  concealed,
  onDone,
}: {
  transaction: Transaction
  account?: Account
  concealed?: boolean
  onDone: () => void
}) {
  const createPlan = useCreateInstalmentPlan()
  const [monthsText, setMonthsText] = useState("6")
  const [firstDueDate, setFirstDueDate] = useState(
    defaultFirstDueDate(account, transaction),
  )
  const months = Number(monthsText)
  const total = transaction.amount
  const monthly = Number.isFinite(months) && months >= 2 ? total / months : null
  const canSave =
    Number.isInteger(months) && months >= 2 && months <= 48 && firstDueDate !== "" && !createPlan.isPending

  function save() {
    if (!canSave) return
    createPlan.mutate(
      { sourceTransactionId: transaction.id, months, firstDueDate },
      { onSuccess: onDone },
    )
  }

  const error = createPlan.error
  const errorMessageText =
    error instanceof ApiError ? error.message : error ? "Ocurrió un error inesperado" : null

  return (
    <form
      className="flex max-h-[calc(100dvh-2rem)] flex-col overflow-hidden"
      onSubmit={(event) => {
        event.preventDefault()
        save()
      }}
    >
      <DrawerHeader className="flex-row items-center justify-between px-5 pt-2 pb-3 text-left">
        <DrawerTitle className="text-center text-[17px] font-semibold">Plan MSI</DrawerTitle>
        <DrawerClose
          render={
            <button
              type="button"
              aria-label="Cerrar plan MSI"
              className="pressable flex size-9 items-center justify-center rounded-full bg-secondary text-secondary-foreground"
            >
              <X size={18} aria-hidden="true" />
            </button>
          }
        />
      </DrawerHeader>
      <div className="min-h-0 flex-1 space-y-5 overflow-y-auto overscroll-contain px-5 py-2">
        <div className="flex items-center gap-3 rounded-xl bg-secondary px-4 py-3">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-primary/12 text-primary">
            <CreditCard size={17} />
          </span>
          <div className="min-w-0">
            <p className="text-[14px] font-medium">
              {concealed ? "••••••" : formatMoney(total)} en {account?.name ?? "tarjeta"}
            </p>
            <p className="text-[12px] text-muted-foreground">
              {new Date(`${transaction.date}T12:00:00`).toLocaleDateString("es-MX", {
                day: "numeric",
                month: "long",
              })}
            </p>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label htmlFor="msi-months" className="mb-2 block text-[13px] font-medium text-muted-foreground">
              Meses sin intereses (2–48)
            </label>
            <input
              id="msi-months"
              autoFocus
              inputMode="numeric"
              maxLength={2}
              value={monthsText}
              onChange={(event) => setMonthsText(event.target.value.replace(/\D/g, ""))}
              className="tnum w-full rounded-xl bg-secondary px-4 py-2.5 text-[15px] outline-none"
            />
          </div>
          <div>
            <label htmlFor="msi-first-due" className="mb-2 block text-[13px] font-medium text-muted-foreground">
              Primer pago
            </label>
            <input
              id="msi-first-due"
              type="date"
              value={firstDueDate}
              min={new Date().toISOString().slice(0, 10)}
              onChange={(event) => setFirstDueDate(event.target.value)}
              className="tnum w-full rounded-xl bg-secondary px-4 py-2.5 text-[15px] outline-none"
            />
          </div>
        </div>
        {monthly !== null && (
          <p className="rounded-xl bg-primary-soft px-3 py-2 text-[12px] text-primary">
            {concealed ? "••••••" : formatMoney(Math.round(monthly * 100) / 100)} por mes · la
            última cuota ajusta el redondeo.
          </p>
        )}
        {errorMessageText && (
          <p className="rounded-xl bg-expense/10 px-3 py-2 text-[13px] text-expense">{errorMessageText}</p>
        )}
      </div>
      <div className="shrink-0 border-t border-border bg-popover px-5 pt-3 pb-[max(1rem,env(safe-area-inset-bottom))]">
        <Button
          size="lg"
          type="submit"
          disabled={!canSave}
          className="pressable h-12 w-full rounded-2xl text-[16px] font-semibold"
        >
          Crear plan
        </Button>
      </div>
    </form>
  )
}

export function InstalmentPlanSheet({
  open,
  onOpenChange,
  planId,
  concealed,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  planId: string | null
  concealed?: boolean
}) {
  return (
    <Drawer open={open} onOpenChange={onOpenChange} showSwipeHandle>
      <DrawerContent className="mx-auto max-w-lg">
        {open && planId !== null && (
          <PlanView key={planId} planId={planId} concealed={concealed} onDone={() => onOpenChange(false)} />
        )}
      </DrawerContent>
    </Drawer>
  )
}

function PlanView({
  planId,
  concealed,
  onDone,
}: {
  planId: string
  concealed?: boolean
  onDone: () => void
}) {
  const { data: plan } = useInstalmentPlan(planId)
  const { data: accounts = [] } = useAccounts()
  const pay = usePayInstalmentPlan()
  const pause = usePauseInstalmentPlan()
  const resume = useResumeInstalmentPlan()
  const cancel = useCancelInstalmentPlan()
  const [sourceAccountId, setSourceAccountId] = useState("")
  const [confirmingCancel, setConfirmingCancel] = useState(false)

  const money = (value: number) => (concealed ? "••••••" : formatMoney(value))
  const error = pay.error ?? pause.error ?? resume.error ?? cancel.error
  const errorText = error instanceof ApiError ? error.message : error ? "Ocurrió un error inesperado" : null
  const isPending = pay.isPending || pause.isPending || resume.isPending || cancel.isPending
  const paymentSources = useMemo(
    () => accounts.filter((account) => !account.isPersonal && account.id !== plan?.accountId),
    [accounts, plan?.accountId],
  )

  if (!plan) return null

  const progress = Math.round((plan.paidCount / plan.months) * 100)
  const active = plan.status === "active"
  const paused = plan.status === "paused"

  function recordPayment() {
    if (!plan) return
    pay.mutate(
      { id: plan.id, sourceAccountId: sourceAccountId || undefined },
      { onSuccess: () => setSourceAccountId("") },
    )
  }

  return (
    <div className="flex max-h-[calc(100dvh-2rem)] flex-col overflow-hidden">
      <DrawerHeader className="flex-row items-center justify-between px-5 pt-2 pb-3 text-left">
        <DrawerTitle className="text-center text-[17px] font-semibold">
          Plan MSI · {plan.accountName}
        </DrawerTitle>
        <DrawerClose
          render={
            <button
              type="button"
              aria-label="Cerrar plan MSI"
              className="pressable flex size-9 items-center justify-center rounded-full bg-secondary text-secondary-foreground"
            >
              <X size={18} aria-hidden="true" />
            </button>
          }
        />
      </DrawerHeader>
      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto overscroll-contain px-5 py-2">
        <div className="flex items-center justify-between">
          <p className="tnum text-[15px] font-semibold">
            {money(plan.monthlyAmount)} × {plan.months}
          </p>
          <span
            className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${
              active
                ? "bg-primary/12 text-primary"
                : paused
                  ? "bg-amber-500/12 text-amber-700 dark:text-amber-300"
                  : "bg-secondary text-muted-foreground"
            }`}
          >
            {active ? "Activo" : paused ? "Pausado" : plan.status === "completed" ? "Completado" : "Cancelado"}
          </span>
        </div>
        <div>
          <div className="mb-1 flex items-center justify-between text-[12px] text-muted-foreground">
            <span>
              {plan.paidCount} de {plan.months} pagos
            </span>
            <span className="tnum">{progress}%</span>
          </div>
          <div
            className="h-2 overflow-hidden rounded-full bg-secondary"
            role="progressbar"
            aria-valuenow={progress}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Progreso del plan MSI"
          >
            <div className="h-full rounded-full bg-income transition-[width] duration-300" style={{ width: `${progress}%` }} />
          </div>
        </div>
        <ul className="space-y-1.5">
          {plan.schedule.map((item, index) => (
            <li
              key={item.date + String(index)}
              className={`flex items-center justify-between rounded-xl px-3 py-2 text-[13px] ${
                index === plan.paidCount && (active || paused) ? "bg-primary/8 ring-1 ring-primary/30" : ""
              } ${item.paid ? "opacity-55" : ""}`}
            >
              <span className="flex items-center gap-2 text-muted-foreground">
                <CalendarClock size={14} aria-hidden="true" />
                {formatDueDate(item.date)}
                {index === plan.paidCount && (active || paused) && (
                  <span className="text-[11px] font-semibold text-primary">próximo</span>
                )}
              </span>
              <span className={`tnum font-medium ${item.paid ? "line-through" : ""}`}>{money(item.amount)}</span>
            </li>
          ))}
        </ul>
        {errorText && (
          <p className="rounded-xl bg-expense/10 px-3 py-2 text-[13px] text-expense">{errorText}</p>
        )}
      </div>
      {(active || paused) && (
        <div className="shrink-0 space-y-2 border-t border-border bg-popover px-5 pt-3 pb-[max(1rem,env(safe-area-inset-bottom))]">
          {active && (
            <>
              <div className="flex gap-2">
                <Select
                  value={sourceAccountId === "" ? "none" : sourceAccountId}
                  onValueChange={(value) => setSourceAccountId(value && value !== "none" ? value : "")}
                >
                  <SelectTrigger aria-label="Cuenta para registrar el pago" className="h-11 flex-1 rounded-xl border-0 bg-secondary text-[14px]">
                    <SelectValue placeholder="Cuenta de pago (opcional)" />
                  </SelectTrigger>
                  <SelectContent className="rounded-xl p-1">
                    <SelectItem value="none">Solo marcar pagado</SelectItem>
                    {paymentSources.map((account: Account) => (
                      <SelectItem key={account.id} value={account.id}>
                        {account.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button
                  size="lg"
                  type="button"
                  onClick={recordPayment}
                  disabled={isPending}
                  className="pressable h-11 flex-1 rounded-xl text-[14px] font-semibold"
                >
                  Registrar pago
                </Button>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  type="button"
                  onClick={() => pause.mutate(plan.id)}
                  disabled={isPending}
                  className="pressable h-11 flex-1 rounded-xl text-[14px]"
                >
                  <Pause size={15} aria-hidden="true" /> Pausar
                </Button>
                <button
                  type="button"
                  onClick={() => {
                    if (!confirmingCancel) return setConfirmingCancel(true)
                    cancel.mutate(plan.id, {
                      onSuccess: onDone,
                      onError: () => setConfirmingCancel(false),
                    })
                  }}
                  disabled={isPending}
                  className={`pressable h-11 flex-1 rounded-xl text-[14px] font-semibold text-expense transition-colors ${
                    confirmingCancel ? "bg-expense/10" : "bg-secondary"
                  }`}
                >
                  <Trash2 size={15} aria-hidden="true" /> {confirmingCancel ? "¿Seguro?" : "Cancelar plan"}
                </button>
              </div>
            </>
          )}
          {paused && (
            <Button
              size="lg"
              type="button"
              onClick={() => resume.mutate(plan.id)}
              disabled={isPending}
              className="pressable h-12 w-full rounded-2xl text-[16px] font-semibold"
            >
              <Play size={16} aria-hidden="true" /> Reanudar plan
            </Button>
          )}
        </div>
      )}
    </div>
  )
}
