import { useEffect, useState } from "react";
import { api } from "../lib/api";

const VAZIO = {
  nome: "", cpf: "", telefone: "", email: "", data_nascimento: "",
  tom_comunicacao: "formal", whatsapp_opt_out: false, notas: "",
  endereco: { cep: "", logradouro: "", numero: "", complemento: "", bairro: "", cidade: "", uf: "" },
};

export default function Clientes() {
  const [clientes, setClientes] = useState([]);
  const [busca, setBusca] = useState("");
  const [form, setForm] = useState(VAZIO);
  const [editId, setEditId] = useState(null);
  const [msg, setMsg] = useState(null);

  async function carregar() {
    const q = busca ? `?busca=${encodeURIComponent(busca)}` : "";
    setClientes(await api(`/api/clientes${q}`));
  }

  useEffect(() => {
    carregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function setEnd(campo, valor) {
    setForm((f) => ({ ...f, endereco: { ...f.endereco, [campo]: valor } }));
  }

  function editar(c) {
    setEditId(c.id);
    setForm({
      ...VAZIO, ...c,
      data_nascimento: c.data_nascimento || "",
      endereco: { ...VAZIO.endereco, ...(c.endereco || {}) },
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function novo() {
    setEditId(null);
    setForm(VAZIO);
  }

  async function salvar(e) {
    e.preventDefault();
    setMsg(null);
    const body = { ...form, data_nascimento: form.data_nascimento || null };
    try {
      if (editId) await api(`/api/clientes/${editId}`, { method: "PUT", body });
      else await api("/api/clientes", { method: "POST", body });
      setMsg("✓ Cliente salvo.");
      novo();
      carregar();
    } catch (err) {
      setMsg(`Erro: ${err.message}`);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-4">Clientes</h1>

      {/* Formulário */}
      <form onSubmit={salvar} className="bg-white rounded-xl border p-5 mb-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-gray-700">{editId ? "Editar cliente" : "Novo cliente"}</h2>
          {editId && <button type="button" onClick={novo} className="text-sm text-gray-500 hover:underline">+ Novo</button>}
        </div>

        <div className="grid md:grid-cols-3 gap-3 mb-3">
          <div className="md:col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Nome completo *</label>
            <input value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} required className="w-full border rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">CPF</label>
            <input value={form.cpf || ""} onChange={(e) => setForm({ ...form, cpf: e.target.value })} placeholder="000.000.000-00" className="w-full border rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">📱 WhatsApp / Telefone</label>
            <input value={form.telefone || ""} onChange={(e) => setForm({ ...form, telefone: e.target.value })} placeholder="+55 99 99999-0000" className="w-full border rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">E-mail</label>
            <input value={form.email || ""} onChange={(e) => setForm({ ...form, email: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Nascimento</label>
            <input type="date" value={form.data_nascimento || ""} onChange={(e) => setForm({ ...form, data_nascimento: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm" />
          </div>
        </div>

        {/* Endereço (evita confundir homônimos) */}
        <p className="text-xs font-medium text-gray-500 mb-2">Endereço</p>
        <div className="grid md:grid-cols-6 gap-3 mb-3">
          <input value={form.endereco.cep} onChange={(e) => setEnd("cep", e.target.value)} placeholder="CEP" className="border rounded-lg px-3 py-2 text-sm" />
          <input value={form.endereco.logradouro} onChange={(e) => setEnd("logradouro", e.target.value)} placeholder="Logradouro" className="border rounded-lg px-3 py-2 text-sm md:col-span-3" />
          <input value={form.endereco.numero} onChange={(e) => setEnd("numero", e.target.value)} placeholder="Nº" className="border rounded-lg px-3 py-2 text-sm" />
          <input value={form.endereco.complemento} onChange={(e) => setEnd("complemento", e.target.value)} placeholder="Compl." className="border rounded-lg px-3 py-2 text-sm" />
          <input value={form.endereco.bairro} onChange={(e) => setEnd("bairro", e.target.value)} placeholder="Bairro" className="border rounded-lg px-3 py-2 text-sm md:col-span-2" />
          <input value={form.endereco.cidade} onChange={(e) => setEnd("cidade", e.target.value)} placeholder="Cidade" className="border rounded-lg px-3 py-2 text-sm md:col-span-3" />
          <input value={form.endereco.uf} onChange={(e) => setEnd("uf", e.target.value)} placeholder="UF" maxLength={2} className="border rounded-lg px-3 py-2 text-sm" />
        </div>

        <div className="grid md:grid-cols-3 gap-3 mb-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Tom de comunicação</label>
            <select value={form.tom_comunicacao} onChange={(e) => setForm({ ...form, tom_comunicacao: e.target.value })} className="w-full border rounded-lg px-3 py-2 text-sm">
              <option value="formal">Formal</option>
              <option value="informal">Informal</option>
            </select>
          </div>
          <label className="flex items-center gap-2 text-sm text-gray-600 mt-5">
            <input type="checkbox" checked={form.whatsapp_opt_out} onChange={(e) => setForm({ ...form, whatsapp_opt_out: e.target.checked })} />
            Não enviar WhatsApp (opt-out)
          </label>
        </div>
        <textarea value={form.notas || ""} onChange={(e) => setForm({ ...form, notas: e.target.value })} placeholder="Notas internas" rows={2} className="w-full border rounded-lg px-3 py-2 text-sm mb-3" />

        <div className="flex items-center gap-3">
          <button type="submit" className="bg-claudio text-white rounded-lg px-5 py-2 text-sm font-medium hover:bg-claudio-light">
            {editId ? "Salvar alterações" : "Cadastrar cliente"}
          </button>
          {msg && <span className="text-sm text-claudio">{msg}</span>}
        </div>
      </form>

      {/* Busca + lista */}
      <form onSubmit={(e) => { e.preventDefault(); carregar(); }} className="mb-3">
        <input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar por nome ou CPF..." className="w-full md:w-96 border rounded-lg px-3 py-2 text-sm" />
      </form>

      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-left">
            <tr><th className="px-4 py-2">Nome</th><th className="px-4 py-2">CPF</th><th className="px-4 py-2">WhatsApp</th><th className="px-4 py-2">Cidade/UF</th><th className="px-4 py-2"></th></tr>
          </thead>
          <tbody className="divide-y">
            {clientes.length === 0 ? (
              <tr><td colSpan={5} className="px-4 py-6 text-center text-gray-400">Nenhum cliente.</td></tr>
            ) : clientes.map((c) => (
              <tr key={c.id} className="hover:bg-gray-50">
                <td className="px-4 py-2 font-medium">{c.nome}</td>
                <td className="px-4 py-2 text-gray-500">{c.cpf || "—"}</td>
                <td className="px-4 py-2">{c.telefone || "—"}</td>
                <td className="px-4 py-2 text-gray-500">{c.endereco?.cidade ? `${c.endereco.cidade}${c.endereco.uf ? "/" + c.endereco.uf : ""}` : "—"}</td>
                <td className="px-4 py-2 text-right">
                  <button onClick={() => editar(c)} className="text-xs text-claudio hover:underline">editar</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
