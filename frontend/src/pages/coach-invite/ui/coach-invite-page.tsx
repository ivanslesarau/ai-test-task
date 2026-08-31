import { useCoachInvitationPreview } from '@/entities/coach-invitation/api/use-coach-invitation-preview'
import { CoachInvitePreview } from '@/features/coach-invite/ui/coach-invite-preview'
import { Route as CoachInviteRoute } from '@/routes/coach-invite.$token'
import { isApiError } from '@/shared/api/errors'
import { BrandingProvider } from '@/widgets/branding-provider/ui/branding-provider'

/**
 * `/coach-invite/$token` — public, unauthenticated (FR-011 – FR-014).
 * The public sibling of `/join/$code`: every refusal — unknown, spent,
 * revoked, superseded, expired, or an inviting trainer no longer Active
 * — is one `invitation_link_invalid` 404, rendered as the single message
 * below, disclosing which condition applied to nobody.
 */
export function CoachInvitePage() {
  const { token } = CoachInviteRoute.useParams()
  const preview = useCoachInvitationPreview(token)

  if (preview.isLoading) {
    return (
      <div className="mx-auto flex min-h-screen max-w-sm flex-col justify-center gap-4 p-4">
        <p className="text-muted-foreground">Checking your invitation…</p>
      </div>
    )
  }

  if (preview.isError) {
    const isNotFound = isApiError(preview.error) && preview.error.status === 404
    return (
      <div className="mx-auto flex min-h-screen max-w-sm flex-col justify-center gap-4 p-4">
        <h1 className="text-hero-title">This link is no longer valid</h1>
        <p className="text-muted-foreground text-body">
          {isNotFound
            ? 'Ask whoever sent it for a fresh link.'
            : 'Something went wrong. Try again shortly.'}
        </p>
      </div>
    )
  }

  if (!preview.data) return null

  return (
    <BrandingProvider branding={preview.data.trainer.portal_branding}>
      <div className="mx-auto flex min-h-screen max-w-sm flex-col justify-center gap-6 p-4">
        <CoachInvitePreview token={token} preview={preview.data} />
      </div>
    </BrandingProvider>
  )
}
