import { useState } from 'react'
import { Send } from 'lucide-react'
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
}

const VISIBILITY_LABELS: Record<Comment['visibility'], string> = {
  ALL: 'Everyone',
  ADVISOR_ONLY: 'Advisor only',
}

function CommentBubble({ comment }: { comment: Comment }) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-2">
        <span className="text-xs font-semibold text-gray-700">{comment.authorName}</span>
        <RoleBadge role={comment.authorRole} size="sm" />
        <span className="ml-auto text-[10px] text-gray-400">
          {new Date(comment.createdAt).toLocaleString()}
        </span>
      </div>
      <p className="rounded-lg bg-gray-50 px-3 py-2 text-sm text-gray-700">{comment.body}</p>
      <p className="text-[10px] text-gray-400">
        Visible to: {VISIBILITY_LABELS[comment.visibility]}
      </p>
    </div>
  )
}

export default function CommentThread({
  comments,
  onAddComment,
  readOnly = false,
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
        <div className="flex flex-col gap-2 border-t border-gray-100 pt-3">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Add a comment…"
            rows={3}
            className="w-full resize-none rounded-lg border border-gray-200 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-400"
          />
          <div className="flex items-center justify-between">
            <select
              value={visibility}
              onChange={(e) => setVisibility(e.target.value as Comment['visibility'])}
              className="rounded border border-gray-200 px-2 py-1 text-xs text-gray-600 focus:outline-none"
            >
              <option value="ALL">Everyone</option>
              <option value="ADVISOR_ONLY">Advisor only</option>
            </select>
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
