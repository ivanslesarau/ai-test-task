import type { ApprovalSearch } from '@/entities/approval/model/approval-search'

/**
 * Single source of truth for every approval-related query key
 * (contracts/frontend-contracts.md §16). Invalidation contract:
 *
 * | Mutation                                        | Invalidates                                                          |
 * |--------------------------------------------------|-----------------------------------------------------------------------|
 * | approveApproval                                   | approvalKeys.all, userKeys.contexts, session, familyKeys.profiles     |
 * | denyApproval / requestInfoOnApproval              | approvalKeys.all                                                      |
 * | withdrawRequest / respondToRequest                | approvalKeys.all                                                      |
 *
 * The asymmetry is the point: a denial changes only the request, while an
 * approval performs the action, so it invalidates everything the action
 * touched (FR-151).
 */
export const approvalKeys = {
  all: ['approvals'] as const,
  queue: (search: ApprovalSearch) => ['approvals', 'queue', search] as const,
  detail: (requestId: string) => ['approvals', 'detail', requestId] as const,
  raised: (search: ApprovalSearch) => ['approvals', 'raised', search] as const,
} as const
