import type { Config } from 'tailwindcss'

// Generates a CSS-variable-backed color token with Tailwind v3 opacity support.
// The corresponding CSS var must be defined as space-separated RGB channels.
const cv = (name: string) => `rgb(var(--${name}) / <alpha-value>)`

export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        // ── Reference-2 semantic tokens (static dark palette for direct use) ──
        'bg-base':        '#0D0F14',
        'bg-surface':     '#161B24',
        'bg-elevated':    '#1E2533',
        'bg-hover':       '#242D3D',
        primary:          '#3B7BF5',
        'primary-hover':  '#2D6BE0',
        'primary-subtle': '#1A2A4A',
        'text-primary':   '#F0F2F5',
        'text-secondary': '#8A94A6',
        'text-muted':     '#4F5A6E',
        success:          '#22C55E',
        'success-subtle': '#0F2A1A',
        warning:          '#F59E0B',
        'warning-subtle': '#2A1F0A',
        danger:           '#EF4444',
        'danger-subtle':  '#2A0F0F',
        info:             '#38BDF8',
        'info-subtle':    '#0A1F2A',
        'border-default': '#2A3140',
        'border-subtle':  '#1E2533',
        // ── Semantic color families — driven by CSS vars so dark mode can
        //    override them in .dark without touching any component files. ──────
        gray: {
          50:  cv('gray-50'),
          100: cv('gray-100'),
          200: cv('gray-200'),
          300: cv('gray-300'),
          400: cv('gray-400'),
          500: cv('gray-500'),
          600: cv('gray-600'),
          700: cv('gray-700'),
          800: cv('gray-800'),
          900: cv('gray-900'),
          950: cv('gray-950'),
        },
        blue: {
          50:  cv('blue-50'),
          100: cv('blue-100'),
          300: cv('blue-300'),
          400: cv('blue-400'),
          500: cv('blue-500'),
          600: cv('blue-600'),
          700: cv('blue-700'),
          900: cv('blue-900'),
          950: cv('blue-950'),
        },
        green: {
          50:  cv('green-50'),
          100: cv('green-100'),
          200: cv('green-200'),
          300: cv('green-300'),
          400: cv('green-400'),
          700: cv('green-700'),
          800: cv('green-800'),
          900: cv('green-900'),
          950: cv('green-950'),
        },
        amber: {
          50:  cv('amber-50'),
          100: cv('amber-100'),
          200: cv('amber-200'),
          300: cv('amber-300'),
          400: cv('amber-400'),
          500: cv('amber-500'),
          700: cv('amber-700'),
          800: cv('amber-800'),
          900: cv('amber-900'),
          950: cv('amber-950'),
        },
        red: {
          50:  cv('red-50'),
          100: cv('red-100'),
          300: cv('red-300'),
          400: cv('red-400'),
          500: cv('red-500'),
          600: cv('red-600'),
          700: cv('red-700'),
          800: cv('red-800'),
          900: cv('red-900'),
          950: cv('red-950'),
        },
        violet: {
          50:  cv('violet-50'),
          100: cv('violet-100'),
          200: cv('violet-200'),
          300: cv('violet-300'),
          400: cv('violet-400'),
          500: cv('violet-500'),
          800: cv('violet-800'),
          950: cv('violet-950'),
        },
        indigo: {
          100: cv('indigo-100'),
          300: cv('indigo-300'),
          400: cv('indigo-400'),
          600: cv('indigo-600'),
          700: cv('indigo-700'),
          900: cv('indigo-900'),
        },
        purple: {
          50:  cv('purple-50'),
          400: cv('purple-400'),
          600: cv('purple-600'),
          950: cv('purple-950'),
        },
        emerald: {
          300: cv('emerald-300'),
          400: cv('emerald-400'),
          600: cv('emerald-600'),
        },
        // Brand — pinned values that must not shift between light and dark
        brand: {
          blue: '#2563eb',
        },
        // Document status tokens
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
