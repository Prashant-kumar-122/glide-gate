import axios from 'axios'
import type { DocumentStatus } from '@/design-system/tokens'
import { useAuthStore } from '@/store/authStore'
import {
  getStoredToken,
  getStoredRefreshToken,
  storeToken,
  storeRefreshToken,
  refreshKeycloakToken,
  keycloakLogout,
} from '@/lib/authConfig'

export const api = axios.create({
  baseURL: '/api',
  withCredentials: true,  // attach httpOnly auth cookie on every request
})

// CSRF double-submit: read the non-httpOnly gg_csrf cookie and echo as header
// on all state-mutating requests. Matches the server-side csrf_protection middleware.
function getCsrfToken(): string | undefined {
  const match = document.cookie.match(/(?:^|;\s*)gg_csrf=([^;]+)/)
  return match?.[1]
}

api.interceptors.request.use((config) => {
  // Keycloak Bearer token (takes precedence over httpOnly cookie for SSO sessions)
  const kcToken = getStoredToken()
  if (kcToken && !config.headers['Authorization']) {
    config.headers['Authorization'] = `Bearer ${kcToken}`
  }

  const method = config.method?.toLowerCase()
  if (method && ['post', 'put', 'patch', 'delete'].includes(method)) {
    const csrf = getCsrfToken()
    if (csrf) config.headers['X-CSRF-Token'] = csrf
  }
  return config
})

const AUTH_PATHS = ['/login', '/signup']

// Serialises concurrent refresh calls so only one token exchange happens at a time.
let _refreshPromise: Promise<string> | null = null

async function _doRefresh(): Promise<string> {
  if (_refreshPromise) return _refreshPromise
  _refreshPromise = refreshKeycloakToken()
    .then(({ access_token, refresh_token }) => {
      storeToken(access_token)
      storeRefreshToken(refresh_token)
      return access_token
    })
    .finally(() => { _refreshPromise = null })
  return _refreshPromise
}

