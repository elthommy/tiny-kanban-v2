import { Fragment } from 'react'
import type { KeyboardEvent } from 'react'
import type { BoardActions } from '../actions'
import type { Card, Column, Label } from '../types'
import { LabelPill, cardLabels, checklistStats } from './LabelPill'

interface BoardProps {
  columns: Column[]
  cards: Record<string, Card>
  labelMap: Record<string, Label>
  menuColId: string | null
  dragging: string | null
  dragOverCol: string | null
  dragOverCard: string | null
  draggingCol: string | null
  colDropBefore: string | null | undefined // undefined = no drop target yet
  actions: BoardActions
}

function dueBadge(dueDate: string) {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const due = new Date(`${dueDate}T00:00:00`)
  const days = Math.round((due.getTime() - today.getTime()) / 86400000)
  return {
    cls: days < 0 ? ' overdue' : days <= 1 ? ' soon' : '',
    text: due.toLocaleDateString(undefined, {
      day: 'numeric',
      month: 'short',
      ...(due.getFullYear() !== today.getFullYear() && { year: 'numeric' }),
    }),
  }
}

function submitOnEnter(e: KeyboardEvent<HTMLInputElement>, submit: (value: string) => void) {
  if (e.key === 'Enter' && e.currentTarget.value.trim()) {
    submit(e.currentTarget.value.trim())
    e.currentTarget.value = ''
  }
}

function CardTile({
  card,
  colId,
  labelMap,
  showIndicator,
  actions,
}: {
  card: Card
  colId: string
  labelMap: Record<string, Label>
  showIndicator: boolean
  actions: BoardActions
}) {
  const labels = cardLabels(card.labels, labelMap)
  const stats = checklistStats(card.checklist)
  const due = card.dueDate ? dueBadge(card.dueDate) : null
  return (
    <>
      {showIndicator && <div className="drop-indicator" />}
      <div
        className="card"
        draggable
        onDragStart={(e) => actions.cardDragStart(e, card.id)}
        onDragEnd={actions.cardDragEnd}
        onDragOver={(e) => actions.cardDragOver(e, colId, card.id)}
        onClick={() => actions.openCard(card.id)}
      >
        {labels.length > 0 && (
          <div className="card-labels">
            {labels.map((l) => (
              <LabelPill key={l.id} label={l} />
            ))}
          </div>
        )}
        <div className="card-title">{card.title}</div>
        {due && (
          <div className={`due-badge${due.cls}`}>
            <span className="due-flag">⚑</span>
            {due.text}
          </div>
        )}
        {stats.has && (
          <div className="progress-row">
            <div className="progress-track">
              <div className="progress-fill" style={{ width: `${stats.pct}%` }} />
            </div>
            <span className="progress-text">{stats.text}</span>
          </div>
        )}
      </div>
    </>
  )
}

function BoardColumn({
  column,
  cards,
  labelMap,
  menuOpen,
  dragging,
  dragOverCol,
  dragOverCard,
  isDragSource,
  actions,
}: {
  column: Column
  cards: Card[]
  labelMap: Record<string, Label>
  menuOpen: boolean
  dragging: string | null
  dragOverCol: string | null
  dragOverCard: string | null
  isDragSource: boolean
  actions: BoardActions
}) {
  const showEndIndicator = !!dragging && dragOverCol === column.id && !dragOverCard
  return (
    <div
      className={`column${isDragSource ? ' drag-src' : ''}`}
      onDragOver={(e) => actions.columnDragOver(e, column.id)}
      onDrop={(e) => actions.drop(e, column.id)}
    >
      <div
        className="col-head"
        draggable
        onDragStart={(e) => actions.colDragStart(e, column.id)}
        onDragEnd={actions.colDragEnd}
      >
        <input
          className="col-title"
          value={column.title}
          onChange={(e) => actions.renameColumn(column.id, e.target.value)}
        />
        <span className="col-count">{cards.length}</span>
        <button
          className="col-menu-btn"
          onClick={(e) => {
            e.stopPropagation()
            actions.toggleColumnMenu(column.id)
          }}
        >
          ⋯
        </button>
        {menuOpen && (
          <div className="col-menu">
            <button className="menu-item" onClick={() => actions.addCard(column.id, 'New card')}>
              Add a card
            </button>
            <button className="menu-item" onClick={() => actions.archiveAll(column.id)}>
              Archive all cards
            </button>
            <div className="menu-sep" />
            <button className="menu-item danger" onClick={() => actions.deleteColumn(column.id)}>
              Delete column
            </button>
          </div>
        )}
      </div>
      <div className="col-cards">
        {cards.map((card) => (
          <CardTile
            key={card.id}
            card={card}
            colId={column.id}
            labelMap={labelMap}
            showIndicator={!!dragging && dragOverCard === card.id}
            actions={actions}
          />
        ))}
        {showEndIndicator && <div className="drop-indicator" />}
      </div>
      <div className="add-card-wrap">
        <input
          className="dashed-input"
          placeholder="+  Add a card"
          onKeyDown={(e) => submitOnEnter(e, (v) => actions.addCard(column.id, v))}
        />
      </div>
    </div>
  )
}

export default function Board({
  columns,
  cards,
  labelMap,
  menuColId,
  dragging,
  dragOverCol,
  dragOverCard,
  draggingCol,
  colDropBefore,
  actions,
}: BoardProps) {
  return (
    <div className="board">
      {columns.map((col) => (
        <Fragment key={col.id}>
          {draggingCol && colDropBefore === col.id && <div className="col-drop-indicator" />}
          <BoardColumn
            column={col}
            cards={col.cardIds.map((id) => cards[id]).filter((c) => c && !c.archived)}
            labelMap={labelMap}
            menuOpen={menuColId === col.id}
            dragging={dragging}
            dragOverCol={dragOverCol}
            dragOverCard={dragOverCard}
            isDragSource={draggingCol === col.id}
            actions={actions}
          />
        </Fragment>
      ))}
      {draggingCol && colDropBefore === null && <div className="col-drop-indicator" />}
      <div className="add-col" onDragOver={actions.boardEndDragOver} onDrop={(e) => actions.drop(e, '')}>
        <input
          className="add-col-input"
          placeholder="+  Add another column"
          onKeyDown={(e) => submitOnEnter(e, actions.addColumn)}
        />
      </div>
    </div>
  )
}
