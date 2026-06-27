import { useState, useEffect } from 'react'
import { Save, CheckCircle, Eye, EyeOff } from 'lucide-react'
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
  const [apiKey, setApiKey] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (config) {
      setProvider(config.provider)
      setModel(config.model)
      setApiKey('')
    }
  }, [config])

  const selectedProvider = PROVIDERS.find((p) => p.value === provider)

  function handleSave() {
    const payload: Partial<LLMConfig> = { provider, model }
    if (apiKey.trim()) payload.api_key = apiKey.trim()
    update.mutate(payload, {
      onSuccess: () => {
        setApiKey('')
        setSaved(true)
        setTimeout(() => setSaved(false), 2000)
      },
    })
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
                setApiKey('')
                setShowKey(false)
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

      {/* API Key — not shown for local provider */}
      {provider !== 'local' && (
        <div className="space-y-2">
          <label className="text-xs font-medium text-gray-700 dark:text-gray-300">API Key</label>
          <div className="relative">
            <input
              type={showKey ? 'text' : 'password'}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={
                config?.api_key_configured
                  ? 'Configured — leave blank to keep'
                  : 'Enter API key…'
              }
              className="w-full border border-gray-200 px-3 py-2 pr-9 font-mono text-xs text-gray-700 placeholder-gray-400 outline-none focus:border-primary focus:ring-1 focus:ring-primary dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200 dark:placeholder-gray-500"
            />
            <button
              type="button"
              onClick={() => setShowKey((v) => !v)}
              className="absolute inset-y-0 right-2 flex items-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              {showKey ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
            </button>
          </div>
          {config?.api_key_configured && (
            <p className="text-xs text-green-600 dark:text-green-400">
              ✓ API key configured
            </p>
          )}
        </div>
      )}

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
