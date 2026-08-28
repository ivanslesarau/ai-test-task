import type { PlayerProfile } from '@/shared/api/types'
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

interface DuplicateDialogProps {
  matches: PlayerProfile[]
  onConfirm: () => void
  onCancel: () => void
  isConfirming: boolean
}

/**
 * The 409 duplicate warning (FR-110, research.md R-45), rendered from the
 * mutation's own error state — never copied into a store
 * (contracts/frontend-contracts.md §18). Confirming resubmits the same
 * form values with `acknowledge_possible_duplicate: true`; twins and a
 * child named for a relative are ordinary, so the warning is overrulable.
 */
export function DuplicateProfileDialog({
  matches,
  onConfirm,
  onCancel,
  isConfirming,
}: DuplicateDialogProps) {
  return (
    <AlertDialog open onOpenChange={(open) => !open && onCancel()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>A similar player already exists</AlertDialogTitle>
          <AlertDialogDescription>
            This account already has {matches.length === 1 ? 'a player' : 'players'} with the same
            name and date of birth:{' '}
            {matches.map((match) => match.display_name).join(', ')}. If this is a different
            child — twins, or named for a relative — add them anyway.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={onCancel}>Go back</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm} disabled={isConfirming}>
            {isConfirming ? 'Adding…' : 'Add anyway'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
