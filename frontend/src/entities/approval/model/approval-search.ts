import { z } from 'zod'

/**
 * Single source of truth for the approvals/requests queues' URL state
 * (contracts/frontend-contracts.md §17). `.catch()` rather than
 * `.default()` on the numeric and enum fields so a hand-edited or stale
 * URL degrades to a valid view instead of throwing.
 */
export const approvalSearchSchema = z.object({
  status: z
    .enum([
      'pending_parent_approval',
      'info_requested',
      'approved',
      'denied',
      'expired',
      'withdrawn',
    ])
    .optional(),
  page: z.number().int().min(1).catch(1),
  page_size: z.number().int().min(1).max(100).catch(25),
})

export type ApprovalSearch = z.infer<typeof approvalSearchSchema>
