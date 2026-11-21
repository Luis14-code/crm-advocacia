"""Task de transcrição de reuniões (roda no whisper-worker, fila 'whisper')."""
import asyncio
import logging

from app.database import async_session_factory
from app.models.agente import Reuniao
from app.models.notificacao import Notificacao
from app.services import embeddings, transcricao
from app.tasks.celery_app import celery_app

logger = logging.getLogger("claudio.tasks.transcricao")


async def _processar(reuniao_id: int) -> dict:
    async with async_session_factory() as db:
        reuniao = await db.get(Reuniao, reuniao_id)
        if not reuniao or not reuniao.audio_path:
            return {"erro": "reunião ou áudio inexistente"}

        reuniao.status = "transcrevendo"
        await db.commit()

        try:
            resultado = transcricao.transcrever_audio(reuniao.audio_path)
            reuniao.transcricao = resultado["texto"]
            reuniao.duracao_segundos = resultado["duracao_segundos"]

            extraido = await transcricao.resumir_e_extrair(resultado["texto"])
            reuniao.resumo = extraido["resumo"]
            reuniao.fatos_peticao = extraido["fatos_peticao"]
            reuniao.pendencias = extraido["pendencias"]
            reuniao.status = "concluido"

            # RAG: indexa resumo + fatos
            conteudo = (extraido["resumo"] or "") + "\n" + "\n".join(extraido["fatos_peticao"])
            await embeddings.indexar(
                db, "reuniao", reuniao.id, conteudo,
                metadata={"cliente_id": reuniao.cliente_id, "processo_id": reuniao.processo_id},
            )

            if reuniao.advogado_id:
                db.add(
                    Notificacao(
                        usuario_id=reuniao.advogado_id,
                        processo_id=reuniao.processo_id,
                        tipo="sistema",
                        titulo="Transcrição concluída",
                        corpo=reuniao.resumo[:200] if reuniao.resumo else "Reunião transcrita.",
                    )
                )
            await db.commit()
            return {"status": "concluido", "duracao": reuniao.duracao_segundos}
        except Exception as exc:  # noqa: BLE001
            logger.exception("Erro na transcrição da reunião %s", reuniao_id)
            reuniao.status = "erro"
            await db.commit()
            return {"erro": str(exc)}


@celery_app.task(name="claudio.transcrever_reuniao")
def transcrever_reuniao_task(reuniao_id: int) -> dict:
    return asyncio.run(_processar(reuniao_id))
