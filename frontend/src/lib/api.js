// Cliente HTTP minimalista com refresh automático de token.
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function getTokens() {
  return {
    access: localStorage.getItem("access_token"),
    refresh: localStorage.getItem("refresh_token"),
  };
}

export function setTokens({ access, refresh }) {
  if (access) localStorage.setItem("access_token", access);
  if (refresh) localStorage.setItem("refresh_token", refresh);
}

export function clearTokens() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

async function refreshAccess() {
  const { refresh } = getTokens();
  if (!refresh) throw new Error("sem refresh token");
  const resp = await fetch(`${API_URL}/api/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!resp.ok) throw new Error("refresh falhou");
  const data = await resp.json();
  setTokens({ access: data.access_token });
  return data.access_token;
}

export async function api(path, { method = "GET", body, sensitive, retry = true } = {}) {
  const { access } = getTokens();
  const headers = { "Content-Type": "application/json" };
  if (access) headers["Authorization"] = `Bearer ${access}`;
  if (sensitive) headers["X-Sensitive-Token"] = sensitive;

  const resp = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (resp.status === 401 && retry) {
    try {
      await refreshAccess();
      return api(path, { method, body, sensitive, retry: false });
    } catch {
      clearTokens();
      window.location.href = "/login";
      return;
    }
  }

  if (!resp.ok) {
    const erro = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(erro.detail || "Erro na requisição");
  }
  if (resp.status === 204) return null;
  return resp.json();
}

// --- Token sensível (financeiro / dashboard dono) ---
export function getSensitiveToken() {
  const raw = sessionStorage.getItem("sensitive");
  if (!raw) return null;
  try {
    const { token, exp } = JSON.parse(raw);
    if (Date.now() > exp) {
      sessionStorage.removeItem("sensitive");
      return null;
    }
    return token;
  } catch {
    return null;
  }
}

export function setSensitiveToken(token) {
  // validade ~30min (alinhada ao backend)
  sessionStorage.setItem("sensitive", JSON.stringify({ token, exp: Date.now() + 29 * 60 * 1000 }));
}

export async function desbloquearSensivel(senha) {
  const data = await api("/api/auth/verify-sensitive", {
    method: "POST",
    body: { senha_sensivel: senha },
  });
  setSensitiveToken(data.sensitive_token);
  return data.sensitive_token;
}

export function wsUrl() {
  const { access } = getTokens();
  const base = API_URL.replace(/^http/, "ws");
  return `${base}/ws/chat?token=${access}`;
}

// URL autenticada por token na query (para <audio>/<img> que não mandam header)
export function authedUrl(path) {
  const { access } = getTokens();
  const sep = path.includes("?") ? "&" : "?";
  return `${API_URL}${path}${sep}token=${access}`;
}

// Baixa um arquivo (ex: PDF) respeitando o Authorization e dispara o download.
export async function baixarArquivo(path, nomeArquivo) {
  const { access } = getTokens();
  const resp = await fetch(`${API_URL}${path}`, {
    headers: access ? { Authorization: `Bearer ${access}` } : {},
  });
  if (!resp.ok) throw new Error("Falha ao baixar arquivo");
  const blob = await resp.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = nomeArquivo;
  a.click();
  URL.revokeObjectURL(url);
}

export { API_URL };
