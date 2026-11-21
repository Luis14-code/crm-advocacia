# Runbook — Colocar o Cláudio para funcionar (Fases 1–4)

Este guia lista **tudo que precisa ser feito** para o sistema rodar de ponta a ponta,
separando o que é **automático** do que **depende de você** (cadastros/credenciais externas).

---

## 0. Pré-requisitos (uma vez)

- Docker + Docker Compose instalados.
- (Opcional, recomendado) GPU NVIDIA para acelerar LLM/transcrição.

---

## 1. Configurar o `.env`

```bash
cp .env.example .env
```

Gere e preencha as chaves obrigatórias:

```bash
# Chave JWT
python -c "import secrets; print('JWT_SECRET=' + secrets.token_urlsafe(48))"
# Chave Fernet (cifra tokens/segredos no banco)
python -c "from cryptography.fernet import Fernet; print('FERNET_KEY=' + Fernet.generate_key().decode())"
# Senha SENSÍVEL (abre Financeiro e Dashboard do Dono) — troque 'minha-senha'
python -c "import bcrypt; print('SENSITIVE_PASSWORD_HASH=' + bcrypt.hashpw(b'minha-senha', bcrypt.gensalt(12)).decode())"
```

> A **senha sensível** é a que você digita para entrar no Financeiro. Guarde-a — ela
> não fica em lugar nenhum além do hash no `.env`.

---

## 2. Subir o sistema (desenvolvimento)

```bash
docker compose --profile dev up -d --build
docker compose exec backend python seed.py   # dados iniciais (sócio/advogado/exemplos)
```

As migrations rodam sozinhas no boot. Acesse:
- Frontend: http://localhost:5173
- API/docs: http://localhost:8000/docs

Login: `socio@claudio.local` / `claudio123` (troque depois).

**Funciona de cara, sem nada externo:** CRM, agente (chat), DataJud (chave pública
embutida), prazos, briefing, reuniões/transcrição, peças, financeiro e simulador.

---

## 3. O que depende de VOCÊ (cadastros externos)

| Recurso | Precisa de você? | O quê |
|---|---|---|
| DataJud (movimentações) | **Não** | Usa a chave pública do CNJ. Opcional: chave própria em Configurações. |
| Transcrição (Whisper) | Não | Roda local. |
| LLM (resumos/peças melhores) | Opcional | Ligar o Ollama (passo 6). |
| **WhatsApp (WA-AKG)** | **Sim** | Um **número/chip dedicado** + parear (passo 4). |
| Boleto real | Depois | Conta num gateway (Asaas/PagHiper) — só quando formos integrar (passo 7). |

---

## 4. WhatsApp (WA-AKG) — passo a passo

> **Importante:** WA-AKG é um gateway **não-oficial** (Baileys). Use um **número dedicado**
> (não o seu pessoal). A estratégia anti-bloqueio já está no sistema: envios em **baixo
> volume, um a um, com sua confirmação**, **simulação de digitação** e **janela de horário
> (08h–20h)**. Mesmo assim, há risco residual de bloqueio do número — por isso, chip dedicado.

1. **Subir o gateway** (perfil `whatsapp`, baixa e compila o WA-AKG do GitHub na 1ª vez):
   ```bash
   docker compose --profile dev --profile whatsapp up -d --build
   ```
2. **Criar o admin do WA-AKG** (painel próprio dele, em http://localhost:3000):
   ```bash
   docker compose exec wa-akg npm run make-admin seu-email@exemplo.com suaSenha
   ```
3. **Gerar a API key** no painel do WA-AKG (http://localhost:3000) e **copiar**.
4. No Cláudio, entre como sócio em **Configurações → WhatsApp (WA-AKG)**:
   - URL base: `http://wa-akg:3000`
   - Session ID: `claudio`
   - API key: cole a chave gerada → **Salvar**.
5. Vá em **WhatsApp → Conectar / QR** e **escaneie o QR** com o WhatsApp do número dedicado.
6. **Registrar o webhook** (para receber mensagens) no painel do WA-AKG, apontando para:
   ```
   http://backend:8000/api/whatsapp/webhook
   ```
   (evento `message.received`).

Pronto. A partir daí:
- Movimentação nova → o Cláudio **prepara** uma mensagem que fica **aguardando sua
  confirmação** na tela de WhatsApp. Você aprova → ele envia “digitando” e com intervalo.
- Você também pode preparar mensagens manuais ou pedir ao Cláudio no chat
  (“avise o cliente X que…”).
- Clientes com **opt-out** nunca recebem.

---

## 5. Financeiro

- Menu **Financeiro** (perfis sócio/financeiro) pede a **senha sensível** (a do passo 1).
- Abas: resumo (KPIs), transações e **simulador de acordo** (deduções, líquido do
  cliente, honorários e comparativo por jurimetria).

---

## 6. (Opcional) Ligar o LLM local (Ollama)

Melhora resumos de reunião, fundamentos de peças e a classificação de intenções do chat.

```bash
docker compose --profile dev --profile llm up -d
docker compose exec ollama ollama pull llama3.1:8b
```
Sem o Ollama, tudo continua funcionando via fallback por regras.

---

## 7. Boleto real (quando formos integrar — futuro)

Hoje o boleto é **placeholder** (registra a cobrança e agenda o aviso, sem banco real).
Para emitir boleto de verdade, você precisará criar conta num gateway (ex.: **Asaas** ou
**PagHiper**) e me passar a API key — a integração entra como as outras (gerenciável em
Configurações). Me avise quando quiser e eu implemento.

---

## Resumo do que você precisa providenciar

1. **Senha sensível** (você define no `.env`, passo 1).
2. **Número/chip de WhatsApp dedicado** + parear o QR (passo 4).
3. (Depois) **Conta num gateway de boleto**, só quando formos ligar boleto real.

Todo o resto é automático.
