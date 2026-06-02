import { Outlet } from 'react-router-dom';
import { IconBuildingBank } from '@tabler/icons-react';

export default function AuthLayout() {
  return (
    <div className="min-h-screen bg-bg-base flex flex-col items-center justify-center px-4">
      {/* Logo */}
      <div className="flex flex-col items-center gap-2 mb-8">
        <div className="flex items-center gap-2">
          <IconBuildingBank size={28} className="text-primary" />
          <span className="text-xl font-bold text-text-primary tracking-tight">
            ClearPath
          </span>
        </div>
        <span className="text-sm text-text-secondary tracking-widest uppercase">
          Onboarding
        </span>
      </div>

      {/* Page content */}
      <div className="w-full max-w-md">
        <Outlet />
      </div>

      {/* Footer */}
      <p className="mt-10 text-xs text-text-muted">
        &copy; {new Date().getFullYear()} ClearPath Financial. All rights reserved.
      </p>
    </div>
  );
}
