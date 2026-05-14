import { useRef, useState } from 'react'
import { Upload, X } from 'lucide-react'

const ALLOWED_MIME = [
  'image/jpeg',
  'image/png',
  'image/webp',
  'image/tiff',
  'application/pdf',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
]

interface UploadButtonProps {
  onUpload: (files: File[]) => void
  multiple?: boolean
  disabled?: boolean
  label?: string
  accept?: string
}

export default function UploadButton({
  onUpload,
  multiple = false,
  disabled = false,
  label = 'Upload Document',
  accept = ALLOWED_MIME.join(','),
}: UploadButtonProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  function processFiles(fileList: FileList | null) {
    if (!fileList) return
    const files = Array.from(fileList).filter((f) =>
      ALLOWED_MIME.includes(f.type)
    )
    if (files.length) onUpload(files)
  }

  function onDragOver(e: React.DragEvent) {
    e.preventDefault()
    if (!disabled) setDragging(true)
  }

  function onDragLeave() {
    setDragging(false)
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragging(false)
    if (!disabled) processFiles(e.dataTransfer.files)
  }

  return (
    <div
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      className={[
        'relative flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-6 py-8 transition-colors',
        dragging
          ? 'border-blue-400 bg-blue-50'
          : 'border-gray-300 bg-gray-50 hover:border-gray-400',
        disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer',
      ].join(' ')}
      onClick={() => !disabled && inputRef.current?.click()}
      role="button"
      tabIndex={disabled ? -1 : 0}
      onKeyDown={(e) => e.key === 'Enter' && !disabled && inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        multiple={multiple}
        accept={accept}
        className="sr-only"
        onChange={(e) => processFiles(e.target.files)}
        disabled={disabled}
      />

      {dragging ? (
        <X className="h-8 w-8 text-blue-400" />
      ) : (
        <Upload className="h-8 w-8 text-gray-400" />
      )}

      <div className="text-center">
        <p className="text-sm font-medium text-gray-700">{label}</p>
        <p className="text-xs text-gray-400">PDF, Word, or image &middot; drag &amp; drop or click</p>
      </div>
    </div>
  )
}
