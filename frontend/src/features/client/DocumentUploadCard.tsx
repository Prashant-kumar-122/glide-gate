import { useState } from 'react'
import { Upload, CheckCircle, AlertTriangle, FileText, MessageCircle } from 'lucide-react'
import StatusBadge from '@/components/StatusBadge'
import type { DocumentOut } from '@/lib/api'

const CATEGORY_LABELS: Record<string, string> = {
  identity: 'Identity Documents',
  financial: 'Financial Documents',
  legal: 'Legal Documents',
  insurance: 'Insurance Documents',
  compliance: 'Compliance Documents',
  entity: 'Entity Documents',
}

const CATEGORY_DESCRIPTIONS: Record<string, string> = {
  identity: "Passport, driver's license, or national ID",
  financial: 'Bank statements, tax returns, investment accounts',
  legal: 'Power of attorney, trust documents',
  insurance: 'Life or health insurance policies',
  compliance: 'Regulatory filings, FATCA/FBAR forms',
  entity: 'Business registration, corporate documents',
}

const ALLOWED_MIME = [
  'image/jpeg',
  'image/png',
  'image/webp',
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
]

interface DocumentUploadCardProps {
  category: string
  documents: DocumentOut[]
  commentCountByDoc?: Record<string, number>
  onUpload: (file: File) => void
  onDocumentClick: (doc: DocumentOut) => void
  isUploading?: boolean
}

export default function DocumentUploadCard({
  category,
  documents,
  commentCountByDoc = {},
  onUpload,
  onDocumentClick,
  isUploading,
}: DocumentUploadCardProps) {
  const [dragging, setDragging] = useState(false)

  function processFiles(fileList: FileList | null) {
    if (!fileList || isUploading) return
    const file = Array.from(fileList).find((f) => ALLOWED_MIME.includes(f.type))
    if (file) onUpload(file)
  }

  function openPicker() {
    if (isUploading) return
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = ALLOWED_MIME.join(',')
    input.onchange = (e) => processFiles((e.target as HTMLInputElement).files)
    input.click()
  }

  const allApproved = documents.length > 0 && documents.every((d) => d.status === 'APPROVED')
  const needsAction = documents.some((d) => d.status === 'NEEDS_REVISION')

  return (
    <div
      className={[
        'rounded-2xl border bg-white p-4 transition-colors',
        needsAction ? 'border-red-200' : allApproved ? 'border-green-200' : 'border-gray-200',
      ].join(' ')}
    >
      {/* Header */}
      <div className="mb-3 flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold text-gray-900">
            {CATEGORY_LABELS[category] ?? category}
          </h3>
          <p className="mt-0.5 text-xs text-gray-400 leading-snug">
            {CATEGORY_DESCRIPTIONS[category] ?? 'Supporting documents'}
          </p>
        </div>
        {allApproved && <CheckCircle className="h-4 w-4 shrink-0 text-green-500" />}
        {needsAction && <AlertTriangle className="h-4 w-4 shrink-0 text-red-500" />}
      </div>

      {/* Existing documents — each row is clickable */}
      {documents.length > 0 && (
        <div className="mb-3 space-y-1">
          {documents.map((doc) => {
            const count = commentCountByDoc[doc.id] ?? 0
            return (
              <button
                key={doc.id}
                onClick={() => onDocumentClick(doc)}
                className="flex w-full items-center justify-between gap-2 rounded-lg bg-gray-50 px-2.5 py-1.5 text-left transition-colors hover:bg-blue-50"
              >
                <div className="flex min-w-0 items-center gap-1.5">
                  <FileText className="h-3 w-3 shrink-0 text-gray-400" />
                  <span className="truncate text-xs text-gray-700">{doc.name}</span>
                  {doc.version > 1 && (
                    <span className="shrink-0 text-[10px] text-gray-400">v{doc.version}</span>
                  )}
                  {count > 0 && (
                    <span className="flex shrink-0 items-center gap-0.5 rounded-full bg-blue-100 px-1.5 py-0.5 text-[10px] font-semibold text-blue-600">
                      <MessageCircle className="h-2.5 w-2.5" />
                      {count}
                    </span>
                  )}
                </div>
                <StatusBadge status={doc.status} size="sm" />
              </button>
            )
          })}
        </div>
      )}

      {/* Upload zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault()
          if (!isUploading) setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          processFiles(e.dataTransfer.files)
        }}
        onClick={openPicker}
        role="button"
        tabIndex={isUploading ? -1 : 0}
        onKeyDown={(e) => e.key === 'Enter' && openPicker()}
        className={[
          'flex flex-col items-center gap-1 rounded-xl border-2 border-dashed py-3 text-center transition-colors',
          dragging
            ? 'border-blue-400 bg-blue-50 cursor-copy'
            : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50 cursor-pointer',
          isUploading ? 'cursor-not-allowed opacity-60' : '',
        ].join(' ')}
      >
        {isUploading ? (
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-200 border-t-blue-500" />
        ) : (
          <Upload
            className={['h-4 w-4', dragging ? 'text-blue-500' : 'text-gray-400'].join(' ')}
          />
        )}
        <p className="text-xs font-medium text-gray-600">
          {isUploading ? 'Uploading…' : documents.length > 0 ? 'Upload new version' : 'Upload document'}
        </p>
        <p className="text-[10px] text-gray-400">PDF, Word, or image · drag & drop or click</p>
      </div>
    </div>
  )
}
