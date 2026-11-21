import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";

const STATUS = [
  { v: "", label: "Todos" },
  { v: "ativo", label: "Ativos" },
  { v: "encerrado", label: "Encerrados" },
  { v: "arquivado", label: "Arquivados" },
];

const CORES = {
  ativo: "bg-green-100 text-green-700",
  encerrado: "bg-gray-100 text-gray-600",
  arquivado: "bg-yellow-100 text-yellow-700",
};

export default function Processos() {
  const [processos, setProcessos] = useState([]);
  const [busca, setBusca] = useState("");
  const [status, setStatus] = useState("");
  const [carregando, setCarregando] = useState(false);

  async function carregar() {
    setCarregando(true);
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    if (busca) params.set("busca", busca);
    try {
      setProcessos(await api(`/api/processos?${params.toString()}`));
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-4">Processos</h1>

      <div className="flex gap-3 mb-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            carregar();
          }}
          className="flex-1"
        >
          <input
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Buscar por número ou tese..."
            className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-claudio-light"
          />
        </form>
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm"
        >
          {STATUS.map((s) => (
            <option key={s.v} value={s.v}>
              {s.label}
            </option>
          ))}
        </select>
      </div>

      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-left">
            <tr>
              <th className="px-4 py-2 font-medium">Número</th>
              <th className="px-4 py-2 font-medium">Tipo</th>
              <th className="px-4 py-2 font-medium">Vara</th>
              <th className="px-4 py-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {carregando ? (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-gray-400">
                  Carregando...
                </td>
              </tr>
            ) : processos.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-gray-400">
                  Nenhum processo encontrado.
                </td>
              </tr>
            ) : (
              processos.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 font-medium">
                    <Link to={`/processos/${p.id}`} className="text-claudio hover:underline">
                      {p.numero}
                    </Link>
                  </td>
                  <td className="px-4 py-2">
                    {p.tipo}
                    {p.subtipo ? ` / ${p.subtipo}` : ""}
                  </td>
                  <td className="px-4 py-2 text-gray-500">{p.vara || "—"}</td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-0.5 rounded-full text-xs ${CORES[p.status] || ""}`}>
                      {p.status}
                    </span>
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
