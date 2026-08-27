import { Outlet, createFileRoute } from '@tanstack/react-router'

import { useSession } from '@/entities/session/api/use-session'
import { isTrainer } from '@/entities/session/model/role-guards'

function TrainerGate() {
  const { data: user } = useSession()

  if (!isTrainer(user)) {
    return (
      <div className="flex min-h-[50vh] flex-col items-center justify-center gap-2 text-center">
        <h1 className="text-block-title">You don&apos;t have access to this page</h1>
        <p className="text-muted-foreground text-body">This area is restricted to Trainers.</p>
      </div>
    )
  }

  return <Outlet />
}

export const Route = createFileRoute('/_authed/trainer')({
  component: TrainerGate,
})
