import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Repeat, Trash2 } from "lucide-react"
import { motion } from "motion/react"

import { CategoryIcon } from "@/components/CategoryIcon"
import { CHART_OTHER } from "@/lib/chart-colors"
import { formatMoney, formatShortDate } from "@/lib/format"
import {
  useAccounts,
  useCategories,
  useDeleteRecurringRule,
  useRecurringRules,
  useUpdateRecurringRule,
} from "@/lib/queries"
import { springAppear } from "@/lib/springs"
import { EmptyState as Empty, PageHeader, Toggle } from "@/components/ui/surface"
import type { Account, Category, RecurringRule } from "@/lib/types"

const frequencyLabel: Record<RecurringRule["frequency"], string> = {
  weekly: "Cada semana",
  monthly: "Cada mes",
}

/**
 * Movimientos recurrentes del hogar: pausar, reanudar y eliminar.
 * Las reglas se crean desde el sheet de registro ("Repetir"), no aquí: nadie
 * piensa "voy a crear una regla", piensa "esta renta se repite cada mes".
 */
export function RecurringPage() {
  const navigate = useNavigate()
  const { data: rules = [], isLoading } = useRecurringRules()
  const { data: categories = [] } = useCategories()
  const { data: accounts = [] } = useAccounts()
  const updateRule = useUpdateRecurringRule()

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springAppear}
      className="flex max-w-2xl flex-col gap-5"
    >
      <PageHeader title="Recurrentes" back={() => navigate(-1)} />

      <div className="overflow-hidden rounded-3xl border border-border bg-card shadow-sm">
        {isLoading ? (
          <p className="px-4 py-3.5 text-[13px] text-muted-foreground">
            Cargando…
          </p>
        ) : rules.length === 0 ? (
          <EmptyState />
        ) : (
          rules.map((rule, i) => (
            <RuleRow
              key={rule.id}
              rule={rule}
              category={categories.find((c) => c.id === rule.categoryId)}
              account={accounts.find((a) => a.id === rule.accountId)}
              first={i === 0}
              onToggle={() =>
                updateRule.mutate({ id: rule.id, active: !rule.active })
              }
            />
          ))
        )}
      </div>

      {rules.length > 0 && (
        <p className="px-4 text-[12px] leading-relaxed text-muted-foreground">
          Las transacciones se generan al abrir la app, no en segundo plano: si
          la dejas cerrada unos días, al volver aparecen todas con su fecha
          correcta. Pausar detiene las siguientes; reanudar continúa desde el
          próximo periodo, sin cobrar el tiempo apagado.
        </p>
      )}
    </motion.div>
  )
}

function EmptyState() {
  return (
    <Empty
      icon={<Repeat size={24} />}
      title="Sin movimientos recurrentes"
      hint={'Al registrar un movimiento, elige "Repetir" para que la renta, el sueldo o una suscripción se generen solos.'}
    />
  )
}

function RuleRow({
  rule,
  category,
  account,
  first,
  onToggle,
}: {
  rule: RecurringRule
  category?: Category
  account?: Account
  first: boolean
  onToggle: () => void
}) {
  const deleteRule = useDeleteRecurringRule()
  const [confirming, setConfirming] = useState(false)
  const isIncome = rule.type === "income"

  return (
    <div
      className={`px-4 py-3 ${first ? "" : "border-t border-border"} ${
        rule.active ? "" : "opacity-50"
      }`}
    >
      <div className="flex items-center gap-3">
        <CategoryIcon
          icon={category?.icon ?? "wallet"}
          color={category?.color ?? CHART_OTHER.light}
          size={20}
          className="size-10 shrink-0"
        />
        <div className="min-w-0 flex-1">
          <p className="truncate text-[15px] font-medium">
            {rule.note || category?.name || "Movimiento"}
          </p>
          <p className="truncate text-[13px] text-muted-foreground">
            {[
              frequencyLabel[rule.frequency],
              account?.name,
              rule.active
                ? `próximo ${formatShortDate(rule.nextRunDate)}`
                : "en pausa",
            ]
              .filter(Boolean)
              .join(" · ")}
          </p>
        </div>
        <span
          className={`tnum shrink-0 text-[15px] font-semibold ${
            isIncome ? "text-income" : ""
          }`}
        >
          {isIncome ? "+" : "−"}
          {formatMoney(rule.amount)}
        </span>
      </div>

      <div className="mt-2 flex items-center gap-2 pl-13">
        <Toggle
          checked={rule.active}
          onChange={onToggle}
          label={`${rule.active ? "Pausar" : "Reanudar"} ${
            rule.note || category?.name || "movimiento"
          }`}
        />
        <span className="flex-1 text-[12px] text-muted-foreground">
          {rule.active ? "Activa" : "Pausada"}
        </span>
        {confirming ? (
          <>
            <button
              onClick={() => setConfirming(false)}
              className="pressable rounded-full bg-secondary px-3 py-1 text-[12px] font-semibold"
            >
              Cancelar
            </button>
            <button
              onClick={() => deleteRule.mutate(rule.id)}
              disabled={deleteRule.isPending}
              className="pressable rounded-full bg-expense px-3 py-1 text-[12px] font-semibold text-white disabled:opacity-50"
            >
              Eliminar
            </button>
          </>
        ) : (
          <button
            onClick={() => setConfirming(true)}
            aria-label="Eliminar regla"
            className="pressable rounded-full p-1.5 text-expense"
          >
            <Trash2 size={16} />
          </button>
        )}
      </div>
      {confirming && (
        <p className="mt-1.5 pl-13 text-[12px] text-muted-foreground">
          Los movimientos ya generados se conservan.
        </p>
      )}
    </div>
  )
}
