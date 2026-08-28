import { useState } from 'react'

import { useNavigate } from '@tanstack/react-router'
import { toast } from 'sonner'

import { useFamilyProfile } from '@/entities/player-profile/api/use-players'
import { useRemovePlayerProfile } from '@/entities/player-profile/api/use-remove-player'
import { useSession } from '@/entities/session/api/use-session'
import { isChildAccount } from '@/entities/session/model/role-guards'
import { AddTrainerForm } from '@/features/family/add-trainer/ui/add-trainer-form'
import { EditPlayerForm } from '@/features/family/edit-player/ui/edit-player-form'
import { GrantSignInForm } from '@/features/family/grant-sign-in/ui/grant-sign-in-form'
import { RemoveTrainerDialog } from '@/features/family/remove-trainer/ui/remove-trainer-dialog'
import { RevokeSignInDialog } from '@/features/family/revoke-sign-in/ui/revoke-sign-in-dialog'
import { Route as FamilyPlayerRoute } from '@/routes/_authed/family/$profileId'
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
import { BackButton } from '@/shared/ui/back-button'
import { Button } from '@/shared/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/shared/ui/dialog'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/ui/table'

/**
 * `/family/$profileId` (US9, US10, US11; FR-124, FR-128, FR-129, FR-134).
 * One child's trainers, token-spending setting, and sign-in on one view
 * (contracts/frontend-contracts.md §15). A signed-in child viewing their
 * own single reachable profile sees none of the parent-only controls
 * below — the server is the actual barrier (FR-133); this page only
 * avoids offering a control that would be refused anyway.
 */
export function FamilyPlayerPage() {
  const { profileId } = FamilyPlayerRoute.useParams()
  const navigate = useNavigate()
  const { data: session } = useSession()
  const { data: profile, isLoading, isError } = useFamilyProfile(profileId)
  const removeProfile = useRemovePlayerProfile()
  const [removingAssociationId, setRemovingAssociationId] = useState<string | null>(null)
  const [signInDialogOpen, setSignInDialogOpen] = useState(false)

  const isChild = isChildAccount(session)

  if (isLoading) return <p className="p-6 text-muted-foreground">Loading…</p>
  if (isError || !profile) return <p className="p-6 text-destructive">Could not load this player.</p>

  const removingAssociation = profile.associations.find(
    (association) => association.association_id === removingAssociationId,
  )

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 p-6">
      <BackButton fallbackTo="/family" className="self-start" />
      <h1 className="text-section-title">{profile.display_name}</h1>

      {/* FR-132: a signed-in child submits no change to their own
          profile through this form — the server refuses the whole PATCH
          for them (`parent_only_field`), so the control is hidden rather
          than shown and refused. */}
      {!isChild && <EditPlayerForm profile={profile} />}

      {!isChild && (
        <section className="flex flex-col gap-4">
          <h2 className="text-card-title">Trainers</h2>
          {profile.associations.length === 0 ? (
            <p className="text-muted-foreground text-body">No trainers yet.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Trainer</TableHead>
                  <TableHead>Since</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {profile.associations.map((association) => (
                  <TableRow key={association.association_id}>
                    <TableCell>{association.trainer_display_name}</TableCell>
                    <TableCell>{new Date(association.joined_at).toLocaleDateString()}</TableCell>
                    <TableCell>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setRemovingAssociationId(association.association_id)}
                      >
                        Remove
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}

          <AddTrainerForm
            profileId={profile.id}
            existingTrainerIds={profile.associations.map((association) => association.trainer_id)}
          />
        </section>
      )}

      {/* US11: a child's own sign-in (FR-129, FR-130, FR-134). Only for a
          `child` profile — a `self` profile's sign-in is the account
          itself (research.md R-37) — and only for the owning parent. */}
      {!isChild && profile.kind === 'child' && (
        <section className="flex flex-col gap-2">
          <h2 className="text-card-title">Sign-in</h2>
          {profile.has_sign_in ? (
            <RevokeSignInDialog profileId={profile.id} playerDisplayName={profile.display_name} />
          ) : (
            <Dialog open={signInDialogOpen} onOpenChange={setSignInDialogOpen}>
              <DialogTrigger asChild>
                <Button variant="outline" className="self-start">
                  Grant sign-in
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Grant {profile.display_name} their own sign-in</DialogTitle>
                </DialogHeader>
                <GrantSignInForm
                  profileId={profile.id}
                  ownEmail={session?.email ?? ''}
                  onSuccess={() => setSignInDialogOpen(false)}
                />
              </DialogContent>
            </Dialog>
          )}
        </section>
      )}

      {!isChild && profile.kind === 'child' && (
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="destructive" className="self-start">
              Remove player
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Remove {profile.display_name}?</AlertDialogTitle>
              <AlertDialogDescription>
                {profile.display_name} will no longer appear on the family page or on any
                trainer&apos;s roster. Their history is kept.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                disabled={removeProfile.isPending}
                onClick={() => {
                  removeProfile.mutate(profile.id, {
                    onSuccess: () => {
                      toast.success(`${profile.display_name} was removed`)
                      void navigate({ to: '/family' })
                    },
                    onError: () => toast.error('Could not remove this player'),
                  })
                }}
              >
                {removeProfile.isPending ? 'Removing…' : 'Remove player'}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}

      {removingAssociation && (
        <RemoveTrainerDialog
          open
          onOpenChange={(open) => !open && setRemovingAssociationId(null)}
          profileId={profile.id}
          associationId={removingAssociation.association_id}
          playerDisplayName={profile.display_name}
          trainerDisplayName={removingAssociation.trainer_display_name}
        />
      )}
    </div>
  )
}
