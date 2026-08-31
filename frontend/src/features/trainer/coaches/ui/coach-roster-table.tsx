import { useState } from 'react'

import { Link } from '@tanstack/react-router'
import { toast } from 'sonner'

import { useEndCoachAssignment } from '@/entities/coach/api/use-end-coach-assignment'
import { useTrainerCoaches } from '@/entities/coach/api/use-trainer-coaches'
import { AvailabilitySummary } from '@/features/availability/ui/availability-summary'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/shared/ui/alert-dialog'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/ui/table'

const PAGE_SIZE = 25

/**
 * The roster half of `/trainer/coaches` (FR-020 – FR-023). Local
 * page/search state rather than URL search params — unlike the player
 * roster, no independent test task asks for a shareable filtered link
 * here, and the coach and invitation lists already share the page.
 */
export function CoachRosterTable() {
  const [page, setPage] = useState(1)
  const [searchTerm, setSearchTerm] = useState('')
  const { data, isLoading, isError } = useTrainerCoaches({
    page,
    page_size: PAGE_SIZE,
    q: searchTerm.trim() === '' ? undefined : searchTerm.trim(),
  })
  const endAssignment = useEndCoachAssignment()

  return (
    <div className="flex flex-col gap-4">
      <Input
        aria-label="Search by coach name or email"
        placeholder="Search by coach name or email"
        value={searchTerm}
        onChange={(event) => {
          setSearchTerm(event.target.value)
          setPage(1)
        }}
        className="max-w-xs"
      />

      {isLoading && <p className="text-muted-foreground text-body">Loading…</p>}
      {isError && <p className="text-destructive text-body">Could not load your coaches.</p>}
      {data && data.items.length === 0 && (
        <p className="text-muted-foreground text-body">
          No coaches yet. Invite one above to get started.
        </p>
      )}

      {data && data.items.length > 0 && (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Joined</TableHead>
                <TableHead>Best times</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.items.map((coach) => (
                <TableRow key={coach.user_id}>
                  <TableCell>
                    <Link
                      to="/trainer/coaches/$coachUserId"
                      params={{ coachUserId: coach.user_id }}
                      className="underline"
                    >
                      {coach.first_name} {coach.last_name}
                    </Link>
                  </TableCell>
                  <TableCell>{coach.email}</TableCell>
                  <TableCell>{new Date(coach.joined_at).toLocaleDateString()}</TableCell>
                  <TableCell>
                    <AvailabilitySummary
                      slots={coach.availability}
                      updatedAt={coach.availability_updated_at}
                    />
                  </TableCell>
                  <TableCell>
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button variant="outline" size="sm">
                          End assignment
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>
                            End {coach.first_name} {coach.last_name}&apos;s assignment?
                          </AlertDialogTitle>
                          <AlertDialogDescription>
                            {coach.first_name} will be on no roster afterwards, and reaches none of
                            your data. Their account, profile, and stated times are kept, and they
                            are free to accept another trainer&apos;s invitation.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction
                            disabled={endAssignment.isPending}
                            onClick={() => {
                              endAssignment.mutate(coach.user_id, {
                                onSuccess: () =>
                                  toast.success(
                                    `${coach.first_name} ${coach.last_name}'s assignment ended`,
                                  ),
                                onError: () => toast.error('Could not end this assignment'),
                              })
                            }}
                          >
                            {endAssignment.isPending ? 'Ending…' : 'End assignment'}
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          <div className="flex items-center justify-between">
            <p className="text-caption text-muted-foreground">
              {data.total} coach{data.total === 1 ? '' : 'es'}
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((prev) => prev - 1)}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page * PAGE_SIZE >= data.total}
                onClick={() => setPage((prev) => prev + 1)}
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
