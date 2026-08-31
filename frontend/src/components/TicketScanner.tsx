import { useCallback, useEffect, useRef, useState } from "react"
import {
  Camera,
  ChevronRight,
  ImagePlus,
  ScanLine,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
  Upload,
  X,
} from "lucide-react"
import { AnimatePresence, motion } from "motion/react"

import { Button } from "@/components/ui/button"
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerTitle,
  DrawerTrigger,
} from "@/components/ui/drawer"
import { CategoryIcon } from "@/components/CategoryIcon"
import { useAccounts, useAddTransaction, useCategories } from "@/lib/queries"
import { ApiError } from "@/lib/api"
import { parseAmount } from "@/lib/format"
import { analyzeTicket, type TicketScanResult } from "@/lib/scan"
import { springAppear } from "@/lib/springs"

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
            <button className="scanner-banner pressable relative flex min-h-40 w-full items-end overflow-hidden rounded-3xl border border-border bg-card p-5 text-left shadow-sm">
              <span className="scanner-banner-grid" aria-hidden="true" />
              <span className="scanner-banner-ticket" aria-hidden="true">
                <span />
                <span />
                <span />
              </span>
              <span className="relative min-w-0 flex-1 pr-16">
                <span className="mb-2 flex size-10 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-md shadow-primary/25">
                  <ScanLine size={20} />
                </span>
                <span className="block text-[17px] font-semibold tracking-tight">
                  Escanear ticket con IA
                </span>
                <span className="mt-1 block text-[13px] leading-snug text-muted-foreground">
                  Obtén los datos de tu compra en segundos.
                </span>
              </span>
              <span className="relative flex size-9 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
                <Sparkles size={16} />
              </span>
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
      <DrawerContent className="mx-auto max-w-lg bg-card [--drawer-content-height:calc(100dvh-0.75rem)] [--drawer-content-max-height:calc(100dvh-0.75rem)] sm:[--drawer-content-height:min(46rem,calc(100dvh-2rem))] sm:[--drawer-content-max-height:calc(100dvh-2rem)]">
        {open && <ScannerFlow onDone={() => setOpen(false)} />}
      </DrawerContent>
    </Drawer>
  )
}

type Step =
  | { name: "pick" }
  | { name: "camera" }
  | { name: "preview"; file: File; url: string }
  | { name: "analyzing"; url: string }
  | { name: "review"; url: string; result: TicketScanResult }
  | { name: "error"; message: string }

