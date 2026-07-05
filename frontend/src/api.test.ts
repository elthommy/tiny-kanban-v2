/**
 * @vitest-environment jsdom
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { STORAGE_KEY } from './config'
import type { BoardData } from './types'

const board: BoardData = {
  subtitle: 'Product · Sprint 24',
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

// api.ts registers window listeners and keeps module-level debounce state,
// so re-import a fresh copy for every test
async function freshApi() {
  vi.resetModules()
  return await import('./api')
}

beforeEach(() => {
  store.clear()
  fetchMock.mockReset()
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

describe('loadBoard', () => {
  it('fetches the board from the API', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(board))
    const { loadBoard } = await freshApi()
    await expect(loadBoard()).resolves.toEqual(board)
    expect(fetchMock).toHaveBeenCalledWith('/api/board')
  })

  it('throws when the backend answers with an error', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({}, false, 500))
    const { loadBoard } = await freshApi()
    await expect(loadBoard()).rejects.toThrow('HTTP 500')
  })

  it('migrates a legacy localStorage board: PUTs it and renames the key', async () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(board))
    fetchMock.mockResolvedValueOnce(jsonResponse(board))
    const { loadBoard } = await freshApi()

    await expect(loadBoard()).resolves.toEqual(board)

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/board')
    expect(init.method).toBe('PUT')
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull()
    expect(localStorage.getItem(`${STORAGE_KEY}-migrated`)).toEqual(JSON.stringify(board))
  })
})

describe('debounced text edits', () => {
  it('coalesces rapid edits to the same target into one merged PATCH', async () => {
    fetchMock.mockResolvedValue(jsonResponse({}))
    const { api } = await freshApi()

    api.patchCardText('c1', { title: 'a' })
    api.patchCardText('c1', { title: 'ab' })
    api.patchCardText('c1', { description: 'why' })
    expect(fetchMock).not.toHaveBeenCalled()

    await vi.runAllTimersAsync()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/cards/c1')
    expect(init.method).toBe('PATCH')
    expect(JSON.parse(init.body)).toEqual({ title: 'ab', description: 'why' })
  })

  it('keeps different targets separate', async () => {
    fetchMock.mockResolvedValue(jsonResponse({}))
    const { api } = await freshApi()

    api.patchCardText('c1', { title: 'x' })
    api.renameColumn('col1', 'y')
    await vi.runAllTimersAsync()

    const urls = fetchMock.mock.calls.map(([u]) => u).sort()
    expect(urls).toEqual(['/api/cards/c1', '/api/columns/col1'])
  })

  it('flushes pending edits when the tab is hidden', async () => {
    fetchMock.mockResolvedValue(jsonResponse({}))
    const { api } = await freshApi()

    api.patchCardText('c1', { title: 'unsaved' })
    Object.defineProperty(document, 'visibilityState', { value: 'hidden', configurable: true })
    document.dispatchEvent(new Event('visibilitychange'))
    await vi.runAllTimersAsync()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ title: 'unsaved' })
  })
})

describe('structural mutations', () => {
  it('returns the parsed board from the server', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(board))
    const { api } = await freshApi()
    await expect(api.addColumn('New')).resolves.toEqual(board)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/columns')
    expect(JSON.parse(init.body)).toEqual({ title: 'New' })
  })

  it('flushes pending text edits before the structural call', async () => {
    fetchMock.mockResolvedValue(jsonResponse(board))
    const { api } = await freshApi()

    api.patchCardText('c1', { title: 'typed just before' })
    await api.archiveCard('c1')

    expect(fetchMock.mock.calls.map(([u, i]) => `${i.method} ${u}`)).toEqual([
      'PATCH /api/cards/c1',
      'POST /api/cards/c1/archive',
    ])
  })

  it('rejects with a readable error on HTTP failure', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({}, false, 422))
    const { api } = await freshApi()
    await expect(api.deleteCard('c1')).rejects.toThrow('DELETE /api/cards/c1 failed (HTTP 422)')
  })
})
