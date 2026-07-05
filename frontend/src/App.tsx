import { useEffect, useMemo, useRef, useState } from 'react'
import type { ArchiveActions, BoardActions, CardActions, LabelEditorActions } from './actions'
import { api, loadBoard } from './api'
import { ARCHIVE_SORT, CONFIRM_DELETE, NEW_CARD_POSITION } from './config'
import type { LabelColor } from './config'
import type { BoardData, Card, Column, Label } from './types'
import ArchiveView from './components/ArchiveView'
import Board from './components/Board'
import CardModal from './components/CardModal'

function confirmOk(msg: string): boolean {
  return !CONFIRM_DELETE || window.confirm(msg)
}

export default function App() {
  const [board, setBoard] = useState<BoardData | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)

  const load = () => {
    setLoadError(null)
    loadBoard()
      .then(setBoard)
      .catch((err: unknown) => setLoadError(err instanceof Error ? err.message : String(err)))
  }
  useEffect(load, [])

  if (loadError) {
    return (
      <div className="app-status">
        <p>Cannot reach the backend ({loadError}).</p>
        <p>
          Start it with <code>./start.sh</code>, then retry.
        </p>
        <button onClick={load}>Retry</button>
      </div>
    )
  }
  if (!board) return <div className="app-status">Loading…</div>
  return <KanbanApp initial={board} />
}

/** Display layer only: board rules live in the backend (service.py). Actions
 *  call the API and adopt the returned board; text edits update local state
 *  optimistically while api.ts debounces the PATCH behind the scenes. */
