import type { Label } from '../types'

export function LabelPill({ label }: { label: Label }) {
  return (
    <span className="label-pill" style={{ background: label.bg, color: label.fg }}>
      <span className="pill-dot" style={{ background: label.dot }} />
      {label.name}
    </span>
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
