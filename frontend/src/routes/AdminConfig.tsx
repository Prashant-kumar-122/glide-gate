export default function AdminConfig() {
  return (
    <div className="flex h-full items-center justify-center p-12">
      <div className="rounded-xl border border-gray-200 bg-white p-8 shadow-sm">
        <h1 className="text-2xl font-semibold text-gray-900">Admin Config</h1>
        <p className="mt-2 text-gray-500">
          LLM provider selector · Deterministic controls · Validation prompt editor · Checkpoint rules
        </p>
        <span className="mt-4 inline-block rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">
          Implemented in STEP-23 / STEP-30
        </span>
      </div>
    </div>
  )
}
