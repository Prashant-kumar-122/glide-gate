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
        sans: ['IBM Plex Sans', 'system-ui', 'sans-serif'],
        mono: ['IBM Plex Mono', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        // Tighter, more data-dense type scale
        '2xs': ['0.625rem', { lineHeight: '0.875rem' }],  // 10px
      },
      letterSpacing: {
        tightest: '-0.02em',
        widest2: '0.15em',
      },
      colors: {
        // ── Investment banking semantic tokens (static dark palette) ──────────
        'bg-base':        '#060A14',   // deep navy-black — app body
        'bg-surface':     '#0C1220',   // nav chrome / side panels
        'bg-elevated':    '#141C2C',   // card surface
        'bg-hover':       '#1C2640',   // hover state
        primary:          '#3B7BF5',   // brand blue
        'primary-hover':  '#2D6BE0',
        'primary-subtle': '#122452',   // subtle tinted bg for selected rows etc.
        'text-primary':   '#DCE2EE',   // primary text
        'text-secondary': '#9CA8BE',   // secondary / labels
        'text-muted':     '#5A687E',   // very muted
        success:          '#52B678',   // muted green
        'success-subtle': '#08180E',
        warning:          '#AC7226',   // muted amber
        'warning-subtle': '#241202',
        danger:           '#A45252',   // muted red
        'danger-subtle':  '#220808',
        info:             '#3B7BF5',
        'info-subtle':    '#0A1432',
        'border-default': '#222C3E',   // standard border
        'border-subtle':  '#141C2C',   // hairline border
        // ── Gold accent — premium indicators (account numbers, completed) ─────
        gold:             '#B8960C',
        'gold-subtle':    '#1A1500',
        // ── CSS var-backed color families (adaptive light ↔ dark) ─────────────
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
          blue: '#2563EB',
        },
        // Document status tokens — used in CaseListTable/ClientStatusTable cells
        status: {
          'not-requested': '#76849B',
          requested:       '#6097FB',
          received:        '#9680BA',
          'under-review':  '#C2903E',
          'needs-revision':'#A45252',
          approved:        '#52B678',
        },
        // Role tokens
        role: {
          advisor:    '#3B7BF5',
          client:     '#7C62A4',
          compliance: '#AC7226',
          'cc-rep':   '#52B678',
          admin:      '#5A687E',
        },
      },
      borderRadius: {
        // IB-standard geometry — much tighter than consumer apps
        DEFAULT: '3px',
        sm:  '2px',
        md:  '4px',
        lg:  '6px',
        xl:  '8px',
        '2xl': '10px',
        full: '9999px',
      },
      boxShadow: {
        // Investment banking: structure via borders, not shadows
        // Only use shadows for floating overlays (dropdowns, modals, tooltips)
        DEFAULT: '0 1px 3px 0 rgb(0 0 0 / 0.25), 0 1px 2px -1px rgb(0 0 0 / 0.25)',
        sm:      '0 1px 2px 0 rgb(0 0 0 / 0.2)',
        md:      '0 2px 6px 0 rgb(0 0 0 / 0.3), 0 1px 3px -1px rgb(0 0 0 / 0.3)',
        lg:      '0 4px 12px 0 rgb(0 0 0 / 0.4), 0 2px 6px -2px rgb(0 0 0 / 0.4)',
        xl:      '0 8px 24px 0 rgb(0 0 0 / 0.5), 0 4px 12px -4px rgb(0 0 0 / 0.5)',
        none:    'none',
      },
    },
  },
  plugins: [],
} satisfies Config
