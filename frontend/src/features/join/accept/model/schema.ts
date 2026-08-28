import { z } from 'zod'

/** Mirrors `JoinAcceptRequest` (contracts/frontend-contracts.md §17,
 * Story 13). The selection lives in the form, not a store
 * (contracts/frontend-contracts.md §18); an empty selection is a valid
 * submission that changes nothing (FR-122). */
export const joinAcceptSchema = z.object({
  player_profile_ids: z.array(z.string()),
})

export type JoinAcceptValues = z.infer<typeof joinAcceptSchema>
