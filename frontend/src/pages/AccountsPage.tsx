import { useState } from "react"
import { CalendarClock, CreditCard, Landmark, PiggyBank, Plus, Wallet } from "lucide-react"

import { InstalmentPlanSheet } from "@/components/InstalmentPlanSheets"
import { AccountFormSheet } from "@/components/AccountFormSheet"
import { AccountCard } from "@/components/AccountCard"
import { Card, EmptyState, IconButton, PageHeader } from "@/components/ui/surface"
import { formatMoney } from "@/lib/format"
import { useAccounts, useInstalmentPlans } from "@/lib/queries"
import type { Account, AccountKind } from "@/lib/types"
const kindMeta: Record<AccountKind, { label: string; icon: typeof Wallet }> = {
  cash: { label: "Efectivo", icon: Wallet },
  debit: { label: "Débito", icon: Landmark },
  credit: { label: "Crédito", icon: CreditCard },
  savings: { label: "Ahorro", icon: PiggyBank },
}

/** Cuentas del hogar con sus saldos. */
export function AccountsPage() {
  const { data: accounts = [] } = useAccounts()
  const sharedAccounts = accounts.filter((account) => !account.isPersonal)
  const personalAccounts = accounts.filter((account) => account.isPersonal)
  const total = sharedAccounts.reduce((sum, a) => sum + a.balance, 0)

  const [sheetOpen, setSheetOpen] = useState(false)
  const [editingAccount, setEditingAccount] = useState<Account | undefined>()

  function openCreate() {
    setEditingAccount(undefined)
    setSheetOpen(true)
  }

  function openEdit(account: Account) {
    setEditingAccount(account)
    setSheetOpen(true)
  }

  return (
    <div className="flex max-w-3xl flex-col gap-4 lg:max-w-4xl">
      <PageHeader
        title="Cuentas"
        eyebrow={<>Total · <span className="tnum">{formatMoney(total)}</span></>}
        action={
          <IconButton label="Crear cuenta" variant="primary" onClick={openCreate}>
            <Plus size={20} strokeWidth={2.5} />
          </IconButton>
        }
      />

      {accounts.length === 0 ? (
        <Card className="flex min-h-[calc(100dvh-12rem)] flex-col items-center justify-center md:min-h-[calc(100dvh-14rem)]">
          <EmptyState
            icon={<Wallet size={26} />}
            title="Sin cuentas"
            hint="Una cuenta es dónde vive tu dinero: efectivo, débito, crédito o ahorro. Crea la primera para empezar a registrar."
            action={
              <button
                onClick={openCreate}
                className="pressable rounded-full bg-primary px-5 py-2.5 text-[14px] font-semibold text-primary-foreground"
              >
                Crear cuenta
              </button>
            }
          />
        </Card>
      ) : (
        <div className="space-y-6">
          <AccountSection title="Del hogar" accounts={sharedAccounts} onEdit={openEdit} />
          <AccountSection title="Personales" accounts={personalAccounts} onEdit={openEdit} empty="Crea una cuenta personal para llevarla en privado." />
        </div>
      )}

      <AccountFormSheet
        open={sheetOpen}
        onOpenChange={setSheetOpen}
        account={editingAccount}
      />
    </div>
  )
}

function AccountSection({ title, accounts, onEdit, empty }: { title: string; accounts: Account[]; onEdit: (account: Account) => void; empty?: string }) {
  const { data: plans = [] } = useInstalmentPlans()
  const [planSheetPlanId, setPlanSheetPlanId] = useState<string | null>(null)
  return <section><h2 className="mb-2 text-[13px] font-semibold text-muted-foreground">{title}</h2>{accounts.length === 0 ? <p className="rounded-2xl border border-dashed border-border px-4 py-5 text-[13px] text-muted-foreground">{empty ?? "Aún no hay cuentas compartidas."}</p> : <div className="grid grid-cols-1 gap-4 md:grid-cols-2">{accounts.map((a) => {
            const accountPlans = plans.filter((plan) => plan.accountId === a.id)
            // Con tarjeta definida → widget tipo wallet; sin ella, la tarjeta
            // clásica con icono por tipo.
            const widget = a.lastFour ? (
              <AccountCard key={a.id} account={a} onClick={() => onEdit(a)} />
            ) : (
              (() => {
                const meta = kindMeta[a.kind]
                const Icon = meta.icon
                return (
                  <button
                    key={a.id}
                    onClick={() => onEdit(a)}
                    className="pressable flex flex-col gap-5 rounded-3xl border border-border bg-card p-5 text-left shadow-sm"
                  >
                    <div className="flex items-start gap-3">
                      <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-secondary text-secondary-foreground">
                        <Icon size={20} />
                      </span>
                       <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2"><p className="truncate text-[15px] font-medium">{a.name}</p>{a.isPersonal && <span className="rounded bg-secondary px-1.5 py-0.5 text-[10px] font-semibold text-muted-foreground">Personal</span>}</div>
                        {/* El tipo sólo aporta si no es literalmente el nombre */}
                        {a.name !== meta.label && (
                          <p className="text-[13px] text-muted-foreground">
                            {meta.label}
                          </p>
                        )}
                      </div>
                    </div>
                    <span
                      className={`tnum text-[20px] leading-none font-bold tracking-tight ${
                        a.balance < 0 ? "text-expense" : ""
                      }`}
                    >
                      {formatMoney(a.balance)}
                    </span>
                  </button>
                )
              })()
            )
            return (
              <div key={a.id} className="flex flex-col gap-1.5">
                {widget}
                {a.kind === "credit" && a.statementDay != null && a.nextPaymentDueDate != null && (
                  <p className="flex items-center gap-1.5 px-1 text-[11px] font-medium text-muted-foreground">
                    <CalendarClock size={12} aria-hidden="true" />
                    Corte {a.statementDay} · Pago {new Date(`${a.nextPaymentDueDate}T12:00:00`).toLocaleDateString("es-MX", { day: "numeric", month: "short" })}
                  </p>
                )}
                {accountPlans.map((plan) => (
                  <button
                    key={plan.id}
                    type="button"
                    onClick={() => setPlanSheetPlanId(plan.id)}
                    aria-label={`Ver plan MSI de ${a.name}`}
                    className="pressable flex items-center justify-between rounded-xl bg-primary/8 px-3 py-2 text-[12px] font-medium text-primary"
                  >
                    <span className="flex items-center gap-1.5">
                      <CreditCard size={13} aria-hidden="true" />
                      MSI {plan.months} meses{plan.status === "paused" ? " · pausado" : ""}
                    </span>
                    <span className="tnum">{plan.paidCount}/{plan.months}</span>
                  </button>
                ))}
              </div>
            )
          })}</div>}
      <InstalmentPlanSheet
        open={planSheetPlanId !== null}
        onOpenChange={(open) => {
          if (!open) setPlanSheetPlanId(null)
        }}
        planId={planSheetPlanId}
      />
    </section>
}
