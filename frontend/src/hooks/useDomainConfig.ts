/**
 * useDomainConfig — Phase 10
 *
 * Fetches GET /api/config/domain and exposes stage labels/styles, persona
 * colors/routes, and the active product catalog as typed, derived lookups.
 *
 * Static wealth-domain values are used as placeholderData so the UI renders
 * correctly before the first network response arrives and as a fallback when
 * the server is unreachable.  This lets every component that currently
 * hard-codes stage/persona display constants migrate incrementally.
 */
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

// ── Static fallback (wealth-domain defaults) ──────────────────────────────────

const _STAGE_FALLBACK = {
  INTAKE:            { label: 'Intake',         color: '#9CA3AF', style: { badge: 'text-gray-400',   dot: 'bg-gray-500',   optionDot: 'bg-gray-400' }, is_terminal: false, is_human_pending: false },
  KYC:               { label: 'KYC',            color: '#3B82F6', style: { badge: 'text-blue-400',   dot: 'bg-blue-500',   optionDot: 'bg-blue-400' }, is_terminal: false, is_human_pending: false },
  PARALLEL_PRODUCTS: { label: 'Products',       color: '#8B5CF6', style: { badge: 'text-violet-400', dot: 'bg-violet-500', optionDot: 'bg-violet-400' }, is_terminal: false, is_human_pending: false },
  REVIEW:            { label: 'Advisor Review', color: '#F59E0B', style: { badge: 'text-amber-400',  dot: 'bg-amber-500',  optionDot: 'bg-amber-400' }, is_terminal: false, is_human_pending: true  },
  SALES_REVIEW:      { label: 'Sales Review',   color: '#F59E0B', style: { badge: 'text-amber-400',  dot: 'bg-amber-500',  optionDot: 'bg-amber-400' }, is_terminal: false, is_human_pending: true  },
  COMPLETE:          { label: 'Live',           color: '#10B981', style: { badge: 'text-green-400',  dot: 'bg-green-500',  optionDot: 'bg-green-400' }, is_terminal: true,  is_human_pending: false },
  ESCALATED:         { label: 'Escalated',      color: '#EF4444', style: { badge: 'text-red-400',    dot: 'bg-red-500',    optionDot: 'bg-red-400' },  is_terminal: false, is_human_pending: false },
} as const

const _PERSONA_FALLBACK = {
  advisor:            { label: 'Advisor',           color: '#3B82F6', default_route: '/',       nav_links: [] },
  sales_manager:      { label: 'Sales Manager',     color: '#F59E0B', default_route: '/',       nav_links: [] },
  admin:              { label: 'Admin',              color: '#8B5CF6', default_route: '/admin',  nav_links: [] },
  client:             { label: 'Client',             color: '#10B981', default_route: '/client', nav_links: [] },
  compliance_officer: { label: 'Compliance Officer', color: '#8B5CF6', default_route: '/',       nav_links: [] },
} as const

// ── Types ─────────────────────────────────────────────────────────────────────

export interface StageConfig {
  code: string
  label: string
  color: string
  style: Record<string, string>
  is_terminal: boolean
  is_human_pending: boolean
}

export interface PersonaConfig {
  code: string
  label: string
  color: string
  default_route: string
  nav_links: { label: string; href: string }[]
}

export interface ProductConfig {
  code: string
  display_name: string
  product_type: string
  is_active: boolean
}

export interface DomainConfigOut {
  domain_code: string
  display_name: string
  stages: StageConfig[]
  personas: PersonaConfig[]
  products: ProductConfig[]
}

// ── Static fallback response ──────────────────────────────────────────────────

const FALLBACK: DomainConfigOut = {
  domain_code: 'wealth_management',
  display_name: 'Wealth Management',
  stages: Object.entries(_STAGE_FALLBACK).map(([code, v]) => ({ code, ...v })),
  personas: Object.entries(_PERSONA_FALLBACK).map(([code, v]) => ({ code, ...v })),
  products: [],
}

// ── Fetch function ─────────────────────────────────────────────────────────────

async function fetchDomainConfig(): Promise<DomainConfigOut> {
  const { data } = await api.get<DomainConfigOut>('/config/domain')
  // Merge styles from static fallback for stages that lack DB display-config rows
  return {
    ...data,
    stages: data.stages.map((s) => ({
      ...s,
      style: Object.keys(s.style ?? {}).length
        ? s.style
        : (_STAGE_FALLBACK[s.code as keyof typeof _STAGE_FALLBACK]?.style ?? {}),
    })),
  }
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useDomainConfig() {
  const { data } = useQuery<DomainConfigOut>({
    queryKey: ['domain-config'],
    queryFn: fetchDomainConfig,
    staleTime: 5 * 60 * 1000,     // cache for 5 min — vocabulary rarely changes
    placeholderData: FALLBACK,     // render immediately; replace when response arrives
  })

  const config = data ?? FALLBACK

  /** Stage lookup by code — includes label, color, style, is_terminal, is_human_pending */
  const stageByCode: Record<string, StageConfig> = Object.fromEntries(
    config.stages.map((s) => [s.code, s])
  )

  /** Persona lookup by persona_code */
  const personaByCode: Record<string, PersonaConfig> = Object.fromEntries(
    config.personas.map((p) => [p.code, p])
  )

  /** Ordered list of all stage codes from the domain */
  const allStageCodes: string[] = config.stages.map((s) => s.code)

  /**
   * Build a ROLE_HOME-style map: persona_code → default_route.
   * Callers should fall back to '/login' when the code is unknown.
   */
  const roleHome: Record<string, string> = Object.fromEntries(
    config.personas.map((p) => [p.code, p.default_route])
  )

  /**
   * Derive NAV_LINKS from persona nav_links, deduplicating by href.
   * Each entry carries the set of persona codes that declared it so callers
   * can filter by the current user's personas.
   *
   * nav_link shape from DB: { label: string; href: string }
   * Output shape: { to: string; label: string; roles: string[] }
   */
  const navLinks: { to: string; label: string; roles: string[] }[] = (() => {
    const map = new Map<string, { label: string; roles: Set<string> }>()
    for (const persona of config.personas) {
      for (const link of persona.nav_links) {
        const href = link.href ?? ''
        if (!href) continue
        if (!map.has(href)) map.set(href, { label: link.label ?? href, roles: new Set() })
        map.get(href)!.roles.add(persona.code)
      }
    }
    return Array.from(map.entries()).map(([href, { label, roles }]) => ({
      to: href,
      label,
      roles: Array.from(roles),
    }))
  })()

  return { config, stageByCode, personaByCode, allStageCodes, roleHome, navLinks }
}
