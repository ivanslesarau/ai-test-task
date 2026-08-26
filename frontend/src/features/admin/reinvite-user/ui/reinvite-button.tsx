import { toast } from 'sonner'

import { useReinviteUser } from '@/entities/user/api/use-users'
import { isApiError } from '@/shared/api/errors'
import { Button } from '@/shared/ui/button'

export function ReinviteButton({ userId }: { userId: string }) {
  const reinvite = useReinviteUser()

  return (
    <Button
      variant="outline"
      size="sm"
      disabled={reinvite.isPending}
      onClick={() =>
        reinvite.mutate(userId, {
          onSuccess: (result) => {
            // A 2xx response only means the request succeeded — it does
            // not mean delivery did. `invitation_sent: false` was
            // previously ignored here, so a delivery failure read as
            // success and the Super Admin never retried (F6).
            if (result.invitation_sent) {
              toast.success('Invitation re-sent')
            } else {
              toast.error(
                'The account was updated, but the invitation email could not be sent. Try again shortly.',
              )
            }
          },
          onError: (error) => {
            toast.error(isApiError(error) ? error.message : 'Could not re-send the invitation')
          },
        })
      }
    >
      {reinvite.isPending ? 'Sending…' : 'Re-invite'}
    </Button>
  )
}
