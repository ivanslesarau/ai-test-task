import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { queryClient, AppQueryProvider } from '@/app/providers/query-provider'
import { AppRouterProvider, router } from '@/app/providers/router-provider'
import { sessionKey } from '@/entities/session/api/use-session'
import { apiClient } from '@/shared/api/client'
import { registerInterceptors } from '@/shared/api/interceptors'
import { Toaster } from '@/shared/ui/sonner'

import './app/styles/globals.css'

registerInterceptors(apiClient, () => {
  queryClient.removeQueries({ queryKey: sessionKey })
  void router.navigate({ to: '/login', search: { redirect: window.location.href } })
})

const rootElement = document.getElementById('root')
if (!rootElement) {
  throw new Error('Root element #root not found')
}

createRoot(rootElement).render(
  <StrictMode>
    <AppQueryProvider>
      <AppRouterProvider />
      <Toaster />
    </AppQueryProvider>
  </StrictMode>,
)
