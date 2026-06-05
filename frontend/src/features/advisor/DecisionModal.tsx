import { useState } from 'react'
import { ShieldCheck, ShieldX, Info } from 'lucide-react'

export type Decision = 'APPROVED' | 'REJECTED' | 'MORE_INFO_REQUESTED'

interface DecisionModalProps {
  type: Decision
  onConfirm: (notes: string) => void
  onCancel: () => void
  isLoading: boolean
}

export default function DecisionModal({ type, onConfirm, onCancel, isLoading }: DecisionModalProps) {
  const [notes, setNotes] = useState('')

  const cfg = {
    APPROVED: {
      title: 'Approve — Initiate KYC',
      desc: 'Approving will trigger the KYC compliance check immediately.',
      icon: <ShieldCheck className="h-5 w-5 text-emerald-500" />,
      btn: 'bg-emerald-600 hover:bg-emerald-700 text-white',
      label: 'Confirm Approval',
      required: false,
      placeholder: 'Optional approval notes…',
    },
    REJECTED: {
      title: 'Reject Application',
      desc: 'The case will be moved back to review and the advisor notified.',
      icon: <ShieldX className="h-5 w-5 text-red-500" />,
      btn: 'bg-red-600 hover:bg-red-700 text-white',
      label: 'Confirm Rejection',
      required: true,
      placeholder: 'Reason for rejection (required)…',
    },
    MORE_INFO_REQUESTED: {
      title: 'Request More Information',
      desc: 'The case will be held pending additional information from the client or advisor.',
      icon: <Info className="h-5 w-5 text-sky-500" />,
      btn: 'bg-sky-600 hover:bg-sky-700 text-white',
      label: 'Send Request',
      required: true,
      placeholder: 'Describe what additional information is needed (required)…',
    },
  }[type]

  const canSubmit = !cfg.required || notes.trim().length > 3

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="w-full max-w-md mx-4 border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900 p-6 max-h-[90dvh] overflow-y-auto">
        <div className="flex items-start gap-3 mb-4">
          {cfg.icon}
          <div>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">{cfg.title}</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{cfg.desc}</p>
          </div>
        </div>
        <textarea
          className="w-full h-24 border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-gray-100 placeholder:text-gray-400 resize-none focus:outline-none focus:ring-1 focus:ring-primary"
          placeholder={cfg.placeholder}
          value={notes}
          onChange={e => setNotes(e.target.value)}
        />
        <div className="flex gap-2 mt-4 justify-end">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-xs font-medium border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            Cancel
          </button>
          <button
            disabled={!canSubmit || isLoading}
            onClick={() => onConfirm(notes.trim())}
            className={`px-4 py-2 text-xs font-semibold transition-colors disabled:opacity-40 ${cfg.btn}`}
          >
            {isLoading ? 'Processing…' : cfg.label}
          </button>
        </div>
      </div>
    </div>
  )
}
