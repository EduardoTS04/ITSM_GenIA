"""initial schema: tickets and comments

Baseline of the schema as it existed before Alembic: everything
Base.metadata.create_all() built, plus the five ticket columns the old
run_migrations() helper in app/main.py used to bolt on with ALTER TABLE
(respuesta_estructurada, escalado_a_humano, es_recurrente, causa_raiz,
accion_preventiva).

Existing databases already match this revision exactly, so they can adopt
Alembic with `alembic stamp 0001` instead of running it. See MIGRATIONS.md.

Revision ID: 0001
Revises:
Create Date: 2026-08-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('tickets',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('titulo', sa.String(), nullable=False),
    sa.Column('descripcion', sa.Text(), nullable=False),
    sa.Column('tipo', sa.String(), nullable=False),
    sa.Column('categoria', sa.String(), nullable=False),
    sa.Column('subcategoria', sa.String(), nullable=True),
    sa.Column('prioridad', sa.String(), nullable=False),
    sa.Column('estado', sa.String(), nullable=True),
    sa.Column('area_responsable', sa.String(), nullable=True),
    sa.Column('impacto', sa.String(), nullable=True),
    sa.Column('urgencia', sa.String(), nullable=True),
    sa.Column('razon_clasificacion', sa.Text(), nullable=True),
    sa.Column('razon_prioridad', sa.Text(), nullable=True),
    sa.Column('confianza_clasificacion', sa.Float(), nullable=True),
    sa.Column('respuesta_estructurada', sa.Text(), nullable=True),
    sa.Column('escalado_a_humano', sa.Boolean(), nullable=True),
    sa.Column('es_recurrente', sa.Boolean(), nullable=True),
    sa.Column('causa_raiz', sa.Text(), nullable=True),
    sa.Column('accion_preventiva', sa.Text(), nullable=True),
    sa.Column('creado_en', sa.DateTime(), nullable=True),
    sa.Column('actualizado_en', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('tickets', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_tickets_id'), ['id'], unique=False)

    op.create_table('comments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ticket_id', sa.Integer(), nullable=False),
    sa.Column('autor', sa.String(), nullable=False),
    sa.Column('texto', sa.Text(), nullable=False),
    sa.Column('valoracion', sa.Integer(), nullable=True),
    sa.Column('creado_en', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('comments', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_comments_id'), ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('comments', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_comments_id'))

    op.drop_table('comments')
    with op.batch_alter_table('tickets', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_tickets_id'))

    op.drop_table('tickets')
