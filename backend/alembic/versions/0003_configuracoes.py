"""Tabela de configurações do escritório (integrações).

Revision ID: 0003_configuracoes
Revises: 0002_notificacoes
Create Date: 2026-11-21
"""
from typing import Sequence, Union

from alembic import op

from app.database import Base
import app.models  # noqa: F401  (popula Base.metadata)

revision: str = "0003_configuracoes"
down_revision: Union[str, None] = "0002_notificacoes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)  # idempotente: cria só a tabela nova


def downgrade() -> None:
    op.drop_table("configuracoes")
