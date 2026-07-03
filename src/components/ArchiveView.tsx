import type { ArchiveActions } from '../actions'
import type { Card, Label } from '../types'
import { LabelPill, cardLabels } from './LabelPill'

interface ArchiveViewProps {
  archived: Card[]
  filtered: Card[]
  query: string
  columnTitles: Record<string, string>
  labelMap: Record<string, Label>
  actions: ArchiveActions
}

export default function ArchiveView({ archived, filtered, query, columnTitles, labelMap, actions }: ArchiveViewProps) {
  return (
    <div className="archive">
      <div className="archive-inner">
        <div className="archive-title">Archived cards</div>
        <div className="archive-sub">Restore a card to its original column, or remove it for good.</div>
        {archived.length > 0 && (
          <input
            className="archive-search"
            value={query}
            onChange={(e) => actions.setQuery(e.target.value)}
            placeholder="Search archived cards…"
          />
        )}
        {filtered.length > 0 && (
          <div className="archive-list">
            {filtered.map((card) => {
              const labels = cardLabels(card.labels, labelMap)
              return (
                <div key={card.id} className="archive-item">
                  <div className="archive-item-body">
                    {labels.length > 0 && (
                      <div className="archive-item-labels">
                        {labels.map((l) => (
                          <LabelPill key={l.id} label={l} />
                        ))}
                      </div>
                    )}
                    <div className="archive-item-title">{card.title}</div>
                    <div className="archive-item-origin">
                      from {(card.archivedFrom && columnTitles[card.archivedFrom]) || 'a deleted column'}
                    </div>
                  </div>
                  <button className="btn-restore" onClick={() => actions.restore(card.id)}>
                    Restore
                  </button>
                  <button className="btn-archive-delete" onClick={() => actions.deleteForever(card.id)}>
                    Delete
                  </button>
                </div>
              )
            })}
          </div>
        )}
        {archived.length > 0 && filtered.length === 0 && (
          <div className="empty-box">No archived cards match your search.</div>
        )}
        {archived.length === 0 && <div className="empty-box">No archived cards yet.</div>}
      </div>
    </div>
  )
}
