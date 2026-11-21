import { useEffect, useState } from "react";
import { api, getSensitiveToken } from "../lib/api";
import SensitiveGate from "../components/SensitiveGate";

const fmt = (v) =>
  (v ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

function Conteudo() {
  const sens = () => getSensitiveToken();
  const [caixa, setCaixa] = useState(null);
  const [transacoes, setTransacoes] = useState([]);
  const [aba, setAba] = useState("resumo");

  // Simulador
  const [processos, setProcessos] = useState([]);
  const [procId, setProcId] = useState("");
  const [valor, setValor] = useState("");
  const [parcelas, setParcelas] = useState(1);
  const [sim, setSim] = useState(null);
  const [erro, setErro] = useState(null);

  const hoje = new Date();
  const ini = new Date(hoje.getTime() - 30 * 86400000).toISOString().slice(0, 10);
  const fim = hoje.toISOString().slice(0, 10);

  async function carregar() {
    try {
      setCaixa(await api(`/api/financeiro/fluxo-caixa?inicio=${ini}&fim=${fim}`, { sensitive: sens() }));
      setTransacoes(await api(`/api/financeiro/transacoes`, { sensitive: sens() }));
    } catch (e) {
      setErro(e.message);
    }
  }

  useEffect(() => {
    carregar();
    api("/api/processos").then(setProcessos).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function simular(e) {
    e.preventDefault();
    setErro(null);
    try {
      const r = await api("/api/financeiro/simular-acordo", {
        method: "POST",
        sensitive: sens(),
        body: { processo_id: Number(procId), valor_bruto: Number(valor), parcelas: Number(parcelas) },
      });
      setSim(r);
    } catch (e) {
      setErro(e.message);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-4">Financeiro</h1>
      {erro && <p className="text-red-600 mb-3 text-sm">{erro}</p>}

      {/* KPIs */}
      {caixa && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-green-600 text-white rounded-xl p-4"><p className="text-xs opacity-80">Entradas (30d)</p><p className="text-xl font-bold">{fmt(caixa.entradas)}</p></div>
          <div className="bg-red-500 text-white rounded-xl p-4"><p className="text-xs opacity-80">Saídas (30d)</p><p className="text-xl font-bold">{fmt(caixa.saidas)}</p></div>
          <div className="bg-claudio text-white rounded-xl p-4"><p className="text-xs opacity-80">A receber</p><p className="text-xl font-bold">{fmt(caixa.a_receber)}</p></div>
          <div className="bg-yellow-500 text-white rounded-xl p-4"><p className="text-xs opacity-80">Inadimplência</p><p className="text-xl font-bold">{fmt(caixa.inadimplencia)}</p></div>
        </div>
      )}

      <div className="flex gap-2 mb-4">
        {["resumo", "transacoes", "simulador"].map((a) => (
          <button key={a} onClick={() => setAba(a)}
            className={`px-4 py-1.5 rounded-lg text-sm capitalize ${aba === a ? "bg-claudio text-white" : "bg-white border"}`}>
            {a === "transacoes" ? "Transações" : a}
          </button>
        ))}
      </div>

      {aba === "transacoes" && (
        <div className="bg-white rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-left">
              <tr><th className="px-4 py-2">Vencimento</th><th className="px-4 py-2">Categoria</th><th className="px-4 py-2">Descrição</th><th className="px-4 py-2">Valor</th><th className="px-4 py-2">Status</th></tr>
            </thead>
            <tbody className="divide-y">
              {transacoes.length === 0 ? (
                <tr><td colSpan={5} className="px-4 py-6 text-center text-gray-400">Sem transações.</td></tr>
              ) : transacoes.map((t) => (
                <tr key={t.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2">{t.data_vencimento ? new Date(t.data_vencimento + "T00:00:00").toLocaleDateString("pt-BR") : "—"}</td>
                  <td className="px-4 py-2">{t.categoria || "—"}</td>
                  <td className="px-4 py-2 text-gray-600">{t.descricao || "—"}</td>
                  <td className={`px-4 py-2 font-medium ${t.tipo === "entrada" ? "text-green-700" : "text-red-600"}`}>{fmt(Number(t.valor))}</td>
                  <td className="px-4 py-2">{t.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {aba === "simulador" && (
        <div className="bg-white rounded-xl border p-5 max-w-2xl">
          <h2 className="font-semibold text-gray-700 mb-3">Simulador de acordo</h2>
          <form onSubmit={simular} className="grid md:grid-cols-3 gap-3 mb-4">
            <select value={procId} onChange={(e) => setProcId(e.target.value)} required className="border rounded-lg px-3 py-2 text-sm">
              <option value="">Processo</option>
              {processos.map((p) => <option key={p.id} value={p.id}>{p.numero}</option>)}
            </select>
            <input type="number" step="0.01" value={valor} onChange={(e) => setValor(e.target.value)} required placeholder="Valor bruto" className="border rounded-lg px-3 py-2 text-sm" />
            <input type="number" min="1" value={parcelas} onChange={(e) => setParcelas(e.target.value)} placeholder="Parcelas" className="border rounded-lg px-3 py-2 text-sm" />
            <button type="submit" className="bg-claudio text-white rounded-lg px-4 py-2 text-sm font-medium md:col-span-3">Simular</button>
          </form>
          {sim && (
            <div className="text-sm bg-gray-50 rounded-lg p-4 font-mono whitespace-pre-wrap">
              {`Valor bruto:            ${fmt(sim.valor_bruto)}
(-) Honorários ${sim.deducoes.honorarios_contratuais.percentual}%:   ${fmt(sim.deducoes.honorarios_contratuais.valor)}
(-) Custas:             ${fmt(sim.deducoes.custas_processuais)}
(-) Despesas:           ${fmt(sim.deducoes.despesas)}
(-) ISS:                ${fmt(sim.deducoes.impostos.valor)}
────────────────────────────
Líquido do cliente:     ${fmt(sim.liquido_cliente)}
Honorários escritório:  ${fmt(sim.honorarios_escritorio)}`}
              {sim.comparativo_sentenca?.valor_estimado && (
                <p className="mt-2 text-claudio">📈 Sentença estimada: {fmt(sim.comparativo_sentenca.valor_estimado)} ({sim.comparativo_sentenca.probabilidade_exito}% êxito)</p>
              )}
              {sim.parcelamento?.length > 1 && (
                <div className="mt-2">{sim.parcelamento.map((p) => (
                  <div key={p.parcela}>{p.parcela}x {fmt(p.valor)} — {p.vencimento}</div>
                ))}</div>
              )}
            </div>
          )}
        </div>
      )}

      {aba === "resumo" && caixa && (
        <div className="bg-white rounded-xl border p-5">
          <h2 className="font-semibold text-gray-700 mb-2">Saldo do período</h2>
          <p className="text-3xl font-bold text-claudio">{fmt(caixa.saldo)}</p>
          <p className="text-sm text-gray-500 mt-1">{caixa.periodo.inicio} a {caixa.periodo.fim}</p>
        </div>
      )}
    </div>
  );
}

export default function Financeiro() {
  return (
    <SensitiveGate titulo="Financeiro">
      <Conteudo />
    </SensitiveGate>
  );
}
