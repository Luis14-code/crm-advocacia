import { useEffect, useRef, useState } from "react";
import { wsUrl } from "../lib/api";

export default function Chat() {
  const [mensagens, setMensagens] = useState([
    { role: "assistant", texto: "Olá! Sou o Cláudio. Pergunte, por exemplo: *quais processos eu tenho?*" },
  ]);
  const [input, setInput] = useState("");
  const [conectado, setConectado] = useState(false);
  const wsRef = useRef(null);
  const fimRef = useRef(null);

  useEffect(() => {
    const ws = new WebSocket(wsUrl());
    wsRef.current = ws;
    ws.onopen = () => setConectado(true);
    ws.onclose = () => setConectado(false);
    ws.onmessage = (ev) => {
      const data = JSON.parse(ev.data);
      setMensagens((m) => [
        ...m,
        { role: "assistant", texto: data.display || data.error || "…", actions: data.actions },
      ]);
    };
    return () => ws.close();
  }, []);

  useEffect(() => {
    fimRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [mensagens]);

  function enviar(e) {
    e?.preventDefault();
    const texto = input.trim();
    if (!texto || !conectado) return;
    setMensagens((m) => [...m, { role: "user", texto }]);
    wsRef.current.send(JSON.stringify({ mensagem: texto }));
    setInput("");
  }

  return (
    <>
      <div className="px-4 py-3 border-b flex items-center gap-2">
        <span className={`w-2 h-2 rounded-full ${conectado ? "bg-green-500" : "bg-gray-400"}`} />
        <span className="font-semibold text-claudio">Cláudio</span>
      </div>

      <div className="flex-1 overflow-auto p-4 space-y-3">
        {mensagens.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm whitespace-pre-wrap ${
                m.role === "user" ? "bg-claudio text-white" : "bg-gray-100 text-gray-800"
              }`}
            >
              {m.texto}
            </div>
          </div>
        ))}
        <div ref={fimRef} />
      </div>

      <form onSubmit={enviar} className="p-3 border-t flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={conectado ? "Pergunte ao Cláudio..." : "Conectando..."}
          disabled={!conectado}
          className="flex-1 border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-claudio-light"
        />
        <button
          type="submit"
          disabled={!conectado}
          className="bg-claudio text-white rounded-lg px-4 text-sm font-medium hover:bg-claudio-light disabled:opacity-50"
        >
          Enviar
        </button>
      </form>
    </>
  );
}
