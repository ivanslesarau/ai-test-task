import { toast } from 'sonner'

import { useRemovePlayerTrainer } from '@/entities/player-profile/api/use-player-trainers'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/shared/ui/alert-dialog'

interface RemoveTrainerDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  profileId: string
  associationId: string
  playerDisplayName: string
  trainerDisplayName: string
}

/**
 * `DELETE /me/players/{profile_id}/trainers/{association_id}` (US10,
 * FR-126). Names the player and the trainer and states the reservation
 * consequence before confirming — required now; the cancellation itself
 * belongs to Epic-02.
 */
export function RemoveTrainerDialog({
  open,
  onOpenChange,
  profileId,
  associationId,
  playerDisplayName,
  trainerDisplayName,
}: RemoveTrainerDialogProps) {
  const removeTrainer = useRemovePlayerTrainer()

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Remove {trainerDisplayName}?</AlertDialogTitle>
          <AlertDialogDescription>
            {playerDisplayName} will no longer train with {trainerDisplayName}. Any upcoming
            reservations with this trainer will be cancelled. Their history together is kept.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            disabled={removeTrainer.isPending}
            onClick={() => {
              removeTrainer.mutate(
                { profileId, associationId },
                {
                  onSuccess: () => {
                    toast.success(`${trainerDisplayName} removed`)
                    onOpenChange(false)
                  },
                  onError: () => {
                    toast.error('Could not remove this trainer')
                  },
                },
              )
            }}
          >
            {removeTrainer.isPending ? 'Removing…' : 'Remove trainer'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
