import { useRef, useState } from 'react'
import { Upload } from 'lucide-react'

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
    const files = Array.from(fileList).filter((f) => ALLOWED_MIME.includes(f.type))
    if (files.length) onUpload(files)
  }

  function onDragOver(e: React.DragEvent) {
    e.preventDefault()
    if (!disabled) setDragging(true)
  }

  function onDragLeave() { setDragging(false) }

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
        'relative flex flex-col items-center justify-center gap-2 border-2 border-dashed px-6 py-6 transition-colors',
        dragging
          ? 'border-primary bg-primary-subtle'
          : 'border-gray-300 bg-gray-50 hover:border-gray-400 dark:border-gray-700 dark:bg-gray-800/40 dark:hover:border-gray-600',
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

      <Upload className={['h-6 w-6', dragging ? 'text-primary' : 'text-gray-400'].join(' ')} />

      <div className="text-center">
        <p className="text-xs font-semibold text-gray-700 dark:text-gray-200">{label}</p>
        <p className="mt-0.5 text-[10px] text-gray-400">PDF, Word, or image · drag & drop or click</p>
      </div>
    </div>
  )
}
