export interface Label {
  id: string
  name: string
  bg: string
  fg: string
  dot: string
}

export interface ChecklistItem {
  id: string
  text: string
  done: boolean
}

export interface Dependency {
  cardId: string // the prerequisite card
  resolved: boolean // computed by the backend: prerequisite archived or in the last column
}

export interface Card {
  id: string
  title: string
  labels: string[]
  checklist: ChecklistItem[]
  description: string
  archived: boolean
  archivedFrom?: string | null
  archivedAt?: number
  dueDate?: string // ISO date "YYYY-MM-DD"
  snoozedUntil?: string // ISO date "YYYY-MM-DD", kept after the card wakes up
  snoozedUntilResolved: boolean // hidden until all prerequisites are resolved
  snoozed: boolean // computed by the backend: hidden (until snoozedUntil, or until resolved)
  justWokeUp: boolean // computed by the backend: the snooze ended today
  dependsOn: Dependency[]
  blocks: string[] // computed by the backend: ids of cards depending on this one
}

export interface Column {
  id: string
  title: string
  cardIds: string[]
}

export interface BoardData {
  subtitle: string
  columns: Column[]
  cards: Record<string, Card>
  labels: Label[]
}
