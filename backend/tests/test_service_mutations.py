import pytest

from tiny_kanban import service
from tiny_kanban.config import PALETTE
from tiny_kanban.schemas import BoardData
from tiny_kanban.seed import seed_board
from tiny_kanban.service import BoardValidationError, NotFoundError

from .conftest import simple_board


@pytest.fixture
def seeded(session):
    """Session with the demo board loaded (4 columns, 9 cards, 6 labels)."""
    service.replace_board(session, seed_board())
    return session


def board(session) -> BoardData:
    return service.get_board(session)


def column_cards(session, column_id: str) -> list[str]:
    cols = {c.id: c for c in board(session).columns}
    return cols[column_id].cardIds


# --- columns -------------------------------------------------------------------

def test_add_column_appends_at_end(seeded):
    new_id = service.add_column(seeded, "Later")
    cols = board(seeded).columns
    assert cols[-1].id == new_id
    assert cols[-1].title == "Later"
    assert cols[-1].cardIds == []


def test_rename_column(seeded):
    service.rename_column(seeded, "col1", "Backlog")
    assert board(seeded).columns[0].title == "Backlog"


def test_rename_unknown_column_404(seeded):
    with pytest.raises(NotFoundError):
        service.rename_column(seeded, "nope", "X")


def test_delete_column_archives_its_cards(seeded):
    service.delete_column(seeded, "col1")
    b = board(seeded)
    assert "col1" not in [c.id for c in b.columns]
    for card_id in ("c1", "c2", "c3"):
        card = b.cards[card_id]
        assert card.archived
        assert card.archivedFrom == "col1"
        assert card.archivedAt is not None


def test_archive_all_empties_column_but_keeps_it(seeded):
    service.archive_all(seeded, "col2")
    b = board(seeded)
    assert [c.id for c in b.columns if c.id == "col2"] == ["col2"]
    assert column_cards(seeded, "col2") == []
    assert b.cards["c4"].archived and b.cards["c4"].archivedFrom == "col2"


# --- cards ------------------------------------------------------------------------

def test_add_card_bottom_and_top(seeded):
    bottom = service.add_card(seeded, "col1", "Last", "bottom")
    top = service.add_card(seeded, "col1", "First", "top")
    ids = column_cards(seeded, "col1")
    assert ids[0] == top and ids[-1] == bottom


def test_add_card_to_unknown_column_404(seeded):
    with pytest.raises(NotFoundError):
        service.add_card(seeded, "nope", "X")


def test_added_card_has_empty_fields(seeded):
    card_id = service.add_card(seeded, "col1", "Fresh")
    card = board(seeded).cards[card_id]
    assert card.description == "" and card.labels == [] and card.checklist == []
    assert not card.archived


def test_update_card_text_partial(seeded):
    service.update_card_text(seeded, "c1", title="New title")
    service.update_card_text(seeded, "c1", description="New desc")
    card = board(seeded).cards["c1"]
    assert card.title == "New title" and card.description == "New desc"


def test_move_card_before_anchor_same_column(seeded):
    # col1 starts as [c1, c2, c3]; move c3 before c1
    service.move_card(seeded, "c3", "col1", "c1")
    assert column_cards(seeded, "col1") == ["c3", "c1", "c2"]


def test_move_card_across_columns_with_anchor(seeded):
    service.move_card(seeded, "c1", "col2", "c5")
    assert column_cards(seeded, "col1") == ["c2", "c3"]
    assert column_cards(seeded, "col2") == ["c4", "c1", "c5"]


def test_move_card_append_when_no_anchor(seeded):
    service.move_card(seeded, "c1", "col4", None)
    assert column_cards(seeded, "col4") == ["c8", "c9", "c1"]


def test_move_card_unknown_anchor_appends(seeded):
    service.move_card(seeded, "c1", "col2", "ghost")
    assert column_cards(seeded, "col2") == ["c4", "c5", "c1"]


