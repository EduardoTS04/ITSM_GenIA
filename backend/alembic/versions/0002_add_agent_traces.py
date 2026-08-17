"""add agent_traces

The agent execution trace table. It arrived after the baseline, so it gets its
own revision: databases created before it exists reach the current schema with
`alembic upgrade head`, while databases that already picked it up from the old
create_all() path are simply stamped. See MIGRATIONS.md.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('agent_traces',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ticket_id', sa.Integer(), nullable=False),
    sa.Column('agent_name', sa.String(), nullable=False),
    sa.Column('prompt_version', sa.String(), nullable=False),
    sa.Column('input_summary', sa.Text(), nullable=True),
    sa.Column('raw_output', sa.Text(), nullable=True),
    sa.Column('latency_ms', sa.Integer(), nullable=False),
    sa.Column('success', sa.Boolean(), nullable=False),
    sa.Column('error_type', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('agent_traces', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_agent_traces_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_agent_traces_ticket_id'), ['ticket_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('agent_traces', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_agent_traces_ticket_id'))
        batch_op.drop_index(batch_op.f('ix_agent_traces_id'))

    op.drop_table('agent_traces')
