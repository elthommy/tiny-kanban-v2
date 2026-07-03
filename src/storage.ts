import { STORAGE_KEY } from './config'
import type { BoardData, Card, ChecklistItem } from './types'

export function uid(prefix = 'id'): string {
  return prefix + Math.random().toString(36).slice(2, 8)
}

export function loadBoard(): BoardData {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const d = JSON.parse(raw)
      if (d && d.columns && d.cards && d.labels) return d as BoardData
    }
  } catch {
    // corrupted storage — fall back to seed data
  }
  return seed()
}

export function saveBoard(data: BoardData): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
  } catch {
    // storage unavailable (private mode, quota) — keep working in memory
  }
}

function seed(): BoardData {
  const labels = [
    { id: 'l1', name: 'Design', bg: '#33265A', fg: '#C9B0F0', dot: '#8B5CF6' },
    { id: 'l2', name: 'Bug', bg: '#4A2620', fg: '#E06A54', dot: '#E0553C' },
    { id: 'l3', name: 'Feature', bg: '#1F3A57', fg: '#9CC6F0', dot: '#3E88C7' },
    { id: 'l4', name: 'Research', bg: '#4A3B18', fg: '#E8CF8F', dot: '#D9A521' },
    { id: 'l5', name: 'Backend', bg: '#1D4238', fg: '#93D9BE', dot: '#2E9E78' },
    { id: 'l6', name: 'Urgent', bg: '#4A2038', fg: '#F0A6C9', dot: '#D63B82' },
  ]
  const ck = (text: string, done = false): ChecklistItem => ({ id: uid('ck'), text, done })
  const cards: Record<string, Card> = {}
  const mk = (id: string, title: string, labs: string[] = [], checklist: ChecklistItem[] = [], description = '') => {
    cards[id] = { id, title, labels: labs, checklist, description, archived: false }
  }
  mk(
    'c1',
    'Redesign onboarding flow',
    ['l1', 'l3'],
    [ck('Audit current screens', true), ck('Wireframe v2'), ck('Usability test with 5 users')],
    'Cut drop-off in the first session by simplifying signup.',
  )
  mk('c2', 'Conduct 5 user interviews', ['l4'], [ck('Recruit participants'), ck('Prepare discussion script')])
  mk('c3', 'Refresh marketing site copy')
  mk(
    'c4',
    'Payment webhook timing out',
    ['l2', 'l5', 'l6'],
    [ck('Reproduce locally', true), ck('Add retry with backoff')],
    'Stripe events arriving after 30s cause missed orders.',
  )
  mk('c5', 'Legal review of updated ToS', [], [], 'Waiting on external counsel — expected end of week.')
  mk('c6', 'Dark mode visual QA', ['l3'], [ck('Cards', true), ck('Modals', true), ck('Charts', true), ck('Print styles')])
  mk('c7', 'API rate limiting', ['l5'], [ck('Design token bucket'), ck('Add response headers')])
  mk('c8', 'Ship v2.3 release', ['l3'])
  mk('c9', 'Migrate assets to new CDN', ['l5'])
  const columns = [
    { id: 'col1', title: 'To Do', cardIds: ['c1', 'c2', 'c3'] },
    { id: 'col2', title: 'Blocked', cardIds: ['c4', 'c5'] },
    { id: 'col3', title: 'Pending Validation', cardIds: ['c6', 'c7'] },
    { id: 'col4', title: 'Done', cardIds: ['c8', 'c9'] },
  ]
  return { columns, cards, labels }
}
