import { useState, useRef, useEffect } from 'react'
import { Send, ChevronDown, Check } from 'lucide-react'
import RoleBadge from './RoleBadge'
import type { TeamRole } from '@/design-system/tokens'

export interface Comment {
  id: string
  authorName: string
  authorRole: TeamRole
  body: string
  createdAt: string
  visibility: 'ALL' | 'ADVISOR_ONLY'
  documentId?: string | null
}

interface CommentThreadProps {
  comments: Comment[]
  currentRole?: TeamRole
  onAddComment?: (body: string, visibility: Comment['visibility']) => void
  readOnly?: boolean
  hideVisibility?: boolean
}

const VISIBILITY_LABELS: Record<Comment['visibility'], string> = {
  ALL: 'Everyone',
  ADVISOR_ONLY: 'Advisor only',
}

function CommentBubble({ comment }: { comment: Comment }) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-2">
        <span className="text-xs font-semibold text-gray-700 dark:text-gray-200">{comment.authorName}</span>
        <RoleBadge role={comment.authorRole} size="sm" />
        <span className="ml-auto text-[10px] text-gray-400">
          {new Date(comment.createdAt).toLocaleString()}
        </span>
      </div>
      <p className="rounded-lg bg-gray-50 px-3 py-2 text-sm text-gray-700 dark:bg-gray-700 dark:text-gray-200">{comment.body}</p>
      <p className="text-[10px] text-gray-400">
        Visible to: {VISIBILITY_LABELS[comment.visibility]}
      </p>
    </div>
  )
}

const VISIBILITY_OPTIONS: { value: Comment['visibility']; label: string }[] = [
  { value: 'ALL', label: 'Everyone' },
  { value: 'ADVISOR_ONLY', label: 'Advisor only' },
]

function VisibilitySelect({
  value,
  onChange,
}: {
  value: Comment['visibility']
  onChange: (v: Comment['visibility']) => void
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  const selected = VISIBILITY_OPTIONS.find((o) => o.value === value)!

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-2.5 py-1.5 text-xs font-medium text-gray-700 transition-colors hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
      >
        {selected.label}
        <ChevronDown className={['h-3 w-3 text-gray-400 transition-transform', open ? 'rotate-180' : ''].join(' ')} />
      </button>

      {open && (
        <div className="absolute top-full left-0 z-50 mt-1 min-w-[130px] overflow-hidden rounded-lg border border-gray-200 bg-white shadow-lg dark:border-gray-600 dark:bg-gray-800">
          {VISIBILITY_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => { onChange(opt.value); setOpen(false) }}
              className={[
                'flex w-full items-center justify-between px-3 py-2 text-left text-xs font-medium transition-colors',
                opt.value === value
                  ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'
                  : 'text-gray-700 hover:bg-gray-50 dark:text-gray-200 dark:hover:bg-gray-700',
              ].join(' ')}
            >
              {opt.label}
              {opt.value === value && <Check className="h-3 w-3" />}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default function CommentThread({
  comments,
  onAddComment,
  readOnly = false,
  hideVisibility = false,
}: CommentThreadProps) {
  const [draft, setDraft] = useState('')
  const [visibility, setVisibility] = useState<Comment['visibility']>('ALL')

  function handleSubmit() {
    const trimmed = draft.trim()
    if (!trimmed || !onAddComment) return
    onAddComment(trimmed, visibility)
    setDraft('')
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-3">
        {comments.length === 0 ? (
          <p className="text-center text-xs text-gray-400 py-4">No comments yet</p>
        ) : (
          comments.map((c) => <CommentBubble key={c.id} comment={c} />)
        )}
      </div>

      {!readOnly && onAddComment && (
        <div className="flex flex-col gap-2 border-t border-gray-100 pt-3 dark:border-gray-700">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Add a comment…"
            rows={3}
            className="w-full resize-none rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-400 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:placeholder-gray-500"
          />
          <div className="flex items-center justify-between">
            {!hideVisibility && (
              <VisibilitySelect value={visibility} onChange={setVisibility} />
            )}
            {hideVisibility && <span />}
            <button
              onClick={handleSubmit}
              disabled={!draft.trim()}
              className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-40"
            >
              <Send className="h-3 w-3" />
              Send
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
