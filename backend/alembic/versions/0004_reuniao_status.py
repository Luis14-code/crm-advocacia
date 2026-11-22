"""Adiciona status à reunião (Fase 3).

Revision ID: 0004_reuniao_status
Revises: 0003_configuracoes
Create Date: 2026-11-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_reuniao_status"
down_revision: Union[str, None] = "0003_configuracoes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # IF NOT EXISTS: a migração 0001 (create_all) já pode ter criado a coluna,
    # pois reflete os modelos atuais. Mantém a migração idempotente.
    op.execute(
        "ALTER TABLE reunioes ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'pendente'"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE reunioes DROP COLUMN IF EXISTS status")
