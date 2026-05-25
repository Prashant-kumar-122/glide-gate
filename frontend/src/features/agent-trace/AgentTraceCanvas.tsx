import { useState, useEffect, useCallback, useRef } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
} from '@xyflow/react'
import type { Node, Edge, NodeTypes, OnNodeClick } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { List, X } from 'lucide-react'

import { useTraceStore } from '@/store/traceStore'
import { useThemeStore } from '@/store/themeStore'
import { AgentNode } from './AgentNode'
import { AgentDetailPopover } from './AgentDetailPopover'
import { MessageLog } from './MessageLog'
import { useAgentTraceSocket } from './useAgentTraceSocket'
import { AGENT_IDS, AGENT_LABELS, AGENT_POSITIONS, STATIC_EDGES, AGENT_NODE_MAP, PRODUCT_NODE_MAP } from './agentPositions'
import { useAgentTrace } from '@/hooks/useAgentTrace'

const NODE_TYPES: NodeTypes = { agentNode: AgentNode }

function makeInitialNodes(): Node[] {
  return AGENT_IDS.map((agentId) => ({
    id: agentId,
    type: 'agentNode',
    position: AGENT_POSITIONS[agentId],
    data: { label: AGENT_LABELS[agentId], agentId, nodeState: 'idle' },
    draggable: true,
  }))
}

function makeStaticEdges(): Edge[] {
  return STATIC_EDGES.map((e) => ({
    ...e,
    type: 'smoothstep',
    style: { stroke: '#e5e7eb', strokeWidth: 1.5 },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#e5e7eb' },
  }))
}

interface AgentTraceCanvasProps {
  activeCaseId: string | null
}

