import { Link, useNavigate } from '@tanstack/react-router'

import { useSession } from '@/entities/session/api/use-session'
import { AcceptInvitationPanel } from '@/features/coach-invite/ui/accept-invitation-panel'
import { CoachRegistrationForm } from '@/features/coach-invite/ui/coach-registration-form'
import { resolveMediaUrl } from '@/shared/api/media'
import type { CoachInvitationPreview as CoachInvitationPreviewData } from '@/shared/api/types'
import { Button } from '@/shared/ui/button'

interface CoachInvitePreviewProps {
  token: string
  preview: CoachInvitationPreviewData
}

/**
 * The trainer's identity and brand, the invited address, the message,
 * the expiry, and the register-or-sign-in branch driven by
 * `account_exists` (FR-011 – FR-014). A signed-in visitor always sees
 * `AcceptInvitationPanel` instead — the session, not `account_exists`,
 * decides that branch (a visitor may hold a session for a *different*
 * account than the invited address; the server's own address-mismatch
 * refusal is what handles that, never a client-side guess).
 */
export function CoachInvitePreview({ token, preview }: CoachInvitePreviewProps) {
  const { data: currentUser } = useSession()
  const navigate = useNavigate()
  const logoUrl = resolveMediaUrl(preview.trainer.portal_branding.logo_url)

  function goHome() {
    void navigate({ to: '/' })
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-3">
        {logoUrl && (
          // <img> only — never <object>, <embed>, or inline SVG.
          <img
            src={logoUrl}
            alt={`${preview.trainer.business_name} logo`}
            className="h-16 w-16 object-contain"
          />
        )}
        <h1 className="text-hero-title">Join {preview.trainer.business_name}</h1>
        <p className="text-muted-foreground text-body">
          Invitation for <strong>{preview.invited_email}</strong>
          {preview.invitee_name ? ` (${preview.invitee_name})` : ''}
        </p>
        {preview.message && <p className="text-body">{preview.message}</p>}
        <p className="text-caption text-muted-foreground">
          Expires {new Date(preview.expires_at).toLocaleDateString()}
        </p>
      </div>

      {currentUser ? (
        <AcceptInvitationPanel
          token={token}
          currentUser={currentUser}
          trainerBusinessName={preview.trainer.business_name}
          onJoined={goHome}
        />
      ) : preview.account_exists ? (
        <div className="flex flex-col gap-2">
          <p className="text-body">
            An account already exists for {preview.invited_email}. Sign in to accept.
          </p>
          <Button asChild className="bg-brand-primary hover:bg-brand-primary-deep">
            <Link to="/login">Sign in</Link>
          </Button>
        </div>
      ) : (
        <CoachRegistrationForm
          token={token}
          invitedEmail={preview.invited_email}
          onSuccess={goHome}
        />
      )}
    </div>
  )
}
