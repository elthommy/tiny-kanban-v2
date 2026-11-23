import { describe, expect, it } from 'vitest'
import {
  NO_FILTER,
  filterFromHash,
  filterToHash,
  isFilterActive,
  matchesLabelFilter,
  pruneFilter,
  toggleFilterLabel,
} from './filter'

describe('matchesLabelFilter', () => {
  it('shows every card when no filter is active', () => {
    expect(matchesLabelFilter([], NO_FILTER)).toBe(true)
    expect(matchesLabelFilter(['l1'], NO_FILTER)).toBe(true)
  })

  it('shows cards having any of the selected labels', () => {
    const f = { labelIds: ['l1', 'l2'], unlabelled: false }
    expect(matchesLabelFilter(['l2', 'l9'], f)).toBe(true)
    expect(matchesLabelFilter(['l9'], f)).toBe(false)
    expect(matchesLabelFilter([], f)).toBe(false)
  })

  it('shows unlabelled cards only when "No label" is selected', () => {
    const f = { labelIds: ['l1'], unlabelled: true }
    expect(matchesLabelFilter([], f)).toBe(true)
    expect(matchesLabelFilter(['l1'], f)).toBe(true)
    expect(matchesLabelFilter(['l2'], { labelIds: [], unlabelled: true })).toBe(false)
  })
})

describe('filter state', () => {
  it('toggles a label on and off', () => {
    const on = toggleFilterLabel(NO_FILTER, 'l1')
    expect(on.labelIds).toEqual(['l1'])
    expect(isFilterActive(on)).toBe(true)
    expect(isFilterActive(toggleFilterLabel(on, 'l1'))).toBe(false)
  })

  it('drops deleted labels', () => {
    const f = { labelIds: ['l1', 'gone'], unlabelled: false }
    expect(pruneFilter(f, ['l1', 'l2']).labelIds).toEqual(['l1'])
    expect(pruneFilter(NO_FILTER, [])).toBe(NO_FILTER)
  })

  it('round-trips through the URL hash', () => {
    const f = { labelIds: ['l1', 'a&b=c'], unlabelled: true }
    expect(filterFromHash(filterToHash(f))).toEqual(f)
    expect(filterToHash(NO_FILTER)).toBe('')
    expect(filterFromHash('')).toEqual(NO_FILTER)
  })
})
