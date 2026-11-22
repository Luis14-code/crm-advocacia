import { useEffect, useState } from "react";
import { api, getSensitiveToken } from "../lib/api";
import SensitiveGate from "../components/SensitiveGate";
import { BarMensal, Donut } from "../components/Charts";
import { ConfiguracoesConteudo } from "./Configuracoes";

const fmt = (v) => (v ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

function Barra({ label, valor, max = 100, sufixo = "%" }) {
  const pct = max ? Math.min(100, Math.round((valor / max) * 100)) : 0;
  return (
    <div className="mb-2">
      <div className="flex justify-between text-xs text-gray-600 mb-0.5">
        <span className="truncate pr-2">{label}</span><span className="font-medium">{valor}{sufixo}</span>
      </div>
      <div className="h-2 bg-gray-100 rounded"><div className="h-2 bg-claudio rounded" style={{ width: `${pct}%` }} /></div>
    </div>
  );
}

function VisaoGeral({ sens }) {
  const [d, setD] = useState(null);
  const [graf, setGraf] = useState(null);
  const [juri, setJuri] = useState([]);
  const [dim, setDim] = useState("tese");
  const [advs, setAdvs] = useState([]);

  useEffect(() => {
    const s = { sensitive: sens() };
    api("/api/dono/dashboard", s).then(setD).catch(() => {});
    api("/api/financeiro/graficos", s).then(setGraf).catch(() => {});
    api("/api/dono/advogados", s).then(setAdvs).catch(() => {});
  }, [sens]);

  useEffect(() => {
    api(`/api/dono/jurimetria?dimensao=${dim}`, { sensitive: sens() }).then(setJuri).catch(() => {});
  }, [dim, sens]);

  if (!d) return <p className="text-gray-400">Carregando...</p>;
  const fat = d.faturamento;
  const boletosDonut = graf ? [
    { categoria: "Pagos", valor: graf.boletos.pago.valor },
    { categoria: "Pendentes", valor: graf.boletos.pendente.valor },
    { categoria: "Vencidos", valor: graf.boletos.vencido.valor },
  ].filter((x) => x.valor > 0) : [];

  return (
    <>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-claudio text-white rounded-xl p-4">
          <p className="text-xs opacity-80">Faturamento (mês)</p>
          <p className="text-xl font-bold">{fmt(fat.mes_atual)}</p>
          {fat.variacao != null && <p className="text-xs opacity-80">{fat.variacao >= 0 ? "▲" : "▼"} {Math.abs(fat.variacao)}% vs anterior</p>}
        </div>
        <div className="bg-claudio-light text-white rounded-xl p-4">
          <p className="text-xs opacity-80">Meta</p>
          <p className="text-xl font-bold">{fat.meta ? fmt(fat.meta) : "—"}</p>
          {fat.percentual_meta != null && <p className="text-xs opacity-80">{fat.percentual_meta}% atingido</p>}
        </div>
        <div className="bg-green-600 text-white rounded-xl p-4"><p className="text-xs opacity-80">Saldo do mês</p><p className="text-xl font-bold">{fmt(d.caixa.saldo_mes)}</p></div>
        <div className="bg-yellow-500 text-white rounded-xl p-4"><p className="text-xs opacity-80">Projeção 30d</p><p className="text-xl font-bold">{fmt(d.caixa.projecao_30)}</p></div>
      </div>

      {/* Gráficos */}
      {graf && (
        <div className="grid md:grid-cols-2 gap-6 mb-6">
          <div className="bg-white rounded-xl border p-5">
            <h2 className="font-semibold text-gray-700 mb-3">Faturamento (6 meses)</h2>
            <BarMensal data={graf.faturamento_mensal} />
          </div>
          <div className="bg-white rounded-xl border p-5">
            <h2 className="font-semibold text-gray-700 mb-3">Boletos pagos × pendentes × vencidos</h2>
            <Donut data={boletosDonut} />
          </div>
          <div className="bg-white rounded-xl border p-5">
            <h2 className="font-semibold text-gray-700 mb-3">Receitas por categoria (mês)</h2>
            <Donut data={graf.receitas_categoria} />
          </div>
          <div className="bg-white rounded-xl border p-5">
            <h2 className="font-semibold text-gray-700 mb-3">Despesas por categoria (mês)</h2>
            <Donut data={graf.despesas_categoria} />
          </div>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-6 mb-6">
        <div className="bg-white rounded-xl border p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-gray-700">Taxa de êxito</h2>
            <select value={dim} onChange={(e) => setDim(e.target.value)} className="border rounded-lg px-2 py-1 text-sm">
              <option value="tese">por tese</option><option value="juiz">por juiz</option><option value="vara">por vara</option><option value="tipo">por tipo</option>
            </select>
          </div>
          {juri.length === 0 ? <p className="text-gray-400 text-sm">Sem dados ainda.</p>
            : juri.slice(0, 8).map((j) => <Barra key={j.chave} label={`${j.chave} (${j.total})`} valor={j.taxa_exito} />)}
        </div>
        <div className="bg-white rounded-xl border p-5">
          <h2 className="font-semibold text-gray-700 mb-3">Processos</h2>
          <p className="text-3xl font-bold text-claudio">{d.processos.ativos}<span className="text-sm text-gray-400 font-normal"> ativos</span></p>
          <div className="mt-3 space-y-1">
            {d.processos.por_status.map((s) => (
              <div key={s.status} className="flex justify-between text-sm"><span className="capitalize text-gray-600">{s.status}</span><span className="font-medium">{s.total}</span></div>
            ))}
          </div>
          <div className="mt-4 pt-3 border-t grid grid-cols-2 gap-2 text-sm">
            <div className="text-red-600">⏰ {d.criticos.prazos_urgentes} prazos urgentes</div>
            <div className="text-yellow-600">💸 {d.criticos.inadimplentes} inadimplentes</div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl border p-5">
        <h2 className="font-semibold text-gray-700 mb-3">Desempenho por advogado</h2>
        <table className="w-full text-sm">
          <thead className="text-gray-500 text-left"><tr><th className="py-1">Advogado</th><th>Ativos</th><th>Encerrados</th><th>Êxito</th><th>Prazos ✓/✗</th><th>Peças</th></tr></thead>
          <tbody className="divide-y">
            {advs.map((a) => (
              <tr key={a.advogado_id}>
                <td className="py-1.5 font-medium">{a.nome}</td><td>{a.ativos}</td><td>{a.encerrados}</td>
                <td>{a.taxa_exito != null ? `${a.taxa_exito}%` : "—"}</td><td>{a.prazos_cumpridos}/{a.prazos_perdidos}</td><td>{a.pecas_produzidas}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function Metas({ sens }) {
  const [meta, setMeta] = useState(null);
  const [valor, setValor] = useState("");
  const [fatMes, setFatMes] = useState(0);
  const [msg, setMsg] = useState(null);

  useEffect(() => {
    const s = { sensitive: sens() };
    api("/api/dono/meta", s).then((m) => setMeta(m.meta_faturamento_mensal)).catch(() => {});
    api("/api/financeiro/dashboard", s).then((d) => setFatMes(d.faturado_mes)).catch(() => {});
  }, [sens]);

  async function salvar(e) {
    e.preventDefault();
    const m = await api("/api/dono/meta", { method: "PUT", sensitive: sens(), body: { valor: Number(valor) } });
    setMeta(m.meta_faturamento_mensal);
    setValor("");
    setMsg("✓ Meta atualizada.");
  }
  const pct = meta ? Math.round((fatMes / meta) * 100) : 0;

  return (
    <div className="max-w-xl">
      <div className="bg-white rounded-xl border p-5 mb-4">
        <h2 className="font-semibold text-gray-700 mb-3">Meta de faturamento mensal</h2>
        {meta != null && (
          <>
            <div className="flex justify-between text-sm mb-1">
              <span>{fmt(fatMes)} de {fmt(meta)}</span><span className="font-medium">{meta ? `${pct}%` : "sem meta"}</span>
            </div>
            <div className="h-3 bg-gray-100 rounded-full mb-4">
              <div className={`h-3 rounded-full ${pct >= 100 ? "bg-green-500" : "bg-claudio"}`} style={{ width: `${Math.min(100, pct)}%` }} />
            </div>
          </>
        )}
        <form onSubmit={salvar} className="flex gap-2">
          <input type="number" step="0.01" value={valor} onChange={(e) => setValor(e.target.value)} placeholder="Nova meta (R$)" className="flex-1 border rounded-lg px-3 py-2 text-sm" />
          <button type="submit" className="bg-claudio text-white rounded-lg px-4 py-2 text-sm font-medium">Salvar</button>
        </form>
        {msg && <p className="text-sm text-claudio mt-2">{msg}</p>}
      </div>
    </div>
  );
}

function Colaboradores({ sens }) {
  const [lista, setLista] = useState([]);
  const [sel, setSel] = useState(null);
  const [det, setDet] = useState(null);

  useEffect(() => {
    api("/api/dono/advogados", { sensitive: sens() }).then(setLista).catch(() => {});
  }, [sens]);

  async function abrir(id) {
    setSel(id);
    setDet(null);
    setDet(await api(`/api/dono/advogado/${id}`, { sensitive: sens() }).catch(() => null));
  }

  const Kpi = ({ label, valor, cor = "text-gray-800" }) => (
    <div className="bg-gray-50 rounded-lg p-3">
      <p className="text-xs text-gray-500">{label}</p>
      <p className={`text-xl font-bold ${cor}`}>{valor}</p>
    </div>
  );

  return (
    <div className="grid md:grid-cols-3 gap-6">
      {/* Lista de colaboradores */}
      <div className="bg-white rounded-xl border p-3 h-fit">
        <h2 className="font-semibold text-gray-700 text-sm px-2 mb-2">Colaboradores</h2>
        <ul className="space-y-1">
          {lista.map((a) => (
            <li key={a.advogado_id}>
              <button onClick={() => abrir(a.advogado_id)}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm ${sel === a.advogado_id ? "bg-claudio text-white" : "hover:bg-gray-100"}`}>
                <span className="block font-medium">{a.nome}</span>
                <span className={`text-xs ${sel === a.advogado_id ? "text-white/70" : "text-gray-400"}`}>
                  {a.ativos} ativos · êxito {a.taxa_exito != null ? `${a.taxa_exito}%` : "—"}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </div>

      {/* Detalhe do colaborador */}
      <div className="md:col-span-2">
        {!det ? (
          <div className="bg-white rounded-xl border p-8 text-center text-gray-400">
            Selecione um colaborador para ver o desempenho.
          </div>
        ) : (
          <div className="bg-white rounded-xl border p-5">
            <h2 className="text-lg font-bold text-gray-800 mb-1">{det.nome}</h2>
            <p className="text-xs text-gray-400 mb-4 capitalize">
              {det.perfil} · última atividade: {det.ultima_atividade ? new Date(det.ultima_atividade).toLocaleString("pt-BR") : "—"}
            </p>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
              <Kpi label="Processos ativos" valor={det.ativos} />
              <Kpi label="Encerrados" valor={det.encerrados} />
              <Kpi label="Taxa de êxito" valor={det.taxa_exito != null ? `${det.taxa_exito}%` : "—"} cor="text-claudio" />
              <Kpi label="Peças (total)" valor={det.pecas_produzidas} />
              <Kpi label="Prazos atrasados" valor={det.prazos_atrasados} cor={det.prazos_atrasados > 0 ? "text-red-600" : "text-green-700"} />
              <Kpi label="Prazos pendentes" valor={det.prazos_pendentes} />
              <Kpi label="Cumpridos / perdidos" valor={`${det.prazos_cumpridos}/${det.prazos_perdidos}`} />
              <Kpi label="Dias ativos (mês)" valor={det.dias_ativos_mes} />
            </div>

            <div className="grid md:grid-cols-2 gap-5">
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Nesta semana</h3>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between"><span className="text-gray-500">Prazos cumpridos</span><span className="font-medium">{det.prazos_cumpridos_semana}</span></div>
                  <div className="flex justify-between"><span className="text-gray-500">Peças produzidas</span><span className="font-medium">{det.pecas_semana}</span></div>
                  <div className="flex justify-between"><span className="text-gray-500">Ações no sistema</span><span className="font-medium">{det.atividade_semana}</span></div>
                </div>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Neste mês</h3>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between"><span className="text-gray-500">Prazos cumpridos</span><span className="font-medium">{det.prazos_cumpridos_mes}</span></div>
                  <div className="flex justify-between"><span className="text-gray-500">Peças produzidas</span><span className="font-medium">{det.pecas_mes}</span></div>
                  <div className="flex justify-between"><span className="text-gray-500">Ações no sistema</span><span className="font-medium">{det.atividade_mes}</span></div>
                </div>
              </div>
            </div>

            {det.resultados && Object.keys(det.resultados).length > 0 && (
              <div className="mt-5">
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Resultados (retorno)</h3>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(det.resultados).map(([r, n]) => (
                    <span key={r} className="text-xs bg-gray-100 rounded-full px-3 py-1 capitalize">{r}: <strong>{n}</strong></span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function Conteudo() {
  const sens = () => getSensitiveToken();
  const [aba, setAba] = useState("visao");
  const ABAS = [["visao", "Visão geral"], ["colaboradores", "Colaboradores"], ["metas", "Metas"], ["integracoes", "Integrações / API"]];
  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-4">👑 Dashboard do Dono</h1>
      <div className="flex gap-2 mb-5 flex-wrap">
        {ABAS.map(([k, label]) => (
          <button key={k} onClick={() => setAba(k)}
            className={`px-4 py-1.5 rounded-lg text-sm ${aba === k ? "bg-claudio text-white" : "bg-white border"}`}>{label}</button>
        ))}
      </div>
      {aba === "visao" && <VisaoGeral sens={sens} />}
      {aba === "colaboradores" && <Colaboradores sens={sens} />}
      {aba === "metas" && <Metas sens={sens} />}
      {aba === "integracoes" && <ConfiguracoesConteudo />}
    </div>
  );
}

export default function Dono() {
  return (
    <SensitiveGate titulo="Dashboard do Dono">
      <Conteudo />
    </SensitiveGate>
  );
}
