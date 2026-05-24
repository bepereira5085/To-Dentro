"""add photo_url to user

Revision ID: 126f070e3b4c
Revises:
Create Date: 2026-05-24 12:02:46.067734

"""
from alembic import op
import sqlalchemy as sa

revision = '126f070e3b4c'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table('_alembic_tmp_users')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('photo_url', sa.String(length=255), nullable=True))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('photo_url')

    op.create_table('_alembic_tmp_users',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('name', sa.VARCHAR(length=50), nullable=False),
    sa.Column('email', sa.VARCHAR(length=100), nullable=False),
    sa.Column('cpf', sa.VARCHAR(length=11), nullable=True),
    sa.Column('phone', sa.VARCHAR(length=11), nullable=False),
    sa.Column('type', sa.VARCHAR(length=9), nullable=False),
    sa.Column('created_at', sa.DATETIME(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('verified_at', sa.DATETIME(), nullable=True),
    sa.Column('password_hash', sa.VARCHAR(length=255), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )