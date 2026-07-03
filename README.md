# Tiny-kanban v2

A small dark-themed kanban board ("Flowboard Dark"), implemented from the
[Claude Design](https://claude.ai/design) project *Kanban board design*.

Everything runs client-side; the board is persisted to `localStorage`
(key `flowboard-kanban-dark-v1`). First launch seeds a demo board.

## Features

- Columns: add, rename inline, delete (cards move to the archive), archive all cards
- Cards: add (Enter in the column footer), drag & drop between/within columns
  with a drop indicator, open in a modal
- Card modal: edit title & description, toggle labels, checklist with progress
  bar, archive or delete
- Labels: shared across the board — create, rename, recolor (8-color palette),
  delete from the "Edit labels" panel in the card modal
- Archive view: search, restore to the original column, permanently delete

Behavior toggles (confirmation dialogs, new-card position, archive sort order)
live in `src/config.ts`.

## Development

```bash
npm install
npm run dev      # start dev server
npm run build    # type-check + production build
npm run preview  # serve the production build
```

Stack: Vite, React 19, TypeScript. No backend.
