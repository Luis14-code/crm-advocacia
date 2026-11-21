import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { useAuth } from "../stores/auth";

export default function Dashboard() {
  const user = useAuth((s) => s.user);
  const [processos, setProcessos] = useState([]);
  const [erro, setErro] = useState(null);

  useEffect(() => {
    api("/api/processos?status=ativo")
      .then(setProcessos)
      .catch((e) => setErro(e.message));
  }, []);

  const cards = [
    { label: "Processos ativos", valor: processos.length, cor: "bg-claudio" },
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

      <div className="bg-white rounded-xl border p-5">
        <h2 className="font-semibold text-gray-700 mb-3">Seus processos ativos</h2>
        {processos.length === 0 ? (
          <p className="text-gray-400 text-sm">Nenhum processo ativo.</p>
        ) : (
          <ul className="divide-y">
            {processos.slice(0, 5).map((p) => (
              <li key={p.id} className="py-2 flex justify-between text-sm">
                <span className="font-medium">{p.numero}</span>
                <span className="text-gray-500">{p.tipo}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
