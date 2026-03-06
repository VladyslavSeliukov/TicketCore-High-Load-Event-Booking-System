"""add ticket status enum

Revision ID: b99bc57a572c
Revises: 1217a828aeb9
Create Date: 2026-03-06 02:13:11.417062

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'b99bc57a572c'
down_revision: Union[str, Sequence[str], None] = '1217a828aeb9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    ticket_status_enum = postgresql.ENUM('RESERVED', 'SOLD', 'CANCELED', name='ticketstatus')
    ticket_status_enum.create(op.get_bind(), checkfirst=True)
    op.add_column('tickets', sa.Column('status', ticket_status_enum, nullable=False, server_default='RESERVED'))
    op.create_index(op.f('ix_tickets_status'), 'tickets', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_tickets_status'), table_name='tickets')
    op.drop_column('tickets', 'status')
    ticket_status_enum = postgresql.ENUM('RESERVED', 'SOLD', 'CANCELED', name='ticketstatus')
    ticket_status_enum.drop(op.get_bind(), checkfirst=True)