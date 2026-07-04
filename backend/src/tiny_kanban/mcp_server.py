"""MCP server exposing the board to LLM clients (read and write).

Mounted at /mcp inside the FastAPI app (streamable HTTP transport). Tools are
thin wrappers over service.py queries and mutations — no board rules here.
Wherever a tool takes a `column` or `label` argument it accepts an id or a
unique case-insensitive name (resolved in service.py); `card_id` arguments are
always ids — get them from list_cards.

Register with a client:
    claude mcp add --transport http tiny-kanban http://127.0.0.1:8000/mcp
"""

from typing import Literal

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from . import service
from .config import Settings
from .db import make_engine, make_session_factory


def build_mcp(settings: Settings) -> FastMCP:
    engine = make_engine(settings)
    session_factory = make_session_factory(engine)

    mcp = FastMCP(
        "tiny-kanban",
        instructions=(
            "Read and write access to a personal kanban board. Use list_cards "
            "for filtered queries, get_card for one card's full detail, "
            "get_board for the entire board structure. Column and label "
            "arguments accept an id or an exact (case-insensitive) name; card "
            "and checklist-item arguments are always ids."
        ),
        stateless_http=True,
        json_response=True,
        # The REST API beside this mount has no Host validation either — the app
        # is a local, unauthenticated, single-user tool. Keeping the MCP check on
        # would only break non-localhost binds (KANBAN_HOST=0.0.0.0) and tests.
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )

    @mcp.tool()
    def get_board() -> dict:
        """The full board: ordered columns with their card ids, all cards
        (including archived ones), and the shared labels."""
        with session_factory() as session:
            return service.get_board(session).model_dump(exclude_none=True)

    @mcp.tool()
    def list_cards(
        query: str | None = None,
        column: str | None = None,
        label: str | None = None,
        archived: bool | None = None,
    ) -> list[dict]:
        """Compact card summaries, optionally filtered.

        query: case-insensitive substring match on title/description/label names.
        column, label: match by id or name (case-insensitive).
        archived: True for archived cards only, False for board cards only.
        """
        with session_factory() as session:
            return service.search_cards(
                session, query=query, column=column, label=label, archived=archived
            )

    @mcp.tool()
    def get_card(card_id: str) -> dict:
        """One card in full detail: text, labels, checklist, archive state."""
        with session_factory() as session:
            return service.get_card_detail(session, card_id)

    # --- write tools: one per service mutation, mutate then return the result --

    @mcp.tool()
    def add_column(title: str) -> dict:
        """Add a column at the right end of the board."""
        with session_factory() as session:
            column_id = service.add_column(session, title)
            return {"id": column_id, "title": title}

    @mcp.tool()
    def rename_column(column: str, title: str) -> dict:
        """Rename a column (by id or current name)."""
        with session_factory() as session:
            column_id = service.resolve_column_id(session, column)
            service.rename_column(session, column_id, title)
            return {"id": column_id, "title": title}

    @mcp.tool()
    def delete_column(column: str) -> dict:
        """Delete a column; its cards are moved to the archive, not destroyed."""
        with session_factory() as session:
            column_id = service.resolve_column_id(session, column)
            service.delete_column(session, column_id)
            return {"deleted": column_id}

    @mcp.tool()
    def archive_all_cards(column: str) -> dict:
        """Archive every card in a column; the column itself stays."""
        with session_factory() as session:
            column_id = service.resolve_column_id(session, column)
            service.archive_all(session, column_id)
            return {"column": column_id, "archived_all": True}

    @mcp.tool()
    def add_card(
        column: str,
        title: str,
        description: str = "",
        position: Literal["top", "bottom"] = "bottom",
    ) -> dict:
        """Create a card in a column. Returns the new card, including its id."""
        with session_factory() as session:
            column_id = service.resolve_column_id(session, column)
            card_id = service.add_card(session, column_id, title, position, description)
            return service.get_card_detail(session, card_id)

    @mcp.tool()
    def update_card(
        card_id: str, title: str | None = None, description: str | None = None
    ) -> dict:
        """Change a card's title and/or description; omitted fields are kept."""
        with session_factory() as session:
            service.update_card_text(session, card_id, title=title, description=description)
            return service.get_card_detail(session, card_id)

    @mcp.tool()
    def move_card(card_id: str, to_column: str, before_card_id: str | None = None) -> dict:
        """Move a card into a column, before the given card (or to the end)."""
        with session_factory() as session:
            column_id = service.resolve_column_id(session, to_column)
            service.move_card(session, card_id, column_id, before_card_id)
            return service.get_card_detail(session, card_id)

    @mcp.tool()
    def archive_card(card_id: str) -> dict:
        """Archive a card (remove it from the board, keep it recoverable)."""
        with session_factory() as session:
            service.archive_card(session, card_id)
            return service.get_card_detail(session, card_id)

    @mcp.tool()
    def restore_card(card_id: str) -> dict:
        """Restore an archived card to the column it came from (or the first one)."""
        with session_factory() as session:
            service.restore_card(session, card_id)
            return service.get_card_detail(session, card_id)

    @mcp.tool()
    def delete_card(card_id: str) -> dict:
        """Permanently delete a card. Prefer archive_card unless asked to delete."""
        with session_factory() as session:
            service.delete_card(session, card_id)
            return {"deleted": card_id}

    @mcp.tool()
    def add_card_label(card_id: str, label: str) -> dict:
        """Attach an existing label (by id or name) to a card."""
        with session_factory() as session:
            label_id = service.resolve_label_id(session, label)
            service.add_card_label(session, card_id, label_id)
            return service.get_card_detail(session, card_id)

    @mcp.tool()
    def remove_card_label(card_id: str, label: str) -> dict:
        """Detach a label (by id or name) from a card."""
        with session_factory() as session:
            label_id = service.resolve_label_id(session, label)
            service.remove_card_label(session, card_id, label_id)
            return service.get_card_detail(session, card_id)

    @mcp.tool()
    def add_checklist_item(card_id: str, text: str) -> dict:
        """Append an unchecked item to a card's checklist."""
        with session_factory() as session:
            service.add_checklist_item(session, card_id, text)
            return service.get_card_detail(session, card_id)

    @mcp.tool()
    def update_checklist_item(
        card_id: str, item_id: str, done: bool | None = None, text: str | None = None
    ) -> dict:
        """Check/uncheck a checklist item and/or rewrite its text."""
        with session_factory() as session:
            service.update_checklist_item(session, card_id, item_id, done=done, text=text)
            return service.get_card_detail(session, card_id)

    @mcp.tool()
    def delete_checklist_item(card_id: str, item_id: str) -> dict:
        """Remove an item from a card's checklist."""
        with session_factory() as session:
            service.delete_checklist_item(session, card_id, item_id)
            return service.get_card_detail(session, card_id)

    @mcp.tool()
    def create_label(name: str) -> dict:
        """Create a board-wide label; its color is auto-picked from the palette."""
        with session_factory() as session:
            label_id = service.add_label(session, name)
            return {"id": label_id, "name": name}

    @mcp.tool()
    def rename_label(label: str, name: str) -> dict:
        """Rename a label everywhere it appears (colors are managed in the UI)."""
        with session_factory() as session:
            label_id = service.resolve_label_id(session, label)
            service.update_label(session, label_id, name=name)
            return {"id": label_id, "name": name}

    @mcp.tool()
    def delete_label(label: str) -> dict:
        """Delete a label from the board and from every card that carries it."""
        with session_factory() as session:
            label_id = service.resolve_label_id(session, label)
            service.delete_label(session, label_id)
            return {"deleted": label_id}

    return mcp
