import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { getSocket } from '@/lib/socket'
import { useWorkspaceStore } from '@/store/workspaceStore'
import {
  applyDocumentStatusUpdate,
  applyDocumentUploaded,
  applyValidationResult,
  qk,
} from '@/hooks/useDocuments'
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
} as const


export function useWorkspaceSocket(caseId: string | null) {
  const qc = useQueryClient()
  const setSocketConnected = useWorkspaceStore((s) => s.setSocketConnected)
  const incrementBadge = useWorkspaceStore((s) => s.incrementBadge)
  const joinedRoom = useRef<string | null>(null)

  useEffect(() => {
    const socket = getSocket()

    function onConnect() {
      setSocketConnected(true)
    }
    function onDisconnect() {
      setSocketConnected(false)
    }

    socket.on('connect', onConnect)
    socket.on('disconnect', onDisconnect)
    if (socket.connected) setSocketConnected(true)

    return () => {
      socket.off('connect', onConnect)
      socket.off('disconnect', onDisconnect)
    }
  }, [setSocketConnected])

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

    socket.on(EVENTS.DOCUMENT_STATUS_CHANGED, onDocStatusChanged)
    socket.on(EVENTS.DOCUMENT_UPLOADED, onDocUploaded)
    socket.on(EVENTS.PRODUCT_TRACK_UPDATE, onProductTrackUpdate)
    socket.on(EVENTS.PROGRESS_UPDATE, onProgressUpdate)
    socket.on(EVENTS.CASE_STAGE_CHANGED, onCaseStageChanged)
    socket.on(EVENTS.KYC_RESULT, onKycResult)
    socket.on(EVENTS.TASK_COMPLETE, onTaskComplete)

    return () => {
      socket.off(EVENTS.DOCUMENT_STATUS_CHANGED, onDocStatusChanged)
      socket.off(EVENTS.DOCUMENT_UPLOADED, onDocUploaded)
      socket.off(EVENTS.PRODUCT_TRACK_UPDATE, onProductTrackUpdate)
      socket.off(EVENTS.PROGRESS_UPDATE, onProgressUpdate)
      socket.off(EVENTS.CASE_STAGE_CHANGED, onCaseStageChanged)
      socket.off(EVENTS.KYC_RESULT, onKycResult)
      socket.off(EVENTS.TASK_COMPLETE, onTaskComplete)
      socket.emit('leave_case_room', { case_id: caseId })
      joinedRoom.current = null
    }
  }, [caseId, qc, incrementBadge])
}
