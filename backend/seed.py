"""Popula o banco com dados iniciais. Uso: docker compose exec backend python seed.py"""
import asyncio
from datetime import date

from sqlalchemy import select

from app.core.security import hash_senha
from app.database import async_session_factory
from app.models.cliente import Cliente
from app.models.enums import Perfil
from app.models.financeiro import ConfigHonorarios
from app.models.processo import Processo
from app.models.usuario import Usuario

SENHA_PADRAO = "claudio123"


async def seed() -> None:
    async with async_session_factory() as db:
        # --- Usuários ---
        existe = await db.execute(select(Usuario).where(Usuario.email == "socio@claudio.local"))
        if existe.scalar_one_or_none():
            print("Seed já aplicado (usuário sócio existe). Abortando.")
            return

        socio = Usuario(
            nome="Dra. Ana Sócia",
            email="socio@claudio.local",
            senha_hash=hash_senha(SENHA_PADRAO),
            perfil=Perfil.socio.value,
            oab="MA-12345",
        )
        advogado = Usuario(
            nome="Dr. Bruno Advogado",
            email="advogado@claudio.local",
            senha_hash=hash_senha(SENHA_PADRAO),
            perfil=Perfil.advogado.value,
            oab="MA-67890",
        )
        db.add_all([socio, advogado])
        await db.flush()

        # --- Config de honorários ---
        db.add_all([
            ConfigHonorarios(tipo_processo="previdenciario", percentual_contratual=30, percentual_sucumbencial=10),
            ConfigHonorarios(tipo_processo="trabalhista", percentual_contratual=30, percentual_sucumbencial=15),
            ConfigHonorarios(tipo_processo="civel", percentual_contratual=20, percentual_sucumbencial=10),
        ])

        # --- Clientes ---
        cliente1 = Cliente(
            nome="José da Silva",
            cpf="123.456.789-00",
            telefone="+5599999990001",
            email="jose@email.com",
            data_nascimento=date(1965, 3, 12),
        )
        cliente2 = Cliente(
            nome="Maria Oliveira",
            cpf="987.654.321-00",
            telefone="+5599999990002",
        )
        db.add_all([cliente1, cliente2])
        await db.flush()

        # --- Processos ---
        db.add_all([
            Processo(
                numero="0001234-56.2024.8.10.0001",
                cliente_id=cliente1.id,
                advogado_id=advogado.id,
                tipo="previdenciario",
                subtipo="aposentadoria_tempo",
                status="ativo",
                valor_causa=150000,
                juiz="João da Silva",
                vara="2ª Vara Federal de Imperatriz",
                tese_principal="Aposentadoria por tempo de contribuição com atividade especial",
                data_distribuicao=date(2024, 2, 10),
            ),
            Processo(
                numero="0007654-32.2024.8.10.0002",
                cliente_id=cliente2.id,
                advogado_id=advogado.id,
                tipo="previdenciario",
                subtipo="aux_doenca",
                status="ativo",
                valor_causa=45000,
                vara="1ª Vara Federal de Imperatriz",
                tese_principal="Auxílio-doença por incapacidade laborativa",
                data_distribuicao=date(2024, 6, 1),
            ),
        ])

        await db.commit()
        print("Seed aplicado com sucesso!")
        print(f"  Sócio:    socio@claudio.local     / {SENHA_PADRAO}")
        print(f"  Advogado: advogado@claudio.local  / {SENHA_PADRAO}")


if __name__ == "__main__":
    asyncio.run(seed())
