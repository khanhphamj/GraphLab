"""update_lab_member_role_system

Revision ID: 4e1bcef5bb7b
Revises: 59c11d2dee44
Create Date: 2025-09-14 05:59:59.733067

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4e1bcef5bb7b'
down_revision: Union[str, Sequence[str], None] = '59c11d2dee44'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check if 'owner' value already exists in enum
    connection = op.get_bind()
    result = connection.execute(
        "SELECT 1 FROM pg_enum WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'lab_member_role') AND enumlabel = 'owner'"
    ).fetchone()
    
    # Only add 'owner' if it doesn't exist
    if not result:
        op.execute("ALTER TYPE lab_member_role ADD VALUE 'owner'")


def downgrade() -> None:
    """Downgrade schema."""
    # Note: PostgreSQL doesn't support removing enum values easily
    # This would require recreating the enum type
    pass