import { create } from 'zustand'

export type PendingActionKind = 'deactivate' | 'reactivate' | 'erase' | 'impersonate'

export interface PendingAction {
  kind: PendingActionKind
  /**
   * Only a routing coordinate the UI already holds — never the account
   * object itself. The dialog resolves current data through
   * userKeys.detail(userId), so no server response is ever copied into
   * this store (constitution Principle IV: Zustand holds UI state only).
   */
  userId: string
}

interface UiState {
  isSidebarCollapsed: boolean
  theme: 'light' | 'dark' | 'system'
  pendingAction: PendingAction | null
  setSidebarCollapsed: (collapsed: boolean) => void
  setTheme: (theme: UiState['theme']) => void
  openPendingAction: (action: PendingAction) => void
  clearPendingAction: () => void
}

export const useUiStore = create<UiState>((set) => ({
  isSidebarCollapsed: false,
  theme: 'system',
  pendingAction: null,
  setSidebarCollapsed: (collapsed) => set({ isSidebarCollapsed: collapsed }),
  setTheme: (theme) => set({ theme }),
  openPendingAction: (action) => set({ pendingAction: action }),
  clearPendingAction: () => set({ pendingAction: null }),
}))
