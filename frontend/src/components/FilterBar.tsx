import type { LabelFilter } from '../filter'
import { isFilterActive } from '../filter'
import type { Label } from '../types'
import { LabelPill } from './LabelPill'

/** Row of label chips above the board: click to show only matching cards. */
export default function FilterBar({
  labels,
  filter,
  onToggleLabel,
  onToggleUnlabelled,
  onClear,
}: {
  labels: Label[]
  filter: LabelFilter
  onToggleLabel: (labelId: string) => void
  onToggleUnlabelled: () => void
  onClear: () => void
}) {
  const active = isFilterActive(filter)
  return (
    <div className={`filter-bar${active ? ' active' : ''}`} role="toolbar" aria-label="Filter by label">
      <span className="filter-title">Filter</span>
      {labels.map((l) => (
        <LabelPill
          key={l.id}
          label={l}
          selected={filter.labelIds.includes(l.id)}
          onClick={() => onToggleLabel(l.id)}
        />
      ))}
      <button
        type="button"
        className={`label-pill clickable no-label${filter.unlabelled ? ' selected' : ''}`}
        aria-pressed={filter.unlabelled}
        onClick={onToggleUnlabelled}
      >
        No label
      </button>
      {active && (
        <button type="button" className="filter-clear" onClick={onClear}>
          ✕ Clear
        </button>
      )}
    </div>
  )
}
