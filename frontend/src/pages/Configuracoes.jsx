import { useEffect, useState } from "react";
import { api } from "../lib/api";

const FONTE_LABEL = {
  db: { txt: "Configurada no sistema", cor: "text-green-700 bg-green-100" },
  env: { txt: "Vinda do .env", cor: "text-blue-700 bg-blue-100" },
  publico: { txt: "Usando chave pública padrão do CNJ", cor: "text-gray-600 bg-gray-100" },
};

export default function Configuracoes() {
  const [status, setStatus] = useState(null);
  const [datajudKey, setDatajudKey] = useState("");
  const [jusbrasil, setJusbrasil] = useState("");
  const [waUrl, setWaUrl] = useState("");
  const [waKey, setWaKey] = useState("");
  const [waSession, setWaSession] = useState("");
  const [teste, setTeste] = useState(null);
  const [msg, setMsg] = useState(null);
  const [salvando, setSalvando] = useState(false);
  const [testando, setTestando] = useState(false);

  async function carregar() {
    try {
      setStatus(await api("/api/config/integracoes"));
    } catch (e) {
      setMsg(e.message);
    }
  }

  useEffect(() => {
    carregar();
  }, []);

  async function salvar() {
    setSalvando(true);
    setMsg(null);
    try {
      const body = {};
      if (datajudKey !== "") body.datajud_api_key = datajudKey;
      if (jusbrasil !== "") body.jusbrasil_default_token = jusbrasil;
      if (waUrl !== "") body.waakg_base_url = waUrl;
      if (waKey !== "") body.waakg_api_key = waKey;
      if (waSession !== "") body.waakg_session_id = waSession;
      const novo = await api("/api/config/integracoes", { method: "PUT", body });
      setStatus(novo);
      setDatajudKey("");
      setJusbrasil("");
      setWaUrl("");
      setWaKey("");
      setWaSession("");
      setMsg("✓ Configurações salvas.");
    } catch (e) {
      setMsg(`Erro: ${e.message}`);
    } finally {
      setSalvando(false);
    }
  }

  async function testarDatajud() {
    setTestando(true);
    setTeste(null);
    try {
      const r = await api("/api/config/integracoes/testar-datajud", {
        method: "POST",
        body: datajudKey ? { api_key: datajudKey } : {},
      });
      setTeste(r);
    } catch (e) {
      setTeste({ ok: false, detalhe: e.message });
    } finally {
      setTestando(false);
    }
  }

  const fonte = status ? FONTE_LABEL[status.datajud_fonte] : null;

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold text-gray-800 mb-1">Configurações · Integrações</h1>
      <p className="text-gray-500 mb-6">
        Gerencie as chaves de API usadas pelo Cláudio. Valores são guardados cifrados no banco.
      </p>

      {msg && <p className="mb-4 text-sm text-claudio bg-blue-50 rounded-lg px-3 py-2">{msg}</p>}

      {/* DataJud */}
      <div className="bg-white rounded-xl border p-5 mb-5">
        <div className="flex items-center justify-between mb-2">
          <h2 className="font-semibold text-gray-700">DataJud (CNJ)</h2>
          {fonte && (
            <span className={`text-xs px-2 py-0.5 rounded-full ${fonte.cor}`}>{fonte.txt}</span>
          )}
        </div>
        <p className="text-sm text-gray-500 mb-3">
          Fonte oficial de movimentações. Funciona com a chave pública padrão; informe uma
          chave própria aqui se desejar.
        </p>
        <label className="block text-sm font-medium text-gray-700 mb-1">API key</label>
        <input
          type="password"
          value={datajudKey}
          onChange={(e) => setDatajudKey(e.target.value)}
          placeholder={status?.datajud_configurada ? "•••••••• (configurada — deixe em branco para manter)" : "Cole a API key do DataJud"}
          className="w-full border rounded-lg px-3 py-2 mb-3 focus:outline-none focus:ring-2 focus:ring-claudio-light"
        />
        <div className="flex items-center gap-3">
          <button
            onClick={testarDatajud}
            disabled={testando}
            className="text-sm border border-claudio text-claudio rounded-lg px-3 py-1.5 hover:bg-claudio hover:text-white transition disabled:opacity-60"
          >
            {testando ? "Testando..." : "Testar conexão"}
          </button>
          {teste && (
            <span className={`text-sm ${teste.ok ? "text-green-700" : "text-red-600"}`}>
              {teste.ok ? "✓" : "✗"} {teste.detalhe}
            </span>
          )}
        </div>
      </div>

      {/* JusBrasil */}
      <div className="bg-white rounded-xl border p-5 mb-5">
        <div className="flex items-center justify-between mb-2">
          <h2 className="font-semibold text-gray-700">JusBrasil (fallback)</h2>
          <span className={`text-xs px-2 py-0.5 rounded-full ${status?.jusbrasil_configurado ? "text-green-700 bg-green-100" : "text-gray-600 bg-gray-100"}`}>
            {status?.jusbrasil_configurado ? "Configurado" : "Não configurado"}
          </span>
        </div>
        <p className="text-sm text-gray-500 mb-3">
          Token padrão de fallback. Cada advogado também pode ter o token individual no perfil.
        </p>
        <label className="block text-sm font-medium text-gray-700 mb-1">Token</label>
        <input
          type="password"
          value={jusbrasil}
          onChange={(e) => setJusbrasil(e.target.value)}
          placeholder={status?.jusbrasil_configurado ? "•••••••• (deixe em branco para manter)" : "Token do JusBrasil"}
          className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-claudio-light"
        />
      </div>

      {/* WhatsApp (WA-AKG) */}
      <div className="bg-white rounded-xl border p-5 mb-5">
        <div className="flex items-center justify-between mb-2">
          <h2 className="font-semibold text-gray-700">WhatsApp (WA-AKG)</h2>
          <span className={`text-xs px-2 py-0.5 rounded-full ${status?.waakg_configurado ? "text-green-700 bg-green-100" : "text-gray-600 bg-gray-100"}`}>
            {status?.waakg_configurado ? "Configurado" : "Não configurado"}
          </span>
        </div>
        <p className="text-sm text-gray-500 mb-3">
          Gateway não-oficial (Baileys). Gere a API key no painel do WA-AKG e cole aqui.
          Depois conecte e pareie o número na tela de WhatsApp.
        </p>
        <div className="grid md:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">URL base</label>
            <input value={waUrl} onChange={(e) => setWaUrl(e.target.value)}
              placeholder={status?.waakg_base_url || "http://wa-akg:3000"}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-claudio-light" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Session ID</label>
            <input value={waSession} onChange={(e) => setWaSession(e.target.value)}
              placeholder={status?.waakg_session_id || "claudio"}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-claudio-light" />
          </div>
        </div>
        <label className="block text-xs font-medium text-gray-600 mb-1 mt-3">API key (X-API-Key)</label>
        <input type="password" value={waKey} onChange={(e) => setWaKey(e.target.value)}
          placeholder={status?.waakg_configurado ? "•••••••• (deixe em branco para manter)" : "API key do WA-AKG"}
          className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-claudio-light" />
      </div>

      <button
        onClick={salvar}
        disabled={salvando}
        className="bg-claudio text-white rounded-lg px-5 py-2 font-medium hover:bg-claudio-light disabled:opacity-60"
      >
        {salvando ? "Salvando..." : "Salvar"}
      </button>
    </div>
  );
}
