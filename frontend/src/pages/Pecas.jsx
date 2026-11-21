import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { marked } from "marked";
import { api, baixarArquivo } from "../lib/api";

export default function Pecas() {
  const [params] = useSearchParams();
  const [docs, setDocs] = useState([]);
  const [atual, setAtual] = useState(null);
  const [conteudo, setConteudo] = useState("");
  const [titulo, setTitulo] = useState("");
  const [preview, setPreview] = useState(false);
  const [msg, setMsg] = useState(null);

  async function carregarLista() {
    const lista = await api("/api/documentos");
    setDocs(lista);
    return lista;
  }

  async function abrir(id) {
    const doc = await api(`/api/documentos/${id}`);
    setAtual(doc);
    setConteudo(doc.conteudo || "");
    setTitulo(doc.titulo || "");
  }

  useEffect(() => {
    carregarLista().then((lista) => {
      const alvo = params.get("doc");
      if (alvo) abrir(Number(alvo));
      else if (lista.length) abrir(lista[0].id);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function salvar() {
    setMsg(null);
    const doc = await api(`/api/documentos/${atual.id}`, {
      method: "PUT",
      body: { titulo, conteudo },
    });
    setAtual(doc);
    setMsg("✓ Salvo.");
    carregarLista();
  }

  async function exportar() {
    await baixarArquivo(`/api/documentos/${atual.id}/pdf`, `${titulo || "documento"}.pdf`);
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-4">Peças</h1>
      <div className="grid md:grid-cols-4 gap-6">
        {/* Lista */}
        <div className="bg-white rounded-xl border p-3 h-fit">
          <h2 className="font-semibold text-gray-700 text-sm px-2 mb-2">Documentos</h2>
          {docs.length === 0 ? (
            <p className="text-gray-400 text-sm px-2">Nenhuma peça. Gere uma pelo chat ou por uma reunião.</p>
          ) : (
            <ul className="space-y-1">
              {docs.map((d) => (
                <li key={d.id}>
                  <button
                    onClick={() => abrir(d.id)}
                    className={`w-full text-left px-2 py-1.5 rounded-lg text-sm ${
                      atual?.id === d.id ? "bg-claudio text-white" : "hover:bg-gray-100"
                    }`}
                  >
                    <span className="block truncate">{d.titulo || `Doc #${d.id}`}</span>
                    {d.gerado_por_ia && (
                      <span className="text-[10px] opacity-70">gerado por IA</span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Editor */}
        <div className="md:col-span-3 bg-white rounded-xl border p-5">
          {!atual ? (
            <p className="text-gray-400">Selecione um documento.</p>
          ) : (
            <>
              <div className="flex items-center justify-between mb-3 gap-3">
                <input
                  value={titulo}
                  onChange={(e) => setTitulo(e.target.value)}
                  className="flex-1 border rounded-lg px-3 py-1.5 text-sm font-medium"
                />
                <div className="flex gap-2">
                  <button onClick={() => setPreview((v) => !v)} className="text-sm border rounded-lg px-3 py-1.5 hover:bg-gray-50">
                    {preview ? "Editar" : "Preview"}
                  </button>
                  <button onClick={salvar} className="bg-claudio text-white rounded-lg px-4 py-1.5 text-sm font-medium hover:bg-claudio-light">
                    Salvar
                  </button>
                  <button onClick={exportar} className="border border-claudio text-claudio rounded-lg px-3 py-1.5 text-sm hover:bg-claudio hover:text-white transition">
                    PDF
                  </button>
                </div>
              </div>
              {msg && <p className="text-sm text-claudio mb-2">{msg}</p>}

              {preview ? (
                <div
                  className="prose prose-sm max-w-none border rounded-lg p-4 min-h-[400px] text-sm"
                  dangerouslySetInnerHTML={{ __html: marked.parse(conteudo || "") }}
                />
              ) : (
                <textarea
                  value={conteudo}
                  onChange={(e) => setConteudo(e.target.value)}
                  rows={22}
                  className="w-full border rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-claudio-light"
                />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
