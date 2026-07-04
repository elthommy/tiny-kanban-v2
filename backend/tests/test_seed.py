from tiny_kanban.seed import seed_board


def test_seed_is_deterministic():
    assert seed_board() == seed_board()


def test_seed_has_four_columns_in_order():
    titles = [c.title for c in seed_board().columns]
    assert titles == ["To Do", "Blocked", "Pending Validation", "Done"]


def test_seed_cards_all_placed_and_not_archived():
    board = seed_board()
    placed = [cid for col in board.columns for cid in col.cardIds]
    assert sorted(placed) == sorted(board.cards.keys())
    assert not any(c.archived for c in board.cards.values())


def test_seed_has_six_labels():
    assert len(seed_board().labels) == 6


def test_seed_checklist_ids_unique_across_board():
    board = seed_board()
    ids = [item.id for card in board.cards.values() for item in card.checklist]
    assert len(ids) == len(set(ids))
