import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import fs from "node:fs";
import path from "node:path";

// HTTPS com certificado self-signed — necessário para liberar microfone/câmera quando
// o app é acessado por IP na rede local (o navegador só dá getUserMedia em HTTPS ou localhost).
// Se os certificados existirem em ./certs, serve em HTTPS; senão, cai para HTTP (localhost).
const certDir = path.resolve(process.cwd(), "certs");
const keyFile = path.join(certDir, "key.pem");
const certFile = path.join(certDir, "cert.pem");
const temHttps = fs.existsSync(keyFile) && fs.existsSync(certFile);

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    allowedHosts: true, // permite acesso por IP da rede (teste multiusuário)
    https: temHttps
      ? { key: fs.readFileSync(keyFile), cert: fs.readFileSync(certFile) }
      : undefined,
    // Origem única: o frontend repassa /api e /ws para o backend (rede interna do Docker).
    // Isso elimina CORS e "conteúdo misto", e mantém tudo sob o mesmo HTTPS — o que faz
    // o microfone funcionar para quem acessa pela rede.
    proxy: {
      "/api": { target: "http://backend:8000", changeOrigin: true, secure: false },
      "/ws": { target: "http://backend:8000", changeOrigin: true, ws: true, secure: false },
    },
    // Docker + Windows: inotify não cruza o bind mount, então usa polling para o HMR.
    watch: { usePolling: true, interval: 300 },
  },
});
