import { useQuery, useMutation } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useAuthStore } from '@/store/authStore'
import { useChatStore } from '@/store/chatStore'

interface MessageRecord {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
}

export const chatQk = {
  messages: (caseId: string) => ['cases', caseId, 'messages'] as const,
}

export function useChatHistory(caseId: string | null) {
  return useQuery<MessageRecord[]>({
    queryKey: chatQk.messages(caseId ?? ''),
    queryFn: () => api.get(`/cases/${caseId}/messages`).then((r) => r.data),
    enabled: !!caseId,
    staleTime: Infinity,
    gcTime: 0,
    refetchOnWindowFocus: false,
  })
}

export function useSendMessage(caseId: string | null) {
  const addMessage = useChatStore((s) => s.addMessage)
  const setTyping = useChatStore((s) => s.setTyping)

  return useMutation({
    mutationFn: async ({
      text,
      onChunk,
      onDone,
    }: {
      text: string
      onChunk?: (accumulated: string) => void
      onDone?: (fullText: string) => void
    }) => {
      if (!caseId) return

      addMessage({
        id: crypto.randomUUID(),
        role: 'user',
        content: text,
        timestamp: new Date().toISOString(),
      })
      setTyping(true)

      let assistantText = ''

      try {
        const token = useAuthStore.getState().token
        const resp = await fetch(`/api/cases/${caseId}/message`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ message: text }),
        })

        if (resp.ok && resp.headers.get('content-type')?.includes('text/event-stream') && resp.body) {
          const reader = resp.body.getReader()
          const decoder = new TextDecoder()

          outer: while (true) {
            const { done, value } = await reader.read()
            if (done) break

            const raw = decoder.decode(value, { stream: true })
            for (const line of raw.split('\n')) {
              if (!line.startsWith('data: ')) continue
              const payload = line.slice(6).trim()
              if (payload === '[DONE]') break outer
              try {
                const parsed = JSON.parse(payload) as { chunk?: string; text?: string; token?: string }
                assistantText += parsed.chunk ?? parsed.text ?? parsed.token ?? ''
                onChunk?.(assistantText)
              } catch {
                // skip malformed SSE line
              }
            }
          }
        }

        if (!assistantText) {
          assistantText =
            "Thank you for your message. Your advisor will review it and get back to you shortly."
        }

        addMessage({
          id: crypto.randomUUID(),
          role: 'assistant',
          content: assistantText,
          timestamp: new Date().toISOString(),
        })
        onDone?.(assistantText)
      } finally {
        setTyping(false)
      }
    },
  })
}
