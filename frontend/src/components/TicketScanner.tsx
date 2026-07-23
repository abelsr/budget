import { useCallback, useRef, useState } from "react"
import { Camera, ImagePlus, ScanLine, Sparkles, TriangleAlert } from "lucide-react"
import { AnimatePresence, motion } from "motion/react"

import { Button } from "@/components/ui/button"
import {
  Drawer,
  DrawerContent,
  DrawerTitle,
  DrawerTrigger,
} from "@/components/ui/drawer"
import { CategoryIcon } from "@/components/CategoryIcon"
import { useAccounts, useAddTransaction, useCategories } from "@/lib/queries"
import { ApiError } from "@/lib/api"
import { analyzeTicket, type TicketScanResult } from "@/lib/scan"
import { springAppear } from "@/lib/springs"
import { formatMoney } from "@/lib/format"

/**
 * Escaneo de ticket con IA.
 * Flujo: elegir/tomar foto → preview → analizar (backend real) → revisar
 * campos editables → guardar como gasto; si el análisis falla, pantalla
 * de error con reintento. El análisis vive en lib/scan.ts.
 */
export function TicketScannerButton({
  variant = "banner",
}: {
  variant?: "banner" | "nav"
}) {
  const [open, setOpen] = useState(false)
  return (
    <Drawer open={open} onOpenChange={setOpen} showSwipeHandle>
      {variant === "banner" ? (
        <DrawerTrigger
          render={
            <button className="pressable flex w-full items-center gap-3 rounded-3xl bg-primary/10 p-4 text-left">
              <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
                <ScanLine size={20} />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-[15px] font-semibold text-primary">
                  Escanear ticket
                </span>
                <span className="block text-[13px] text-primary/70">
                  Sube una foto y la IA registra el gasto por ti
                </span>
              </span>
              <Sparkles size={18} className="shrink-0 text-primary/50" />
            </button>
          }
        />
      ) : (
        <DrawerTrigger
          render={
            <button className="pressable relative flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-[15px] font-medium text-foreground/70 hover:bg-black/5 dark:hover:bg-white/10">
              <ScanLine size={20} />
              Escanear ticket
            </button>
          }
        />
      )}
      <DrawerContent className="mx-auto max-w-lg">
        {open && <ScannerFlow onDone={() => setOpen(false)} />}
      </DrawerContent>
    </Drawer>
  )
}

type Step =
  | { name: "pick" }
  | { name: "preview"; file: File; url: string }
  | { name: "analyzing"; url: string }
  | { name: "review"; url: string; result: TicketScanResult }
  | { name: "error"; message: string }

