import { useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { motion } from "motion/react"
import {
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import {
  ChevronDown,
  CreditCard,
  Eye,
  EyeOff,
  Landmark,
  PiggyBank,
  Wallet,
} from "lucide-react"

import { TicketScannerButton } from "@/components/TicketScanner"
import { TransactionItem } from "@/components/TransactionItem"
import { useAuth } from "@/lib/auth"
import { CHART_OTHER, seriesColor } from "@/lib/chart-colors"
import { formatMoney, formatMoneyCompact, monthLabel } from "@/lib/format"
import {
  useAccounts,
  useCategories,
  useMembers,
  useMonthSummary,
  useTransactions,
} from "@/lib/queries"
import { useTheme } from "@/lib/theme"
import type { Account, Category, Member, Transaction } from "@/lib/types"

const kindIcon = { cash: Wallet, debit: Landmark, credit: CreditCard, savings: PiggyBank }
const MAX_SLICES = 6

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.04 } },
}
const item = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: { duration: 0.25 } },
}

export function DashboardPage() {
  const [balancesVisible, setBalancesVisible] = useState(true)
  const { session } = useAuth()
  const { data: accounts = [] } = useAccounts()
  const { data: categories = [] } = useCategories()
  const { data: members = [] } = useMembers()
  const { data: transactions = [] } = useTransactions()
  const { data: summary } = useMonthSummary()
  const slices = useSlices(summary?.byCategory, categories)

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="flex flex-col gap-3 lg:gap-4">
      <motion.header variants={item} className="px-1">
        <p className="hidden text-[13px] font-medium text-muted-foreground lg:block">{monthLabel()}</p>
        <p className="text-[13px] font-medium text-foreground lg:hidden">Hola, {firstName(session?.name)} <span aria-hidden="true">👋</span></p>
        <h1 className="mt-0.5 text-[23px] font-bold tracking-tight lg:text-[20px]">Resumen</h1>
      </motion.header>

      <div className="grid gap-3 lg:grid-cols-12 lg:gap-4">
        <div className="min-w-0 lg:col-span-4"><BalanceCard accounts={accounts} visible={balancesVisible} onVisibilityChange={() => setBalancesVisible((current) => !current)} /></div>
        <div className="min-w-0 lg:col-span-4"><AccountsCard accounts={accounts} concealed={!balancesVisible} /></div>
        <div className="min-w-0 lg:col-span-4"><FlowChart income={summary?.income ?? 0} expense={summary?.expense ?? 0} transactions={transactions} concealed={!balancesVisible} /></div>

        <div className="min-w-0 lg:col-span-5"><CategoryCard slices={slices} total={summary?.expense ?? 0} concealed={!balancesVisible} /></div>
        <div className="min-w-0 lg:col-span-4"><RecentCard transactions={transactions} categories={categories} accounts={accounts} members={members} concealed={!balancesVisible} /></div>
        <motion.div variants={item} className="min-w-0 lg:col-span-3"><TicketScannerButton /></motion.div>
      </div>
    </motion.div>
  )
}

function firstName(name?: string) {
  return name?.trim().split(/\s+/)[0] || ""
}

function maskedMoney(amount: number, concealed: boolean) {
  return concealed ? "••••••" : formatMoney(amount)
}

function BalanceCard({ accounts, visible, onVisibilityChange }: { accounts: Account[]; visible: boolean; onVisibilityChange: () => void }) {
  const total = accounts.reduce((sum, account) => sum + account.balance, 0)
  const shown = visible ? formatMoney(total) : "••••••••"

  return (
    <motion.section variants={item} className="surface-brand dashboard-balance relative min-h-40 overflow-hidden p-4 lg:min-h-47 lg:p-4.5">
      <svg aria-hidden="true" viewBox="0 0 400 100" preserveAspectRatio="none" className="pointer-events-none absolute inset-x-0 bottom-0 h-23 w-full text-primary-foreground/35">
        <path d="M0 77 Q 45 86, 82 65 T 150 48 T 223 55 T 287 24 T 347 52 T 400 45" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        <path d="M0 77 Q 45 86, 82 65 T 150 48 T 223 55 T 287 24 T 347 52 T 400 45 L400 100 L0 100 Z" fill="currentColor" opacity="0.22" />
      </svg>
      <div className="relative">
        <div className="flex items-center justify-between">
          <p className="text-[12px] font-medium text-primary-foreground/85">Saldo total</p>
          <button onClick={onVisibilityChange} aria-label={visible ? "Ocultar saldos" : "Mostrar saldos"} className="pressable flex size-8 items-center justify-center rounded-full text-primary-foreground/90 hover:bg-primary-foreground/10">
            {visible ? <Eye size={16} /> : <EyeOff size={16} />}
          </button>
        </div>
        <p className="tnum mt-2 truncate text-[27px] font-bold leading-none tracking-tight lg:text-[30px]">{shown}</p>
      </div>
    </motion.section>
  )
}

