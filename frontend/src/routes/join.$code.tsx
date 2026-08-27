import { createFileRoute } from '@tanstack/react-router'

import { JoinPage } from '@/pages/join'

/**
 * Public — sits beside login.tsx at the top level, NOT under `_authed`,
 * which would redirect away the very visitor this page exists to serve
 * (plan.md §Extension). Renders for both a visitor with no session and a
 * signed-in Player/Parent; JoinPage branches on the server-resolved
 * `viewer.state`, never on a local reading of the session.
 */
export const Route = createFileRoute('/join/$code')({
  component: JoinPage,
})
