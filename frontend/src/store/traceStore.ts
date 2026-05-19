import { create } from 'zustand'

export type AgentNodeState = 'idle' | 'active' | 'escalated' | 'complete'

export interface AgentEdgeEvent {
  id: string
  fromAgent: string
  toAgent: string
  messageType: string
  timestamp: string
}

export interface TraceMessage {
  id: string
  fromAgent: string
  toAgent: string
  taskType: string
  status: string
  timestamp: string
}

interface TraceStore {
  nodeStates: Record<string, AgentNodeState>
  edgeQueue: AgentEdgeEvent[]
  messageLog: TraceMessage[]
  selectedAgent: string | null
  setNodeState: (agentId: string, state: AgentNodeState) => void
  enqueueEdge: (event: AgentEdgeEvent) => void
  dequeueEdge: (eventId: string) => void
  appendMessage: (msg: TraceMessage) => void
  initMessages: (msgs: TraceMessage[]) => void
  setSelectedAgent: (agentId: string | null) => void
  reset: () => void
}

export const useTraceStore = create<TraceStore>((set) => ({
  nodeStates: {},
  edgeQueue: [],
  messageLog: [],
  selectedAgent: null,
  setNodeState: (agentId, state) =>
    set((s) => ({ nodeStates: { ...s.nodeStates, [agentId]: state } })),
  enqueueEdge: (event) =>
    set((s) => ({ edgeQueue: [...s.edgeQueue, event] })),
  dequeueEdge: (eventId) =>
    set((s) => ({ edgeQueue: s.edgeQueue.filter((e) => e.id !== eventId) })),
  appendMessage: (msg) =>
    set((s) =>
      s.messageLog.some((m) => m.id === msg.id)
        ? s
        : { messageLog: [...s.messageLog, msg] },
    ),
  initMessages: (msgs) =>
    set((s) => ({ messageLog: msgs.filter((m) => !s.messageLog.some((e) => e.id === m.id)) })),
  setSelectedAgent: (agentId) => set({ selectedAgent: agentId }),
  reset: () => set({ nodeStates: {}, edgeQueue: [], messageLog: [], selectedAgent: null }),
}))
