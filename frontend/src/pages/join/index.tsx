import { useNavigate } from '@tanstack/react-router'

import { useJoinPreview } from '@/entities/join/api/use-join-preview'
import { useAcceptJoinLink } from '@/features/join/accept/api/use-accept'
import { JoinRegisterForm } from '@/features/join/register/ui/join-register-form'
import { Route as JoinRoute } from '@/routes/join.$code'
import { isApiError } from '@/shared/api/errors'
import { resolveMediaUrl } from '@/shared/api/media'
import { Button } from '@/shared/ui/button'
import { BrandingProvider } from '@/widgets/branding-provider/ui/branding-provider'

export function JoinPage() {
  const { code } = JoinRoute.useParams()
  const navigate = useNavigate()
  const preview = useJoinPreview(code)
  const accept = useAcceptJoinLink(code)

  function goHome() {
    void navigate({ to: '/' })
  }

  if (preview.isLoading) {
    return (
      <div className="mx-auto flex min-h-screen max-w-sm flex-col justify-center gap-4 p-4">
        <p className="text-muted-foreground">Checking your invitation…</p>
      </div>
    )
  }

  if (preview.isError) {
    // FR-070: one message for every refusal cause — the response itself
    // discloses nothing about which condition applied, and neither does
    // this page.
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

  const { trainer_display_name: trainerName, branding, viewer } = preview.data
  const logoUrl = resolveMediaUrl(branding.logo_url)

  return (
    // Branding comes from this response, not the session — a visitor
    // here has none yet (FR-073: the join page is branded before anyone
    // has an account).
    <BrandingProvider branding={branding}>
      <div className="mx-auto flex min-h-screen max-w-sm flex-col justify-center gap-6 p-4">
        <div className="flex flex-col gap-3">
          {logoUrl && (
            // <img> only — never <object>, <embed>, or inline SVG
            // (research.md R-27's last, most durable layer of defence).
            <img src={logoUrl} alt={`${trainerName} logo`} className="h-16 w-16 object-contain" />
          )}
          <h1 className="text-hero-title">Join {trainerName}</h1>
          <p className="text-muted-foreground text-body">
            {viewer.state === 'anonymous' &&
              'Create an account to see their events and content.'}
            {viewer.state === 'can_join' && `Connect your account with ${trainerName}.`}
          </p>
        </div>

        {viewer.state === 'anonymous' && (
          <JoinRegisterForm code={code} onSuccess={goHome} />
        )}

        {viewer.state === 'can_join' && (
          <Button
            className="bg-brand-primary hover:bg-brand-primary-deep"
            onClick={() => accept.mutate(undefined, { onSuccess: goHome })}
            disabled={accept.isPending}
          >
            {accept.isPending ? 'Joining…' : `Join ${trainerName}`}
          </Button>
        )}

        {viewer.state === 'already_associated' && (
          <div className="flex flex-col gap-2">
            <p className="text-body">You already train with {trainerName}.</p>
            <Button variant="outline" onClick={goHome}>
              Go to {trainerName}
            </Button>
          </div>
        )}

        {viewer.state === 'role_cannot_join' && (
          <p className="text-body">This link is for players and parents.</p>
        )}
      </div>
    </BrandingProvider>
  )
}
