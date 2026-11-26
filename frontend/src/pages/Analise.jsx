import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../stores/auth";

export default function Analise() {
  const user = useAuth((s) => s.user);
  const ehSocio = user?.perfil === "socio";

  const [advogados, setAdvogados] = useState([]);
  const [advogadoId, setAdvogadoId] = useState(ehSocio ? "" : String(user?.id || ""));
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [processando, setProcessando] = useState(false);
  const [msg, setMsg] = useState(null);
  const [erro, setErro] = useState(null);

  // Sócio escolhe de quem é a análise; advogado vê a própria.
  useEffect(() => {
    if (!ehSocio) return;
    api("/api/usuarios")
      .then((us) => {
        const advs = us.filter((u) => ["advogado", "socio"].includes(u.perfil) && u.ativo !== false);
        setAdvogados(advs);
        if (advs.length && !advogadoId) setAdvogadoId(String(advs.find((a) => a.perfil === "advogado")?.id || advs[0].id));
      })
      .catch(() => {});
  }, [ehSocio]);

  async function carregar() {
    if (!advogadoId) return;
    setCarregando(true);
    setErro(null);
    setMsg(null);
    try {
      const q = ehSocio ? `?advogado_id=${advogadoId}` : "";
      setDados(await api(`/api/analise/dia${q}`));
    } catch (e) {
      setErro(e.message);
      setDados(null);
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    if (advogadoId) carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [advogadoId]);

  async function processar() {
    setProcessando(true);
    setMsg(null);
    try {
      const q = ehSocio ? `?advogado_id=${advogadoId}` : "";
      const r = await api(`/api/analise/dia/processar${q}`, { method: "POST" });
      const n = (r.itens || []).filter((i) => i.mensagem_pendente_id).length;
      setMsg(`✓ ${n} mensagem(ns) enviada(s) para a fila de aprovação (aba WhatsApp). Análise marcada como vista.`);
      await carregar();
    } catch (e) {
      setMsg(`Erro: ${e.message}`);
    } finally {
      setProcessando(false);
    }
  }

  const itens = dados?.itens || [];

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-2xl font-bold text-gray-800">Análise do dia</h1>
        <button
          onClick={processar}
          disabled={processando || carregando || itens.length === 0}
          className="bg-claudio text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-claudio-light disabled:opacity-50"
        >
          {processando ? "Processando..." : "Gerar mensagens p/ aprovação"}
        </button>
      </div>
      <p className="text-sm text-gray-500 mb-4">
        O Cláudio varre os processos ativos, aponta <strong>o que mudou desde a última análise</strong>,
        monta um <strong>plano de ação</strong> e rascunha a mensagem do cliente — que vai para a
        <strong> fila de aprovação</strong> (nada é enviado sem o seu aval).
      </p>

      {/* Seletor de advogado (sócio) */}
      {ehSocio && (
        <div className="mb-4 flex items-center gap-2">
          <label className="text-sm text-gray-500">Advogado:</label>
          <select
            value={advogadoId}
            onChange={(e) => setAdvogadoId(e.target.value)}
            className="border rounded-lg px-3 py-1.5 text-sm"
          >
            {advogados.map((a) => (
              <option key={a.id} value={a.id}>{a.nome}</option>
            ))}
          </select>
        </div>
      )}

      {/* JusBrasil — busca aprofundada (varredura no navegador do advogado) */}
      <div className="mb-5 rounded-xl border border-amber-300 bg-amber-50 p-4">
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => window.open("https://www.jusbrasil.com.br/", "_blank", "noopener,noreferrer")}
            className="bg-amber-600 text-white rounded-lg px-4 py-2 text-sm font-semibold hover:bg-amber-700"
          >
            🔎 Buscar no JusBrasil
          </button>
          <button
            onClick={carregar}
            disabled={carregando}
            className="border border-amber-400 text-amber-800 rounded-lg px-4 py-2 text-sm font-medium hover:bg-amber-100 disabled:opacity-50"
          >
            ↻ Atualizar análise
          </button>
          <span className="text-xs text-amber-700">Login manual — sua senha nunca passa pelo sistema.</span>
        </div>
        <ol className="mt-3 text-sm text-amber-800 list-decimal list-inside space-y-0.5">
          <li>Clique em <strong>Buscar no JusBrasil</strong> e faça seu login normalmente.</li>
          <li>Abra <strong>"Meus processos"</strong> e, no painel do Cláudio (canto inferior da página), clique em <strong>"Varrer meus processos"</strong>.</li>
          <li>Volte aqui e clique em <strong>"Atualizar análise"</strong> — o que foi encontrado entra automaticamente nos <strong>prazos, processos, dados do cliente e no rascunho de WhatsApp</strong> (só adiciona o que é novo; nada existente é alterado).</li>
        </ol>
        <p className="mt-2 text-xs text-amber-600">1ª vez: é preciso instalar o script de varredura no navegador (Tampermonkey). Peça o passo a passo ao Cláudio.</p>
      </div>

      {msg && <p className="mb-4 text-sm text-claudio bg-blue-50 rounded-lg px-3 py-2">{msg}</p>}
      {erro && <p className="mb-4 text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{erro}</p>}

      {carregando ? (
        <div className="bg-white rounded-xl border p-8 text-center">
          <p className="text-gray-500 text-sm">Analisando os processos com IA…</p>
          <p className="text-gray-400 text-xs mt-1">Na primeira vez pode levar até ~1 min (a IA lê cada processo).</p>
        </div>
      ) : itens.length === 0 ? (
        <div className="bg-white rounded-xl border p-8 text-center text-gray-400">
          Tudo em dia — nenhuma novidade nova desde a última análise.
        </div>
      ) : (
        <div className="space-y-4">
          {itens.map((it) => (
            <div key={it.processo_id} className="bg-white rounded-xl border p-5">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <Link to={`/processos/${it.processo_id}`} className="text-claudio font-semibold hover:underline">
                    {it.numero}
                  </Link>
                  {it.cliente && <span className="text-gray-500 text-sm"> · {it.cliente}</span>}
                </div>
                <span className="text-[10px] uppercase tracking-wide px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">
                  IA: {it.fonte_ia === "llm" ? "assistente" : "regras"}
                </span>
              </div>

              {/* Resumo */}
              <p className="text-sm text-gray-800 mb-3"><strong>Resumo:</strong> {it.resumo}</p>

              <div className="grid md:grid-cols-2 gap-4">
                {/* Novidades */}
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase mb-1">Novidades</p>
                  <ul className="space-y-1">
                    {it.novidades.map((n, i) => (
                      <li key={i} className="text-sm text-gray-700">
                        <span className="text-gray-400">{n.data}</span> — {n.descricao}
                        <span className="text-[10px] text-gray-400"> ({n.fonte})</span>
                      </li>
                    ))}
                  </ul>
                  {it.prazos_pendentes.length > 0 && (
                    <div className="mt-2">
                      <p className="text-xs font-semibold text-gray-500 uppercase mb-1">Prazos pendentes</p>
                      <ul className="space-y-1">
                        {it.prazos_pendentes.map((p, i) => (
                          <li key={i} className="text-sm text-red-600">⏰ {p.descricao} — {p.data_limite}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                {/* Plano de ação */}
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase mb-1">Plano de ação</p>
                  <ol className="space-y-1 list-decimal list-inside">
                    {it.plano_acao.map((p, i) => (
                      <li key={i} className="text-sm text-gray-700">{p}</li>
                    ))}
                  </ol>
                </div>
              </div>

              {/* Mensagem rascunhada */}
              <div className="mt-4 rounded-lg bg-gray-50 border p-3">
                <p className="text-xs font-semibold text-gray-500 uppercase mb-1">
                  Rascunho da mensagem ao cliente {it.mensagem_pendente_id ? "· na fila de aprovação" : ""}
                </p>
                <p className="text-sm text-gray-800">{it.mensagem_cliente}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