export default function AgentTraceCanvas({ activeCaseId }: AgentTraceCanvasProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState(makeInitialNodes())
  const [edges, setEdges] = useEdgesState(makeStaticEdges())
  const [showPanel, setShowPanel] = useState(false)

  const nodeStates = useTraceStore((s) => s.nodeStates)
  const edgeQueue = useTraceStore((s) => s.edgeQueue)
  const dequeueEdge = useTraceStore((s) => s.dequeueEdge)
  const selectedAgent = useTraceStore((s) => s.selectedAgent)
  const setSelectedAgent = useTraceStore((s) => s.setSelectedAgent)
  const setNodeState = useTraceStore((s) => s.setNodeState)
  const initMessages = useTraceStore((s) => s.initMessages)
  const theme = useThemeStore((s) => s.theme)

  const { data: traceData } = useAgentTrace(activeCaseId)

  useAgentTraceSocket(activeCaseId)

  // Sync node colours with traceStore
  useEffect(() => {
    setNodes((prev) =>
      prev.map((n) => ({
        ...n,
        data: { ...n.data, nodeState: nodeStates[n.id] ?? 'idle' },
      })),
    )
  }, [nodeStates, setNodes])

  // Hydrate node states and message log from persisted task history on load / poll
  useEffect(() => {
    if (!traceData?.tasks?.length) return

    const agentTasks: Record<string, { status: string }[]> = {}
    for (const task of traceData.tasks) {
      let nodeKey = task.to_agent
      if (task.to_agent === 'product_onboarding' && task.product_code) {
        nodeKey = PRODUCT_NODE_MAP[task.product_code] ?? task.to_agent
      }
      if (!agentTasks[nodeKey]) agentTasks[nodeKey] = []
      agentTasks[nodeKey].push(task)
    }

    const allStatuses = traceData.tasks.map((t) => t.status)
    const anyEscalated = allStatuses.some((s) => s === 'ESCALATED')
    const anyInProgress = allStatuses.some((s) => s === 'IN_PROGRESS' || s === 'PENDING')
    const allDone = allStatuses.every((s) => ['SUCCESS', 'PARTIAL', 'FAILED'].includes(s))
    setNodeState(
      'orchestrator',
      anyEscalated ? 'escalated' : anyInProgress ? 'active' : allDone ? 'complete' : 'idle',
    )

    for (const [agentId, tasks] of Object.entries(agentTasks)) {
      if (agentId === 'orchestrator') continue
      const hasEscalated = tasks.some((t) => t.status === 'ESCALATED')
      const hasInProgress = tasks.some((t) => t.status === 'IN_PROGRESS' || t.status === 'PENDING')
      const hasSuccess = tasks.some((t) => t.status === 'SUCCESS' || t.status === 'PARTIAL')
      const state = hasEscalated ? 'escalated' : hasInProgress ? 'active' : hasSuccess ? 'complete' : 'idle'
      const nodeIds = AGENT_NODE_MAP[agentId] ?? [agentId]
      nodeIds.forEach((n) => setNodeState(n, state))
    }

    const historicalMessages = traceData.tasks
      .slice()
      .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
      .map((task) => ({
        id: task.id,
        fromAgent: task.from_agent,
        toAgent: task.to_agent,
        taskType: task.task_type,
        status: task.status,
        timestamp: task.created_at,
      }))
    initMessages(historicalMessages)
  }, [traceData, setNodeState, initMessages])

  // Build edge set: static structural + animated in-flight messages
  useEffect(() => {
    const base = makeStaticEdges()
    const active: Edge[] = edgeQueue.map((ev) => ({
      id: `active-${ev.id}`,
      source: ev.fromAgent,
      target: ev.toAgent,
      type: 'smoothstep',
      animated: true,
      style: { stroke: '#3b82f6', strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#3b82f6' },
      label: ev.messageType,
      labelStyle: { fontSize: 9, fill: '#3b82f6', fontWeight: 600 },
      labelBgStyle: { fill: '#eff6ff', fillOpacity: 0.85 },
    }))
    setEdges([...base, ...active])
  }, [edgeQueue, setEdges])

  // Auto-expire animated edges after 2 s
  useEffect(() => {
    if (edgeQueue.length === 0) return
    const timers = edgeQueue.map((ev) =>
      window.setTimeout(() => dequeueEdge(ev.id), 2000),
    )
    return () => timers.forEach(window.clearTimeout)
  }, [edgeQueue, dequeueEdge])

  const onNodeClick = useCallback<OnNodeClick>(
    (_evt, node) => {
      setSelectedAgent(node.id === selectedAgent ? null : node.id)
      setShowPanel(true)
    },
    [selectedAgent, setSelectedAgent],
  )

  const miniMapNodeColor = useCallback(
    (node: Node) => {
      const state = nodeStates[node.id] ?? 'idle'
      if (state === 'active') return '#3b82f6'
      if (state === 'escalated') return '#f59e0b'
      if (state === 'complete') return '#22c55e'
      return '#d1d5db'
    },
    [nodeStates],
  )

  const bgColor = theme === 'dark' ? '#374151' : '#e5e7eb'

  return (
    <div className="flex h-full">
      {/* ── React Flow canvas ─────────────────────────────────────────────── */}
      <div className="relative flex-1 overflow-hidden">

        {/* Mobile: "Log" button — top-right floating */}
        <button
          onClick={() => setShowPanel(true)}
          className="absolute right-3 top-3 z-10 flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white/90 px-3 py-2 text-[11px] font-medium text-gray-600 shadow-sm backdrop-blur-sm transition-colors hover:bg-white lg:hidden dark:border-gray-700 dark:bg-gray-900/90 dark:text-gray-400 dark:hover:bg-gray-800"
          aria-label="Open message log"
        >
          <List className="h-3.5 w-3.5" />
          Log
        </button>

        {/* Status legend — bottom-left floating card */}
        <div className="absolute bottom-16 left-3 z-10 flex flex-col gap-1 rounded-lg border border-gray-200 bg-white/90 px-3 py-2 text-[9px] shadow-sm backdrop-blur-sm dark:border-gray-700 dark:bg-gray-900/90">
          {(
            [
              { color: 'bg-gray-300', label: 'Idle' },
              { color: 'bg-blue-500', label: 'Active' },
              { color: 'bg-amber-500', label: 'Escalated' },
              { color: 'bg-green-500', label: 'Complete' },
            ] as const
          ).map(({ color, label }) => (
            <div key={label} className="flex items-center gap-1.5">
              <span className={['h-2 w-2 rounded-full', color].join(' ')} />
              <span className="text-gray-600 dark:text-gray-400">{label}</span>
            </div>
          ))}
        </div>

        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onNodeClick={onNodeClick}
          nodeTypes={NODE_TYPES}
          fitView
          fitViewOptions={{ padding: 0.25 }}
          colorMode={theme === 'dark' ? 'dark' : 'light'}
          className={theme === 'dark' ? 'bg-gray-900' : 'bg-gray-50'}
        >
          <Background color={bgColor} gap={16} />
          <Controls />
          <MiniMap nodeColor={miniMapNodeColor} className="hidden sm:block !bottom-4 !right-4" />
        </ReactFlow>
      </div>

      {/* ── Right panel: agent detail + message log ───────────────────────── */}

      {/* Mobile backdrop */}
      {showPanel && (
        <div
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
          onClick={() => setShowPanel(false)}
          aria-hidden="true"
        />
      )}

      <div
        className={[
          'fixed inset-y-0 right-0 z-40 flex w-full flex-col border-l border-gray-200 bg-white shadow-xl dark:border-gray-700 dark:bg-gray-800',
          'transition-transform duration-300 ease-in-out sm:w-80',
          showPanel ? 'translate-x-0' : 'translate-x-full',
          'lg:relative lg:inset-auto lg:z-auto lg:w-80 lg:translate-x-0 lg:shadow-none lg:transition-none',
        ].join(' ')}
        aria-label="Agent log panel"
      >
        {/* Mobile panel header with close button */}
        <div className="flex shrink-0 items-center justify-between border-b border-gray-100 px-4 py-2.5 lg:hidden dark:border-gray-700">
          <p className="text-xs font-semibold text-gray-700 dark:text-gray-300">Agent Log</p>
          <button
            onClick={() => setShowPanel(false)}
            className="rounded p-1 text-gray-400 transition-colors hover:text-gray-600 dark:hover:text-gray-300"
            aria-label="Close agent log"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {selectedAgent ? (
          <AgentDetailPopover
            agentId={selectedAgent}
            traceData={traceData}
            onClose={() => setSelectedAgent(null)}
          />
        ) : (
          <div className="border-b border-gray-100 px-4 py-3 dark:border-gray-700">
            <p className="text-[11px] text-gray-400">
              Click an agent node to inspect its tasks and current state.
            </p>
          </div>
        )}
        <div className="min-h-0 flex-1">
          <MessageLog />
        </div>
      </div>
    </div>
  )
}
