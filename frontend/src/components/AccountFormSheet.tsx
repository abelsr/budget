import { useState } from "react"
import { CreditCard, Landmark, PiggyBank, Wallet, X } from "lucide-react"

import { AccountCard } from "@/components/AccountCard"
import { Button } from "@/components/ui/button"
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer"
import { ApiError } from "@/lib/api"
import { BANK_SUGGESTIONS } from "@/lib/brands"
import { parseAmount } from "@/lib/format"
import {
  useCreateAccount,
  useDeleteAccount,
  useUpdateAccount,
} from "@/lib/queries"
import type { Account, AccountKind, CardBrand } from "@/lib/types"

const kindOptions: { kind: AccountKind; label: string; icon: typeof Wallet }[] = [
  { kind: "cash", label: "Efectivo", icon: Wallet },
  { kind: "debit", label: "Débito", icon: Landmark },
  { kind: "credit", label: "Crédito", icon: CreditCard },
  { kind: "savings", label: "Ahorro", icon: PiggyBank },
]

const brandOptions: { value: CardBrand; label: string }[] = [
  { value: "visa", label: "Visa" },
  { value: "mastercard", label: "Mastercard" },
  { value: "amex", label: "Amex" },
  { value: "other", label: "Otra" },
]

interface AccountFormSheetProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Si viene, el sheet edita esa cuenta; si no, crea una nueva. */
  account?: Account
}

/** Bottom sheet para crear o editar una cuenta del hogar. */
export function AccountFormSheet({
  open,
  onOpenChange,
  account,
}: AccountFormSheetProps) {
  return (
    <Drawer open={open} onOpenChange={onOpenChange} showSwipeHandle>
      <DrawerContent className="mx-auto max-w-lg">
        {open && (
          <AccountForm account={account} onDone={() => onOpenChange(false)} />
        )}
      </DrawerContent>
    </Drawer>
  )
}

