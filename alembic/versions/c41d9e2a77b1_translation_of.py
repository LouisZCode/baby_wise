"""Add guideline_chunks.translation_of (bilingual store)."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'c41d9e2a77b1'
down_revision: Union[str, Sequence[str], None] = 'fd5584f863b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'guideline_chunks',
        sa.Column('translation_of', sa.String(36), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('guideline_chunks', 'translation_of')
