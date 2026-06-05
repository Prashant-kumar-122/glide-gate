import { useState, useEffect } from 'react'
import { Save, CheckCircle, Plus, X } from 'lucide-react'
import { useValidationPrompts, useUpdateValidationPrompt } from '@/hooks/useValidationPrompts'
import type { ValidationPrompt } from '@/lib/api'

const CATEGORY_LABELS: Record<string, string> = {
  identity: 'Identity',
  financial: 'Financial',
  legal: 'Legal',
  insurance: 'Insurance',
  compliance: 'Compliance',
  entity: 'Entity / Company',
}

interface EditorProps {
  prompt: ValidationPrompt
}

function CategoryEditor({ prompt }: EditorProps) {
  const update = useUpdateValidationPrompt()
  const [goal, setGoal] = useState(prompt.goal)
  const [factors, setFactors] = useState<string[]>(prompt.factors)
  const [newFactor, setNewFactor] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    setGoal(prompt.goal)
    setFactors(prompt.factors)
  }, [prompt])

  function addFactor() {
    const trimmed = newFactor.trim()
    if (trimmed && !factors.includes(trimmed)) {
      setFactors((prev) => [...prev, trimmed])
    }
    setNewFactor('')
  }

  function removeFactor(f: string) {
    setFactors((prev) => prev.filter((x) => x !== f))
  }

  function handleSave() {
    update.mutate(
      { category: prompt.category, prompt: { goal, factors } },
      {
        onSuccess: () => {
          setSaved(true)
          setTimeout(() => setSaved(false), 2000)
        },
      },
    )
  }

  return (
    <div className="space-y-4">
      {/* Goal */}
      <div className="space-y-1.5">
        <label className="text-xs font-medium text-gray-700 dark:text-gray-300">Validation Goal</label>
        <textarea
          rows={3}
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          className="w-full resize-none border border-gray-200 px-3 py-2 text-xs text-gray-700 outline-none focus:border-primary focus:ring-1 focus:ring-primary dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
          placeholder="Describe the validation objective for this document category…"
        />
      </div>

      {/* Factors */}
      <div className="space-y-1.5">
        <label className="text-xs font-medium text-gray-700 dark:text-gray-300">Check Factors</label>
        <ul className="space-y-1.5">
          {factors.map((f, i) => (
            <li key={i} className="flex items-center gap-2">
              <span className="flex h-4 w-4 shrink-0 items-center justify-center bg-blue-100 text-[8px] font-bold text-blue-600 dark:bg-blue-900 dark:text-blue-300">
                {i + 1}
              </span>
              <span className="flex-1 rounded bg-gray-50 px-2 py-1 text-xs text-gray-700 dark:bg-gray-700 dark:text-gray-200">{f}</span>
              <button
                onClick={() => removeFactor(f)}
                className="rounded p-0.5 text-gray-400 hover:bg-red-50 hover:text-red-500 dark:hover:bg-red-950"
              >
                <X className="h-3 w-3" />
              </button>
            </li>
          ))}
        </ul>

        {/* Add factor */}
        <div className="flex gap-2">
          <input
            type="text"
            value={newFactor}
            onChange={(e) => setNewFactor(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && addFactor()}
            placeholder="Add a check factor…"
            className="flex-1 border border-gray-200 px-3 py-1.5 text-xs text-gray-700 outline-none focus:border-primary focus:ring-1 focus:ring-primary dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
          />
          <button
            onClick={addFactor}
            className="flex items-center gap-1 bg-gray-100 px-2.5 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
          >
            <Plus className="h-3 w-3" />
            Add
          </button>
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
        {saved ? 'Saved!' : update.isPending ? 'Saving…' : `Save ${CATEGORY_LABELS[prompt.category] ?? prompt.category}`}
      </button>
    </div>
  )
}

export default function ValidationPromptEditor() {
  const { data: prompts, isLoading } = useValidationPrompts()
  const [activeCategory, setActiveCategory] = useState('identity')

  const categories = prompts?.map((p) => p.category) ?? Object.keys(CATEGORY_LABELS)
  const activePrompt = prompts?.find((p) => p.category === activeCategory)

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-16 animate-pulse rounded-xl bg-gray-100 dark:bg-gray-700" />
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Validation Prompts</h3>
        <p className="mt-0.5 text-xs text-gray-500">
          Editable goal and check factors for each document category. Used by the Document Intelligence Agent.
        </p>
      </div>

      <div className="flex gap-6">
        {/* Category tabs (vertical) */}
        <nav className="flex w-36 shrink-0 flex-col gap-0.5">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={[
                'px-3 py-2 text-left text-xs font-medium transition-all',
                activeCategory === cat
                  ? 'bg-blue-50 text-primary dark:bg-primary-subtle dark:text-blue-300'
                  : 'text-gray-500 hover:bg-gray-50 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-gray-200',
              ].join(' ')}
            >
              {CATEGORY_LABELS[cat] ?? cat}
            </button>
          ))}
        </nav>

        {/* Editor */}
        <div className="flex-1">
          {activePrompt ? (
            <CategoryEditor key={activePrompt.category} prompt={activePrompt} />
          ) : (
            <p className="text-xs text-gray-400">Select a category to edit its prompt.</p>
          )}
        </div>
      </div>
    </div>
  )
}
