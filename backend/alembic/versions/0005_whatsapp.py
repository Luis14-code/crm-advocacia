"""Mensagens de WhatsApp (Fase 4).

Revision ID: 0005_whatsapp
Revises: 0004_reuniao_status
Create Date: 2026-11-21
"""
from typing import Sequence, Union

from alembic import op

from app.database import Base
import app.models  # noqa: F401

revision: str = "0005_whatsapp"
down_revision: Union[str, None] = "0004_reuniao_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())  # idempotente: cria só a tabela nova


def downgrade() -> None:
    op.drop_table("mensagens_whatsapp")
