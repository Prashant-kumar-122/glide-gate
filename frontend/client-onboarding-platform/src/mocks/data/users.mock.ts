import type { User } from '../../types';

export const MOCK_USERS: User[] = [
  { id: 'u1', email: 'client@acme.com',    fullName: 'Jordan Lee',       role: 'client',          createdAt: '2024-01-10T08:00:00Z' },
  { id: 'u2', email: 'sales@bank.com',     fullName: 'Marcus Chen',      role: 'sales',            createdAt: '2023-06-01T08:00:00Z' },
  { id: 'u3', email: 'onboard@bank.com',   fullName: 'Priya Sharma',     role: 'onboarding',       createdAt: '2023-06-01T08:00:00Z' },
  { id: 'u4', email: 'risk@bank.com',      fullName: 'David Walsh',      role: 'risk_compliance',  createdAt: '2023-06-01T08:00:00Z' },
  { id: 'u5', email: 'client2@beta.com',   fullName: 'Sophia Reeves',    role: 'client',           createdAt: '2024-03-15T08:00:00Z' },
];

export const MOCK_SALES_CONTACT = {
  name: 'Marcus Chen',
  email: 'marcus.chen@bank.com',
  phone: '+1 (212) 555-0142',
  title: 'Relationship Manager',
};
