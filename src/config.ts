export const STORAGE_KEY = 'flowboard-kanban-dark-v1'

/** Ask before destructive actions (delete card/column, permanent delete). */
export const CONFIRM_DELETE = true

/** Where cards added from the column menu / add input land. */
export const NEW_CARD_POSITION: 'top' | 'bottom' = 'bottom'

/** Archive list ordering. */
export const ARCHIVE_SORT: 'newest' | 'oldest' = 'newest'

export interface LabelColor {
  bg: string
  fg: string
  dot: string
}

export const PALETTE: LabelColor[] = [
  { bg: '#33265A', fg: '#C9B0F0', dot: '#8B5CF6' },
  { bg: '#4A2620', fg: '#E06A54', dot: '#E0553C' },
  { bg: '#1F3A57', fg: '#9CC6F0', dot: '#3E88C7' },
  { bg: '#4A3B18', fg: '#E8CF8F', dot: '#D9A521' },
  { bg: '#1D4238', fg: '#93D9BE', dot: '#2E9E78' },
  { bg: '#4A2038', fg: '#F0A6C9', dot: '#D63B82' },
  { bg: '#16403F', fg: '#8FD6D9', dot: '#22A6AD' },
  { bg: '#2E313A', fg: '#B7BDCB', dot: '#8892A6' },
]
