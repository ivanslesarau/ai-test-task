import { createFileRoute } from '@tanstack/react-router'

import { FamilyPlayerPage } from '@/pages/family-player'

export const Route = createFileRoute('/_authed/family/$profileId')({
  component: FamilyPlayerPage,
})
