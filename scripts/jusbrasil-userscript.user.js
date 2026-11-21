// ==UserScript==
// @name         Cláudio — Sync JusBrasil
// @namespace    claudio.crm
// @version      0.1.0
// @description  Extrai movimentações de páginas de processo do JusBrasil e envia ao Cláudio.
// @match        https://www.jusbrasil.com.br/*
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_xmlhttpRequest
// @connect      localhost
// ==/UserScript==

/*
 * CONFIGURAÇÃO (uma vez):
 *   1. Faça login no Cláudio, abra o Console do navegador e rode:
 *        localStorage.getItem('access_token')
 *   2. Copie o token e, ao clicar no botão "Sincronizar", cole quando solicitado.
 *   O token e a URL do backend ficam salvos no Tampermonkey (GM_setValue).
 */

(function () {
  "use strict";

  const BACKEND = GM_getValue("claudio_backend", "http://localhost:8000");

  function getToken() {
    let t = GM_getValue("claudio_token", "");
    if (!t) {
      t = prompt("Cole seu token do Cláudio (access_token):") || "";
      if (t) GM_setValue("claudio_token", t.trim());
    }
    return t;
  }

  // Extrai o número CNJ e as movimentações da página (seletores ajustáveis à página real).
  function extrair() {
    const texto = document.body.innerText;
    const cnj = (texto.match(/\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}/) || [])[0];
    const movs = [];
    document.querySelectorAll("[data-movimentacao], .andamento, .timeline-item").forEach((el) => {
      const data = (el.innerText.match(/\d{2}\/\d{2}\/\d{4}/) || [])[0];
      const descricao = el.innerText.replace(/\s+/g, " ").trim().slice(0, 500);
      if (data && descricao) {
        const [d, m, a] = data.split("/");
        movs.push({ data: `${a}-${m}-${d}`, descricao, tipo: "jusbrasil" });
      }
    });
    return { numero: cnj, movimentacoes: movs };
  }

  function enviar() {
    const token = getToken();
    if (!token) return alert("Token não configurado.");
    const payload = extrair();
    if (!payload.numero) return alert("Não encontrei número CNJ nesta página.");

    GM_xmlhttpRequest({
      method: "POST",
      url: `${BACKEND}/api/sync/jusbrasil`,
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      data: JSON.stringify(payload),
      onload: (r) =>
        alert(r.status === 200 ? "Sincronizado com o Cláudio!" : `Erro ${r.status}: ${r.responseText}`),
      onerror: () => alert("Falha de conexão com o backend do Cláudio."),
    });
  }

  // Botão flutuante
  const btn = document.createElement("button");
  btn.textContent = "⚖️ Sincronizar com o Cláudio";
  Object.assign(btn.style, {
    position: "fixed", bottom: "20px", right: "20px", zIndex: 99999,
    background: "#1e3a5f", color: "#fff", border: "none", borderRadius: "8px",
    padding: "10px 14px", cursor: "pointer", fontWeight: "600",
  });
  btn.onclick = enviar;
  document.body.appendChild(btn);
})();
