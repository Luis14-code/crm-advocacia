# APIs e Credenciais — o que falta para rodar 100%

Guia único das integrações do Cláudio. Para cada uma: **o que faz**, **status**,
**como conseguir** e **o que me mandar / onde preencher**.

> Onde preencher no sistema: entre como **sócio** → **Dashboard do Dono → Integrações / API**
> (ou menu **Configurações**). Tudo fica guardado **cifrado** no banco.

---

## 1. DataJud (CNJ) — movimentações oficiais dos processos ✅ já funciona

- **O que faz:** fonte oficial do CNJ. Puxa as movimentações do processo pelo número
  CNJ (o "navegar no juiz" automático) e alimenta prazos, briefing e os avisos ao cliente.
- **Status:** **já funciona** com a chave pública do CNJ (embutida). Nada a fazer.
- **Opcional:** se quiser usar uma chave própria, dá para colar em Integrações → DataJud.

---

## 2. JusBrasil — fonte complementar (por advogado) 🟡 opcional

- **O que faz:** complementa o DataJud com dados enriquecidos, usando o login individual
  do advogado.
- **Como conseguir:** conta no JusBrasil de cada advogado. A captura é feita por um
  **userscript** (Tampermonkey) que instala no Chrome e envia os dados ao sistema.
- **O que fazer:** instalar `scripts/jusbrasil-userscript.user.js` no Tampermonkey e, se
  quiser um token de fallback, colar em Integrações → JusBrasil.
- **Precisa agora?** Não. O DataJud já cobre o essencial.

---

## 3. Gateway de pagamento / boleto 🔴 precisa do seu cadastro

- **O que faz:** **gera boletos de verdade**, recebe o aviso quando o cliente paga
  (**identifica quem pagou e de onde veio**), dá baixa automática e alimenta os gráficos.
  É a "API do banco para gerar boleto e receber as informações de recebimento".
- **Recomendado:** **Asaas** (tem ambiente **sandbox gratuito** para testar, e Pix + boleto).
  Alternativas: PagHiper, Cora, etc.
- **Como conseguir:**
  1. Crie conta em **asaas.com** (ou use o sandbox: sandbox.asaas.com).
  2. No painel do Asaas: **Configurações → Integrações → Chave de API** → copie a chave.
  3. Cadastre o **webhook de pagamento** apontando para:
     `http://SEU_HOST/api/pagamentos/webhook` (evento de pagamento recebido/confirmado).
- **O que me mandar:** a **API key** (e se é produção ou sandbox). Eu configuro em
  Integrações → Pagamentos/Banco (provedor + chave) e deixo o webhook pronto.
- **Pix:** sai por esse mesmo gateway quando a conta estiver ativa.

---

## 4. WhatsApp (WA-AKG) 🔴 precisa de número dedicado

- **O que faz:** envia os avisos ao cliente (movimentação, boleto) e recebe respostas.
  Gateway **não-oficial** (Baileys) — de graça, sem API paga.
- **Como conseguir:**
  1. Um **número/chip de WhatsApp dedicado** (NÃO o seu pessoal — há risco de bloqueio).
  2. Eu subo o container do WA-AKG aqui; ele abre um **QR Code**.
  3. Você **escaneia o QR** com o WhatsApp desse número.
  4. No painel do WA-AKG eu gero a **API key** e configuro em Integrações → WhatsApp.
- **O que me mandar:** só confirmar que tem o **número dedicado** pronto para parear.
  (Eu cuido do resto: subo o container, gero a chave, cadastro o webhook.)

---

## 5. Open Finance (extrato direto do banco) 🔵 futuro

- **O que faz:** saldo e extrato do seu banco em tempo real (conciliação automática total).
- **Status:** exige **credenciamento/certificado** junto à sua instituição (processo
  regulado e mais burocrático).
- **Enquanto isso:** a **importação de extrato OFX/CSV** já concilia os recebimentos
  (Financeiro → A receber → Importar extrato). O gateway (item 3) já identifica os boletos pagos.
- **Precisa agora?** Não. Quando você tiver as credenciais do banco, eu ligo.

---

## 6. LLM (Ollama) — IA local 🟢 opcional, melhora tudo

- **O que faz:** deixa muito melhor os resumos de reunião, as peças e o chat do Cláudio.
- **Status:** **não é API externa** — é um container local. Sem ele, tudo funciona com
  fallback por regras.
- **O que fazer:** eu subo o container e baixo o modelo (uma vez). É só pedir.

---

## Resumo: o que só você consegue providenciar

| # | Integração | Ação sua | Me manda |
|---|---|---|---|
| 3 | **Gateway de boleto (Asaas)** | Criar conta + copiar API key | A **API key** (prod ou sandbox) |
| 4 | **WhatsApp (WA-AKG)** | Ter um **número dedicado** | "Número pronto" (eu subo e gero o QR) |
| 2 | JusBrasil (opcional) | Instalar userscript / token | Token (se quiser) |
| 5 | Open Finance (futuro) | Credenciamento no banco | Quando tiver |

**Já prontos sem você:** DataJud (item 1) e, quando quiser, Ollama (item 6).

---

### Ordem sugerida para começar
1. **WhatsApp** — você só precisa do número; eu subo o WA-AKG e te mostro o QR agora.
2. **Asaas (boleto/Pix)** — você cria a conta (sandbox é grátis) e me passa a chave.
3. Depois: JusBrasil e Open Finance, conforme a necessidade.
