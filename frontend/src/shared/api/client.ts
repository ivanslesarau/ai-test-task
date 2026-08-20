import axios from 'axios'

/**
 * The single axios instance for the whole frontend (constitution Principle
 * IV: centralize axios in shared/api; UI components never call axios
 * directly). `withCredentials` is required because the session is a
 * first-party cookie, not an Authorization header (research.md R-03).
 */
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api/v1',
  withCredentials: true,
})
