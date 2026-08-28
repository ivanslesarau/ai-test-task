import { toast } from 'sonner'

import { useRevokeChildSignIn } from '@/entities/player-profile/api/use-child-signin'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/shared/ui/alert-dialog'
import { Button } from '@/shared/ui/button'

interface RevokeSignInDialogProps {
  profileId: string
  playerDisplayName: string
}

/**
 * `DELETE /me/players/{profile_id}/sign-in` (US11, FR-134). Ends every
 * session that account holds; the profile, its trainers, and its history
 * are untouched (stated here so the confirmation is accurate, not just
 * reassuring).
 */
export function RevokeSignInDialog({ profileId, playerDisplayName }: RevokeSignInDialogProps) {
  const revokeSignIn = useRevokeChildSignIn()

  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant="outline" className="self-start">
          Revoke sign-in
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Revoke {playerDisplayName}&apos;s sign-in?</AlertDialogTitle>
          <AlertDialogDescription>
            {playerDisplayName} will no longer be able to sign in, and any session they currently
            hold stops working immediately. Their profile, trainers, and history are kept.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            disabled={revokeSignIn.isPending}
            onClick={() => {
              revokeSignIn.mutate(profileId, {
                onSuccess: () => toast.success(`${playerDisplayName}'s sign-in was revoked`),
                onError: () => toast.error("Could not revoke this child's sign-in"),
              })
            }}
          >
            {revokeSignIn.isPending ? 'Revoking…' : 'Revoke sign-in'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
