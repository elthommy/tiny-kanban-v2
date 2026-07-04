from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Meta(Base):
    """Key/value store for app metadata (e.g. whether the board was ever initialized,
    so an intentionally emptied board is not re-seeded with demo data)."""

    __tablename__ = "meta"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(String, nullable=False)


class BoardColumn(Base):
    __tablename__ = "columns"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Column the card was archived from (kept even if that column is later deleted)
    archived_from: Mapped[str | None] = mapped_column(String, nullable=True)
    archived_at: Mapped[int | None] = mapped_column(Integer, nullable=True)  # ms epoch, matches JS Date.now()
    # NULL for archived/orphan cards
    column_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("columns.id", ondelete="CASCADE"), nullable=True
    )
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Label(Base):
    __tablename__ = "labels"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    bg: Mapped[str] = mapped_column(String, nullable=False)
    fg: Mapped[str] = mapped_column(String, nullable=False)
    dot: Mapped[str] = mapped_column(String, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class CardLabel(Base):
    __tablename__ = "card_labels"

    card_id: Mapped[str] = mapped_column(
        String, ForeignKey("cards.id", ondelete="CASCADE"), primary_key=True
    )
    label_id: Mapped[str] = mapped_column(
        String, ForeignKey("labels.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    card_id: Mapped[str] = mapped_column(
        String, ForeignKey("cards.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