function ScannerFlow({ onDone }: { onDone: () => void }) {
  const [step, setStep] = useState<Step>({ name: "pick" })
  const inputRef = useRef<HTMLInputElement>(null)
  const objectUrlRef = useRef<string | null>(null)

  useEffect(() => {
    return () => {
      if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current)
    }
  }, [])

  const pickFile = useCallback((file: File | undefined) => {
    if (!file || !file.type.startsWith("image/")) return
    if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current)
    const url = URL.createObjectURL(file)
    objectUrlRef.current = url
    setStep({ name: "preview", file, url })
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
    <div className="flex min-h-0 flex-1 flex-col">
      <header className="flex shrink-0 items-center justify-between border-b border-border px-5 py-4">
        <DrawerTitle className="text-[17px] font-semibold tracking-tight">
          {step.name === "review" ? "Resultado" : "Escanear ticket"}
        </DrawerTitle>
        <DrawerClose
          aria-label="Cerrar escáner"
          className="pressable flex size-9 items-center justify-center rounded-full bg-secondary text-secondary-foreground"
        >
          <X size={18} />
        </DrawerClose>
      </header>

      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={step.name}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={springAppear}
          className="flex min-h-0 flex-1 flex-col overflow-y-auto overscroll-contain px-5 py-5"
        >
          {step.name === "pick" && (
            <PickStep
              inputRef={inputRef}
              onCamera={() => setStep({ name: "camera" })}
              onFile={pickFile}
            />
          )}
          {step.name === "camera" && (
            <CameraStep onBack={() => setStep({ name: "pick" })} onCapture={pickFile} />
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
  onCamera,
  onFile,
}: {
  inputRef: React.RefObject<HTMLInputElement | null>
  onCamera: () => void
  onFile: (file: File | undefined) => void
}) {
  const [dragging, setDragging] = useState(false)
  return (
    <div className="flex flex-col gap-4">
      <button
        onClick={onCamera}
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
        className={`scanner-camera pressable relative flex min-h-72 flex-col items-center justify-center overflow-hidden rounded-3xl border-2 border-dashed p-8 transition-colors ${
          dragging ? "border-primary bg-primary/5" : "border-border bg-secondary/35"
        }`}
      >
        <span className="scanner-corner left-4 top-4" />
        <span className="scanner-corner right-4 top-4 rotate-90" />
        <span className="scanner-corner bottom-4 left-4 -rotate-90" />
        <span className="scanner-corner right-4 bottom-4 rotate-180" />
        <span className="relative flex size-14 items-center justify-center rounded-2xl bg-card text-primary shadow-sm">
          <ImagePlus size={25} />
        </span>
        <span className="relative mt-3 text-[16px] font-semibold tracking-tight">
          Abrir cámara
        </span>
        <span className="relative max-w-52 text-[13px] leading-relaxed text-muted-foreground">
          Usa la cámara trasera y centra el comprobante dentro del marco.
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
      <button
        onClick={() => inputRef.current?.click()}
        className="pressable flex min-h-11 items-center justify-center gap-2 rounded-xl text-[14px] font-medium text-primary"
      >
        <Upload size={16} />
        Elegir una imagen
      </button>
      <p className="flex items-center justify-center gap-1.5 text-center text-[11px] leading-relaxed text-muted-foreground">
        <ShieldCheck size={13} className="text-primary" />
        Tus datos se procesan de forma segura.
      </p>
    </div>
  )
}

function CameraStep({
  onBack,
  onCapture,
}: {
  onBack: () => void
  onCapture: (file: File) => void
}) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const [state, setState] = useState<"loading" | "ready" | "error">("loading")

  useEffect(() => {
    let cancelled = false

    async function openCamera() {
      if (!navigator.mediaDevices?.getUserMedia) {
        if (!cancelled) setState("error")
        return
      }

      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: false,
          video: {
            facingMode: { ideal: "environment" },
            width: { ideal: 1920 },
            height: { ideal: 1080 },
          },
        })
        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop())
          return
        }
        streamRef.current = stream
        if (videoRef.current) {
          videoRef.current.srcObject = stream
          await videoRef.current.play()
        }
        if (!cancelled) setState("ready")
      } catch {
        if (!cancelled) setState("error")
      }
    }

    openCamera()
    return () => streamRef.current?.getTracks().forEach((track) => track.stop())
  }, [])

  function capture() {
    const video = videoRef.current
    if (!video || !video.videoWidth || !video.videoHeight) return

    const canvas = document.createElement("canvas")
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const context = canvas.getContext("2d")
    if (!context) return
    context.drawImage(video, 0, 0, canvas.width, canvas.height)
    canvas.toBlob(
      (blob) => {
        if (!blob) return
        onCapture(new File([blob], `ticket-${Date.now()}.jpg`, { type: "image/jpeg" }))
      },
      "image/jpeg",
      0.92,
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="scanner-camera relative aspect-[3/4] overflow-hidden rounded-3xl bg-foreground">
        <video
          ref={videoRef}
          autoPlay
          muted
          playsInline
          className={`h-full w-full object-cover transition-opacity ${
            state === "ready" ? "opacity-100" : "opacity-0"
          }`}
          aria-label="Vista previa de la cámara"
        />
        <div className="pointer-events-none absolute inset-6 rounded-2xl border border-white/30" />
        <span className="scanner-corner left-6 top-6 border-white" />
        <span className="scanner-corner right-6 top-6 rotate-90 border-white" />
        <span className="scanner-corner bottom-6 left-6 -rotate-90 border-white" />
        <span className="scanner-corner right-6 bottom-6 rotate-180 border-white" />
        {state === "loading" && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-center text-white">
            <span className="size-8 animate-spin rounded-full border-2 border-white/30 border-t-white" />
            <p className="text-[14px] font-medium">Abriendo cámara...</p>
          </div>
        )}
        {state === "error" && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 px-8 text-center text-white">
            <TriangleAlert size={28} />
            <p className="text-[15px] font-semibold">No se pudo abrir la cámara</p>
            <p className="text-[13px] leading-relaxed text-white/75">
              Revisa los permisos del navegador o elige una imagen de tu galería.
            </p>
          </div>
        )}
      </div>
      <p className="text-center text-[13px] leading-relaxed text-muted-foreground">
        Alinea los cuatro bordes del ticket dentro del marco.
      </p>
      <div className="flex gap-2">
        <Button variant="secondary" onClick={onBack} className="pressable h-12 flex-1 rounded-xl">
          Cancelar
        </Button>
        <Button
          onClick={capture}
          disabled={state !== "ready"}
          className="pressable h-12 flex-1 rounded-xl"
        >
          <Camera size={17} />
          Capturar
        </Button>
      </div>
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
    <div className="flex min-h-full flex-col gap-4">
      <div className="scanner-preview relative min-h-72 flex-1 overflow-hidden rounded-3xl bg-secondary/50 p-4">
        <img
          src={url}
          alt="Ticket seleccionado"
          className="h-full min-h-64 w-full object-contain"
        />
        <span className="scanner-corner left-5 top-5" />
        <span className="scanner-corner right-5 top-5 rotate-90" />
        <span className="scanner-corner bottom-5 left-5 -rotate-90" />
        <span className="scanner-corner right-5 bottom-5 rotate-180" />
      </div>
      <div className="flex gap-2">
        <Button variant="secondary" onClick={onRetry} className="pressable h-12 flex-1 rounded-xl">
          Elegir otra
        </Button>
        <Button onClick={onAnalyze} className="pressable h-12 flex-1 rounded-xl">
          <Camera size={16} />
          Analizar con IA
        </Button>
      </div>
    </div>
  )
}

