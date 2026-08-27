import { z } from 'zod'

/**
 * URL state for the trainer's roster table — the same debounce-and-
 * replace convention as the directory's search (contracts/frontend-
 * contracts.md §8, D-04).
 */
export const rosterSearchSchema = z.object({
  page: z.number().int().min(1).catch(1),
  page_size: z.number().int().min(1).max(100).catch(25),
  q: z.string().max(200).optional(),
})

export type RosterSearch = z.infer<typeof rosterSearchSchema>
