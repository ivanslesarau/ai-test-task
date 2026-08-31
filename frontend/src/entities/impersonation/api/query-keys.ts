/** `GET /admin/impersonations`' own query parameters (US7, contracts/
 * openapi.yaml). Declared here alongside `impersonationKeys` even though
 * US6 never calls `list` — the same reason `coachInvitationKeys.preview`
 * is declared ahead of the story that reads it (frontend-contracts.md
 * §31): one factory per resource, not one per story. */
export interface ImpersonationHistoryParams {
  page: number
  page_size: number
  admin_user_id?: string
  target_user_id?: string
  started_from?: string
  started_to?: string
}

export const impersonationKeys = {
  all: ['impersonations'] as const,
  list: (params: ImpersonationHistoryParams) => ['impersonations', 'list', params] as const,
}