def test_move_card_onto_itself_is_noop(seeded):
    before = column_cards(seeded, "col1")
    service.move_card(seeded, "c1", "col1", "c1")
    assert column_cards(seeded, "col1") == before


def test_move_to_empty_column(seeded):
    new_col = service.add_column(seeded, "Empty")
    service.move_card(seeded, "c1", new_col, None)
    assert column_cards(seeded, new_col) == ["c1"]


def test_move_archived_card_rejected(seeded):
    service.archive_card(seeded, "c1")
    with pytest.raises(BoardValidationError, match="archived"):
        service.move_card(seeded, "c1", "col2", None)


def test_archive_card_records_source(seeded):
    service.archive_card(seeded, "c4")
    card = board(seeded).cards["c4"]
    assert card.archived and card.archivedFrom == "col2" and card.archivedAt
    assert "c4" not in column_cards(seeded, "col2")


def test_archive_card_is_idempotent(seeded):
    service.archive_card(seeded, "c4")
    first = board(seeded).cards["c4"]
    service.archive_card(seeded, "c4")
    again = board(seeded).cards["c4"]
    assert again.archivedFrom == first.archivedFrom == "col2"
    assert again.archivedAt == first.archivedAt


def test_restore_returns_to_origin_column(seeded):
    service.archive_card(seeded, "c4")
    service.restore_card(seeded, "c4")
    card = board(seeded).cards["c4"]
    assert not card.archived
    assert card.archivedFrom is None and card.archivedAt is None
    assert column_cards(seeded, "col2")[-1] == "c4"


def test_restore_falls_back_to_first_column_when_origin_deleted(seeded):
    service.archive_card(seeded, "c4")
    service.delete_column(seeded, "col2")
    service.restore_card(seeded, "c4")
    assert column_cards(seeded, "col1")[-1] == "c4"


def test_restore_with_no_columns_rejected(session):
    b = simple_board()
    service.replace_board(session, BoardData(**b))
    service.archive_card(session, "c1")
    service.archive_card(session, "c2")
    service.delete_column(session, "col1")
    with pytest.raises(BoardValidationError, match="no columns"):
        service.restore_card(session, "c1")


def test_restore_non_archived_card_is_noop(seeded):
    before = column_cards(seeded, "col1")
    service.restore_card(seeded, "c1")
    assert column_cards(seeded, "col1") == before


def test_delete_card_removes_everywhere(seeded):
    service.delete_card(seeded, "c4")
    b = board(seeded)
    assert "c4" not in b.cards
    assert "c4" not in column_cards(seeded, "col2")


# --- card labels ---------------------------------------------------------------------

def test_add_and_remove_card_label(seeded):
    service.add_card_label(seeded, "c3", "l2")
    assert board(seeded).cards["c3"].labels == ["l2"]
    service.remove_card_label(seeded, "c3", "l2")
    assert board(seeded).cards["c3"].labels == []


def test_add_card_label_preserves_order(seeded):
    # c4 already has [l2, l5, l6]
    service.add_card_label(seeded, "c4", "l1")
    assert board(seeded).cards["c4"].labels == ["l2", "l5", "l6", "l1"]


def test_add_existing_card_label_is_noop(seeded):
    service.add_card_label(seeded, "c4", "l2")
    assert board(seeded).cards["c4"].labels == ["l2", "l5", "l6"]


def test_card_label_unknown_ids_404(seeded):
    with pytest.raises(NotFoundError):
        service.add_card_label(seeded, "nope", "l1")
    with pytest.raises(NotFoundError):
        service.add_card_label(seeded, "c1", "nope")


# --- checklist --------------------------------------------------------------------------

def test_add_checklist_item_appends(seeded):
    item_id = service.add_checklist_item(seeded, "c4", "Ship the fix")
    checklist = board(seeded).cards["c4"].checklist
    assert checklist[-1].id == item_id
    assert checklist[-1].text == "Ship the fix" and checklist[-1].done is False


