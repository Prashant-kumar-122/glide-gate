import type { Case, Task, Document, CommunicationMessage, WorkflowStage, CaseStatus, FormSubmission, FormStatus, ProductType, EnrollmentFormData, CDDFormData, ControlPerson } from '../../types';
import { MOCK_CASES, MOCK_TASKS, MOCK_DOCUMENTS, MOCK_MESSAGES, MOCK_FORM_SUBMISSIONS } from '../data/cases.mock';

const delay = (ms = 400) => new Promise(r => setTimeout(r, ms));

let cases = [...MOCK_CASES];
let tasks = [...MOCK_TASKS];

export interface CaseFilters {
  status?: CaseStatus;
  stage?: WorkflowStage;
  assignedTo?: string;
  search?: string;
}

export const casesService = {
  async getCases(filters?: CaseFilters): Promise<Case[]> {
    await delay();
    let result = [...cases];
    if (filters?.status)     result = result.filter(c => c.status === filters.status);
    if (filters?.stage)      result = result.filter(c => c.currentStage === filters.stage);
    if (filters?.assignedTo) result = result.filter(c => c.assignedTo === filters.assignedTo);
    if (filters?.search)     result = result.filter(c => c.clientName.toLowerCase().includes(filters.search!.toLowerCase()));
    return result;
  },

  async getCaseById(id: string): Promise<Case | undefined> {
    await delay();
    return cases.find(c => c.id === id);
  },

  async getCasesByClientId(clientId: string): Promise<Case[]> {
    await delay();
    return cases.filter(c => c.clientId === clientId);
  },

  async submitCase(payload: Partial<Case>): Promise<Case> {
    await delay(800);
    const newCase: Case = {
      id: `case-${Date.now()}`,
      clientId: payload.clientId!,
      clientName: payload.clientName!,
      entityId: `ent-${Date.now()}`,
      products: payload.products || [],
      currentStage: 'CLIENT_ENROLLMENT',
      status: 'active',
      taskIds: [],
      documentIds: [],
      communicationIds: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    cases = [newCase, ...cases];
    return newCase;
  },

  async submitMultipleCases(payload: {
    clientId: string;
    clientName: string;
    products: ProductType[];
    entityId?: string;
    enrollmentData?: Partial<EnrollmentFormData>;
    cddData?: Partial<CDDFormData>;
    controlPersons?: ControlPerson[];
  }): Promise<Case[]> {
    await delay(900);
    const now       = new Date().toISOString();
    const entityId  = payload.entityId ?? `ent-${Date.now()}`;
    const created: Case[] = [];

    payload.products.forEach((product, idx) => {
      const caseId = `case-${Date.now()}-${idx}`;

      const newCase: Case = {
        id: caseId,
        clientId:    payload.clientId,
        clientName:  payload.clientName,
        entityId,
        products:    [product],
        currentStage: 'CLIENT_ENROLLMENT',
        status:      'active',
        taskIds:     [],
        documentIds: [],
        communicationIds: [],
        createdAt:   now,
        updatedAt:   now,
      };
      cases = [newCase, ...cases];

      // Attach shared form submissions to every case
      if (payload.enrollmentData && Object.keys(payload.enrollmentData).length > 0) {
        formSubmissions = [
          {
            id: `form-enr-${Date.now()}-${idx}`,
            caseId,
            type: 'ENROLLMENT',
            status: 'pending_review',
            submittedAt: now,
            data: payload.enrollmentData as EnrollmentFormData,
          },
          ...formSubmissions,
        ];
      }
      if (payload.cddData && Object.keys(payload.cddData).length > 0) {
        formSubmissions = [
          {
            id: `form-cdd-${Date.now()}-${idx}`,
            caseId,
            type: 'CDD',
            status: 'pending_review',
            submittedAt: now,
            data: payload.cddData as CDDFormData,
          },
          ...formSubmissions,
        ];
      }
      if (payload.controlPersons && payload.controlPersons.length > 0) {
        formSubmissions = [
          {
            id: `form-cp-${Date.now()}-${idx}`,
            caseId,
            type: 'CONTROL_PERSON',
            status: 'pending_review',
            submittedAt: now,
            data: { controlPersons: payload.controlPersons },
          },
          ...formSubmissions,
        ];
      }

      created.push(newCase);
    });

    return created;
  },

  async updateCaseStage(id: string, stage: WorkflowStage): Promise<Case> {
    await delay();
    cases = cases.map(c => c.id === id ? { ...c, currentStage: stage, updatedAt: new Date().toISOString() } : c);
    return cases.find(c => c.id === id)!;
  },
};

export const tasksService = {
  async getMyTasks(userId: string): Promise<Task[]> {
    await delay();
    return tasks.filter(t => t.assignedTo === userId);
  },

  async getTasksByCase(caseId: string): Promise<Task[]> {
    await delay();
    return tasks.filter(t => t.caseId === caseId);
  },

  async getTaskById(id: string): Promise<Task | undefined> {
    await delay();
    return tasks.find(t => t.id === id);
  },

  async getAllTasks(): Promise<Task[]> {
    await delay();
    return [...tasks];
  },

  async approveTask(id: string, notes?: string): Promise<Task> {
    await delay(600);
    tasks = tasks.map(t =>
      t.id === id ? { ...t, status: 'approved', notes, resolvedAt: new Date().toISOString() } : t
    );
    return tasks.find(t => t.id === id)!;
  },

  async rejectTask(id: string, notes?: string): Promise<Task> {
    await delay(600);
    tasks = tasks.map(t =>
      t.id === id ? { ...t, status: 'rejected', notes, resolvedAt: new Date().toISOString() } : t
    );
    return tasks.find(t => t.id === id)!;
  },

  async requestInfo(id: string, message: string): Promise<Task> {
    await delay(600);
    tasks = tasks.map(t =>
      t.id === id ? { ...t, status: 'info_requested', notes: message } : t
    );
    return tasks.find(t => t.id === id)!;
  },
};

export const documentsService = {
  async getDocumentsByCase(caseId: string): Promise<Document[]> {
    await delay();
    return MOCK_DOCUMENTS.filter(d => d.caseId === caseId);
  },

  async uploadDocument(caseId: string, file: File, type: string): Promise<Document> {
    await delay(1000);
    return {
      id: `doc-${Date.now()}`,
      caseId,
      type: type as Document['type'],
      fileName: file.name,
      fileSize: `${(file.size / 1024 / 1024).toFixed(1)} MB`,
      uploadedAt: new Date().toISOString(),
      status: 'uploaded',
    };
  },

  async extractData(docId: string): Promise<Record<string, string>> {
    await delay(1500);
    const doc = MOCK_DOCUMENTS.find(d => d.id === docId);
    return doc?.extractedData ?? {};
  },
};

let formSubmissions = [...MOCK_FORM_SUBMISSIONS];

export const formsService = {
  async getFormsByCase(caseId: string): Promise<FormSubmission[]> {
    await delay();
    const STATUS_ORDER: Record<FormStatus, number> = { pending_review: 0, rejected: 1, approved: 2 };
    return formSubmissions
      .filter(f => f.caseId === caseId)
      .sort((a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status]);
  },

  async updateFormStatus(id: string, status: FormStatus): Promise<FormSubmission> {
    await delay(400);
    formSubmissions = formSubmissions.map(f => f.id === id ? { ...f, status } : f);
    return formSubmissions.find(f => f.id === id)!;
  },
};

export const messagesService = {
  async getMessages(caseId: string): Promise<CommunicationMessage[]> {
    await delay();
    return MOCK_MESSAGES.filter(m => m.caseId === caseId);
  },

  async sendMessage(caseId: string, senderId: string, senderName: string, body: string): Promise<CommunicationMessage> {
    await delay(400);
    return {
      id: `msg-${Date.now()}`,
      caseId,
      senderId,
      senderName,
      direction: 'inbound',
      body,
      createdAt: new Date().toISOString(),
    };
  },
};
