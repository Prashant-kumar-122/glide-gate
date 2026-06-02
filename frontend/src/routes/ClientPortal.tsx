import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import CaseDashboard from '@/features/client/CaseDashboard'
import OnboardingWizard from '@/features/client/OnboardingWizard'
import CaseDetailView from '@/features/client/CaseDetailView'
import type { CaseOut } from '@/lib/api'

type View = 'dashboard' | 'wizard' | 'caseDetail'

export default function ClientPortal() {
  const navigate = useNavigate()
  const { user } = useAuthStore()

  const [view, setView] = useState<View>('dashboard')
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null)
  const [resumeCaseId, setResumeCaseId] = useState<string | null>(null)
  const [resumeProducts, setResumeProducts] = useState<string[]>([])

  if (!user || user.role !== 'client') {
    navigate('/login')
    return null
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
    <CaseDashboard
      firstName={user.firstName}
      onOpenNewAccount={openWizard}
      onOpenCase={openCase}
    />
  )
}
