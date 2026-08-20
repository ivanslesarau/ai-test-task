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
          onSuccess: () => toast.success('Invitation re-sent'),
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
