import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { LogOut, Building2, User, ChevronDown } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import CaseDashboard from '@/features/client/CaseDashboard'
import OnboardingWizard from '@/features/client/OnboardingWizard'
import CaseDetailView from '@/features/client/CaseDetailView'
import type { CaseOut } from '@/lib/api'

type View = 'dashboard' | 'wizard' | 'caseDetail'

export default function ClientPortal() {
  const navigate = useNavigate()
  const { user, clearAuth } = useAuthStore()

  const [view, setView] = useState<View>('dashboard')
  const [profileOpen, setProfileOpen] = useState(false)
  const profileRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null)
  const [resumeCaseId, setResumeCaseId] = useState<string | null>(null)
  const [resumeProducts, setResumeProducts] = useState<string[]>([])

  if (!user || user.role !== 'client') {
    navigate('/login')
    return null
  }

  function handleLogout() {
    clearAuth()
    navigate('/')
  }

  function openCase(c: CaseOut) {
    // INTAKE = still being filled → resume in the wizard
    if (c.status === 'INTAKE') {
      setResumeCaseId(c.id)
      setResumeProducts(c.selected_products ?? [])
      setView('wizard')
    } else {
      setSelectedCaseId(c.id)
      setView('caseDetail')
    }
  }

  function openWizard() {
    setResumeCaseId(null)
    setResumeProducts([])
    setView('wizard')
  }

  function backToDashboard() {
    setView('dashboard')
    setSelectedCaseId(null)
    setResumeCaseId(null)
    setResumeProducts([])
  }

  function handleWizardComplete(caseId: string) {
    setSelectedCaseId(caseId)
    setResumeCaseId(null)
    setResumeProducts([])
    setView('caseDetail')
  }

  if (view === 'wizard') {
    return (
      <OnboardingWizard
        initialCaseId={resumeCaseId ?? undefined}
        initialSelectedProducts={resumeProducts.length > 0 ? resumeProducts : undefined}
        onComplete={handleWizardComplete}
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

          <div className="relative" ref={profileRef}>
            <button
              onClick={() => setProfileOpen((o) => !o)}
              className="flex items-center gap-2 rounded-xl px-2 py-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              <div className="w-8 h-8 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center text-sm font-bold text-gray-600 dark:text-gray-300">
                {user.firstName.charAt(0)}
              </div>
              <div className="hidden md:block text-left">
                <div className="text-sm font-medium text-gray-900 dark:text-white">
                  {user.firstName} {user.lastName}
                </div>
                <div className="text-gray-400 text-xs">{user.email}</div>
              </div>
              <ChevronDown className={`w-3.5 h-3.5 text-gray-400 transition-transform ${profileOpen ? 'rotate-180' : ''}`} />
            </button>

            {profileOpen && (
              <div className="absolute right-0 mt-2 w-48 rounded-xl border border-gray-200 bg-white dark:bg-gray-800 dark:border-gray-700 shadow-lg py-1 z-50">
                <button
                  onClick={() => { setProfileOpen(false); navigate('/profile') }}
                  className="flex w-full items-center gap-2.5 px-4 py-2.5 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                >
                  <User className="w-4 h-4 text-gray-400" />
                  View Profile
                </button>
                <div className="my-1 border-t border-gray-100 dark:border-gray-700" />
                <button
                  onClick={() => { setProfileOpen(false); handleLogout() }}
                  className="flex w-full items-center gap-2.5 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  Sign Out
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Dashboard */}
      <CaseDashboard
        firstName={user.firstName}
        onOpenNewAccount={openWizard}
        onOpenCase={openCase}
      />
    </div>
  )
}