function AccountsCard({ accounts, concealed }: { accounts: Account[]; concealed: boolean }) {
  return (
    <motion.section variants={item} className="dashboard-card p-3.5 lg:p-4">
      <CardHeading title="Por cuenta" href="/app/cuentas" label="Ver todas" />
      {accounts.length === 0 ? (
        <p className="pt-5 text-[13px] text-muted-foreground">Agrega una cuenta para ver tu saldo.</p>
      ) : (
        <ul className="mt-2 divide-y divide-border">
          {accounts.map((account) => {
            const Icon = kindIcon[account.kind]
            return <li key={account.id} className="flex min-w-0 items-center gap-2.5 py-2"><span className="flex size-6 shrink-0 items-center justify-center rounded-md bg-primary-soft text-primary"><Icon size={14} /></span><span className="min-w-0 flex-1 truncate text-[12px] font-medium">{account.name}</span><span className={`tnum max-w-[45%] shrink truncate text-[12px] font-semibold ${!concealed && account.balance < 0 ? "text-expense" : ""}`}>{maskedMoney(account.balance, concealed)}</span></li>
          })}
        </ul>
      )}
    </motion.section>
  )
}

function FlowChart({ income, expense, transactions, concealed }: { income: number; expense: number; transactions: Transaction[]; concealed: boolean }) {
  const daily = useMemo(() => dailyFlow(transactions), [transactions])
  return (
    <motion.section variants={item} className="dashboard-card p-3.5 lg:p-4">
      <div className="flex items-center justify-between gap-2"><h2 className="text-[13px] font-semibold">Ingresos vs Gastos</h2><span aria-label="Mes mostrado: este mes" className="flex items-center gap-1 rounded-md border border-border px-2 py-1 text-[10px] font-medium text-muted-foreground">Este mes <ChevronDown size={12} /></span></div>
      <div className="mt-3 grid grid-cols-2 gap-3"><Stat label="Ingresos" amount={income} tone="text-income" concealed={concealed} /><Stat label="Gastos" amount={expense} tone="text-expense" concealed={concealed} /></div>
      {daily.length === 0 ? <p className="flex h-22 items-end text-[12px] text-muted-foreground">Aún no hay movimientos este mes.</p> : <div className="mt-2 h-23" role="img" aria-label={concealed ? `Barras diarias de ${monthLabel()}: montos ocultos` : `Barras diarias de ${monthLabel()}: ingresos ${formatMoney(income)} y gastos ${formatMoney(expense)}`}><ResponsiveContainer width="100%" height="100%"><BarChart data={daily} barGap={2} barCategoryGap="30%" margin={{ top: 4, right: 0, left: -20, bottom: 0 }}><XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fontSize: 9, fill: "var(--muted-foreground)" }} interval="preserveStartEnd" /><YAxis hide /><Tooltip cursor={{ fill: "var(--secondary)" }} content={<FlowTooltip concealed={concealed} />} /><Bar dataKey="income" name="Ingresos" fill="var(--income)" radius={[2, 2, 0, 0]} /><Bar dataKey="expense" name="Gastos" fill="var(--expense)" radius={[2, 2, 0, 0]} /></BarChart></ResponsiveContainer></div>}
      <div className="mt-1 flex justify-center gap-3 text-[10px] text-muted-foreground"><span><i className="mr-1 inline-block size-1.5 rounded-sm bg-income" />Ingresos</span><span><i className="mr-1 inline-block size-1.5 rounded-sm bg-expense" />Gastos</span></div>
    </motion.section>
  )
}

function Stat({ label, amount, tone, concealed }: { label: string; amount: number; tone: string; concealed: boolean }) { return <div className="min-w-0"><p className="text-[10px] text-muted-foreground">{label}</p><p className={`tnum mt-0.5 truncate text-[13px] font-semibold ${tone}`}>{maskedMoney(amount, concealed)}</p></div> }

function dailyFlow(transactions: Transaction[]) {
  const now = new Date(); const year = now.getFullYear(); const month = now.getMonth(); const days = new Map<number, { income: number; expense: number }>()
  for (const transaction of transactions) { const date = new Date(`${transaction.date}T12:00:00`); if (date.getFullYear() !== year || date.getMonth() !== month) continue; const row = days.get(date.getDate()) ?? { income: 0, expense: 0 }; row[transaction.type] += transaction.amount; days.set(date.getDate(), row) }
  return [...days.entries()].sort(([a], [b]) => a - b).map(([day, amounts]) => ({ label: String(day), ...amounts }))
}

function FlowTooltip({ active, payload, concealed }: { active?: boolean; payload?: { name: string; value: number; payload: { label: string } }[]; concealed: boolean }) {
  if (!active || !payload?.length) return null
  return <div className="rounded-md border border-border bg-card px-2 py-1.5 text-[11px] shadow-sm"><p className="text-muted-foreground">Día {payload[0].payload.label}</p>{payload.map((row) => <p key={row.name} className="tnum font-medium">{row.name}: {maskedMoney(row.value, concealed)}</p>)}</div>
}

