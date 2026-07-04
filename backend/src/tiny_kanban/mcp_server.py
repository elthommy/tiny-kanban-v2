"""Read-only MCP server exposing the board to LLM clients.

Mounted at /mcp inside the FastAPI app (streamable HTTP transport). Tools are
thin wrappers over service.py queries — no board rules here. Write tools are
deliberately absent for now (roadmap: add them once needed, they can reuse the
service mutations directly).

Register with a client:
    claude mcp add --transport http tiny-kanban http://127.0.0.1:8000/mcp
"""

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
            "Read-only access to a personal kanban board. Use list_cards for "
            "filtered queries, get_card for one card's full detail, get_board "
            "for the entire board structure."
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

    return mcp
