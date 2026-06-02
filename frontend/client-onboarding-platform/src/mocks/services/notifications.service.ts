import type { Notification, ActivityItem } from '../../types';
import { MOCK_NOTIFICATIONS, MOCK_ACTIVITIES } from '../data/cases.mock';

const delay = (ms = 300) => new Promise(r => setTimeout(r, ms));

let notifications = [...MOCK_NOTIFICATIONS];

export const notificationsService = {
  async getForUser(userId: string): Promise<Notification[]> {
    await delay();
    return notifications.filter(n => n.userId === userId).sort(
      (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
    );
  },

  async markRead(id: string): Promise<void> {
    await delay(200);
    notifications = notifications.map(n => n.id === id ? { ...n, read: true } : n);
  },

  async markAllRead(userId: string): Promise<void> {
    await delay(200);
    notifications = notifications.map(n => n.userId === userId ? { ...n, read: true } : n);
  },
};

let activities = [...MOCK_ACTIVITIES].sort(
  (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
);

export const activityService = {
  async getAll(): Promise<ActivityItem[]> {
    await delay();
    return [...activities];
  },

  async markAllSeen(): Promise<void> {
    await delay(200);
    activities = activities.map(a => ({ ...a, seen: true }));
  },

  async addActivity(item: Omit<ActivityItem, 'id' | 'seen' | 'createdAt'>): Promise<ActivityItem> {
    const newItem: ActivityItem = {
      ...item,
      id: `act-${Date.now()}`,
      seen: false,
      createdAt: new Date().toISOString(),
    };
    activities = [newItem, ...activities];
    return newItem;
  },
};
