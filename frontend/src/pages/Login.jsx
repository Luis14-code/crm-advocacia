import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../stores/auth";

export default function Login() {
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const { login, loading, error } = useAuth();
  const navigate = useNavigate();

  async function onSubmit(e) {
    e.preventDefault();
    const ok = await login(email, senha);
    if (ok) navigate("/");
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-claudio">
      <form
        onSubmit={onSubmit}
        className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-sm"
      >
        <div className="text-center mb-6">
          <h1 className="text-3xl font-bold text-claudio">Cláudio</h1>
          <p className="text-sm text-gray-500">CRM Jurídico</p>
        </div>

        <label className="block text-sm font-medium text-gray-700 mb-1">E-mail</label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="w-full border rounded-lg px-3 py-2 mb-4 focus:outline-none focus:ring-2 focus:ring-claudio-light"
          placeholder="advogado@escritorio.com"
        />

        <label className="block text-sm font-medium text-gray-700 mb-1">Senha</label>
        <input
          type="password"
          value={senha}
          onChange={(e) => setSenha(e.target.value)}
          required
          className="w-full border rounded-lg px-3 py-2 mb-4 focus:outline-none focus:ring-2 focus:ring-claudio-light"
          placeholder="••••••••"
        />

        {error && <p className="text-red-600 text-sm mb-3">{error}</p>}

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-claudio text-white rounded-lg py-2 font-medium hover:bg-claudio-light disabled:opacity-60"
        >
          {loading ? "Entrando..." : "Entrar"}
        </button>
      </form>
    </div>
  );
}
