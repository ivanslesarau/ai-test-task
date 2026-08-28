import { Link } from '@tanstack/react-router'

import type { PlayerProfile } from '@/shared/api/types'
import { Badge } from '@/shared/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/ui/table'

interface FamilyRosterListProps {
  profiles: PlayerProfile[]
}

/**
 * The family page's table (US9, FR-124): one row per profile, the
 * account-holder marker for a `self` profile, and every trainer that
 * profile currently trains with, each with the date the association
 * began. Composes `shared/ui` primitives only (tasks.md T363).
 */
export function FamilyRosterList({ profiles }: FamilyRosterListProps) {
  if (profiles.length === 0) {
    return (
      <p className="text-muted-foreground text-body">
        No players on this account yet. Add a child to get started.
      </p>
    )
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Age</TableHead>
          <TableHead>Trainers</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {profiles.map((profile) => (
          <TableRow key={profile.id}>
            <TableCell>
              <Link
                to="/family/$profileId"
                params={{ profileId: profile.id }}
                className="underline"
              >
                {profile.display_name}
              </Link>
              {profile.kind === 'self' && (
                <Badge variant="outline" className="ml-2">
                  Me
                </Badge>
              )}
            </TableCell>
            <TableCell>{profile.age ?? '—'}</TableCell>
            <TableCell>
              {profile.associations.length === 0 ? (
                <span className="text-muted-foreground">No trainers yet</span>
              ) : (
                <ul className="flex flex-col gap-1">
                  {profile.associations.map((association) => (
                    <li key={association.association_id}>
                      {association.trainer_display_name}{' '}
                      <span className="text-muted-foreground text-caption">
                        since {new Date(association.joined_at).toLocaleDateString()}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
