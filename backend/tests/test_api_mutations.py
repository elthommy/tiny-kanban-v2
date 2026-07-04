import pytest


@pytest.fixture
def seeded_client(client):
    client.get("/api/board")  # triggers demo-board seeding
    return client


def board_of(response) -> dict:
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"columns", "cards", "labels"}, "mutations must return the full board"
    return body


def column(board: dict, column_id: str) -> dict:
    return next(c for c in board["columns"] if c["id"] == column_id)


# --- columns -------------------------------------------------------------------

def test_create_column(seeded_client):
    b = board_of(seeded_client.post("/api/columns", json={"title": "Later"}))
    assert b["columns"][-1]["title"] == "Later"


def test_rename_column(seeded_client):
    b = board_of(seeded_client.patch("/api/columns/col1", json={"title": "Backlog"}))
    assert column(b, "col1")["title"] == "Backlog"


def test_delete_column_archives_cards(seeded_client):
    b = board_of(seeded_client.delete("/api/columns/col1"))
    assert "col1" not in [c["id"] for c in b["columns"]]
    assert b["cards"]["c1"]["archived"] is True


def test_archive_all(seeded_client):
    b = board_of(seeded_client.post("/api/columns/col2/archive-all"))
    assert column(b, "col2")["cardIds"] == []
    assert b["cards"]["c4"]["archived"] is True


def test_column_endpoints_404_on_unknown_id(seeded_client):
    assert seeded_client.patch("/api/columns/nope", json={"title": "X"}).status_code == 404
    assert seeded_client.delete("/api/columns/nope").status_code == 404
    assert seeded_client.post("/api/columns/nope/archive-all").status_code == 404
    assert seeded_client.post("/api/columns/nope/cards", json={"title": "X"}).status_code == 404


def test_create_column_missing_title_422(seeded_client):
    assert seeded_client.post("/api/columns", json={}).status_code == 422


# --- cards ---------------------------------------------------------------------------

def test_create_card_bottom_by_default(seeded_client):
    b = board_of(seeded_client.post("/api/columns/col1/cards", json={"title": "Newest"}))
    new_id = column(b, "col1")["cardIds"][-1]
    assert b["cards"][new_id]["title"] == "Newest"


def test_create_card_top(seeded_client):
    b = board_of(
        seeded_client.post("/api/columns/col1/cards", json={"title": "Top", "position": "top"})
    )
    top_id = column(b, "col1")["cardIds"][0]
    assert b["cards"][top_id]["title"] == "Top"


def test_create_card_bad_position_422(seeded_client):
    r = seeded_client.post("/api/columns/col1/cards", json={"title": "X", "position": "middle"})
    assert r.status_code == 422


def test_patch_card_text(seeded_client):
    b = board_of(seeded_client.patch("/api/cards/c1", json={"title": "T2", "description": "D2"}))
    assert b["cards"]["c1"]["title"] == "T2" and b["cards"]["c1"]["description"] == "D2"


def test_move_card(seeded_client):
    b = board_of(
        seeded_client.post("/api/cards/c1/move", json={"toColumnId": "col2", "beforeCardId": "c5"})
    )
    assert column(b, "col2")["cardIds"] == ["c4", "c1", "c5"]


def test_move_card_unknown_target_404(seeded_client):
    assert seeded_client.post("/api/cards/c1/move", json={"toColumnId": "nope"}).status_code == 404


def test_move_archived_card_422(seeded_client):
    seeded_client.post("/api/cards/c1/archive")
    r = seeded_client.post("/api/cards/c1/move", json={"toColumnId": "col2"})
    assert r.status_code == 422


def test_archive_restore_cycle(seeded_client):
    b = board_of(seeded_client.post("/api/cards/c4/archive"))
    assert b["cards"]["c4"]["archived"] is True
    b = board_of(seeded_client.post("/api/cards/c4/restore"))
    assert b["cards"]["c4"]["archived"] is False
    assert column(b, "col2")["cardIds"][-1] == "c4"


