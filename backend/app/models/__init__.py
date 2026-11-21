"""Importa todos os modelos para que o Alembic/metadata os registre."""
from app.models.agente import (
    AuditLog,
    Embedding,
    Feedback,
    Mensagem,
    Reuniao,
    ResultadoCaso,
)
from app.models.cliente import Cliente
from app.models.configuracao import Configuracao
from app.models.documento import Documento
from app.models.financeiro import ConfigHonorarios, Transacao
from app.models.movimentacao import Movimentacao
from app.models.notificacao import Notificacao
from app.models.prazo import Prazo
from app.models.processo import Processo
from app.models.usuario import Usuario

__all__ = [
    "Usuario",
    "Cliente",
    "Configuracao",
    "Processo",
    "Movimentacao",
    "Notificacao",
    "Prazo",
    "Documento",
    "Transacao",
    "ConfigHonorarios",
    "AuditLog",
    "Feedback",
    "ResultadoCaso",
    "Embedding",
    "Reuniao",
    "Mensagem",
]
