"""Add mb_11 field to member table

Revision ID: 1b3243a1467f
Revises: 944947252fbe
Create Date: 2023-11-04 15:52:06.704540

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1b3243a1467f'
down_revision: Union[str, None] = '944947252fbe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
