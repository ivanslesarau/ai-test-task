import { createFileRoute } from '@tanstack/react-router'

import { AvailabilityPage } from '@/pages/availability/ui/availability-page'

export const Route = createFileRoute('/_authed/availability')({
  component: AvailabilityPage,
})
