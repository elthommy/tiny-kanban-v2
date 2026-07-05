import pytest

from .conftest import make_board, make_card, make_label, simple_board


def put_ok(client, board: dict) -> None:
    r = client.put("/api/board", json=board)
    assert r.status_code == 200, r.text


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# --- seeding ----------------------------------------------------------------

def test_first_get_returns_seeded_demo_board(client):
    board = client.get("/api/board").json()
    assert [c["title"] for c in board["columns"]] == [
        "To Do", "Blocked", "Pending Validation", "Done",
    ]
    assert len(board["cards"]) == 9
    assert len(board["labels"]) == 6
    assert board["subtitle"] == "Product · Sprint 24"


def test_get_is_stable_across_calls(client):
    assert client.get("/api/board").json() == client.get("/api/board").json()


def test_cleared_board_is_not_reseeded(client):
    client.get("/api/board")  # triggers seeding
    put_ok(client, make_board())  # user empties the board
    board = client.get("/api/board").json()
    assert board == make_board()


def test_put_before_first_get_prevents_seeding(client):
    board = simple_board()
    put_ok(client, board)
    got = client.get("/api/board").json()
    assert got == board


# --- round-trips ------------------------------------------------------------

ARCHIVED_BOARD = make_board(
    columns=[{"id": "col1", "title": "Only", "cardIds": ["c2"]}],
    cards={
        "c1": make_card("c1", "Archived one", archived=True, archivedFrom="col1", archivedAt=1700000000000),
        "c2": make_card("c2", "On board"),
    },
)

UNICODE_BOARD = make_board(
    columns=[{"id": "col1", "title": "À faire 📋", "cardIds": ["c1"]}],
    cards={"c1": make_card("c1", "Café ☕ — «tâche n°1»", description="emoji 🎉 and\nnewlines")},
    labels=[make_label("l1", "Priorité")],
)

EMPTY_COLUMNS_BOARD = make_board(
    columns=[
        {"id": "col1", "title": "Empty A", "cardIds": []},
        {"id": "col2", "title": "Empty B", "cardIds": []},
    ]
)

ORPHAN_BOARD = make_board(cards={"c1": make_card("c1", "orphan, not archived")})


@pytest.mark.parametrize(
    "board",
    [
        make_board(),
        simple_board(),
        ARCHIVED_BOARD,
        UNICODE_BOARD,
        EMPTY_COLUMNS_BOARD,
        ORPHAN_BOARD,
    ],
    ids=["empty", "simple", "archived", "unicode", "empty-columns", "orphan"],
)
def test_put_get_round_trip_identity(client, board):
    put_ok(client, board)
    assert client.get("/api/board").json() == board


def test_put_with_subtitle_stores_it(client):
    put_ok(client, make_board(subtitle="Platform · Sprint 25"))
    assert client.get("/api/board").json()["subtitle"] == "Platform · Sprint 25"


def test_put_without_subtitle_keeps_stored_one(client):
    put_ok(client, make_board(subtitle="Platform · Sprint 25"))
    legacy = simple_board()
    legacy.pop("subtitle")  # pre-subtitle exports (e.g. localStorage migration)
    put_ok(client, legacy)
    assert client.get("/api/board").json()["subtitle"] == "Platform · Sprint 25"


def test_data_survives_app_restart(settings):
    from fastapi.testclient import TestClient

    from tiny_kanban.main import create_app

    board = simple_board()
    with TestClient(create_app(settings)) as client:
        put_ok(client, board)
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/board").json() == board


# --- ordering ---------------------------------------------------------------

def test_card_order_within_column_preserved(client):
    ids = [f"c{i}" for i in range(10)]
    board = make_board(
        columns=[{"id": "col1", "title": "T", "cardIds": list(reversed(ids))}],
        cards={i: make_card(i) for i in ids},
    )
    put_ok(client, board)
    assert client.get("/api/board").json()["columns"][0]["cardIds"] == list(reversed(ids))


