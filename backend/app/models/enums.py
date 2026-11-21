"""Enums de domínio usados pelos modelos e schemas."""
import enum


class Perfil(str, enum.Enum):
    socio = "socio"
    advogado = "advogado"
    estagiario = "estagiario"
    financeiro = "financeiro"


class StatusProcesso(str, enum.Enum):
    ativo = "ativo"
    encerrado = "encerrado"
    arquivado = "arquivado"


class ResultadoProcesso(str, enum.Enum):
    procedente = "procedente"
    improcedente = "improcedente"
    acordo = "acordo"
    parcial = "parcial"


class StatusPrazo(str, enum.Enum):
    pendente = "pendente"
    cumprido = "cumprido"
    perdido = "perdido"


class FonteMovimentacao(str, enum.Enum):
    datajud = "datajud"
    jusbrasil = "jusbrasil"
    manual = "manual"


class TipoTransacao(str, enum.Enum):
    entrada = "entrada"
    saida = "saida"


class StatusTransacao(str, enum.Enum):
    pendente = "pendente"
    pago = "pago"
    vencido = "vencido"
    cancelado = "cancelado"


class RoleMensagem(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"
