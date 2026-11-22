import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { useAuth } from "../stores/auth";

export default function Whatsapp() {
  const user = useAuth((s) => s.user);
  const [status, setStatus] = useState(null);
  const [qr, setQr] = useState(null);
  const [pareando, setPareando] = useState(false);
  const [pendentes, setPendentes] = useState([]);
  const [historico, setHistorico] = useState([]);
  const [clientes, setClientes] = useState([]);
  const [clienteId, setClienteId] = useState("");
  const [texto, setTexto] = useState("");
  const [msg, setMsg] = useState(null);

  async function carregar() {
    try {
      setStatus(await api("/api/whatsapp/status"));
      setPendentes(await api("/api/whatsapp/pendentes"));
    } catch (e) {
      setMsg(e.message);
    }
  }

  useEffect(() => {
    carregar();
    api("/api/clientes").then(setClientes).catch(() => {});
    const t = setInterval(carregar, 15000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    if (clienteId) api(`/api/whatsapp/mensagens?cliente_id=${clienteId}`).then(setHistorico).catch(() => {});
  }, [clienteId]);

  async function conectar() {
    setMsg(null);
    setQr(null);
    try {
      await api("/api/whatsapp/conectar", { method: "POST" });
      setPareando(true);
      try {
        const r = await api("/api/whatsapp/qr");
        if (r.base64) setQr(r.base64);
      } catch {
        /* QR pode levar 1-2s; o poll abaixo pega */
      }
    } catch (e) {
      setMsg(e.message);
    }
  }

  // Enquanto pareia: o QR do WhatsApp expira em segundos, então renova sozinho até conectar.
  useEffect(() => {
    if (!pareando) return;
    const t = setInterval(async () => {
      try {
        const s = await api("/api/whatsapp/status");
        setStatus(s);
        if (s.conectado) {
          setPareando(false);
          setQr(null);
          setMsg("✓ WhatsApp conectado!");
          return;
        }
        const r = await api("/api/whatsapp/qr");
        if (r.base64) setQr(r.base64);
      } catch {
        /* ignora falhas transitórias do QR */
      }
    }, 4000);
    return () => clearInterval(t);
  }, [pareando]);

  async function aprovar(id) {
    await api(`/api/whatsapp/${id}/aprovar`, { method: "POST" });
    carregar();
  }
  async function rejeitar(id) {
    await api(`/api/whatsapp/${id}/rejeitar`, { method: "POST" });
    carregar();
  }

  async function enviar(e) {
    e.preventDefault();
    setMsg(null);
    try {
      await api("/api/whatsapp/enviar", {
        method: "POST",
        body: { cliente_id: Number(clienteId), texto },
      });
      setTexto("");
      setMsg("Mensagem criada e aguardando sua confirmação abaixo.");
      carregar();
    } catch (e) {
      setMsg(`Erro: ${e.message}`);
    }
  }

  const ehSocio = user?.perfil === "socio";

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-4">WhatsApp</h1>
      {msg && <p className="mb-3 text-sm text-claudio bg-blue-50 rounded-lg px-3 py-2">{msg}</p>}

      {/* Status */}
      <div className="bg-white rounded-xl border p-5 mb-5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className={`w-3 h-3 rounded-full ${status?.conectado ? "bg-green-500" : "bg-gray-400"}`} />
          <div>
            <p className="font-medium text-gray-800">
              {!status?.configurado ? "Gateway não configurado" : status?.conectado ? "Conectado" : "Desconectado"}
            </p>
            <p className="text-xs text-gray-500">{status?.detalhe || (!status?.configurado && "Defina a API key do WA-AKG em Configurações")}</p>
          </div>
        </div>
        {ehSocio && status?.configurado && (
          <button onClick={conectar} className="bg-claudio text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-claudio-light">
            Conectar / QR
          </button>
        )}
      </div>

      {qr && (
        <div className="bg-white rounded-xl border p-5 mb-5 text-center">
          <p className="text-sm text-gray-600 mb-2">Escaneie com o WhatsApp do número dedicado:</p>
          <img src={qr} alt="QR" className="mx-auto w-56 h-56" />
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-6">
        {/* Pendentes */}
        <div className="bg-white rounded-xl border p-5">
          <h2 className="font-semibold text-gray-700 mb-3">Aguardando confirmação ({pendentes.length})</h2>
          {pendentes.length === 0 ? (
            <p className="text-gray-400 text-sm">Nada pendente.</p>
          ) : (
            <ul className="space-y-3">
              {pendentes.map((p) => (
                <li key={p.id} className="border rounded-lg p-3">
                  <p className="text-xs text-gray-400">{p.gatilho} · {p.telefone}</p>
                  <p className="text-sm text-gray-800 my-1">{p.texto}</p>
                  <div className="flex gap-2">
                    <button onClick={() => aprovar(p.id)} className="text-xs bg-green-600 text-white rounded px-3 py-1">Aprovar e enviar</button>
                    <button onClick={() => rejeitar(p.id)} className="text-xs border rounded px-3 py-1">Rejeitar</button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Enviar + histórico */}
        <div className="bg-white rounded-xl border p-5">
          <h2 className="font-semibold text-gray-700 mb-3">Conversa</h2>
          <select value={clienteId} onChange={(e) => setClienteId(e.target.value)} className="w-full border rounded-lg px-3 py-2 text-sm mb-3">
            <option value="">Selecione um cliente</option>
            {clientes.map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
          </select>

          {clienteId && (
            <>
              <div className="max-h-56 overflow-auto space-y-2 mb-3">
                {historico.length === 0 ? (
                  <p className="text-gray-400 text-sm">Sem mensagens.</p>
                ) : historico.slice().reverse().map((m) => (
                  <div key={m.id} className={`flex ${m.direcao === "saida" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[80%] rounded-2xl px-3 py-1.5 text-sm ${m.direcao === "saida" ? "bg-claudio text-white" : "bg-gray-100"}`}>
                      {m.texto}
                      <div className="text-[10px] opacity-70 mt-0.5">{m.status}</div>
                    </div>
                  </div>
                ))}
              </div>
              <form onSubmit={enviar} className="flex gap-2">
                <input value={texto} onChange={(e) => setTexto(e.target.value)} placeholder="Mensagem..." className="flex-1 border rounded-lg px-3 py-2 text-sm" />
                <button type="submit" className="bg-claudio text-white rounded-lg px-4 text-sm font-medium">Preparar</button>
              </form>
              <p className="text-xs text-gray-400 mt-1">A mensagem entra como pendente até você aprovar.</p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
