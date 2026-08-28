import { useState } from 'react'

import { toast } from 'sonner'

import { useFamilyProfiles } from '@/entities/player-profile/api/use-players'
import { useSession } from '@/entities/session/api/use-session'
import { isChildAccount } from '@/entities/session/model/role-guards'
import { AddChildForm } from '@/features/family/add-child/ui/add-child-form'
import { BackButton } from '@/shared/ui/back-button'
import { Button } from '@/shared/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/shared/ui/dialog'
import { FamilyRosterList } from '@/widgets/family-roster-list/ui/family-roster-list'

/**
 * `/family` (US9, FR-106, FR-124). The account holder's own profile,
 * when they train, alongside every child. A signed-in child sees only
 * their own single profile — the scoping is server-side (FR-132), so
 * this page renders whatever `GET /me/players` returns without asking
 * "am I a child" itself.
 */
export function FamilyPage() {
  const { data: session } = useSession()
  const { data, isLoading, isError } = useFamilyProfiles()
  const [dialogOpen, setDialogOpen] = useState(false)

  const isChild = isChildAccount(session)

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6 p-6">
      <BackButton fallbackTo="/" className="self-start" />
      <div className="flex items-center justify-between">
        <h1 className="text-section-title">Family</h1>
        {!isChild && (
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button>Add child</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add a child</DialogTitle>
              </DialogHeader>
              <AddChildForm
                onSuccess={(profile) => {
                  setDialogOpen(false)
                  toast.success(`${profile.display_name} was added`)
                }}
              />
            </DialogContent>
          </Dialog>
        )}
      </div>

      {isLoading && <p className="text-muted-foreground text-body">Loading…</p>}
      {isError && <p className="text-destructive text-body">Could not load your family.</p>}
      {data && <FamilyRosterList profiles={data.profiles} />}
    </div>
  )
}
