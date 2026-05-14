import { useState } from 'react'
import { Settings, Sliders, FileText, Shield } from 'lucide-react'
import LLMProviderConfig from '@/features/admin/LLMProviderConfig'
import DeterministicControls from '@/features/admin/DeterministicControls'
import ValidationPromptEditor from '@/features/admin/ValidationPromptEditor'
import CheckpointRulesEditor from '@/features/admin/CheckpointRulesEditor'

const TABS = [
  { id: 'provider', label: 'LLM Provider', icon: Settings },
  { id: 'deterministic', label: 'Deterministic Controls', icon: Sliders },
  { id: 'prompts', label: 'Validation Prompts', icon: FileText },
  { id: 'rules', label: 'Checkpoint Rules', icon: Shield },
] as const

type TabId = (typeof TABS)[number]['id']

export default function AdminConfig() {
  const [active, setActive] = useState<TabId>('provider')

  return (
    <div className="flex h-[calc(100vh-48px)] flex-col">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white px-6 py-4">
        <h1 className="text-sm font-semibold text-gray-900">Admin Configuration</h1>
        <p className="mt-0.5 text-[11px] text-gray-400">
          LLM provider, deterministic controls, validation prompts, and checkpoint rules
        </p>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Vertical tab nav */}
        <nav className="w-52 shrink-0 border-r border-gray-200 bg-white p-3">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActive(id)}
              className={[
                'mb-0.5 flex w-full items-center gap-2.5 rounded-lg px-3 py-2.5 text-left text-xs font-medium transition-all',
                active === id
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700',
              ].join(' ')}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </button>
          ))}
        </nav>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-8">
          {active === 'provider' && <LLMProviderConfig />}
          {active === 'deterministic' && <DeterministicControls />}
          {active === 'prompts' && <ValidationPromptEditor />}
          {active === 'rules' && <CheckpointRulesEditor />}
        </div>
      </div>
    </div>
  )
}
