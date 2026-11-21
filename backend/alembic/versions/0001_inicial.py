"""Schema inicial — todas as tabelas da Seção 12 + pgvector + índices críticos.

Revision ID: 0001_inicial
Revises:
Create Date: 2026-11-20
"""
from typing import Sequence, Union

from alembic import op

from app.database import Base
import app.models  # noqa: F401  (popula Base.metadata)

revision: str = "0001_inicial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # Extensão para embeddings (RAG)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Cria todas as tabelas a partir do metadata dos modelos
    Base.metadata.create_all(bind=bind)

    # Índices críticos (Seção 12.4) — partials / compostos / ivfflat
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_processos_advogado "
        "ON processos(advogado_id) WHERE status = 'ativo'"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_prazos_pendentes "
        "ON prazos(data_limite) WHERE status = 'pendente'"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_movimentacoes_processo "
        "ON movimentacoes(processo_id, data DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_transacoes_vencimento "
        "ON transacoes(data_vencimento) WHERE status = 'pendente'"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_log_usuario "
        "ON audit_log(usuario_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_resultados_jurimetria "
        "ON resultados_caso(tese, juiz, resultado)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_embeddings_vector "
        "ON embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
