import { useState, useEffect, useRef } from 'react'
import { ChevronDown, Upload, CheckCircle, AlertTriangle, FileText, FolderOpen, MessageCircle, Lock } from 'lucide-react'
import StatusBadge from '@/components/StatusBadge'
import ClientDocumentModal from './ClientDocumentModal'
import { useClientDocuments, useClientUpload } from '@/hooks/useClientDocuments'
import { useComments } from '@/hooks/useComments'
import type { DocumentOut } from '@/lib/api'

const CATEGORIES = [
  'identity',
  'financial',
  'legal',
  'insurance',
  'compliance',
  'entity',
] as const

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

function groupByCategory(docs: DocumentOut[]): Record<string, DocumentOut[]> {
  const map: Record<string, DocumentOut[]> = {}
  for (const doc of docs) {
    const cat = doc.category ?? 'other'
    if (!map[cat]) map[cat] = []
    map[cat].push(doc)
  }
  return map
}

interface AccordionItemProps {
  category: string
  documents: DocumentOut[]
  commentCountByDoc: Record<string, number>
  onUpload: (file: File, parentDocId?: string) => void
  onDocumentClick: (doc: DocumentOut) => void
  isUploading?: boolean
  open: boolean
  onToggle: () => void
  readOnly?: boolean
}

