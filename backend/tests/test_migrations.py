import pytest
from sqlalchemy import inspect

from tiny_kanban.config import Settings
from tiny_kanban.db import make_engine
from tiny_kanban.main import run_migrations

EXPECTED_TABLES = {
    "columns",
    "cards",
    "labels",
    "card_labels",
    "checklist_items",
    "meta",
}


@pytest.fixture
def inspector(migrated_settings: Settings):
    engine = make_engine(migrated_settings)
    yield inspect(engine)
    engine.dispose()


def test_upgrade_head_creates_all_tables(inspector):
    assert EXPECTED_TABLES <= set(inspector.get_table_names())


def test_upgrade_records_alembic_version(inspector):
    assert "alembic_version" in inspector.get_table_names()


def test_upgrade_is_idempotent(migrated_settings: Settings):
    run_migrations(migrated_settings)  # second run must be a no-op, not an error
    engine = make_engine(migrated_settings)
    assert EXPECTED_TABLES <= set(inspect(engine).get_table_names())
    engine.dispose()


def test_migrations_create_db_file_and_parent_dir(migrated_settings: Settings):
    assert migrated_settings.db_path.is_file()


def test_cards_column_fk_cascades(migrated_settings: Settings):
    engine = make_engine(migrated_settings)
    fks = inspect(engine).get_foreign_keys("cards")
    engine.dispose()
    assert any(
        fk["referred_table"] == "columns" and fk["options"].get("ondelete") == "CASCADE"
        for fk in fks
    )
