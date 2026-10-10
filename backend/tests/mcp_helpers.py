"""JSON-RPC helpers for calling the /mcp mount from a TestClient."""

import json

MCP_HEADERS = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
}


def rpc(client, method: str, params: dict | None = None, id: int = 1) -> dict:
    """POST one JSON-RPC request to /mcp (no redirect following), return the body."""
    payload = {"jsonrpc": "2.0", "id": id, "method": method}
    if params is not None:
        payload["params"] = params
    r = client.post("/mcp", json=payload, headers=MCP_HEADERS, follow_redirects=False)
    assert r.status_code == 200, r.text
    return r.json()


def call_tool(client, name: str, arguments: dict) -> dict:
    """Call a tool that must succeed; return the raw tools/call result."""
    body = rpc(client, "tools/call", {"name": name, "arguments": arguments})
    result = body["result"]
    assert result.get("isError") is not True, result
    return result


def call_tool_error(client, name: str, arguments: dict) -> str:
    """Call a tool that must fail; return the error message the model sees."""
    body = rpc(client, "tools/call", {"name": name, "arguments": arguments})
    result = body["result"]
    assert result.get("isError") is True, result
    message = result["content"][0]["text"]
    # The SDK's bare crash text means the reason was swallowed (see tool_session).
    assert message != f"Error executing tool {name}", "error reason was hidden"
    return message


def tool_result(client, name: str, arguments: dict) -> dict:
    """Call a tool that must succeed; return its JSON text content decoded."""
    return json.loads(call_tool(client, name, arguments)["content"][0]["text"])


def rest_board(client) -> dict:
    """The board as REST clients see it (proves an MCP write was persisted)."""
    return client.get("/api/board").json()
