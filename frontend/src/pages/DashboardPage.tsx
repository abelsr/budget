import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { motion } from "motion/react"
import {
  Area,
  AreaChart,
  Cell,
  Pie,
  PieChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import {
  ArrowDownLeft,
  ArrowUpRight,
  CreditCard,
  Landmark,
  Plus,
  PiggyBank,
  Wallet,
} from "lucide-react"

import { formatMoney, formatMoneyCompact, monthLabel } from "@/lib/format"
import {
  useAccounts,
  useBudgets,
  useBudgetsStatus,
  useCategories,
  useMembers,
  useMonthSummary,
  useTransactions,
} from "@/lib/queries"
import {
  CHART_OTHER,
  CHART_PALETTE_DARK,
  CHART_PALETTE_LIGHT,
  cssVar,
  seriesColor,
} from "@/lib/chart-colors"
import { springAppear } from "@/lib/springs"
import { useTheme } from "@/lib/theme"
import type { Account, Budget, BudgetStatus, Category, Member, Transaction } from "@/lib/types"
import { BudgetBar } from "@/components/BudgetBar"
import { BudgetFormSheet } from "@/components/BudgetFormSheet"
import { TransactionItem } from "@/components/TransactionItem"
import { TicketScannerButton } from "@/components/TicketScanner"
import { CARD } from "@/components/ui/surface"

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.05 } },
}
const item = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: springAppear },
}

/** Máximo de segmentos en la dona; el resto se pliega en "Otros". */
const MAX_SLICES = 6

/**
 * Animación de gráficas "solo al primer montaje" (§6). Recharts re-anima cada
 * vez que cambian los datos; aquí el flag se activa únicamente cuando los datos
 * llegan por primera vez y luego queda apagado, para que una actualización en
 * caliente se refleje en su sitio sin leerse como "pasó algo nuevo".
 */
function useFirstDataAnim(hasData: boolean) {
  const [animated, setAnimated] = useState(false)
  useEffect(() => {
    if (hasData) setAnimated(true)
  }, [hasData])
  return hasData && !animated
}

/**
 * Dashboard.
 *
 * Responde cuatro preguntas, en este orden (docs/design-guidelines.md §8):
 *   1. ¿Cuánto tenemos?      → hero de saldo
 *   2. ¿Cómo va el mes?      → flujo (ingresos vs gastos) + ritmo de gasto
 *   3. ¿En qué se va?        → dona por categoría + presupuestos
 *   4. ¿Qué acaba de pasar?  → movimientos recientes
 *
 * Móvil: una columna por urgencia. Escritorio: rejilla de 12 con el análisis
 * en la columna derecha, para que la izquierda sea un solo hilo de lectura.
 */
export function DashboardPage() {
  const { data: accounts = [] } = useAccounts()
  const { data: categories = [] } = useCategories()
  const { data: members = [] } = useMembers()
  const { data: transactions = [] } = useTransactions()
  const { data: summary } = useMonthSummary()
  const { data: budgets = [] } = useBudgets()
  const { data: budgetsStatus = [] } = useBudgetsStatus()

  const income = summary?.income ?? 0
  const expense = summary?.expense ?? 0

  const slices = useSlices(summary?.byCategory, categories)
  const overBudgetCount = budgetsStatus.filter((s) => s.percentage >= 100).length
  const budgetTotal = budgets.reduce((sum, b) => sum + b.amount, 0)

  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="flex flex-col gap-4 lg:gap-6"
    >
      <motion.header variants={item} className="px-1">
        <p className="text-[13px] font-medium text-muted-foreground">
          {monthLabel()}
        </p>
        <h1 className="text-[34px] leading-tight font-bold tracking-tight">
          Resumen
        </h1>
      </motion.header>

      <div className="grid gap-4 lg:grid-cols-12 lg:gap-6">
        {/* 1 · ¿Cuánto tenemos? */}
        <div className="lg:col-span-7">
          <BalanceHero accounts={accounts} />
        </div>

        {/* 2 · ¿Cómo va el mes? */}
        <div className="lg:col-span-5">
          <FlowCard income={income} expense={expense} />
        </div>
        <div className="lg:col-span-12">
          <PaceCard transactions={transactions} budgetTotal={budgetTotal} />
        </div>

        {/* Móvil: el escáner va en el hilo principal, antes del análisis */}
        <motion.div variants={item} className="lg:hidden">
          <TicketScannerButton />
        </motion.div>

        {/* 3 · ¿En qué se va? — en escritorio, columna derecha */}
        <div className="flex flex-col gap-4 lg:order-1 lg:col-span-5 lg:gap-6">
          <DonutCard slices={slices} total={expense} overBudgetCount={overBudgetCount} />
          <BudgetsCard budgets={budgets} status={budgetsStatus} categories={categories} />
          <motion.div variants={item} className="hidden lg:block">
            <TicketScannerButton />
          </motion.div>
        </div>

        {/* 4 · ¿Qué acaba de pasar? */}
        <div className="flex flex-col gap-4 lg:col-span-7 lg:gap-6">
          <RecentCard
            transactions={transactions}
            categories={categories}
            accounts={accounts}
            members={members}
          />
          {/* En móvil las cuentas ya viven como chips dentro del hero */}
          <div className="hidden lg:block">
            <AccountsSummary accounts={accounts} />
          </div>
        </div>
      </div>
    </motion.div>
  )
}

