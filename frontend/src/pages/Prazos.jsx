import { useEffect, useState } from "react";
import { api } from "../lib/api";

function classificar(dataLimiteUtil) {
  const hoje = new Date();
  hoje.setHours(0, 0, 0, 0);
  const limite = new Date(dataLimiteUtil + "T00:00:00");
  const dias = Math.round((limite - hoje) / 86400000);
  if (dias < 0) return { cor: "border-red-500 bg-red-50", tag: "Atrasado", txt: "text-red-700" };
  if (dias === 0) return { cor: "border-red-500 bg-red-50", tag: "Vence hoje", txt: "text-red-700" };
  if (dias <= 3) return { cor: "border-yellow-400 bg-yellow-50", tag: `${dias}d`, txt: "text-yellow-700" };
  return { cor: "border-green-500 bg-green-50", tag: `${dias}d`, txt: "text-green-700" };
}

export default function Prazos() {
  const [prazos, setPrazos] = useState([]);
  const [carregando, setCarregando] = useState(true);

  async function carregar() {
    setCarregando(true);
    try {
      setPrazos(await api("/api/prazos?status=pendente"));
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    carregar();
  }, []);

  async function cumprir(id) {
    await api(`/api/prazos/${id}`, { method: "PATCH", body: { status: "cumprido" } });
    setPrazos((arr) => arr.filter((p) => p.id !== id));
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold text-gray-800">Prazos</h1>
        <div className="flex gap-3 text-xs text-gray-500">
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-red-500" /> Hoje/atrasado</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-yellow-400" /> ≤ 3 dias</span>
          <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-green-500" /> No prazo</span>
        </div>
      </div>

      {carregando ? (
        <p className="text-gray-400">Carregando...</p>
      ) : prazos.length === 0 ? (
        <div className="bg-white rounded-xl border p-8 text-center text-gray-400">
          🟢 Nenhum prazo pendente. Tudo em dia!
        </div>
      ) : (
        <div className="space-y-3">
          {prazos.map((p) => {
            const c = classificar(p.data_limite_util);
            return (
              <div
                key={p.id}
                className={`border-l-4 ${c.cor} rounded-lg p-4 flex items-center justify-between`}
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold">
                      {new Date(p.data_limite_util + "T00:00:00").toLocaleDateString("pt-BR")}
                    </span>
                    <span className={`text-xs font-medium ${c.txt}`}>{c.tag}</span>
                  </div>
                  <p className="text-sm text-gray-700">{p.descricao}</p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    ⚖️ {p.processo_numero || "—"}
                    {p.cliente_nome ? ` · 👤 ${p.cliente_nome}` : ""}
                  </p>
                </div>
                <button
                  onClick={() => cumprir(p.id)}
                  className="text-xs text-claudio border border-claudio rounded-lg px-3 py-1.5 hover:bg-claudio hover:text-white transition"
                >
                  Marcar cumprido
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
