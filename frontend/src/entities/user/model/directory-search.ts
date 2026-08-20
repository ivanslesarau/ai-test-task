import { z } from 'zod'

/**
 * Single source of truth for the directory's URL state
 * (contracts/frontend-contracts.md §1). `.catch()` rather than `.default()`
 * on the numeric and enum fields so a hand-edited or stale URL degrades to
 * a valid view instead of throwing.
 */
export const directorySearchSchema = z.object({
  page: z.number().int().min(1).catch(1),
  page_size: z.number().int().min(1).max(100).catch(25),
  q: z.string().max(200).optional(),
  role: z.enum(['super_admin', 'trainer', 'coach', 'player_parent']).optional(),
  status: z.enum(['active', 'inactive', 'deleted']).optional(),
  sort: z
    .enum(['created_at_desc', 'created_at_asc', 'name_asc', 'name_desc'])
    .catch('created_at_desc'),
})

export type DirectorySearch = z.infer<typeof directorySearchSchema>
