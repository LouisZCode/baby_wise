"""Add messages table (conversation turns)."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'd82f1a4b9c33'
down_revision: Union[str, Sequence[str], None] = 'c41d9e2a77b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'messages',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('chat_id', sa.String(36),
                  sa.ForeignKey('chats.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('role', sa.String(16), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('lang', sa.String(8), nullable=False, server_default='de'),
        sa.Column('sources', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('messages')