// ── 1 · Saldo ────────────────────────────────────────────────────────────────

const kindIcon = { cash: Wallet, debit: Landmark, credit: CreditCard, savings: PiggyBank }

/**
 * Única superficie de marca de la pantalla: gradiente azul + curva decorativa
 * (que no es dato). El saldo total es la única cifra por encima de 32px.
 */
function BalanceHero({ accounts }: { accounts: Account[] }) {
  const total = accounts.reduce((sum, a) => sum + a.balance, 0)
  return (
    <motion.section
      variants={item}
      className="surface-brand relative h-full overflow-hidden rounded-3xl p-6 shadow-lg lg:p-8"
    >
      {/* Decoración: curva y halo. No codifica ningún dato. */}
      <svg
        aria-hidden="true"
        viewBox="0 0 400 100"
        preserveAspectRatio="none"
        className="pointer-events-none absolute inset-x-0 bottom-0 h-24 w-full opacity-25"
      >
        <path
          d="M0 78 Q 60 30, 120 62 T 240 38 T 400 58 L400 100 L0 100 Z"
          fill="rgba(255,255,255,0.16)"
        />
        <path
          d="M0 78 Q 60 30, 120 62 T 240 38 T 400 58"
          fill="none"
          stroke="#ffffff"
          strokeWidth="2.5"
          strokeLinecap="round"
        />
      </svg>
      <div className="pointer-events-none absolute -top-20 -right-20 size-56 rounded-full bg-white/10 blur-3xl" />

      <div className="relative">
        <p className="text-[13px] font-medium tracking-wide text-white/80">
          Saldo total
        </p>
        <p className="mt-1 text-[40px] leading-none font-bold tracking-[-0.03em] lg:text-[52px]">
          {formatMoney(total)}
        </p>
        <div className="mt-5 flex flex-wrap gap-2">
          {accounts.map((a) => {
            const Icon = kindIcon[a.kind]
            return (
              <span
                key={a.id}
                className="tnum flex shrink-0 items-center gap-1.5 rounded-full bg-white/15 px-3 py-1.5 text-[12px] font-medium text-white backdrop-blur-sm"
              >
                <Icon size={13} aria-hidden="true" />
                {a.name}
                <span className="text-white/75">{formatMoney(a.balance, true)}</span>
              </span>
            )
          })}
        </div>
      </div>
    </motion.section>
  )
}

// ── 2 · El mes ───────────────────────────────────────────────────────────────

/**
 * Ingresos y gastos son una comparación, no dos datos sueltos: comparten una
 * barra proporcional y el resultado se dice en palabras.
 */
