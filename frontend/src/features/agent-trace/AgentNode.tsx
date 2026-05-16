import { Handle, Position } from '@xyflow/react'
import type { NodeProps } from '@xyflow/react'
import {
  GitBranch,
  MessageSquare,
  ShieldCheck,
  FileSearch,
  Package,
  Users,
  PhoneCall,
  Bell,
} from 'lucide-react'
import type { AgentNodeState } from '@/store/traceStore'

export type AgentNodeData = {
  label: string
  agentId: string
  nodeState: AgentNodeState
}

const AGENT_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  orchestrator: GitBranch,
  customer_service: MessageSquare,
  kyc_compliance: ShieldCheck,
  document_intelligence: FileSearch,
  product_onboarding: Package,
  product_onboarding_cash: Package,
  product_onboarding_retirement: Package,
  collaboration: Users,
  contact_centre: PhoneCall,
  notification: Bell,
}

const STATE_STYLES: Record<
  AgentNodeState,
  { wrapper: string; icon: string; dot: string; badge: string }
> = {
  idle: {
    wrapper: 'border-gray-300 bg-white',
    icon: 'text-gray-400',
    dot: 'bg-gray-300',
    badge: 'bg-gray-100 text-gray-500',
  },
  active: {
    wrapper: 'border-blue-400 bg-blue-50',
    icon: 'text-blue-600',
    dot: 'bg-blue-500 animate-pulse',
    badge: 'bg-blue-100 text-blue-700',
  },
  escalated: {
    wrapper: 'border-amber-400 bg-amber-50',
    icon: 'text-amber-600',
    dot: 'bg-amber-500 animate-pulse',
    badge: 'bg-amber-100 text-amber-700',
  },
  complete: {
    wrapper: 'border-green-400 bg-green-50',
    icon: 'text-green-600',
    dot: 'bg-green-500',
    badge: 'bg-green-100 text-green-700',
  },
}

export function AgentNode({ data, selected }: NodeProps) {
  const { label, agentId, nodeState } = data as AgentNodeData
  const Icon = AGENT_ICONS[agentId] ?? GitBranch
  const s = STATE_STYLES[nodeState ?? 'idle']

  return (
    <div
      className={[
        'relative flex w-36 flex-col items-center gap-1.5 rounded-xl border-2 px-3 py-2.5 shadow-sm transition-all duration-300',
        s.wrapper,
        selected ? 'ring-2 ring-blue-400 ring-offset-1' : '',
      ].join(' ')}
    >
      <Handle
        type="target"
        position={Position.Top}
        style={{ background: '#9ca3af', borderColor: '#d1d5db', width: 8, height: 8 }}
      />

      {/* Status dot */}
      <span
        className={['absolute right-2 top-2 h-2 w-2 rounded-full transition-colors', s.dot].join(' ')}
      />

      <Icon className={['h-5 w-5 transition-colors', s.icon].join(' ')} />

      <span className="text-center text-[11px] font-semibold leading-tight text-gray-700">
        {label}
      </span>

      <span
        className={[
          'rounded-full px-1.5 py-0.5 text-[9px] font-medium capitalize',
          s.badge,
        ].join(' ')}
      >
        {nodeState ?? 'idle'}
      </span>

      <Handle
        type="source"
        position={Position.Bottom}
        style={{ background: '#9ca3af', borderColor: '#d1d5db', width: 8, height: 8 }}
      />
    </div>
  )
}
