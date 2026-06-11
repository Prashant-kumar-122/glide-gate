# UX/UI Standards

**Mandatory** design and accessibility standards for all GlideGate / CADF frontend screens and
components. Every UI change must pass the §8 checklist before it is considered done.

Companion: `docs/FRAMEWORK.md` §Frontend · `docs/TRACEABILITY.md` NFR-09

---

## 1. Design Tokens (single source of truth)

All colors, spacing, typography, and border-radius values come from
`frontend/src/design-system/tokens.ts`. **Never hardcode hex values or pixel sizes in
component code.** Use tokens or Tailwind classes derived from the token scale.

### Color tokens (current IB theme — IBM Plex Sans, sharp geometry)

```ts
// Light mode
surface:        #FFFFFF
surface-raised: #F4F5F7
border:         #DFE1E6
text-primary:   #172B4D
text-secondary: #6B778C
accent:         #0052CC        // IBM Blue
accent-hover:   #0747A6
success:        #36B37E
warning:        #FFAB00
danger:         #DE350B

// Dark mode (auto-detected + user-override persisted)
surface:        #0D1117
surface-raised: #161B22
border:         #30363D
text-primary:   #E6EDF3
text-secondary: #8B949E
accent:         #2F81F7
```

### Typography

- **Font:** IBM Plex Sans (loaded via `index.css`)
- **Scale:** `text-xs` (11px) → `text-sm` (13px) → `text-base` (15px) → `text-lg` (18px) →
  `text-xl` (20px) → `text-2xl` (24px) → `text-3xl` (30px)
- **Line height:** `leading-tight` for headings; `leading-relaxed` for body
- **Weight:** Regular (400) for body; Medium (500) for labels; SemiBold (600) for headings

---

## 2. Theming

- **Default:** follows `prefers-color-scheme` (OS preference)
- **Toggle:** user can switch theme; preference persisted to `localStorage`
- **No flash:** pre-paint script in `index.html` applies theme class before React hydrates
- **Token enforcement:** all colors via CSS variables from the token system — never inline

---

## 3. Responsiveness

All screens must work on three breakpoints as first-class targets:

| Breakpoint | Width | Layout |
|---|---|---|
| Mobile | < 768px | Single column; bottom tab bar nav; full-width cards |
| Tablet | 768px–1279px | Two-column where appropriate; side rail collapses to icons |
| Desktop | ≥ 1280px | Full multi-column layouts; expanded side navigation |

**Rules:**
- No horizontal scroll at any breakpoint
- Touch targets ≥ 44px × 44px (WCAG 2.5.5)
- Fluid layouts (no fixed widths wider than the container)
- Navigation adapts: top bar + inline nav on tablet/desktop; bottom tab bar on mobile

---

## 4. Accessibility (WCAG 2.1 AA — non-negotiable)

Every screen must pass an automated `axe` scan with **zero critical or serious violations**.
Run axe via the Playwright E2E suite:

```bash
make e2e   # includes accessibility sweep
```

**Required:**
- Semantic HTML (`<nav>`, `<main>`, `<article>`, `<section>`, `<header>`, `<button>`)
- Visible focus rings on all interactive elements (never `outline: none` without a replacement)
- All form inputs have associated `<label>` (not just placeholder)
- Color contrast: 4.5:1 minimum for normal text; 3:1 for large text (both light & dark themes)
- ARIA labels on icon-only buttons
- Keyboard navigation: every action reachable without a mouse
- `prefers-reduced-motion`: animations must respect this media query
- Screen reader: no decorative images without `alt=""`; meaningful images have descriptive alt text
- Skip link: `<a href="#main">Skip to main content</a>` in the page header

---

## 5. Component Library

Use existing components from `frontend/src/components/` before creating new ones.

Current primitives:

| Component | Location | Notes |
|---|---|---|
| `StatusBadge` | `components/StatusBadge.tsx` | Stage/status colors from tokens |
| `ProgressBar` | `components/ProgressBar.tsx` | Animated; respects reduced-motion |
| `ConfirmationModal` | `components/ConfirmationModal.tsx` | Use for destructive or regulated actions |
| `DocumentRow` | `components/DocumentRow.tsx` | Document list item with status |
| `BaseGrid` | `components/grid/BaseGrid.tsx` | Data grid base |
| `CommentThread` | `components/CommentThread.tsx` | Collaboration comments |
| `CategoryCard` | `components/CategoryCard.tsx` | Card with category header |

**For new components:**
- Compose from existing primitives first
- Use Tailwind utility classes + tokens (no inline styles)
- Export a typed props interface
- Include all states: default, hover, focus, disabled, loading, error, empty

---

## 6. Loading, Error & Empty States

Every data-fetching surface must implement all three:

| State | Pattern |
|---|---|
| **Loading** | Skeleton placeholders matching the shape of loaded content; never a spinner in the content area |
| **Error** | Inline error message with a retry action; never a blank screen |
| **Empty** | Descriptive empty state with a contextual CTA (e.g. "No cases yet — create your first case") |

---

## 7. Forms

- Client-side validation runs on blur and on submit; never on every keystroke
- Error messages appear below the relevant field (not in a banner)
- Required fields marked with `*` and `aria-required="true"`
- Submit button disabled while submitting; shows loading indicator
- Success/failure feedback via toast (`NotificationToast`), not alert dialogs

---

## 8. Definition-of-Done Checklist (run before every UI change is considered complete)

- [ ] **Tokens only** — no hardcoded hex, pixel, or font values; all via `tokens.ts` or Tailwind
- [ ] **Light + dark** — screenshotted/tested in both themes; no invisible elements in either
- [ ] **Mobile (360px)** — no overflow, no broken layout, touch targets ≥ 44px
- [ ] **Tablet (768px)** — layout adapts correctly; navigation collapses appropriately
- [ ] **Desktop (1280px)** — full layout; no excessive whitespace
- [ ] **All states** — loading skeleton, error + retry, empty state with CTA all implemented
- [ ] **Keyboard** — every action reachable via keyboard alone; focus order logical
- [ ] **axe (Playwright)** — zero critical/serious violations in both light and dark themes
- [ ] **Reduced motion** — animations gated on `prefers-reduced-motion: no-preference`
- [ ] **Screen reader** — all interactive elements have accessible names

---

## 9. IB Theme Principles (GlideGate brand)

GlideGate uses an investment-banking aesthetic applied in June 2026:

- **Sharp geometry:** `border-radius: 2px` for cards and inputs (not rounded)
- **Dense information density:** compact table rows, smaller font sizes preferred over large cards
- **Monochromatic base** with a single accent color (IBM Blue `#0052CC` / `#2F81F7` dark)
- **Split-panel login:** left panel with brand/imagery; right panel with form
- **Data-forward:** tables over card grids for list views; charts use muted colors

When adding new screens, follow these principles. Do not introduce rounded corners, large
decorative imagery, or colorful gradients without approval.

---

## 10. Adding a New Screen

1. Create component in `frontend/src/features/{module}/`
2. Add route in `App.tsx` with `ProtectedRoute` and correct permission scope
3. Run the §8 checklist above — all items must pass
4. Add Playwright E2E test covering the happy path and the empty state
5. Add axe accessibility assertion to `frontend/e2e/a11y.spec.ts`
6. Update `docs/FRAMEWORK.md` §Frontend Feature Structure
