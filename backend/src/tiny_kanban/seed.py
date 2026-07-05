"""Demo board seeded on first launch (Python port of the original frontend seed)."""

from itertools import count

from .schemas import BoardData, CardSchema, ChecklistItemSchema, ColumnSchema, LabelSchema

_ck_counter = count(1)


def _reset_counter() -> None:
    global _ck_counter
    _ck_counter = count(1)


def _ck(text: str, done: bool = False) -> ChecklistItemSchema:
    return ChecklistItemSchema(id=f"ck{next(_ck_counter)}", text=text, done=done)


def _card(
    id: str,
    title: str,
    labels: list[str] | None = None,
    checklist: list[ChecklistItemSchema] | None = None,
    description: str = "",
) -> CardSchema:
    return CardSchema(
        id=id,
        title=title,
        labels=labels or [],
        checklist=checklist or [],
        description=description,
        archived=False,
    )


def seed_board() -> BoardData:
    _reset_counter()  # deterministic checklist ids on every call
    labels = [
        LabelSchema(id="l1", name="Design", bg="#33265A", fg="#C9B0F0", dot="#8B5CF6"),
        LabelSchema(id="l2", name="Bug", bg="#4A2620", fg="#E06A54", dot="#E0553C"),
        LabelSchema(id="l3", name="Feature", bg="#1F3A57", fg="#9CC6F0", dot="#3E88C7"),
        LabelSchema(id="l4", name="Research", bg="#4A3B18", fg="#E8CF8F", dot="#D9A521"),
        LabelSchema(id="l5", name="Backend", bg="#1D4238", fg="#93D9BE", dot="#2E9E78"),
        LabelSchema(id="l6", name="Urgent", bg="#4A2038", fg="#F0A6C9", dot="#D63B82"),
    ]
    cards = [
        _card(
            "c1",
            "Redesign onboarding flow",
            ["l1", "l3"],
            [_ck("Audit current screens", True), _ck("Wireframe v2"), _ck("Usability test with 5 users")],
            "Cut drop-off in the first session by simplifying signup.",
        ),
        _card(
            "c2",
            "Conduct 5 user interviews",
            ["l4"],
            [_ck("Recruit participants"), _ck("Prepare discussion script")],
        ),
        _card("c3", "Refresh marketing site copy"),
        _card(
            "c4",
            "Payment webhook timing out",
            ["l2", "l5", "l6"],
            [_ck("Reproduce locally", True), _ck("Add retry with backoff")],
            "Stripe events arriving after 30s cause missed orders.",
        ),
        _card("c5", "Legal review of updated ToS", description="Waiting on external counsel — expected end of week."),
        _card(
            "c6",
            "Dark mode visual QA",
            ["l3"],
            [_ck("Cards", True), _ck("Modals", True), _ck("Charts", True), _ck("Print styles")],
        ),
        _card("c7", "API rate limiting", ["l5"], [_ck("Design token bucket"), _ck("Add response headers")]),
        _card("c8", "Ship v2.3 release", ["l3"]),
        _card("c9", "Migrate assets to new CDN", ["l5"]),
    ]
    columns = [
        ColumnSchema(id="col1", title="To Do", cardIds=["c1", "c2", "c3"]),
        ColumnSchema(id="col2", title="Blocked", cardIds=["c4", "c5"]),
        ColumnSchema(id="col3", title="Pending Validation", cardIds=["c6", "c7"]),
        ColumnSchema(id="col4", title="Done", cardIds=["c8", "c9"]),
    ]
    return BoardData(
        subtitle="Product · Sprint 24",
        columns=columns,
        cards={c.id: c for c in cards},
        labels=labels,
    )
