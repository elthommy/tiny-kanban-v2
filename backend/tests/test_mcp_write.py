"""MCP write tools over the streamable-HTTP mount.

Board rules themselves are covered in test_service_mutations.py — these tests
prove each tool wires JSON-RPC arguments to the right service mutation, that
id-or-name resolution works, and that REST clients observe the changes
(shared DB, version bump).
"""

from .mcp_helpers import call_tool_error, rest_board, tool_result

# --- columns -------------------------------------------------------------------


def test_add_column(seeded_client):
    created = tool_result(seeded_client, "add_column", {"title": "Later"})
    cols = rest_board(seeded_client)["columns"]
    assert cols[-1] == {"id": created["id"], "title": "Later", "cardIds": []}


def test_rename_column_by_name(seeded_client):
    tool_result(seeded_client, "rename_column", {"column": "to do", "title": "Backlog"})
    assert rest_board(seeded_client)["columns"][0]["title"] == "Backlog"


def test_move_column_by_name(seeded_client):
    tool_result(
        seeded_client, "move_column", {"column": "Done", "before_column": "blocked"}
    )
    cols = [c["id"] for c in rest_board(seeded_client)["columns"]]
    assert cols == ["col1", "col4", "col2", "col3"]


def test_move_column_to_end(seeded_client):
    tool_result(seeded_client, "move_column", {"column": "To Do"})
    cols = [c["id"] for c in rest_board(seeded_client)["columns"]]
    assert cols == ["col2", "col3", "col4", "col1"]


def test_delete_column_archives_its_cards(seeded_client):
    tool_result(seeded_client, "delete_column", {"column": "Done"})
    board = rest_board(seeded_client)
    assert "col4" not in [c["id"] for c in board["columns"]]
    assert board["cards"]["c8"]["archived"] is True


def test_sort_column_by_name(seeded_client):
    # col3: c6 "Dark mode visual QA" (Feature), c7 "API rate limiting" (Backend)
    tool_result(seeded_client, "sort_column", {"column": "Pending Validation"})
    board = rest_board(seeded_client)
    assert next(c for c in board["columns"] if c["id"] == "col3")["cardIds"] == [
        "c6",
        "c7",
    ]


def test_archive_all_cards(seeded_client):
    tool_result(seeded_client, "archive_all_cards", {"column": "Blocked"})
    board = rest_board(seeded_client)
    assert next(c for c in board["columns"] if c["id"] == "col2")["cardIds"] == []
    assert board["cards"]["c4"]["archived"] is True


# --- cards ---------------------------------------------------------------------


def test_add_card_with_description_and_position(seeded_client):
    detail = tool_result(
        seeded_client,
        "add_card",
        {
            "column": "To Do",
            "title": "From MCP",
            "description": "why not",
            "position": "top",
        },
    )
    assert detail["column"] == "To Do"
    board = rest_board(seeded_client)
    assert board["columns"][0]["cardIds"][0] == detail["id"]
    assert board["cards"][detail["id"]]["description"] == "why not"


def test_add_card_defaults_to_bottom(seeded_client):
    detail = tool_result(seeded_client, "add_card", {"column": "To Do", "title": "x"})
    assert rest_board(seeded_client)["columns"][0]["cardIds"][-1] == detail["id"]


def test_update_card_keeps_omitted_fields(seeded_client):
    detail = tool_result(
        seeded_client, "update_card", {"card_id": "c4", "title": "New title"}
    )
    assert detail["title"] == "New title"
    assert detail["description"].startswith("Stripe events")
    card = rest_board(seeded_client)["cards"]["c4"]
    assert card["title"] == "New title"
    assert card["description"].startswith("Stripe events")


def test_update_card_description_only(seeded_client):
    detail = tool_result(
        seeded_client, "update_card", {"card_id": "c4", "description": "rewritten"}
    )
    assert detail["title"] == "Payment webhook timing out"
    assert rest_board(seeded_client)["cards"]["c4"]["description"] == "rewritten"


def test_set_and_clear_card_due_date(seeded_client):
    detail = tool_result(
        seeded_client, "set_card_due_date", {"card_id": "c2", "due_date": "2026-08-15"}
    )
    assert detail["due_date"] == "2026-08-15"
    assert rest_board(seeded_client)["cards"]["c2"]["dueDate"] == "2026-08-15"
    detail = tool_result(seeded_client, "set_card_due_date", {"card_id": "c2"})
    assert detail["due_date"] is None


def test_move_card_before_anchor(seeded_client):
    detail = tool_result(
        seeded_client,
        "move_card",
        {"card_id": "c8", "to_column": "To Do", "before_card_id": "c2"},
    )
    assert detail["column"] == "To Do"
    assert rest_board(seeded_client)["columns"][0]["cardIds"] == [
        "c1",
        "c8",
        "c2",
        "c3",
    ]


def test_move_card_to_end_without_anchor(seeded_client):
    tool_result(seeded_client, "move_card", {"card_id": "c1", "to_column": "Blocked"})
    cols = rest_board(seeded_client)["columns"]
    assert cols[1]["cardIds"] == ["c4", "c5", "c1"]
    assert "c1" not in cols[0]["cardIds"]


def test_archive_then_restore_card(seeded_client):
    assert (
        tool_result(seeded_client, "archive_card", {"card_id": "c1"})["archived"]
        is True
    )
    board = rest_board(seeded_client)
    assert board["cards"]["c1"]["archived"] is True
    assert "c1" not in board["columns"][0]["cardIds"]

    restored = tool_result(seeded_client, "restore_card", {"card_id": "c1"})
    assert restored["archived"] is False
    assert restored["column"] == "To Do"
    board = rest_board(seeded_client)
    assert board["cards"]["c1"]["archived"] is False
    assert "c1" in board["columns"][0]["cardIds"]


