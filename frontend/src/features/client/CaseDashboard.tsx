import { Building2, Clock, CheckCircle, Plus, FileText, Layers } from 'lucide-react'
import { useCases } from '@/hooks/useDocuments'
import CaseCard from '@/features/client/CaseCard'

interface Props {
  firstName: string
  onOpenNewAccount: () => void
  onOpenCase: (id: string) => void
}

export default function CaseDashboard({ firstName, onOpenNewAccount, onOpenCase }: Props) {
  const { data: cases = [], isLoading } = useCases()

  const inProgress = cases.filter((c) => c.current_stage !== 'COMPLETE')
  const completed = cases.filter((c) => c.current_stage === 'COMPLETE')

  const stats = [
    { label: 'In Progress',        value: inProgress.length,  icon: Clock,       color: 'text-blue-600 bg-blue-50' },
    { label: 'Completed',          value: completed.length,   icon: CheckCircle, color: 'text-emerald-600 bg-emerald-50' },
    { label: 'Total Applications', value: cases.length,       icon: Layers,      color: 'text-violet-600 bg-violet-50' },
    { label: 'Documents Pending',  value: 0,                  icon: FileText,    color: 'text-amber-600 bg-amber-50' },
  ]

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Welcome back, {firstName}</h1>
          <p className="text-gray-500 text-sm mt-1">Overview of your accounts and applications</p>
        </div>
        <button
          onClick={onOpenNewAccount}
          className="flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Open New Account
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {stats.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="rounded-2xl border border-gray-200 bg-white p-4">
            <div className={['w-10 h-10 rounded-xl flex items-center justify-center mb-3', color].join(' ')}>
              <Icon className="w-5 h-5" />
            </div>
            <div className="text-2xl font-bold text-gray-900">{value}</div>
            <div className="text-xs text-gray-500 mt-0.5">{label}</div>
          </div>
        ))}
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex justify-center py-12">
          <div className="h-7 w-7 rounded-full border-2 border-gray-200 border-t-blue-500 animate-spin" />
        </div>
      )}

      {/* In-progress cases */}
      {!isLoading && inProgress.length > 0 && (
        <div className="mb-8">
          <h2 className="text-base font-bold text-gray-900 mb-4 flex items-center gap-2">
            <Clock className="w-4 h-4 text-blue-500" />
            Applications In Progress ({inProgress.length})
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {inProgress.map((c) => (
              <CaseCard key={c.id} caseData={c} onClick={() => onOpenCase(c.id)} />
            ))}
          </div>
        </div>
      )}

      {/* Completed cases */}
      {!isLoading && completed.length > 0 && (
        <div className="mb-8">
          <h2 className="text-base font-bold text-gray-900 mb-4 flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-500" />
            Completed Accounts ({completed.length})
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {completed.map((c) => (
              <CaseCard key={c.id} caseData={c} onClick={() => onOpenCase(c.id)} />
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && cases.length === 0 && (
        <div className="rounded-2xl border border-gray-200 bg-white p-16 text-center">
          <Building2 className="w-12 h-12 text-gray-200 mx-auto mb-4" />
          <h3 className="text-gray-600 font-semibold mb-2">No accounts yet</h3>
          <p className="text-gray-400 text-sm mb-6">
            Open your first investment account to get started
          </p>
          <button
            onClick={onOpenNewAccount}
            className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Open New Account
          </button>
        </div>
      )}
    </div>
  )
}
