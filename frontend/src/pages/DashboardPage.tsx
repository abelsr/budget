import { useState } from "react"
import { Link } from "react-router-dom"
import { motion } from "motion/react"
import { Cell, Pie, PieChart, ResponsiveContainer } from "recharts"
import {
  CreditCard,
  Landmark,
  Plus,
  PiggyBank,
  TrendingDown,
  TrendingUp,
  Wallet,
} from "lucide-react"

import { formatMoney, monthLabel } from "@/lib/format"
import {
  useAccounts,
  useBudgets,
  useBudgetsStatus,
  useCategories,
  useMembers,
  useMonthSummary,
  useTransactions,
} from "@/lib/queries"
import { springAppear } from "@/lib/springs"
import type { Account, Budget, BudgetStatus, Category, Member, Transaction } from "@/lib/types"
import { BudgetBar } from "@/components/BudgetBar"
import { BudgetFormSheet } from "@/components/BudgetFormSheet"
import { TransactionItem } from "@/components/TransactionItem"
import { TicketScannerButton } from "@/components/TicketScanner"

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06 } },
}
const item = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: springAppear },
}

/**
 * Dashboard.
 * - Móvil: una columna (balance → mes → escáner → dona → recientes).
 * - Escritorio: dos columnas; la principal respira con más aire y la
 *   lateral agrupa análisis (escáner, dona, cuentas).
 */
export function DashboardPage() {
  const { data: accounts = [] } = useAccounts()
  const { data: categories = [] } = useCategories()
  const { data: members = [] } = useMembers()
  const { data: transactions = [] } = useTransactions()
  const { data: summary } = useMonthSummary()
  const { data: budgets = [] } = useBudgets()
  const { data: budgetsStatus = [] } = useBudgetsStatus()

  const donutData = (summary?.byCategory ?? [])
    .map((row) => ({
      ...row,
      category: categories.find((c) => c.id === row.categoryId),
    }))
    .filter((row) => row.category)

  const overBudgetCount = budgetsStatus.filter((s) => s.percentage >= 100).length

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

      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:gap-6">
        {/* Columna principal */}
        <div className="flex min-w-0 flex-1 flex-col gap-4 lg:gap-6">
          <div className="grid gap-4 lg:gap-6 xl:grid-cols-5">
            <div className="xl:col-span-3">
              <BalanceCard accounts={accounts} />
            </div>
            <div className="xl:col-span-2">
              <MonthCards income={summary?.income ?? 0} expense={summary?.expense ?? 0} />
            </div>
          </div>

          {/* Móvil: escáner y dona van en el flujo principal */}
          <motion.div variants={item} className="lg:hidden">
            <TicketScannerButton />
          </motion.div>
          <div className="lg:hidden">
            <DonutCard data={donutData} overBudgetCount={overBudgetCount} />
          </div>
          <div className="lg:hidden">
            <BudgetsCard budgets={budgets} status={budgetsStatus} categories={categories} />
          </div>

          <RecentCard
            transactions={transactions.slice(0, 5)}
            categories={categories}
            accounts={accounts}
            members={members}
          />
        </div>

        {/* Columna lateral (solo escritorio) */}
        <div className="hidden w-[340px] shrink-0 flex-col gap-4 lg:flex lg:gap-6 xl:w-[380px]">
          <motion.div variants={item}>
            <TicketScannerButton />
          </motion.div>
          <DonutCard data={donutData} overBudgetCount={overBudgetCount} />
          <BudgetsCard budgets={budgets} status={budgetsStatus} categories={categories} />
          <AccountsSummary accounts={accounts} />
        </div>
      </div>
    </motion.div>
  )
}

function BalanceCard({ accounts }: { accounts: Account[] }) {
  const totalBalance = accounts.reduce((sum, a) => sum + a.balance, 0)
  return (
    <motion.section
      variants={item}
      className="h-full rounded-3xl bg-card p-6 shadow-sm lg:p-8"
    >
      <p className="text-[13px] font-medium text-muted-foreground">
        Balance total
      </p>
      <p className="tnum mt-1 text-[40px] leading-none font-bold tracking-tight lg:text-5xl">
        {formatMoney(totalBalance)}
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        {accounts.map((a) => (
          <span
            key={a.id}
            className="tnum shrink-0 rounded-full bg-secondary px-3 py-1 text-[12px] font-medium text-secondary-foreground"
          >
            {a.name} · {formatMoney(a.balance, true)}
          </span>
        ))}
      </div>
    </motion.section>
  )
}

function MonthCards({ income, expense }: { income: number; expense: number }) {
  return (
    <motion.section
      variants={item}
      className="grid h-full grid-cols-2 gap-3 lg:gap-4 xl:grid-cols-1 xl:grid-rows-2"
    >
      <div className="rounded-3xl bg-card p-4 shadow-sm lg:p-5">
        <div className="flex items-center gap-1.5 text-[13px] font-medium text-muted-foreground">
          <TrendingUp size={15} className="text-income" />
          Ingresos
        </div>
        <p className="tnum mt-1 text-xl font-bold text-income lg:text-2xl">
          {formatMoney(income)}
        </p>
      </div>
      <div className="rounded-3xl bg-card p-4 shadow-sm lg:p-5">
        <div className="flex items-center gap-1.5 text-[13px] font-medium text-muted-foreground">
          <TrendingDown size={15} className="text-expense" />
          Gastos
        </div>
        <p className="tnum mt-1 text-xl font-bold lg:text-2xl">
          {formatMoney(expense)}
        </p>
      </div>
    </motion.section>
  )
}