interface Slice { id: string; name: string; total: number; color: string; share: number }
function useSlices(byCategory: { categoryId: string; total: number }[] | undefined, categories: Category[]) {
  const { isDark } = useTheme()
  return useMemo(() => { const rows = (byCategory ?? []).map((row) => ({ row, category: categories.find((category) => category.id === row.categoryId) })).filter((row) => row.category).sort((a, b) => b.row.total - a.row.total); const sum = rows.reduce((total, row) => total + row.row.total, 0); if (!sum) return []; const slices = rows.slice(0, MAX_SLICES).map(({ row, category }) => ({ id: row.categoryId, name: category!.name, total: row.total, color: seriesColor(category!.color, isDark), share: row.total / sum })); const rest = rows.slice(MAX_SLICES); if (rest.length) { const total = rest.reduce((amount, row) => amount + row.row.total, 0); slices.push({ id: "other", name: "Otros", total, color: isDark ? CHART_OTHER.dark : CHART_OTHER.light, share: total / sum }) } return slices }, [byCategory, categories, isDark])
}

function CategoryCard({ slices, total, concealed }: { slices: Slice[]; total: number; concealed: boolean }) {
  return <motion.section variants={item} className="dashboard-card min-w-0 p-3.5 lg:p-4"><CardHeading title="Gastos por categoría" href="/app/categorias" label="Ver reporte" />{slices.length === 0 ? <p className="py-10 text-[13px] text-muted-foreground">Registra un gasto y aquí verás su reparto.</p> : <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4"><div className="relative size-34 shrink-0 self-center" role="img" aria-label={concealed ? "Distribución de gastos por categoría, montos ocultos" : `Distribución de gastos por categoría, total ${formatMoney(total)}`}><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={slices} dataKey="total" nameKey="name" innerRadius="63%" outerRadius="96%" paddingAngle={1.5} strokeWidth={0}>{slices.map((slice) => <Cell key={slice.id} fill={slice.color} />)}</Pie><Tooltip content={<SliceTooltip concealed={concealed} />} /></PieChart></ResponsiveContainer><div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center"><span className="tnum text-[14px] font-bold">{concealed ? "••••••" : formatMoneyCompact(total)}</span><span className="text-[10px] text-muted-foreground">Total</span></div></div><ul className="min-w-0 w-full flex-1 space-y-1.5">{slices.map((slice) => <li key={slice.id} className="flex min-w-0 items-center gap-1.5 text-[11px]"><span className="size-2 shrink-0 rounded-full" style={{ backgroundColor: slice.color }} /><span className="min-w-0 flex-1 truncate">{slice.name}</span><span className="tnum max-w-[40%] shrink truncate text-muted-foreground">{concealed ? "••••" : formatMoneyCompact(slice.total)}</span><span className="tnum w-7 shrink-0 text-right text-muted-foreground">{Math.round(slice.share * 100)}%</span></li>)}</ul></div>}</motion.section>
}

function SliceTooltip({ active, payload, concealed }: { active?: boolean; payload?: { payload: Slice }[]; concealed: boolean }) { if (!active || !payload?.length) return null; const slice = payload[0].payload; return <div className="rounded-md border border-border bg-card px-2 py-1.5 text-[11px] shadow-sm"><p>{slice.name}</p><p className="tnum font-medium">{maskedMoney(slice.total, concealed)} · {Math.round(slice.share * 100)}%</p></div> }

function RecentCard({ transactions, categories, accounts, members, concealed }: { transactions: Transaction[]; categories: Category[]; accounts: Account[]; members: Member[]; concealed: boolean }) {
  const rows = transactions.slice(0, 5)
  return <motion.section variants={item} className="dashboard-card overflow-hidden"><div className="px-3.5 pt-3.5"><CardHeading title="Movimientos recientes" href="/app/transacciones" label="Ver todos" /></div>{rows.length === 0 ? <p className="px-3.5 py-8 text-[13px] text-muted-foreground">Todavía no hay movimientos.</p> : <ul className="mt-1 divide-y divide-border">{rows.map((transaction) => <TransactionItem key={transaction.id} transaction={transaction} category={categories.find((category) => category.id === transaction.categoryId)} account={accounts.find((account) => account.id === transaction.accountId)} member={members.find((member) => member.id === transaction.memberId)} hideAmount={concealed} />)}</ul>}</motion.section>
}

function CardHeading({ title, href, label }: { title: string; href: string; label: string }) { return <div className="flex min-w-0 items-center justify-between gap-3"><h2 className="min-w-0 truncate text-[13px] font-semibold">{title}</h2><Link to={href} className="shrink-0 text-[11px] font-medium text-primary">{label}</Link></div> }
