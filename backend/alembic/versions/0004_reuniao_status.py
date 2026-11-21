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
    op.add_column(
        "reunioes",
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pendente"),
    )


def downgrade() -> None:
    op.drop_column("reunioes", "status")
