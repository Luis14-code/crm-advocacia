"""Integração com provedor de pagamentos/banco (gateway de boleto).

Suporta um provedor configurável. Implementação de referência: Asaas (header
`access_token`). Outros provedores (PagHiper, banco via Open Finance) podem ser
adicionados implementando a mesma interface.

- criar_cobranca(): emite o boleto (quando há provedor + chave configurados).
- parse_webhook(): normaliza a notificação de PAGAMENTO para a conciliação,
  identificando valor, pagador e referência (de qual boleto/processo veio).
"""
import logging

import httpx

logger = logging.getLogger("claudio.pagamentos")

BASES = {
    "asaas": "https://api.asaas.com/v3",
    "asaas_sandbox": "https://sandbox.asaas.com/api/v3",
}


class PagamentosError(Exception):
    pass


def parse_webhook(payload: dict) -> dict | None:
    """Normaliza o webhook de pagamento. Retorna None se não for evento de pagamento.

    Formato de saída:
      {referencia, valor, pagador, data_pagamento, provedor_id, evento}
    """
    evento = payload.get("event") or payload.get("evento") or ""
    pagamento = payload.get("payment") or payload.get("pagamento") or payload

    # Só interessa pagamento recebido/confirmado
    pago = evento in ("PAYMENT_RECEIVED", "PAYMENT_CONFIRMED") or str(
        pagamento.get("status", "")
    ).upper() in ("RECEIVED", "CONFIRMED", "PAID", "PAGO")
    if not pago:
        return None

    cliente = pagamento.get("customer")
    pagador = None
    if isinstance(cliente, dict):
        pagador = cliente.get("name")
    pagador = pagador or pagamento.get("payerName") or pagamento.get("pagador")

    return {
        "referencia": pagamento.get("externalReference") or pagamento.get("referencia"),
        "valor": pagamento.get("value") or pagamento.get("valor"),
        "pagador": pagador,
        "data_pagamento": pagamento.get("paymentDate") or pagamento.get("confirmedDate"),
        "provedor_id": pagamento.get("id"),
        "evento": evento or "pagamento",
    }


class PagamentosClient:
    def __init__(self, provedor: str, api_key: str, base_url: str | None = None):
        self.provedor = provedor
        self.api_key = api_key
        self.base_url = (base_url or BASES.get(provedor) or BASES["asaas"]).rstrip("/")

    @property
    def _headers(self) -> dict:
        # Asaas usa 'access_token'; outros podem usar Authorization.
        if self.provedor.startswith("asaas"):
            return {"access_token": self.api_key, "Content-Type": "application/json"}
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def _post(self, caminho: str, json: dict) -> dict:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(f"{self.base_url}{caminho}", headers=self._headers, json=json)
            if resp.status_code >= 400:
                raise PagamentosError(f"HTTP {resp.status_code}: {resp.text[:300]}")
            return resp.json()
        except httpx.HTTPError as exc:
            raise PagamentosError(f"Falha no provedor de pagamentos: {exc}") from exc

    async def criar_cobranca(
        self, nome: str, cpf: str | None, valor: float, vencimento: str,
        descricao: str, external_ref: str,
    ) -> dict:
        """Emite um boleto. Implementação de referência: Asaas (cria cliente + cobrança)."""
        if self.provedor.startswith("asaas"):
            cliente = await self._post("/customers", {"name": nome, "cpfCnpj": (cpf or "").replace(".", "").replace("-", "")})
            cobranca = await self._post(
                "/payments",
                {
                    "customer": cliente.get("id"),
                    "billingType": "BOLETO",
                    "value": float(valor),
                    "dueDate": vencimento,
                    "description": descricao,
                    "externalReference": external_ref,
                },
            )
            return {
                "id": cobranca.get("id"),
                "url": cobranca.get("bankSlipUrl") or cobranca.get("invoiceUrl"),
            }
        raise PagamentosError(f"Provedor '{self.provedor}' não implementado para emissão")
