import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { getSocket } from '@/lib/socket'
import { useWorkspaceStore } from '@/store/workspaceStore'
import { useNotificationStore } from '@/store/notificationStore'
import type { NotificationRecord } from '@/store/notificationStore'
import {
  applyDocumentStatusUpdate,
  applyDocumentUploaded,
  applyValidationResult,
  qk,
} from '@/hooks/useDocuments'
import { taskQk } from '@/hooks/useTasks'
import type { CaseSummary, ValidationResult } from '@/lib/api'

const EVENTS = {
  DOCUMENT_STATUS_CHANGED: 'document_status_changed',
  DOCUMENT_UPLOADED: 'document_uploaded',
  KYC_RESULT: 'kyc_result',
  ESCALATION_TRIGGERED: 'escalation_triggered',
  PRODUCT_TRACK_UPDATE: 'product_track_update',
  PROGRESS_UPDATE: 'progress_update',
  CASE_STAGE_CHANGED: 'case_stage_changed',
  REVIEW_DECIDED: 'review_decided',
  NOTIFICATION_SENT: 'notification_sent',
  AGENT_MESSAGE: 'agent_message',
  TASK_ASSIGNED: 'task_assigned',
  TASK_COMPLETE: 'task_complete',
  TASK_CREATED: 'task_created',
  TASK_UPDATED: 'task_updated',
} as const


export function useWorkspaceSocket(caseId: string | null) {
  const qc = useQueryClient()
  const setSocketConnected = useWorkspaceStore((s) => s.setSocketConnected)
  const incrementBadge = useWorkspaceStore((s) => s.incrementBadge)
  const appendNotification = useNotificationStore((s) => s.appendNotification)
  const joinedRoom = useRef<string | null>(null)

  useEffect(() => {
    const socket = getSocket()

    function onConnect() {
      setSocketConnected(true)
    }
    function onDisconnect() {
      setSocketConnected(false)
    }

    function onNotificationSent(data: {
      notification_id?: string
      template_id?: string
      channel?: string
      subject?: string
      body_preview?: string
      priority?: string
    }) {
      // Only show in-app notifications in the bell — email events are case-room
      // audit signals for the agent trace, not user-facing notifications
      if (data.channel !== 'in_app') return
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

    socket.on('connect', onConnect)
    socket.on('disconnect', onDisconnect)
    socket.on(EVENTS.NOTIFICATION_SENT, onNotificationSent)
    if (socket.connected) setSocketConnected(true)

    return () => {
      socket.off('connect', onConnect)
      socket.off('disconnect', onDisconnect)
      socket.off(EVENTS.NOTIFICATION_SENT, onNotificationSent)
    }
  }, [setSocketConnected, appendNotification])

  useEffect(() => {
    if (!caseId) return
    const socket = getSocket()

    // Leave previous room
    if (joinedRoom.current && joinedRoom.current !== caseId) {
      socket.emit('leave_case_room', { case_id: joinedRoom.current })
    }
    socket.emit('join_case_room', { case_id: caseId })
    joinedRoom.current = caseId

    function onDocStatusChanged(data: { document_id: string; status: string; badge_count?: number }) {
      applyDocumentStatusUpdate(qc, caseId!, data.document_id, data.status)
      qc.invalidateQueries({ queryKey: qk.caseSummary(caseId!) })
    }

    function onDocUploaded(data: { case_id: string; badge_count?: number }) {
      if (data.case_id === caseId) {
        incrementBadge(caseId!)
        applyDocumentUploaded(qc, caseId!)
      }
    }

    function onProductTrackUpdate(data: { case_id: string }) {
      if (data.case_id === caseId) {
        qc.invalidateQueries({ queryKey: qk.caseSummary(caseId!) })
      }
    }

    function onProgressUpdate(data: { case_id: string; progress?: Partial<CaseSummary> }) {
      if (data.case_id === caseId) {
        qc.invalidateQueries({ queryKey: qk.caseSummary(caseId!) })
      }
    }

    function onCaseStageChanged(data: { case_id: string }) {
      if (data.case_id === caseId) {
        qc.invalidateQueries({ queryKey: qk.caseDetail(caseId!) })
        qc.invalidateQueries({ queryKey: qk.caseSummary(caseId!) })
      }
    }

    function onKycResult(data: { case_id: string }) {
      if (data.case_id === caseId) {
        qc.invalidateQueries({ queryKey: qk.caseSummary(caseId!) })
      }
    }

    function onTaskComplete(data: { result?: { validation_result?: ValidationResult; document_id?: string } }) {
      if (data.result?.validation_result && data.result.document_id) {
        applyValidationResult(qc, data.result.document_id, data.result.validation_result)
      }
    }

    function onTaskCreated() {
      qc.invalidateQueries({ queryKey: taskQk.all })
    }
    function onTaskUpdated() {
      qc.invalidateQueries({ queryKey: taskQk.all })
    }

    socket.on(EVENTS.DOCUMENT_STATUS_CHANGED, onDocStatusChanged)
    socket.on(EVENTS.DOCUMENT_UPLOADED, onDocUploaded)
    socket.on(EVENTS.PRODUCT_TRACK_UPDATE, onProductTrackUpdate)
    socket.on(EVENTS.PROGRESS_UPDATE, onProgressUpdate)
    socket.on(EVENTS.CASE_STAGE_CHANGED, onCaseStageChanged)
    socket.on(EVENTS.KYC_RESULT, onKycResult)
    socket.on(EVENTS.TASK_COMPLETE, onTaskComplete)
    socket.on(EVENTS.TASK_CREATED, onTaskCreated)
    socket.on(EVENTS.TASK_UPDATED, onTaskUpdated)

    return () => {
      socket.off(EVENTS.DOCUMENT_STATUS_CHANGED, onDocStatusChanged)
      socket.off(EVENTS.DOCUMENT_UPLOADED, onDocUploaded)
      socket.off(EVENTS.PRODUCT_TRACK_UPDATE, onProductTrackUpdate)
      socket.off(EVENTS.PROGRESS_UPDATE, onProgressUpdate)
      socket.off(EVENTS.CASE_STAGE_CHANGED, onCaseStageChanged)
      socket.off(EVENTS.KYC_RESULT, onKycResult)
      socket.off(EVENTS.TASK_COMPLETE, onTaskComplete)
      socket.off(EVENTS.TASK_CREATED, onTaskCreated)
      socket.off(EVENTS.TASK_UPDATED, onTaskUpdated)
      socket.emit('leave_case_room', { case_id: caseId })
      joinedRoom.current = null
    }
  }, [caseId, qc, incrementBadge])
}
