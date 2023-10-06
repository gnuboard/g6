"""write

Revision ID: 1d302b9739e0
Revises: 2d00c0bdecc8
Create Date: 2023-10-05 14:31:48.968092

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '1d302b9739e0'
down_revision: Union[str, None] = '2d00c0bdecc8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        'g6_write_free',
        sa.Column('wr_id', sa.Integer, primary_key=True),
        sa.Column('wr_num', sa.Integer, nullable=False, default=0),
        sa.Column('wr_reply', sa.String(10), nullable=False),
        sa.Column('wr_parent', sa.Integer, nullable=False, default=0),
        sa.Column('wr_is_comment', sa.Boolean, nullable=False, default=False),
        sa.Column('wr_comment', sa.Integer, nullable=False, default=0),
        sa.Column('wr_comment_reply', sa.String(5), nullable=False),
        sa.Column('ca_name', sa.String(255), nullable=False),
        sa.Column('wr_option', sa.String(255), nullable=False),
        sa.Column('wr_subject', sa.String(255), nullable=False),
        sa.Column('wr_content', sa.Text(), nullable=False),
        sa.Column('wr_seo_title', sa.String(255), nullable=False, default=''),
        sa.Column('wr_link1', sa.Text(), nullable=False),
        sa.Column('wr_link2', sa.Text(), nullable=False),
        sa.Column('wr_link1_hit', sa.Integer, nullable=False, default=0),
        sa.Column('wr_link2_hit', sa.Integer, nullable=False, default=0),
        sa.Column('wr_hit', sa.Integer, nullable=False, default=0),
        sa.Column('wr_good', sa.Integer, nullable=False, default=0),
        sa.Column('wr_nogood', sa.Integer, nullable=False, default=0),
        sa.Column('mb_id', sa.String(20), nullable=False),
        sa.Column('wr_password', sa.String(255), nullable=False),
        sa.Column('wr_name', sa.String(255), nullable=False),
        sa.Column('wr_email', sa.String(255), nullable=False),
        sa.Column('wr_homepage', sa.String(255), nullable=False),
        sa.Column('wr_datetime', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('wr_file', sa.Boolean, nullable=False, default=False),
        sa.Column('wr_last', sa.String(19), nullable=False),
        sa.Column('wr_ip', sa.String(255), nullable=False),
        sa.Column('wr_facebook_user', sa.String(255), nullable=False),
        sa.Column('wr_twitter_user', sa.String(255), nullable=False),
        sa.Column('wr_1', sa.String(255), nullable=False),
        sa.Column('wr_2', sa.String(255), nullable=False),
        sa.Column('wr_3', sa.String(255), nullable=False),
        sa.Column('wr_4', sa.String(255), nullable=False),
        sa.Column('wr_5', sa.String(255), nullable=False),
        sa.Column('wr_6', sa.String(255), nullable=False),
        sa.Column('wr_7', sa.String(255), nullable=False),
        sa.Column('wr_8', sa.String(255), nullable=False),
        sa.Column('wr_9', sa.String(255), nullable=False),
        sa.Column('wr_10', sa.String(255), nullable=False),
    )


def downgrade():
    op.drop_table('g5_write_free')
