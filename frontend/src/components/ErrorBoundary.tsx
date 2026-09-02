import { Component, type ErrorInfo, type ReactNode } from 'react'
import { Button } from '@/components/ui/button'

interface Props {
  children: ReactNode
}

interface State {
  error: Error | null
}

/**
 * ErrorBoundary global para la PWA: cualquier error de render muestra un
 * fallback con "Recargar" en vez de dejar la pantalla blanca (issue #43).
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // En una PWA no hay consola visible; se loguea para debugging.
    console.error('ErrorBoundary caught', error, info.componentStack)
  }

  render() {
    const { error } = this.state
    if (error === null) {
      return this.props.children
    }
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
        <h1 className="text-lg font-semibold">Algo salió mal</h1>
        <p className="max-w-sm text-sm text-muted-foreground">
          Ocurrió un error inesperado en la app. Puedes reintentar recargando la
          pantalla.
        </p>
        <Button onClick={() => window.location.reload()} className="mt-2">
          Recargar
        </Button>
      </div>
    )
  }
}
