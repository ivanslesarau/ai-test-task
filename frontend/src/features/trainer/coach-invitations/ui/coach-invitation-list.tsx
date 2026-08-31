import { toast } from 'sonner'

import { useCoachInvitations } from '@/entities/coach-invitation/api/use-coach-invitations'
import { useResendCoachInvitation } from '@/entities/coach-invitation/api/use-resend-coach-invitation'
import { useRevokeCoachInvitation } from '@/entities/coach-invitation/api/use-revoke-coach-invitation'
import { COACH_INVITATION_STATE_LABELS } from '@/entities/coach-invitation/model/invitation'
import { isApiError } from '@/shared/api/errors'
import type { CoachInvitationPresentedState } from '@/shared/api/types'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'

const STATE_BADGE_VARIANT: Record<
  CoachInvitationPresentedState,
  'default' | 'secondary' | 'destructive' | 'outline'
> = {
  awaiting: 'secondary',
  accepted: 'default',
  expired: 'outline',
  revoked: 'destructive',
  blocked: 'destructive',
}

/** Every state this endpoint can present, whether or not it may be
 * resent or revoked (data-model.md §101.1's precedence): `awaiting` and
 * `blocked` permit both; `expired` permits only resend; `accepted` and
 * `revoked` permit neither. */
function canResend(state: CoachInvitationPresentedState): boolean {
  return state === 'awaiting' || state === 'blocked' || state === 'expired'
}

function canRevoke(state: CoachInvitationPresentedState): boolean {
  return state === 'awaiting' || state === 'blocked'
}

/**
 * `GET /trainer/coach-invitations` (FR-004) — one row per invitation with
 * its address, presented-state badge, expiry, and the resend/revoke
 * actions that state permits. `superseded` rows never appear — the server
 * already excludes them (FR-005), so this list has nothing to filter.
 */
export function CoachInvitationList() {
  const { data, isLoading } = useCoachInvitations({ page: 1, page_size: 25 })
  const resendInvitation = useResendCoachInvitation()
  const revokeInvitation = useRevokeCoachInvitation()

  if (isLoading || !data) {
    return <p className="text-muted-foreground text-body">Loading invitations…</p>
  }

  if (data.items.length === 0) {
    return <p className="text-muted-foreground text-body">No invitations yet.</p>
  }

  return (
    <ul className="flex flex-col gap-3">
      {data.items.map((invitation) => (
        <li
          key={invitation.id}
          className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-input p-3"
        >
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <span className="text-body">{invitation.invited_email}</span>
              <Badge variant={STATE_BADGE_VARIANT[invitation.state]}>
                {COACH_INVITATION_STATE_LABELS[invitation.state]}
              </Badge>
            </div>
            <p className="text-muted-foreground text-caption">
              Expires {new Date(invitation.expires_at).toLocaleDateString()}
            </p>
          </div>

          <div className="flex items-center gap-2">
            {canResend(invitation.state) && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={resendInvitation.isPending}
                onClick={() => {
                  resendInvitation.mutate(invitation.id, {
                    onSuccess: () => toast.success('Invitation resent.'),
                    onError: (error) => {
                      toast.error(isApiError(error) ? error.message : 'Could not resend.')
                    },
                  })
                }}
              >
                Resend
              </Button>
            )}
            {canRevoke(invitation.state) && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={revokeInvitation.isPending}
                onClick={() => {
                  revokeInvitation.mutate(invitation.id, {
                    onSuccess: () => toast.success('Invitation revoked.'),
                    onError: (error) => {
                      toast.error(isApiError(error) ? error.message : 'Could not revoke.')
                    },
                  })
                }}
              >
                Revoke
              </Button>
            )}
          </div>
        </li>
      ))}
    </ul>
  )
}
