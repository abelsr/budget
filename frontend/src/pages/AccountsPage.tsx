import { useState } from "react"
import { CreditCard, Landmark, PiggyBank, Plus, Wallet } from "lucide-react"

import { AccountFormSheet } from "@/components/AccountFormSheet"
import { AccountCard } from "@/components/AccountCard"
import { Card, EmptyState, IconButton, PageHeader } from "@/components/ui/surface"
import { formatMoney } from "@/lib/format"
import { useAccounts } from "@/lib/queries"
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
  const total = accounts.reduce((sum, a) => sum + a.balance, 0)

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
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {accounts.map((a) => {
            // Con tarjeta definida → widget tipo wallet; sin ella, la tarjeta
            // clásica con icono por tipo.
            if (a.lastFour) {
              return (
                <AccountCard
                  key={a.id}
                  account={a}
                  onClick={() => openEdit(a)}
                />
              )
            }
            const meta = kindMeta[a.kind]
            const Icon = meta.icon
            return (
              <button
                key={a.id}
                onClick={() => openEdit(a)}
                className="pressable flex flex-col gap-5 rounded-3xl border border-border bg-card p-5 text-left shadow-sm"
              >
                <div className="flex items-start gap-3">
                  <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-secondary text-secondary-foreground">
                    <Icon size={20} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-[15px] font-medium">{a.name}</p>
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
          })}
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