function KanbanApp({ initial }: { initial: BoardData }) {
  const [data, setData] = useState<BoardData>(initial)
  const [actionError, setActionError] = useState<string | null>(null)
  const [view, setView] = useState<'board' | 'archive'>('board')
  const [openCardId, setOpenCardId] = useState<string | null>(null)
  const [menuColId, setMenuColId] = useState<string | null>(null)
  const [dragging, setDragging] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState<{ col: string | null; card: string | null }>({ col: null, card: null })
  const [labelEditorOpen, setLabelEditorOpen] = useState(false)
  const [colorPickerLabel, setColorPickerLabel] = useState<string | null>(null)
  const [archiveQuery, setArchiveQuery] = useState('')
  const dragCardId = useRef<string | null>(null)

  /** Run a structural mutation and adopt the server's board. */
  const apply = (mutation: Promise<BoardData>) => {
    mutation
      .then((b) => {
        setData(b)
        setActionError(null)
      })
      .catch((err: unknown) => setActionError(err instanceof Error ? err.message : String(err)))
  }

  const labelMap = useMemo(() => {
    const m: Record<string, Label> = {}
    data.labels.forEach((l) => (m[l.id] = l))
    return m
  }, [data.labels])

  // Optimistic local updates backing the per-keystroke text inputs
  const patchColumns = (fn: (columns: Column[]) => Column[]) => setData((d) => ({ ...d, columns: fn(d.columns) }))
  const updateCard = (id: string, patch: Partial<Card>) =>
    setData((d) => (d.cards[id] ? { ...d, cards: { ...d.cards, [id]: { ...d.cards[id], ...patch } } } : d))

  const clearDrag = () => {
    dragCardId.current = null
    setDragging(null)
    setDragOver({ col: null, card: null })
  }

  const boardActions: BoardActions = {
    renameColumn: (colId, title) => {
      patchColumns((cols) => cols.map((c) => (c.id === colId ? { ...c, title } : c)))
      api.renameColumn(colId, title)
    },
    addCard: (colId, title) => {
      apply(api.addCard(colId, title, NEW_CARD_POSITION))
      setMenuColId(null)
    },
    addColumn: (title) => apply(api.addColumn(title)),
    archiveAll: (colId) => {
      apply(api.archiveAll(colId))
      setMenuColId(null)
    },
    deleteColumn: (colId) => {
      if (confirmOk('Delete this column? Its cards will be moved to Archive.')) {
        apply(api.deleteColumn(colId))
      }
      setMenuColId(null)
    },
    toggleColumnMenu: (colId) => setMenuColId((cur) => (cur === colId ? null : colId)),
    closeMenus: () => setMenuColId(null),
    openCard: (cardId) => {
      setOpenCardId(cardId)
      setMenuColId(null)
    },
    cardDragStart: (e, cardId) => {
      dragCardId.current = cardId
      e.dataTransfer.effectAllowed = 'move'
      try {
        e.dataTransfer.setData('text/plain', cardId)
      } catch {
        // some browsers restrict dataTransfer — the ref is the source of truth
      }
      setDragging(cardId)
    },
    cardDragEnd: clearDrag,
    cardDragOver: (e, colId, cardId) => {
      e.preventDefault()
      e.stopPropagation()
      setDragOver((cur) => (cur.col === colId && cur.card === cardId ? cur : { col: colId, card: cardId }))
    },
    columnDragOver: (e, colId) => {
      e.preventDefault()
      setDragOver((cur) => (cur.col === colId && cur.card === null ? cur : { col: colId, card: null }))
    },
    drop: (e, colId) => {
      e.preventDefault()
      const cardId = dragCardId.current
      const beforeId = dragOver.card
      clearDrag()
      if (cardId && cardId !== beforeId) apply(api.moveCard(cardId, colId, beforeId))
    },
  }

  const openCard = openCardId ? data.cards[openCardId] : null

  const cardActions: CardActions = {
    close: () => setOpenCardId(null),
    setTitle: (title) => {
      if (!openCardId) return
      updateCard(openCardId, { title })
      api.patchCardText(openCardId, { title })
    },
    setDescription: (description) => {
      if (!openCardId) return
      updateCard(openCardId, { description })
      api.patchCardText(openCardId, { description })
    },
    toggleLabel: (labelId) => {
      if (!openCard) return
      apply(
        openCard.labels.includes(labelId)
          ? api.removeCardLabel(openCard.id, labelId)
          : api.addCardLabel(openCard.id, labelId),
      )
    },
    addCheckItem: (text) => openCard && apply(api.addCheckItem(openCard.id, text)),
    toggleCheckItem: (itemId) => {
      if (!openCard) return
      const item = openCard.checklist.find((it) => it.id === itemId)
      if (item) apply(api.patchCheckItem(openCard.id, itemId, { done: !item.done }))
    },
    deleteCheckItem: (itemId) => openCard && apply(api.deleteCheckItem(openCard.id, itemId)),
    archiveCard: () => {
      if (!openCardId) return
      apply(api.archiveCard(openCardId))
      setOpenCardId(null)
    },
    deleteCard: () => {
      if (!openCardId || !confirmOk('Delete this card? This cannot be undone.')) return
      apply(api.deleteCard(openCardId))
      setOpenCardId(null)
    },
  }

  const labelActions: LabelEditorActions = {
    toggleEditor: () => {
      setLabelEditorOpen((v) => !v)
      setColorPickerLabel(null)
    },
    addLabel: () => apply(api.addLabel()),
    renameLabel: (labelId, name) => {
      setData((d) => ({ ...d, labels: d.labels.map((l) => (l.id === labelId ? { ...l, name } : l)) }))
      api.renameLabel(labelId, name)
    },
    deleteLabel: (labelId) => {
      apply(api.deleteLabel(labelId))
      setColorPickerLabel((cur) => (cur === labelId ? null : cur))
    },
    togglePicker: (labelId) => setColorPickerLabel((cur) => (cur === labelId ? null : labelId)),
    setColor: (labelId, color: LabelColor) => {
      apply(api.setLabelColor(labelId, color))
      setColorPickerLabel(null)
    },
  }

  const archived = useMemo(() => {
    const list = Object.values(data.cards).filter((c) => c.archived)
    list.sort((a, b) =>
      ARCHIVE_SORT === 'oldest' ? (a.archivedAt || 0) - (b.archivedAt || 0) : (b.archivedAt || 0) - (a.archivedAt || 0),
    )
    return list
  }, [data.cards])

  const q = archiveQuery.trim().toLowerCase()
  const filtered = archived.filter(
    (c) =>
      !q ||
      c.title.toLowerCase().includes(q) ||
      c.labels.some((id) => labelMap[id] && labelMap[id].name.toLowerCase().includes(q)),
  )

  const columnTitles = useMemo(() => {
    const m: Record<string, string> = {}
    data.columns.forEach((c) => (m[c.id] = c.title))
    return m
  }, [data.columns])

  const archiveActions: ArchiveActions = {
    setQuery: setArchiveQuery,
    restore: (cardId) => apply(api.restoreCard(cardId)),
    deleteForever: (cardId) => {
      if (!confirmOk('Permanently delete this card? This cannot be undone.')) return
      apply(api.deleteCard(cardId))
    },
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand-row">
          <div className="brand">Tiny-kanban v2</div>
          <input
            className="brand-sub"
            value={data.subtitle}
            aria-label="Board subtitle"
            onChange={(e) => {
              const subtitle = e.target.value
              setData((d) => ({ ...d, subtitle }))
              api.setSubtitle(subtitle)
            }}
          />
        </div>
        <div className="seg">
          <button
            className={`seg-btn${view === 'board' ? ' active' : ''}`}
            onClick={() => {
              setView('board')
              setMenuColId(null)
            }}
          >
            Board
          </button>
          <button
            className={`seg-btn${view === 'archive' ? ' active' : ''}`}
            onClick={() => {
              setView('archive')
              setMenuColId(null)
            }}
          >
            Archive · {archived.length}
          </button>
        </div>
      </header>

      {actionError && (
        <div className="action-error">
          <span>Sync failed: {actionError}</span>
          <button onClick={() => setActionError(null)}>×</button>
        </div>
      )}

      {view === 'board' ? (
        <Board
          columns={data.columns}
          cards={data.cards}
          labelMap={labelMap}
          menuColId={menuColId}
          dragging={dragging}
          dragOverCol={dragOver.col}
          dragOverCard={dragOver.card}
          actions={boardActions}
        />
      ) : (
        <ArchiveView
          archived={archived}
          filtered={filtered}
          query={archiveQuery}
          columnTitles={columnTitles}
          labelMap={labelMap}
          actions={archiveActions}
        />
      )}

      {menuColId && <div className="menu-backdrop" onClick={() => setMenuColId(null)} />}

      {openCard && (
        <CardModal
          card={openCard}
          labels={data.labels}
          labelEditorOpen={labelEditorOpen}
          colorPickerLabel={colorPickerLabel}
          actions={cardActions}
          labelActions={labelActions}
        />
      )}
    </div>
  )
}
