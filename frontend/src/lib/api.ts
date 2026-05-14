import axios from 'axios'
import type { DocumentStatus } from '@/design-system/tokens'

export const api = axios.create({ baseURL: '/api' })

// ── Domain types ─────────────────────────────────────────────────────────────

export interface ClientOut {
  id: string
  full_name: string
  email: string
  phone?: string
  created_at: string
}

export interface CaseOut {
  id: string
  client_id: string
  client_name?: string
  current_stage: string
  status: string
  selected_products: string[]
  created_at: string
  updated_at: string
}

export interface CaseSummary {
  case_id: string
  client_id: string
  client_name: string
  current_stage: string
  overall_progress: number
  documents_total: number
  documents_approved: number
  products: ProductTrack[]
  kyc_status?: string
  escalated?: boolean
}

export interface ProductTrack {
  product_code: string
  product_name: string
  progress: number
  status: string
  steps_total: number
  steps_completed: number
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
  created_at: string
  updated_at: string
}

export interface FindingResult {
  field: string
  verdict: 'pass' | 'warn' | 'fail'
  message: string
  confidence?: number
}

export interface ValidationResult {
  document_id: string
  findings: FindingResult[]
  overall_verdict: 'pass' | 'warn' | 'fail'
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
  visibility: 'ALL' | 'ADVISOR_ONLY' | 'CLIENT_VISIBLE'
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
