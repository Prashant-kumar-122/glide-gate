export const AGENT_IDS = [
  'orchestrator',
  'customer_service',
  'sales_manager',
  'kyc_compliance',
  'document_intelligence',
  'product_onboarding_cash',
  'product_onboarding_retirement',
  'collaboration',
  'contact_centre',
  'notification',
] as const

export type AgentId = (typeof AGENT_IDS)[number]

export const AGENT_LABELS: Record<AgentId, string> = {
  orchestrator: 'Orchestrator',
  customer_service: 'Customer Service',
  sales_manager: 'Sales Manager',
  kyc_compliance: 'KYC Compliance',
  document_intelligence: 'Doc Intelligence',
  product_onboarding_cash: 'Cash Account Track',
  product_onboarding_retirement: 'Retirement Track',
  collaboration: 'Collaboration',
  contact_centre: 'Contact Centre',
  notification: 'Notification',
}

export const AGENT_POSITIONS: Record<AgentId, { x: number; y: number }> = {
  orchestrator:                  { x: 360, y: 20  },
  customer_service:              { x: 0,   y: 180 },
  sales_manager:                 { x: 180, y: 180 },
  kyc_compliance:                { x: 360, y: 180 },
  document_intelligence:         { x: 540, y: 180 },
  collaboration:                 { x: 720, y: 180 },
  product_onboarding_cash:       { x: 80,  y: 370 },
  product_onboarding_retirement: { x: 280, y: 370 },
  contact_centre:                { x: 480, y: 370 },
  notification:                  { x: 680, y: 370 },
}

// Back-compat map: A2A agent_id → node IDs it controls
export const AGENT_NODE_MAP: Record<string, AgentId[]> = {
  product_onboarding: ['product_onboarding_cash', 'product_onboarding_retirement'],
}

// Map product_code → node ID
export const PRODUCT_NODE_MAP: Record<string, AgentId> = {
  cash_account: 'product_onboarding_cash',
  retirement_account: 'product_onboarding_retirement',
}

export const STATIC_EDGES = [
  { id: 'e-orch-cs',    source: 'orchestrator', target: 'customer_service' },
  { id: 'e-orch-sm',    source: 'orchestrator', target: 'sales_manager' },
  { id: 'e-orch-kyc',   source: 'orchestrator', target: 'kyc_compliance' },
  { id: 'e-orch-di',    source: 'orchestrator', target: 'document_intelligence' },
  { id: 'e-orch-col',   source: 'orchestrator', target: 'collaboration' },
  { id: 'e-orch-poc',   source: 'orchestrator', target: 'product_onboarding_cash' },
  { id: 'e-orch-por',   source: 'orchestrator', target: 'product_onboarding_retirement' },
  { id: 'e-orch-cc',    source: 'orchestrator', target: 'contact_centre' },
  { id: 'e-orch-notif', source: 'orchestrator', target: 'notification' },
  { id: 'e-cs-kyc',     source: 'customer_service', target: 'kyc_compliance' },
  { id: 'e-sm-kyc',     source: 'sales_manager', target: 'kyc_compliance' },
  { id: 'e-kyc-poc',    source: 'kyc_compliance', target: 'product_onboarding_cash' },
  { id: 'e-kyc-por',    source: 'kyc_compliance', target: 'product_onboarding_retirement' },
]
