import { createFileRoute } from '@tanstack/react-router'

import { approvalSearchSchema } from '@/entities/approval/model/approval-search'
import { RequestsPage } from '@/pages/requests'

export const Route = createFileRoute('/_authed/requests')({
  validateSearch: approvalSearchSchema,
  component: RequestsPage,
})
