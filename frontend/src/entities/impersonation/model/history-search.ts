import { z } from 'zod'

/**
 * Single source of truth for the impersonation history's URL state
 * (US7, FR-053, FR-054, frontend-contracts.md §32). `.catch()` rather
 * than `.default()` on every field so a hand-edited or stale URL
 * degrades to a valid view instead of throwing — the same convention
 * `directorySearchSchema` already uses.
 */
export const impersonationHistorySearchSchema = z.object({
  page: z.number().int().min(1).catch(1),
  page_size: z.number().int().min(1).max(100).catch(25),
  admin_user_id: z.string().uuid().optional().catch(undefined),
  target_user_id: z.string().uuid().optional().catch(undefined),
  started_from: z.string().datetime().optional().catch(undefined),
  started_to: z.string().datetime().optional().catch(undefined),
})

export type ImpersonationHistorySearch = z.infer<typeof impersonationHistorySearchSchema>
