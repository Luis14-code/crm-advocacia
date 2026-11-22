import { useEffect, useRef, useState } from "react";
import { api, getSensitiveToken, API_URL } from "../lib/api";
import SensitiveGate from "../components/SensitiveGate";
import { BarMensal, Donut } from "../components/Charts";

const fmt = (v) => (v ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const hojeISO = () => new Date().toISOString().slice(0, 10);
const mesISO = () => new Date().toISOString().slice(0, 7) + "-01";

function Conteudo() {
  const sens = () => getSensitiveToken();
  const [dash, setDash] = useState(null);
  const [graf, setGraf] = useState(null);
  const [transacoes, setTransacoes] = useState([]);
  const [cobrancas, setCobrancas] = useState([]);
  const [clientes, setClientes] = useState([]);
  const [processos, setProcessos] = useState([]);
  const [dre, setDre] = useState(null);
  const [aba, setAba] = useState("resumo");
  const [msg, setMsg] = useState(null);
  const fileRef = useRef(null);

  // Simulador
  const [procId, setProcId] = useState("");
  const [valor, setValor] = useState("");
  const [parcelas, setParcelas] = useState(1);
  const [sim, setSim] = useState(null);

  async function carregar() {
    const s = { sensitive: sens() };
    setTransacoes(await api("/api/financeiro/transacoes", s).catch(() => []));
    setCobrancas(await api("/api/financeiro/cobrancas", s).catch(() => []));
  }

  useEffect(() => {
    const s = { sensitive: sens() };
    api("/api/financeiro/dashboard", s).then(setDash).catch(() => {});
    api("/api/financeiro/graficos", s).then(setGraf).catch(() => {});
    api(`/api/financeiro/dre?inicio=${mesISO()}&fim=${hojeISO()}`, s).then(setDre).catch(() => {});
    api("/api/processos").then(setProcessos).catch(() => {});
    api("/api/clientes").then(setClientes).catch(() => {});
    carregar();

    const access = localStorage.getItem("access_token");
    const es = new EventSource(`${API_URL}/api/financeiro/dashboard/stream?token=${access}&sensitive=${sens()}`);
    es.onmessage = (ev) => { try { setDash(JSON.parse(ev.data)); } catch { /* */ } };
    es.onerror = () => es.close();
    return () => es.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function simular(e) {
    e.preventDefault();
    setMsg(null);
    try {
      setSim(await api("/api/financeiro/simular-acordo", {
        method: "POST", sensitive: sens(),
        body: { processo_id: Number(procId), valor_bruto: Number(valor), parcelas: Number(parcelas) },
      }));
    } catch (e) { setMsg(e.message); }
  }

  async function importarExtrato(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setMsg("Importando...");
    const form = new FormData();
    form.append("arquivo", file);
    try {
      const resp = await fetch(`${API_URL}/api/financeiro/conciliacao/importar`, {
        method: "POST",
        headers: { Authorization: `Bearer ${localStorage.getItem("access_token")}`, "X-Sensitive-Token": sens() },
        body: form,
      });
      const r = await resp.json();
      setMsg(`✓ ${r.lancamentos} lançamentos: ${r.conciliadas} conciliados, ${r.novas} novos.`);
      carregar();
    } catch (err) { setMsg(`Erro: ${err.message}`); }
    if (fileRef.current) fileRef.current.value = "";
  }

  const ABAS = [
    ["resumo", "Resumo"], ["receber", "A receber"], ["pagar", "A pagar"],
    ["dre", "DRE"], ["cobrancas", "Cobranças"], ["simulador", "Simulador"],
  ];

  const boletosDonut = graf ? [
    { categoria: "Pagos", valor: graf.boletos.pago.valor },
    { categoria: "Pendentes", valor: graf.boletos.pendente.valor },
    { categoria: "Vencidos", valor: graf.boletos.vencido.valor },
  ].filter((x) => x.valor > 0) : [];

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-4">Financeiro</h1>
      {msg && <p className="text-sm text-claudio mb-3">{msg}</p>}

      {/* KPIs em tempo real */}
      {dash && (
        <>
          <div className="flex items-center gap-2 mb-2 text-xs text-gray-400">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" /> Tempo real · {dash.atualizado_em?.slice(11, 19)}
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-green-600 text-white rounded-xl p-4"><p className="text-xs opacity-80">Faturado na semana</p><p className="text-xl font-bold">{fmt(dash.faturado_semana)}</p></div>
            <div className="bg-claudio text-white rounded-xl p-4"><p className="text-xs opacity-80">Faturado no mês</p><p className="text-xl font-bold">{fmt(dash.faturado_mes)}</p></div>
            <div className="bg-claudio-light text-white rounded-xl p-4"><p className="text-xs opacity-80">A receber</p><p className="text-xl font-bold">{fmt(dash.a_receber)}</p></div>
            <div className="bg-yellow-500 text-white rounded-xl p-4"><p className="text-xs opacity-80">Inadimplência</p><p className="text-xl font-bold">{fmt(dash.inadimplencia)}</p></div>
          </div>
        </>
      )}

      <div className="flex gap-2 mb-4 flex-wrap">
        {ABAS.map(([k, label]) => (
          <button key={k} onClick={() => setAba(k)}
            className={`px-4 py-1.5 rounded-lg text-sm ${aba === k ? "bg-claudio text-white" : "bg-white border"}`}>
            {label}
          </button>
        ))}
      </div>

      {aba === "resumo" && graf && (
        <div className="grid md:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border p-5">
            <h2 className="font-semibold text-gray-700 mb-3">Faturamento (6 meses)</h2>
            <BarMensal data={graf.faturamento_mensal} />
          </div>
          <div className="bg-white rounded-xl border p-5">
            <h2 className="font-semibold text-gray-700 mb-3">Boletos</h2>
            <Donut data={boletosDonut} nameKey="categoria" valueKey="valor" />
            <div className="flex justify-around text-xs text-gray-500 mt-1">
              <span>✅ {graf.boletos.pago.qtd} pagos</span>
              <span>🟡 {graf.boletos.pendente.qtd} pendentes</span>
              <span>🔴 {graf.boletos.vencido.qtd} vencidos</span>
            </div>
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

      {(aba === "receber" || aba === "pagar") && (
        <TabContas
          tipo={aba === "receber" ? "entrada" : "saida"}
          transacoes={transacoes.filter((t) => t.tipo === (aba === "receber" ? "entrada" : "saida"))}
          clientes={clientes}
          processos={processos}
          sens={sens}
          onChange={carregar}
          fileRef={fileRef}
          importar={importarExtrato}
        />
      )}

      {aba === "dre" && dre && (
        <div className="bg-white rounded-xl border p-5 max-w-3xl">
          <h2 className="font-semibold text-gray-700 mb-1">DRE — Demonstrativo de Resultados</h2>
          <p className="text-xs text-gray-400 mb-4">{dre.periodo.inicio} a {dre.periodo.fim}</p>
          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <h3 className="text-sm font-medium text-green-700 mb-2">Receitas · {fmt(dre.total_receitas)}</h3>
              {dre.receitas.map((r) => (
                <div key={r.categoria} className="flex justify-between text-sm py-1 border-b">
                  <span className="capitalize text-gray-600">{r.categoria}</span><span>{fmt(r.valor)}</span>
                </div>
              ))}
            </div>
            <div>
              <h3 className="text-sm font-medium text-red-600 mb-2">Despesas · {fmt(dre.total_despesas)}</h3>
              {dre.despesas.map((d) => (
                <div key={d.categoria} className="flex justify-between text-sm py-1 border-b">
                  <span className="capitalize text-gray-600">{d.categoria}</span><span>{fmt(d.valor)}</span>
                </div>
              ))}
            </div>
          </div>
          <div className={`mt-5 p-4 rounded-lg ${dre.resultado >= 0 ? "bg-green-50" : "bg-red-50"}`}>
            <div className="flex justify-between items-center">
              <span className="font-semibold">Resultado do período</span>
              <span className={`text-2xl font-bold ${dre.resultado >= 0 ? "text-green-700" : "text-red-600"}`}>
                {fmt(dre.resultado)} {dre.margem != null && <span className="text-sm">({dre.margem}%)</span>}
              </span>
            </div>
          </div>
        </div>
      )}

      {aba === "cobrancas" && (
        <TabCobrancas cobrancas={cobrancas} clientes={clientes} processos={processos} sens={sens} onChange={carregar} setMsg={setMsg} />
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
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function TabContas({ tipo, transacoes, clientes, processos, sens, onChange, fileRef, importar }) {
  const [form, setForm] = useState({ descricao: "", valor: "", categoria: "", data_vencimento: "", cliente_id: "", processo_id: "" });
  async function criar(e) {
    e.preventDefault();
    await api("/api/financeiro/transacoes", {
      method: "POST", sensitive: sens(),
      body: {
        tipo, descricao: form.descricao, categoria: form.categoria || (tipo === "saida" ? "despesa" : "honorarios"),
        valor: Number(form.valor), data_vencimento: form.data_vencimento || null,
        cliente_id: form.cliente_id ? Number(form.cliente_id) : null,
        processo_id: form.processo_id ? Number(form.processo_id) : null,
      },
    });
    setForm({ descricao: "", valor: "", categoria: "", data_vencimento: "", cliente_id: "", processo_id: "" });
    onChange();
  }
  const cor = { pago: "text-green-700", pendente: "text-yellow-700", vencido: "text-red-600", cancelado: "text-gray-400" };
  return (
    <div>
      <form onSubmit={criar} className="bg-white rounded-xl border p-4 mb-4 grid md:grid-cols-6 gap-2 items-end">
        <input value={form.descricao} onChange={(e) => setForm({ ...form, descricao: e.target.value })} placeholder="Descrição" className="border rounded-lg px-3 py-2 text-sm md:col-span-2" />
        <input value={form.categoria} onChange={(e) => setForm({ ...form, categoria: e.target.value })} placeholder="Categoria" className="border rounded-lg px-3 py-2 text-sm" />
        <input type="number" step="0.01" value={form.valor} onChange={(e) => setForm({ ...form, valor: e.target.value })} placeholder="Valor" required className="border rounded-lg px-3 py-2 text-sm" />
        <input type="date" value={form.data_vencimento} onChange={(e) => setForm({ ...form, data_vencimento: e.target.value })} className="border rounded-lg px-3 py-2 text-sm" />
        <button type="submit" className="bg-claudio text-white rounded-lg px-3 py-2 text-sm font-medium">+ {tipo === "saida" ? "Despesa" : "Receita"}</button>
      </form>

      {tipo === "entrada" && (
        <div className="mb-3">
          <label className="text-sm bg-white border rounded-lg px-3 py-1.5 cursor-pointer hover:bg-gray-50">
            📥 Importar extrato (OFX/CSV)
            <input ref={fileRef} type="file" accept=".ofx,.csv,.txt" onChange={importar} className="hidden" />
          </label>
        </div>
      )}

      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-left">
            <tr><th className="px-4 py-2">Vencimento</th><th className="px-4 py-2">Categoria</th><th className="px-4 py-2">Descrição</th><th className="px-4 py-2">Valor</th><th className="px-4 py-2">Status</th></tr>
          </thead>
          <tbody className="divide-y">
            {transacoes.length === 0 ? (
              <tr><td colSpan={5} className="px-4 py-6 text-center text-gray-400">Nada aqui.</td></tr>
            ) : transacoes.map((t) => (
              <tr key={t.id} className="hover:bg-gray-50">
                <td className="px-4 py-2">{t.data_vencimento ? new Date(t.data_vencimento + "T00:00:00").toLocaleDateString("pt-BR") : "—"}</td>
                <td className="px-4 py-2">{t.categoria || "—"}</td>
                <td className="px-4 py-2 text-gray-600">{t.descricao || "—"}</td>
                <td className="px-4 py-2 font-medium">{fmt(Number(t.valor))}</td>
                <td className={`px-4 py-2 ${cor[t.status] || ""}`}>{t.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function TabCobrancas({ cobrancas, clientes, processos, sens, onChange, setMsg }) {
  const [form, setForm] = useState({ cliente_id: "", valor: "", descricao: "", recorrencia: "mensal", dia_vencimento: 10, enviar_whatsapp: true });
  async function criar(e) {
    e.preventDefault();
    if (!form.cliente_id) return;
    await api("/api/financeiro/cobrancas", {
      method: "POST", sensitive: sens(),
      body: { ...form, cliente_id: Number(form.cliente_id), valor: Number(form.valor), dia_vencimento: Number(form.dia_vencimento) },
    });
    setForm({ cliente_id: "", valor: "", descricao: "", recorrencia: "mensal", dia_vencimento: 10, enviar_whatsapp: true });
    onChange();
  }
  async function toggle(c) {
    await api(`/api/financeiro/cobrancas/${c.id}`, { method: "PUT", sensitive: sens(), body: { ativo: !c.ativo } });
    onChange();
  }
  async function remover(id) {
    await api(`/api/financeiro/cobrancas/${id}`, { method: "DELETE", sensitive: sens() });
    onChange();
  }
  async function processar() {
    const r = await api("/api/financeiro/cobrancas/processar", { method: "POST", sensitive: sens() });
    setMsg(`✓ ${r.gerados} boleto(s) gerado(s) agora.`);
    onChange();
  }
  return (
    <div>
      <div className="bg-blue-50 border border-blue-100 rounded-lg p-3 mb-4 text-sm text-gray-600">
        Programe cobranças recorrentes por cliente. O Cláudio gera o boleto no vencimento e, se marcado,
        <strong> avisa o cliente pelo WhatsApp</strong> automaticamente.
      </div>

      <form onSubmit={criar} className="bg-white rounded-xl border p-4 mb-4 grid md:grid-cols-6 gap-2 items-end">
        <select value={form.cliente_id} onChange={(e) => setForm({ ...form, cliente_id: e.target.value })} required className="border rounded-lg px-3 py-2 text-sm md:col-span-2">
          <option value="">Cliente</option>
          {clientes.map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
        </select>
        <input type="number" step="0.01" value={form.valor} onChange={(e) => setForm({ ...form, valor: e.target.value })} placeholder="Valor" required className="border rounded-lg px-3 py-2 text-sm" />
        <select value={form.recorrencia} onChange={(e) => setForm({ ...form, recorrencia: e.target.value })} className="border rounded-lg px-3 py-2 text-sm">
          <option value="mensal">Mensal</option>
          <option value="unica">Única</option>
        </select>
        <input type="number" min="1" max="28" value={form.dia_vencimento} onChange={(e) => setForm({ ...form, dia_vencimento: e.target.value })} placeholder="Dia venc." className="border rounded-lg px-3 py-2 text-sm" />
        <label className="flex items-center gap-1 text-xs text-gray-600">
          <input type="checkbox" checked={form.enviar_whatsapp} onChange={(e) => setForm({ ...form, enviar_whatsapp: e.target.checked })} /> WhatsApp
        </label>
        <input value={form.descricao} onChange={(e) => setForm({ ...form, descricao: e.target.value })} placeholder="Descrição (opcional)" className="border rounded-lg px-3 py-2 text-sm md:col-span-5" />
        <button type="submit" className="bg-claudio text-white rounded-lg px-3 py-2 text-sm font-medium">+ Programar</button>
      </form>

      <div className="flex justify-end mb-2">
        <button onClick={processar} className="text-sm border border-claudio text-claudio rounded-lg px-3 py-1.5 hover:bg-claudio hover:text-white transition">
          Gerar vencidas agora
        </button>
      </div>

      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-left">
            <tr><th className="px-4 py-2">Cliente</th><th className="px-4 py-2">Valor</th><th className="px-4 py-2">Recorrência</th><th className="px-4 py-2">Próxima</th><th className="px-4 py-2">Zap</th><th className="px-4 py-2">Status</th><th className="px-4 py-2"></th></tr>
          </thead>
          <tbody className="divide-y">
            {cobrancas.length === 0 ? (
              <tr><td colSpan={7} className="px-4 py-6 text-center text-gray-400">Nenhuma cobrança programada.</td></tr>
            ) : cobrancas.map((c) => (
              <tr key={c.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 font-medium">{c.cliente_nome || `#${c.cliente_id}`}</td>
                <td className="px-4 py-2">{fmt(Number(c.valor))}</td>
                <td className="px-4 py-2 capitalize">{c.recorrencia}</td>
                <td className="px-4 py-2">{new Date(c.proxima_data + "T00:00:00").toLocaleDateString("pt-BR")}</td>
                <td className="px-4 py-2">{c.enviar_whatsapp ? "📱" : "—"}</td>
                <td className="px-4 py-2">
                  <button onClick={() => toggle(c)} className={`text-xs px-2 py-0.5 rounded-full ${c.ativo ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                    {c.ativo ? "ativa" : "pausada"}
                  </button>
                </td>
                <td className="px-4 py-2 text-right">
                  <button onClick={() => remover(c.id)} className="text-xs text-red-500 hover:underline">excluir</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
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
