import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User } from 'lucide-react'
import { useChatStore } from '@/store/chatStore'
import type { ChatMessage } from '@/store/chatStore'
import { useSendMessage } from '@/hooks/useClientChat'

function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === 'user'
  return (
    <div className={['flex gap-2.5', isUser ? 'flex-row-reverse' : 'flex-row'].join(' ')}>
      <div
        className={[
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
          isUser ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-700',
        ].join(' ')}
      >
        {isUser ? (
          <User className="h-4 w-4 text-white" />
        ) : (
          <Bot className="h-4 w-4 text-gray-600 dark:text-gray-300" />
        )}
      </div>
      <div
        className={[
          'max-w-[76%] px-4 py-2.5 text-sm leading-relaxed',
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-gray-100 text-gray-900 dark:bg-gray-700 dark:text-gray-100',
        ].join(' ')}
      >
        <p className="whitespace-pre-wrap">{msg.content}</p>
        <p
          className={[
            'mt-1 text-[10px]',
            isUser ? 'text-blue-200 text-right' : 'text-gray-400',
          ].join(' ')}
        >
          {new Date(msg.timestamp).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </p>
      </div>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="flex gap-2.5">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gray-200 dark:bg-gray-700">
        <Bot className="h-4 w-4 text-gray-600 dark:text-gray-300" />
      </div>
      <div className="bg-gray-100 px-4 py-3 dark:bg-gray-700">
        <div className="flex gap-1 items-center">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="h-2 w-2 animate-bounce rounded-full bg-gray-400 dark:bg-gray-500"
              style={{ animationDelay: `${i * 150}ms` }}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

interface OptionChipsProps {
  options: string[]
  onSelect: (option: string) => void
}

function OptionChips({ options, onSelect }: OptionChipsProps) {
  return (
    <div className="flex flex-wrap gap-2 pl-10">
      {options.map((opt) => (
        <button
          key={opt}
          onClick={() => onSelect(opt)}
          className="border border-blue-300 bg-white px-3.5 py-1.5 text-sm font-medium text-blue-700 transition-all hover:bg-blue-600 hover:text-white hover:border-blue-600 dark:border-blue-700 dark:bg-gray-800 dark:text-blue-300 dark:hover:bg-blue-600 dark:hover:text-white"
        >
          {opt}
        </button>
      ))}
    </div>
  )
}

interface ConversationalChatProps {
  caseId: string | null
  questionnaireDone?: boolean
}

export default function ConversationalChat({ caseId, questionnaireDone = false }: ConversationalChatProps) {
  const [input, setInput] = useState('')
  const [streamingText, setStreamingText] = useState('')
  const messages = useChatStore((s) => s.messages)
  const typingIndicator = useChatStore((s) => s.typingIndicator)
  const pendingOptions = useChatStore((s) => s.pendingOptions)
  const clearPendingOptions = useChatStore((s) => s.clearPendingOptions)
  const isComplete = questionnaireDone
  const bottomRef = useRef<HTMLDivElement>(null)
  const sendMessage = useSendMessage(caseId)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, typingIndicator, streamingText, pendingOptions])

  function submitText(text: string) {
    if (!text.trim() || !caseId || sendMessage.isPending || isComplete) return
    setInput('')
    sendMessage.mutate({
      text: text.trim(),
      onChunk: (accumulated) => setStreamingText(accumulated),
      onDone: () => setStreamingText(''),
    })
  }

  function handleSend() {
    submitText(input)
  }

  function handleOptionClick(option: string) {
    clearPendingOptions()
    submitText(option)
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  function handleInputChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setInput(e.target.value)
    if (pendingOptions.length > 0) clearPendingOptions()
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center gap-2.5 border-b border-gray-100 px-4 py-3 dark:border-gray-700">
        <div className="flex h-8 w-8 items-center justify-center bg-blue-50 dark:bg-blue-950">
          <Bot className="h-4 w-4 text-blue-600 dark:text-blue-400" />
        </div>
        <div>
          <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">GlideGate Assistant</p>
          <p className="text-xs text-gray-400">Here to guide you through onboarding</p>
        </div>
      </div>

      {/* Messages list */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && !typingIndicator && !streamingText && (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
            <div className="bg-blue-50 p-4 dark:bg-blue-950">
              <Bot className="h-7 w-7 text-blue-500" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-700 dark:text-gray-200">Start your onboarding journey</p>
              <p className="mt-1 text-xs text-gray-400">
                Say hello and I'll guide you through the process
              </p>
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} msg={msg} />
        ))}

        {streamingText && (
          <MessageBubble
            msg={{
              id: '__streaming__',
              role: 'assistant',
              content: streamingText,
              timestamp: new Date().toISOString(),
            }}
          />
        )}

        {typingIndicator && !streamingText && <TypingIndicator />}

        {pendingOptions.length > 0 && !typingIndicator && !streamingText && (
          <OptionChips options={pendingOptions} onSelect={handleOptionClick} />
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-gray-100 p-3 dark:border-gray-700">
        {isComplete ? (
          <div className="bg-green-50 border border-green-200 px-4 py-3 text-center dark:bg-green-950 dark:border-green-800">
            <p className="text-sm font-medium text-green-700 dark:text-green-300">All questions answered</p>
            <p className="mt-0.5 text-xs text-green-500 dark:text-green-400">
              You can review your answers in the Details panel
            </p>
          </div>
        ) : (
          <>
            {!caseId && (
              <p className="pb-2 text-center text-xs text-gray-400">
                Select a case above to start chatting
              </p>
            )}
            <div className="flex gap-2">
              <textarea
                value={input}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                placeholder="Type a message… (Enter to send, Shift+Enter for new line)"
                rows={2}
                disabled={!caseId || sendMessage.isPending}
                className="flex-1 resize-none border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:cursor-not-allowed disabled:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-100 dark:placeholder-gray-500 dark:disabled:bg-gray-900"
              />
              <button
                onClick={handleSend}
                disabled={!caseId || !input.trim() || sendMessage.isPending}
                className="flex items-center justify-center self-end bg-primary p-2.5 text-white transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:bg-gray-300 dark:disabled:bg-gray-700"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
