"""Add cf_12 field to config table

Revision ID: 944947252fbe
Revises: a8d57505a28f
Create Date: 2023-11-04 15:50:04.861261

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '944947252fbe'
down_revision: Union[str, None] = 'a8d57505a28f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
