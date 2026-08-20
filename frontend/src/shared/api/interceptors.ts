import type { AxiosInstance } from 'axios'

import { toApiError } from './errors'

/**
 * Contract fixed in specs/001-user-roles-admin/contracts/frontend-contracts.md §5:
 * - A 401 clears the session and redirects to /login, EXCEPT when the
 *   failing request is the session query itself — otherwise the app loops
 *   on load.
 * - A 403 never redirects; it means a legitimate session attempted
 *   something its role forbids, and hiding that behind a redirect would
 *   make it undiagnosable.
 */
export function registerInterceptors(client: AxiosInstance, onSessionExpired: () => void): void {
  client.interceptors.response.use(
    (response) => response,
    (error: unknown) => {
      const apiError = toApiError(error)
      const requestUrl = (error as { config?: { url?: string } })?.config?.url ?? ''
      const isSessionCheck = requestUrl.includes('/auth/session')

      if (apiError.status === 401 && !isSessionCheck) {
        onSessionExpired()
      }

      return Promise.reject(apiError)
    },
  )
}
