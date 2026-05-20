import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { CheckCircle, Upload, Sparkles, AlertCircle } from 'lucide-react'
import { useUploadDocument, useQuestionnaireSchema, qk } from '@/hooks/useDocuments'
import { useDocumentPrefill } from '@/hooks/useDocumentPrefill'
import type { DocumentOut } from '@/lib/api'
import type { QuestionSchemaItem } from '@/hooks/useDocuments'

const UPLOAD_CATEGORIES = [
  { id: 'identity',   label: 'Identity Document',  hint: 'Passport, National ID, Driving Licence' },
  { id: 'financial',  label: 'Financial Document',  hint: 'Bank statement, financial report' },
  { id: 'compliance', label: 'Compliance / KYC',    hint: 'KYC form, tax declaration' },
] as const

type Phase = 'upload' | 'analysing' | 'done'

interface Props {
  caseId: string
  onAnalysed: (count: number) => void
  onSkip: () => void
}

export default function DocumentUploadStep({ caseId, onAnalysed, onSkip }: Props) {
  const qc = useQueryClient()
  const uploadDocument = useUploadDocument(caseId)
  const { data: schemaData } = useQuestionnaireSchema(caseId)
  const { prefill } = useDocumentPrefill(caseId)

  const [phase, setPhase] = useState<Phase>('upload')
  const [uploaded, setUploaded] = useState<Record<string, string>>({}) // category → filename
  const [prefillCount, setPrefillCount] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const uploadedCount = Object.keys(uploaded).length

  async function handleUpload(file: File, category: string) {
    try {
      await uploadDocument.mutateAsync({ file, category })
      setUploaded((prev) => ({ ...prev, [category]: file.name }))
    } catch {
      setError(`Failed to upload ${file.name}. Please try again.`)
    }
  }

  async function handleAnalyse() {
    setPhase('analysing')
    setError(null)
    try {
      // Give the backend OCR agent time to finish (simulated: 100–600 ms)
      await new Promise((r) => setTimeout(r, 900))
      await qc.invalidateQueries({ queryKey: qk.documents(caseId) })
      const docs = qc.getQueryData<DocumentOut[]>(qk.documents(caseId)) ?? []
      const schema: QuestionSchemaItem[] = schemaData?.fields ?? []
      const { count } = await prefill(docs, schema)
      setPrefillCount(count)
      setPhase('done')
      onAnalysed(count)
    } catch {
      setError('Extraction failed. You can continue and fill in the fields manually.')
      setPhase('upload')
    }
  }

  if (phase === 'analysing') {
    return (
      <div className="flex flex-col items-center gap-4 py-16 rounded-2xl bg-violet-50 border border-violet-200">
        <div className="h-10 w-10 rounded-full border-4 border-violet-200 border-t-violet-600 animate-spin" />
        <div className="text-center">
          <p className="font-semibold text-violet-800 text-sm">AI is reading your documents…</p>
          <p className="text-xs text-violet-500 mt-1">
            Extracting fields from {uploadedCount} document{uploadedCount !== 1 ? 's' : ''}
          </p>
        </div>
      </div>
    )
  }

  if (phase === 'done') {
    return (
      <div className="space-y-4">
        <div className="flex items-start gap-3 rounded-xl bg-violet-50 border border-violet-200 px-4 py-4">
          <CheckCircle className="w-5 h-5 text-violet-500 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-violet-800">Extraction complete</p>
            {prefillCount > 0 ? (
              <p className="text-xs text-violet-600 mt-0.5">
                {prefillCount} field{prefillCount !== 1 ? 's' : ''} pre-filled from your documents.
                Click <strong>Continue</strong> to review them.
              </p>
            ) : (
              <p className="text-xs text-violet-600 mt-0.5">
                No fields could be matched automatically — you can fill them in on the next steps.
              </p>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-bold text-gray-900">Upload Documents</h3>
        <p className="text-sm text-gray-500 mt-1">
          Upload your KYC documents. Our AI will read them and pre-fill your application — saving
          you time on the next steps.
        </p>
      </div>

      {error && (
        <div className="flex items-start gap-3 rounded-xl bg-amber-50 border border-amber-100 px-4 py-3">
          <AlertCircle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
          <p className="text-xs text-amber-700">{error}</p>
        </div>
      )}

      {/* Upload cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {UPLOAD_CATEGORIES.map((cat) => {
          const filename = uploaded[cat.id]
          const isUploaded = !!filename
          return (
            <label
              key={cat.id}
              className={[
                'cursor-pointer block rounded-xl border-2 border-dashed p-5 transition-colors',
                isUploaded
                  ? 'border-emerald-300 bg-emerald-50/60'
                  : 'border-gray-300 bg-white hover:border-blue-400',
              ].join(' ')}
            >
              <input
                type="file"
                accept=".pdf,.jpg,.jpeg,.png"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0]
                  if (file) handleUpload(file, cat.id)
                  e.target.value = ''
                }}
              />
              {isUploaded ? (
                <div className="flex flex-col items-center gap-2 text-emerald-700">
                  <CheckCircle className="w-6 h-6 text-emerald-500" />
                  <span className="text-xs font-semibold text-center">{cat.label}</span>
                  <span className="text-xs text-emerald-600 truncate max-w-full px-1 text-center">
                    {filename}
                  </span>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-2 text-center text-gray-400">
                  <Upload className="w-6 h-6" />
                  <p className="text-xs font-semibold text-gray-600">{cat.label}</p>
                  <p className="text-xs text-gray-400">{cat.hint}</p>
                  <p className="text-xs text-gray-300 mt-1">PDF, JPG, PNG</p>
                </div>
              )}
            </label>
          )
        })}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-4">
        {uploadedCount > 0 && (
          <button
            onClick={handleAnalyse}
            className="flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 transition-colors"
          >
            <Sparkles className="w-4 h-4" />
            Analyse Documents ({uploadedCount})
          </button>
        )}
        <button
          onClick={onSkip}
          className="text-xs text-gray-400 hover:text-gray-600 underline transition-colors"
        >
          Skip for now
        </button>
      </div>

      <p className="text-xs text-gray-400 text-center">
        Missing documents can be submitted later through your account page.
      </p>
    </div>
  )
}
