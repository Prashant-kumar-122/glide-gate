import { useState, useEffect } from 'react'
import { Save, CheckCircle } from 'lucide-react'
import { useLLMConfig, useUpdateLLMConfig } from '@/hooks/useLLMConfig'
import type { LLMConfig } from '@/lib/api'

const PROVIDERS: { value: LLMConfig['provider']; label: string; models: string[] }[] = [
  {
    value: 'anthropic',
    label: 'Anthropic',
    models: ['claude-sonnet-4-6', 'claude-opus-4-7', 'claude-haiku-4-5-20251001'],
  },
  {
    value: 'openai',
    label: 'OpenAI',
    models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'],
  },
  {
    value: 'google',
    label: 'Google Gemini',
    models: ['gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-2.0-flash'],
  },
  {
    value: 'local',
    label: 'Local (OpenAI-compat)',
    models: ['llama-3.1-8b', 'mistral-7b', 'qwen2.5-7b'],
  },
]

export default function LLMProviderConfig() {
  const { data: config } = useLLMConfig()
  const update = useUpdateLLMConfig()

  const [provider, setProvider] = useState<LLMConfig['provider']>('anthropic')
  const [model, setModel] = useState('claude-sonnet-4-6')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (config) {
      setProvider(config.provider)
      setModel(config.model)
    }
  }, [config])

  const selectedProvider = PROVIDERS.find((p) => p.value === provider)

  function handleSave() {
    update.mutate(
      { provider, model },
      {
        onSuccess: () => {
          setSaved(true)
          setTimeout(() => setSaved(false), 2000)
        },
      },
    )
  }

  return (
    <div className="max-w-xl space-y-6">
      <div>
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">LLM Provider</h3>
        <p className="mt-0.5 text-xs text-gray-500">
          Primary AI provider for all agent LLM calls. Fallback chain is configured in code.
        </p>
      </div>

      {/* Provider selector */}
      <div className="space-y-2">
        <label className="text-xs font-medium text-gray-700 dark:text-gray-300">Provider</label>
        <div className="grid grid-cols-2 gap-2">
          {PROVIDERS.map((p) => (
            <button
              key={p.value}
              onClick={() => {
                setProvider(p.value)
                setModel(p.models[0])
              }}
              className={[
                'border px-4 py-3 text-left text-sm font-medium transition-all',
                provider === p.value
                  ? 'border-primary bg-blue-50 text-primary ring-1 ring-primary dark:bg-primary-subtle dark:text-blue-300'
                  : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300 hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200 dark:hover:border-gray-600 dark:hover:bg-gray-700',
              ].join(' ')}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Model selector */}
      <div className="space-y-2">
        <label className="text-xs font-medium text-gray-700 dark:text-gray-300">Model</label>
        <div className="space-y-1.5">
          {selectedProvider?.models.map((m) => (
            <label
              key={m}
              className={[
                'flex cursor-pointer items-center gap-3 border px-3 py-2.5 transition-all',
                model === m
                  ? 'border-primary bg-blue-50 dark:border-primary dark:bg-primary-subtle'
                  : 'border-gray-200 hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-700',
              ].join(' ')}
            >
              <input
                type="radio"
                name="model"
                value={m}
                checked={model === m}
                onChange={() => setModel(m)}
                className="accent-blue-600"
              />
              <span className="font-mono text-xs text-gray-700 dark:text-gray-200">{m}</span>
            </label>
          ))}
        </div>
        {/* Custom model */}
        <div className="mt-2">
          <input
            type="text"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            placeholder="Or type a custom model ID…"
            className="w-full border border-gray-200 px-3 py-2 font-mono text-xs text-gray-700 placeholder-gray-300 outline-none focus:border-primary focus:ring-1 focus:ring-primary dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200 dark:placeholder-gray-600"
          />
        </div>
      </div>

      {/* Save */}
      <button
        onClick={handleSave}
        disabled={update.isPending}
        className={[
          'flex items-center gap-2 px-4 py-2 text-sm font-medium text-white transition-all',
          saved
            ? 'bg-green-500'
            : 'bg-blue-600 hover:bg-blue-700 disabled:opacity-60',
        ].join(' ')}
      >
        {saved ? (
          <CheckCircle className="h-4 w-4" />
        ) : (
          <Save className="h-4 w-4" />
        )}
        {saved ? 'Saved!' : update.isPending ? 'Saving…' : 'Save Provider Config'}
      </button>
    </div>
  )
}
