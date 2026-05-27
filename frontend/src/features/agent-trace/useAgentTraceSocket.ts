import { useEffect } from 'react'
import { getSocket } from '@/lib/socket'
import { useTraceStore } from '@/store/traceStore'
import type { AgentEdgeEvent, TraceMessage } from '@/store/traceStore'
import { useNotificationStore } from '@/store/notificationStore'
import type { NotificationRecord } from '@/store/notificationStore'
import { AGENT_NODE_MAP, PRODUCT_NODE_MAP } from './agentPositions'
import type { AgentId } from './agentPositions'

const EV = {
  AGENT_MESSAGE: 'agent_message',
  TASK_ASSIGNED: 'task_assigned',
  TASK_COMPLETE: 'task_complete',
  ESCALATION_TRIGGERED: 'escalation_triggered',
  CASE_STAGE_CHANGED: 'case_stage_changed',
  PROGRESS_UPDATE: 'progress_update',
  NOTIFICATION_SENT: 'notification_sent',
} as const

/** Resolve an A2A agent_id to one or more canvas node IDs.
 * When product_code is provided for a product_onboarding task, maps to
 * the specific product node instead of activating all product nodes.
 */
function resolveNodes(agentId: string, productCode?: string | null): string[] {
  if (agentId === 'product_onboarding' && productCode && PRODUCT_NODE_MAP[productCode]) {
    return [PRODUCT_NODE_MAP[productCode]]
  }
  return AGENT_NODE_MAP[agentId] ?? [agentId]
}

export function useAgentTraceSocket(caseId: string | null) {
  const setNodeState = useTraceStore((s) => s.setNodeState)
  const enqueueEdge = useTraceStore((s) => s.enqueueEdge)
  const appendMessage = useTraceStore((s) => s.appendMessage)
  const reset = useTraceStore((s) => s.reset)

  useEffect(() => {
    if (!caseId) return
    const socket = getSocket()
    const appendNotification = useNotificationStore.getState().appendNotification

    socket.emit('join_case_room', { case_id: caseId })

    function onAgentMessage(data: {
      from_agent?: string
      to_agent?: string
      task_type?: string
      task_id?: string
      status?: string
      product_code?: string | null
    }) {
      const fromAgent = data.from_agent ?? ''
      const toAgent = data.to_agent ?? ''
      const taskType = data.task_type ?? 'TASK'
      const id = data.task_id ?? `${Date.now()}-${Math.random()}`

      const toNodes = resolveNodes(toAgent, data.product_code)
      const primaryTo = toNodes[0] ?? toAgent

      const edge: AgentEdgeEvent = {
        id,
        fromAgent,
        toAgent: primaryTo,
        messageType: taskType,
        timestamp: new Date().toISOString(),
      }
      enqueueEdge(edge)
      toNodes.forEach((n) => setNodeState(n, 'active'))

      const msg: TraceMessage = {
        id,
        fromAgent,
        toAgent,
        taskType,
        status: data.status ?? 'IN_FLIGHT',
        timestamp: new Date().toISOString(),
      }
      appendMessage(msg)
    }

    function onTaskAssigned(data: { to_agent?: string; product_code?: string | null }) {
      if (data.to_agent) {
        resolveNodes(data.to_agent, data.product_code).forEach((n) => setNodeState(n, 'active'))
      }
    }

    function onTaskComplete(data: {
      from_agent?: string
      to_agent?: string
      task_type?: string
      status?: string
      task_id?: string
      product_code?: string | null
    }) {
      if (data.from_agent) {
        const state = data.status === 'FAILED' ? 'idle' : 'complete'
        resolveNodes(data.from_agent, data.product_code).forEach((n) => setNodeState(n, state))
      }
      if (data.task_id ?? data.task_type) {
        const msg: TraceMessage = {
          id: data.task_id ?? `${Date.now()}`,
          fromAgent: data.from_agent ?? '',
          toAgent: data.to_agent ?? '',
          taskType: data.task_type ?? 'TASK_COMPLETE',
          status: data.status ?? 'SUCCESS',
          timestamp: new Date().toISOString(),
        }
        appendMessage(msg)
      }
    }

    function onEscalation(data: { agent_id?: string }) {
      resolveNodes(data.agent_id ?? 'kyc_compliance').forEach((n) =>
        setNodeState(n, 'escalated'),
      )
      setNodeState('orchestrator', 'escalated')
    }

    function onStageChanged(data: { stage?: string }) {
      if (data.stage === 'COMPLETE') setNodeState('orchestrator', 'complete')
      else if (data.stage === 'ESCALATED') setNodeState('orchestrator', 'escalated')
      else if (data.stage) setNodeState('orchestrator', 'active')
    }

    function onNotificationSent(data: {
      notification_id?: string
      template_id?: string
      channel?: string
      subject?: string
      body_preview?: string
      priority?: string
    }) {
      const record: NotificationRecord = {
        id: data.notification_id ?? `${Date.now()}-${Math.random()}`,
        templateId: data.template_id ?? '',
        channel: (data.channel ?? 'in_app') as NotificationRecord['channel'],
        subject: data.subject ?? 'New notification',
        bodyPreview: data.body_preview ?? '',
        priority: data.priority ?? 'NORMAL',
        receivedAt: new Date().toISOString(),
        read: false,
      }
      appendNotification(record)
    }

    function onProgressUpdate(data: {
      event?: string
      products?: string[]
      results?: Array<{ product_code?: string; status?: string }>
    }) {
      if (data.event === 'parallel_products_started' && data.products) {
        data.products.forEach((pc) => {
          const nodeId = PRODUCT_NODE_MAP[pc] as AgentId | undefined
          if (nodeId) setNodeState(nodeId, 'active')
        })
      } else if (data.event === 'parallel_products_complete' && data.results) {
        data.results.forEach((r) => {
          const nodeId = r.product_code
            ? (PRODUCT_NODE_MAP[r.product_code] as AgentId | undefined)
            : undefined
          if (!nodeId) return
          const state =
            r.status === 'COMPLETE'
              ? 'complete'
              : r.status === 'FAILED' || r.status === 'UNSUITABLE'
              ? 'idle'
              : 'active'
          setNodeState(nodeId, state)
        })
      }
    }

    socket.on(EV.AGENT_MESSAGE, onAgentMessage)
    socket.on(EV.TASK_ASSIGNED, onTaskAssigned)
    socket.on(EV.TASK_COMPLETE, onTaskComplete)
    socket.on(EV.ESCALATION_TRIGGERED, onEscalation)
    socket.on(EV.CASE_STAGE_CHANGED, onStageChanged)
    socket.on(EV.PROGRESS_UPDATE, onProgressUpdate)
    socket.on(EV.NOTIFICATION_SENT, onNotificationSent)

    return () => {
      socket.off(EV.AGENT_MESSAGE, onAgentMessage)
      socket.off(EV.TASK_ASSIGNED, onTaskAssigned)
      socket.off(EV.TASK_COMPLETE, onTaskComplete)
      socket.off(EV.ESCALATION_TRIGGERED, onEscalation)
      socket.off(EV.CASE_STAGE_CHANGED, onStageChanged)
      socket.off(EV.PROGRESS_UPDATE, onProgressUpdate)
      socket.off(EV.NOTIFICATION_SENT, onNotificationSent)
      socket.emit('leave_case_room', { case_id: caseId })
      reset()
    }
  }, [caseId, setNodeState, enqueueEdge, appendMessage, reset])
}