def test_delete_card(seeded_client):
    b = board_of(seeded_client.delete("/api/cards/c1"))
    assert "c1" not in b["cards"]


def test_card_endpoints_404_on_unknown_id(seeded_client):
    assert seeded_client.patch("/api/cards/nope", json={"title": "X"}).status_code == 404
    assert seeded_client.post("/api/cards/nope/archive").status_code == 404
    assert seeded_client.post("/api/cards/nope/restore").status_code == 404
    assert seeded_client.delete("/api/cards/nope").status_code == 404


# --- card labels / checklist ------------------------------------------------------------

def test_toggle_label_endpoints(seeded_client):
    b = board_of(seeded_client.put("/api/cards/c3/labels/l2"))
    assert b["cards"]["c3"]["labels"] == ["l2"]
    b = board_of(seeded_client.delete("/api/cards/c3/labels/l2"))
    assert b["cards"]["c3"]["labels"] == []


def test_label_link_404s(seeded_client):
    assert seeded_client.put("/api/cards/c3/labels/nope").status_code == 404
    assert seeded_client.put("/api/cards/nope/labels/l1").status_code == 404


def test_checklist_crud_over_http(seeded_client):
    b = board_of(seeded_client.post("/api/cards/c3/checklist", json={"text": "step"}))
    item = b["cards"]["c3"]["checklist"][0]
    assert item["text"] == "step" and item["done"] is False

    b = board_of(
        seeded_client.patch(f"/api/cards/c3/checklist/{item['id']}", json={"done": True})
    )
    assert b["cards"]["c3"]["checklist"][0]["done"] is True

    b = board_of(seeded_client.delete(f"/api/cards/c3/checklist/{item['id']}"))
    assert b["cards"]["c3"]["checklist"] == []


def test_checklist_item_of_other_card_404(seeded_client):
    b = seeded_client.get("/api/board").json()
    item_id = b["cards"]["c4"]["checklist"][0]["id"]
    assert seeded_client.patch(f"/api/cards/c1/checklist/{item_id}", json={"done": True}).status_code == 404


# --- labels ------------------------------------------------------------------------------

def test_create_label_with_defaults(seeded_client):
    b = board_of(seeded_client.post("/api/labels", json={}))
    assert b["labels"][-1]["name"] == "New label"
    assert b["labels"][-1]["bg"].startswith("#")


def test_create_label_with_name(seeded_client):
    b = board_of(seeded_client.post("/api/labels", json={"name": "Ops"}))
    assert b["labels"][-1]["name"] == "Ops"


def test_patch_label_colors(seeded_client):
    b = board_of(
        seeded_client.patch("/api/labels/l1", json={"bg": "#111111", "fg": "#EEEEEE", "dot": "#ABCDEF"})
    )
    lb = next(x for x in b["labels"] if x["id"] == "l1")
    assert (lb["bg"], lb["fg"], lb["dot"]) == ("#111111", "#EEEEEE", "#ABCDEF")


def test_delete_label_cascades(seeded_client):
    b = board_of(seeded_client.delete("/api/labels/l5"))
    assert "l5" not in [x["id"] for x in b["labels"]]
    assert "l5" not in b["cards"]["c4"]["labels"]


def test_unknown_body_keys_rejected(seeded_client):
    assert seeded_client.post("/api/columns", json={"title": "X", "nope": 1}).status_code == 422
    assert seeded_client.patch("/api/cards/c1", json={"archived": True}).status_code == 422


def test_mutations_survive_restart(settings):
    from fastapi.testclient import TestClient

    from tiny_kanban.main import create_app

    with TestClient(create_app(settings)) as client:
        client.get("/api/board")
        client.post("/api/columns", json={"title": "Kept"})
    with TestClient(create_app(settings)) as client:
        titles = [c["title"] for c in client.get("/api/board").json()["columns"]]
        assert titles[-1] == "Kept"
