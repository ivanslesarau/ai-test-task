import { createFileRoute } from '@tanstack/react-router'

import { FamilyPage } from '@/pages/family'

export const Route = createFileRoute('/_authed/family/')({
  component: FamilyPage,
})
