"""add keyword approval flag

Revision ID: 7a9db87c1b2f
Revises: 4b93a493a4aa
Create Date: 2024-05-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a9db87c1b2f'
down_revision: Union[str, Sequence[str], None] = '4b93a493a4aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add approved_by_user flag to research_keywords."""
    op.add_column(
        'research_keywords',
        sa.Column(
            'approved_by_user',
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    op.execute(
        """
        UPDATE research_keywords
        SET approved_by_user = CASE WHEN source = 'user' THEN TRUE ELSE FALSE END
        """
    )

    op.alter_column(
        'research_keywords',
        'approved_by_user',
        server_default=None,
        existing_type=sa.Boolean(),
    )


def downgrade() -> None:
    """Remove approved_by_user flag from research_keywords."""
    op.drop_column('research_keywords', 'approved_by_user')
