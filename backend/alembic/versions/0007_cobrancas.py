"""Cobranças programadas (Fase financeiro detalhado).

Revision ID: 0007_cobrancas
Revises: 0006_prazo_conclusao
Create Date: 2026-11-22
"""
from typing import Sequence, Union

from alembic import op

from app.database import Base
import app.models  # noqa: F401

revision: str = "0007_cobrancas"
down_revision: Union[str, None] = "0006_prazo_conclusao"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())  # idempotente: cria só a tabela nova


def downgrade() -> None:
    op.drop_table("cobrancas_programadas")
