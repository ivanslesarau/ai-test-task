import { useState } from 'react'

import { toast } from 'sonner'

import { useRaisedRequests } from '@/entities/approval/api/use-raised-requests'
import { useRespondToRequest } from '@/entities/approval/api/use-respond-to-request'
import { useWithdrawRequest } from '@/entities/approval/api/use-withdraw-request'
import { Route as RequestsRoute } from '@/routes/_authed/requests'
import { isApiError } from '@/shared/api/errors'
import type { ApprovalRequest } from '@/shared/api/types'
import { BackButton } from '@/shared/ui/back-button'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/shared/ui/dialog'
import { Input } from '@/shared/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/ui/table'

function subjectText(request: ApprovalRequest): string {
  if (request.kind === 'join_trainer') return `Join ${request.trainer_display_name ?? 'a trainer'}`
  if (request.kind === 'token_spend') return 'Spend tokens'
  return 'A payment'
}

const STATUS_LABELS: Record<ApprovalRequest['status'], string> = {
  pending_parent_approval: 'Waiting for a decision',
  info_requested: 'Your parent asked a question',
  approved: 'Approved',
  denied: 'Denied',
  expired: 'Expired',
  withdrawn: 'Withdrawn',
}

/**
 * `/requests` (US12, FR-131, FR-153). A child's own view of what they
 * asked for — every status, the parent's note on a denial or an
 * information request, and a control to withdraw a pending one.
 */
export function RequestsPage() {
  const search = RequestsRoute.useSearch()
  const { data, isLoading, isError } = useRaisedRequests(search)
  const withdraw = useWithdrawRequest()
  const respond = useRespondToRequest()
  const [replyingTo, setReplyingTo] = useState<string | null>(null)
  const [replyNote, setReplyNote] = useState('')

  function handleWithdraw(requestId: string) {
    withdraw.mutate(requestId, {
      onSuccess: () => toast.success('Withdrawn'),
      onError: (error) => {
        if (isApiError(error) && error.code === 'request_already_resolved') {
          toast.info('That request was already decided.')
          return
        }
        toast.error(isApiError(error) ? error.message : 'Could not withdraw this request')
      },
    })
  }

  function handleRespond() {
    if (!replyingTo || !replyNote.trim()) return
    respond.mutate(
      { requestId: replyingTo, note: replyNote.trim() },
      {
        onSuccess: () => {
          toast.success('Sent')
          setReplyingTo(null)
          setReplyNote('')
        },
        onError: (error) => {
          if (isApiError(error) && error.code === 'request_already_resolved') {
            toast.info('That request was already decided.')
            setReplyingTo(null)
            return
          }
          toast.error(isApiError(error) ? error.message : 'Could not send that reply')
        },
      },
    )
  }

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6 p-6">
      <BackButton fallbackTo="/" className="self-start" />
      <h1 className="text-section-title">Requests</h1>

      {isLoading && <p className="text-muted-foreground text-body">Loading…</p>}
      {isError && <p className="text-destructive text-body">Could not load your requests.</p>}

      {data && data.items.length === 0 && (
        <p className="text-muted-foreground text-body">You haven&apos;t asked for anything yet.</p>
      )}

      {data && data.items.length > 0 && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Asked to</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Note</TableHead>
              <TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.items.map((request) => (
              <TableRow key={request.id}>
                <TableCell>{subjectText(request)}</TableCell>
                <TableCell>
                  <Badge variant={request.status === 'approved' ? 'default' : 'outline'}>
                    {STATUS_LABELS[request.status]}
                  </Badge>
                </TableCell>
                <TableCell>{request.parent_note ?? '—'}</TableCell>
                <TableCell>
                  <div className="flex gap-2">
                    {request.status === 'info_requested' && (
                      <Button size="sm" onClick={() => setReplyingTo(request.id)}>
                        Reply
                      </Button>
                    )}
                    {(request.status === 'pending_parent_approval' ||
                      request.status === 'info_requested') && (
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={withdraw.isPending}
                        onClick={() => handleWithdraw(request.id)}
                      >
                        Withdraw
                      </Button>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <Dialog open={replyingTo !== null} onOpenChange={(open) => !open && setReplyingTo(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reply to your parent</DialogTitle>
          </DialogHeader>
          <Input
            value={replyNote}
            onChange={(event) => setReplyNote(event.target.value)}
            placeholder="Your answer"
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setReplyingTo(null)}>
              Cancel
            </Button>
            <Button disabled={!replyNote.trim() || respond.isPending} onClick={handleRespond}>
              {respond.isPending ? 'Sending…' : 'Send'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
