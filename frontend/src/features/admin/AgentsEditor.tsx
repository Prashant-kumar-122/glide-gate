import { useState } from 'react'
import { Plus, Trash2, Loader2, ChevronDown, ChevronRight, ToggleLeft, ToggleRight } from 'lucide-react'
import {
  useAgents,
  useAddAgent,
  useUpdateAgentStatus,
  useRemoveAgent,
  useAgentPrompts,
  useUpsertPrompt,
  useDeletePrompt,
  useAgentSkills,
  useAgentToolGrants,
  useAddToolGrant,
  useRemoveToolGrant,
  type AgentRosterOut,
} from '@/hooks/useDomainAdmin'

interface Props {
  domainId: string
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={[
        'inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-semibold ring-1',
        status === 'APPROVED'
          ? 'bg-emerald-50 text-emerald-700 ring-emerald-200 dark:bg-emerald-950 dark:text-emerald-300 dark:ring-emerald-800'
          : 'bg-gray-50 text-gray-500 ring-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:ring-gray-700',
      ].join(' ')}
    >
      {status === 'APPROVED' ? <ToggleRight className="h-3 w-3" /> : <ToggleLeft className="h-3 w-3" />}
      {status}
    </span>
  )
}

function AgentDetail({ domainId, agent }: { domainId: string; agent: AgentRosterOut }) {
  const { data: prompts } = useAgentPrompts(domainId, agent.agent_id)
  const { data: skills } = useAgentSkills(domainId, agent.agent_id)
  const { data: grants } = useAgentToolGrants(domainId, agent.agent_id)
  const upsertPrompt = useUpsertPrompt(domainId, agent.agent_id)
  const deletePrompt = useDeletePrompt(domainId, agent.agent_id)
  const addGrant = useAddToolGrant(domainId, agent.agent_id)
  const removeGrant = useRemoveToolGrant(domainId, agent.agent_id)

  const [editingPrompt, setEditingPrompt] = useState<{ role: string; text: string } | null>(null)
  const [newPromptRole, setNewPromptRole] = useState('')
  const [grantForm, setGrantForm] = useState({ connector_id: '', tool_name: '' })

  return (
    <div className="space-y-6 border-t border-gray-100 p-4 dark:border-gray-700">
      {/* Prompts */}
      <div>
        <h5 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-gray-500">System Prompts</h5>
        <div className="space-y-2">
          {(prompts ?? []).map((p) => (
            <div key={p.id} className="border border-gray-200 p-3 dark:border-gray-700">
              <div className="mb-1 flex items-center justify-between">
                <span className="font-mono text-[11px] font-medium text-blue-600 dark:text-blue-400">{p.prompt_role}</span>
                <button
                  onClick={() => deletePrompt.mutate(p.prompt_role)}
                  className="rounded p-0.5 text-gray-300 hover:text-red-500"
                  aria-label="Delete prompt"
                >
                  <Trash2 className="h-3 w-3" />
                </button>
              </div>
              {editingPrompt?.role === p.prompt_role ? (
                <div className="space-y-2">
                  <textarea
                    value={editingPrompt.text}
                    onChange={(e) => setEditingPrompt((ep) => ep ? { ...ep, text: e.target.value } : null)}
                    rows={4}
                    className="w-full border border-gray-200 bg-white px-2 py-1.5 font-mono text-[11px] text-gray-700 outline-none dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={() => {
                        upsertPrompt.mutate({ prompt_role: editingPrompt.role, prompt_text: editingPrompt.text }, {
                          onSuccess: () => setEditingPrompt(null),
                        })
                      }}
                      className="bg-primary px-2.5 py-1 text-[11px] font-medium text-white hover:bg-primary-hover"
                    >
                      Save
                    </button>
                    <button onClick={() => setEditingPrompt(null)} className="px-2.5 py-1 text-[11px] text-gray-500">Cancel</button>
                  </div>
                </div>
              ) : (
                <button
                  className="w-full text-left text-[11px] text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
                  onClick={() => setEditingPrompt({ role: p.prompt_role, text: p.prompt_text })}
                >
                  <span className="line-clamp-2">{p.prompt_text || '(empty)'}</span>
                  <span className="text-[10px] text-blue-500">Click to edit</span>
                </button>
              )}
            </div>
          ))}

          <div className="flex gap-2">
            <input
              type="text"
              value={newPromptRole}
              onChange={(e) => setNewPromptRole(e.target.value)}
              placeholder="prompt role (e.g. system)"
              className="flex-1 border border-gray-200 bg-white px-2.5 py-1.5 text-xs text-gray-700 outline-none dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
            />
            <button
              onClick={() => {
                if (!newPromptRole.trim()) return
                setEditingPrompt({ role: newPromptRole.trim(), text: '' })
                setNewPromptRole('')
              }}
              className="border border-dashed border-gray-300 px-3 py-1.5 text-xs text-gray-500 hover:border-primary hover:text-primary"
            >
              <Plus className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Skills */}
      <div>
        <h5 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-gray-500">Skill Bindings</h5>
        {(skills ?? []).length === 0 ? (
          <p className="text-[11px] text-gray-400">No skills bound.</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {(skills ?? []).map((s) => (
              <span key={s.id} className="rounded bg-purple-50 px-2 py-0.5 text-[11px] text-purple-700 ring-1 ring-purple-200 dark:bg-purple-950 dark:text-purple-300 dark:ring-purple-800">
                {s.skill_id}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Tool Grants */}
      <div>
        <h5 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-gray-500">MCP Tool Grants</h5>
        <div className="space-y-1">
          {(grants ?? []).map((g) => (
            <div key={g.id} className="flex items-center justify-between text-[11px]">
              <span className="font-mono text-gray-700 dark:text-gray-300">
                {g.connector_id} / {g.tool_name}
              </span>
              <button
                onClick={() => removeGrant.mutate(g.id)}
                className="rounded p-0.5 text-gray-300 hover:text-red-500"
                aria-label="Remove grant"
              >
                <Trash2 className="h-3 w-3" />
              </button>
            </div>
          ))}

          <div className="flex gap-2">
            <input
              type="text"
              value={grantForm.connector_id}
              onChange={(e) => setGrantForm((p) => ({ ...p, connector_id: e.target.value }))}
              placeholder="connector_id"
              className="w-28 border border-gray-200 bg-white px-2 py-1 text-[11px] text-gray-700 outline-none dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
            />
            <span className="py-1 text-[10px] text-gray-400">/</span>
            <input
              type="text"
              value={grantForm.tool_name}
              onChange={(e) => setGrantForm((p) => ({ ...p, tool_name: e.target.value }))}
              placeholder="tool_name"
              className="w-28 border border-gray-200 bg-white px-2 py-1 text-[11px] text-gray-700 outline-none dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
            />
            <button
              onClick={() => {
                if (!grantForm.connector_id.trim() || !grantForm.tool_name.trim()) return
                addGrant.mutate(grantForm, { onSuccess: () => setGrantForm({ connector_id: '', tool_name: '' }) })
              }}
              disabled={addGrant.isPending}
              className="border border-dashed border-gray-300 px-2 py-1 text-[11px] text-gray-500 hover:border-primary hover:text-primary"
            >
              {addGrant.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function AgentsEditor({ domainId }: Props) {
  const { data: agents, isLoading } = useAgents(domainId)
  const addAgent = useAddAgent(domainId)
  const updateStatus = useUpdateAgentStatus(domainId)
  const removeAgent = useRemoveAgent(domainId)

  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({ agent_id: '', agent_class: '' })
  const [expanded, setExpanded] = useState<string | null>(null)

  function handleAdd() {
    if (!form.agent_id.trim() || !form.agent_class.trim()) return
    addAgent.mutate(form, {
      onSuccess: () => {
        setForm({ agent_id: '', agent_class: '' })
        setShowAdd(false)
      },
    })
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">Agent Roster</h3>
        <p className="mt-0.5 text-xs text-gray-500">
          Manage agents, their prompts, skill bindings, and MCP tool grants. Toggle status to enable/disable dispatch without redeployment.
        </p>
      </div>

      <div className="overflow-hidden border border-gray-200 dark:border-gray-700">
        {isLoading ? (
          <div className="flex items-center justify-center py-8 text-xs text-gray-400">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading…
          </div>
        ) : (
          <div className="divide-y divide-gray-100 dark:divide-gray-700">
            {(agents ?? []).length === 0 && (
              <p className="py-8 text-center text-xs text-gray-400">No agents in roster.</p>
            )}
            {(agents ?? []).map((agent) => (
              <div key={agent.id}>
                <div className="flex items-center justify-between px-4 py-3">
                  <div className="flex min-w-0 flex-1 items-center gap-3">
                    <button
                      onClick={() => setExpanded((e) => (e === agent.agent_id ? null : agent.agent_id))}
                      className="shrink-0 text-gray-400 hover:text-gray-600"
                      aria-label="Expand agent"
                    >
                      {expanded === agent.agent_id
                        ? <ChevronDown className="h-4 w-4" />
                        : <ChevronRight className="h-4 w-4" />
                      }
                    </button>
                    <div className="min-w-0">
                      <p className="font-mono text-xs font-medium text-gray-800 dark:text-gray-100">{agent.agent_id}</p>
                      <p className="truncate text-[11px] text-gray-400">{agent.agent_class}</p>
                    </div>
                  </div>
                  <div className="ml-3 flex shrink-0 items-center gap-2">
                    <StatusBadge status={agent.status} />
                    <button
                      onClick={() =>
                        updateStatus.mutate({
                          agentId: agent.agent_id,
                          status: agent.status === 'APPROVED' ? 'DEPRECATED' : 'APPROVED',
                        })
                      }
                      disabled={updateStatus.isPending}
                      className="border border-gray-200 px-2 py-1 text-[11px] text-gray-500 hover:bg-gray-50 disabled:opacity-40 dark:border-gray-700 dark:text-gray-400 dark:hover:bg-gray-700"
                    >
                      Toggle
                    </button>
                    <button
                      onClick={() => removeAgent.mutate(agent.agent_id)}
                      disabled={removeAgent.isPending}
                      className="rounded p-1 text-gray-300 hover:bg-red-50 hover:text-red-500 disabled:opacity-30 dark:hover:bg-red-950"
                      aria-label="Remove agent"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
                {expanded === agent.agent_id && <AgentDetail domainId={domainId} agent={agent} />}
              </div>
            ))}
          </div>
        )}
      </div>

      {showAdd ? (
        <div className="border border-blue-200 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-950">
          <p className="mb-3 text-xs font-semibold text-blue-700 dark:text-blue-300">Add Agent to Roster</p>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">Agent ID <span className="text-red-400">*</span></label>
              <input
                type="text"
                value={form.agent_id}
                onChange={(e) => setForm((p) => ({ ...p, agent_id: e.target.value }))}
                placeholder="e.g. kyc_compliance"
                className="w-full border border-gray-200 bg-white px-2.5 py-1.5 font-mono text-xs outline-none focus:border-primary dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-gray-600 dark:text-gray-400">Agent Class <span className="text-red-400">*</span></label>
              <input
                type="text"
                value={form.agent_class}
                onChange={(e) => setForm((p) => ({ ...p, agent_class: e.target.value }))}
                placeholder="e.g. app.agents.kyc_compliance.KYCComplianceAgent"
                className="w-full border border-gray-200 bg-white px-2.5 py-1.5 font-mono text-xs outline-none focus:border-primary dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
              />
            </div>
          </div>
          {addAgent.isError && (
            <p className="mt-2 text-[11px] text-red-600 dark:text-red-400">Failed to add agent.</p>
          )}
          <div className="mt-3 flex gap-2">
            <button
              onClick={handleAdd}
              disabled={!form.agent_id.trim() || !form.agent_class.trim() || addAgent.isPending}
              className="flex items-center gap-1.5 bg-primary px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-hover disabled:opacity-50"
            >
              {addAgent.isPending && <Loader2 className="h-3 w-3 animate-spin" />}
              Add Agent
            </button>
            <button
              onClick={() => setShowAdd(false)}
              className="bg-white px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-100 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 border border-dashed border-gray-300 px-4 py-2.5 text-xs font-medium text-gray-500 hover:border-primary hover:text-primary dark:border-gray-600 dark:text-gray-400"
        >
          <Plus className="h-3.5 w-3.5" />
          Add Agent
        </button>
      )}
    </div>
  )
}
