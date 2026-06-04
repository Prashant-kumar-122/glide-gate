export const TASK_LABELS: Record<string, string> = {
  start_onboarding: 'Starting onboarding process',
  resume_onboarding: 'Resuming onboarding process',
  advance_stage: 'Advancing to next stage',
  collect_client_data: 'Collecting client information',
  continue_conversation: 'Continuing client conversation',
  run_kyc_check: 'Running KYC compliance check',
  verify_identity: 'Verifying client identity',
  classify_document: 'Classifying uploaded document',
  validate_document: 'Validating document contents',
  extract_ocr: 'Extracting text from document (OCR)',
  compute_diff: 'Comparing document versions',
  onboard_product: 'Onboarding selected product',
  assess_suitability: 'Assessing product suitability',
  product_track_complete: 'Product track completed',
  create_collaboration_room: 'Creating collaboration room',
  add_comment: 'Adding comment to case',
  summarise_call: 'Summarising contact centre call',
  get_client_status: 'Fetching client status',
  send_notification: 'Sending notification to client',
  send_escalation_alert: 'Sending escalation alert',
  escalate: 'Escalating case for review',
  health_check: 'Agent health check',
  sales_manager_review: 'Sales Manager reviewing institutional case',
  sales_manager_decide: 'Sales Manager recording decision',
}

export function formatTaskLabel(taskType: string): string {
  return TASK_LABELS[taskType] ?? taskType.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}
