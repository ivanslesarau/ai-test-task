import { useApprovals } from '@/entities/approval/api/use-approvals'
import { Route as ApprovalsRoute } from '@/routes/_authed/approvals'
import { ApprovalDecisionControls } from '@/features/approvals/decide/ui/approval-decision-controls'
import type { ApprovalRequest } from '@/shared/api/types'
import { BackButton } from '@/shared/ui/back-button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/ui/table'

const MINOR_UNIT_DIVISOR = 100

function formatAmount(request: ApprovalRequest): string | null {
  if (request.amount_minor === null || request.currency === null) return null
  return `${(request.amount_minor / MINOR_UNIT_DIVISOR).toFixed(2)} ${request.currency}`
}

/**
 * Derived at render from `expires_at`, never ticked in a store and
 * never treated as authoritative — the server's predicate decides, so a
 * client whose clock says time remains may still receive a 409
 * (contracts/frontend-contracts.md §18, research.md R-41).
 */
function formatTimeRemaining(expiresAt: string): string {
  const remainingMs = new Date(expiresAt).getTime() - Date.now()
  if (remainingMs <= 0) return 'Expired'
  const hours = Math.floor(remainingMs / (60 * 60 * 1000))
  if (hours < 1) return 'Less than an hour left'
  return `${hours}h left`
}

function subjectText(request: ApprovalRequest): string {
  if (request.kind === 'join_trainer') return `Join ${request.trainer_display_name ?? 'a trainer'}`
  if (request.kind === 'token_spend') return 'Spend tokens'
  return 'A payment'
}

/**
 * `/approvals` (US12, FR-149, FR-159). The parent's decision queue —
 * every entry names the child, what is asked, the amount when
 * financial, and the derived time remaining.
 */
export function ApprovalsPage() {
  const search = ApprovalsRoute.useSearch()
  const { data, isLoading, isError } = useApprovals(search)

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6 p-6">
      <BackButton fallbackTo="/" className="self-start" />
      <h1 className="text-section-title">Approvals</h1>

      {isLoading && <p className="text-muted-foreground text-body">Loading…</p>}
      {isError && <p className="text-destructive text-body">Could not load your approvals.</p>}

      {data && data.items.length === 0 && (
        <p className="text-muted-foreground text-body">Nothing is waiting on your decision.</p>
      )}

      {data && data.items.length > 0 && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Child</TableHead>
              <TableHead>Asking to</TableHead>
              <TableHead>Amount</TableHead>
              <TableHead>Time remaining</TableHead>
              <TableHead>Decide</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.items.map((request) => (
              <TableRow key={request.id}>
                <TableCell>{request.player_display_name}</TableCell>
                <TableCell>{subjectText(request)}</TableCell>
                <TableCell>{formatAmount(request) ?? '—'}</TableCell>
                <TableCell>{formatTimeRemaining(request.expires_at)}</TableCell>
                <TableCell>
                  <ApprovalDecisionControls
                    requestId={request.id}
                    childDisplayName={request.player_display_name}
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  )
}
