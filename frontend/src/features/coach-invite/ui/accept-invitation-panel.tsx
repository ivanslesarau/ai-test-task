import { useAcceptCoachInvitation } from '@/entities/coach-invitation/api/use-accept-coach-invitation'
import { isApiError } from '@/shared/api/errors'
import type { CoachJoinResult, CurrentUser } from '@/shared/api/types'
import { Button } from '@/shared/ui/button'

interface AcceptInvitationPanelProps {
  token: string
  currentUser: CurrentUser
  trainerBusinessName: string
  onJoined: (result: CoachJoinResult) => void
}

/**
 * The signed-in path (FR-012 – FR-019). Renders each of the four server
 * outcomes with the server's own message and no hint of another trainer
 * (SC-003) — this component never composes its own copy for a refusal,
 * only relays what `POST .../accept` returned.
 */
export function AcceptInvitationPanel({
  token,
  currentUser,
  trainerBusinessName,
  onJoined,
}: AcceptInvitationPanelProps) {
  const accept = useAcceptCoachInvitation(token)

  if (accept.isSuccess) {
    const result = accept.data
    return (
      <div className="flex flex-col gap-2">
        <p className="text-body">
          {result.outcome === 'already_on_this_roster'
            ? `You are already on ${result.trainer_business_name}'s roster.`
            : `You have joined ${result.trainer_business_name}.`}
        </p>
        <Button variant="outline" onClick={() => onJoined(result)}>
          Continue
        </Button>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      <p className="text-body">
        Signed in as <strong>{currentUser.email}</strong>.
      </p>
      {accept.isError && (
        <p className="text-destructive text-body" role="alert">
          {isApiError(accept.error) ? accept.error.message : 'Something went wrong. Try again.'}
        </p>
      )}
      <Button
        className="bg-brand-primary hover:bg-brand-primary-deep"
        onClick={() => accept.mutate()}
        disabled={accept.isPending}
      >
        {accept.isPending ? 'Joining…' : `Join ${trainerBusinessName}`}
      </Button>
    </div>
  )
}
