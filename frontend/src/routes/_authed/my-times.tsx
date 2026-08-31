import { createFileRoute } from '@tanstack/react-router'

import { useSession } from '@/entities/session/api/use-session'
import { isCoach } from '@/entities/session/model/role-guards'
import { MyTimesPage } from '@/pages/my-times/ui/my-times-page'

function MyTimesGate() {
  const { data: user } = useSession()

  if (!isCoach(user)) {
    return (
      <div className="flex min-h-[50vh] flex-col items-center justify-center gap-2 text-center">
        <h1 className="text-block-title">You don&apos;t have access to this page</h1>
        <p className="text-muted-foreground text-body">This area is restricted to Coaches.</p>
      </div>
    )
  }

  return <MyTimesPage />
}

export const Route = createFileRoute('/_authed/my-times')({
  component: MyTimesGate,
})
