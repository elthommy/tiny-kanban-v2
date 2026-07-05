"""MCP endpoint smoke tests over the streamable-HTTP mount.

Deeper query logic is covered in test_service_mutations.py (search_cards,
get_card_detail) — these tests prove the JSON-RPC surface works end to end.
"""

import json

import pytest

MCP_HEADERS = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
}


def rpc(client, method: str, params: dict | None = None, id: int = 1):
    payload = {"jsonrpc": "2.0", "id": id, "method": method}
    if params is not None:
        payload["params"] = params
    r = client.post("/mcp", json=payload, headers=MCP_HEADERS, follow_redirects=False)
    assert r.status_code == 200, r.text
    return r.json()


def call_tool(client, name: str, arguments: dict) -> dict:
    body = rpc(client, "tools/call", {"name": name, "arguments": arguments})
    result = body["result"]
    assert result.get("isError") is not True, result
    return result


@pytest.fixture
def seeded_client(client):
    client.get("/api/board")
    return client


def test_initialize(client):
    body = rpc(
        client,
        "initialize",
        {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "0"},
        },
    )
    assert body["result"]["serverInfo"]["name"] == "tiny-kanban"


def test_no_redirect_on_bare_mcp_path(client):
    r = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        headers=MCP_HEADERS,
        follow_redirects=False,
    )
    assert r.status_code == 200  # a 307 here breaks MCP clients that don't follow redirects


READ_TOOLS = {"get_board", "list_cards", "get_card"}
WRITE_TOOLS = {
    "set_board_subtitle",
    "add_column", "rename_column", "delete_column", "archive_all_cards",
    "add_card", "update_card", "move_card", "archive_card", "restore_card", "delete_card",
    "add_card_label", "remove_card_label",
    "add_checklist_item", "update_checklist_item", "delete_checklist_item",
    "create_label", "rename_label", "delete_label",
}


def test_tools_list_exposes_exactly_the_expected_tools(client):
    body = rpc(client, "tools/list")
    names = {t["name"] for t in body["result"]["tools"]}
    assert names == READ_TOOLS | WRITE_TOOLS


def test_get_board_tool(seeded_client):
    result = call_tool(seeded_client, "get_board", {})
    board = json.loads(result["content"][0]["text"])
    assert len(board["columns"]) == 4 and len(board["cards"]) == 9


def test_list_cards_with_filters(seeded_client):
    result = call_tool(seeded_client, "list_cards", {"label": "Backend", "column": "Blocked"})
    cards = result["structuredContent"]["result"]
    assert [c["title"] for c in cards] == ["Payment webhook timing out"]


def test_list_cards_text_query(seeded_client):
    result = call_tool(seeded_client, "list_cards", {"query": "stripe"})
    assert [c["id"] for c in result["structuredContent"]["result"]] == ["c4"]


def test_get_card_tool(seeded_client):
    result = call_tool(seeded_client, "get_card", {"card_id": "c4"})
    detail = json.loads(result["content"][0]["text"])
    assert detail["column"] == "Blocked"
    assert detail["checklist_total"] == 2


def test_get_card_unknown_id_reports_tool_error(seeded_client):
    body = rpc(seeded_client, "tools/call", {"name": "get_card", "arguments": {"card_id": "nope"}})
    assert body["result"]["isError"] is True


def test_mcp_reflects_rest_mutations(seeded_client):
    seeded_client.post("/api/columns/col1/cards", json={"title": "Fresh from REST"})
    result = call_tool(seeded_client, "list_cards", {"query": "Fresh from REST"})
    assert len(result["structuredContent"]["result"]) == 1
