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

  // Gravação ao vivo
  const [gravando, setGravando] = useState(false);
  const [segundos, setSegundos] = useState(0);
  const [blobGravado, setBlobGravado] = useState(null);
  const recorderRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);

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

  async function uploadAudio(file) {
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
      setMsg("✓ Áudio enviado! O Cláudio vai transcrever e montar o relatório.");
      await carregar();
      return true;
    } catch (err) {
      setMsg(`Erro: ${err.message}`);
      return false;
    } finally {
      setEnviando(false);
    }
  }

  async function enviar(e) {
    e.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) return setMsg("Selecione um arquivo de áudio.");
    if (await uploadAudio(file)) fileRef.current.value = "";
  }

  async function iniciarGravacao() {
    setMsg(null);
    setBlobGravado(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      chunksRef.current = [];
      rec.ondataavailable = (e) => e.data.size > 0 && chunksRef.current.push(e.data);
      rec.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        setBlobGravado(blob);
        stream.getTracks().forEach((t) => t.stop());
      };
      recorderRef.current = rec;
      rec.start();
      setGravando(true);
      setSegundos(0);
      timerRef.current = setInterval(() => setSegundos((s) => s + 1), 1000);
    } catch {
      setMsg("Não consegui acessar o microfone. Permita o acesso no navegador.");
    }
  }

  function pararGravacao() {
    recorderRef.current?.stop();
    setGravando(false);
    clearInterval(timerRef.current);
  }

  async function processarGravacao() {
    if (!blobGravado) return;
    const file = new File([blobGravado], `reuniao-${Date.now()}.webm`, { type: "audio/webm" });
    if (await uploadAudio(file)) setBlobGravado(null);
  }

  const mmss = `${String(Math.floor(segundos / 60)).padStart(2, "0")}:${String(segundos % 60).padStart(2, "0")}`;

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-4">Reuniões</h1>

      {/* Nova reunião */}
      <div className="bg-white rounded-xl border p-5 mb-6">
        <h2 className="font-semibold text-gray-700 mb-3">Nova reunião</h2>

        {/* Cliente / processo */}
        <div className="grid md:grid-cols-2 gap-3 mb-4">
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

        {/* Gravar ao vivo */}
        <div className="rounded-lg border border-dashed p-4 mb-4">
          <div className="flex items-center gap-4">
            {!gravando ? (
              <button onClick={iniciarGravacao} disabled={enviando}
                className="flex items-center gap-2 bg-red-600 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-red-700 disabled:opacity-60">
                <span className="w-2.5 h-2.5 rounded-full bg-white" /> Gravar reunião
              </button>
            ) : (
              <button onClick={pararGravacao}
                className="flex items-center gap-2 bg-gray-800 text-white rounded-lg px-4 py-2 text-sm font-medium">
                ⏹ Parar
              </button>
            )}

            {/* "terminal" de gravação */}
            {gravando && (
              <div className="flex items-center gap-2 text-sm text-red-600">
                <span className="w-3 h-3 rounded-full bg-red-600 animate-pulse" />
                Gravando… <span className="font-mono">{mmss}</span>
              </div>
            )}

            {!gravando && blobGravado && (
              <div className="flex items-center gap-3">
                <audio controls src={URL.createObjectURL(blobGravado)} className="h-8" />
                <button onClick={processarGravacao} disabled={enviando}
                  className="bg-claudio text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-claudio-light disabled:opacity-60">
                  {enviando ? "Processando..." : "Processar"}
                </button>
              </div>
            )}
          </div>
          <p className="text-xs text-gray-400 mt-2">
            Grave a reunião e clique em <strong>Processar</strong> — o Cláudio transcreve e monta o relatório com os pontos cruciais.
          </p>
        </div>

        {/* Ou enviar arquivo */}
        <form onSubmit={enviar} className="flex flex-wrap items-center gap-3">
          <span className="text-sm text-gray-500">ou envie um arquivo:</span>
          <input
            ref={fileRef}
            type="file"
            accept="audio/*,.m4a,.mp3,.wav,.ogg,.webm"
            className="text-sm border rounded-lg px-3 py-1.5"
          />
          <button type="submit" disabled={enviando}
            className="bg-claudio text-white rounded-lg px-4 py-1.5 text-sm font-medium hover:bg-claudio-light disabled:opacity-60">
            {enviando ? "Enviando..." : "Enviar"}
          </button>
        </form>

        {msg && <p className="mt-3 text-sm text-claudio">{msg}</p>}
      </div>

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
