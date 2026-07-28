import { useState } from "react"
import { CreditCard, Landmark, PiggyBank, Plus, Wallet } from "lucide-react"

import { AccountFormSheet } from "@/components/AccountFormSheet"
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
    <div className="flex max-w-3xl flex-col gap-4">
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
        <Card>
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
        <Card>
          <ul className="divide-y divide-border py-2">
            {accounts.map((a) => {
              const meta = kindMeta[a.kind]
              const Icon = meta.icon
              return (
                <li
                  key={a.id}
                  onClick={() => openEdit(a)}
                  className="pressable flex cursor-pointer items-center gap-3 px-4 py-3"
                >
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
                  <span
                    className={`tnum shrink-0 text-[15px] font-semibold ${
                      a.balance < 0 ? "text-expense" : ""
                    }`}
                  >
                    {formatMoney(a.balance)}
                  </span>
                </li>
              )
            })}
          </ul>
        </Card>
      )}

      <AccountFormSheet
        open={sheetOpen}
        onOpenChange={setSheetOpen}
        account={editingAccount}
      />
    </div>
  )
}
