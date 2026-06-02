import { create } from 'zustand'
import type { AgentTaskOut } from '@/lib/api'
import { AGENT_NODE_MAP, PRODUCT_NODE_MAP } from '@/features/agent-trace/agentPositions'

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

// Module-level ref avoids stale closures inside the setInterval callback
let _replayInterval: ReturnType<typeof setInterval> | null = null

function resolveNodes(agentId: string, productCode?: string | null): string[] {
  if (agentId === 'product_onboarding' && productCode && PRODUCT_NODE_MAP[productCode]) {
    return [PRODUCT_NODE_MAP[productCode]]
  }
  return AGENT_NODE_MAP[agentId] ?? [agentId]
}

interface TraceStore {
  nodeStates: Record<string, AgentNodeState>
  edgeQueue: AgentEdgeEvent[]
  messageLog: TraceMessage[]
  selectedAgent: string | null
  replayState: 'idle' | 'playing'
  replayProgress: number
  replaySpeed: number
  setNodeState: (agentId: string, state: AgentNodeState) => void
  enqueueEdge: (event: AgentEdgeEvent) => void
  dequeueEdge: (eventId: string) => void
  appendMessage: (msg: TraceMessage) => void
  initMessages: (msgs: TraceMessage[]) => void
  setSelectedAgent: (agentId: string | null) => void
  reset: () => void
  startReplay: (tasks: AgentTaskOut[]) => void
  stopReplay: () => void
  setReplaySpeed: (ms: number) => void
}

export const useTraceStore = create<TraceStore>((set, get) => ({
  nodeStates: {},
  edgeQueue: [],
  messageLog: [],
  selectedAgent: null,
  replayState: 'idle',
  replayProgress: 0,
  replaySpeed: 600,

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
    set((s) => {
      const existingIds = new Set(s.messageLog.map((m) => m.id))
      const incoming = msgs.filter((m) => !existingIds.has(m.id))
      return incoming.length > 0 ? { messageLog: [...s.messageLog, ...incoming] } : s
    }),
  setSelectedAgent: (agentId) => set({ selectedAgent: agentId }),
  reset: () => set({ nodeStates: {}, edgeQueue: [], messageLog: [], selectedAgent: null }),

  startReplay: (tasks) => {
    if (_replayInterval) {
      clearInterval(_replayInterval)
      _replayInterval = null
    }

    const sorted = [...tasks].sort(
      (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    )
    const total = sorted.length
    if (total === 0) return

    // Reset canvas to idle then begin
    set({ nodeStates: {}, edgeQueue: [], messageLog: [], replayState: 'playing', replayProgress: 0 })

    let index = 0
    const speed = get().replaySpeed

    _replayInterval = setInterval(() => {
      if (index >= total) {
        clearInterval(_replayInterval!)
        _replayInterval = null
        set({ replayState: 'idle', replayProgress: 100 })
        return
      }

      const task = sorted[index]
      const toNodes = resolveNodes(task.to_agent, task.product_code)
      const primaryTo = toNodes[0] ?? task.to_agent
      const fromNodes = resolveNodes(task.from_agent, null)

      const edge: AgentEdgeEvent = {
        id: `replay-${task.id}-${index}`,
        fromAgent: task.from_agent,
        toAgent: primaryTo,
        messageType: task.task_type,
        timestamp: task.created_at,
      }

      const fromState: AgentNodeState =
        task.status === 'ESCALATED'
          ? 'escalated'
          : task.status === 'FAILED'
          ? 'idle'
          : task.status === 'SUCCESS' || task.status === 'PARTIAL' || task.status === 'COMPLETE'
          ? 'complete'
          : 'active'

      const msg: TraceMessage = {
        id: `replay-msg-${task.id}-${index}`,
        fromAgent: task.from_agent,
        toAgent: task.to_agent,
        taskType: task.task_type,
        status: task.status,
        timestamp: task.created_at,
      }

      index++

      set((s) => {
        const newNodeStates = { ...s.nodeStates }
        toNodes.forEach((n) => { newNodeStates[n] = 'active' })
        fromNodes.forEach((n) => { newNodeStates[n] = fromState })
        return {
          nodeStates: newNodeStates,
          edgeQueue: [...s.edgeQueue, edge],
          messageLog: [...s.messageLog, msg],
          replayProgress: Math.round((index / total) * 100),
        }
      })
    }, speed)
  },

  stopReplay: () => {
    if (_replayInterval) {
      clearInterval(_replayInterval)
      _replayInterval = null
    }
    set({ replayState: 'idle' })
  },

  setReplaySpeed: (ms) => set({ replaySpeed: ms }),
}))
