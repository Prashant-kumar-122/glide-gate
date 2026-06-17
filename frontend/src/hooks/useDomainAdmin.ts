import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'

// ── Types ─────────────────────────────────────────────────────────────────────

export interface DomainOut {
  id: string
  domain_code: string
  display_name: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface StageOut {
  id: string
  domain_id: string
  stage_code: string
  display_name: string
  is_terminal: boolean
  is_human_pending: boolean
}

export interface TransitionOut {
  id: string
  domain_id: string
  from_stage: string
  to_stage: string
}

export interface TaskRoutingOut {
  id: string
  domain_id: string
  stage_code: string
  target_agent: string
  task_type: string
  priority: string
  payload_template: Record<string, unknown>
  notification_templates: Record<string, unknown>
}

export interface AgentRosterOut {
  id: string
  domain_id: string
  agent_id: string
  agent_class: string
  status: 'APPROVED' | 'DEPRECATED'
}

export interface AgentCapabilitiesOut {
  id: string
  domain_id: string
  agent_id: string
  subscribed_task_types: string[]
  emitted_task_types: string[]
  allowed_handoff_targets: string[]
}

export interface AgentPromptOut {
  id: string
  domain_id: string
  agent_id: string
  prompt_role: string
  prompt_text: string
}

export interface AgentSkillOut {
  id: string
  domain_id: string
  agent_id: string
  skill_id: string
  bound_parameters: Record<string, unknown>
}

export interface AgentToolGrantOut {
  id: string
  domain_id: string
  agent_id: string
  connector_id: string
  tool_name: string
}

export interface ProductOut {
  id: string
  domain_id: string
  product_code: string
  display_name: string
  product_type: string
  is_active: boolean
  suitability_criteria: Record<string, unknown>
  required_documents: string[]
  activation_criteria: Record<string, unknown>
  extra_metadata: Record<string, unknown>
}

export interface PipelineStepOut {
  id: string
  domain_id: string
  product_code: string
  step_id: string
  step_label: string
  step_order: number
  is_parallel: boolean
  step_config: Record<string, unknown>
}

export interface SLAOut {
  id: string
  domain_id: string
  stage_code: string
  priority_tier: string | null
  product_code: string | null
  is_enabled: boolean
  window_hours: number
  warning_pct: number
  escalation_pct: number
  warning_task_type: string
  escalation_task_type: string
  escalation_target_agent: string
  pause_on_human_review: boolean
}

export interface SLAHealthEntry {
  case_id: string
  stage_code: string
  started_at: string
  net_elapsed_seconds: number
  window_hours: number | null
  warning_pct: number | null
  escalation_pct: number | null
  warning_sent: boolean
  breach_triggered: boolean
  pct_elapsed: number | null
}

export interface PersonaOut {
  id: string
  domain_id: string
  persona_code: string
  display_label: string
  color: string
  default_route: string
  nav_links: unknown[]
}

export interface PermissionOut {
  id: string
  domain_id: string
  persona_code: string
  permission_scope: string
}

export interface DomainValidationResult {
  valid: boolean
  errors: string[]
}

// ── Domain hooks ──────────────────────────────────────────────────────────────

export function useDomains() {
  return useQuery<DomainOut[]>({
    queryKey: ['admin', 'domains'],
    queryFn: () => api.get('/admin/domains').then((r) => r.data),
  })
}

export function useCreateDomain() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { domain_code: string; display_name: string; is_active?: boolean }) =>
      api.post('/admin/domains', body).then((r) => r.data as DomainOut),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'domains'] }),
  })
}

export function useUpdateDomain() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string; display_name?: string; is_active?: boolean }) =>
      api.put(`/admin/domains/${id}`, body).then((r) => r.data as DomainOut),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'domains'] }),
  })
}

