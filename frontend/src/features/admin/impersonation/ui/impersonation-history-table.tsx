import { useNavigate } from '@tanstack/react-router'

import { useImpersonations } from '@/entities/impersonation/api/use-impersonations'
import type { ImpersonationHistorySearch } from '@/entities/impersonation/model/history-search'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/ui/table'

interface ImpersonationHistoryTableProps {
  search: ImpersonationHistorySearch
}

function formatDuration(seconds: number | null): string {
  if (seconds === null) return '—'
  const minutes = Math.floor(seconds / 60)
  const rest = seconds % 60
  return `${minutes}m ${rest}s`
}

/**
 * The append-only impersonation history (US7, FR-053, FR-054). Every
 * impersonation the platform has ever permitted, newest first; a row
 * still in progress shows no end time and no duration rather than a
 * placeholder value that could be mistaken for zero.
 */
export function ImpersonationHistoryTable({ search }: ImpersonationHistoryTableProps) {
  const navigate = useNavigate({ from: '/admin/impersonations' })
  const { data, isLoading, isError } = useImpersonations(search)

  function updateSearch(patch: Partial<ImpersonationHistorySearch>) {
    void navigate({
      search: (prev) => ({ ...prev, ...patch, page: patch.page ?? 1 }),
    })
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-2">
        <Input
          aria-label="Filter by admin id"
          placeholder="Admin id"
          value={search.admin_user_id ?? ''}
          onChange={(event) =>
            updateSearch({ admin_user_id: event.target.value.trim() || undefined })
          }
          className="max-w-xs"
        />
        <Input
          aria-label="Filter by impersonated account id"
          placeholder="Impersonated account id"
          value={search.target_user_id ?? ''}
          onChange={(event) =>
            updateSearch({ target_user_id: event.target.value.trim() || undefined })
          }
          className="max-w-xs"
        />
      </div>

      {isLoading && <p className="text-muted-foreground text-body">Loading…</p>}
      {isError && <p className="text-destructive text-body">Could not load the history.</p>}
      {data && data.items.length === 0 && (
        <p className="text-muted-foreground text-body">No impersonations recorded.</p>
      )}

      {data && data.items.length > 0 && (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Admin</TableHead>
                <TableHead>Viewing as</TableHead>
                <TableHead>Started</TableHead>
                <TableHead>Ended</TableHead>
                <TableHead>Duration</TableHead>
                <TableHead>Reason</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((row) => (
                <TableRow key={row.id}>
                  <TableCell>{row.admin.display_name}</TableCell>
                  <TableCell>{row.target.display_name}</TableCell>
                  <TableCell>{new Date(row.started_at).toLocaleString()}</TableCell>
                  <TableCell>
                    {row.ended_at ? (
                      new Date(row.ended_at).toLocaleString()
                    ) : (
                      <Badge variant="secondary">In progress</Badge>
                    )}
                  </TableCell>
                  <TableCell>{formatDuration(row.duration_seconds)}</TableCell>
                  <TableCell>{row.end_reason ?? '—'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          <div className="flex items-center justify-between">
            <p className="text-caption text-muted-foreground">
              {data.total} impersonation{data.total === 1 ? '' : 's'}
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={search.page <= 1}
                onClick={() => updateSearch({ page: search.page - 1 })}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={search.page * search.page_size >= data.total}
                onClick={() => updateSearch({ page: search.page + 1 })}
              >
                Next
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