function DonutCard({
  data,
  overBudgetCount,
}: {
  data: { categoryId: string; total: number; category?: Category }[]
  overBudgetCount: number
}) {
  if (data.length === 0) return null
  return (
    <motion.section
      variants={item}
      className="rounded-3xl bg-card p-5 shadow-sm lg:p-6"
    >
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
      <div className="mt-2 flex items-center gap-4">
        <div className="size-36 shrink-0 lg:size-40">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                dataKey="total"
                nameKey="category.name"
                innerRadius="72%"
                outerRadius="100%"
                paddingAngle={3}
                cornerRadius={6}
                strokeWidth={0}
              >
                {data.map((row) => (
                  <Cell key={row.categoryId} fill={row.category!.color} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
        </div>
        <ul className="min-w-0 flex-1 space-y-1.5">
          {data.slice(0, 5).map((row) => (
            <li key={row.categoryId} className="flex items-center gap-2 text-[13px]">
              <span
                className="size-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: row.category!.color }}
              />
              <span className="min-w-0 flex-1 truncate font-medium">
                {row.category!.name}
              </span>
              <span className="tnum shrink-0 text-muted-foreground">
                {formatMoney(row.total)}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </motion.section>
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

  if (budgets.length === 0) {
    return (
      <>
        <motion.section
          variants={item}
          className="rounded-3xl bg-card p-5 shadow-sm lg:p-6"
        >
          <div className="flex items-baseline justify-between">
            <h2 className="text-[17px] font-semibold tracking-tight">
              Presupuestos
            </h2>
            <button
              onClick={openCreate}
              aria-label="Nuevo presupuesto"
              className="pressable flex size-7 items-center justify-center rounded-full bg-secondary text-secondary-foreground"
            >
              <Plus size={16} strokeWidth={2.5} />
            </button>
          </div>
          <p className="mt-2 text-[13px] text-muted-foreground">
            Pon un límite mensual a una categoría de gasto para verla aquí.
          </p>
        </motion.section>
        <BudgetFormSheet open={sheetOpen} onOpenChange={setSheetOpen} budget={editing} />
      </>
    )
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
      <motion.section
        variants={item}
        className="rounded-3xl bg-card p-5 shadow-sm lg:p-6"
      >
        <div className="flex items-baseline justify-between">
          <h2 className="text-[17px] font-semibold tracking-tight">
            Presupuestos
          </h2>
          <button
            onClick={openCreate}
            aria-label="Nuevo presupuesto"
            className="pressable flex size-7 items-center justify-center rounded-full bg-secondary text-secondary-foreground"
          >
            <Plus size={16} strokeWidth={2.5} />
          </button>
        </div>
        <ul className="mt-3 space-y-3">
          {rows.map((row) => {
            const spent = row.status?.spent ?? 0
            const percentage = row.status?.percentage ?? 0
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
                    style={{ backgroundColor: row.category!.color }}
                  />
                  <span className="min-w-0 flex-1 truncate font-medium">
                    {row.category!.name}
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
      </motion.section>
      <BudgetFormSheet open={sheetOpen} onOpenChange={setSheetOpen} budget={editing} />
    </>
  )
}

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
  return (
    <motion.section variants={item} className="rounded-3xl bg-card shadow-sm">
      <div className="flex items-baseline justify-between px-4 pt-4 pb-1 lg:px-5">
        <h2 className="text-[17px] font-semibold tracking-tight">
          Movimientos recientes
        </h2>
        <Link to="/transacciones" className="text-[13px] font-medium text-primary">
          Ver todos
        </Link>
      </div>
      <ul className="divide-y divide-border/60 pb-2">
        {transactions.map((t) => (
          <TransactionItem
            key={t.id}
            transaction={t}
            category={categories.find((c) => c.id === t.categoryId)}
            account={accounts.find((a) => a.id === t.accountId)}
            member={members.find((m) => m.id === t.memberId)}
          />
        ))}
      </ul>
    </motion.section>
  )
}

const kindIcon = { cash: Wallet, debit: Landmark, credit: CreditCard, savings: PiggyBank }

function AccountsSummary({ accounts }: { accounts: Account[] }) {
  return (
    <motion.section variants={item} className="rounded-3xl bg-card p-5 shadow-sm">
      <div className="flex items-baseline justify-between">
        <h2 className="text-[17px] font-semibold tracking-tight">Cuentas</h2>
        <Link to="/cuentas" className="text-[13px] font-medium text-primary">
          Ver todas
        </Link>
      </div>
      <ul className="mt-2 space-y-1">
        {accounts.map((a) => {
          const Icon = kindIcon[a.kind]
          return (
            <li key={a.id} className="flex items-center gap-3 py-1.5">
              <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-secondary text-secondary-foreground">
                <Icon size={15} />
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
