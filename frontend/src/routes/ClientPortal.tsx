export default function ClientPortal() {
  return (
    <div className="flex h-full items-center justify-center p-12">
      <div className="rounded-xl border border-gray-200 bg-white p-8 shadow-sm">
        <h1 className="text-2xl font-semibold text-gray-900">Client Portal</h1>
        <p className="mt-2 text-gray-500">
          Streaming conversational chat · Document hub · Upload · Progress tracker
        </p>
        <span className="mt-4 inline-block rounded-full bg-purple-100 px-3 py-1 text-xs font-medium text-purple-700">
          Implemented in STEP-21
        </span>
      </div>
    </div>
  )
}
