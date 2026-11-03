import type { SnoozedActions } from '../actions'
import { formatDay } from '../dates'
import type { Card, Label } from '../types'
import { LabelPill, cardLabels } from './LabelPill'

interface SnoozedViewProps {
  snoozed: Card[] // soonest wake-up first
  columnOf: Record<string, string> // card id -> title of the column it waits in
  labelMap: Record<string, Label>
  actions: SnoozedActions
}

export default function SnoozedView({ snoozed, columnOf, labelMap, actions }: SnoozedViewProps) {
  return (
    <div className="archive">
      <div className="archive-inner">
        <div className="archive-title">Snoozed cards</div>
        <div className="archive-sub">
          Hidden from the board until their date, then back in place on their own. Wake one up early, or change
          its date.
        </div>
        {snoozed.length > 0 && (
          <div className="archive-list">
            {snoozed.map((card) => {
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
                    <button className="archive-item-title snoozed-open" onClick={() => actions.openCard(card.id)}>
                      {card.title}
                    </button>
                    <div className="archive-item-origin">
                      wakes {card.snoozedUntil && formatDay(card.snoozedUntil)} · in {columnOf[card.id] ?? '?'}
                    </div>
                  </div>
                  <button className="btn-archive-delete" onClick={() => actions.changeDate(card.id)}>
                    Change date
                  </button>
                  <button className="btn-restore" onClick={() => actions.unsnooze(card.id)}>
                    Wake now
                  </button>
                </div>
              )
            })}
          </div>
        )}
        {snoozed.length === 0 && (
          <div className="empty-box">No snoozed cards. Snooze one from its card window to hide it until a date.</div>
        )}
      </div>
    </div>
  )
}
