# Theme Suggestions for GlideGate

## Context
The project currently uses Tailwind CSS with a `darkMode: 'class'` approach, defaulting to dark mode. The navbar is `bg-gray-900` with a `bg-blue-600` logo accent. The `themeStore.ts` only supports `dark | light`. We'll extend it to support 5 named themes, each applied via a `data-theme` attribute on `<html>` + CSS custom properties.

---

## 5 Theme Previews

### 1. Midnight Indigo *(current feel, refined)*
> Deep navy with indigo-violet accents. Professional and financial.

```
┌─────────────────────────────────────────────────────┐
│  NavBar  ██████████████████████████████████████████  │
│  bg: #0f172a (slate-950)   accent: #6366f1 (indigo) │
├─────────────────────────────────────────────────────┤
│  Surface cards: #1e293b (slate-800)                  │
│  Text primary:  #f1f5f9 (slate-100)                  │
│  Text muted:    #94a3b8 (slate-400)                  │
│                                                       │
│  Status badges stay the same (blue/green/red/amber)  │
│  Logo box:  ▓▓ indigo-600 #4f46e5                    │
└─────────────────────────────────────────────────────┘
Palette: slate-950 · indigo-600 · slate-800 · slate-100
```

---

### 2. Emerald Wealth
> Deep forest green with emerald accents. Conveys growth & prosperity.

```
┌─────────────────────────────────────────────────────┐
│  NavBar  ████████████████████████████████████████   │
│  bg: #052e16 (green-950)   accent: #10b981 (emerald)│
├─────────────────────────────────────────────────────┤
│  Surface cards: #064e3b (emerald-900)                │
│  Text primary:  #ecfdf5 (green-50)                   │
│  Text muted:    #6ee7b7 (emerald-300)                │
│                                                       │
│  Status: approved → teal, warning → lime             │
│  Logo box:  ▓▓ emerald-500 #10b981                   │
└─────────────────────────────────────────────────────┘
Palette: green-950 · emerald-500 · emerald-900 · green-50
```

---

### 3. Royal Amethyst
> Deep purple background with violet accents. Premium & luxury feel.

```
┌─────────────────────────────────────────────────────┐
│  NavBar  ████████████████████████████████████████   │
│  bg: #1e1b4b (indigo-950)  accent: #8b5cf6 (violet) │
├─────────────────────────────────────────────────────┤
│  Surface cards: #312e81 (indigo-900)                 │
│  Text primary:  #f5f3ff (violet-50)                  │
│  Text muted:    #c4b5fd (violet-300)                 │
│                                                       │
│  Status: roles get violet/fuchsia tones              │
│  Logo box:  ▓▓ violet-500 #8b5cf6                    │
└─────────────────────────────────────────────────────┘
Palette: indigo-950 · violet-500 · indigo-900 · violet-50
```

---

### 4. Warm Charcoal *(earthy / copper)*
> Warm stone-dark background with amber/copper accents. Sophisticated & grounded.

```
┌─────────────────────────────────────────────────────┐
│  NavBar  ████████████████████████████████████████   │
│  bg: #1c1917 (stone-900)   accent: #f59e0b (amber)  │
├─────────────────────────────────────────────────────┤
│  Surface cards: #292524 (stone-800)                  │
│  Text primary:  #fafaf9 (stone-50)                   │
│  Text muted:    #a8a29e (stone-400)                  │
│                                                       │
│  Status: amber-heavy palette, warm reds              │
│  Logo box:  ▓▓ amber-500 #f59e0b                     │
└─────────────────────────────────────────────────────┘
Palette: stone-900 · amber-500 · stone-800 · stone-50
```

---

### 5. Arctic Frost *(light mode, clean)*
> Crisp white + sky blue. Airy, modern, high-contrast light theme.

```
┌─────────────────────────────────────────────────────┐
│  NavBar  ████████████████████████████████████████   │
│  bg: #0c4a6e (sky-900)     accent: #0ea5e9 (sky-500)│
├─────────────────────────────────────────────────────┤
│  Surface cards: #ffffff · page bg: #f0f9ff (sky-50)  │
│  Text primary:  #0f172a (slate-900)                  │
│  Text muted:    #64748b (slate-500)                  │
│                                                       │
│  Status badges: vivid on white background            │
│  Logo box:  ▓▓ sky-500 #0ea5e9                       │
└─────────────────────────────────────────────────────┘
Palette: sky-900 navbar · sky-500 accent · white surface · sky-50 bg
```

---

## Implementation Plan

### Files to change

| File | Change |
|------|--------|
| `frontend/src/index.css` | Add CSS custom property blocks per `[data-theme="x"]` |
| `frontend/tailwind.config.ts` | Extend colors with `var(--color-primary)`, `var(--color-surface)`, etc. |
| `frontend/src/store/themeStore.ts` | Extend `Theme` type to 5 named themes, apply `data-theme` on `<html>` |
| `frontend/src/App.tsx` | Replace `bg-gray-900` / `bg-blue-600` logo with CSS-var-driven classes |
| `frontend/src/components/ThemePicker.tsx` | New: swatch picker component shown in the navbar |

### CSS Variable Strategy

```css
/* index.css */
[data-theme="midnight-indigo"] {
  --color-nav:     #0f172a;
  --color-surface: #1e293b;
  --color-accent:  #6366f1;
  --color-text:    #f1f5f9;
  --color-muted:   #94a3b8;
}
[data-theme="emerald-wealth"] { ... }
[data-theme="royal-amethyst"] { ... }
[data-theme="warm-charcoal"]  { ... }
[data-theme="arctic-frost"]   { ... }
```

### ThemeStore update

```ts
type Theme = 'midnight-indigo' | 'emerald-wealth' | 'royal-amethyst' | 'warm-charcoal' | 'arctic-frost'
// applies data-theme on html element; arctic-frost also removes `dark` class
```

### ThemePicker UI (navbar)
- Small palette icon button in the navbar (right side)
- Dropdown with 5 color swatches (circular dots in each theme's accent color)
- Clicking a swatch applies the theme instantly

## Verification
1. `npm run dev` in `frontend/`
2. Open browser → click palette icon → all 5 themes switch live
3. Refresh page → theme persists (localStorage via Zustand persist)
4. Check status badges remain readable across all themes