export function useDeleteDomain() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.delete(`/admin/domains/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'domains'] }),
  })
}

export function useValidateDomain() {
  return useMutation({
    mutationFn: (id: string) =>
      api.post(`/admin/domains/${id}/validate`).then((r) => r.data as DomainValidationResult),
  })
}

export function useActivateDomain() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      api.post(`/admin/domains/${id}/activate`).then((r) => r.data as DomainOut),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'domains'] }),
  })
}

export function useDeactivateDomain() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      api.post(`/admin/domains/${id}/deactivate`).then((r) => r.data as DomainOut),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'domains'] }),
  })
}

// ── Stage hooks ───────────────────────────────────────────────────────────────

export function useStages(domainId: string | null) {
  return useQuery<StageOut[]>({
    queryKey: ['admin', 'domains', domainId, 'stages'],
    queryFn: () => api.get(`/admin/domains/${domainId}/stages`).then((r) => r.data),
    enabled: !!domainId,
  })
}

export function useCreateStage(domainId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { stage_code: string; display_name: string; is_terminal?: boolean; is_human_pending?: boolean }) =>
      api.post(`/admin/domains/${domainId}/stages`, body).then((r) => r.data as StageOut),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'domains', domainId, 'stages'] }),
  })
}

export function useUpdateStage(domainId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string; display_name?: string; is_terminal?: boolean; is_human_pending?: boolean }) =>
      api.put(`/admin/domains/${domainId}/stages/${id}`, body).then((r) => r.data as StageOut),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'domains', domainId, 'stages'] }),
  })
}

export function useDeleteStage(domainId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (stageId: string) => api.delete(`/admin/domains/${domainId}/stages/${stageId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'domains', domainId, 'stages'] }),
  })
}

export function useTransitions(domainId: string | null) {
  return useQuery<TransitionOut[]>({
    queryKey: ['admin', 'domains', domainId, 'transitions'],
    queryFn: () => api.get(`/admin/domains/${domainId}/transitions`).then((r) => r.data),
    enabled: !!domainId,
  })
}

export function useCreateTransition(domainId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { from_stage: string; to_stage: string }) =>
      api.post(`/admin/domains/${domainId}/transitions`, body).then((r) => r.data as TransitionOut),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'domains', domainId, 'transitions'] }),
  })
}

export function useDeleteTransition(domainId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (transitionId: string) => api.delete(`/admin/domains/${domainId}/transitions/${transitionId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'domains', domainId, 'transitions'] }),
  })
}

export function useTaskRouting(domainId: string | null) {
  return useQuery<TaskRoutingOut[]>({
    queryKey: ['admin', 'domains', domainId, 'task-routing'],
    queryFn: () => api.get(`/admin/domains/${domainId}/task-routing`).then((r) => r.data),
    enabled: !!domainId,
  })
}

// ── Agent hooks ───────────────────────────────────────────────────────────────

export function useAgents(domainId: string | null) {
  return useQuery<AgentRosterOut[]>({
    queryKey: ['admin', 'domains', domainId, 'agents'],
    queryFn: () => api.get(`/admin/domains/${domainId}/agents`).then((r) => r.data),
    enabled: !!domainId,
  })
}

export function useAddAgent(domainId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { agent_id: string; agent_class: string; status?: string }) =>
      api.post(`/admin/domains/${domainId}/agents`, body).then((r) => r.data as AgentRosterOut),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'domains', domainId, 'agents'] }),
  })
}

export function useUpdateAgentStatus(domainId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ agentId, status }: { agentId: string; status: string }) =>
      api.patch(`/admin/domains/${domainId}/agents/${agentId}/status`, { status }).then((r) => r.data as AgentRosterOut),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'domains', domainId, 'agents'] }),
  })
}

export function useRemoveAgent(domainId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (agentId: string) => api.delete(`/admin/domains/${domainId}/agents/${agentId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'domains', domainId, 'agents'] }),
  })
}

export function useAgentPrompts(domainId: string | null, agentId: string | null) {
  return useQuery<AgentPromptOut[]>({
    queryKey: ['admin', 'domains', domainId, 'agents', agentId, 'prompts'],
    queryFn: () =>
      api.get(`/admin/domains/${domainId}/agents/${agentId}/prompts`).then((r) => r.data),
    enabled: !!domainId && !!agentId,
  })
}

