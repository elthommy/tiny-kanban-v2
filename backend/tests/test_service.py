import pytest

from tiny_kanban.schemas import BoardData
from tiny_kanban.seed import seed_board
from tiny_kanban.service import (
    BoardValidationError,
    get_board,
    is_initialized,
    replace_board,
    validate_board,
)

from .conftest import make_board, make_card, make_label, simple_board


def test_get_board_on_empty_db_returns_empty_board(session):
    board = get_board(session)
    assert board.columns == [] and board.cards == {} and board.labels == []


def test_empty_db_is_not_initialized(session):
    assert not is_initialized(session)


def test_replace_marks_initialized(session):
    replace_board(session, BoardData(**make_board()))
    assert is_initialized(session)


def test_round_trip_simple_board(session):
    board = BoardData(**simple_board())
    replace_board(session, board)
    assert get_board(session) == board


def test_round_trip_seed_board(session):
    board = seed_board()
    replace_board(session, board)
    assert get_board(session) == board


def test_replace_is_a_full_replace(session):
    replace_board(session, seed_board())
    small = BoardData(**simple_board())
    replace_board(session, small)
    assert get_board(session) == small


def test_orphan_card_survives_round_trip(session):
    board = make_board(cards={"c9": make_card("c9", "orphan")})
    replace_board(session, BoardData(**board))
    assert get_board(session).cards["c9"].title == "orphan"
    assert get_board(session).columns == []


# --- validation -------------------------------------------------------------

def test_unknown_card_in_column_rejected():
    board = make_board(columns=[{"id": "col1", "title": "T", "cardIds": ["ghost"]}])
    with pytest.raises(BoardValidationError, match="unknown card"):
        validate_board(BoardData(**board))


def test_card_in_two_columns_rejected():
    board = make_board(
        columns=[
            {"id": "col1", "title": "A", "cardIds": ["c1"]},
            {"id": "col2", "title": "B", "cardIds": ["c1"]},
        ],
        cards={"c1": make_card()},
    )
    with pytest.raises(BoardValidationError, match="more than one place"):
        validate_board(BoardData(**board))


def test_card_twice_in_same_column_rejected():
    board = make_board(
        columns=[{"id": "col1", "title": "A", "cardIds": ["c1", "c1"]}],
        cards={"c1": make_card()},
    )
    with pytest.raises(BoardValidationError, match="more than one place"):
        validate_board(BoardData(**board))


def test_unknown_label_on_card_rejected():
    board = make_board(cards={"c1": make_card(labels=["nope"])})
    with pytest.raises(BoardValidationError, match="unknown label"):
        validate_board(BoardData(**board))


def test_duplicate_label_id_rejected():
    board = make_board(labels=[make_label("l1"), make_label("l1", "Other")])
    with pytest.raises(BoardValidationError, match="duplicate label"):
        validate_board(BoardData(**board))


def test_duplicate_column_id_rejected():
    board = make_board(
        columns=[
            {"id": "col1", "title": "A", "cardIds": []},
            {"id": "col1", "title": "B", "cardIds": []},
        ]
    )
    with pytest.raises(BoardValidationError, match="duplicate column"):
        validate_board(BoardData(**board))


def test_archived_card_in_column_rejected():
    board = make_board(
        columns=[{"id": "col1", "title": "A", "cardIds": ["c1"]}],
        cards={"c1": make_card(archived=True)},
    )
    with pytest.raises(BoardValidationError, match="archived"):
        validate_board(BoardData(**board))


def test_cards_key_mismatch_rejected():
    board = make_board(cards={"other": make_card("c1")})
    with pytest.raises(BoardValidationError, match="does not match"):
        validate_board(BoardData(**board))


def test_duplicate_checklist_item_id_rejected():
    card = make_card(
        checklist=[
            {"id": "ck1", "text": "a", "done": False},
            {"id": "ck1", "text": "b", "done": False},
        ]
    )
    with pytest.raises(BoardValidationError, match="duplicate checklist"):
        validate_board(BoardData(**make_board(cards={"c1": card})))


def test_invalid_board_leaves_existing_data_untouched(session):
    good = BoardData(**simple_board())
    replace_board(session, good)
    bad = make_board(columns=[{"id": "col1", "title": "T", "cardIds": ["ghost"]}])
    with pytest.raises(BoardValidationError):
        replace_board(session, BoardData(**bad))
    assert get_board(session) == good


def test_seed_board_is_valid():
    validate_board(seed_board())
