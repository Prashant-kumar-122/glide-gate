/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
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
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