function FlowCard({ income, expense }: { income: number; expense: number }) {
  const net = income - expense
  const max = Math.max(income, expense, 1)
  const rate = income > 0 ? Math.round((net / income) * 100) : 0

  return (
    <motion.section variants={item} className={`${CARD} h-full p-5 lg:p-6`}>
      <h2 className="text-[17px] font-semibold tracking-tight">Este mes</h2>

      <div className="mt-4 space-y-3">
        <FlowRow
          label="Ingresos"
          amount={income}
          width={(income / max) * 100}
          tone="income"
        />
        <FlowRow
          label="Gastos"
          amount={expense}
          width={(expense / max) * 100}
          tone="expense"
        />
      </div>

      <p className="mt-4 border-t border-border pt-4 text-[13px] text-muted-foreground">
        {income === 0 && expense === 0 ? (
          "Aún no hay movimientos este mes."
        ) : net >= 0 ? (
          <>
            Ahorraste{" "}
            <span className="tnum font-semibold text-income">{formatMoney(net)}</span>
            {income > 0 && ` · ${rate}% de tus ingresos`}
          </>
        ) : (
          <>
            Gastaste{" "}
            <span className="tnum font-semibold text-expense">
              {formatMoney(Math.abs(net))}
            </span>{" "}
            más de lo que entró
          </>
        )}
      </p>
    </motion.section>
  )
}

function FlowRow({
  label,
  amount,
  width,
  tone,
}: {
  label: string
  amount: number
  width: number
  tone: "income" | "expense"
}) {
  const isIncome = tone === "income"
  const Icon = isIncome ? ArrowDownLeft : ArrowUpRight
  return (
    <div>
      <div className="flex items-baseline justify-between gap-2">
        <span className="flex items-center gap-1.5 text-[13px] font-medium text-muted-foreground">
          <Icon
            size={14}
            className={isIncome ? "text-income" : "text-expense"}
            aria-hidden="true"
          />
          {label}
        </span>
        <span
          className={`tnum text-[19px] font-bold tracking-tight ${
            isIncome ? "text-income" : "text-expense"
          }`}
        >
          {isIncome ? "+" : "−"}
          {formatMoney(amount)}
        </span>
      </div>
      <div className="mt-1.5 h-2 w-full overflow-hidden rounded-full bg-secondary">
        <div
          className={`h-full rounded-full ${isIncome ? "bg-income" : "bg-expense"}`}
          style={{ width: `${Math.max(width, amount > 0 ? 3 : 0)}%` }}
        />
      </div>
    </div>
  )
}

/**
 * Ritmo de gasto: gasto acumulado del mes en curso, día a día.
 * Se deriva de la ventana de transacciones que el cliente ya tiene; por eso
 * no se dibuja comparación con el mes anterior (esa ventana no lo garantiza).
 */
function PaceCard({
  transactions,
  budgetTotal,
}: {
  transactions: Transaction[]
  budgetTotal: number
}) {
  const { isDark } = useTheme()
  const data = useMemo(() => cumulativeExpense(transactions), [transactions])
  const animate = useFirstDataAnim(data.length >= 2)

  if (data.length < 2) return null

  const spent = data[data.length - 1].total
  const overBudget = budgetTotal > 0 && spent > budgetTotal
  // Serie única: slot 1 de la paleta categórica (el azul de marca)
  const stroke = isDark ? CHART_PALETTE_DARK[0] : CHART_PALETTE_LIGHT[0]

  return (
    <motion.section variants={item} className={`${CARD} p-5 lg:p-6`}>
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="text-[17px] font-semibold tracking-tight">Ritmo de gasto</h2>
        <span className="tnum text-[13px] font-medium text-muted-foreground">
          {formatMoney(spent)} acumulado
        </span>
      </div>

      <div className="mt-3 h-40 w-full lg:h-52">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -8 }}>
            <defs>
              <linearGradient id="pace-fill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={stroke} stopOpacity={0.18} />
                <stop offset="100%" stopColor={stroke} stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="day"
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 11, fill: cssVar("--muted-foreground") }}
              minTickGap={24}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              width={56}
              tick={{ fontSize: 11, fill: cssVar("--muted-foreground") }}
              tickFormatter={(v: number) => formatMoneyCompact(v)}
            />
            {budgetTotal > 0 && (
              <ReferenceLine
                y={budgetTotal}
                stroke={cssVar(overBudget ? "--expense" : "--muted-foreground")}
                strokeDasharray="4 4"
                strokeWidth={1.5}
                label={{
                  value: "Presupuesto total",
                  position: "insideTopLeft",
                  fontSize: 11,
                  fill: cssVar(overBudget ? "--expense" : "--muted-foreground"),
                }}
              />
            )}
            <Tooltip
              cursor={{ stroke: cssVar("--border"), strokeWidth: 1 }}
              content={<PaceTooltip />}
            />
            <Area
              type="monotone"
              dataKey="total"
              stroke={stroke}
              strokeWidth={2}
              fill="url(#pace-fill)"
              activeDot={{ r: 4, strokeWidth: 2, stroke: cssVar("--card") }}
              isAnimationActive={animate}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </motion.section>
  )
}

