// ==UserScript==
// @name         Cláudio — Varredura JusBrasil
// @namespace    claudio.crm
// @version      0.2.0
// @description  Após o login manual no JusBrasil, varre os processos do advogado e envia os andamentos ao Cláudio (que faz a análise + plano de ação).
// @match        https://www.jusbrasil.com.br/*
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_xmlhttpRequest
// @connect      localhost
// @connect      127.0.0.1
// ==/UserScript==

/*
 * COMO FUNCIONA (sem guardar senha):
 *   1. O advogado faz login NORMAL no JusBrasil (no navegador dele).
 *   2. Abre a página "Meus processos" / monitoramento (a lista dele).
 *   3. Clica em "⚖️ Varrer meus processos": o script percorre cada processo,
 *      extrai os andamentos e envia ao Cláudio. A senha nunca sai do JusBrasil.
 *   4. No Cláudio, a aba "Análise do dia" mostra o resumo + plano de ação e
 *      rascunha as mensagens (que vão para a fila de pré-aprovação).
 *
 * CONFIGURAÇÃO (uma vez só):
 *   - Backend: por padrão http://localhost:8000. Hospedou? Clique em "⚙" e troque.
 *   - Token: no Cláudio, abra o Console (F12) e rode:
 *         localStorage.getItem('access_token')
 *     Copie e cole no script quando ele pedir. Fica salvo (não precisa repetir).
 *
 * IMPORTANTE (seletores): o JusBrasil muda o HTML com frequência. Os seletores de
 * extração estão em SELETORES e PADROES abaixo, marcados com "AJUSTE". Se a varredura
 * não achar andamentos, é só ajustar ali conforme a página real.
 */

