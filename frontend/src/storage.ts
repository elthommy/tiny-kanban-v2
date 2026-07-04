import { STORAGE_KEY } from './config'
import type { BoardData } from './types'

export function uid(prefix = 'id'): string {
  return prefix + Math.random().toString(36).slice(2, 8)
}

const API_URL = '/api/board'
const SAVE_DEBOUNCE_MS = 400
const JSON_HEADERS = { 'Content-Type': 'application/json' }

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
  const res = await fetch(API_URL, { method: 'PUT', headers: JSON_HEADERS, body: JSON.stringify(board) })
  if (!res.ok) return null // leave the key in place; we'll retry on next launch
  localStorage.setItem(`${STORAGE_KEY}-migrated`, localStorage.getItem(STORAGE_KEY)!)
  localStorage.removeItem(STORAGE_KEY)
  return board
}

export async function loadBoard(): Promise<BoardData> {
  const migrated = await migrateLocalStorageBoard()
  if (migrated) return migrated
  const res = await fetch(API_URL)
  if (!res.ok) throw new Error(`Failed to load board (HTTP ${res.status})`)
  return (await res.json()) as BoardData
}

let pending: BoardData | null = null
let timer: ReturnType<typeof setTimeout> | undefined

async function flushSave(): Promise<void> {
  if (!pending) return
  const body = JSON.stringify(pending)
  pending = null
  try {
    // keepalive lets the request finish even if the tab is closing
    await fetch(API_URL, { method: 'PUT', headers: JSON_HEADERS, body, keepalive: true })
  } catch (err) {
    console.error('Failed to save board; changes stay in memory until the next edit', err)
  }
}

/** Debounced: rapid edits (typing, dragging) coalesce into one PUT. */
export function saveBoard(data: BoardData): void {
  pending = data
  clearTimeout(timer)
  timer = setTimeout(() => void flushSave(), SAVE_DEBOUNCE_MS)
}

function flushNow(): void {
  clearTimeout(timer)
  void flushSave()
}

if (typeof document !== 'undefined') {
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') flushNow()
  })
  window.addEventListener('beforeunload', flushNow)
}
