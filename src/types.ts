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

export interface Card {
  id: string
  title: string
  labels: string[]
  checklist: ChecklistItem[]
  description: string
  archived: boolean
  archivedFrom?: string | null
  archivedAt?: number
}

export interface Column {
  id: string
  title: string
  cardIds: string[]
}

export interface BoardData {
  columns: Column[]
  cards: Record<string, Card>
  labels: Label[]
}
