import { create } from 'zustand'

/**
 * Which impersonation ids have already had their end-reason toast shown
 * (research.md R2-20, frontend-contracts.md §33). The server derives
 * `impersonation_ended` from a 120-second look-back with no "notice
 * delivered" flag of its own — "have I shown this toast" is client UI
 * state, exactly what the constitution reserves Zustand for. No server
 * response is copied in here, only the `id` already carried by the
 * session query's own data.
 */
interface ImpersonationNoticeState {
  shownIds: ReadonlySet<string>
  hasBeenShown: (id: string) => boolean
  markShown: (id: string) => void
}

export const useImpersonationNoticeStore = create<ImpersonationNoticeState>((set, get) => ({
  shownIds: new Set(),
  hasBeenShown: (id) => get().shownIds.has(id),
  markShown: (id) =>
    set((state) => ({ shownIds: new Set(state.shownIds).add(id) })),
}))