def test_column_order_preserved(client):
    board = make_board(
        columns=[{"id": f"col{i}", "title": f"T{i}", "cardIds": []} for i in (3, 1, 2)]
    )
    put_ok(client, board)
    assert [c["id"] for c in client.get("/api/board").json()["columns"]] == ["col3", "col1", "col2"]


def test_label_order_on_board_preserved(client):
    board = make_board(labels=[make_label(f"l{i}", f"L{i}") for i in (2, 3, 1)])
    put_ok(client, board)
    assert [lb["id"] for lb in client.get("/api/board").json()["labels"]] == ["l2", "l3", "l1"]


def test_label_order_on_card_preserved(client):
    board = make_board(
        cards={"c1": make_card(labels=["l3", "l1", "l2"])},
        labels=[make_label(f"l{i}", f"L{i}") for i in (1, 2, 3)],
    )
    put_ok(client, board)
    assert client.get("/api/board").json()["cards"]["c1"]["labels"] == ["l3", "l1", "l2"]


def test_checklist_order_preserved(client):
    checklist = [{"id": f"ck{i}", "text": f"item {i}", "done": i % 2 == 0} for i in (5, 2, 9, 1)]
    board = make_board(cards={"c1": make_card(checklist=checklist)})
    put_ok(client, board)
    assert client.get("/api/board").json()["cards"]["c1"]["checklist"] == checklist


# --- replace semantics ------------------------------------------------------

def test_second_put_removes_stale_rows(client):
    put_ok(client, simple_board())
    replacement = make_board(
        columns=[{"id": "colX", "title": "New", "cardIds": ["cX"]}],
        cards={"cX": make_card("cX", "Only card")},
        labels=[make_label("lX", "Only label")],
    )
    put_ok(client, replacement)
    board = client.get("/api/board").json()
    assert board == replacement
    assert set(board["cards"]) == {"cX"}


def test_removing_checklist_items_does_not_leak(client):
    with_items = make_board(
        cards={"c1": make_card(checklist=[{"id": "ck1", "text": "x", "done": False}])}
    )
    put_ok(client, with_items)
    without_items = make_board(cards={"c1": make_card()})
    put_ok(client, without_items)
    assert client.get("/api/board").json()["cards"]["c1"]["checklist"] == []


# --- validation over HTTP ---------------------------------------------------

@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"columns": []},
        {"columns": [], "cards": {}},
        {"columns": [], "cards": {}, "labels": [], "extra": 1},
        {"columns": [{"id": "col1"}], "cards": {}, "labels": []},
    ],
    ids=["empty-object", "missing-two", "missing-labels", "extra-key", "bad-column"],
)
def test_structurally_invalid_payloads_rejected(client, payload):
    assert client.put("/api/board", json=payload).status_code == 422


def test_malformed_json_rejected(client):
    r = client.put("/api/board", content=b"not json", headers={"Content-Type": "application/json"})
    assert r.status_code == 422


def test_unknown_card_in_column_rejected_with_detail(client):
    board = make_board(columns=[{"id": "col1", "title": "T", "cardIds": ["ghost"]}])
    r = client.put("/api/board", json=board)
    assert r.status_code == 422
    assert "ghost" in r.json()["detail"]


def test_unknown_label_rejected_over_http(client):
    board = make_board(cards={"c1": make_card(labels=["nope"])})
    assert client.put("/api/board", json=board).status_code == 422


def test_duplicate_card_across_columns_rejected_over_http(client):
    board = make_board(
        columns=[
            {"id": "col1", "title": "A", "cardIds": ["c1"]},
            {"id": "col2", "title": "B", "cardIds": ["c1"]},
        ],
        cards={"c1": make_card()},
    )
    assert client.put("/api/board", json=board).status_code == 422


def test_invalid_put_does_not_clobber_stored_board(client):
    board = simple_board()
    put_ok(client, board)
    bad = make_board(columns=[{"id": "col1", "title": "T", "cardIds": ["ghost"]}])
    assert client.put("/api/board", json=bad).status_code == 422
    assert client.get("/api/board").json() == board