interface TooltipRow {
  payload: { day: number; total: number }
}

function PaceTooltip({ active, payload }: { active?: boolean; payload?: TooltipRow[] }) {
  if (!active || !payload?.length) return null
  const { day, total } = payload[0].payload
  return (
    <div className="rounded-xl border border-border bg-card px-3 py-2 shadow-lg">
      <p className="text-[11px] font-medium text-muted-foreground">Día {day}</p>
      <p className="tnum text-[14px] font-semibold">{formatMoney(total)}</p>
    </div>
  )
}

/** Serie acumulada de gasto del mes en curso, un punto por día transcurrido. */
function cumulativeExpense(transactions: Transaction[]) {
  const now = new Date()
  const year = now.getFullYear()
  const month = now.getMonth()
  const byDay = new Map<number, number>()

  for (const t of transactions) {
    if (t.type !== "expense") continue
    const d = new Date(t.date + "T12:00:00")
    if (d.getFullYear() !== year || d.getMonth() !== month) continue
    const day = d.getDate()
    byDay.set(day, (byDay.get(day) ?? 0) + t.amount)
  }
  if (byDay.size === 0) return []

  const series: { day: number; total: number }[] = []
  let running = 0
  for (let day = 1; day <= now.getDate(); day++) {
    running += byDay.get(day) ?? 0
    series.push({ day, total: running })
  }
  return series
}

// ── 3 · En qué se va ─────────────────────────────────────────────────────────

interface Slice {
  id: string
  name: string
  total: number
  color: string
  share: number
}

/** Top de categorías del mes; a partir de MAX_SLICES se pliega en "Otros". */
function useSlices(
  byCategory: { categoryId: string; total: number }[] | undefined,
  categories: Category[],
): Slice[] {
  const { isDark } = useTheme()
  return useMemo(() => {
    const rows = (byCategory ?? [])
      .map((row) => ({
        row,
        category: categories.find((c) => c.id === row.categoryId),
      }))
      .filter((r) => r.category)
      .sort((a, b) => b.row.total - a.row.total)

    const sum = rows.reduce((acc, r) => acc + r.row.total, 0)
    if (sum === 0) return []

    const head = rows.slice(0, MAX_SLICES).map(({ row, category }) => ({
      id: row.categoryId,
      name: category!.name,
      total: row.total,
      color: seriesColor(category!.color, isDark),
      share: row.total / sum,
    }))
    const tail = rows.slice(MAX_SLICES)
    if (tail.length > 0) {
      const total = tail.reduce((acc, r) => acc + r.row.total, 0)
      head.push({
        id: "otros",
        name: `Otros (${tail.length})`,
        total,
        color: isDark ? CHART_OTHER.dark : CHART_OTHER.light,
        share: total / sum,
      })
    }
    return head
  }, [byCategory, categories, isDark])
}

