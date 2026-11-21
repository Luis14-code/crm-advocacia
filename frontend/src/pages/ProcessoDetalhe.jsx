import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../lib/api";

export default function ProcessoDetalhe() {
  const { id } = useParams();
  const [processo, setProcesso] = useState(null);
  const [movs, setMovs] = useState([]);
  const [prazos, setPrazos] = useState([]);
  const [sincronizando, setSincronizando] = useState(false);
  const [msg, setMsg] = useState(null);
  const [erro, setErro] = useState(null);

  async function carregar() {
    try {
      const [p, m, pr] = await Promise.all([
        api(`/api/processos/${id}`),
        api(`/api/processos/${id}/movimentacoes`),
        api(`/api/prazos`),
      ]);
      setProcesso(p);
      setMovs(m);
      setPrazos(pr.filter((x) => x.processo_id === Number(id)));
    } catch (e) {
      setErro(e.message);
    }
  }

  useEffect(() => {
    carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function sincronizar() {
    setSincronizando(true);
    setMsg(null);
    try {
      const r = await api(`/api/processos/${id}/sync`, { method: "POST" });
      setMsg(
        r.erro
          ? `Sincronização parcial: ${r.erro}`
          : `✓ ${r.novas} nova(s) movimentação(ões), ${r.prazos} prazo(s) detectado(s) (fonte: ${r.fonte})`
      );
      await carregar();
    } catch (e) {
      setMsg(`Erro: ${e.message}`);
    } finally {
      setSincronizando(false);
    }
  }

  if (erro) return <p className="text-red-600">{erro}</p>;
  if (!processo) return <p className="text-gray-400">Carregando...</p>;

  return (
    <div>
      <Link to="/processos" className="text-sm text-claudio hover:underline">
        ← Voltar
      </Link>

      <div className="flex items-start justify-between mt-2 mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">{processo.numero}</h1>
          <p className="text-gray-500">
            {processo.tipo}
            {processo.subtipo ? ` / ${processo.subtipo}` : ""} · {processo.vara || "vara não informada"}
          </p>
          {processo.tese_principal && (
            <p className="text-sm text-gray-600 mt-1">
              <span className="font-medium">Tese:</span> {processo.tese_principal}
            </p>
          )}
        </div>
        <button
          onClick={sincronizar}
          disabled={sincronizando}
          className="bg-claudio text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-claudio-light disabled:opacity-60"
        >
          {sincronizando ? "Sincronizando..." : "🔄 Sincronizar (DataJud)"}
        </button>
      </div>

      {msg && <p className="mb-4 text-sm text-claudio bg-blue-50 rounded-lg px-3 py-2">{msg}</p>}

      <div className="grid md:grid-cols-3 gap-6">
        {/* Timeline */}
        <div className="md:col-span-2 bg-white rounded-xl border p-5">
          <h2 className="font-semibold text-gray-700 mb-4">Timeline de movimentações</h2>
          {movs.length === 0 ? (
            <p className="text-gray-400 text-sm">Nenhuma movimentação registrada.</p>
          ) : (
            <ol className="relative border-l-2 border-claudio/20 ml-2">
              {movs.map((m) => (
                <li key={m.id} className="mb-5 ml-4">
                  <span className="absolute -left-[7px] w-3 h-3 bg-claudio rounded-full mt-1.5" />
                  <time className="text-xs text-gray-400">
                    {new Date(m.data).toLocaleDateString("pt-BR")} · {m.fonte}
                  </time>
                  <p className="text-sm text-gray-800">{m.descricao}</p>
                </li>
              ))}
            </ol>
          )}
        </div>

        {/* Prazos */}
        <div className="bg-white rounded-xl border p-5">
          <h2 className="font-semibold text-gray-700 mb-4">Prazos</h2>
          {prazos.length === 0 ? (
            <p className="text-gray-400 text-sm">Sem prazos.</p>
          ) : (
            <ul className="space-y-2">
              {prazos.map((p) => (
                <li key={p.id} className="text-sm border-l-4 border-claudio-accent pl-2">
                  <p className="font-medium">
                    {new Date(p.data_limite_util).toLocaleDateString("pt-BR")}
                  </p>
                  <p className="text-gray-500 text-xs">{p.descricao}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