function AccountForm({
  account,
  onDone,
}: {
  account?: Account
  onDone: () => void
}) {
  const createAccount = useCreateAccount()
  const updateAccount = useUpdateAccount()
  const deleteAccount = useDeleteAccount()

  const [name, setName] = useState(account?.name ?? "")
  const [kind, setKind] = useState<AccountKind>(account?.kind ?? "cash")
  const [balanceText, setBalanceText] = useState(
    account ? String(account.openingBalance) : "0",
  )
  const [bank, setBank] = useState(account?.bank ?? "")
  const [cardBrand, setCardBrand] = useState<CardBrand | "">(
    account?.cardBrand ?? "",
  )
  const [lastFour, setLastFour] = useState(account?.lastFour ?? "")
  const [statementDayText, setStatementDayText] = useState(
    account?.statementDay != null ? String(account.statementDay) : "",
  )
  const [paymentDueDaysText, setPaymentDueDaysText] = useState(
    account?.paymentDueDays != null ? String(account.paymentDueDays) : "",
  )
  const [isPersonal, setIsPersonal] = useState(account?.isPersonal ?? false)
  /** Segundo toque de la confirmación en dos pasos del checkbox "Cuenta personal". */
  const [pendingPersonal, setPendingPersonal] = useState<boolean | null>(null)
  const [confirmingDelete, setConfirmingDelete] = useState(false)

  const openingBalance = parseAmount(balanceText)
  const lastFourValid = lastFour === "" || /^\d{4}$/.test(lastFour)
  const statementDay = statementDayText === "" ? null : Number(statementDayText)
  const paymentDueDays = paymentDueDaysText === "" ? null : Number(paymentDueDaysText)
  const cycleValid =
    (statementDay === null || (statementDay >= 1 && statementDay <= 28)) &&
    (paymentDueDays === null || (paymentDueDays >= 1 && paymentDueDays <= 60))
  const isPending =
    createAccount.isPending ||
    updateAccount.isPending ||
    deleteAccount.isPending
  const canSave =
    name.trim().length > 0 &&
    openingBalance !== null &&
    lastFourValid &&
    cycleValid &&
    !isPending

  /**
   * Cambiar la visibilidad de una cuenta existente pide confirmación inline
   * en dos pasos (mismo patrón que el borrado): el primer toque arma la
   * confirmación y el segundo (botón "¿Seguro?") aplica el cambio.
   */
  function onPersonalChange() {
    const next = !isPersonal
    if (pendingPersonal !== null) return
    if (account && next !== account.isPersonal) {
      setPendingPersonal(next)
      return
    }
    setIsPersonal(next)
  }

  function confirmPersonalChange() {
    if (pendingPersonal === null) return
    setIsPersonal(pendingPersonal)
    setPendingPersonal(null)
  }

  const error =
    createAccount.error ?? updateAccount.error ?? deleteAccount.error
  const errorMessage =
    error instanceof ApiError
      ? error.message
      : error
        ? "Ocurrió un error inesperado"
        : null

  function save() {
    if (!canSave || openingBalance === null) return
    // The cycle fields only apply to credit cards; clearing them on a kind
    // change is what the backend requires (422 otherwise).
    const withCycle = kind === "credit"
    const input = {
      name: name.trim(),
      kind,
      openingBalance,
      bank: bank.trim() || null,
      cardBrand: cardBrand || null,
      lastFour: lastFour || null,
      isPersonal,
      statementDay: withCycle ? statementDay : null,
      paymentDueDays: withCycle ? paymentDueDays : null,
    }
    if (account) {
      updateAccount.mutate({ id: account.id, ...input }, { onSuccess: onDone })
    } else {
      createAccount.mutate(input, { onSuccess: onDone })
    }
  }

  /** Eliminación en dos pasos: el primer toque pide confirmación inline. */
  function remove() {
    if (!account || isPending) return
    if (!confirmingDelete) {
      setConfirmingDelete(true)
      return
    }
    deleteAccount.mutate(account.id, {
      onSuccess: onDone,
      onError: () => setConfirmingDelete(false),
    })
  }

  return (
    <form
      className="flex max-h-[calc(100dvh-2rem)] flex-col overflow-hidden"
      onSubmit={(event) => {
        event.preventDefault()
        save()
      }}
    >
      <DrawerHeader className="flex-row items-center justify-between px-5 pt-2 pb-3 text-left">
        <DrawerTitle className="text-center text-[17px] font-semibold">
          {account ? "Editar cuenta" : "Nueva cuenta"}
        </DrawerTitle>
        <DrawerClose
          render={
            <button
              type="button"
              aria-label="Cerrar formulario de cuenta"
              className="pressable flex size-9 items-center justify-center rounded-full bg-secondary text-secondary-foreground"
            >
              <X size={18} aria-hidden="true" />
            </button>
          }
        />
      </DrawerHeader>

      <div className="min-h-0 flex-1 space-y-5 overflow-y-auto overscroll-contain px-5 py-2">
        {/* Nombre */}
        <div>
          <label htmlFor="account-name" className="mb-2 block text-[13px] font-medium text-muted-foreground">
            Nombre
          </label>
          <input
            id="account-name"
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Ej. Cuenta nómina"
            className="w-full rounded-xl bg-secondary px-4 py-2.5 text-[15px] outline-none placeholder:text-muted-foreground"
          />
        </div>

        {/* Tipo */}
        <div>
          <p id="account-kind-label" className="mb-2 text-[13px] font-medium text-muted-foreground">
            Tipo
          </p>
          <div className="grid grid-cols-2 gap-2" role="group" aria-labelledby="account-kind-label">
            {kindOptions.map(({ kind: k, label, icon: Icon }) => {
              const selected = kind === k
              return (
                <button
                  key={k}
                  type="button"
                  onClick={() => setKind(k)}
                  aria-pressed={selected}
                  className={`pressable flex items-center gap-2 rounded-xl px-4 py-2.5 text-[14px] font-medium transition-colors ${
                    selected
                      ? "bg-primary text-primary-foreground"
                      : "bg-secondary text-secondary-foreground"
                  }`}
                >
                  <Icon size={18} />
                  {label}
                </button>
              )
            })}
          </div>
        </div>

        {/* Saldo inicial */}
        <div>
          <label htmlFor="account-opening-balance" className="mb-2 block text-[13px] font-medium text-muted-foreground">
            Saldo inicial
          </label>
          <input
            id="account-opening-balance"
            inputMode="decimal"
            value={balanceText}
            onChange={(e) =>
              setBalanceText(e.target.value.replace(/[^0-9.,-]/g, ""))
            }
            className="tnum w-full rounded-xl bg-secondary px-4 py-2.5 text-[15px] outline-none"
          />
          {openingBalance === null && (
            <p className="mt-1 text-[12px] text-expense">
              Escribe un saldo válido (ej. 1,234.56).
            </p>
          )}
        </div>

        {/* Cuenta personal: al editar, cambiar la visibilidad pide confirmación
            inline en dos pasos (mismo patrón que el borrado de la cuenta). */}
        <div className="rounded-xl bg-secondary px-4 py-3">
          <label className="flex cursor-pointer items-start gap-3">
            <input
              type="checkbox"
              checked={pendingPersonal ?? isPersonal}
              disabled={pendingPersonal !== null}
              onChange={onPersonalChange}
              className="mt-0.5"
              aria-label="Cuenta personal"
            />
            <span>
              <span className="block text-[14px] font-medium">Cuenta personal</span>
              <span className="block text-[12px] text-muted-foreground">Solo tú la verás y no suma al total del hogar.</span>
            </span>
          </label>
          {pendingPersonal !== null && (
            <div className="mt-2 space-y-2">
              <p className="text-[12px] font-medium text-expense">
                {pendingPersonal
                  ? "Esta cuenta dejará de ser visible para el hogar y ya no sumará a sus balances."
                  : "Esta cuenta y sus movimientos volverán a ser visibles para todo el hogar."}
              </p>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={confirmPersonalChange}
                  className="pressable flex-1 rounded-lg bg-expense/10 px-3 py-2 text-[13px] font-semibold text-expense"
                >
                  ¿Seguro? Toca para confirmar
                </button>
                <button
                  type="button"
                  onClick={() => setPendingPersonal(null)}
                  className="pressable rounded-lg bg-card px-3 py-2 text-[13px] font-semibold text-secondary-foreground"
                >
                  Cancelar
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Datos de tarjeta (opcional) — activan el widget tipo wallet */}
        <div>
          <p id="account-card-details-label" className="mb-2 text-[13px] font-medium text-muted-foreground">
            Datos de tarjeta <span className="font-normal">(opcional)</span>
          </p>
          <div className="flex flex-col gap-2" aria-labelledby="account-card-details-label">
          <input
            id="account-bank"
            list="bank-suggestions"
            value={bank}
            onChange={(e) => setBank(e.target.value)}
            placeholder="Banco (ej. BBVA)"
            className="w-full rounded-xl bg-secondary px-4 py-2.5 text-[15px] outline-none placeholder:text-muted-foreground"
            aria-label="Banco"
          />
          <datalist id="bank-suggestions">
            {BANK_SUGGESTIONS.map((b) => (
              <option key={b} value={b} />
            ))}
          </datalist>
          <div className="flex gap-2">
            <input
              id="account-last-four"
              inputMode="numeric"
              maxLength={4}
              value={lastFour}
              onChange={(e) =>
                setLastFour(e.target.value.replace(/\D/g, "").slice(0, 4))
              }
              placeholder="Últimos 4 dígitos"
              className="tnum w-36 rounded-xl bg-secondary px-4 py-2.5 text-[15px] outline-none placeholder:text-muted-foreground"
              aria-label="Últimos 4 dígitos de la tarjeta"
            />
            <div className="flex flex-1 gap-1.5" role="group" aria-label="Marca de la tarjeta">
              {brandOptions.map(({ value, label }) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setCardBrand(value)}
                  aria-pressed={cardBrand === value}
                  className={`pressable flex-1 rounded-xl px-2 py-2.5 text-[12px] font-medium transition-colors ${
                    cardBrand === value
                      ? "bg-primary text-primary-foreground"
                      : "bg-secondary text-secondary-foreground"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          {lastFour !== "" && !lastFourValid && (
            <p className="text-[12px] text-expense">Deben ser 4 dígitos.</p>
          )}
          </div>
        </div>

        {/* Ciclo de la tarjeta (solo crédito) — deriva corte y fecha de pago */}
        {kind === "credit" && (
          <div>
            <p id="account-card-cycle-label" className="mb-2 text-[13px] font-medium text-muted-foreground">
              Ciclo de la tarjeta <span className="font-normal">(opcional)</span>
            </p>
            <div className="flex gap-2" aria-labelledby="account-card-cycle-label">
              <div className="flex-1">
                <input
                  id="account-statement-day"
                  inputMode="numeric"
                  maxLength={2}
                  value={statementDayText}
                  onChange={(e) => setStatementDayText(e.target.value.replace(/\D/g, ""))}
                  placeholder="Día de corte (1–28)"
                  className="tnum w-full rounded-xl bg-secondary px-4 py-2.5 text-[15px] outline-none placeholder:text-muted-foreground"
                  aria-label="Día de corte del ciclo de la tarjeta"
                />
              </div>
              <div className="flex-1">
                <input
                  id="account-payment-due-days"
                  inputMode="numeric"
                  maxLength={2}
                  value={paymentDueDaysText}
                  onChange={(e) => setPaymentDueDaysText(e.target.value.replace(/\D/g, ""))}
                  placeholder="Días hasta el pago (ej. 20)"
                  className="tnum w-full rounded-xl bg-secondary px-4 py-2.5 text-[15px] outline-none placeholder:text-muted-foreground"
                  aria-label="Días entre el corte y la fecha límite de pago"
                />
              </div>
            </div>
            {(statementDay !== null && (statementDay < 1 || statementDay > 28)) ||
            (paymentDueDays !== null && (paymentDueDays < 1 || paymentDueDays > 60)) ? (
              <p className="text-[12px] text-expense">Corte entre 1 y 28; pago entre 1 y 60 días.</p>
            ) : null}
          </div>
        )}

        {/* Vista previa del widget tipo wallet */}
        {lastFour !== "" && openingBalance !== null && (
          <div>
            <p className="mb-2 text-[13px] font-medium text-muted-foreground">
              Vista previa
            </p>
            <AccountCard
              account={{
                id: account?.id ?? "preview",
                householdId: account?.householdId ?? "",
                name: name.trim() || "Nombre de la cuenta",
                kind,
                openingBalance,
                balance: openingBalance,
                bank: bank.trim() || null,
                cardBrand: cardBrand || null,
                lastFour,
                isPersonal,
              }}
            />
          </div>
        )}

        {errorMessage && (
          <p className="rounded-xl bg-expense/10 px-3 py-2 text-[13px] text-expense">
            {errorMessage}
          </p>
        )}
      </div>

      <div className="shrink-0 border-t border-border bg-popover px-5 pt-3 pb-[max(1rem,env(safe-area-inset-bottom))]">
        <Button
          size="lg"
          type="submit"
          disabled={!canSave}
          className="pressable h-12 w-full rounded-2xl text-[16px] font-semibold"
        >
          Guardar
        </Button>

        {account && (
          <button
            type="button"
            onClick={remove}
            disabled={isPending}
            className={`pressable mt-2 h-12 w-full rounded-2xl text-[15px] font-semibold text-expense transition-colors ${
              confirmingDelete ? "bg-expense/10" : ""
            }`}
          >
            {confirmingDelete ? "¿Seguro? Toca para confirmar" : "Eliminar cuenta"}
          </button>
        )}
      </div>
    </form>
  )
}
