import { useRef, useState, useCallback } from 'react';
import { IconUpload, IconFile, IconX } from '@tabler/icons-react';

interface FileUploadZoneProps {
  onFilesAccepted: (files: File[]) => void;
  accept?: string;
  multiple?: boolean;
  label?: string;
  description?: string;
}

export function FileUploadZone({
  onFilesAccepted,
  accept,
  multiple = false,
  label = 'Drop files here or click to upload',
  description = 'Any file type accepted',
}: FileUploadZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging]       = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);

  // ── Helpers ──────────────────────────────────────────────────────────────────

  const addFiles = useCallback(
    (incoming: FileList | null) => {
      if (!incoming || incoming.length === 0) return;
      const newFiles = Array.from(incoming);
      const merged   = multiple ? [...selectedFiles, ...newFiles] : newFiles;
      setSelectedFiles(merged);
      onFilesAccepted(merged);
    },
    [multiple, selectedFiles, onFilesAccepted],
  );

  const removeFile = (index: number) => {
    const updated = selectedFiles.filter((_, i) => i !== index);
    setSelectedFiles(updated);
    onFilesAccepted(updated);
    // Reset the hidden input so the same file can be re-added later
    if (inputRef.current) inputRef.current.value = '';
  };

  // ── Drag handlers ─────────────────────────────────────────────────────────────

  const onDragEnter = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const onDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    // Only clear if the drag actually left the zone boundary
    if (!e.currentTarget.contains(e.relatedTarget as Node)) {
      setIsDragging(false);
    }
  };

  const onDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const onDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    addFiles(e.dataTransfer.files);
  };

  // ── Input change ──────────────────────────────────────────────────────────────

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    addFiles(e.target.files);
  };

  const openDialog = () => inputRef.current?.click();

  // ── Render ────────────────────────────────────────────────────────────────────

  return (
    <div className="w-full space-y-3">
      {/* Drop zone */}
      <div
        role="button"
        tabIndex={0}
        aria-label="File upload area"
        onClick={openDialog}
        onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && openDialog()}
        onDragEnter={onDragEnter}
        onDragLeave={onDragLeave}
        onDragOver={onDragOver}
        onDrop={onDrop}
        className={[
          'relative flex flex-col items-center justify-center gap-3 w-full',
          'min-h-[140px] rounded-lg border-2 border-dashed cursor-pointer',
          'transition-colors duration-150 outline-none select-none',
          'focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-bg-surface',
          isDragging
            ? 'border-primary bg-primary-subtle'
            : 'border-border-default bg-bg-surface hover:border-primary/50 hover:bg-bg-elevated',
        ].join(' ')}
      >
        {/* Hidden file input */}
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          className="hidden"
          onChange={onInputChange}
          aria-hidden="true"
          tabIndex={-1}
        />

        {/* Icon */}
        <div
          className={[
            'flex items-center justify-center w-12 h-12 rounded-full transition-colors',
            isDragging ? 'bg-primary/20' : 'bg-bg-elevated',
          ].join(' ')}
        >
          <IconUpload
            size={22}
            className={isDragging ? 'text-primary' : 'text-text-muted'}
            strokeWidth={1.75}
          />
        </div>

        {/* Text */}
        <div className="text-center px-4">
          <p
            className={[
              'text-sm font-medium transition-colors',
              isDragging ? 'text-primary' : 'text-text-primary',
            ].join(' ')}
          >
            {label}
          </p>
          <p className="mt-0.5 text-xs text-text-muted">{description}</p>
          {accept && (
            <p className="mt-1 text-xs text-text-muted">
              Accepted: <span className="text-text-secondary">{accept}</span>
            </p>
          )}
        </div>
      </div>

      {/* Selected file list */}
      {selectedFiles.length > 0 && (
        <ul className="space-y-2">
          {selectedFiles.map((file, i) => (
            <li
              key={i}
              className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-bg-elevated border border-border-default"
            >
              {/* File icon */}
              <div className="flex-shrink-0 flex items-center justify-center w-8 h-8 rounded bg-primary-subtle">
                <IconFile size={16} className="text-primary" strokeWidth={1.75} />
              </div>

              {/* Name + size */}
              <div className="flex-1 min-w-0">
                <p className="text-sm text-text-primary font-medium truncate">{file.name}</p>
                <p className="text-xs text-text-muted">
                  {file.size < 1024
                    ? `${file.size} B`
                    : file.size < 1024 * 1024
                    ? `${(file.size / 1024).toFixed(1)} KB`
                    : `${(file.size / (1024 * 1024)).toFixed(2)} MB`}
                </p>
              </div>

              {/* Remove button */}
              <button
                type="button"
                onClick={e => { e.stopPropagation(); removeFile(i); }}
                aria-label={`Remove ${file.name}`}
                className="flex-shrink-0 flex items-center justify-center w-6 h-6 rounded text-text-muted hover:text-danger hover:bg-danger-subtle transition-colors"
              >
                <IconX size={14} strokeWidth={2} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default FileUploadZone;
