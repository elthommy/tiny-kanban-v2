import type { DragEvent } from 'react'
import type { LabelColor } from './config'

export interface BoardActions {
  renameColumn: (colId: string, title: string) => void
  addCard: (colId: string, title: string) => void
  addColumn: (title: string) => void
  archiveAll: (colId: string) => void
  deleteColumn: (colId: string) => void
  toggleColumnMenu: (colId: string) => void
  closeMenus: () => void
  openCard: (cardId: string) => void
  cardDragStart: (e: DragEvent, cardId: string) => void
  cardDragEnd: () => void
  cardDragOver: (e: DragEvent, colId: string, cardId: string) => void
  columnDragOver: (e: DragEvent, colId: string) => void
  drop: (e: DragEvent, colId: string) => void
}

export interface CardActions {
  close: () => void
  setTitle: (title: string) => void
  setDescription: (description: string) => void
  toggleLabel: (labelId: string) => void
  addCheckItem: (text: string) => void
  toggleCheckItem: (itemId: string) => void
  deleteCheckItem: (itemId: string) => void
  archiveCard: () => void
  deleteCard: () => void
}

export interface LabelEditorActions {
  toggleEditor: () => void
  addLabel: () => void
  renameLabel: (labelId: string, name: string) => void
  deleteLabel: (labelId: string) => void
  togglePicker: (labelId: string) => void
  setColor: (labelId: string, color: LabelColor) => void
}

export interface ArchiveActions {
  setQuery: (q: string) => void
  restore: (cardId: string) => void
  deleteForever: (cardId: string) => void
}
