/** Board label filter: view state only (no data changes), kept in the URL
 *  hash so it survives reloads, e.g. `#label=l1&label=l2&unlabelled=1`.
 *  A card is shown when it has ANY selected label (or no label at all, when
 *  "No label" is selected). An empty selection shows every card. */

export interface LabelFilter {
  labelIds: string[]
  unlabelled: boolean
}

export const NO_FILTER: LabelFilter = { labelIds: [], unlabelled: false }

export function isFilterActive(f: LabelFilter): boolean {
  return f.labelIds.length > 0 || f.unlabelled
}

export function matchesLabelFilter(cardLabelIds: string[], f: LabelFilter): boolean {
  if (!isFilterActive(f)) return true
  if (cardLabelIds.length === 0) return f.unlabelled
  return cardLabelIds.some((id) => f.labelIds.includes(id))
}

export function toggleFilterLabel(f: LabelFilter, labelId: string): LabelFilter {
  const labelIds = f.labelIds.includes(labelId) ? f.labelIds.filter((id) => id !== labelId) : [...f.labelIds, labelId]
  return { ...f, labelIds }
}

/** Drop ids of labels that no longer exist (deleted, or a stale URL). */
export function pruneFilter(f: LabelFilter, existingLabelIds: string[]): LabelFilter {
  const labelIds = f.labelIds.filter((id) => existingLabelIds.includes(id))
  return labelIds.length === f.labelIds.length ? f : { ...f, labelIds }
}

export function filterFromHash(hash: string): LabelFilter {
  const params = new URLSearchParams(hash.replace(/^#/, ''))
  return { labelIds: params.getAll('label'), unlabelled: params.get('unlabelled') === '1' }
}

/** The URL hash for a filter, '' when no filter is active. */
export function filterToHash(f: LabelFilter): string {
  const params = new URLSearchParams()
  f.labelIds.forEach((id) => params.append('label', id))
  if (f.unlabelled) params.set('unlabelled', '1')
  const s = params.toString()
  return s ? `#${s}` : ''
}
