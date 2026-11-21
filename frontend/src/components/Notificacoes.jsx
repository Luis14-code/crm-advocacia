import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";

export default function Notificacoes() {
  const [aberto, setAberto] = useState(false);
  const [itens, setItens] = useState([]);
  const [naoLidas, setNaoLidas] = useState(0);
  const ref = useRef(null);

  async function carregarContador() {
    try {
      const { unread } = await api("/api/notificacoes/unread-count");
      setNaoLidas(unread);
    } catch {
      /* ignora */
    }
  }

  async function abrir() {
    setAberto((v) => !v);
    if (!aberto) {
      try {
        setItens(await api("/api/notificacoes?limit=20"));
      } catch {
        /* ignora */
      }
    }
  }

  async function marcarTodas() {
    await api("/api/notificacoes/read-all", { method: "POST" });
    setNaoLidas(0);
    setItens((arr) => arr.map((n) => ({ ...n, lida: true })));
  }

  useEffect(() => {
    carregarContador();
    const t = setInterval(carregarContador, 30000); // polling a cada 30s
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    function fora(e) {
      if (ref.current && !ref.current.contains(e.target)) setAberto(false);
    }
    document.addEventListener("mousedown", fora);
    return () => document.removeEventListener("mousedown", fora);
  }, []);

  const ICONE = { movimentacao: "📬", prazo: "⏰", briefing: "📋", sync: "🔄", sistema: "ℹ️" };

  return (
    <div className="relative" ref={ref}>
      <button onClick={abrir} className="relative text-xl">
        🔔
        {naoLidas > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-[10px] rounded-full min-w-[16px] h-4 px-1 flex items-center justify-center">
            {naoLidas > 9 ? "9+" : naoLidas}
          </span>
        )}
      </button>

      {aberto && (
        <div className="absolute right-0 mt-2 w-80 bg-white border rounded-xl shadow-lg z-50">
          <div className="flex items-center justify-between px-4 py-2 border-b">
            <span className="font-semibold text-gray-700 text-sm">Notificações</span>
            <button onClick={marcarTodas} className="text-xs text-claudio hover:underline">
              Marcar todas como lidas
            </button>
          </div>
          <div className="max-h-80 overflow-auto">
            {itens.length === 0 ? (
              <p className="px-4 py-6 text-center text-gray-400 text-sm">Nenhuma notificação.</p>
            ) : (
              itens.map((n) => (
                <div
                  key={n.id}
                  className={`px-4 py-3 border-b text-sm ${n.lida ? "opacity-60" : "bg-blue-50/40"}`}
                >
                  <div className="flex gap-2">
                    <span>{ICONE[n.tipo] || "•"}</span>
                    <div>
                      <p className="font-medium text-gray-800">{n.titulo}</p>
                      {n.corpo && <p className="text-gray-500 text-xs mt-0.5">{n.corpo}</p>}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
