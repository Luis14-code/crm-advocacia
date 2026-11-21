import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { api, authedUrl } from "../lib/api";

export default function ReuniaoDetalhe() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [r, setR] = useState(null);
  const [fatos, setFatos] = useState("");
  const [pendencias, setPendencias] = useState("");
  const [msg, setMsg] = useState(null);
  const [gerando, setGerando] = useState(false);

  async function carregar() {
    const dados = await api(`/api/reunioes/${id}`);
    setR(dados);
    setFatos((dados.fatos_peticao || []).join("\n"));
    setPendencias((dados.pendencias || []).join("\n"));
  }

  useEffect(() => {
    carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function salvar() {
    setMsg(null);
    await api(`/api/reunioes/${id}`, {
      method: "PATCH",
      body: {
        fatos_peticao: fatos.split("\n").map((s) => s.trim()).filter(Boolean),
        pendencias: pendencias.split("\n").map((s) => s.trim()).filter(Boolean),
      },
    });
    setMsg("✓ Fatos atualizados.");
    carregar();
  }

  async function gerarPeca() {
    if (!r.processo_id) return setMsg("Vincule um processo à reunião para gerar a peça.");
    setGerando(true);
    try {
      const doc = await api("/api/documentos/gerar", {
        method: "POST",
        body: { processo_id: r.processo_id, reuniao_id: Number(id), tipo: "peticao_inicial" },
      });
      navigate(`/pecas?doc=${doc.id}`);
    } catch (e) {
      setMsg(`Erro: ${e.message}`);
    } finally {
      setGerando(false);
    }
  }

  if (!r) return <p className="text-gray-400">Carregando...</p>;

  return (
    <div>
      <Link to="/reunioes" className="text-sm text-claudio hover:underline">← Voltar</Link>
      <div className="flex items-center justify-between mt-2 mb-4">
        <h1 className="text-2xl font-bold text-gray-800">Reunião #{r.id}</h1>
        <span className="text-sm text-gray-500">Status: {r.status}</span>
      </div>

      <audio controls src={authedUrl(`/api/reunioes/${id}/audio`)} className="w-full mb-6" />

      {msg && <p className="mb-4 text-sm text-claudio bg-blue-50 rounded-lg px-3 py-2">{msg}</p>}

      <div className="grid md:grid-cols-2 gap-6">
        {/* Transcrição */}
        <div className="bg-white rounded-xl border p-5">
          <h2 className="font-semibold text-gray-700 mb-3">Transcrição</h2>
          {r.status !== "concluido" ? (
            <p className="text-gray-400 text-sm">
              {r.status === "erro" ? "Falha na transcrição." : "Transcrição em andamento..."}
            </p>
          ) : (
            <p className="text-sm text-gray-700 whitespace-pre-wrap max-h-96 overflow-auto">
              {r.transcricao || "—"}
            </p>
          )}
          {r.resumo && (
            <>
              <h3 className="font-medium text-gray-600 mt-4 mb-1 text-sm">Resumo</h3>
              <p className="text-sm text-gray-600">{r.resumo}</p>
            </>
          )}
        </div>

        {/* Fatos editáveis */}
        <div className="bg-white rounded-xl border p-5">
          <h2 className="font-semibold text-gray-700 mb-2">Fatos para petição (editável)</h2>
          <p className="text-xs text-gray-400 mb-2">Um fato por linha.</p>
          <textarea
            value={fatos}
            onChange={(e) => setFatos(e.target.value)}
            rows={8}
            className="w-full border rounded-lg px-3 py-2 text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-claudio-light"
          />
          <h3 className="font-medium text-gray-600 mb-1 text-sm">Pendências</h3>
          <textarea
            value={pendencias}
            onChange={(e) => setPendencias(e.target.value)}
            rows={4}
            className="w-full border rounded-lg px-3 py-2 text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-claudio-light"
          />
          <div className="flex gap-3">
            <button onClick={salvar} className="bg-claudio text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-claudio-light">
              Salvar fatos
            </button>
            <button
              onClick={gerarPeca}
              disabled={gerando}
              className="border border-claudio text-claudio rounded-lg px-4 py-2 text-sm font-medium hover:bg-claudio hover:text-white transition disabled:opacity-60"
            >
              {gerando ? "Gerando..." : "✍️ Gerar petição"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
