import { useEffect, useState } from "react";
import { api } from "../lib/api";

export default function Mural() {
  const [m, setM] = useState(null);

  useEffect(() => {
    api("/api/mural").then(setM).catch(() => {});
    const t = setInterval(() => api("/api/mural").then(setM).catch(() => {}), 30000);
    return () => clearInterval(t);
  }, []);

  if (!m) return null;
  const g = m.gamificacao;

  return (
    <div className="bg-gradient-to-r from-claudio to-claudio-light text-white rounded-xl p-5 mb-6">
      <div className="flex items-center justify-between mb-2">
        <h2 className="font-semibold">🎉 Mural de conquistas</h2>
        <div className="flex gap-3 text-xs">
          <span className="bg-white/15 rounded-full px-2 py-0.5">🔥 streak {g.streak_prazos}</span>
          <span className="bg-white/15 rounded-full px-2 py-0.5">🤝 {g.acordos_mes} acordos/mês</span>
        </div>
      </div>
      <div className="flex flex-wrap gap-3">
        {m.eventos.map((e, i) => (
          <span key={i} className="text-sm bg-white/10 rounded-lg px-3 py-1">
            {e.icone} {e.texto}
          </span>
        ))}
      </div>
    </div>
  );
}
