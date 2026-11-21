import { useEffect, useState } from "react";
import { api, getSensitiveToken } from "../lib/api";
import SensitiveGate from "../components/SensitiveGate";

const fmt = (v) => (v ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

function Barra({ label, valor, max, sufixo = "%" }) {
  const pct = max ? Math.round((valor / max) * 100) : 0;
  return (
    <div className="mb-2">
      <div className="flex justify-between text-xs text-gray-600 mb-0.5">
        <span className="truncate pr-2">{label}</span>
        <span className="font-medium">{valor}{sufixo}</span>
      </div>
      <div className="h-2 bg-gray-100 rounded">
        <div className="h-2 bg-claudio rounded" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function Conteudo() {
  const sens = () => getSensitiveToken();
  const [d, setD] = useState(null);
  const [juri, setJuri] = useState([]);
  const [dim, setDim] = useState("tese");
  const [advs, setAdvs] = useState([]);
  const [erro, setErro] = useState(null);

  useEffect(() => {
    api("/api/dono/dashboard", { sensitive: sens() }).then(setD).catch((e) => setErro(e.message));
    api("/api/dono/advogados", { sensitive: sens() }).then(setAdvs).catch(() => {});
  }, []);

  useEffect(() => {
    api(`/api/dono/jurimetria?dimensao=${dim}`, { sensitive: sens() }).then(setJuri).catch(() => {});
  }, [dim]);

  if (erro) return <p className="text-red-600">{erro}</p>;
  if (!d) return <p className="text-gray-400">Carregando...</p>;

  const fat = d.faturamento;

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-4">Dashboard do Dono</h1>

      {/* Faturamento + caixa */}
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
        <div className="bg-green-600 text-white rounded-xl p-4">
          <p className="text-xs opacity-80">Saldo do mês</p>
          <p className="text-xl font-bold">{fmt(d.caixa.saldo_mes)}</p>
        </div>
        <div className="bg-yellow-500 text-white rounded-xl p-4">
          <p className="text-xs opacity-80">Projeção 30d</p>
          <p className="text-xl font-bold">{fmt(d.caixa.projecao_30)}</p>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Jurimetria */}
        <div className="bg-white rounded-xl border p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-gray-700">Taxa de êxito</h2>
            <select value={dim} onChange={(e) => setDim(e.target.value)} className="border rounded-lg px-2 py-1 text-sm">
              <option value="tese">por tese</option>
              <option value="juiz">por juiz</option>
              <option value="vara">por vara</option>
              <option value="tipo">por tipo</option>
            </select>
          </div>
          {juri.length === 0 ? (
            <p className="text-gray-400 text-sm">Sem dados de jurimetria ainda (registre resultados dos casos encerrados).</p>
          ) : (
            juri.slice(0, 8).map((j) => (
              <Barra key={j.chave} label={`${j.chave} (${j.total})`} valor={j.taxa_exito} max={100} />
            ))
          )}
        </div>

        {/* Processos + críticos */}
        <div className="bg-white rounded-xl border p-5">
          <h2 className="font-semibold text-gray-700 mb-3">Processos</h2>
          <p className="text-3xl font-bold text-claudio">{d.processos.ativos}<span className="text-sm text-gray-400 font-normal"> ativos</span></p>
          <div className="mt-3 space-y-1">
            {d.processos.por_status.map((s) => (
              <div key={s.status} className="flex justify-between text-sm">
                <span className="capitalize text-gray-600">{s.status}</span>
                <span className="font-medium">{s.total}</span>
              </div>
            ))}
          </div>
          <div className="mt-4 pt-3 border-t grid grid-cols-2 gap-2 text-sm">
            <div className="text-red-600">⏰ {d.criticos.prazos_urgentes} prazos urgentes</div>
            <div className="text-yellow-600">💸 {d.criticos.inadimplentes} inadimplentes</div>
          </div>
        </div>
      </div>

      {/* Comparativo entre advogados */}
      <div className="bg-white rounded-xl border p-5 mt-6">
        <h2 className="font-semibold text-gray-700 mb-3">Desempenho por advogado</h2>
        <table className="w-full text-sm">
          <thead className="text-gray-500 text-left">
            <tr><th className="py-1">Advogado</th><th>Ativos</th><th>Encerrados</th><th>Êxito</th><th>Prazos ✓/✗</th><th>Peças</th></tr>
          </thead>
          <tbody className="divide-y">
            {advs.map((a) => (
              <tr key={a.advogado_id}>
                <td className="py-1.5 font-medium">{a.nome}</td>
                <td>{a.ativos}</td>
                <td>{a.encerrados}</td>
                <td>{a.taxa_exito != null ? `${a.taxa_exito}%` : "—"}</td>
                <td>{a.prazos_cumpridos}/{a.prazos_perdidos}</td>
                <td>{a.pecas_produzidas}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
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
