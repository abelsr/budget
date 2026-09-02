import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import './index.css'
import App from './App.tsx'
import { ThemeProvider } from '@/lib/theme'
import { AuthProvider } from '@/lib/auth'
import { OfflineProvider } from '@/lib/offline'
import { AuthenticatedQueryCache } from '@/lib/query-cache'
import { ErrorBoundary } from '@/components/ErrorBoundary'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          <AuthenticatedQueryCache>
            <OfflineProvider>
              <ErrorBoundary>
                <App />
              </ErrorBoundary>
            </OfflineProvider>
          </AuthenticatedQueryCache>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  </StrictMode>,
)
