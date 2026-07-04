import { useEffect, useMemo, useRef, useState } from 'react'
import type { ArchiveActions, BoardActions, CardActions, LabelEditorActions } from './actions'
import { ARCHIVE_SORT, CONFIRM_DELETE, NEW_CARD_POSITION, PALETTE } from './config'
import type { LabelColor } from './config'
import { loadBoard, saveBoard, uid } from './storage'
import type { BoardData, Card, Column, Label } from './types'
import ArchiveView from './components/ArchiveView'
import Board from './components/Board'
import CardModal from './components/CardModal'

function confirmOk(msg: string): boolean {
  return !CONFIRM_DELETE || window.confirm(msg)
}

function archiveInto(cards: Record<string, Card>, cardId: string, fromColId: string | null): Record<string, Card> {
  const card = cards[cardId]
  if (!card) return cards
  return { ...cards, [cardId]: { ...card, archived: true, archivedFrom: fromColId, archivedAt: Date.now() } }
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

function KanbanApp({ initial }: { initial: BoardData }) {
  const [data, setData] = useState<BoardData>(initial)
  const [view, setView] = useState<'board' | 'archive'>('board')
  const [openCardId, setOpenCardId] = useState<string | null>(null)
  const [menuColId, setMenuColId] = useState<string | null>(null)
  const [dragging, setDragging] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState<{ col: string | null; card: string | null }>({ col: null, card: null })
  const [labelEditorOpen, setLabelEditorOpen] = useState(false)
  const [colorPickerLabel, setColorPickerLabel] = useState<string | null>(null)
  const [archiveQuery, setArchiveQuery] = useState('')
  const dragCardId = useRef<string | null>(null)

  useEffect(() => {
    // Identity check skips the save of the board we just loaded
    if (data !== initial) saveBoard(data)
  }, [data, initial])

  const labelMap = useMemo(() => {
    const m: Record<string, Label> = {}
    data.labels.forEach((l) => (m[l.id] = l))
    return m
  }, [data.labels])

  const patchColumns = (fn: (columns: Column[]) => Column[]) => setData((d) => ({ ...d, columns: fn(d.columns) }))

  const updateCard = (id: string, patch: Partial<Card>) =>
    setData((d) => (d.cards[id] ? { ...d, cards: { ...d.cards, [id]: { ...d.cards[id], ...patch } } } : d))

  const clearDrag = () => {
    dragCardId.current = null
    setDragging(null)
    setDragOver({ col: null, card: null })
  }

  const moveCard = (cardId: string | null, toColId: string, beforeId: string | null) => {
    if (!cardId || cardId === beforeId) return
    patchColumns((columns) => {
      const stripped = columns.map((c) => ({ ...c, cardIds: c.cardIds.filter((id) => id !== cardId) }))
      const to = stripped.find((c) => c.id === toColId)
      if (!to) return columns
      const idx = beforeId ? to.cardIds.indexOf(beforeId) : -1
      if (idx >= 0) to.cardIds.splice(idx, 0, cardId)
      else to.cardIds.push(cardId)
      return stripped
    })
  }

  const boardActions: BoardActions = {
    renameColumn: (colId, title) => patchColumns((cols) => cols.map((c) => (c.id === colId ? { ...c, title } : c))),
    addCard: (colId, title) => {
      setData((d) => {
        const id = uid('c')
        const card: Card = { id, title, labels: [], checklist: [], description: '', archived: false }
        const columns = d.columns.map((c) => {
          if (c.id !== colId) return c
          const cardIds = NEW_CARD_POSITION === 'top' ? [id, ...c.cardIds] : [...c.cardIds, id]
          return { ...c, cardIds }
        })
        return { ...d, columns, cards: { ...d.cards, [id]: card } }
      })
      setMenuColId(null)
    },
    addColumn: (title) => patchColumns((cols) => [...cols, { id: uid('col'), title, cardIds: [] }]),
    archiveAll: (colId) => {
      setData((d) => {
        const col = d.columns.find((c) => c.id === colId)
        if (!col) return d
        let cards = d.cards
        col.cardIds.forEach((cid) => (cards = archiveInto(cards, cid, colId)))
        return { ...d, cards, columns: d.columns.map((c) => (c.id === colId ? { ...c, cardIds: [] } : c)) }
      })
      setMenuColId(null)
    },
    deleteColumn: (colId) => {
      if (!confirmOk('Delete this column? Its cards will be moved to Archive.')) {
        setMenuColId(null)
        return
      }
      setData((d) => {
        const col = d.columns.find((c) => c.id === colId)
        let cards = d.cards
        col?.cardIds.forEach((cid) => (cards = archiveInto(cards, cid, colId)))
        return { ...d, cards, columns: d.columns.filter((c) => c.id !== colId) }
      })
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
      moveCard(dragCardId.current, colId, dragOver.card)
      clearDrag()
    },
  }

  const openCard = openCardId ? data.cards[openCardId] : null

  const cardActions: CardActions = {
    close: () => setOpenCardId(null),
    setTitle: (title) => openCardId && updateCard(openCardId, { title }),
    setDescription: (description) => openCardId && updateCard(openCardId, { description }),
    toggleLabel: (labelId) => {
      if (!openCard) return
      const labels = openCard.labels.includes(labelId)
        ? openCard.labels.filter((l) => l !== labelId)
        : [...openCard.labels, labelId]
      updateCard(openCard.id, { labels })
    },
    addCheckItem: (text) =>
      openCard && updateCard(openCard.id, { checklist: [...openCard.checklist, { id: uid('ck'), text, done: false }] }),
    toggleCheckItem: (itemId) =>
      openCard &&
      updateCard(openCard.id, {
        checklist: openCard.checklist.map((it) => (it.id === itemId ? { ...it, done: !it.done } : it)),
      }),
    deleteCheckItem: (itemId) =>
      openCard && updateCard(openCard.id, { checklist: openCard.checklist.filter((it) => it.id !== itemId) }),
    archiveCard: () => {
      if (!openCardId) return
      setData((d) => {
        const col = d.columns.find((c) => c.cardIds.includes(openCardId))
        return {
          ...d,
          cards: archiveInto(d.cards, openCardId, col ? col.id : null),
          columns: d.columns.map((c) => ({ ...c, cardIds: c.cardIds.filter((id) => id !== openCardId) })),
        }
      })
      setOpenCardId(null)
    },
    deleteCard: () => {
      if (!openCardId || !confirmOk('Delete this card? This cannot be undone.')) return
      setData((d) => {
        const cards = { ...d.cards }
        delete cards[openCardId]
        return { ...d, cards, columns: d.columns.map((c) => ({ ...c, cardIds: c.cardIds.filter((id) => id !== openCardId) })) }
      })
      setOpenCardId(null)
    },
  }

  const labelActions: LabelEditorActions = {
    toggleEditor: () => {
      setLabelEditorOpen((v) => !v)
      setColorPickerLabel(null)
    },
    addLabel: () =>
      setData((d) => {
        const c = PALETTE[d.labels.length % PALETTE.length]
        return { ...d, labels: [...d.labels, { id: uid('l'), name: 'New label', ...c }] }
      }),
    renameLabel: (labelId, name) =>
      setData((d) => ({ ...d, labels: d.labels.map((l) => (l.id === labelId ? { ...l, name } : l)) })),
    deleteLabel: (labelId) => {
      setData((d) => {
        const cards: Record<string, Card> = {}
        Object.values(d.cards).forEach((c) => {
          cards[c.id] = c.labels.includes(labelId) ? { ...c, labels: c.labels.filter((l) => l !== labelId) } : c
        })
        return { ...d, cards, labels: d.labels.filter((l) => l.id !== labelId) }
      })
      setColorPickerLabel((cur) => (cur === labelId ? null : cur))
    },
    togglePicker: (labelId) => setColorPickerLabel((cur) => (cur === labelId ? null : labelId)),
    setColor: (labelId, color: LabelColor) => {
      setData((d) => ({ ...d, labels: d.labels.map((l) => (l.id === labelId ? { ...l, ...color } : l)) }))
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
    restore: (cardId) =>
      setData((d) => {
        const card = d.cards[cardId]
        if (!card) return d
        const target = d.columns.find((c) => c.id === card.archivedFrom) || d.columns[0]
        const restored = { ...card, archived: false }
        delete restored.archivedFrom
        delete restored.archivedAt
        return {
          ...d,
          cards: { ...d.cards, [cardId]: restored },
          columns: target ? d.columns.map((c) => (c.id === target.id ? { ...c, cardIds: [...c.cardIds, cardId] } : c)) : d.columns,
        }
      }),
    deleteForever: (cardId) => {
      if (!confirmOk('Permanently delete this card? This cannot be undone.')) return
      setData((d) => {
        const cards = { ...d.cards }
        delete cards[cardId]
        return { ...d, cards, columns: d.columns.map((c) => ({ ...c, cardIds: c.cardIds.filter((id) => id !== cardId) })) }
      })
    },
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand-row">
          <div className="brand">Tiny-kanban v2</div>
          <div className="brand-sub">Product · Sprint 24</div>
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
