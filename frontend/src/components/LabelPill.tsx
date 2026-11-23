import type { Label } from '../types'

/** A label pill; clickable (a button) when `onClick` is given, e.g. to filter. */
export function LabelPill({
  label,
  onClick,
  selected,
  title,
}: {
  label: Label
  onClick?: () => void
  selected?: boolean
  title?: string
}) {
  const content = (
    <>
      <span className="pill-dot" style={{ background: label.dot }} />
      {label.name}
    </>
  )
  const style = { background: label.bg, color: label.fg }
  if (!onClick) {
    return (
      <span className="label-pill" style={style}>
        {content}
      </span>
    )
  }
  return (
    <button
      type="button"
      className={`label-pill clickable${selected ? ' selected' : ''}`}
      style={style}
      aria-pressed={selected}
      title={title}
      onClick={(e) => {
        e.stopPropagation() // on a card tile: filter, don't open the card
        onClick()
      }}
    >
      {content}
    </button>
  )
}

export function cardLabels(labelIds: string[], labelMap: Record<string, Label>): Label[] {
  return labelIds.map((id) => labelMap[id]).filter(Boolean)
}

export function checklistStats(checklist: { done: boolean }[]) {
  const total = checklist.length
  const done = checklist.filter((x) => x.done).length
  return {
    total,
    done,
    pct: total ? Math.round((done / total) * 100) : 0,
    text: `${done}/${total}`,
    has: total > 0,
  }
}
