"""fix_column_name_hashed_password

Revision ID: 9437ba7f0a94
Revises: 198561f49dc2
Create Date: 2025-08-29 06:38:29.167526

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9437ba7f0a94'
down_revision: Union[str, Sequence[str], None] = '198561f49dc2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema: Fix column name from hashedPassword to hashed_password"""
    op.alter_column('users', 'hashedPassword', 
                   new_column_name='hashed_password',
                   existing_type=sa.String(length=255),
                   existing_nullable=False)

def downgrade() -> None:
    """Downgrade schema: Revert hashed_password back to hashedPassword"""
    op.alter_column('users', 'hashed_password',
                   new_column_name='hashedPassword', 
                   existing_type=sa.String(length=255),
                   existing_nullable=False)
