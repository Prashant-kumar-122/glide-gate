import { useState } from 'react'
import { Settings, Sliders, FileText, Shield, LayoutGrid } from 'lucide-react'
import LLMProviderConfig from '@/features/admin/LLMProviderConfig'
import DeterministicControls from '@/features/admin/DeterministicControls'
import ValidationPromptEditor from '@/features/admin/ValidationPromptEditor'
import CheckpointRulesEditor from '@/features/admin/CheckpointRulesEditor'
import DomainPortal from '@/features/admin/DomainPortal'

const TABS = [
  { id: 'domain', label: 'Domain Portal', shortLabel: 'Domain', icon: LayoutGrid },
  { id: 'provider', label: 'LLM Provider', shortLabel: 'LLM', icon: Settings },
  { id: 'deterministic', label: 'Deterministic Controls', shortLabel: 'Controls', icon: Sliders },
  { id: 'prompts', label: 'Validation Prompts', shortLabel: 'Prompts', icon: FileText },
  { id: 'rules', label: 'Checkpoint Rules', shortLabel: 'Rules', icon: Shield },
] as const

type TabId = (typeof TABS)[number]['id']

export default function AdminConfig() {
  const [active, setActive] = useState<TabId>('domain')

  return (
    <div className="flex h-[calc(100vh-48px)] flex-col">
      {/* Header */}
      <div className="shrink-0 border-b border-gray-200 bg-white px-4 py-3 sm:px-6 sm:py-4 dark:border-gray-700 dark:bg-gray-800">
        <h1 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Admin Configuration</h1>
        <p className="mt-0.5 text-[11px] text-gray-400">
          Domain portal, LLM provider, deterministic controls, validation prompts, and checkpoint rules
        </p>
      </div>

      <div className="flex flex-1 flex-col overflow-hidden md:flex-row">
        {/* ── Mobile: horizontal scrollable tab bar ───────────────────────── */}
        <div
          className="flex shrink-0 overflow-x-auto border-b border-gray-200 bg-white md:hidden dark:border-gray-700 dark:bg-gray-800"
          role="tablist"
          aria-label="Admin configuration tabs"
        >
          {TABS.map(({ id, shortLabel, icon: Icon }) => (
            <button
              key={id}
              role="tab"
              aria-selected={active === id}
              onClick={() => setActive(id)}
              className={[
                'flex shrink-0 flex-col items-center gap-1 px-5 py-3 text-[11px] font-semibold transition-colors',
                active === id
                  ? 'border-b-2 border-blue-600 text-blue-700 dark:text-blue-400'
                  : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300',
              ].join(' ')}
            >
              <Icon className="h-4 w-4" />
              {shortLabel}
            </button>
          ))}
        </div>

        {/* ── Desktop: vertical tab nav sidebar ───────────────────────────── */}
        <nav
          className="hidden w-52 shrink-0 border-r border-gray-200 bg-white p-3 md:block dark:border-gray-700 dark:bg-gray-800"
          aria-label="Admin configuration navigation"
        >
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActive(id)}
              className={[
                'mb-0.5 flex w-full items-center gap-2.5 rounded-lg px-3 py-2.5 text-left text-xs font-medium transition-all',
                active === id
                  ? 'bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300'
                  : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-gray-200',
              ].join(' ')}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </button>
          ))}
        </nav>

        {/* Content area — Domain Portal fills the full pane; others scroll */}
        {active === 'domain' ? (
          <div className="flex flex-1 flex-col overflow-hidden">
            <DomainPortal />
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto p-4 md:p-8">
            {active === 'provider' && <LLMProviderConfig />}
            {active === 'deterministic' && <DeterministicControls />}
            {active === 'prompts' && <ValidationPromptEditor />}
            {active === 'rules' && <CheckpointRulesEditor />}
          </div>
        )}
      </div>
    </div>
  )
}
