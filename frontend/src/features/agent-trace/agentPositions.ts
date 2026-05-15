export const AGENT_IDS = [
  'orchestrator',
  'customer_service',
  'kyc_compliance',
  'document_intelligence',
  'product_onboarding',
  'collaboration',
  'contact_centre',
  'notification',
] as const

export type AgentId = (typeof AGENT_IDS)[number]

export const AGENT_LABELS: Record<AgentId, string> = {
  orchestrator: 'Orchestrator',
  customer_service: 'Customer Service',
  kyc_compliance: 'KYC Compliance',
  document_intelligence: 'Doc Intelligence',
  product_onboarding: 'Product Onboarding',
  collaboration: 'Collaboration',
  contact_centre: 'Contact Centre',
  notification: 'Notification',
}

export const AGENT_POSITIONS: Record<AgentId, { x: number; y: number }> = {
  orchestrator:          { x: 305, y: 20  },
  customer_service:      { x: 20,  y: 180 },
  kyc_compliance:        { x: 200, y: 180 },
  document_intelligence: { x: 390, y: 180 },
  collaboration:         { x: 590, y: 180 },
  product_onboarding:    { x: 100, y: 360 },
  contact_centre:        { x: 340, y: 360 },
  notification:          { x: 570, y: 360 },
}

export const STATIC_EDGES = [
  { id: 'e-orch-cs',    source: 'orchestrator', target: 'customer_service' },
  { id: 'e-orch-kyc',   source: 'orchestrator', target: 'kyc_compliance' },
  { id: 'e-orch-di',    source: 'orchestrator', target: 'document_intelligence' },
  { id: 'e-orch-col',   source: 'orchestrator', target: 'collaboration' },
  { id: 'e-orch-po',    source: 'orchestrator', target: 'product_onboarding' },
  { id: 'e-orch-cc',    source: 'orchestrator', target: 'contact_centre' },
  { id: 'e-orch-notif', source: 'orchestrator', target: 'notification' },
  { id: 'e-cs-kyc',     source: 'customer_service', target: 'kyc_compliance' },
  { id: 'e-kyc-po',     source: 'kyc_compliance', target: 'product_onboarding' },
]
