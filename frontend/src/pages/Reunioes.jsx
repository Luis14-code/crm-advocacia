import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, API_URL } from "../lib/api";

const STATUS_COR = {
  pendente: "bg-gray-100 text-gray-600",
  transcrevendo: "bg-yellow-100 text-yellow-700",
  concluido: "bg-green-100 text-green-700",
  erro: "bg-red-100 text-red-700",
};

export default function Reunioes() {
  const [reunioes, setReunioes] = useState([]);
  const [clientes, setClientes] = useState([]);
  const [processos, setProcessos] = useState([]);
  const [clienteId, setClienteId] = useState("");
  const [processoId, setProcessoId] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [msg, setMsg] = useState(null);
  const fileRef = useRef(null);

  async function carregar() {
    setReunioes(await api("/api/reunioes"));
  }

  useEffect(() => {
    carregar();
    api("/api/clientes").then(setClientes).catch(() => {});
    api("/api/processos").then(setProcessos).catch(() => {});
    const t = setInterval(carregar, 10000); // atualiza status
    return () => clearInterval(t);
  }, []);

  async function enviar(e) {
    e.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) return setMsg("Selecione um arquivo de áudio.");
    setEnviando(true);
    setMsg(null);

    const form = new FormData();
    form.append("audio", file);
    if (clienteId) form.append("cliente_id", clienteId);
    if (processoId) form.append("processo_id", processoId);

    try {
      const token = localStorage.getItem("access_token");
      const resp = await fetch(`${API_URL}/api/reunioes`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: resp.statusText }));
        throw new Error(err.detail);
      }
      setMsg("✓ Áudio enviado! A transcrição foi enfileirada.");
      fileRef.current.value = "";
      await carregar();
    } catch (err) {
      setMsg(`Erro: ${err.message}`);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-4">Reuniões</h1>

      {/* Upload */}
      <form onSubmit={enviar} className="bg-white rounded-xl border p-5 mb-6">
        <h2 className="font-semibold text-gray-700 mb-3">Nova gravação</h2>
        <div className="grid md:grid-cols-3 gap-3 mb-3">
          <input
            ref={fileRef}
            type="file"
            accept="audio/*,.m4a,.mp3,.wav,.ogg,.webm"
            className="text-sm border rounded-lg px-3 py-2"
          />
          <select value={clienteId} onChange={(e) => setClienteId(e.target.value)} className="border rounded-lg px-3 py-2 text-sm">
            <option value="">Cliente (opcional)</option>
            {clientes.map((c) => (
              <option key={c.id} value={c.id}>{c.nome}</option>
            ))}
          </select>
          <select value={processoId} onChange={(e) => setProcessoId(e.target.value)} className="border rounded-lg px-3 py-2 text-sm">
            <option value="">Processo (opcional)</option>
            {processos.map((p) => (
              <option key={p.id} value={p.id}>{p.numero}</option>
            ))}
          </select>
        </div>
        <button
          type="submit"
          disabled={enviando}
          className="bg-claudio text-white rounded-lg px-5 py-2 text-sm font-medium hover:bg-claudio-light disabled:opacity-60"
        >
          {enviando ? "Enviando..." : "Enviar e transcrever"}
        </button>
        {msg && <p className="mt-3 text-sm text-claudio">{msg}</p>}
      </form>

      {/* Lista */}
      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-left">
            <tr>
              <th className="px-4 py-2 font-medium">#</th>
              <th className="px-4 py-2 font-medium">Resumo</th>
              <th className="px-4 py-2 font-medium">Duração</th>
              <th className="px-4 py-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {reunioes.length === 0 ? (
              <tr><td colSpan={4} className="px-4 py-6 text-center text-gray-400">Nenhuma reunião ainda.</td></tr>
            ) : (
              reunioes.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2">
                    <Link to={`/reunioes/${r.id}`} className="text-claudio font-medium hover:underline">#{r.id}</Link>
                  </td>
                  <td className="px-4 py-2 text-gray-600 max-w-md truncate">{r.resumo || "—"}</td>
                  <td className="px-4 py-2 text-gray-500">{r.duracao_segundos ? `${r.duracao_segundos}s` : "—"}</td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-0.5 rounded-full text-xs ${STATUS_COR[r.status] || ""}`}>{r.status}</span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
