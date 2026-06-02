import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react';
import type { ActivityItem } from '../types';
import { activityService } from '../mocks/services/notifications.service';

interface ActivityContextValue {
  activities: ActivityItem[];
  unseenCount: number;
  markAllSeen: () => void;
  addActivity: (item: Omit<ActivityItem, 'id' | 'seen' | 'createdAt'>) => void;
}

const ActivityContext = createContext<ActivityContextValue | null>(null);

export function ActivityProvider({ children }: { children: ReactNode }) {
  const [activities, setActivities] = useState<ActivityItem[]>([]);

  useEffect(() => {
    activityService.getAll().then(setActivities);
  }, []);

  const unseenCount = activities.filter(a => !a.seen).length;

  const markAllSeen = useCallback(() => {
    activityService.markAllSeen();
    setActivities(prev => prev.map(a => ({ ...a, seen: true })));
  }, []);

  const addActivity = useCallback((item: Omit<ActivityItem, 'id' | 'seen' | 'createdAt'>) => {
    activityService.addActivity(item).then(newItem => {
      setActivities(prev => [newItem, ...prev]);
    });
  }, []);

  return (
    <ActivityContext.Provider value={{ activities, unseenCount, markAllSeen, addActivity }}>
      {children}
    </ActivityContext.Provider>
  );
}

export function useActivity() {
  const ctx = useContext(ActivityContext);
  if (!ctx) throw new Error('useActivity must be used within ActivityProvider');
  return ctx;
}
