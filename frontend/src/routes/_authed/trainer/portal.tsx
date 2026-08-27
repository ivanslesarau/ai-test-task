import { createFileRoute } from '@tanstack/react-router'

import { TrainerPortalPage } from '@/pages/trainer-portal'

export const Route = createFileRoute('/_authed/trainer/portal')({
  component: TrainerPortalPage,
})