function AnalyzingStep({ url }: { url: string }) {
  return (
    <div className="flex min-h-full flex-col items-center gap-5 py-1">
      <div className="scanner-preview relative min-h-72 w-full flex-1 overflow-hidden rounded-3xl bg-secondary/50 p-4">
        <img
          src={url}
          alt=""
          className="h-full min-h-64 w-full object-contain opacity-60"
        />
        {/* Línea de escaneo animada */}
        <motion.div
          className="absolute inset-x-5 h-0.5 rounded-full bg-primary shadow-[0_0_12px_2px] shadow-primary/60"
          animate={{ top: ["8%", "92%", "8%"] }}
          transition={{ duration: 2.2, repeat: Infinity, ease: "easeInOut" }}
        />
      </div>
      <div className="w-full rounded-2xl bg-secondary/65 p-4">
        <p className="text-[15px] font-semibold">Analizando ticket...</p>
        <p className="mt-1 text-[12px] text-muted-foreground">Esto puede tomar unos segundos</p>
        <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-card">
          <motion.div
            className="h-full w-2/5 rounded-full bg-primary"
            animate={{ x: ["-100%", "250%"] }}
            transition={{ duration: 1.2, repeat: Infinity, ease: "easeInOut" }}
          />
        </div>
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
  // Elección explícita del usuario; null = todavía no eligió (usa la sugerencia).
  const [categoryId, setCategoryId] = useState<string | null>(null)
  const [accountId, setAccountId] = useState<string | null>(null)

  const amount = parseAmount(amountText)
  const expenseCategories = categories.filter((c) => c.type === "expense" && c.active)
  // La IA puede sugerir una categoría inexistente o inactiva; solo se
  // pre-selecciona si existe entre las categorías de gasto activas. Se deriva
  // (no se fija en el estado) para que también aplique si las categorías
  // cargan después de montar el paso de revisión.
  const suggestedCategoryId =
    expenseCategories.some((c) => c.id === result.suggestedCategoryId)
      ? result.suggestedCategoryId
      : null
  const effectiveCategoryId = categoryId ?? suggestedCategoryId
  const effectiveAccountId =
    accountId ?? accounts.find((a) => a.kind === "debit")?.id ?? accounts[0]?.id
  const canSave =
    amount !== null && amount > 0 && effectiveCategoryId !== null && effectiveAccountId
  const lowConfidence = result.confidence < 0.9

  function save() {
    if (!canSave || !effectiveAccountId || effectiveCategoryId === null) return
    addTransaction.mutate(
      {
        type: "expense",
        amount,
        categoryId: effectiveCategoryId,
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
      <div className="flex items-center gap-3 rounded-2xl bg-secondary/50 p-3">
        <img src={url} alt="" className="size-16 rounded-xl object-cover" />
        <div className="min-w-0 flex-1">
          <p className="truncate text-[15px] font-semibold">{result.merchant}</p>
          <p className="text-[12px] text-muted-foreground">{formatScanDate(result.date)}</p>
        </div>
        {lowConfidence && (
          <span className="flex items-center gap-1 rounded-full bg-expense/10 px-2.5 py-1 text-[11px] font-medium text-expense">
            <TriangleAlert size={12} />
            Revisar
          </span>
        )}
      </div>

      <div>
        <p className="mb-1 text-[12px] font-medium text-muted-foreground">
          Total detectado
        </p>
        <div className="flex items-baseline gap-1">
          <span className="text-xl font-semibold text-muted-foreground">$</span>
          <input
            inputMode="decimal"
            value={amountText}
            onChange={(e) => setAmountText(e.target.value.replace(/[^0-9.,]/g, ""))}
            className="tnum min-w-0 flex-1 bg-transparent text-3xl font-bold tracking-tight outline-none"
            aria-label="Monto"
          />
        </div>
        {amount === null && (
          <p className="mt-1 flex items-center gap-1.5 text-[11px] font-medium text-expense">
            <TriangleAlert size={13} />
            Escribe un monto válido
          </p>
        )}
        <p
          className={`mt-1 flex items-center gap-1.5 text-[11px] font-medium ${
            lowConfidence ? "text-expense" : "text-income"
          }`}
        >
          <ShieldCheck size={13} />
          {lowConfidence ? "Confianza baja: verifica el monto" : "Confianza alta"}
        </p>
      </div>

      <ReviewSelector label="Categoría sugerida">
        <div className="flex gap-2 overflow-x-auto py-1">
          {expenseCategories.map((c) => {
            const selected = effectiveCategoryId === c.id
            return (
              <button
                key={c.id}
                onClick={() => setCategoryId(c.id)}
                className={`pressable flex shrink-0 items-center gap-2 rounded-xl px-2.5 py-2 text-[13px] font-medium ${
                  selected ? "bg-primary-soft text-primary" : "bg-secondary/60"
                }`}
              >
                <CategoryIcon icon={c.icon} color={c.color} size={17} />
                {c.name}
              </button>
            )
          })}
        </div>
      </ReviewSelector>

      <ReviewSelector label="Cuenta">
        <div className="flex gap-2 overflow-x-auto py-1">
          {accounts.map((a) => (
            <button
              key={a.id}
              onClick={() => setAccountId(a.id)}
              className={`pressable shrink-0 rounded-xl px-3 py-2 text-[13px] font-medium ${
                effectiveAccountId === a.id ? "bg-primary-soft text-primary" : "bg-secondary/60"
              }`}
            >
              {a.name}
            </button>
          ))}
        </div>
      </ReviewSelector>

      <label className="block">
        <span className="mb-1.5 block text-[12px] font-medium text-muted-foreground">
          Nota (opcional)
        </span>
        <input
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Comercio"
          className="h-11 w-full rounded-xl bg-secondary/65 px-3 text-[14px] outline-none placeholder:text-muted-foreground"
        />
      </label>

      <Button
        size="lg"
        disabled={!canSave}
        onClick={save}
        className="pressable h-12 rounded-xl text-[15px] font-semibold"
      >
        Guardar gasto
      </Button>
    </div>
  )
}

function ReviewSelector({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="mb-1.5 text-[12px] font-medium text-muted-foreground">{label}</p>
      <div className="flex items-center rounded-xl bg-secondary/45 px-2">
        <div className="min-w-0 flex-1">{children}</div>
        <ChevronRight size={16} className="shrink-0 text-muted-foreground" />
      </div>
    </div>
  )
}

function formatScanDate(date: string) {
  const value = new Date(`${date}T12:00:00`)
  return Number.isNaN(value.getTime())
    ? date
    : new Intl.DateTimeFormat("es-MX", {
        day: "numeric",
        month: "short",
        year: "numeric",
      }).format(value)
}
