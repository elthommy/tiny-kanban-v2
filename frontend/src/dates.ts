/** Local-calendar date helpers for the snooze picker and labels.
 *
 * Dates are ISO "YYYY-MM-DD" strings in the user's local calendar — never via
 * toISOString(), which converts to UTC and can shift the day. The backend owns
 * the rule (a snooze date must be after today); this only builds suggestions.
 */

export interface SnoozePreset {
  label: string
  date: string // ISO "YYYY-MM-DD"
}

export function isoDate(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

export function parseIsoDate(iso: string): Date {
  return new Date(`${iso}T00:00:00`)
}

export function addDays(d: Date, days: number): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate() + days)
}

/** Same day next month(s), clamped to the month's last day (31 Jan → 28/29 Feb). */
export function addMonths(d: Date, months: number): Date {
  const lastDay = new Date(d.getFullYear(), d.getMonth() + months + 1, 0).getDate()
  return new Date(d.getFullYear(), d.getMonth() + months, Math.min(d.getDate(), lastDay))
}

/** Quick picks for the snooze popup. "Next Monday" on a Monday is a week away. */
export function snoozePresets(today: Date = new Date()): SnoozePreset[] {
  const daysToMonday = (8 - today.getDay()) % 7 || 7
  return [
    { label: 'Tomorrow', date: isoDate(addDays(today, 1)) },
    { label: 'Next Monday', date: isoDate(addDays(today, daysToMonday)) },
    { label: 'In 1 week', date: isoDate(addDays(today, 7)) },
    { label: 'In 1 month', date: isoDate(addMonths(today, 1)) },
  ]
}

/** "Tue 12 Nov" (the year is added when it isn't the current one). */
export function formatDay(iso: string, today: Date = new Date()): string {
  const d = parseIsoDate(iso)
  return d.toLocaleDateString(undefined, {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    ...(d.getFullYear() !== today.getFullYear() && { year: 'numeric' }),
  })
}
