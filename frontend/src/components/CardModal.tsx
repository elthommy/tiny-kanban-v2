import { useEffect, useRef, useState } from 'react'
import type { KeyboardEvent } from 'react'
import type { CardActions, LabelEditorActions } from '../actions'
import { PALETTE } from '../config'
import type { Card, Column, Label } from '../types'
import { checklistStats } from './LabelPill'

interface CardModalProps {
  card: Card
  cards: Record<string, Card>
  columns: Column[]
  labels: Label[]
  labelEditorOpen: boolean
  colorPickerLabel: string | null
  actions: CardActions
  labelActions: LabelEditorActions
}

export default function CardModal({
  card,
  cards,
  columns,
  labels,
  labelEditorOpen,
  colorPickerLabel,
  actions,
  labelActions,
}: CardModalProps) {
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
          DUE DATE
        </div>
        <div className="due-row">
          <input
            type="date"
            className="due-input"
            value={card.dueDate ?? ''}
            onChange={(e) => actions.setDueDate(e.target.value || null)}
            aria-label="Due date"
          />
          {card.dueDate && (
            <button className="due-clear" onClick={() => actions.setDueDate(null)} title="Remove due date">
              ×
            </button>
          )}
        </div>

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
              <input
                className={`check-text-input${it.done ? ' done' : ''}`}
                value={it.text}
                onChange={(e) => actions.setCheckItemText(it.id, e.target.value)}
              />
              <button className="check-del" onClick={() => actions.deleteCheckItem(it.id)}>
                ×
              </button>
            </div>
          ))}
        </div>
        <input className="dashed-input add-check" placeholder="+  Add an item, press Enter" onKeyDown={onAddChecklist} />

        <DependencySection card={card} cards={cards} columns={columns} actions={actions} />

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

function DependencySection({
  card,
  cards,
  columns,
  actions,
}: {
  card: Card
  cards: Record<string, Card>
  columns: Column[]
  actions: CardActions
}) {
  const columnOf: Record<string, string> = {}
  for (const col of columns) for (const id of col.cardIds) columnOf[id] = col.title
  const where = (c: Card) => (c.archived ? 'Archived' : columnOf[c.id] ?? '')
  const linked = new Set(card.dependsOn.map((d) => d.cardId))
  // Board cards in board order; cycles are rejected by the backend
  const candidates = columns
    .flatMap((col) => col.cardIds)
    .filter((id) => id !== card.id && !linked.has(id) && cards[id])
    .map((id) => cards[id])

  return (
    <>
      <div className="section-label" style={{ marginBottom: 8 }}>
        DEPENDS ON
      </div>
      <div className="check-list">
        {card.dependsOn.map((dep) => {
          const other = cards[dep.cardId]
          if (!other) return null
          return (
            <div key={dep.cardId} className="check-item">
              <span className={`dep-status${dep.resolved ? ' resolved' : ''}`} title={dep.resolved ? 'Done' : 'Not done yet'}>
                {dep.resolved ? '✓' : '○'}
              </span>
              <button className={`dep-link${dep.resolved ? ' done' : ''}`} onClick={() => actions.openCard(other.id)}>
                {other.title}
              </button>
              <span className="dep-where">{where(other)}</span>
              <button className="check-del" onClick={() => actions.removeDependency(other.id)} title="Remove dependency">
                ×
              </button>
            </div>
          )
        })}
      </div>
      <DependencyPicker candidates={candidates} where={where} onPick={actions.addDependency} />

      {card.blocks.length > 0 && (
        <>
          <div className="section-label" style={{ marginBottom: 8 }}>
            BLOCKS
          </div>
          <div className="check-list add-check">
            {card.blocks
              .map((id) => cards[id])
              .filter(Boolean)
              .map((other) => (
                <div key={other.id} className="check-item">
                  <button className="dep-link" onClick={() => actions.openCard(other.id)}>
                    {other.title}
                  </button>
                  <span className="dep-where">{where(other)}</span>
                </div>
              ))}
          </div>
        </>
      )}
    </>
  )
}

/** Type-to-filter picker for adding a dependency (all words must match title or column). */
function DependencyPicker({
  candidates,
  where,
  onPick,
}: {
  candidates: Card[]
  where: (c: Card) => string
  onPick: (cardId: string) => void
}) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)

  const words = query.toLowerCase().split(/\s+/).filter(Boolean)
  const matches = candidates.filter((c) => {
    const hay = `${c.title} ${where(c)}`.toLowerCase()
    return words.every((w) => hay.includes(w))
  })
  const current = Math.min(active, Math.max(matches.length - 1, 0))

  const pick = (c: Card) => {
    onPick(c.id)
    setQuery('')
    setActive(0)
  }

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setOpen(true)
      setActive(Math.min(current + 1, matches.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActive(Math.max(current - 1, 0))
    } else if (e.key === 'Enter' && open && matches[current]) {
      e.preventDefault()
      pick(matches[current])
    } else if (e.key === 'Escape' && (open || query)) {
      e.stopPropagation() // close the list, not the modal
      setOpen(false)
      setQuery('')
    }
  }

  return (
    <div className="dep-picker add-check">
      <input
        className="dashed-input"
        placeholder={candidates.length ? '+  Add a card this one depends on…' : 'No other cards to depend on'}
        disabled={!candidates.length}
        value={query}
        onChange={(e) => {
          setQuery(e.target.value)
          setActive(0)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={onKeyDown}
        role="combobox"
        aria-expanded={open}
        aria-label="Add a dependency"
      />
      {open && (
        <div className="dep-options" role="listbox">
          {matches.length === 0 && <div className="dep-option empty">No matching card</div>}
          {matches.map((c, i) => (
            <div
              key={c.id}
              role="option"
              aria-selected={i === current}
              className={`dep-option${i === current ? ' active' : ''}`}
              onMouseDown={(e) => e.preventDefault()} // keep focus so the list stays open
              onMouseEnter={() => setActive(i)}
              onClick={() => pick(c)}
            >
              <span className="dep-option-title">{c.title}</span>
              <span className="dep-where">{where(c)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
