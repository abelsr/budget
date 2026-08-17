import { AnimatePresence, MotionConfig, motion } from "motion/react"
import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react"

import { Button } from "@/components/ui/button"

export interface SnackbarOptions {
  message: string
  action?: { label: string; onClick: () => void }
}

type ShowSnackbar = (options: SnackbarOptions) => void

const SnackbarContext = createContext<ShowSnackbar>(() => {})

const AUTO_DISMISS_MS = 8000

export function SnackbarProvider({ children }: { children: ReactNode }) {
  const [snackbar, setSnackbar] = useState<{ key: number } & SnackbarOptions | null>(null)
  const timer = useRef<number | null>(null)

  const dismiss = useCallback(() => {
    if (timer.current !== null) {
      window.clearTimeout(timer.current)
      timer.current = null
    }
    setSnackbar(null)
  }, [])

  const show = useCallback<ShowSnackbar>(
    (options) => {
      dismiss()
      setSnackbar({ key: Date.now(), ...options })
      timer.current = window.setTimeout(dismiss, AUTO_DISMISS_MS)
    },
    [dismiss],
  )

  useEffect(() => dismiss, [dismiss])

  return (
    <SnackbarContext.Provider value={show}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 bottom-24 z-50 flex justify-center px-4 md:bottom-8">
        <AnimatePresence initial={false}>
          {snackbar && (
            <MotionConfig reducedMotion="user">
              <motion.div
                key={snackbar.key}
                role="status"
                aria-live="polite"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 12 }}
                transition={{ duration: 0.18 }}
                className="pointer-events-auto flex items-center gap-3 rounded-xl bg-foreground py-2.5 pr-2.5 pl-4 text-background shadow-lg"
              >
                <p className="text-sm font-medium">{snackbar.message}</p>
                {snackbar.action && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-background hover:bg-background/15 hover:text-background"
                    onClick={() => {
                      dismiss()
                      snackbar.action?.onClick()
                    }}
                  >
                    {snackbar.action.label}
                  </Button>
                )}
              </motion.div>
            </MotionConfig>
          )}
        </AnimatePresence>
      </div>
    </SnackbarContext.Provider>
  )
}

export function useSnackbar() {
  return useContext(SnackbarContext)
}
