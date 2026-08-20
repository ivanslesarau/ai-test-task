import { createFileRoute } from '@tanstack/react-router'

import { UserDetailPage } from '@/pages/admin-users'

export const Route = createFileRoute('/_authed/admin/users/$userId')({
  component: UserDetailPage,
})
