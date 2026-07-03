import { useEffect, useRef } from 'react'
import type { KeyboardEvent } from 'react'
import type { CardActions, LabelEditorActions } from '../actions'
import { PALETTE } from '../config'
import type { Card, Label } from '../types'
import { checklistStats } from './LabelPill'

interface CardModalProps {
  card: Card
  labels: Label[]
  labelEditorOpen: boolean
  colorPickerLabel: string | null
  actions: CardActions
  labelActions: LabelEditorActions
}

export default function CardModal({ card, labels, labelEditorOpen, colorPickerLabel, actions, labelActions }: CardModalProps) {
  const stats = checklistStats(card.checklist)
  const titleRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    const onKey = (e: globalThis.KeyboardEvent) => {
      if (e.key === 'Escape') actions.close()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [actions])

  // keep the title textarea sized to its content
  useEffect(() => {
    const el = titleRef.current
    if (el) {
      el.style.height = 'auto'
      el.style.height = `${el.scrollHeight}px`
    }
  }, [card.title])

  const onAddChecklist = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && e.currentTarget.value.trim()) {
      actions.addCheckItem(e.currentTarget.value.trim())
      e.currentTarget.value = ''
    }
  }

  return (
    <div className="modal-backdrop" onClick={actions.close}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div className="modal-kicker">Card</div>
          <button className="modal-close" onClick={actions.close}>
            ×
          </button>
        </div>

        <textarea
          ref={titleRef}
          className="modal-title"
          value={card.title}
          onChange={(e) => actions.setTitle(e.target.value)}
          rows={1}
        />

        <div className="section-row">
          <div className="section-label">LABELS</div>
          <button className="link-btn" onClick={labelActions.toggleEditor}>
            {labelEditorOpen ? 'Done' : 'Edit labels'}
          </button>
        </div>
        <div className="chip-row">
          {labels.map((l) => {
            const selected = card.labels.includes(l.id)
            return (
              <button
                key={l.id}
                className={`label-chip${selected ? '' : ' off'}`}
                style={selected ? { background: l.bg, color: l.fg, border: '1px solid transparent' } : undefined}
                onClick={() => actions.toggleLabel(l.id)}
              >
                <span className="chip-dot" style={{ background: l.dot }} />
                {l.name}
              </button>
            )
          })}
        </div>
        {labelEditorOpen && (
          <div className="label-editor">
            {labels.map((l) => (
              <div key={l.id} className="label-row">
                <div className="label-row-main">
                  <button
                    className="swatch-btn"
                    style={{ background: l.dot }}
                    onClick={() => labelActions.togglePicker(l.id)}
                  />
                  <input
                    className="label-name-input"
                    value={l.name}
                    onChange={(e) => labelActions.renameLabel(l.id, e.target.value)}
                  />
                  <button className="label-del" onClick={() => labelActions.deleteLabel(l.id)}>
                    ×
                  </button>
                </div>
                {colorPickerLabel === l.id && (
                  <div className="palette-row">
                    {PALETTE.map((c) => (
                      <button
                        key={c.dot}
                        className="palette-sw"
                        style={{ background: c.dot }}
                        onClick={() => labelActions.setColor(l.id, c)}
                      />
                    ))}
                  </div>
                )}
              </div>
            ))}
            <button className="add-label-btn" onClick={labelActions.addLabel}>
              +  Add label
            </button>
          </div>
        )}

        <div className="section-label" style={{ marginBottom: 8 }}>
          DESCRIPTION
        </div>
        <textarea
          className="desc-input"
          value={card.description}
          onChange={(e) => actions.setDescription(e.target.value)}
          placeholder="Add more detail…"
          rows={3}
        />

        <div className="check-head">
          <div className="section-label">CHECKLIST</div>
          {stats.has && (
            <div className="check-progress">
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${stats.pct}%` }} />
              </div>
              <span className="progress-text">{stats.text}</span>
            </div>
          )}
        </div>
        <div className="check-list">
          {card.checklist.map((it) => (
            <div key={it.id} className="check-item">
              <input type="checkbox" checked={it.done} onChange={() => actions.toggleCheckItem(it.id)} />
              <span className={`check-text${it.done ? ' done' : ''}`}>{it.text}</span>
              <button className="check-del" onClick={() => actions.deleteCheckItem(it.id)}>
                ×
              </button>
            </div>
          ))}
        </div>
        <input className="dashed-input add-check" placeholder="+  Add an item, press Enter" onKeyDown={onAddChecklist} />

        <div className="modal-footer">
          <button className="btn-archive-card" onClick={actions.archiveCard}>
            Archive card
          </button>
          <button className="btn-delete-card" onClick={actions.deleteCard}>
            Delete
          </button>
        </div>
      </div>
    </div>
  )
}
