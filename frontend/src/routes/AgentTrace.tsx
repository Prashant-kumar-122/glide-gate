import AgentTraceCanvas from '@/features/agent-trace/AgentTraceCanvas'

export default function AgentTrace() {
  return (
    <div className="flex h-[calc(100vh-48px)] flex-col">
      <div className="flex items-center justify-between border-b border-gray-200 bg-white px-6 py-3">
        <div>
          <h1 className="text-sm font-semibold text-gray-900">Agent Trace Canvas</h1>
          <p className="text-[11px] text-gray-400">
            Live A2A message flow · 8 agent nodes · Real-time state machine
          </p>
        </div>
      </div>
      <div className="flex-1 overflow-hidden">
        <AgentTraceCanvas />
      </div>
    </div>
  )
}
