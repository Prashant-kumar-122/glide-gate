const MONTH_ABBR: Record<string, string> = {
  jan: '01', feb: '02', mar: '03', apr: '04', may: '05', jun: '06',
  jul: '07', aug: '08', sep: '09', oct: '10', nov: '11', dec: '12',
}

/**
 * Normalize any common date format to YYYY-MM-DD.
 * Handles: YYYY-MM-DD, YYYY/MM/DD, DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY,
 *          MM/DD/YYYY (US), DD MMM YYYY, MMM DD YYYY, MMM DD, YYYY, Date.parse fallback.
 * When DD and MM are both ≤ 12 (ambiguous), DD/MM/YYYY is assumed (international KYC standard).
 */
export function normalizeDateToISO(raw: string): string {
  const v = raw.trim()

  // Already YYYY-MM-DD
  if (/^\d{4}-\d{2}-\d{2}$/.test(v)) return v

  // YYYY/MM/DD or YYYY.MM.DD
  let m = v.match(/^(\d{4})[/.](\d{1,2})[/.](\d{1,2})$/)
  if (m) return `${m[1]}-${m[2].padStart(2, '0')}-${m[3].padStart(2, '0')}`

  // DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY (swap when "month" part > 12 → MM/DD/YYYY)
  m = v.match(/^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})$/)
  if (m) {
    let [, d, mo, yr] = m
    if (parseInt(mo) > 12 && parseInt(d) <= 12) [d, mo] = [mo, d]
    return `${yr}-${mo.padStart(2, '0')}-${d.padStart(2, '0')}`
  }

  // DD MMM YYYY or DD MMMM YYYY  e.g. "14 Jun 1989", "14 June 1989"
  m = v.match(/^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$/)
  if (m) {
    const mo = MONTH_ABBR[m[2].toLowerCase().slice(0, 3)]
    if (mo) return `${m[3]}-${mo}-${m[1].padStart(2, '0')}`
  }

  // MMM DD, YYYY or MMMM DD, YYYY  e.g. "Jun 14, 1989", "June 14, 1989"
  m = v.match(/^([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})$/)
  if (m) {
    const mo = MONTH_ABBR[m[1].toLowerCase().slice(0, 3)]
    if (mo) return `${m[3]}-${mo}-${m[2].padStart(2, '0')}`
  }

  // Fallback: let the JS engine try (handles RFC 2822, ISO 8601 variants, etc.)
  const ts = Date.parse(v)
  if (!isNaN(ts)) {
    const d = new Date(ts)
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  }

  return v
}
