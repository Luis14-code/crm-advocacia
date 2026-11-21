"""Base de conhecimento de teses jurídicas (foco previdenciário).

Mapeia tipo/subtipo de processo para teses pertinentes. Serve de ponto de partida
para o plugin sugerir_tese, que ainda enriquece com a jurimetria interna do escritório.
"""

TESES_PREVIDENCIARIO: dict[str, list[str]] = {
    "aposentadoria_tempo": [
        "Reconhecimento de atividade especial (PPP + LTCAT) e conversão em tempo comum (fator 1,4)",
        "Revisão da vida toda (Tema 1102/STF) — observar modulação e coisa julgada",
        "Cômputo de tempo rural com início de prova material + prova testemunhal",
    ],
    "aposentadoria_idade": [
        "Aposentadoria por idade híbrida (soma de tempo urbano e rural)",
        "Reconhecimento de tempo rural em regime de economia familiar",
    ],
    "aux_doenca": [
        "Auxílio-doença por incapacidade temporária com perícia judicial",
        "Conversão em aposentadoria por incapacidade permanente (invalidez)",
        "Pedido de restabelecimento com DCB indevida (cessação do INSS)",
    ],
    "invalidez": [
        "Aposentadoria por incapacidade permanente com acréscimo de 25% (grande invalidez)",
        "Incapacidade multiprofissional considerando idade e condições socioeconômicas",
    ],
    "loas": [
        "Benefício assistencial (LOAS) ao idoso/deficiente — critério de miserabilidade (1/4 do salário mínimo)",
        "Afastamento do critério objetivo de renda por elementos do caso concreto",
    ],
    "especial": [
        "Conversão de tempo especial em comum (exposição a agentes nocivos)",
        "Enquadramento por categoria profissional até 28/04/1995",
    ],
}

TESES_GENERICAS = [
    "Verificar prescrição quinquenal das parcelas vencidas",
    "Analisar possibilidade de tutela de urgência (risco + probabilidade do direito)",
]


def sugerir(tipo: str | None, subtipo: str | None) -> list[str]:
    tipo = (tipo or "").lower()
    subtipo = (subtipo or "").lower()

    if tipo and "previden" not in tipo and tipo not in ("", "previdenciario"):
        return TESES_GENERICAS

    # Procura por correspondência de subtipo (chave contida no subtipo informado)
    for chave, teses in TESES_PREVIDENCIARIO.items():
        if chave in subtipo or any(parte in subtipo for parte in chave.split("_")):
            return teses + TESES_GENERICAS

    # Sem subtipo claro: devolve um panorama previdenciário
    panorama = []
    for teses in TESES_PREVIDENCIARIO.values():
        panorama.append(teses[0])
    return panorama + TESES_GENERICAS
