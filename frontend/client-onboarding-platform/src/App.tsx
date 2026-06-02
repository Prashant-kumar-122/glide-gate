import '@mantine/core/styles.css';
import '@mantine/notifications/styles.css';
import { MantineProvider } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import { QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider } from 'react-router-dom';
import { queryClient } from './lib/queryClient';
import { AuthProvider } from './store/AuthContext';
import { NotificationProvider } from './store/NotificationContext';
import { ActivityProvider } from './store/ActivityContext';
import { router } from './router';

export default function App() {
  return (
    <MantineProvider defaultColorScheme="dark">
      <Notifications position="top-right" />
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <NotificationProvider>
            <ActivityProvider>
              <RouterProvider router={router} />
            </ActivityProvider>
          </NotificationProvider>
        </AuthProvider>
      </QueryClientProvider>
    </MantineProvider>
  );
}
