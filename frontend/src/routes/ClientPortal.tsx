import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { LogOut, Building2 } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import CaseDashboard from '@/features/client/CaseDashboard'
import OnboardingWizard from '@/features/client/OnboardingWizard'
import CaseDetailView from '@/features/client/CaseDetailView'

type PortalView = 'dashboard' | 'wizard' | 'caseDetail'

export default function ClientPortal() {
  const navigate = useNavigate()
  const { user, clearAuth } = useAuthStore()

  const [view, setView] = useState<PortalView>('dashboard')
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null)

  if (!user || user.role !== 'client') {
    navigate('/login')
    return null
  }

  function handleLogout() {
    clearAuth()
    navigate('/')
  }

  function openCase(id: string) {
    setSelectedCaseId(id)
    setView('caseDetail')
  }

  function backToDashboard() {
    setSelectedCaseId(null)
    setView('dashboard')
  }

  // Full-screen overlays (wizard + case detail) render without the shared header
  if (view === 'wizard') {
    return (
      <OnboardingWizard
        onComplete={backToDashboard}
        onCancel={backToDashboard}
      />
    )
  }

  if (view === 'caseDetail' && selectedCaseId) {
    return (
      <CaseDetailView
        caseId={selectedCaseId}
        onBack={backToDashboard}
      />
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <Building2 className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-sm text-gray-900 dark:text-white">GlideGate</span>
            <span className="text-gray-400 text-sm hidden md:block">/ Client Portal</span>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center text-sm font-bold text-gray-600 dark:text-gray-300">
                {user.firstName.charAt(0)}
              </div>
              <div className="hidden md:block">
                <div className="text-sm font-medium text-gray-900 dark:text-white">
                  {user.firstName} {user.lastName}
                </div>
                <div className="text-gray-400 text-xs">{user.email}</div>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="text-gray-400 hover:text-gray-700 dark:hover:text-white transition-colors"
              aria-label="Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Dashboard */}
      <CaseDashboard
        firstName={user.firstName}
        onOpenNewAccount={() => setView('wizard')}
        onOpenCase={openCase}
      />
    </div>
  )
}
