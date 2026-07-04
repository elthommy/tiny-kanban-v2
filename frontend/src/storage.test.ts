/**
 * @vitest-environment jsdom
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { STORAGE_KEY } from './config'
import type { BoardData } from './types'

const board: BoardData = {
  columns: [{ id: 'col1', title: 'To Do', cardIds: ['c1'] }],
  cards: { c1: { id: 'c1', title: 'A card', labels: [], checklist: [], description: '', archived: false } },
  labels: [],
}

const fetchMock = vi.fn()
vi.stubGlobal('fetch', fetchMock)

// jsdom 29 no longer bundles localStorage (Node's needs --localstorage-file),
// so give the module under test a plain in-memory implementation
const store = new Map<string, string>()
vi.stubGlobal('localStorage', {
  getItem: (k: string) => store.get(k) ?? null,
  setItem: (k: string, v: string) => void store.set(k, String(v)),
  removeItem: (k: string) => void store.delete(k),
  clear: () => store.clear(),
})

function jsonResponse(body: unknown, ok = true, status = 200) {
  return { ok, status, json: () => Promise.resolve(body) }
}

// storage.ts registers window listeners and keeps module-level debounce state,
// so re-import a fresh copy for every test
async function freshStorage() {
  vi.resetModules()
  return await import('./storage')
}

beforeEach(() => {
  localStorage.clear()
  fetchMock.mockReset()
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('loadBoard', () => {
  it('fetches the board from the API', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(board))
    const storage = await freshStorage()
    await expect(storage.loadBoard()).resolves.toEqual(board)
    expect(fetchMock).toHaveBeenCalledWith('/api/board')
  })

  it('throws when the backend answers with an error', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({}, false, 500))
    const storage = await freshStorage()
    await expect(storage.loadBoard()).rejects.toThrow('HTTP 500')
  })

  it('migrates a legacy localStorage board: PUTs it and renames the key', async () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(board))
    fetchMock.mockResolvedValueOnce(jsonResponse({ status: 'ok' }))
    const storage = await freshStorage()

    await expect(storage.loadBoard()).resolves.toEqual(board)

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/board')
    expect(init.method).toBe('PUT')
    expect(JSON.parse(init.body)).toEqual(board)
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull()
    expect(localStorage.getItem(`${STORAGE_KEY}-migrated`)).toEqual(JSON.stringify(board))
  })

  it('keeps the legacy key and falls back to GET when the migration PUT fails', async () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(board))
    fetchMock.mockResolvedValueOnce(jsonResponse({}, false, 503)) // PUT fails
    fetchMock.mockResolvedValueOnce(jsonResponse(board)) // GET fallback
    const storage = await freshStorage()

    await expect(storage.loadBoard()).resolves.toEqual(board)
    expect(localStorage.getItem(STORAGE_KEY)).toEqual(JSON.stringify(board))
  })

  it('ignores corrupted localStorage content', async () => {
    localStorage.setItem(STORAGE_KEY, 'not json{')
    fetchMock.mockResolvedValueOnce(jsonResponse(board))
    const storage = await freshStorage()

    await expect(storage.loadBoard()).resolves.toEqual(board)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock).toHaveBeenCalledWith('/api/board')
  })
})

describe('saveBoard', () => {
  it('debounces rapid saves into a single PUT of the last board', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ status: 'ok' }))
    const storage = await freshStorage()

    storage.saveBoard(board)
    storage.saveBoard({ ...board, labels: [] })
    const last = { ...board, columns: [] }
    storage.saveBoard(last)
    expect(fetchMock).not.toHaveBeenCalled()

    await vi.runAllTimersAsync()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [, init] = fetchMock.mock.calls[0]
    expect(init.method).toBe('PUT')
    expect(JSON.parse(init.body)).toEqual(last)
  })

  it('flushes a pending save immediately when the tab is hidden', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ status: 'ok' }))
    const storage = await freshStorage()

    storage.saveBoard(board)
    expect(fetchMock).not.toHaveBeenCalled()

    Object.defineProperty(document, 'visibilityState', { value: 'hidden', configurable: true })
    document.dispatchEvent(new Event('visibilitychange'))

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual(board)
  })
})