export function useUpsertPrompt(domainId: string, agentId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ prompt_role, prompt_text }: { prompt_role: string; prompt_text: string }) =>
      api
        .put(`/admin/domains/${domainId}/agents/${agentId}/prompts/${prompt_role}`, { prompt_role, prompt_text })
        .then((r) => r.data as AgentPromptOut),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['admin', 'domains', domainId, 'agents', agentId, 'prompts'] }),
  })
}

export function useDeletePrompt(domainId: string, agentId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (promptRole: string) =>
      api.delete(`/admin/domains/${domainId}/agents/${agentId}/prompts/${promptRole}`),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['admin', 'domains', domainId, 'agents', agentId, 'prompts'] }),
  })
}

export function useAgentSkills(domainId: string | null, agentId: string | null) {
  return useQuery<AgentSkillOut[]>({
    queryKey: ['admin', 'domains', domainId, 'agents', agentId, 'skills'],
    queryFn: () =>
      api.get(`/admin/domains/${domainId}/agents/${agentId}/skills`).then((r) => r.data),
    enabled: !!domainId && !!agentId,
  })
}

export function useAgentToolGrants(domainId: string | null, agentId: string | null) {
  return useQuery<AgentToolGrantOut[]>({
    queryKey: ['admin', 'domains', domainId, 'agents', agentId, 'tool-grants'],
    queryFn: () =>
      api.get(`/admin/domains/${domainId}/agents/${agentId}/tool-grants`).then((r) => r.data),
    enabled: !!domainId && !!agentId,
  })
}

export function useAddToolGrant(domainId: string, agentId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { connector_id: string; tool_name: string }) =>
      api
        .post(`/admin/domains/${domainId}/agents/${agentId}/tool-grants`, body)
        .then((r) => r.data as AgentToolGrantOut),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['admin', 'domains', domainId, 'agents', agentId, 'tool-grants'] }),
  })
}

export function useRemoveToolGrant(domainId: string, agentId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (grantId: string) =>
      api.delete(`/admin/domains/${domainId}/agents/${agentId}/tool-grants/${grantId}`),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['admin', 'domains', domainId, 'agents', agentId, 'tool-grants'] }),
  })
}

// ── Product hooks ─────────────────────────────────────────────────────────────

export function useProducts(domainId: string | null) {
  return useQuery<ProductOut[]>({
    queryKey: ['admin', 'domains', domainId, 'products'],
    queryFn: () => api.get(`/admin/domains/${domainId}/products`).then((r) => r.data),
    enabled: !!domainId,
  })
}

export function useCreateProduct(domainId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: Partial<ProductOut> & { product_code: string; display_name: string }) =>
      api.post(`/admin/domains/${domainId}/products`, body).then((r) => r.data as ProductOut),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'domains', domainId, 'products'] }),
  })
}

export function useUpdateProduct(domainId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...body }: Partial<ProductOut> & { id: string }) =>
      api.put(`/admin/domains/${domainId}/products/${id}`, body).then((r) => r.data as ProductOut),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'domains', domainId, 'products'] }),
  })
}

