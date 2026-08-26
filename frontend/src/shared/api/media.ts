import { apiClient } from '@/shared/api/client'

/**
 * `photo_url`/`thumbnail_url` are API-relative paths (e.g.
 * `/media/photos/{key}`). A request made through `apiClient` resolves them
 * against its `baseURL` automatically; a DOM `src` does not — it resolves
 * against the document origin instead, where the dev proxy forwards only
 * `/api`. This is the only place a media path becomes DOM-usable
 * (contracts/frontend-contracts.md §5, §6); components must never
 * concatenate the base URL themselves.
 */
export function resolveMediaUrl(path: string | null): string | null {
  if (path === null) return null
  const baseUrl = apiClient.defaults.baseURL ?? ''
  return `${baseUrl.replace(/\/+$/, '')}${path}`
}
