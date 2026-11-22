"""Adiciona data_conclusao ao prazo (Fase 5 — mural/gamificação).

Revision ID: 0006_prazo_conclusao
Revises: 0005_whatsapp
Create Date: 2026-11-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_prazo_conclusao"
down_revision: Union[str, None] = "0005_whatsapp"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # IF NOT EXISTS: a migração 0001 (create_all) já pode ter criado a coluna.
    op.execute("ALTER TABLE prazos ADD COLUMN IF NOT EXISTS data_conclusao DATE")


def downgrade() -> None:
    op.execute("ALTER TABLE prazos DROP COLUMN IF EXISTS data_conclusao")