def test_delete_card(seeded_client):
    assert tool_result(seeded_client, "delete_card", {"card_id": "c3"}) == {
        "deleted": "c3"
    }
    assert "c3" not in rest_board(seeded_client)["cards"]


# --- card labels & checklist -----------------------------------------------------


def test_add_and_remove_card_label_by_name(seeded_client):
    detail = tool_result(
        seeded_client, "add_card_label", {"card_id": "c3", "label": "urgent"}
    )
    assert detail["labels"] == ["Urgent"]
    assert rest_board(seeded_client)["cards"]["c3"]["labels"] == ["l6"]
    detail = tool_result(
        seeded_client, "remove_card_label", {"card_id": "c3", "label": "Urgent"}
    )
    assert detail["labels"] == []
    assert rest_board(seeded_client)["cards"]["c3"]["labels"] == []


def test_add_card_label_by_id(seeded_client):
    detail = tool_result(
        seeded_client, "add_card_label", {"card_id": "c3", "label": "l5"}
    )
    assert detail["labels"] == ["Backend"]
    assert rest_board(seeded_client)["cards"]["c3"]["labels"] == ["l5"]


def test_checklist_item_lifecycle(seeded_client):
    detail = tool_result(
        seeded_client, "add_checklist_item", {"card_id": "c3", "text": "step"}
    )
    item = detail["checklist"][0]
    assert (item["text"], item["done"]) == ("step", False)
    assert rest_board(seeded_client)["cards"]["c3"]["checklist"] == [item]

    detail = tool_result(
        seeded_client,
        "update_checklist_item",
        {"card_id": "c3", "item_id": item["id"], "done": True},
    )
    assert detail["checklist"][0]["done"] is True
    assert detail["checklist_done"] == 1
    assert rest_board(seeded_client)["cards"]["c3"]["checklist"][0]["done"] is True

    detail = tool_result(
        seeded_client,
        "update_checklist_item",
        {"card_id": "c3", "item_id": item["id"], "text": "renamed"},
    )
    assert (detail["checklist"][0]["text"], detail["checklist"][0]["done"]) == (
        "renamed",
        True,
    )
    assert rest_board(seeded_client)["cards"]["c3"]["checklist"][0]["text"] == "renamed"

    detail = tool_result(
        seeded_client, "delete_checklist_item", {"card_id": "c3", "item_id": item["id"]}
    )
    assert detail["checklist"] == []
    assert rest_board(seeded_client)["cards"]["c3"]["checklist"] == []


# --- labels ----------------------------------------------------------------------


def test_label_lifecycle(seeded_client):
    created = tool_result(seeded_client, "create_label", {"name": "Ops"})
    tool_result(seeded_client, "rename_label", {"label": "Ops", "name": "Infra"})
    labels = {lb["id"]: lb["name"] for lb in rest_board(seeded_client)["labels"]}
    assert labels[created["id"]] == "Infra"

    tool_result(seeded_client, "delete_label", {"label": created["id"]})
    assert created["id"] not in {lb["id"] for lb in rest_board(seeded_client)["labels"]}


# --- errors & versioning -----------------------------------------------------------


def test_unknown_column_name_reports_tool_error(seeded_client):
    message = call_tool_error(
        seeded_client, "add_card", {"column": "Nowhere", "title": "x"}
    )
    assert "unknown column 'Nowhere'" in message


def test_moving_archived_card_reports_tool_error(seeded_client):
    tool_result(seeded_client, "archive_card", {"card_id": "c1"})
    message = call_tool_error(
        seeded_client, "move_card", {"card_id": "c1", "to_column": "Done"}
    )
    assert "is archived" in message


def test_ambiguous_column_name_reports_tool_error(seeded_client):
    tool_result(seeded_client, "add_column", {"title": "To Do"})
    message = call_tool_error(
        seeded_client, "add_card", {"column": "to do", "title": "x"}
    )
    assert "column name 'to do' is ambiguous, use its id" in message


def test_ambiguous_label_name_reports_tool_error(seeded_client):
    tool_result(seeded_client, "create_label", {"name": "bug"})  # seed has "Bug"
    message = call_tool_error(
        seeded_client, "add_card_label", {"card_id": "c3", "label": "Bug"}
    )
    assert "label name 'Bug' is ambiguous, use its id" in message


def test_invalid_due_date_reports_tool_error(seeded_client):
    message = call_tool_error(
        seeded_client, "set_card_due_date", {"card_id": "c2", "due_date": "tomorrow"}
    )
    assert "invalid due date 'tomorrow', expected YYYY-MM-DD" in message


def test_unknown_checklist_item_reports_tool_error(seeded_client):
    message = call_tool_error(
        seeded_client,
        "update_checklist_item",
        {"card_id": "c3", "item_id": "nope", "done": True},
    )
    assert "unknown checklist item 'nope' on card 'c3'" in message


def test_unknown_card_on_write_reports_tool_error(seeded_client):
    message = call_tool_error(seeded_client, "archive_card", {"card_id": "nope"})
    assert "unknown card 'nope'" in message


def test_mcp_write_bumps_the_board_version(seeded_client):
    before = seeded_client.get("/api/board").headers["etag"]
    tool_result(seeded_client, "add_column", {"title": "Bump"})
    after = seeded_client.get("/api/board").headers["etag"]
    assert int(after.strip('"')) == int(before.strip('"')) + 1


# --- board ---------------------------------------------------------------------


def test_set_board_subtitle(seeded_client):
    result = tool_result(
        seeded_client, "set_board_subtitle", {"subtitle": "Ops · Sprint 30"}
    )
    assert result == {"subtitle": "Ops · Sprint 30"}
    assert rest_board(seeded_client)["subtitle"] == "Ops · Sprint 30"