export function useDeleteProduct(domainId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (productId: string) => api.delete(`/admin/domains/${domainId}/products/${productId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'domains', domainId, 'products'] }),
  })
}

export function usePipeline(domainId: string | null, productCode: string | null) {
  return useQuery<PipelineStepOut[]>({
    queryKey: ['admin', 'domains', domainId, 'products', productCode, 'pipeline'],
    queryFn: () =>
      api.get(`/admin/domains/${domainId}/products/${productCode}/pipeline`).then((r) => r.data),
    enabled: !!domainId && !!productCode,
  })
}

export function useAddPipelineStep(domainId: string, productCode: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: Omit<PipelineStepOut, 'id' | 'domain_id' | 'product_code'>) =>
      api
        .post(`/admin/domains/${domainId}/products/${productCode}/pipeline`, body)
        .then((r) => r.data as PipelineStepOut),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['admin', 'domains', domainId, 'products', productCode, 'pipeline'] }),
  })
}

export function useDeletePipelineStep(domainId: string, productCode: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (stepId: string) =>
      api.delete(`/admin/domains/${domainId}/products/${productCode}/pipeline/${stepId}`),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['admin', 'domains', domainId, 'products', productCode, 'pipeline'] }),
  })
}

// ── SLA hooks ─────────────────────────────────────────────────────────────────

export function useSLAs(domainId: string | null) {
  return useQuery<SLAOut[]>({
    queryKey: ['admin', 'domains', domainId, 'slas'],
    queryFn: () => api.get(`/admin/domains/${domainId}/slas`).then((r) => r.data),
    enabled: !!domainId,
  })
}

export function useCreateSLA(domainId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: Omit<SLAOut, 'id' | 'domain_id'>) =>
      api.post(`/admin/domains/${domainId}/slas`, body).then((r) => r.data as SLAOut),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'domains', domainId, 'slas'] }),
  })
}

export function useUpdateSLA(domainId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...body }: Partial<SLAOut> & { id: string }) =>
      api.put(`/admin/domains/${domainId}/slas/${id}`, body).then((r) => r.data as SLAOut),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'domains', domainId, 'slas'] }),
  })
}

export function useDeleteSLA(domainId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (slaId: string) => api.delete(`/admin/domains/${domainId}/slas/${slaId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'domains', domainId, 'slas'] }),
  })
}

export function useSLAHealth(domainCode = 'wealth_management') {
  return useQuery<SLAHealthEntry[]>({
    queryKey: ['admin', 'sla-health', domainCode],
    queryFn: () => api.get(`/admin/sla-health?domain_code=${domainCode}`).then((r) => r.data),
    refetchInterval: 30_000,
  })
}

// ── Persona hooks ─────────────────────────────────────────────────────────────

export function usePersonas(domainId: string | null) {
  return useQuery<PersonaOut[]>({
    queryKey: ['admin', 'domains', domainId, 'personas'],
    queryFn: () => api.get(`/admin/domains/${domainId}/personas`).then((r) => r.data),
    enabled: !!domainId,
  })
}

export function useCreatePersona(domainId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: Omit<PersonaOut, 'id' | 'domain_id'>) =>
      api.post(`/admin/domains/${domainId}/personas`, body).then((r) => r.data as PersonaOut),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'domains', domainId, 'personas'] }),
  })
}

export function useUpdatePersona(domainId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...body }: Partial<PersonaOut> & { id: string }) =>
      api.put(`/admin/domains/${domainId}/personas/${id}`, body).then((r) => r.data as PersonaOut),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'domains', domainId, 'personas'] }),
  })
}

export function useDeletePersona(domainId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (personaId: string) => api.delete(`/admin/domains/${domainId}/personas/${personaId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'domains', domainId, 'personas'] }),
  })
}

export function usePermissions(domainId: string | null, personaCode: string | null) {
  return useQuery<PermissionOut[]>({
    queryKey: ['admin', 'domains', domainId, 'personas', personaCode, 'permissions'],
    queryFn: () =>
      api.get(`/admin/domains/${domainId}/personas/${personaCode}/permissions`).then((r) => r.data),
    enabled: !!domainId && !!personaCode,
  })
}

export function useAddPermission(domainId: string, personaCode: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (permission_scope: string) =>
      api
        .post(`/admin/domains/${domainId}/personas/${personaCode}/permissions`, { permission_scope })
        .then((r) => r.data as PermissionOut),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['admin', 'domains', domainId, 'personas', personaCode, 'permissions'] }),
  })
}

export function useRemovePermission(domainId: string, personaCode: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (scope: string) =>
      api.delete(`/admin/domains/${domainId}/personas/${personaCode}/permissions/${scope}`),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['admin', 'domains', domainId, 'personas', personaCode, 'permissions'] }),
  })
}
