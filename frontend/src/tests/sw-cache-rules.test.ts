/**
 * CI gate: assert that the service worker NETWORK_ONLY_PATTERNS cover every
 * sensitive API route family.  A future PR cannot silently add a caching rule
 * for /api/clients, /api/cases, etc. without this test failing.
 *
 * This test reads sw.ts as source text and verifies the pattern list.
 */
import { readFileSync } from 'fs'
import { resolve } from 'path'
import { describe, it, expect } from 'vitest'

const SW_SOURCE = readFileSync(resolve(__dirname, '../sw.ts'), 'utf-8')

const REQUIRED_PATTERNS = [
  '/api/',
  '/socket.io/',
]

describe('Service Worker cache rules', () => {
  it('registers NetworkOnly for all sensitive API namespaces', () => {
    for (const required of REQUIRED_PATTERNS) {
      // Check the raw regex pattern appears in the source
      expect(SW_SOURCE, `Missing NetworkOnly pattern for: ${required}`).toContain(
        required.replace(/\./g, '\\.').replace(/\//g, '\\/')
      )
    }
  })

  it('does not register a caching strategy for /api/ routes', () => {
    // Ensure there is no NetworkFirst / CacheFirst / StaleWhileRevalidate call
    // that matches any /api/ path (a simple heuristic — the CI gate catches accidents)
    const cachingStrategies = ['NetworkFirst', 'CacheFirst', 'StaleWhileRevalidate']
    for (const strategy of cachingStrategies) {
      if (SW_SOURCE.includes(strategy)) {
        // If a caching strategy is used, it must NOT be paired with /api/
        const strategyBlocks = SW_SOURCE.split(strategy)
        for (const block of strategyBlocks.slice(1)) {
          const nearbyContext = block.slice(0, 200)
          expect(nearbyContext, `${strategy} must not be used for /api/ routes`).not.toMatch(
            /\/api\//
          )
        }
      }
    }
  })

  it('NETWORK_ONLY_PATTERNS covers /api/ and /socket.io/', () => {
    expect(SW_SOURCE).toContain('/\\/api\\//')
    expect(SW_SOURCE).toContain('/\\/socket\\.io\\//')
  })
})
