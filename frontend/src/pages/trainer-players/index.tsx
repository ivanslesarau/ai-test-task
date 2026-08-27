import { Route as TrainerPlayersRoute } from '@/routes/_authed/trainer/players'
import { BackButton } from '@/shared/ui/back-button'
import { TrainerRosterTable } from '@/widgets/trainer-roster-table/ui/trainer-roster-table'

export function TrainerPlayersPage() {
  const search = TrainerPlayersRoute.useSearch()

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6 p-6">
      <BackButton fallbackTo="/" className="self-start" />
      <h1 className="text-section-title">Players</h1>
      <TrainerRosterTable search={search} />
    </div>
  )
}
