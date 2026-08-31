import { createFileRoute } from '@tanstack/react-router'

import { CoachDetailPage } from '@/pages/coach-detail/ui/coach-detail-page'

export const Route = createFileRoute('/_authed/trainer/coaches/$coachUserId')({
  component: CoachDetailPage,
})
