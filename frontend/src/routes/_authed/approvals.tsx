import { createFileRoute } from '@tanstack/react-router'

import { approvalSearchSchema } from '@/entities/approval/model/approval-search'
import { ApprovalsPage } from '@/pages/approvals'

export const Route = createFileRoute('/_authed/approvals')({
  validateSearch: approvalSearchSchema,
  component: ApprovalsPage,
})