function DonutCard({
  slices,
  total,
  overBudgetCount,
}: {
  slices: Slice[]
  total: number
  overBudgetCount: number
}) {
  const animate = useFirstDataAnim(slices.length > 0)

  if (slices.length === 0) {
    return (
      <motion.section variants={item} className={`${CARD} p-5 lg:p-6`}>
        <h2 className="text-[17px] font-semibold tracking-tight">
          ¿En qué se fue el dinero?
        </h2>
        <p className="mt-2 text-[13px] text-muted-foreground">
          Registra un gasto y aquí verás su reparto por categoría.
        </p>
      </motion.section>
    )
  }

  return (
    <motion.section variants={item} className={`${CARD} p-5 lg:p-6`}>
      <div className="flex items-center gap-2">
        <h2 className="text-[17px] font-semibold tracking-tight">
          ¿En qué se fue el dinero?
        </h2>
        {overBudgetCount > 0 && (
          <span
            className="tnum flex size-5 shrink-0 items-center justify-center rounded-full bg-expense text-[11px] font-semibold text-white"
            title={`${overBudgetCount} categoría(s) sobre su presupuesto`}
          >
            {overBudgetCount}
          </span>
        )}
      </div>

      <div className="mt-3 flex items-center gap-5">
        <div className="relative size-32 shrink-0 lg:size-36">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={slices}
                dataKey="total"
                nameKey="name"
                innerRadius="70%"
                outerRadius="100%"
                paddingAngle={2}
                cornerRadius={5}
                strokeWidth={0}
                isAnimationActive={animate}
              >
                {slices.map((s) => (
                  <Cell key={s.id} fill={s.color} />
                ))}
              </Pie>
              <Tooltip content={<SliceTooltip />} />
            </PieChart>
          </ResponsiveContainer>
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-[11px] font-medium text-muted-foreground">Total</span>
            <span className="tnum text-[14px] font-bold tracking-tight">
              {formatMoneyCompact(total)}
            </span>
          </div>
        </div>

        {/* Leyenda: cubre todas las series dibujadas, con valor y % */}
        <ul className="min-w-0 flex-1 space-y-1.5">
          {slices.map((s) => (
            <li key={s.id} className="flex items-center gap-2 text-[13px]">
              <span
                className="size-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: s.color }}
                aria-hidden="true"
              />
              <span className="min-w-0 flex-1 truncate font-medium">{s.name}</span>
              <span className="tnum shrink-0 text-muted-foreground">
                {formatMoneyCompact(s.total)}
              </span>
              <span className="tnum w-9 shrink-0 text-right text-muted-foreground">
                {Math.round(s.share * 100)}%
              </span>
            </li>
          ))}
        </ul>
      </div>
    </motion.section>
  )
}

function SliceTooltip({
  active,
  payload,
}: {
  active?: boolean
  payload?: { payload: Slice }[]
}) {
  if (!active || !payload?.length) return null
  const s = payload[0].payload
  return (
    <div className="rounded-xl border border-border bg-card px-3 py-2 shadow-lg">
      <p className="flex items-center gap-1.5 text-[11px] font-medium text-muted-foreground">
        <span
          className="size-2 rounded-full"
          style={{ backgroundColor: s.color }}
          aria-hidden="true"
        />
        {s.name}
      </p>
      <p className="tnum text-[14px] font-semibold">
        {formatMoney(s.total)} · {Math.round(s.share * 100)}%
      </p>
    </div>
  )
}

