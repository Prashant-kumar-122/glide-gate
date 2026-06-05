interface AuthLayoutProps {
  eyebrow: string
  heading: string
  children: React.ReactNode
}

export default function AuthLayout({ eyebrow, heading, children }: AuthLayoutProps) {
  return (
    <div className="flex min-h-screen">
      {/* Left panel — brand statement */}
      <div className="hidden lg:flex lg:w-[480px] xl:w-[560px] flex-col justify-between bg-gray-950 border-r border-gray-800 px-12 py-14 shrink-0">
        {/* Brand statement */}
        <div>
          <h1 className="mb-6 text-3xl font-semibold leading-tight tracking-tight text-white">
            Onboarding intelligence<br />for financial professionals
          </h1>
          <p className="mb-10 text-sm leading-relaxed text-gray-400">
            End-to-end KYC document workflows, AI-assisted validation,
            and real-time case management — built to institutional standards.
          </p>

          {/* Feature list */}
          <div className="space-y-3">
            {[
              'AI document validation with audit trail',
              'Multi-stage workflow — Intake to Live Account',
              'Role-based access across advisor, compliance & sales',
            ].map((item) => (
              <div key={item} className="flex items-start gap-3">
                <div className="mt-1 h-1.5 w-1.5 shrink-0 bg-primary" />
                <p className="text-xs text-gray-400">{item}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="border-t border-gray-800 pt-6">
          <div className="flex items-center gap-4">
            {['Secure', 'Compliant', 'Regulated'].map((tag) => (
              <span
                key={tag}
                className="text-[10px] font-medium uppercase tracking-widest text-gray-600"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Right panel — form */}
      <div className="flex flex-1 items-center justify-center bg-gray-50 dark:bg-gray-950 px-6 py-12">
        <div className="w-full max-w-sm">
          {/* Mobile-only logo */}
          <div className="mb-8 flex items-center gap-2.5 lg:hidden">
            <div className="flex h-7 w-7 items-center justify-center bg-primary">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                <rect x="1" y="1" width="5" height="5" fill="white" opacity="0.9" />
                <rect x="8" y="1" width="5" height="5" fill="white" opacity="0.6" />
                <rect x="1" y="8" width="5" height="5" fill="white" opacity="0.6" />
                <rect x="8" y="8" width="5" height="5" fill="white" opacity="0.3" />
              </svg>
            </div>
            <span className="text-sm font-semibold tracking-tight text-gray-900 dark:text-white">GlideGate</span>
          </div>

          {/* Form heading */}
          <div className="mb-8">
            <p className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-gray-400 dark:text-gray-500">
              {eyebrow}
            </p>
            <h2 className="text-xl font-semibold tracking-tight text-gray-900 dark:text-gray-100">
              {heading}
            </h2>
          </div>

          {/* Hairline card */}
          <div className="border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-900">
            {children}
          </div>

          <p className="mt-4 text-center text-xs text-gray-400 dark:text-gray-600">
            Protected by TLS 1.3 · Institutional security standards
          </p>
        </div>
      </div>
    </div>
  )
}
