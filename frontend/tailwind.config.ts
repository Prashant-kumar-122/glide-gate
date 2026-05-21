import type { Config } from 'tailwindcss'

export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Document status tokens (STEP-19)
        status: {
          'not-requested': '#94a3b8',
          requested: '#60a5fa',
          received: '#a78bfa',
          'under-review': '#fbbf24',
          'needs-revision': '#f87171',
          approved: '#34d399',
        },
        // Role tokens
        role: {
          advisor: '#3b82f6',
          client: '#8b5cf6',
          compliance: '#f59e0b',
          'cc-rep': '#10b981',
          admin: '#6b7280',
        },
      },
    },
  },
  plugins: [],
} satisfies Config
