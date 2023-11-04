"""Add cf_11 field to config table

Revision ID: a8d57505a28f
Revises: 464263d9475e
Create Date: 2023-11-04 15:32:17.441209

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8d57505a28f'
down_revision: Union[str, None] = '464263d9475e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
