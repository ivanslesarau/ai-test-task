import { useEffect, useState } from 'react'

import { useNavigate } from '@tanstack/react-router'

import { useSession } from '@/entities/session/api/use-session'
import { useTrainerRoster } from '@/entities/trainer-context/api/use-roster'
import type { RosterSearch } from '@/entities/trainer-context/model/roster-search'
import { useDebouncedCallback } from '@/shared/lib/use-debounced-callback'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/ui/table'

interface TrainerRosterTableProps {
  search: RosterSearch
}

/** Same debounce-and-replace convention as the Super Admin directory
 * (D-04): 500 ms, `replace: true` on the search term, normal history
 * entries for paging. */
export function TrainerRosterTable({ search }: TrainerRosterTableProps) {
  const { data: session } = useSession()
  const navigate = useNavigate({ from: '/trainer/players' })
  const { data, isLoading, isError } = useTrainerRoster(session?.id ?? '', search)

  const [searchTerm, setSearchTerm] = useState(search.q ?? '')
  useEffect(() => {
    setSearchTerm(search.q ?? '')
  }, [search.q])

  function updateSearch(patch: Partial<RosterSearch>, options?: { replace?: boolean }) {
    void navigate({
      search: (prev) => ({ ...prev, ...patch, page: patch.page ?? 1 }),
      replace: options?.replace ?? false,
    })
  }

  const debouncedPushSearchTerm = useDebouncedCallback((term: string) => {
    updateSearch({ q: term.trim() === '' ? undefined : term }, { replace: true })
  }, 500)

  return (
    <div className="flex flex-col gap-4">
      <Input
        aria-label="Search by player name"
        placeholder="Search by player name"
        value={searchTerm}
        onChange={(event) => {
          setSearchTerm(event.target.value)
          debouncedPushSearchTerm(event.target.value)
        }}
        className="max-w-xs"
      />

      {isLoading && <p className="text-muted-foreground text-body">Loading…</p>}
      {isError && <p className="text-destructive text-body">Could not load your roster.</p>}
      {data && data.items.length === 0 && (
        <p className="text-muted-foreground text-body">No players yet. Share your invitation link to get started.</p>
      )}

      {data && data.items.length > 0 && (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Age</TableHead>
                <TableHead>Joined</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((player) => (
                <TableRow key={player.player_user_id}>
                  <TableCell>{player.display_name}</TableCell>
                  <TableCell>{player.age ?? '—'}</TableCell>
                  <TableCell>{new Date(player.joined_at).toLocaleDateString()}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          <div className="flex items-center justify-between">
            <p className="text-caption text-muted-foreground">
              {data.total} player{data.total === 1 ? '' : 's'}
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