function BudgetsCard({
  budgets,
  status,
  categories,
}: {
  budgets: Budget[]
  status: BudgetStatus[]
  categories: Category[]
}) {
  const { isDark } = useTheme()
  const [sheetOpen, setSheetOpen] = useState(false)
  const [editing, setEditing] = useState<Budget | undefined>(undefined)

  function openCreate() {
    setEditing(undefined)
    setSheetOpen(true)
  }

  function openEdit(budget: Budget) {
    setEditing(budget)
    setSheetOpen(true)
  }

  const rows = budgets
    .map((b) => ({
      budget: b,
      category: categories.find((c) => c.id === b.categoryId),
      status: status.find((s) => s.categoryId === b.categoryId),
    }))
    .filter((row) => row.category)

  return (
    <>
      <motion.section variants={item} className={`${CARD} p-5 lg:p-6`}>
        <div className="flex items-baseline justify-between">
          <h2 className="text-[17px] font-semibold tracking-tight">Presupuestos</h2>
          <button
            onClick={openCreate}
            aria-label="Nuevo presupuesto"
            /* el pseudo-elemento lleva el área táctil a 44px sin agrandar el botón */
            className="pressable relative flex size-7 items-center justify-center rounded-full bg-secondary text-secondary-foreground before:absolute before:-inset-2 before:content-['']"
          >
            <Plus size={16} strokeWidth={2.5} />
          </button>
        </div>

        {rows.length === 0 ? (
          <p className="mt-2 text-[13px] text-muted-foreground">
            Pon un límite mensual a una categoría de gasto para verla aquí.
          </p>
        ) : (
          <ul className="mt-3 space-y-3">
            {rows.map((row) => {
              const spent = row.status?.spent ?? 0
              const percentage = row.status?.percentage ?? 0
              const tone =
                percentage >= 100
                  ? "text-expense"
                  : percentage >= 75
                    ? "text-warning"
                    : "text-muted-foreground"
              return (
                <li
                  key={row.budget.id}
                  onClick={() => openEdit(row.budget)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault()
                      openEdit(row.budget)
                    }
                  }}
                  className="pressable cursor-pointer"
                >
                  <div className="mb-1 flex items-center gap-2 text-[13px]">
                    <span
                      className="size-2.5 shrink-0 rounded-full"
                      style={{ backgroundColor: seriesColor(row.category!.color, isDark) }}
                      aria-hidden="true"
                    />
                    <span className="min-w-0 flex-1 truncate font-medium">
                      {row.category!.name}
                    </span>
                    {/* El % en texto hace redundante el color de la barra */}
                    <span className={`tnum shrink-0 font-semibold ${tone}`}>
                      {Math.round(percentage)}%
                    </span>
                    <span className="tnum shrink-0 text-muted-foreground">
                      {formatMoney(spent, true)} / {formatMoney(row.budget.amount, true)}
                    </span>
                  </div>
                  <BudgetBar percentage={percentage} />
                </li>
              )
            })}
          </ul>
        )}
      </motion.section>
      <BudgetFormSheet open={sheetOpen} onOpenChange={setSheetOpen} budget={editing} />
    </>
  )
}

function AccountsSummary({ accounts }: { accounts: Account[] }) {
  return (
    <motion.section variants={item} className={`${CARD} p-5 lg:p-6`}>
      <div className="flex items-baseline justify-between">
        <h2 className="text-[17px] font-semibold tracking-tight">Cuentas</h2>
        <Link to="/app/cuentas" className="text-[13px] font-medium text-primary">
          Ver todas
        </Link>
      </div>
      <ul className="mt-2 space-y-1">
        {accounts.map((a) => {
          const Icon = kindIcon[a.kind]
          return (
            <li key={a.id} className="flex items-center gap-3 py-1.5">
              <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-secondary text-secondary-foreground">
                <Icon size={16} />
              </span>
              <span className="min-w-0 flex-1 truncate text-[14px] font-medium">
                {a.name}
              </span>
              <span
                className={`tnum shrink-0 text-[14px] font-semibold ${
                  a.balance < 0 ? "text-expense" : ""
                }`}
              >
                {formatMoney(a.balance)}
              </span>
            </li>
          )
        })}
      </ul>
    </motion.section>
  )
}

// ── 4 · Qué acaba de pasar ───────────────────────────────────────────────────

function RecentCard({
  transactions,
  categories,
  accounts,
  members,
}: {
  transactions: Transaction[]
  categories: Category[]
  accounts: Account[]
  members: Member[]
}) {
  const rows = transactions.slice(0, 6)
  return (
    <motion.section variants={item} className={CARD}>
      <div className="flex items-baseline justify-between px-5 pt-5 pb-1">
        <h2 className="text-[17px] font-semibold tracking-tight">
          Movimientos recientes
        </h2>
        <Link to="/app/transacciones" className="text-[13px] font-medium text-primary">
          Ver todos
        </Link>
      </div>
      {rows.length === 0 ? (
        <p className="px-5 pt-2 pb-5 text-[13px] text-muted-foreground">
          Todavía no hay movimientos. Registra el primero con el botón +.
        </p>
      ) : (
        <ul className="divide-y divide-border pb-2">
          {rows.map((t) => (
            <TransactionItem
              key={t.id}
              transaction={t}
              category={categories.find((c) => c.id === t.categoryId)}
              account={accounts.find((a) => a.id === t.accountId)}
              member={members.find((m) => m.id === t.memberId)}
            />
          ))}
        </ul>
      )}
    </motion.section>
  )
}
