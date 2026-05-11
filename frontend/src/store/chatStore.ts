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
  addMessage: (msg: ChatMessage) => void
  setTyping: (typing: boolean) => void
  setSessionId: (id: string) => void
  clearMessages: () => void
}

export const useChatStore = create<ChatStore>((set) => ({
  messages: [],
  typingIndicator: false,
  sessionId: null,
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  setTyping: (typing) => set({ typingIndicator: typing }),
  setSessionId: (id) => set({ sessionId: id }),
  clearMessages: () => set({ messages: [] }),
}))