def test_toggle_and_edit_checklist_item(seeded):
    item_id = board(seeded).cards["c4"].checklist[1].id
    service.update_checklist_item(seeded, "c4", item_id, done=True)
    service.update_checklist_item(seeded, "c4", item_id, text="Retry w/ backoff")
    item = board(seeded).cards["c4"].checklist[1]
    assert item.done is True and item.text == "Retry w/ backoff"


def test_delete_checklist_item(seeded):
    item_id = board(seeded).cards["c4"].checklist[0].id
    service.delete_checklist_item(seeded, "c4", item_id)
    assert item_id not in [it.id for it in board(seeded).cards["c4"].checklist]


def test_checklist_item_must_belong_to_card(seeded):
    item_id = board(seeded).cards["c4"].checklist[0].id
    with pytest.raises(NotFoundError):
        service.update_checklist_item(seeded, "c1", item_id, done=True)


# --- labels ---------------------------------------------------------------------------------

def test_add_label_defaults_cycle_palette(seeded):
    # seed has 6 labels; the next two take palette entries 6 and 7
    id7 = service.add_label(seeded)
    id8 = service.add_label(seeded)
    labels = {lb.id: lb for lb in board(seeded).labels}
    assert labels[id7].name == "New label"
    assert {"bg": labels[id7].bg, "fg": labels[id7].fg, "dot": labels[id7].dot} == PALETTE[6]
    assert {"bg": labels[id8].bg, "fg": labels[id8].fg, "dot": labels[id8].dot} == PALETTE[7]


def test_update_label_partial(seeded):
    service.update_label(seeded, "l1", name="UX")
    service.update_label(seeded, "l1", bg="#000000", fg="#FFFFFF", dot="#FF0000")
    lb = next(x for x in board(seeded).labels if x.id == "l1")
    assert (lb.name, lb.bg, lb.fg, lb.dot) == ("UX", "#000000", "#FFFFFF", "#FF0000")


def test_delete_label_strips_it_from_cards(seeded):
    service.delete_label(seeded, "l5")  # on c4, c7, c9
    b = board(seeded)
    assert "l5" not in [lb.id for lb in b.labels]
    for card in b.cards.values():
        assert "l5" not in card.labels
    assert b.cards["c4"].labels == ["l2", "l6"]  # order of the rest preserved


# --- queries ------------------------------------------------------------------------------------

def test_search_cards_by_text(seeded):
    hits = service.search_cards(seeded, query="stripe")
    assert [h["id"] for h in hits] == ["c4"]


def test_search_cards_by_column_name_case_insensitive(seeded):
    hits = service.search_cards(seeded, column="blocked")
    assert sorted(h["id"] for h in hits) == ["c4", "c5"]


def test_search_cards_by_label_name(seeded):
    hits = service.search_cards(seeded, label="backend")
    assert sorted(h["id"] for h in hits) == ["c4", "c7", "c9"]


def test_search_cards_archived_filter(seeded):
    service.archive_card(seeded, "c4")
    archived = service.search_cards(seeded, archived=True)
    assert [h["id"] for h in archived] == ["c4"]
    assert archived[0]["column"] is None
    active = service.search_cards(seeded, archived=False)
    assert "c4" not in [h["id"] for h in active]


def test_search_cards_combined_filters(seeded):
    hits = service.search_cards(seeded, label="Backend", column="Blocked")
    assert [h["id"] for h in hits] == ["c4"]


def test_card_summary_shape(seeded):
    detail = service.get_card_detail(seeded, "c4")
    assert detail["column"] == "Blocked"
    assert detail["labels"] == ["Bug", "Backend", "Urgent"]
    assert detail["checklist_done"] == 1 and detail["checklist_total"] == 2
    assert [it["done"] for it in detail["checklist"]] == [True, False]


def test_get_card_detail_unknown_404(seeded):
    with pytest.raises(NotFoundError):
        service.get_card_detail(seeded, "nope")
