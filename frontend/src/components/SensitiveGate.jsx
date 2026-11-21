import { useState } from "react";
import { getSensitiveToken, desbloquearSensivel } from "../lib/api";

export default function SensitiveGate({ children, titulo = "Área protegida" }) {
  const [desbloqueado, setDesbloqueado] = useState(!!getSensitiveToken());
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState(null);
  const [carregando, setCarregando] = useState(false);

  async function entrar(e) {
    e.preventDefault();
    setCarregando(true);
    setErro(null);
    try {
      await desbloquearSensivel(senha);
      setDesbloqueado(true);
    } catch (err) {
      setErro(err.message || "Senha incorreta");
    } finally {
      setCarregando(false);
    }
  }

  if (desbloqueado) return children;

  return (
    <div className="max-w-sm mx-auto mt-16">
      <form onSubmit={entrar} className="bg-white rounded-xl border p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-1">🔒 {titulo}</h2>
        <p className="text-sm text-gray-500 mb-4">
          Esta área exige a senha sensível (segunda autenticação).
        </p>
        <input
          type="password"
          value={senha}
          onChange={(e) => setSenha(e.target.value)}
          placeholder="Senha sensível"
          className="w-full border rounded-lg px-3 py-2 mb-3 focus:outline-none focus:ring-2 focus:ring-claudio-light"
          autoFocus
        />
        {erro && <p className="text-red-600 text-sm mb-2">{erro}</p>}
        <button
          type="submit"
          disabled={carregando}
          className="w-full bg-claudio text-white rounded-lg py-2 font-medium hover:bg-claudio-light disabled:opacity-60"
        >
          {carregando ? "Validando..." : "Desbloquear"}
        </button>
      </form>
    </div>
  );
}
