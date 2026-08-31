import { createFileRoute } from '@tanstack/react-router'

import { impersonationHistorySearchSchema } from '@/entities/impersonation/model/history-search'
import { AdminImpersonationsPage } from '@/pages/admin-impersonations/ui/admin-impersonations-page'

export const Route = createFileRoute('/_authed/admin/impersonations')({
  validateSearch: impersonationHistorySearchSchema,
  component: AdminImpersonationsPage,
})
