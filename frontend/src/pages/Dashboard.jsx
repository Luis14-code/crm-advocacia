import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../stores/auth";

function BlocoBriefing({ titulo, cor, itens }) {
  if (!itens || itens.length === 0) return null;
  return (
    <div className="mb-3">
      <h3 className={`text-sm font-semibold ${cor} mb-1`}>{titulo}</h3>
      <ul className="space-y-1">
        {itens.map((it, i) => (
          <li key={i} className="text-sm text-gray-700">
            <span className="font-medium">{it.processo}</span>: {it.descricao || it.tipo}
            {it.data_limite && (
              <span className="text-gray-400"> (vence {new Date(it.data_limite + "T00:00:00").toLocaleDateString("pt-BR")})</span>
            )}
            {it.dias_parado != null && <span className="text-gray-400"> ({it.dias_parado}d parado)</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function Dashboard() {
  const user = useAuth((s) => s.user);
  const [processos, setProcessos] = useState([]);
  const [briefing, setBriefing] = useState(null);
  const [erro, setErro] = useState(null);

  useEffect(() => {
    api("/api/processos?status=ativo").then(setProcessos).catch((e) => setErro(e.message));
    api("/api/briefing").then(setBriefing).catch(() => {});
  }, []);

  const cards = [
    { label: "Processos ativos", valor: processos.length, cor: "bg-claudio" },
    { label: "Urgentes hoje", valor: briefing?.urgente?.length ?? "—", cor: "bg-red-600" },
    { label: "Em atenção", valor: briefing?.atencao?.length ?? "—", cor: "bg-yellow-500" },
    { label: "Perfil", valor: user?.perfil, cor: "bg-claudio-light" },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-1">
        Bom dia, {user?.nome?.split(" ")[0]} 👋
      </h1>
      <p className="text-gray-500 mb-6">Aqui está um panorama do seu dia.</p>

      {erro && <p className="text-red-600 mb-4">{erro}</p>}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {cards.map((c) => (
          <div key={c.label} className={`${c.cor} text-white rounded-xl p-5`}>
            <p className="text-sm text-white/80">{c.label}</p>
            <p className="text-3xl font-bold mt-1 capitalize">{c.valor}</p>
          </div>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Briefing do dia */}
        <div className="bg-white rounded-xl border p-5">
          <h2 className="font-semibold text-gray-700 mb-3">📋 Briefing do dia</h2>
          {!briefing ? (
            <p className="text-gray-400 text-sm">Carregando briefing...</p>
          ) : (
            <>
              <p className="text-xs text-gray-400 mb-3">{briefing.resumo}</p>
              <BlocoBriefing titulo="🔴 Urgente" cor="text-red-600" itens={briefing.urgente} />
              <BlocoBriefing titulo="🟡 Atenção" cor="text-yellow-600" itens={briefing.atencao} />
              <BlocoBriefing titulo="🟢 Acompanhamento" cor="text-green-600" itens={briefing.acompanhamento} />
              {briefing.urgente.length === 0 &&
                briefing.atencao.length === 0 &&
                briefing.acompanhamento.length === 0 && (
                  <p className="text-gray-400 text-sm">Nada pendente para hoje. ☕</p>
                )}
            </>
          )}
        </div>

        {/* Processos ativos */}
        <div className="bg-white rounded-xl border p-5">
          <h2 className="font-semibold text-gray-700 mb-3">Seus processos ativos</h2>
          {processos.length === 0 ? (
            <p className="text-gray-400 text-sm">Nenhum processo ativo.</p>
          ) : (
            <ul className="divide-y">
              {processos.slice(0, 6).map((p) => (
                <li key={p.id} className="py-2 flex justify-between text-sm">
                  <Link to={`/processos/${p.id}`} className="font-medium text-claudio hover:underline">
                    {p.numero}
                  </Link>
                  <span className="text-gray-500">{p.tipo}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
