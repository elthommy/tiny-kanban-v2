from .conftest import simple_board


def etag(response) -> str:
    assert "etag" in response.headers, "every board response must carry an ETag"
    return response.headers["etag"]


def test_get_board_has_etag(client):
    assert etag(client.get("/api/board")) == '"1"'  # seeding was mutation #1


def test_every_mutation_bumps_the_etag(client):
    client.get("/api/board")
    versions = [
        etag(client.post("/api/columns", json={"title": "A"})),
        etag(client.post("/api/columns/col1/cards", json={"title": "B"})),
        etag(client.post("/api/cards/c1/archive")),
        etag(client.post("/api/cards/c1/restore")),
        etag(client.patch("/api/labels/l1", json={"name": "C"})),
    ]
    assert versions == ['"2"', '"3"', '"4"', '"5"', '"6"']


def test_noop_mutation_does_not_bump(client):
    client.get("/api/board")
    v1 = etag(client.post("/api/cards/c1/archive"))
    v2 = etag(client.post("/api/cards/c1/archive"))  # idempotent second archive
    assert v1 == v2


def test_put_board_without_if_match_succeeds(client):
    r = client.put("/api/board", json=simple_board())
    assert r.status_code == 200


def test_put_board_with_matching_if_match(client):
    current = etag(client.get("/api/board"))
    r = client.put("/api/board", json=simple_board(), headers={"If-Match": current})
    assert r.status_code == 200
    assert etag(r) != current


def test_put_board_with_stale_if_match_412(client):
    client.get("/api/board")
    client.post("/api/columns", json={"title": "bump"})
    r = client.put("/api/board", json=simple_board(), headers={"If-Match": '"1"'})
    assert r.status_code == 412
    assert "version" in r.json()["detail"]


def test_put_board_if_match_accepts_bare_number(client):
    client.get("/api/board")
    r = client.put("/api/board", json=simple_board(), headers={"If-Match": "1"})
    assert r.status_code == 200


def test_stale_put_does_not_clobber(client):
    client.get("/api/board")
    client.post("/api/columns", json={"title": "Keep me"})
    client.put("/api/board", json=simple_board(), headers={"If-Match": '"1"'})
    titles = [c["title"] for c in client.get("/api/board").json()["columns"]]
    assert "Keep me" in titles
