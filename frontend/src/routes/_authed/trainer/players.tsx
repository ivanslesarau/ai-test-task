import { createFileRoute } from '@tanstack/react-router'

import { rosterSearchSchema } from '@/entities/trainer-context/model/roster-search'
import { TrainerPlayersPage } from '@/pages/trainer-players'

export const Route = createFileRoute('/_authed/trainer/players')({
  validateSearch: rosterSearchSchema,
  component: TrainerPlayersPage,
})
