import { create } from 'zustand'

interface CCStore {
  selectedClientId: string | null
  filterText: string
  socketStatus: 'connected' | 'disconnected' | 'connecting'
  setSelectedClient: (id: string | null) => void
  setFilterText: (text: string) => void
  setSocketStatus: (status: CCStore['socketStatus']) => void
}

export const useCCStore = create<CCStore>((set) => ({
  selectedClientId: null,
  filterText: '',
  socketStatus: 'disconnected',
  setSelectedClient: (id) => set({ selectedClientId: id }),
  setFilterText: (text) => set({ filterText: text }),
  setSocketStatus: (status) => set({ socketStatus: status }),
}))
