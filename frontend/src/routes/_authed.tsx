import { useEffect } from 'react'

import { Outlet, createFileRoute, redirect } from '@tanstack/react-router'
import { toast } from 'sonner'

import { useImpersonationNoticeStore } from '@/app/store/impersonation-notice-slice'
import { sessionQueryOptions, useSession } from '@/entities/session/api/use-session'
import { AppShell } from '@/widgets/app-shell/ui/app-shell'
import { BrandingProvider } from '@/widgets/branding-provider/ui/branding-provider'
import { ImpersonationBanner } from '@/widgets/impersonation-banner/ui/impersonation-banner'

const END_REASON_LABEL: Record<string, string> = {
  timed_out: 'The impersonation ended after reaching its one-hour limit.',
  signed_out: 'The impersonation ended because you signed out.',
  superseded: 'That impersonation ended when you started a new one.',
  target_deactivated: 'The impersonation ended because the account was deactivated.',
  target_erased: 'The impersonation ended because the account was erased.',
  admin_deactivated: 'The impersonation ended because your account was deactivated.',
}

/**
 * `session.impersonation_ended`, shown once per impersonation id
 * (research.md R2-20, frontend-contracts.md §35). `exited` never appears
 * here — the admin who clicked Exit does not need telling they clicked
 * Exit, and the server excludes it from the derived field entirely.
 */
function useImpersonationEndedToast(): void {
  const { data: session } = useSession()
  const hasBeenShown = useImpersonationNoticeStore((state) => state.hasBeenShown)
  const markShown = useImpersonationNoticeStore((state) => state.markShown)
  const ended = session?.impersonation_ended ?? null

  useEffect(() => {
    if (!ended || hasBeenShown(ended.id)) return
    const label = ended.end_reason ? END_REASON_LABEL[ended.end_reason] : undefined
    toast.info(label ?? 'Your impersonation session ended.')
    markShown(ended.id)
  }, [ended, hasBeenShown, markShown])
}

/**
 * Layout route guarding every authenticated page. This is a rendering
 * decision, not the security boundary — every rule here is re-enforced by
 * the server on each request (FR-015). It exists so an unauthenticated
 * visitor sees a redirect to sign-in instead of a page full of failed
 * requests.
 */
function AuthedLayout() {
  const { data: session } = useSession()
  useImpersonationEndedToast()

  return (
    <BrandingProvider branding={session?.portal_branding}>
      <ImpersonationBanner />
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
