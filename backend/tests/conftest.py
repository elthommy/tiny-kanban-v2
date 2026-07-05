from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tiny_kanban.config import Settings
from tiny_kanban.db import make_engine, make_session_factory
from tiny_kanban.main import create_app, run_migrations


def make_settings(tmp_path: Path, **overrides) -> Settings:
    """Settings isolated from the developer's .env and environment."""
    defaults = dict(
        db_path=tmp_path / "data" / "test.db",
        static_dir=tmp_path / "no-dist",
    )
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return make_settings(tmp_path)


@pytest.fixture
def migrated_settings(settings: Settings) -> Settings:
    run_migrations(settings)
    return settings


@pytest.fixture
def session(migrated_settings: Settings) -> Iterator[Session]:
    engine = make_engine(migrated_settings)
    factory = make_session_factory(engine)
    with factory() as s:
        yield s
    engine.dispose()


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    """TestClient running the full app lifespan (migrations included)."""
    app = create_app(settings)
    with TestClient(app) as c:
        yield c


# --- payload builders -------------------------------------------------------


def make_label(id: str = "l1", name: str = "Bug") -> dict:
    return {"id": id, "name": name, "bg": "#4A2620", "fg": "#E06A54", "dot": "#E0553C"}


def make_card(id: str = "c1", title: str = "A card", **overrides) -> dict:
    card = {
        "id": id,
        "title": title,
        "labels": [],
        "checklist": [],
        "description": "",
        "archived": False,
    }
    card.update(overrides)
    return card


def make_board(
    columns=None, cards=None, labels=None, subtitle="Product · Sprint 24"
) -> dict:
    return {
        "subtitle": subtitle,
        "columns": columns or [],
        "cards": cards or {},
        "labels": labels or [],
    }


def simple_board() -> dict:
    """One column, two cards, one label, checklists — a representative small board."""
    return make_board(
        columns=[{"id": "col1", "title": "To Do", "cardIds": ["c1", "c2"]}],
        cards={
            "c1": make_card(
                "c1",
                "First",
                labels=["l1"],
                checklist=[{"id": "ck1", "text": "step one", "done": True}],
                description="hello",
            ),
            "c2": make_card("c2", "Second"),
        },
        labels=[make_label()],
    )
