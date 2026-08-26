import { Outlet, createFileRoute, redirect } from '@tanstack/react-router'

import { sessionQueryOptions } from '@/entities/session/api/use-session'
import { AppShell } from '@/widgets/app-shell/ui/app-shell'

/**
 * Layout route guarding every authenticated page. This is a rendering
 * decision, not the security boundary — every rule here is re-enforced by
 * the server on each request (FR-015). It exists so an unauthenticated
 * visitor sees a redirect to sign-in instead of a page full of failed
 * requests.
 */
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
  component: () => (
    <>
      <AppShell />
      <Outlet />
    </>
  ),
})
