import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../stores/auth";
import Chat from "./Chat";

const MENU = [
  { to: "/", label: "Dashboard", icon: "📊", perfis: ["socio", "advogado", "estagiario", "financeiro"] },
  { to: "/processos", label: "Processos", icon: "⚖️", perfis: ["socio", "advogado", "estagiario"] },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [chatAberto, setChatAberto] = useState(true);

  function sair() {
    logout();
    navigate("/login");
  }

  const itens = MENU.filter((m) => m.perfis.includes(user?.perfil));

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <aside className="w-60 bg-claudio text-white flex flex-col">
        <div className="px-5 py-4 border-b border-white/10">
          <h1 className="text-2xl font-bold">Cláudio</h1>
          <p className="text-xs text-white/60">CRM Jurídico</p>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {itens.map((m) => (
            <NavLink
              key={m.to}
              to={m.to}
              end={m.to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm ${
                  isActive ? "bg-white/15 font-medium" : "hover:bg-white/10"
                }`
              }
            >
              <span>{m.icon}</span>
              {m.label}
            </NavLink>
          ))}
        </nav>
        <div className="px-4 py-3 border-t border-white/10 text-sm">
          <p className="font-medium">{user?.nome}</p>
          <p className="text-white/60 text-xs capitalize">{user?.perfil}</p>
          <button onClick={sair} className="mt-2 text-xs text-claudio-accent hover:underline">
            Sair
          </button>
        </div>
      </aside>

      {/* Conteúdo */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 bg-white border-b flex items-center justify-between px-6">
          <h2 className="text-lg font-semibold text-gray-700">Escritório</h2>
          <button
            onClick={() => setChatAberto((v) => !v)}
            className="text-sm text-claudio hover:underline"
          >
            {chatAberto ? "Fechar chat" : "Falar com o Cláudio"}
          </button>
        </header>
        <div className="flex-1 flex min-h-0">
          <main className="flex-1 overflow-auto p-6">
            <Outlet />
          </main>
          {chatAberto && (
            <div className="w-96 border-l bg-white flex flex-col">
              <Chat />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
