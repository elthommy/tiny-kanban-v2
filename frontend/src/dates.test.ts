import { describe, expect, it } from 'vitest'
import { addMonths, isoDate, snoozePresets } from './dates'

const day = (y: number, m: number, d: number) => new Date(y, m - 1, d)

describe('snoozePresets', () => {
  it('builds local dates from a Tuesday', () => {
    expect(snoozePresets(day(2026, 11, 3))).toEqual([
      { label: 'Tomorrow', date: '2026-11-04' },
      { label: 'Next Monday', date: '2026-11-09' },
      { label: 'In 1 week', date: '2026-11-10' },
      { label: 'In 1 month', date: '2026-12-03' },
    ])
  })

  it('puts next Monday a week away on a Monday, and tomorrow on a Sunday', () => {
    expect(snoozePresets(day(2026, 11, 9))[1].date).toBe('2026-11-16')
    expect(snoozePresets(day(2026, 11, 8))[1].date).toBe('2026-11-09')
  })

  it('crosses month and year ends', () => {
    const presets = snoozePresets(day(2026, 12, 31))
    expect(presets[0].date).toBe('2027-01-01')
    expect(presets[3].date).toBe('2027-01-31')
  })
})

describe('addMonths', () => {
  it('clamps to the last day of a shorter month', () => {
    expect(isoDate(addMonths(day(2027, 1, 31), 1))).toBe('2027-02-28')
    expect(isoDate(addMonths(day(2028, 1, 31), 1))).toBe('2028-02-29')
  })
})
