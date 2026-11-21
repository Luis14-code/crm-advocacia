"""Tabela de notificações internas (Fase 2).

Revision ID: 0002_notificacoes
Revises: 0001_inicial
Create Date: 2026-11-21
"""
from typing import Sequence, Union

from alembic import op

from app.database import Base
import app.models  # noqa: F401  (popula Base.metadata)

revision: str = "0002_notificacoes"
down_revision: Union[str, None] = "0001_inicial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    # create_all é idempotente (checkfirst=True): cria apenas a tabela nova.
    Base.metadata.create_all(bind=bind)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_notificacoes_nao_lidas "
        "ON notificacoes(usuario_id) WHERE lida = false"
    )


def downgrade() -> None:
    op.drop_table("notificacoes")
