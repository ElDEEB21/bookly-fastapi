"""add_tags_and_booktag

Revision ID: b475bb9914ef
Revises: 1319cd83e7f0
Create Date: 2026-08-29 20:15:59.017267

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import sqlmodel


revision: str = 'b475bb9914ef'
down_revision: Union[str, Sequence[str], None] = '1319cd83e7f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('tags',
    sa.Column('uid', sa.UUID(), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), nullable=True),
    sa.PrimaryKeyConstraint('uid')
    )
    op.create_table('booktag',
    sa.Column('book_id', sa.UUID(), nullable=False),
    sa.Column('tag_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['book_id'], ['books.uid'], ),
    sa.ForeignKeyConstraint(['tag_id'], ['tags.uid'], ),
    sa.PrimaryKeyConstraint('book_id', 'tag_id')
    )


def downgrade() -> None:
    op.drop_table('booktag')
    op.drop_table('tags')