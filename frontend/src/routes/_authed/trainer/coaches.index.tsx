import { createFileRoute } from '@tanstack/react-router'

import { TrainerCoachesPage } from '@/pages/trainer-coaches/ui/trainer-coaches-page'

export const Route = createFileRoute('/_authed/trainer/coaches/')({
  component: TrainerCoachesPage,
})