(function () {
  "use strict";

  const CNJ_RE = /\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/g;
  const DATA_RE = /(\d{2})\/(\d{2})\/(\d{4})/;

  // AJUSTE: seletores candidatos para a lista de processos e para os andamentos.
  const SELETORES = {
    // Links que levam à página de um processo (na lista "Meus processos").
    linkProcesso: 'a[href*="/processos/"], a[href*="/consulta"], a[href*="/diarios/"], a[href*="processo"]',
    // Blocos de andamento/movimentação dentro da página de um processo.
    andamento: '[data-movimentacao], [data-testid*="movimenta"], .andamento, .timeline-item, .movimentacao, li[class*="andament"]',
  };

  // ---------- util ----------
  const cfg = {
    get backend() { return GM_getValue("claudio_backend", "http://localhost:8000"); },
    set backend(v) { GM_setValue("claudio_backend", v); },
    get token() { return GM_getValue("claudio_token", ""); },
    set token(v) { GM_setValue("claudio_token", (v || "").trim()); },
  };

  function getToken() {
    let t = cfg.token;
    if (!t) {
      t = prompt("Cole seu token do Cláudio (localStorage 'access_token'):") || "";
      if (t) cfg.token = t;
    }
    return cfg.token;
  }

  function dataISO(texto) {
    const m = (texto || "").match(DATA_RE);
    if (!m) return null;
    return `${m[3]}-${m[2]}-${m[1]}`;
  }

  function http(method, url, { headers = {}, data = null } = {}) {
    return new Promise((resolve, reject) => {
      GM_xmlhttpRequest({
        method, url, headers, data,
        onload: (r) => resolve({ status: r.status, text: r.responseText, finalUrl: r.finalUrl }),
        onerror: () => reject(new Error("Falha de conexão: " + url)),
        ontimeout: () => reject(new Error("Tempo esgotado: " + url)),
        timeout: 30000,
      });
    });
  }

  // ---------- extração ----------
  // Extrai {numero, movimentacoes[]} de um documento (a página atual ou uma baixada).
  function extrair(doc) {
    const texto = (doc.body && doc.body.innerText) || "";
    const numero = (texto.match(CNJ_RE) || [])[0] || null;

    const vistos = new Set();
    const movs = [];
    let blocos = Array.from(doc.querySelectorAll(SELETORES.andamento));

    // Fallback: se nenhum seletor casou, varre elementos pequenos que contêm uma data.
    if (!blocos.length) {
      blocos = Array.from(doc.querySelectorAll("li, tr, p, div")).filter((el) => {
        const t = el.innerText || "";
        return DATA_RE.test(t) && t.length < 600 && el.children.length < 8;
      });
    }

    for (const el of blocos) {
      const t = (el.innerText || "").replace(/\s+/g, " ").trim();
      const data = dataISO(t);
      if (!data) continue;
      const descricao = t.slice(0, 1000);
      const chave = data + "|" + descricao.slice(0, 80);
      if (vistos.has(chave)) continue;
      vistos.add(chave);
      movs.push({ data, descricao, tipo: "jusbrasil" });
    }
    return { numero, movimentacoes: movs };
  }

  async function enviar(payload) {
    const token = getToken();
    if (!token) throw new Error("Token do Cláudio não configurado.");
    const r = await http("POST", `${cfg.backend}/api/sync/jusbrasil`, {
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      data: JSON.stringify(payload),
    });
    if (r.status !== 200) throw new Error(`HTTP ${r.status}: ${r.text.slice(0, 160)}`);
    return JSON.parse(r.text);
  }

  // ---------- ações ----------
  async function sincronizarPagina(log) {
    const payload = extrair(document);
    if (!payload.numero) { log("⚠️ Não achei número CNJ nesta página.", "erro"); return; }
    log(`Enviando ${payload.numero} (${payload.movimentacoes.length} andamento[s])...`);
    try {
      const res = await enviar(payload);
      log(`✓ ${payload.numero}: ${res.novas} nova(s), ${res.prazos} prazo(s).`, "ok");
    } catch (e) {
      log(`✗ ${payload.numero}: ${e.message}`, "erro");
    }
  }

  function coletarLinksProcessos() {
    const links = new Set();
    document.querySelectorAll(SELETORES.linkProcesso).forEach((a) => {
      if (a.href) links.add(a.href.split("#")[0]);
    });
    return Array.from(links);
  }

  async function varrerProcessos(log) {
    const links = coletarLinksProcessos();
    if (!links.length) {
      log("Não encontrei links de processos nesta página. Abra a lista 'Meus processos' e tente de novo. (Ou use 'Sincronizar esta página' dentro de um processo.)", "erro");
      return;
    }
    log(`Encontrei ${links.length} processo(s). Iniciando varredura...`);
    let ok = 0, falhas = 0;
    for (const [i, url] of links.entries()) {
      try {
        const r = await http("GET", url);
        const doc = new DOMParser().parseFromString(r.text, "text/html");
        const payload = extrair(doc);
        if (!payload.numero) { log(`(${i + 1}/${links.length}) sem CNJ — pulado`); continue; }
        const res = await enviar(payload);
        ok++;
        log(`(${i + 1}/${links.length}) ✓ ${payload.numero}: ${res.novas} nova(s), ${res.prazos} prazo(s).`, "ok");
      } catch (e) {
        falhas++;
        log(`(${i + 1}/${links.length}) ✗ ${e.message}`, "erro");
      }
      await new Promise((r) => setTimeout(r, 1200 + Math.random() * 800)); // educação anti-bloqueio
    }
    log(`Fim da varredura: ${ok} enviado(s), ${falhas} falha(s). Veja a 'Análise do dia' no Cláudio.`, "ok");
  }

  // ---------- painel ----------
  function montarPainel() {
    const box = document.createElement("div");
    Object.assign(box.style, {
      position: "fixed", bottom: "20px", right: "20px", zIndex: 999999, width: "320px",
      background: "#fff", color: "#111", border: "1px solid #d1d5db", borderRadius: "12px",
      boxShadow: "0 8px 30px rgba(0,0,0,.18)", font: "13px/1.4 system-ui, sans-serif", overflow: "hidden",
    });
    box.innerHTML = `
      <div style="background:#1e3a5f;color:#fff;padding:10px 12px;display:flex;align-items:center;justify-content:space-between">
        <strong>⚖️ Cláudio — JusBrasil</strong>
        <span style="cursor:pointer" data-cfg title="Configurar backend">⚙</span>
      </div>
      <div style="padding:12px;display:flex;flex-direction:column;gap:8px">
        <button data-varrer style="background:#1e3a5f;color:#fff;border:none;border-radius:8px;padding:9px;cursor:pointer;font-weight:600">Varrer meus processos</button>
        <button data-pagina style="background:#eef2f7;color:#1e3a5f;border:none;border-radius:8px;padding:8px;cursor:pointer">Sincronizar esta página</button>
        <div data-log style="max-height:160px;overflow:auto;background:#f8fafc;border:1px solid #eef2f7;border-radius:8px;padding:8px;font-size:12px;color:#334155;display:none"></div>
      </div>`;
    document.body.appendChild(box);

    const logEl = box.querySelector("[data-log]");
    const log = (m, tipo) => {
      logEl.style.display = "block";
      const cor = tipo === "ok" ? "#15803d" : tipo === "erro" ? "#b91c1c" : "#334155";
      const linha = document.createElement("div");
      linha.style.color = cor;
      linha.textContent = m;
      logEl.appendChild(linha);
      logEl.scrollTop = logEl.scrollHeight;
    };

    box.querySelector("[data-varrer]").onclick = () => varrerProcessos(log);
    box.querySelector("[data-pagina]").onclick = () => sincronizarPagina(log);
    box.querySelector("[data-cfg]").onclick = () => {
      const url = prompt("URL do backend do Cláudio:", cfg.backend);
      if (url) { cfg.backend = url.trim(); log(`Backend: ${cfg.backend}`); }
      const trocarToken = confirm("Deseja (re)configurar o token do Cláudio agora?");
      if (trocarToken) { cfg.token = ""; getToken(); }
    };
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", montarPainel);
  } else {
    montarPainel();
  }
})();
