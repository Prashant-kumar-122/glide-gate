// ─── Auth ─────────────────────────────────────────────────────────────────────

export type UserRole = 'client' | 'sales' | 'onboarding' | 'risk_compliance';

export interface User {
  id: string;
  email: string;
  fullName: string;
  role: UserRole;
  createdAt: string;
}

// ─── Shared primitives ────────────────────────────────────────────────────────

export interface Address {
  line1: string;
  line2?: string;
  city: string;
  state: string;
  zip: string;
  country: string;
}

export interface ContactPerson {
  fullName: string;
  email: string;
  phone: string;
  title: string;
}

// ─── Org / Entity / Account hierarchy ────────────────────────────────────────

export interface Organization {
  id: string;
  name: string;
  entityIds: string[];
}

export interface Entity {
  id: string;
  organizationId: string;
  legalName: string;
  taxId: string;
  incorporationState: string;
  incorporationDate: string;
  businessType: string;
  address: Address;
  primaryContact: ContactPerson;
  accountIds: string[];
}

export type ProductType = 'PB' | 'DvP' | 'IB_CASH' | 'FCM' | 'RETIREMENT' | 'RETAIL';

export const PRODUCT_LABELS: Record<ProductType, string> = {
  PB: 'Prime Brokerage',
  DvP: 'Delivery vs Payment',
  IB_CASH: 'IB Cash',
  FCM: 'Futures Commission Merchant',
  RETIREMENT: 'Retirement Account',
  RETAIL: 'Active Retail Account',
};

export type AccountStatus = 'in_progress' | 'live' | 'suspended' | 'closed';

export interface Account {
  id: string;
  entityId: string;
  product: ProductType;
  status: AccountStatus;
  openedAt?: string;
}

// ─── Onboarding Case ──────────────────────────────────────────────────────────

export type WorkflowStage =
  | 'CLIENT_ENROLLMENT'
  | 'SALES_MANAGER_REVIEW'
  | 'KYC'
  | 'DUE_DILIGENCE'
  | 'SIGN_AND_EXECUTE'
  | 'ACCOUNT_SETUP'
  | 'LIVE';

export const WORKFLOW_STAGES: WorkflowStage[] = [
  'CLIENT_ENROLLMENT',
  'SALES_MANAGER_REVIEW',
  'KYC',
  'DUE_DILIGENCE',
  'SIGN_AND_EXECUTE',
  'ACCOUNT_SETUP',
  'LIVE',
];

export const STAGE_LABELS: Record<WorkflowStage, string> = {
  CLIENT_ENROLLMENT: 'Client Enrollment',
  SALES_MANAGER_REVIEW: 'Sales Review',
  KYC: 'KYC',
  DUE_DILIGENCE: 'Due Diligence',
  SIGN_AND_EXECUTE: 'Sign & Execute',
  ACCOUNT_SETUP: 'Account Setup',
  LIVE: 'Live',
};

export type CaseStatus = 'active' | 'pending_info' | 'approved' | 'rejected' | 'completed';

export interface CaseContact {
  firstName: string;
  lastName:  string;
  email:     string;
}

export interface Case {
  id: string;
  clientId: string;
  clientName: string;
  entityId: string;
  products: ProductType[];
  currentStage: WorkflowStage;
  status: CaseStatus;
  assignedTo?: string;
  assignedToName?: string;
  taskIds: string[];
  documentIds: string[];
  communicationIds: string[];
  createdAt: string;
  updatedAt: string;
}

// ─── Tasks ────────────────────────────────────────────────────────────────────
// Tasks are always children of a Case — a Task cannot exist without a parent Case.
// Navigation to a task must go through its parent: /internal/cases/:caseId?task=:taskId

export type TaskType =
  | 'ENROLLMENT_FORM_REVIEW'
  | 'DOCUMENT_VERIFICATION'
  | 'COMPLIANCE_CHECK'
  | 'KYC_REVIEW'
  | 'SIGN_AND_EXECUTE';

export const TASK_TYPE_LABELS: Record<TaskType, string> = {
  ENROLLMENT_FORM_REVIEW: 'Enrollment Form Review',
  DOCUMENT_VERIFICATION:  'Document Verification',
  COMPLIANCE_CHECK:       'Compliance Check',
  KYC_REVIEW:             'KYC Review',
  SIGN_AND_EXECUTE:       'Sign & Execute',
};

export type TaskStatus = 'pending' | 'in_review' | 'approved' | 'rejected' | 'info_requested';

/** A task always belongs to exactly one Case (caseId is required and immutable). */
export interface Task {
  id: string;
  /** Parent case — every task must belong to a case. */
  caseId: string;
  clientName: string;
  type: TaskType;
  /** Human-readable title shown in tabs; defaults to TASK_TYPE_LABELS[type] if omitted. */
  title?: string;
  stage: WorkflowStage;
  assignedTo: string;
  assignedToName: string;
  status: TaskStatus;
  notes?: string;
  createdAt: string;
  resolvedAt?: string;
}

