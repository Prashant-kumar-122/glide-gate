import { create } from 'zustand'

interface ClientTab {
  clientId: string
  label: string
}

interface CCStore {
  selectedClientId: string | null
  filterText: string
  socketStatus: 'connected' | 'disconnected' | 'connecting'
  openTabs: ClientTab[]
  activeTabId: string
  setSelectedClient: (id: string | null) => void
  setFilterText: (text: string) => void
  setSocketStatus: (status: CCStore['socketStatus']) => void
  openClientTab: (id: string, label: string) => void
  closeClientTab: (id: string) => void
  setActiveTab: (tabId: string) => void
}

export const useCCStore = create<CCStore>((set) => ({
  selectedClientId: null,
  filterText: '',
  socketStatus: 'disconnected',
  openTabs: [],
  activeTabId: 'clients',
  setSelectedClient: (id) => set({ selectedClientId: id }),
  setFilterText: (text) => set({ filterText: text }),
  setSocketStatus: (status) => set({ socketStatus: status }),
  openClientTab: (id, label) =>
    set((s) => {
      const exists = s.openTabs.find((t) => t.clientId === id)
      const newTabs = exists ? s.openTabs : [...s.openTabs, { clientId: id, label }]
      return { openTabs: newTabs, activeTabId: id, selectedClientId: id }
    }),
  closeClientTab: (id) =>
    set((s) => {
      const newTabs = s.openTabs.filter((t) => t.clientId !== id)
      const wasActive = s.activeTabId === id
      let newActiveTabId = s.activeTabId
      let newSelectedClientId = s.selectedClientId

      if (wasActive) {
        const idx = s.openTabs.findIndex((t) => t.clientId === id)
        const next = newTabs[idx] ?? newTabs[idx - 1] ?? null
        newActiveTabId = next ? next.clientId : 'clients'
        newSelectedClientId = next ? next.clientId : null
      }

      return { openTabs: newTabs, activeTabId: newActiveTabId, selectedClientId: newSelectedClientId }
    }),
  setActiveTab: (tabId) =>
    set((s) => {
      const tab = s.openTabs.find((t) => t.clientId === tabId)
      return {
        activeTabId: tabId,
        selectedClientId: tabId === 'clients' ? null : (tab?.clientId ?? null),
      }
    }),
}))
