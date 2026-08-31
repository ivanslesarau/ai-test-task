import { CoachInvitationList } from '@/features/trainer/coach-invitations/ui/coach-invitation-list'
import { InviteCoachForm } from '@/features/trainer/coach-invitations/ui/invite-coach-form'
import { CoachRosterTable } from '@/features/trainer/coaches/ui/coach-roster-table'
import { BackButton } from '@/shared/ui/back-button'

/**
 * `/trainer/coaches` (US1 + US2, FR-001 – FR-010, FR-020 – FR-023). The
 * roster — coaches already on this trainer's team — plus the invite form
 * and the invitation list.
 */
export function TrainerCoachesPage() {
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-8 p-6">
      <BackButton fallbackTo="/" className="self-start" />
      <h1 className="text-section-title">Coaches</h1>

      <section className="flex flex-col gap-4">
        <h2 className="text-block-title">Your coaches</h2>
        <CoachRosterTable />
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-block-title">Invite a coach</h2>
        <InviteCoachForm />
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="text-block-title">Invitations</h2>
        <CoachInvitationList />
      </section>
    </div>
  )
}