function AccordionItem({
  category,
  documents,
  commentCountByDoc,
  onUpload,
  onDocumentClick,
  isUploading,
  open,
  onToggle,
  readOnly = false,
}: AccordionItemProps) {
  const [dragging, setDragging] = useState(false)

  function processFiles(fileList: FileList | null, parentDocId?: string) {
    if (!fileList || isUploading) return
    const file = Array.from(fileList).find((f) => ALLOWED_MIME.includes(f.type))
    if (file) onUpload(file, parentDocId)
  }

  function openPicker(parentDocId?: string) {
    if (isUploading) return
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = ALLOWED_MIME.join(',')
    input.onchange = (e) => processFiles((e.target as HTMLInputElement).files, parentDocId)
    input.click()
  }

  const allApproved = documents.length > 0 && documents.every((d) => d.status === 'APPROVED')
  const needsAction = documents.some((d) => d.status === 'NEEDS_REVISION')

  return (
    <div
      className={[
        'border bg-white overflow-hidden transition-colors dark:bg-gray-800',
        needsAction ? 'border-red-200 dark:border-red-800' : allApproved ? 'border-green-200 dark:border-green-800' : 'border-gray-200 dark:border-gray-700',
      ].join(' ')}
    >
      {/* Accordion header */}
      <button
        onClick={onToggle}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-gray-50 transition-colors dark:hover:bg-gray-700"
      >
        <div className="flex min-w-0 items-center gap-2.5">
          {allApproved ? (
            <CheckCircle className="h-4 w-4 shrink-0 text-green-500" />
          ) : needsAction ? (
            <AlertTriangle className="h-4 w-4 shrink-0 text-amber-500" />
          ) : (
            <FolderOpen className="h-4 w-4 shrink-0 text-gray-400" />
          )}
          <div className="min-w-0">
            <span className="block truncate text-sm font-semibold text-gray-900 dark:text-gray-100">
              {CATEGORY_LABELS[category] ?? category}
            </span>
            <span className="block truncate text-xs text-gray-400">
              {CATEGORY_DESCRIPTIONS[category] ?? 'Supporting documents'}
            </span>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {documents.length > 0 && (
            <span className="bg-gray-100 px-2 py-0.5 text-[10px] font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-300">
              {documents.length}
            </span>
          )}
          <ChevronDown
            className={[
              'h-4 w-4 text-gray-400 transition-transform duration-200',
              open ? 'rotate-180' : '',
            ].join(' ')}
          />
        </div>
      </button>

      {/* Accordion body */}
      {open && (
        <div className="border-t border-gray-100 px-4 pb-4 pt-3 dark:border-gray-700">
          {/* Document list */}
          {documents.length > 0 && (
            <div className="mb-3 space-y-1">
              {documents.map((doc) => (
                <div
                  key={doc.id}
                  onClick={() => onDocumentClick(doc)}
                  className="group flex cursor-pointer items-center justify-between gap-2 bg-gray-50 px-3 py-2 hover:bg-gray-100 transition-colors dark:bg-gray-700 dark:hover:bg-gray-600"
                >
                  <div className="flex min-w-0 items-center gap-2">
                    <FileText className="h-3 w-3 shrink-0 text-gray-400" />
                    <span className="truncate text-xs text-gray-700 dark:text-gray-200">{doc.name}</span>
                    {doc.version > 1 && (
                      <span className="shrink-0 text-[10px] text-gray-400">v{doc.version}</span>
                    )}
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    {(commentCountByDoc[doc.id] ?? 0) > 0 && (
                      <span className="flex items-center gap-0.5 bg-blue-100 px-1.5 py-0.5 text-[9px] font-bold text-blue-600 dark:bg-blue-900 dark:text-blue-300">
                        <MessageCircle className="h-2.5 w-2.5" />
                        {commentCountByDoc[doc.id]}
                      </span>
                    )}
                    <StatusBadge status={doc.status} size="sm" />
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Upload zone */}
          {readOnly ? (
            <div className="flex items-center justify-center gap-2 border border-amber-200 bg-amber-50 px-4 py-3 text-xs font-medium text-amber-700 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-300">
              <Lock className="h-3.5 w-3.5 shrink-0" />
              <span>Uploads locked during KYC review or once completed</span>
            </div>
          ) : documents[documents.length - 1]?.status === 'APPROVED' ? (
            <div className="flex items-center justify-center gap-2 border border-green-200 bg-green-50 px-4 py-3 text-xs font-medium text-green-700 dark:border-green-800 dark:bg-green-950 dark:text-green-300">
              <CheckCircle className="h-3.5 w-3.5 shrink-0" />
              <span>Document approved — no further uploads needed</span>
            </div>
          ) : (
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
              onClick={() => openPicker()}
              role="button"
              tabIndex={isUploading ? -1 : 0}
              onKeyDown={(e) => e.key === 'Enter' && openPicker()}
              className={[
                'flex items-center justify-center gap-2 border-2 border-dashed py-3 text-center transition-colors',
                dragging
                  ? 'border-blue-400 bg-blue-50 cursor-copy dark:border-blue-500 dark:bg-blue-950'
                  : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50 cursor-pointer dark:border-gray-600 dark:hover:border-gray-500 dark:hover:bg-gray-700',
                isUploading ? 'cursor-not-allowed opacity-60' : '',
              ].join(' ')}
            >
              {isUploading ? (
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-200 border-t-blue-500" />
              ) : (
                <Upload className={['h-3.5 w-3.5', dragging ? 'text-blue-500' : 'text-gray-400'].join(' ')} />
              )}
              <div>
                <p className="text-xs font-medium text-gray-600 dark:text-gray-300">
                  {isUploading ? 'Uploading…' : documents.length > 0 ? 'Upload new version' : 'Upload document'}
                </p>
                <p className="text-[10px] text-gray-400">PDF, Word, or image · drag & drop or click</p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

interface ClientDocumentHubProps {
  caseId: string | null
  readOnly?: boolean
}

export default function ClientDocumentHub({ caseId, readOnly = false }: ClientDocumentHubProps) {
  const { data: docs, isLoading } = useClientDocuments(caseId)
  const upload = useClientUpload(caseId ?? '')
  const { data: comments = [] } = useComments(caseId)
  const [selectedDoc, setSelectedDoc] = useState<DocumentOut | null>(null)

  const commentCountByDoc = comments.reduce<Record<string, number>>((acc, c) => {
    if (c.documentId) acc[c.documentId] = (acc[c.documentId] ?? 0) + 1
    return acc
  }, {})
  const byCategory = groupByCategory(docs ?? [])

  // Start all closed; open categories with documents once data loads
  const [openCategories, setOpenCategories] = useState<Set<string>>(() => new Set<string>())
  const hasOpenedRef = useRef(false)
  useEffect(() => {
    if (!hasOpenedRef.current && docs && docs.length > 0) {
      hasOpenedRef.current = true
      const grouped = groupByCategory(docs)
      const withDocs = new Set(
        CATEGORIES.filter((cat) => {
          const catDocs = grouped[cat] ?? []
          return catDocs.length > 0 && !catDocs.every((d) => d.status === 'APPROVED')
        })
      )
      setOpenCategories(withDocs)
    }
  }, [docs])

  function toggleCategory(cat: string) {
    setOpenCategories((prev) => {
      const next = new Set(prev)
      if (next.has(cat)) next.delete(cat)
      else next.add(cat)
      return next
    })
  }

  if (!caseId) {
    return (
      <div className="flex h-40 items-center justify-center">
        <p className="text-sm text-gray-400">Select a case to view documents</p>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-14 animate-pulse bg-gray-200 dark:bg-gray-700" />
        ))}
      </div>
    )
  }

  const totalDocs = docs?.length ?? 0
  const approvedDocs = docs?.filter((d) => d.status === 'APPROVED').length ?? 0

  return (
    <div>
      {totalDocs > 0 && (
        <div className="mb-4 flex items-center gap-2 border border-gray-200 bg-white px-4 py-2.5 dark:border-gray-700 dark:bg-gray-800">
          <FolderOpen className="h-4 w-4 text-gray-400" />
          <p className="text-xs text-gray-600 dark:text-gray-300">
            <span className="font-semibold text-gray-900 dark:text-gray-100">{approvedDocs}</span> of{' '}
            <span className="font-semibold text-gray-900 dark:text-gray-100">{totalDocs}</span> document
            {totalDocs !== 1 ? 's' : ''} approved
          </p>
        </div>
      )}

      <div className="space-y-2">
        {CATEGORIES.map((cat) => (
          <AccordionItem
            key={cat}
            category={cat}
            documents={byCategory[cat] ?? []}
            commentCountByDoc={commentCountByDoc}
            onUpload={(file, parentDocId) => upload.mutate({ file, category: cat, parentDocId })}
            onDocumentClick={setSelectedDoc}
            isUploading={upload.isPending}
            open={openCategories.has(cat)}
            onToggle={() => toggleCategory(cat)}
            readOnly={readOnly}
          />
        ))}
      </div>

      {selectedDoc && caseId && (
        <ClientDocumentModal
          doc={selectedDoc}
          caseId={caseId}
          onClose={() => setSelectedDoc(null)}
        />
      )}
    </div>
  )
}
