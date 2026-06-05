import { create } from 'zustand'

interface TabEntry {
  caseId: string
  clientId: string
  label: string
}

interface WorkspaceStore {
  selectedClientId: string | null
  selectedCaseId: string | null
  activeDocumentId: string | null
  isDrawerOpen: boolean
  uploadBadgeCounts: Record<string, number>
  socketConnected: boolean
  openTabs: TabEntry[]
  activeTabId: string
  setSelectedClient: (clientId: string | null, caseId: string | null) => void
  setActiveDocument: (id: string | null) => void
  setDrawerOpen: (open: boolean) => void
  incrementBadge: (caseId: string) => void
  clearBadge: (caseId: string) => void
  setSocketConnected: (connected: boolean) => void
  pendingTaskId: string | null
  setPendingTaskId: (id: string | null) => void
  openCaseTab: (caseId: string, clientId: string, label: string) => void
  closeCaseTab: (caseId: string) => void
  setActiveTab: (tabId: string) => void
}

export const useWorkspaceStore = create<WorkspaceStore>((set) => ({
  selectedClientId: null,
  selectedCaseId: null,
  activeDocumentId: null,
  isDrawerOpen: false,
  uploadBadgeCounts: {},
  socketConnected: false,
  openTabs: [],
  activeTabId: 'dashboard',
  setSelectedClient: (clientId, caseId) =>
    set({ selectedClientId: clientId, selectedCaseId: caseId, activeDocumentId: null, isDrawerOpen: false }),
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
  pendingTaskId: null,
  setPendingTaskId: (id) => set({ pendingTaskId: id }),
  openCaseTab: (caseId, clientId, label) =>
    set((s) => {
      const exists = s.openTabs.find((t) => t.caseId === caseId)
      const newTabs = exists ? s.openTabs : [...s.openTabs, { caseId, clientId, label }]
      return {
        openTabs: newTabs,
        activeTabId: caseId,
        selectedCaseId: caseId,
        selectedClientId: clientId,
        activeDocumentId: null,
        isDrawerOpen: false,
      }
    }),
  closeCaseTab: (caseId) =>
    set((s) => {
      const newTabs = s.openTabs.filter((t) => t.caseId !== caseId)
      const wasActive = s.activeTabId === caseId
      let newActiveTabId = s.activeTabId
      let newSelectedCaseId = s.selectedCaseId
      let newSelectedClientId = s.selectedClientId

      if (wasActive) {
        const idx = s.openTabs.findIndex((t) => t.caseId === caseId)
        const next = newTabs[idx] ?? newTabs[idx - 1] ?? null
        newActiveTabId = next ? next.caseId : 'dashboard'
        newSelectedCaseId = next ? next.caseId : null
        newSelectedClientId = next ? next.clientId : null
      }

      return {
        openTabs: newTabs,
        activeTabId: newActiveTabId,
        selectedCaseId: newSelectedCaseId,
        selectedClientId: newSelectedClientId,
        activeDocumentId: null,
        isDrawerOpen: false,
      }
    }),
  setActiveTab: (tabId) =>
    set((s) => {
      const tab = s.openTabs.find((t) => t.caseId === tabId)
      return {
        activeTabId: tabId,
        selectedCaseId: tabId === 'dashboard' ? null : tabId,
        selectedClientId: tabId === 'dashboard' ? null : (tab?.clientId ?? null),
        activeDocumentId: null,
        isDrawerOpen: false,
      }
    }),
}))