// ─── Documents ────────────────────────────────────────────────────────────────

export type DocumentType =
  | 'PASSPORT'
  | 'NATIONAL_ID'
  | 'ARTICLES_OF_INCORPORATION'
  | 'PROOF_OF_ADDRESS'
  | 'TAX_FORM'
  | 'ENROLLMENT_FORM'
  | 'CDD_FORM'
  | 'CONTROL_PERSON_FORM';

export type DocumentStatus = 'uploaded' | 'under_review' | 'approved' | 'rejected';

export interface Document {
  id: string;
  caseId: string;
  type: DocumentType;
  fileName: string;
  fileSize: string;
  uploadedAt: string;
  status: DocumentStatus;
  extractedData?: Record<string, string>;
}

// ─── Forms ────────────────────────────────────────────────────────────────────

export interface EnrollmentFormData {
  legalName: string;
  taxId: string;
  incorporationDate: string;
  incorporationState: string;
  businessType: string;
  address: Address;
  primaryContact: ContactPerson;
}

export interface CDDFormData {
  natureOfBusiness: string;
  sourceOfFunds: string;
  expectedTradingVolume: string;
  jurisdictions: string[];
  pepStatus: boolean;
  sanctionsStatus: boolean;
}

export interface ControlPerson {
  fullName: string;
  title: string;
  ownershipPercentage: number;
  dateOfBirth: string;
  nationality: string;
  idDocumentType: string;
  idDocumentNumber: string;
}

export interface ControlPersonFormData {
  controlPersons: ControlPerson[];
}

// ─── Form submissions ─────────────────────────────────────────────────────────

export interface TaxFormData {
  entityName: string;
  taxIdType: string;
  taxIdNumber: string;
  taxClassification: string;
  countryOfTaxResidency: string;
  fatcaStatus: string;
  treatyCountry: string;
  treatyArticle: string;
  withholdingRate: string;
}

export interface SSIFormData {
  currency: string;
  bankName: string;
  bankAddress: string;
  swiftBic: string;
  accountNumber: string;
  accountName: string;
  correspondentBankName: string;
  correspondentSwift: string;
  correspondentAccountNumber: string;
}

export type FormType = 'ENROLLMENT' | 'CDD' | 'CONTROL_PERSON' | 'TAX' | 'SSI';
export type FormStatus = 'pending_review' | 'approved' | 'rejected';

export interface FormSubmission {
  id: string;
  caseId: string;
  type: FormType;
  status: FormStatus;
  submittedAt: string;
  data: EnrollmentFormData | CDDFormData | ControlPersonFormData | TaxFormData | SSIFormData;
}

// ─── Communication ────────────────────────────────────────────────────────────

export type MessageDirection = 'inbound' | 'outbound';

export interface CommunicationMessage {
  id: string;
  caseId: string;
  senderId: string;
  senderName: string;
  direction: MessageDirection;
  body: string;
  createdAt: string;
}

// ─── Notifications ────────────────────────────────────────────────────────────

export type NotificationEvent =
  | 'APPLICATION_SUBMITTED'
  | 'TASK_APPROVED'
  | 'TASK_REJECTED'
  | 'INFO_REQUESTED'
  | 'STAGE_CHANGED'
  | 'ACCOUNT_LIVE';

export interface Notification {
  id: string;
  userId: string;
  event: NotificationEvent;
  caseId?: string;
  message: string;
  read: boolean;
  createdAt: string;
}

// ─── Activity log ─────────────────────────────────────────────────────────────

export type ActivityType =
  | 'CASE_CREATED'
  | 'PRODUCT_ADDED'
  | 'TASK_APPROVED'
  | 'TASK_REJECTED'
  | 'TASK_INFO_REQUESTED'
  | 'STAGE_CHANGED'
  | 'COMMENT_ADDED'
  | 'DOCUMENT_UPLOADED'
  | 'FORM_SUBMITTED';

export interface ActivityItem {
  id: string;
  type: ActivityType;
  actor: string;
  title: string;
  description: string;
  caseId?: string;
  taskId?: string;
  seen: boolean;
  createdAt: string;
}

// ─── Onboarding wizard state ──────────────────────────────────────────────────

export interface OnboardingState {
  selectedProducts: ProductType[];
  uploadedDocuments: { file: File; type: DocumentType }[];
  extractedData: Record<string, string>;
  enrollmentForm: Partial<EnrollmentFormData>;
  cddForm: Partial<CDDFormData>;
  controlPersonForm: Partial<ControlPersonFormData>;
}