function ScannerFlow({ onDone }: { onDone: () => void }) {
  const [step, setStep] = useState<Step>({ name: "pick" })
  const inputRef = useRef<HTMLInputElement>(null)

  const pickFile = useCallback((file: File | undefined) => {
    if (!file || !file.type.startsWith("image/")) return
    setStep({ name: "preview", file, url: URL.createObjectURL(file) })
  }, [])

  async function analyze(file: File, url: string) {
    setStep({ name: "analyzing", url })
    try {
      const result = await analyzeTicket(file)
      setStep({ name: "review", url, result })
    } catch (err) {
      // ApiError trae el detail del servidor (p. ej. 501 sin GEMINI_API_KEY)
      const message =
        err instanceof ApiError
          ? err.message
          : "No se pudo analizar el ticket. Inténtalo de nuevo."
      setStep({ name: "error", message })
    }
  }

  return (
    <div className="flex flex-col gap-5 px-5 pb-8">
      <DrawerTitle className="text-center text-[17px] font-semibold tracking-tight">
        Escanear ticket
      </DrawerTitle>

      <AnimatePresence mode="wait">
        <motion.div
          key={step.name}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={springAppear}
        >
          {step.name === "pick" && (
            <PickStep
              inputRef={inputRef}
              onFile={pickFile}
            />
          )}
          {step.name === "preview" && (
            <PreviewStep
              url={step.url}
              onAnalyze={() => analyze(step.file, step.url)}
              onRetry={() => setStep({ name: "pick" })}
            />
          )}
          {step.name === "analyzing" && <AnalyzingStep url={step.url} />}
          {step.name === "review" && (
            <ReviewStep url={step.url} result={step.result} onDone={onDone} />
          )}
          {step.name === "error" && (
            <ErrorStep
              message={step.message}
              onRetry={() => setStep({ name: "pick" })}
              onDone={onDone}
            />
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}

function PickStep({
  inputRef,
  onFile,
}: {
  inputRef: React.RefObject<HTMLInputElement | null>
  onFile: (file: File | undefined) => void
}) {
  const [dragging, setDragging] = useState(false)
  return (
    <div className="flex flex-col gap-3">
      <button
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          onFile(e.dataTransfer.files[0])
        }}
        className={`flex flex-col items-center gap-3 rounded-3xl border-2 border-dashed p-10 transition-colors ${
          dragging ? "border-primary bg-primary/5" : "border-border"
        }`}
      >
        <span className="flex size-14 items-center justify-center rounded-full bg-secondary text-muted-foreground">
          <ImagePlus size={26} />
        </span>
        <span className="text-[15px] font-medium">
          Arrastra una foto o toca para elegir
        </span>
        <span className="text-[13px] text-muted-foreground">
          En el celular puedes tomar la foto directamente
        </span>
      </button>
      {/* capture="environment": abre la cámara trasera en móvil */}
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={(e) => onFile(e.target.files?.[0])}
      />
    </div>
  )
}

function PreviewStep({
  url,
  onAnalyze,
  onRetry,
}: {
  url: string
  onAnalyze: () => void
  onRetry: () => void
}) {
  return (
    <div className="flex flex-col gap-4">
      <img
        src={url}
        alt="Ticket"
        className="max-h-64 w-full rounded-2xl object-contain bg-secondary"
      />
      <div className="flex gap-2">
        <Button variant="secondary" onClick={onRetry} className="pressable flex-1 rounded-2xl">
          Elegir otra
        </Button>
        <Button onClick={onAnalyze} className="pressable flex-1 rounded-2xl">
          <Camera size={16} />
          Analizar con IA
        </Button>
      </div>
    </div>
  )
}

function AnalyzingStep({ url }: { url: string }) {
  return (
    <div className="flex flex-col items-center gap-5 py-2">
      <div className="relative">
        <img
          src={url}
          alt=""
          className="max-h-40 rounded-2xl object-contain opacity-60"
        />
        {/* Línea de escaneo animada */}
        <motion.div
          className="absolute inset-x-2 h-0.5 rounded-full bg-primary shadow-[0_0_12px_2px] shadow-primary/60"
          animate={{ top: ["8%", "92%", "8%"] }}
          transition={{ duration: 2.2, repeat: Infinity, ease: "easeInOut" }}
        />
      </div>
      <p className="text-[14px] font-medium text-muted-foreground">
        Analizando ticket…
      </p>
      <div className="w-full space-y-2">
        <div className="h-4 w-2/3 animate-pulse rounded-full bg-secondary" />
        <div className="h-4 w-1/3 animate-pulse rounded-full bg-secondary" />
        <div className="h-4 w-1/2 animate-pulse rounded-full bg-secondary" />
      </div>
    </div>
  )
}

function ErrorStep({
  message,
  onRetry,
  onDone,
}: {
  message: string
  onRetry: () => void
  onDone: () => void
}) {
  return (
    <div className="flex flex-col items-center gap-4 py-2">
      <span className="flex size-14 items-center justify-center rounded-full bg-expense/10 text-expense">
        <TriangleAlert size={26} />
      </span>
      <p className="text-center text-[15px] font-medium">{message}</p>
      <div className="flex w-full gap-2">
        <Button
          variant="secondary"
          onClick={onDone}
          className="pressable flex-1 rounded-2xl"
        >
          Cerrar
        </Button>
        <Button onClick={onRetry} className="pressable flex-1 rounded-2xl">
          Intentar de nuevo
        </Button>
      </div>
    </div>
  )
}

function ReviewStep({
  url,
  result,
  onDone,
}: {
  url: string
  result: TicketScanResult
  onDone: () => void
}) {
  const { data: accounts = [] } = useAccounts()
  const { data: categories = [] } = useCategories()
  const addTransaction = useAddTransaction()

  const [amountText, setAmountText] = useState(String(result.total))
  const [note, setNote] = useState(result.merchant)
  const [categoryId, setCategoryId] = useState(result.suggestedCategoryId)
  const [accountId, setAccountId] = useState<string | null>(null)

  const amount = Number(amountText.replace(",", ".")) || 0
  const expenseCategories = categories.filter((c) => c.type === "expense" && c.active)
  const effectiveAccountId =
    accountId ?? accounts.find((a) => a.kind === "debit")?.id ?? accounts[0]?.id
  const canSave = amount > 0 && effectiveAccountId
  const lowConfidence = result.confidence < 0.9

  function save() {
    if (!canSave || !effectiveAccountId) return
    addTransaction.mutate(
      {
        type: "expense",
        amount,
        categoryId,
        accountId: effectiveAccountId,
        date: result.date,
        note: note.trim() || undefined,
      },
      {
        onSuccess: () => {
          navigator.vibrate?.(10)
          onDone()
        },
      },
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <img src={url} alt="" className="size-16 rounded-xl object-cover" />
        <div className="min-w-0 flex-1">
          <p className="truncate text-[15px] font-semibold">{result.merchant}</p>
          <p className="tnum text-[13px] text-muted-foreground">
            {formatMoney(result.total)} detectado
          </p>
        </div>
        {lowConfidence && (
          <span className="flex items-center gap-1 rounded-full bg-expense/10 px-2.5 py-1 text-[11px] font-medium text-expense">
            <TriangleAlert size={12} />
            Revisar
          </span>
        )}
      </div>

      <div className="flex items-baseline justify-center gap-1">
        <span className="text-xl font-semibold text-muted-foreground">$</span>
        <input
          inputMode="decimal"
          value={amountText}
          onChange={(e) => setAmountText(e.target.value.replace(/[^0-9.,]/g, ""))}
          className="tnum w-40 bg-transparent text-center text-4xl font-bold tracking-tight outline-none"
          aria-label="Monto"
        />
      </div>

      <input
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="Comercio"
        className="rounded-xl bg-secondary px-4 py-2.5 text-[15px] outline-none placeholder:text-muted-foreground"
      />

      <div className="grid grid-cols-4 gap-2">
        {expenseCategories.map((c) => {
          const selected = categoryId === c.id
          return (
            <button
              key={c.id}
              onClick={() => setCategoryId(c.id)}
              className="pressable flex flex-col items-center gap-1.5 rounded-2xl py-2"
            >
              <CategoryIcon
                icon={c.icon}
                color={c.color}
                size={22}
                className={`size-12 transition-shadow ${
                  selected ? "ring-2 ring-offset-2 ring-offset-background" : ""
                }`}
                style={{ ["--tw-ring-color" as string]: c.color }}
              />
              <span className="max-w-full truncate text-[11px] font-medium">
                {c.name}
              </span>
            </button>
          )
        })}
      </div>

      <div className="flex gap-2 overflow-x-auto pb-1">
        {accounts.map((a) => (
          <button
            key={a.id}
            onClick={() => setAccountId(a.id)}
            className={`pressable shrink-0 rounded-full px-4 py-1.5 text-[13px] font-medium transition-colors ${
              effectiveAccountId === a.id
                ? "bg-primary text-primary-foreground"
                : "bg-secondary text-secondary-foreground"
            }`}
          >
            {a.name}
          </button>
        ))}
      </div>

      <Button
        size="lg"
        disabled={!canSave}
        onClick={save}
        className="pressable h-12 rounded-2xl text-[16px] font-semibold"
      >
        Guardar gasto
      </Button>
    </div>
  )
}
