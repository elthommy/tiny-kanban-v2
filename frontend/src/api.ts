/** API client — the only file that talks to the backend.
 *
 * Two kinds of calls:
 * - Structural mutations (`api.*`): return the server's authoritative board;
 *   the caller replaces its state with it. Pending text edits are flushed
 *   first so a structural response can never revive stale text.
 * - Text edits (`api.patch*` / `api.rename*`): the UI updates its own state
 *   optimistically (controlled inputs fire per keystroke) and the PATCH is
 *   debounced per target; the response is ignored.
 */

import { STORAGE_KEY } from './config'
import type { BoardData, ChecklistItem } from './types'

const JSON_HEADERS = { 'Content-Type': 'application/json' }
const TEXT_DEBOUNCE_MS = 400

function isBoardData(d: unknown): d is BoardData {
  return !!d && typeof d === 'object' && 'columns' in d && 'cards' in d && 'labels' in d
}

/** One-time migration: boards saved by the localStorage version get pushed to the
 *  backend, then the key is renamed (kept as a backup, never re-imported). */
async function migrateLocalStorageBoard(): Promise<BoardData | null> {
  let board: BoardData
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (!isBoardData(parsed)) return null
    board = parsed
  } catch {
    return null
  }
  const res = await fetch('/api/board', { method: 'PUT', headers: JSON_HEADERS, body: JSON.stringify(board) })
  if (!res.ok) return null // leave the key in place; we'll retry on next launch
  localStorage.setItem(`${STORAGE_KEY}-migrated`, localStorage.getItem(STORAGE_KEY)!)
  localStorage.removeItem(STORAGE_KEY)
  return board
}

export async function loadBoard(): Promise<BoardData> {
  const migrated = await migrateLocalStorageBoard()
  if (migrated) return migrated
  const res = await fetch('/api/board')
  if (!res.ok) throw new Error(`Failed to load board (HTTP ${res.status})`)
  return (await res.json()) as BoardData
}

// --- debounced text PATCHes ---------------------------------------------------

const pendingText = new Map<string, Record<string, unknown>>()
const textTimers = new Map<string, ReturnType<typeof setTimeout>>()

function patchTextDebounced(path: string, patch: Record<string, unknown>): void {
  pendingText.set(path, { ...pendingText.get(path), ...patch })
  clearTimeout(textTimers.get(path))
  textTimers.set(path, setTimeout(() => void flushOne(path), TEXT_DEBOUNCE_MS))
}

async function flushOne(path: string): Promise<void> {
  const body = pendingText.get(path)
  pendingText.delete(path)
  clearTimeout(textTimers.get(path))
  textTimers.delete(path)
  if (!body) return
  try {
    // keepalive lets the request finish even if the tab is closing
    await fetch(path, { method: 'PATCH', headers: JSON_HEADERS, body: JSON.stringify(body), keepalive: true })
  } catch (err) {
    console.error('Failed to save text edit', path, err)
  }
}

export async function flushTextEdits(): Promise<void> {
  await Promise.all([...pendingText.keys()].map((path) => flushOne(path)))
}

if (typeof document !== 'undefined') {
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') void flushTextEdits()
  })
  window.addEventListener('beforeunload', () => void flushTextEdits())
}

// --- structural mutations -------------------------------------------------------

async function mutate(path: string, method: string, body?: unknown): Promise<BoardData> {
  await flushTextEdits()
  const res = await fetch(path, {
    method,
    ...(body !== undefined && { headers: JSON_HEADERS, body: JSON.stringify(body) }),
  })
  if (!res.ok) throw new Error(`${method} ${path} failed (HTTP ${res.status})`)
  return (await res.json()) as BoardData
}

const id = encodeURIComponent

export const api = {
  // columns
  addColumn: (title: string) => mutate('/api/columns', 'POST', { title }),
  deleteColumn: (colId: string) => mutate(`/api/columns/${id(colId)}`, 'DELETE'),
  archiveAll: (colId: string) => mutate(`/api/columns/${id(colId)}/archive-all`, 'POST'),
  renameColumn: (colId: string, title: string) =>
    patchTextDebounced(`/api/columns/${id(colId)}`, { title }),

  // cards
  addCard: (colId: string, title: string, position: 'top' | 'bottom') =>
    mutate(`/api/columns/${id(colId)}/cards`, 'POST', { title, position }),
  moveCard: (cardId: string, toColumnId: string, beforeCardId: string | null) =>
    mutate(`/api/cards/${id(cardId)}/move`, 'POST', { toColumnId, beforeCardId }),
  archiveCard: (cardId: string) => mutate(`/api/cards/${id(cardId)}/archive`, 'POST'),
  restoreCard: (cardId: string) => mutate(`/api/cards/${id(cardId)}/restore`, 'POST'),
  deleteCard: (cardId: string) => mutate(`/api/cards/${id(cardId)}`, 'DELETE'),
  patchCardText: (cardId: string, patch: { title?: string; description?: string }) =>
    patchTextDebounced(`/api/cards/${id(cardId)}`, patch),

  // card labels
  addCardLabel: (cardId: string, labelId: string) =>
    mutate(`/api/cards/${id(cardId)}/labels/${id(labelId)}`, 'PUT'),
  removeCardLabel: (cardId: string, labelId: string) =>
    mutate(`/api/cards/${id(cardId)}/labels/${id(labelId)}`, 'DELETE'),

  // checklist
  addCheckItem: (cardId: string, text: string) =>
    mutate(`/api/cards/${id(cardId)}/checklist`, 'POST', { text }),
  patchCheckItem: (cardId: string, itemId: string, patch: Partial<Pick<ChecklistItem, 'done' | 'text'>>) =>
    mutate(`/api/cards/${id(cardId)}/checklist/${id(itemId)}`, 'PATCH', patch),
  deleteCheckItem: (cardId: string, itemId: string) =>
    mutate(`/api/cards/${id(cardId)}/checklist/${id(itemId)}`, 'DELETE'),

  // labels
  addLabel: () => mutate('/api/labels', 'POST', {}),
  setLabelColor: (labelId: string, colors: { bg: string; fg: string; dot: string }) =>
    mutate(`/api/labels/${id(labelId)}`, 'PATCH', colors),
  deleteLabel: (labelId: string) => mutate(`/api/labels/${id(labelId)}`, 'DELETE'),
  renameLabel: (labelId: string, name: string) =>
    patchTextDebounced(`/api/labels/${id(labelId)}`, { name }),
}
