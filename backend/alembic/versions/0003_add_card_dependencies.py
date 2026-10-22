"""add card_dependencies

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-22 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "card_dependencies",
        sa.Column("card_id", sa.String(), nullable=False),
        sa.Column("depends_on_id", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["depends_on_id"], ["cards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("card_id", "depends_on_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("card_dependencies")
