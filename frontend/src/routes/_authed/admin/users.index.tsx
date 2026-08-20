import { createFileRoute } from '@tanstack/react-router'

import { directorySearchSchema } from '@/entities/user/model/directory-search'
import { UsersIndexPage } from '@/pages/admin-users'

export const Route = createFileRoute('/_authed/admin/users/')({
  validateSearch: directorySearchSchema,
  component: UsersIndexPage,
})
