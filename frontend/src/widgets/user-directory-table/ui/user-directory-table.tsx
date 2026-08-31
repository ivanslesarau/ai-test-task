import { useEffect, useState } from 'react'

import { Link, useNavigate } from '@tanstack/react-router'

import { useUiStore } from '@/app/store/ui-store'
import { useUserDirectory } from '@/entities/user/api/use-users'
import type { DirectorySearch } from '@/entities/user/model/directory-search'
import { ImpersonateAction } from '@/features/admin/impersonation/ui/impersonate-action'
import { ReinviteButton } from '@/features/admin/reinvite-user/ui/reinvite-button'
import type { AccountStatus, UserRole } from '@/shared/api/types'
import { useDebouncedCallback } from '@/shared/lib/use-debounced-callback'
import { Badge } from '@/shared/ui/badge'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/ui/table'

const STATUS_VARIANT: Record<AccountStatus, 'default' | 'secondary' | 'outline'> = {
  active: 'default',
  inactive: 'secondary',
  deleted: 'outline',
}

const ROLE_LABEL: Record<UserRole, string> = {
  super_admin: 'Super Admin',
  trainer: 'Trainer',
  coach: 'Coach',
  player_parent: 'Player/Parent',
}

interface UserDirectoryTableProps {
  search: DirectorySearch
}

export function UserDirectoryTable({ search }: UserDirectoryTableProps) {
  const navigate = useNavigate({ from: '/admin/users/' })
  const { data, isLoading, isError } = useUserDirectory(search)
  const openPendingAction = useUiStore((state) => state.openPendingAction)

  // The URL stays the single source of truth for `q`
  // (contracts/frontend-contracts.md §4) — this is local UI state for the
  // input's own keystroke-by-keystroke value, not a second copy of the
  // search term. It re-seeds from `search.q` whenever the URL changes out
  // from under it (back/forward navigation, a role/status filter change).
  const [searchTerm, setSearchTerm] = useState(search.q ?? '')

  useEffect(() => {
    setSearchTerm(search.q ?? '')
  }, [search.q])

  function updateSearch(patch: Partial<DirectorySearch>, options?: { replace?: boolean }) {
    void navigate({
      search: (prev) => ({ ...prev, ...patch, page: patch.page ?? 1 }),
      replace: options?.replace ?? false,
    })
  }

  // Debounced 500ms (interval decided by the user, 2026-08-25) and pushed
  // with `replace: true`, so a 20-character search term leaves one history
  // entry instead of twenty (FR-063, SC-013). Paging and the role/status
  // filters below still call `updateSearch` directly, pushing a normal
  // entry — those are deliberate steps a Super Admin should be able to
  // reverse.
  const debouncedPushSearchTerm = useDebouncedCallback((term: string) => {
    updateSearch({ q: term.trim() === '' ? undefined : term }, { replace: true })
  }, 500)

  function handleSearchTermChange(value: string) {
    setSearchTerm(value)
    debouncedPushSearchTerm(value)
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <Input
          aria-label="Search by name or email"
          placeholder="Search by name or email"
          value={searchTerm}
          onChange={(event) => handleSearchTermChange(event.target.value)}
          className="max-w-xs"
        />
        <Select
          value={search.role ?? 'all'}
          onValueChange={(value) =>
            updateSearch({ role: value === 'all' ? undefined : (value as UserRole) })
          }
        >
          <SelectTrigger className="w-40" aria-label="Filter by role">
            <SelectValue placeholder="Role" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All roles</SelectItem>
            {Object.entries(ROLE_LABEL).map(([value, label]) => (
              <SelectItem key={value} value={value}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={search.status ?? 'all'}
          onValueChange={(value) =>
            updateSearch({ status: value === 'all' ? undefined : (value as AccountStatus) })
          }
        >
          <SelectTrigger className="w-40" aria-label="Filter by status">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="inactive">Inactive</SelectItem>
            <SelectItem value="deleted">Deleted</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isLoading && <p className="text-muted-foreground text-body">Loading…</p>}
      {isError && <p className="text-destructive text-body">Could not load the directory.</p>}
      {data && data.items.length === 0 && (
        <p className="text-muted-foreground text-body">
          No accounts match the current search and filters.
        </p>
      )}

      {data && data.items.length > 0 && (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((user) => (
                <TableRow
                  key={user.id}
                  data-inactive={user.status !== 'active'}
                  className="data-[inactive=true]:opacity-60"
                >
                  <TableCell>
                    <Link
                      to="/admin/users/$userId"
                      params={{ userId: user.id }}
                      className="underline"
                    >
                      {user.first_name} {user.last_name}
                    </Link>
                  </TableCell>
                  <TableCell>{user.email}</TableCell>
                  <TableCell>{ROLE_LABEL[user.role]}</TableCell>
                  <TableCell>
                    <Badge variant={STATUS_VARIANT[user.status]}>{user.status}</Badge>
                  </TableCell>
                  <TableCell className="flex gap-2">
                    {!user.has_password && user.status === 'active' && (
                      <ReinviteButton userId={user.id} />
                    )}
                    {user.status === 'active' && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => openPendingAction({ kind: 'deactivate', userId: user.id })}
                      >
                        Deactivate
                      </Button>
                    )}
                    {user.status === 'inactive' && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => openPendingAction({ kind: 'reactivate', userId: user.id })}
                      >
                        Reactivate
                      </Button>
                    )}
                    <ImpersonateAction user={user} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          <div className="flex items-center justify-between">
            <p className="text-caption text-muted-foreground">
              {data.total} account{data.total === 1 ? '' : 's'}
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
