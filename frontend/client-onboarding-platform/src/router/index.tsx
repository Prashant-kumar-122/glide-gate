import { createBrowserRouter, Navigate } from 'react-router-dom';
import { useAuth } from '../store/AuthContext';
import type { UserRole } from '../types';
import type { ReactNode } from 'react';

// Auth pages
import SignInPage from '../features/auth/pages/SignInPage';
import SignUpPage from '../features/auth/pages/SignUpPage';

// Layouts
import ClientPortalLayout from '../components/layout/ClientPortalLayout';
import InternalPortalLayout from '../components/layout/InternalPortalLayout';
import AuthLayout from '../components/layout/AuthLayout';

// Client portal pages
import ClientDashboardPage from '../features/client-portal/dashboard/ClientDashboardPage';
import OpenNewAccountPage from '../features/client-portal/onboarding/OpenNewAccountPage';
import AddProductPage from '../features/client-portal/add-product/AddProductPage';
import ApplicationTrackingPage from '../features/client-portal/application-tracking/ApplicationTrackingPage';
import EnrollmentFormPage from '../features/client-portal/enrollment/EnrollmentFormPage';
import CDDFormPage from '../features/client-portal/forms/CDDFormPage';
import TaxFormPage from '../features/client-portal/forms/TaxFormPage';
import ControllerPersonFormPage from '../features/client-portal/forms/ControllerPersonFormPage';
import SSIFormPage from '../features/client-portal/forms/SSIFormPage';

// Internal portal pages
import InternalDashboardPage from '../features/internal-portal/dashboard/InternalDashboardPage';
import CaseListPage from '../features/internal-portal/cases/CaseListPage';
import CaseDetailPage from '../features/internal-portal/cases/CaseDetailPage';
import TaskRedirect from '../features/internal-portal/tasks/TaskRedirect';
import FormDetailPage from '../features/internal-portal/forms/FormDetailPage';

function RequireAuth({ children, allowedRoles }: { children: ReactNode; allowedRoles?: UserRole[] }) {
  const { user, isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/auth/signin" replace />;
  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    return <Navigate to={user.role === 'client' ? '/client/dashboard' : '/internal/dashboard'} replace />;
  }
  return <>{children}</>;
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Navigate to="/auth/signin" replace />,
  },
  {
    path: '/auth',
    element: <AuthLayout />,
    children: [
      { path: 'signin', element: <SignInPage /> },
      { path: 'signup', element: <SignUpPage /> },
    ],
  },
  {
    path: '/client',
    element: (
      <RequireAuth allowedRoles={['client']}>
        <ClientPortalLayout />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <Navigate to="dashboard" replace /> },
      { path: 'dashboard',            element: <ClientDashboardPage /> },
      { path: 'onboarding/new',       element: <OpenNewAccountPage /> },
      { path: 'onboarding/add-product', element: <AddProductPage /> },
      { path: 'applications/:caseId', element: <ApplicationTrackingPage /> },
    ],
  },
  {
    path: '/client/enrollment/:caseId',
    element: (
      <RequireAuth allowedRoles={['client']}>
        <EnrollmentFormPage />
      </RequireAuth>
    ),
  },
  {
    path: '/client/forms/:caseId/cdd',
    element: (
      <RequireAuth allowedRoles={['client']}>
        <CDDFormPage />
      </RequireAuth>
    ),
  },
  {
    path: '/client/forms/:caseId/tax',
    element: (
      <RequireAuth allowedRoles={['client']}>
        <TaxFormPage />
      </RequireAuth>
    ),
  },
  {
    path: '/client/forms/:caseId/controller-person',
    element: (
      <RequireAuth allowedRoles={['client']}>
        <ControllerPersonFormPage />
      </RequireAuth>
    ),
  },
  {
    path: '/client/forms/:caseId/ssi',
    element: (
      <RequireAuth allowedRoles={['client']}>
        <SSIFormPage />
      </RequireAuth>
    ),
  },
  {
    path: '/internal',
    element: (
      <RequireAuth allowedRoles={['sales', 'onboarding', 'risk_compliance']}>
        <InternalPortalLayout />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <Navigate to="dashboard" replace /> },
      { path: 'dashboard',          element: <InternalDashboardPage /> },
      { path: 'cases',              element: <CaseListPage /> },
      { path: 'cases/:caseId',      element: <CaseDetailPage /> },
      { path: 'tasks/:taskId',               element: <TaskRedirect /> },
      { path: 'cases/:caseId/forms/:formId', element: <FormDetailPage /> },
    ],
  },
]);
