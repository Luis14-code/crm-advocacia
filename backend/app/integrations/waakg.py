"""Cliente HTTP para o gateway WhatsApp WA-AKG (baseado em Baileys).

Repositório: https://github.com/mrifqidaffaaditya/WA-AKG (MIT). Self-hosted, REST,
autenticação por header X-API-Key. Endpoints usados:
  - POST /api/sessions                              criar sessão
  - POST /api/sessions/{id}/{start|stop|restart}    controlar sessão
  - GET  /api/sessions/{id}/qr                       obter QR (base64)
  - GET  /api/sessions/{id}                          status (Connected/Disconnected/...)
  - POST /api/messages/{sessionId}/{jid}/send        enviar texto
  - POST /api/chat/{sessionId}/{jid}/presence        presença (composing = "digitando")
  - POST /api/webhooks/{sessionId}                   registrar webhook

Obs.: trata-se de gateway de terceiros, não-oficial. Uso de baixo volume e com
simulação de digitação para reduzir risco de bloqueio do número.
"""
import logging
import re

import httpx

logger = logging.getLogger("claudio.waakg")

_SO_DIGITOS = re.compile(r"\D")


class WaakgError(Exception):
    pass


def telefone_para_jid(telefone: str) -> str:
    """Normaliza um telefone para o JID do WhatsApp (ex: 5599999990001@s.whatsapp.net)."""
    numero = _SO_DIGITOS.sub("", telefone or "")
    return f"{numero}@s.whatsapp.net"


class WaakgClient:
    def __init__(self, base_url: str, api_key: str | None, session_id: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session_id = session_id

    @property
    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["X-API-Key"] = self.api_key
        return h

    async def _req(self, metodo: str, caminho: str, json: dict | None = None) -> dict:
        url = f"{self.base_url}/api{caminho}"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.request(metodo, url, headers=self._headers, json=json)
            if resp.status_code >= 400:
                raise WaakgError(f"HTTP {resp.status_code}: {resp.text[:300]}")
            return resp.json() if resp.content else {}
        except httpx.HTTPError as exc:
            raise WaakgError(f"Falha de conexão com WA-AKG: {exc}") from exc

    async def criar_sessao(self, nome: str = "Cláudio") -> dict:
        return await self._req("POST", "/sessions", {"name": nome, "sessionId": self.session_id})

    async def iniciar(self) -> dict:
        return await self._req("POST", f"/sessions/{self.session_id}/start")

    async def obter_qr(self) -> dict:
        return await self._req("GET", f"/sessions/{self.session_id}/qr")

    async def status(self) -> dict:
        return await self._req("GET", f"/sessions/{self.session_id}")

    async def enviar_texto(self, jid: str, texto: str) -> dict:
        return await self._req(
            "POST", f"/messages/{self.session_id}/{jid}/send", {"message": {"text": texto}}
        )

    async def presenca(self, jid: str, presenca: str = "composing") -> dict:
        """presenca: composing (digitando) | paused | available | unavailable."""
        try:
            return await self._req(
                "POST", f"/chat/{self.session_id}/{jid}/presence", {"presence": presenca}
            )
        except WaakgError as exc:
            # Presença é "best effort"; não deve impedir o envio.
            logger.debug("Presença falhou (ignorado): %s", exc)
            return {}

    async def registrar_webhook(self, url: str, secret: str | None = None) -> dict:
        corpo = {"name": "claudio", "url": url, "events": ["message.received"]}
        if secret:
            corpo["secret"] = secret
        return await self._req("POST", f"/webhooks/{self.session_id}", corpo)
