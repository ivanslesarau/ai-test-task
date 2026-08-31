import { createFileRoute } from '@tanstack/react-router'

import { CoachInvitePage } from '@/pages/coach-invite/ui/coach-invite-page'

/**
 * Public — sits beside join.$code.tsx at the top level, NOT under
 * `_authed`, which would redirect away the very visitor this page exists
 * to serve (frontend-contracts.md §30). Renders for both a visitor with
 * no session and a signed-in Coach; `CoachInvitePage` branches on the
 * server-resolved preview and the caller's own session, never on a
 * locally-guessed state.
 */
export const Route = createFileRoute('/coach-invite/$token')({
  component: CoachInvitePage,
})
