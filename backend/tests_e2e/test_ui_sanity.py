"""Sanity checks of the main UI flows with real clicks and drag & drop.

Kept deliberately few: board rules are tested in tests/ (service + HTTP); these
only prove the UI wires them up. Demo board columns, left to right:
To Do (c1 Redesign…, c2 Conduct…, c3 Refresh…), Blocked (c4 Payment…, c5 Legal…),
Pending Validation, Done.
"""

from datetime import date, timedelta

from playwright.sync_api import Locator, Page, expect

TODO, BLOCKED = 0, 1


def column_titles(page: Page, index: int) -> Locator:
    """Titles of the cards shown in the index-th column, in board order."""
    return page.locator(".column").nth(index).locator(".card-title")


def card(page: Page, title: str) -> Locator:
    """The board tile of the card with this title."""
    return page.locator(".card", has_text=title)


def show_board(page: Page) -> None:
    """Switch to the Board tab."""
    page.get_by_role("button", name="Board", exact=True).click()


def test_drag_card_to_another_column(board_page: Page):
    page = board_page
    card(page, "Refresh marketing site copy").drag_to(
        card(page, "Legal review of updated ToS")
    )
    moved = [
        "Payment webhook timing out",
        "Refresh marketing site copy",
        "Legal review of updated ToS",
    ]
    expect(column_titles(page, BLOCKED)).to_have_text(moved)
    page.reload()  # the move was saved, not just drawn
    expect(column_titles(page, BLOCKED)).to_have_text(moved)


def test_snooze_and_wake_card(board_page: Page):
    page = board_page
    card(page, "Conduct 5 user interviews").click()
    page.locator(".modal-footer").get_by_role("button", name="Snooze").click()
    page.locator(".snooze-preset", has_text="Tomorrow").click()
    expect(column_titles(page, TODO)).to_have_text(
        ["Redesign onboarding flow", "Refresh marketing site copy"]
    )

    page.get_by_role("button", name="1 snoozed").click()
    item = page.locator(".archive-item", has_text="Conduct 5 user interviews")
    expect(item).to_contain_text("in To Do")
    item.get_by_role("button", name="Wake now").click()
    expect(page.locator(".archive-item")).to_have_count(0)

    show_board(page)
    expect(column_titles(page, TODO)).to_have_text(
        [
            "Redesign onboarding flow",
            "Conduct 5 user interviews",
            "Refresh marketing site copy",
        ]
    )


def test_drag_around_a_snoozed_card_keeps_it_in_place(board_page: Page, app_url):
    page = board_page
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    page.request.put(f"{app_url}/api/cards/c2/snooze", data={"until": tomorrow})
    page.reload()
    card(page, "Refresh marketing site copy").drag_to(
        card(page, "Redesign onboarding flow")
    )
    expect(column_titles(page, TODO)).to_have_text(
        ["Refresh marketing site copy", "Redesign onboarding flow"]
    )
    board = page.request.get(f"{app_url}/api/board").json()
    assert board["columns"][TODO]["cardIds"] == ["c3", "c1", "c2"]


def test_archive_and_restore_card(board_page: Page):
    page = board_page
    card(page, "Legal review of updated ToS").click()
    page.get_by_role("button", name="Archive card").click()
    expect(card(page, "Legal review of updated ToS")).to_have_count(0)

    page.get_by_role("button", name="Archive · 1").click()
    item = page.locator(".archive-item", has_text="Legal review of updated ToS")
    expect(item).to_contain_text("from Blocked")
    item.get_by_role("button", name="Restore").click()

    show_board(page)
    expect(column_titles(page, BLOCKED)).to_have_text(
        ["Payment webhook timing out", "Legal review of updated ToS"]
    )


def test_add_dependency_shows_blocked_badge(board_page: Page):
    page = board_page
    card(page, "Redesign onboarding flow").click()
    page.get_by_role("combobox", name="Add a dependency").fill("legal review")
    page.keyboard.press("Enter")
    expect(page.locator(".modal .dep-link")).to_have_text(
        ["Legal review of updated ToS"]
    )
    page.locator(".modal-close").click()
    expect(
        card(page, "Redesign onboarding flow").locator(".dep-badge")
    ).to_contain_text("0/1")


def test_snooze_until_prerequisites_done_then_just_woke_up(board_page: Page, app_url):
    page = board_page
    page.request.put(f"{app_url}/api/cards/c2/dependencies/c4")
    page.reload()
    card(page, "Conduct 5 user interviews").click()
    page.locator(".modal-footer").get_by_role("button", name="Snooze").click()
    page.locator(".snooze-preset", has_text="Until its prerequisites are done").click()
    expect(card(page, "Conduct 5 user interviews")).to_have_count(0)

    card(page, "Payment webhook timing out").click()
    page.get_by_role("button", name="Archive card").click()  # resolves c4
    expect(card(page, "Conduct 5 user interviews").locator(".woke-badge")).to_have_text(
        "⏰Just woke up"
    )


def test_filter_board_by_label(board_page: Page):
    page = board_page
    filter_bar = page.get_by_role("toolbar", name="Filter by label")
    filter_bar.get_by_role("button", name="Feature").click()
    expect(column_titles(page, TODO)).to_have_text(["Redesign onboarding flow"])
    expect(column_titles(page, BLOCKED)).to_have_count(0)
    expect(page.locator(".column").nth(TODO).locator(".col-count")).to_have_text("1/3")

    # Clicking a label on a card adds it to the filter instead of opening the card
    card(page, "Ship v2.3 release").get_by_role("button", name="Feature").click()
    expect(column_titles(page, TODO)).to_have_count(3)  # Feature toggled off
    card(page, "API rate limiting").get_by_role("button", name="Backend").click()
    expect(page.locator(".modal")).to_have_count(0)
    expect(column_titles(page, BLOCKED)).to_have_text(["Payment webhook timing out"])

    page.reload()  # the filter is kept in the URL
    expect(column_titles(page, BLOCKED)).to_have_text(["Payment webhook timing out"])

    # A card added while filtered stays visible until the filter changes
    page.locator(".column").nth(BLOCKED).get_by_placeholder("Add a card").fill(
        "New task"
    )
    page.keyboard.press("Enter")
    expect(column_titles(page, BLOCKED)).to_have_text(
        ["Payment webhook timing out", "New task"]
    )
    filter_bar.get_by_role("button", name="No label").click()
    filter_bar.get_by_role("button", name="No label").click()
    expect(column_titles(page, BLOCKED)).to_have_text(["Payment webhook timing out"])
    filter_bar.get_by_role("button", name="Clear").click()
    expect(column_titles(page, BLOCKED)).to_have_count(3)
