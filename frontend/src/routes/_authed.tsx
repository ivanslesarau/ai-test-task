import { Outlet, createFileRoute, redirect } from '@tanstack/react-router'

import { sessionQueryOptions, useSession } from '@/entities/session/api/use-session'
import { AppShell } from '@/widgets/app-shell/ui/app-shell'
import { BrandingProvider } from '@/widgets/branding-provider/ui/branding-provider'

/**
 * Layout route guarding every authenticated page. This is a rendering
 * decision, not the security boundary — every rule here is re-enforced by
 * the server on each request (FR-015). It exists so an unauthenticated
 * visitor sees a redirect to sign-in instead of a page full of failed
 * requests.
 */
function AuthedLayout() {
  const { data: session } = useSession()

  return (
    <BrandingProvider branding={session?.portal_branding}>
      <AppShell />
      <Outlet />
    </BrandingProvider>
  )
}

export const Route = createFileRoute('/_authed')({
  beforeLoad: async ({ context, location }) => {
    try {
      await context.queryClient.ensureQueryData(sessionQueryOptions)
    } catch {
      throw redirect({
        to: '/login',
        search: { redirect: location.href },
      })
    }
  },
  component: AuthedLayout,
})