api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config as typeof err.config & { _retry?: boolean }

    // Attempt silent token refresh on 401 for Keycloak sessions only.
    // _retry flag prevents an infinite loop if the retried request also 401s.
    if (
      err?.response?.status === 401 &&
      !original._retry &&
      !AUTH_PATHS.includes(window.location.pathname) &&
      getStoredRefreshToken()
    ) {
      original._retry = true
      try {
        const newToken = await _doRefresh()
        original.headers = original.headers ?? {}
        original.headers['Authorization'] = `Bearer ${newToken}`
        return api(original)
      } catch {
        useAuthStore.getState().clearAuth()
        keycloakLogout()
        return Promise.reject(err)
      }
    }

    // No refresh token (local auth) or retry already attempted — go to login.
    if (
      err?.response?.status === 401 &&
      !AUTH_PATHS.includes(window.location.pathname)
    ) {
      useAuthStore.getState().clearAuth()
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// ── Auth types ────────────────────────────────────────────────────────────────

export interface UserOut {
  id: string
  email: string
  first_name: string
  last_name: string
  role: 'client' | 'advisor' | 'admin' | 'sales_manager'
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: UserOut
}

// ── Domain types ──────────────────────────────────────────────────────────────

export interface ClientOut {
  id: string
  full_name: string
  email: string
  phone?: string
  created_at: string
}

export interface ClientAccountOut {
  account_number: string
  product: string
  created_at: string
}

export interface CaseOut {
  id: string
  client_id: string
  client_name?: string
  case_name?: string
  current_stage: string
  status: string
  selected_products: string[]
  percentage: number
  created_at: string
  updated_at: string
  assigned_advisor_name?: string | null
}

export interface CaseSummary {
  case_id: string
  client_id: string
  client_name: string
  case_name?: string
  current_stage: string
  overall_progress: number
  questionnaire_pct: number
  documents_total: number
  documents_approved: number
  products: ProductTrack[]
  kyc_status?: string
  escalated?: boolean
  is_institutional?: boolean
}

export interface ProductTrack {
  product_code: string
  product_name: string
  progress: number
  status: string
  steps_total: number
  steps_completed: number
}

export interface OcrField {
  key: string
  value: string
  confidence: number
}

export interface OcrResult {
  fields: OcrField[]
  raw_text: string
  extraction_quality: number
}

export interface DocumentOut {
  id: string
  name: string
  category: string
  status: DocumentStatus
  version: number
  case_id: string
  client_id: string
  storage_path?: string
  checksum_sha256?: string
  has_validation_result: boolean
  has_diff: boolean
  parent_doc_id?: string
  validation_result?: ValidationResult
  diff_result?: DiffResult
  ocr_result?: OcrResult | null
  created_at: string
  updated_at: string
}

export interface FindingResult {
  field: string
  severity: 'pass' | 'warn' | 'fail'
  message: string
  confidence?: number
}

export interface ValidationResult {
  document_id: string
  findings: FindingResult[]
  overall_status: 'pass' | 'warn' | 'fail'
  validated_at: string
  prompt_version?: string
}

export interface DiffSection {
  section: string
  change_type: 'added' | 'modified' | 'removed' | 'unchanged'
  old_value?: string
  new_value?: string
}

export interface DiffResult {
  document_id: string
  parent_id: string
  similarity_ratio: number
  sections: DiffSection[]
  summary: string
  computed_at: string
}

export interface CallSummary {
  case_id: string
  summary: string
  key_points: string[]
  recommended_actions: string[]
  stage_label: string
  generated_at: string
}

export interface CollaborationComment {
  id: string
  author_name: string
  author_role: string
  body: string
  visibility: 'ALL' | 'ADVISOR_ONLY'
  document_id: string | null
  created_at: string
}

export interface AgentOut {
  id: string
  agent_type: string
  name: string
  status: string
  description?: string
  last_active?: string
}

export interface AgentTaskOut {
  id: string
  from_agent: string
  to_agent: string
  task_type: string
  status: string
  duration_ms?: number
  created_at: string
  case_id?: string
  product_code?: string | null
}

export interface AgentTraceOut {
  agents: AgentOut[]
  tasks: AgentTaskOut[]
}

export interface LLMConfig {
  provider: 'anthropic' | 'openai' | 'google' | 'local'
  model: string
  temperature: number
  top_p: number
  seed: number | null
  frequency_penalty: number
  presence_penalty: number
  max_retries: number
  cache_ttl: number
}

export interface ValidationPrompt {
  category: string
  goal: string
  factors: string[]
}

export interface ReviewOut {
  id: string
  case_id: string
  kyc_check_id: string
  reviewer_id: string | null
  reviewer_role: string | null
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'MORE_INFO_REQUESTED'
  evidence_packet: EvidencePacket
  decision: string | null
  decision_notes: string | null
  escalation_reason: string | null
  assigned_at: string
  decided_at: string | null
  created_at: string
}

export interface EvidencePacket {
  case_id: string
  client_id: string
  assembled_at: string
  kyc_result: {
    kyc_status: string
    risk_band: string
    composite_score: number
    identity_score: number
    aml_score: number
    profile_score: number
    should_escalate: boolean
    escalation_reasons: string[]
    required_documents: string[]
    verification_id?: string
    checked_at?: string
  }
  client_summary: Record<string, unknown>
  document_summary: {
    total: number
    by_status: Record<string, number>
    categories_present: string[]
    categories_missing: string[]
  }
  case_summary: {
    current_stage: string
    status: string
    selected_products: string[]
  }
}

export interface DecisionOut {
  review_id: string
  decision: string
  decided_at: string
  message: string
}

// ── Sales Manager Review types ────────────────────────────────────────────────

export interface SalesReviewDocument {
  id: string
  filename: string
  document_type: string
  status: string
  uploaded_at: string | null
}

export interface SalesReviewCaseSnapshot {
  case_id: string
  selected_products: string[]
  client_name: string
  case_name: string
  client_data: Record<string, unknown>
  product_tracks: { product_code: string; status: string }[]
  documents: SalesReviewDocument[]
  total_documents: number
  approved_documents: number
}

export interface SalesManagerReviewOut {
  id: string
  case_id: string
  reviewer_id: string | null
  reviewer_role: string | null
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'MORE_INFO_REQUESTED'
  decision: string | null
  decision_notes: string | null
  ai_risk_summary: string | null
  risk_score: number | null
  case_snapshot: SalesReviewCaseSnapshot
  assigned_at: string
  decided_at: string | null
  created_at: string
}

export interface SalesDecisionOut {
  review_id: string
  decision: string
  decided_at: string
  message: string
}

export interface ProductOut {
  id: string
  product_code: string
  name: string
  description: string | null
}

export interface AdvisorOut {
  id: string
  email: string
  first_name: string
  last_name: string
  role: string
}

export interface CheckpointRuleOut {
  rule_id: string
  description: string
  product_type: string | null
  risk_level: string | null
  account_value_band: string | null
  jurisdiction: string | null
  action: 'ESCALATE' | 'ENHANCED_DD' | 'REQUIRE_DOCUMENTS'
  required_documents: string[]
  reason_template: string
  is_builtin: boolean
}

export interface CreateCheckpointRuleRequest {
  rule_id?: string
  description: string
  product_type?: string | null
  risk_level?: string | null
  account_value_band?: string | null
  jurisdiction?: string | null
  action: 'ESCALATE' | 'ENHANCED_DD' | 'REQUIRE_DOCUMENTS'
  required_documents?: string[]
  reason_template?: string
}

// ── Document AI extraction ────────────────────────────────────────────────────

export interface AnalyseDocumentsResponse {
  extracted_fields: OcrField[]
  documents_analysed: number
  extraction_quality: number
}

export async function analyseDocuments(caseId: string): Promise<AnalyseDocumentsResponse> {
  const { data } = await api.post<AnalyseDocumentsResponse>(`/cases/${caseId}/analyse-documents`)
  return data
}

// ── Workspace Tasks ───────────────────────────────────────────────────────────

export interface TaskDocumentSnapshot {
  id: string
  filename: string
  status: string
  category: string
  storage_path: string | null
  mime_type: string | null
}

export interface TaskReviewSnapshot {
  id: string
  ai_risk_summary: string | null
  risk_score: number | null
  case_snapshot: Record<string, unknown>
  status: string
}

export interface TaskOut {
  id: string
  case_id: string
  assignee_id: string | null
  assignee_role: 'advisor' | 'sales_manager'
  task_type: 'DOCUMENT_REVIEW' | 'SALES_REVIEW'
  title: string
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'MORE_INFO_REQUESTED'
  document_id: string | null
  review_id: string | null
  decision_notes: string | null
  decided_by: string | null
  decided_at: string | null
  case_name: string | null
  client_name: string | null
  created_at: string
  updated_at: string
  document_snapshot: TaskDocumentSnapshot | null
  review_snapshot: TaskReviewSnapshot | null
}

export interface TaskDecideRequest {
  decision: 'APPROVED' | 'REJECTED' | 'MORE_INFO_REQUESTED'
  decision_notes?: string
}

export async function getTasks(role: string, caseId?: string): Promise<TaskOut[]> {
  const params: Record<string, string> = { role }
  if (caseId) params.case_id = caseId
  const { data } = await api.get<TaskOut[]>('/tasks', { params })
  return data
}

export async function getTask(taskId: string): Promise<TaskOut> {
  const { data } = await api.get<TaskOut>(`/tasks/${taskId}`)
  return data
}

export async function decideTask(taskId: string, body: TaskDecideRequest): Promise<TaskOut> {
  const { data } = await api.patch<TaskOut>(`/tasks/${taskId}/decide`, body)
  return data
}

// ── Notifications ─────────────────────────────────────────────────────────────

export interface NotificationItem {
  id: string
  template_id: string | null
  channel: string
  subject: string | null
  body_preview: string | null
  received_at: string
}

export async function fetchMyNotifications(): Promise<NotificationItem[]> {
  const { data } = await api.get<NotificationItem[]>('/notifications')
  return data
}
