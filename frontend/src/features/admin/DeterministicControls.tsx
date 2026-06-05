import { useState, useEffect } from 'react'
import { Save, CheckCircle, Info } from 'lucide-react'
import { useLLMConfig, useUpdateLLMConfig } from '@/hooks/useLLMConfig'
import type { LLMConfig } from '@/lib/api'

interface SliderFieldProps {
  label: string
  description: string
  value: number
  min: number
  max: number
  step: number
  onChange: (v: number) => void
}

function SliderField({ label, description, value, min, max, step, onChange }: SliderFieldProps) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <label className="text-xs font-medium text-gray-700 dark:text-gray-300">{label}</label>
          <div className="group relative">
            <Info className="h-3 w-3 text-gray-300 dark:text-gray-600" />
            <div className="absolute left-5 top-0 z-10 hidden w-52 border border-gray-200 bg-white p-2 text-[10px] text-gray-500 group-hover:block dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400">
              {description}
            </div>
          </div>
        </div>
        <span className="font-mono text-xs tabular-nums text-gray-600 dark:text-gray-400">{value.toFixed(2)}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="h-1.5 w-full cursor-pointer accent-blue-600"
      />
      <div className="flex justify-between text-[9px] text-gray-300 dark:text-gray-600">
        <span>{min}</span>
        <span>{max}</span>
      </div>
    </div>
  )
}

interface NumFieldProps {
  label: string
  description: string
  value: number
  min: number
  max: number
  step: number
  onChange: (v: number) => void
}

function NumField({ label, description, value, min, max, step, onChange }: NumFieldProps) {
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-1.5">
        <label className="text-xs font-medium text-gray-700 dark:text-gray-300">{label}</label>
        <div className="group relative">
          <Info className="h-3 w-3 text-gray-300 dark:text-gray-600" />
          <div className="absolute left-5 top-0 z-10 hidden w-52 rounded-lg border border-gray-200 bg-white p-2 text-[10px] text-gray-500 shadow-md group-hover:block dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400">
            {description}
          </div>
        </div>
      </div>
      <input
        type="number"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseInt(e.target.value, 10))}
        className="w-full border border-gray-200 px-3 py-2 font-mono text-xs text-gray-700 outline-none focus:border-primary focus:ring-1 focus:ring-primary dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
      />
    </div>
  )
}

export default function DeterministicControls() {
  const { data: config } = useLLMConfig()
  const update = useUpdateLLMConfig()

  const [vals, setVals] = useState<Pick<
    LLMConfig,
    'temperature' | 'top_p' | 'seed' | 'frequency_penalty' | 'presence_penalty' | 'max_retries' | 'cache_ttl'
  >>({
    temperature: 0.7,
    top_p: 1.0,
    seed: null as unknown as number,
    frequency_penalty: 0,
    presence_penalty: 0,
    max_retries: 3,
    cache_ttl: 300,
  })
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (config) {
      setVals({
        temperature: config.temperature,
        top_p: config.top_p,
        seed: config.seed as unknown as number,
        frequency_penalty: config.frequency_penalty,
        presence_penalty: config.presence_penalty,
        max_retries: config.max_retries,
        cache_ttl: config.cache_ttl,
      })
    }
  }, [config])

  function set<K extends keyof typeof vals>(key: K, value: (typeof vals)[K]) {
    setVals((prev) => ({ ...prev, [key]: value }))
  }

  function handleSave() {
    update.mutate(
      { ...vals, seed: vals.seed || null },
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
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Deterministic Controls</h3>
        <p className="mt-0.5 text-xs text-gray-500">
          Fine-tune LLM behaviour for consistent, reproducible outputs.
        </p>
      </div>

      <div className="space-y-5">
        <SliderField
          label="Temperature"
          description="Controls randomness. Lower = more deterministic. Range 0–2."
          value={vals.temperature}
          min={0}
          max={2}
          step={0.05}
          onChange={(v) => set('temperature', v)}
        />

        <SliderField
          label="Top-P (nucleus sampling)"
          description="Considers tokens comprising the top P probability mass. Range 0–1."
          value={vals.top_p}
          min={0}
          max={1}
          step={0.01}
          onChange={(v) => set('top_p', v)}
        />

        <SliderField
          label="Frequency Penalty"
          description="Penalises repeated tokens. Positive = less repetition. Range −2 to 2."
          value={vals.frequency_penalty}
          min={-2}
          max={2}
          step={0.1}
          onChange={(v) => set('frequency_penalty', v)}
        />

        <SliderField
          label="Presence Penalty"
          description="Encourages new topics. Positive = more diverse. Range −2 to 2."
          value={vals.presence_penalty}
          min={-2}
          max={2}
          step={0.1}
          onChange={(v) => set('presence_penalty', v)}
        />

        <div className="grid grid-cols-2 gap-4">
          <NumField
            label="Seed"
            description="Fixed seed for reproducibility. Set to 0 to disable."
            value={vals.seed ?? 0}
            min={0}
            max={2147483647}
            step={1}
            onChange={(v) => set('seed', v || (null as unknown as number))}
          />
          <NumField
            label="Max Retries"
            description="Number of retry attempts on API failure."
            value={vals.max_retries}
            min={1}
            max={10}
            step={1}
            onChange={(v) => set('max_retries', v)}
          />
        </div>

        <div>
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-gray-700 dark:text-gray-300">Cache TTL (seconds)</label>
            <span className="font-mono text-xs tabular-nums text-gray-600 dark:text-gray-400">
              {vals.cache_ttl}s ({Math.round(vals.cache_ttl / 60)}m)
            </span>
          </div>
          <input
            type="range"
            min={0}
            max={3600}
            step={60}
            value={vals.cache_ttl}
            onChange={(e) => set('cache_ttl', parseInt(e.target.value, 10))}
            className="mt-1.5 h-1.5 w-full cursor-pointer accent-blue-600"
          />
          <div className="flex justify-between text-[9px] text-gray-300 dark:text-gray-600">
            <span>0s (off)</span>
            <span>3600s (1 hr)</span>
          </div>
        </div>
      </div>

      <button
        onClick={handleSave}
        disabled={update.isPending}
        className={[
          'flex items-center gap-2 px-4 py-2 text-sm font-medium text-white transition-all',
          saved ? 'bg-green-500' : 'bg-blue-600 hover:bg-blue-700 disabled:opacity-60',
        ].join(' ')}
      >
        {saved ? <CheckCircle className="h-4 w-4" /> : <Save className="h-4 w-4" />}
        {saved ? 'Saved!' : update.isPending ? 'Saving…' : 'Save Controls'}
      </button>
    </div>
  )
}
