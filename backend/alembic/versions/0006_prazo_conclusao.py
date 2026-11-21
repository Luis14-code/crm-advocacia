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
    op.add_column("prazos", sa.Column("data_conclusao", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("prazos", "data_conclusao")
