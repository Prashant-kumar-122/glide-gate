import { create } from 'zustand'

interface WorkspaceStore {
  selectedClientId: string | null
  activeDocumentId: string | null
  isDrawerOpen: boolean
  uploadBadgeCounts: Record<string, number>
  socketConnected: boolean
  setSelectedClient: (id: string | null) => void
  setActiveDocument: (id: string | null) => void
  setDrawerOpen: (open: boolean) => void
  incrementBadge: (caseId: string) => void
  clearBadge: (caseId: string) => void
  setSocketConnected: (connected: boolean) => void
}

export const useWorkspaceStore = create<WorkspaceStore>((set) => ({
  selectedClientId: null,
  activeDocumentId: null,
  isDrawerOpen: false,
  uploadBadgeCounts: {},
  socketConnected: false,
  setSelectedClient: (id) => set({ selectedClientId: id }),
  setActiveDocument: (id) => set({ activeDocumentId: id }),
  setDrawerOpen: (open) => set({ isDrawerOpen: open }),
  incrementBadge: (caseId) =>
    set((s) => ({
      uploadBadgeCounts: {
        ...s.uploadBadgeCounts,
        [caseId]: (s.uploadBadgeCounts[caseId] ?? 0) + 1,
      },
    })),
  clearBadge: (caseId) =>
    set((s) => {
      const next = { ...s.uploadBadgeCounts }
      delete next[caseId]
      return { uploadBadgeCounts: next }
    }),
  setSocketConnected: (connected) => set({ socketConnected: connected }),
}))
