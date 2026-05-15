import { create } from 'zustand'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

interface ChatStore {
  messages: ChatMessage[]
  typingIndicator: boolean
  sessionId: string | null
  pendingOptions: string[]
  questionnairePct: number
  addMessage: (msg: ChatMessage) => void
  setTyping: (typing: boolean) => void
  setSessionId: (id: string) => void
  clearMessages: () => void
  setPendingOptions: (options: string[]) => void
  clearPendingOptions: () => void
  setQuestionnairePct: (pct: number) => void
}

export const useChatStore = create<ChatStore>((set) => ({
  messages: [],
  typingIndicator: false,
  sessionId: null,
  pendingOptions: [],
  questionnairePct: 0,
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  setTyping: (typing) => set({ typingIndicator: typing }),
  setSessionId: (id) => set({ sessionId: id }),
  clearMessages: () => set({ messages: [], pendingOptions: [], questionnairePct: 0 }),
  setPendingOptions: (options) => set({ pendingOptions: options }),
  clearPendingOptions: () => set({ pendingOptions: [] }),
  setQuestionnairePct: (pct) => set({ questionnairePct: pct }),
}))
