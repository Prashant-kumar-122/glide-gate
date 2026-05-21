import { ShieldAlert, User, FileText, Package, AlertCircle } from 'lucide-react'
import type { EvidencePacket } from '@/lib/api'
import { useEvidencePacket } from '@/hooks/usePendingReviews'

const RISK_BAND_COLOR: Record<string, string> = {
  LOW: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
  MEDIUM: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
  HIGH: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-300',
  VERY_HIGH: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
}

interface Props {
  reviewId: string
}

export function EvidencePacketPanel({ reviewId }: Props) {
  const { data: packet, isLoading, isError } = useEvidencePacket(reviewId)

  if (isLoading) {
    return (
      <div className="p-4 space-y-3">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-24 bg-gray-100 rounded-lg animate-pulse dark:bg-gray-700" />
        ))}
      </div>
    )
  }

  if (isError || !packet) {
    return (
      <div className="p-4 text-sm text-red-600 flex items-center gap-2 dark:text-red-400">
        <AlertCircle size={16} />
        Failed to load evidence packet.
      </div>
    )
  }

  return (
    <div className="p-4 space-y-4">
      {/* KYC Scores */}
      <Section icon={<ShieldAlert size={16} className="text-amber-600" />} title="KYC Risk Assessment">
        <div className="grid grid-cols-2 gap-2 mt-2">
          <ScoreCard label="Composite" value={packet.kyc_result.composite_score} />
          <ScoreCard label="Identity" value={packet.kyc_result.identity_score} />
          <ScoreCard label="AML" value={packet.kyc_result.aml_score} />
          <ScoreCard label="Profile" value={packet.kyc_result.profile_score} />
        </div>
        <div className="mt-2 flex items-center gap-2">
          <span className="text-xs text-gray-500 dark:text-gray-400">Risk Band:</span>
          <span
            className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
              RISK_BAND_COLOR[packet.kyc_result.risk_band] ?? 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
            }`}
          >
            {packet.kyc_result.risk_band}
          </span>
        </div>
        {packet.kyc_result.escalation_reasons.length > 0 && (
          <div className="mt-2">
            <p className="text-xs font-medium text-gray-600 mb-1 dark:text-gray-300">Escalation Reasons:</p>
            <ul className="space-y-1">
              {packet.kyc_result.escalation_reasons.map((r, i) => (
                <li key={i} className="text-xs text-red-700 flex items-start gap-1 dark:text-red-400">
                  <span className="mt-0.5">•</span>
                  {r}
                </li>
              ))}
            </ul>
          </div>
        )}
      </Section>

      {/* Client Summary */}
      <Section icon={<User size={16} className="text-blue-600" />} title="Client Profile">
        <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
          {Object.entries(packet.client_summary).map(([k, v]) => (
            v != null ? (
              <div key={k} className="contents">
                <dt className="text-gray-500 capitalize dark:text-gray-400">{k.replace(/_/g, ' ')}</dt>
                <dd className="text-gray-900 font-medium truncate dark:text-gray-100">{String(v)}</dd>
              </div>
            ) : null
          ))}
        </dl>
      </Section>

      {/* Document Summary */}
      <Section icon={<FileText size={16} className="text-indigo-600" />} title="Documents">
        <div className="mt-2 text-xs space-y-1">
          <p className="text-gray-700 dark:text-gray-200">
            <span className="font-medium">{packet.document_summary.total}</span> documents on file
          </p>
          <div className="flex flex-wrap gap-1">
            {Object.entries(packet.document_summary.by_status).map(([status, count]) => (
              <span key={status} className="px-1.5 py-0.5 rounded bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-200">
                {status}: {count}
              </span>
            ))}
          </div>
          {packet.document_summary.categories_missing.length > 0 && (
            <p className="text-red-600 dark:text-red-400">
              Missing categories: {packet.document_summary.categories_missing.join(', ')}
            </p>
          )}
        </div>
      </Section>

      {/* Case Summary */}
      <Section icon={<Package size={16} className="text-purple-600" />} title="Case Details">
        <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
          <dt className="text-gray-500 dark:text-gray-400">Stage</dt>
          <dd className="text-gray-900 font-medium dark:text-gray-100">{packet.case_summary.current_stage}</dd>
          <dt className="text-gray-500 dark:text-gray-400">Status</dt>
          <dd className="text-gray-900 font-medium dark:text-gray-100">{packet.case_summary.status}</dd>
          <dt className="text-gray-500 dark:text-gray-400">Products</dt>
          <dd className="text-gray-900 font-medium dark:text-gray-100">
            {packet.case_summary.selected_products.join(', ') || '—'}
          </dd>
        </dl>
      </Section>
    </div>
  )
}

function Section({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode
  title: string
  children: React.ReactNode
}) {
  return (
    <div className="border border-gray-200 rounded-lg p-3 dark:border-gray-700">
      <div className="flex items-center gap-1.5 font-semibold text-sm text-gray-800 dark:text-gray-100">
        {icon}
        {title}
      </div>
      {children}
    </div>
  )
}

function ScoreCard({ label, value }: { label: string; value: number | null }) {
  const pct = value != null ? Math.round(Number(value) * 100) : null
  const color =
    pct == null ? 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
    : pct >= 70 ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300'
    : pct >= 40 ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300'
    : 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300'

  return (
    <div className={`rounded-md p-2 text-center ${color}`}>
      <p className="text-xs font-medium">{label}</p>
      <p className="text-lg font-bold">{pct != null ? `${pct}%` : '—'}</p>
    </div>
  )
}
