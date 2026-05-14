import { useEffect, useRef } from 'react'
import { getSocket } from '@/lib/socket'
import { useTraceStore } from '@/store/traceStore'
import type { AgentEdgeEvent, TraceMessage } from '@/store/traceStore'

const EV = {
  AGENT_MESSAGE: 'agent_message',
  TASK_ASSIGNED: 'task_assigned',
  TASK_COMPLETE: 'task_complete',
  ESCALATION_TRIGGERED: 'escalation_triggered',
  CASE_STAGE_CHANGED: 'case_stage_changed',
} as const

export function useAgentTraceSocket(caseId: string | null) {
  const setNodeState = useTraceStore((s) => s.setNodeState)
  const enqueueEdge = useTraceStore((s) => s.enqueueEdge)
  const appendMessage = useTraceStore((s) => s.appendMessage)
  const reset = useTraceStore((s) => s.reset)
  const joinedRoom = useRef<string | null>(null)

  useEffect(() => {
    if (!caseId) return
    const socket = getSocket()

    if (joinedRoom.current && joinedRoom.current !== caseId) {
      socket.emit('leave_case_room', { case_id: joinedRoom.current })
      reset()
    }
    socket.emit('join_case_room', { case_id: caseId })
    joinedRoom.current = caseId

    function onAgentMessage(data: {
      from_agent?: string
      to_agent?: string
      task_type?: string
      task_id?: string
      status?: string
    }) {
      const fromAgent = data.from_agent ?? ''
      const toAgent = data.to_agent ?? ''
      const taskType = data.task_type ?? 'TASK'
      const id = data.task_id ?? `${Date.now()}-${Math.random()}`

      const edge: AgentEdgeEvent = {
        id,
        fromAgent,
        toAgent,
        messageType: taskType,
        timestamp: new Date().toISOString(),
      }
      enqueueEdge(edge)
      setNodeState(toAgent, 'active')

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

    function onTaskAssigned(data: { to_agent?: string }) {
      if (data.to_agent) setNodeState(data.to_agent, 'active')
    }

    function onTaskComplete(data: {
      from_agent?: string
      to_agent?: string
      task_type?: string
      status?: string
      task_id?: string
    }) {
      if (data.from_agent) {
        setNodeState(data.from_agent, data.status === 'FAILED' ? 'idle' : 'complete')
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
      setNodeState(data.agent_id ?? 'kyc_compliance', 'escalated')
      setNodeState('orchestrator', 'escalated')
    }

    function onStageChanged(data: { stage?: string }) {
      if (data.stage === 'COMPLETE') setNodeState('orchestrator', 'complete')
      else if (data.stage === 'ESCALATED') setNodeState('orchestrator', 'escalated')
      else if (data.stage) setNodeState('orchestrator', 'active')
    }

    socket.on(EV.AGENT_MESSAGE, onAgentMessage)
    socket.on(EV.TASK_ASSIGNED, onTaskAssigned)
    socket.on(EV.TASK_COMPLETE, onTaskComplete)
    socket.on(EV.ESCALATION_TRIGGERED, onEscalation)
    socket.on(EV.CASE_STAGE_CHANGED, onStageChanged)

    return () => {
      socket.off(EV.AGENT_MESSAGE, onAgentMessage)
      socket.off(EV.TASK_ASSIGNED, onTaskAssigned)
      socket.off(EV.TASK_COMPLETE, onTaskComplete)
      socket.off(EV.ESCALATION_TRIGGERED, onEscalation)
      socket.off(EV.CASE_STAGE_CHANGED, onStageChanged)
      socket.emit('leave_case_room', { case_id: caseId })
      joinedRoom.current = null
    }
  }, [caseId, setNodeState, enqueueEdge, appendMessage, reset])
}
