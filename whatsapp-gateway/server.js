"use strict";
/*
 * Gateway WhatsApp do Cláudio — enxuto, baseado em Baileys.
 *
 * Expõe a MESMA API que o backend já espera (ver app/integrations/waakg.py):
 *   POST /api/sessions                         cria sessão {name, sessionId}
 *   POST /api/sessions/:id/:action             start | stop | restart | logout
 *   GET  /api/sessions/:id/qr                  QR {data:{qr, base64}}
 *   GET  /api/sessions/:id                     status {data:{status, me}}
 *   POST /api/messages/:sessionId/:jid/send    envia {message:{text}}
 *   POST /api/chat/:sessionId/:jid/presence    presença {presence}
 *   POST /api/webhooks/:sessionId              registra webhook {url, events}
 *
 * Autenticação por header X-API-Key (vem da env API_KEY — sem painel, sem cadastro).
 * As credenciais da sessão do WhatsApp ficam em /data/auth/<sessionId> (volume).
 * Mensagens recebidas são enviadas ao WEBHOOK_URL (ou ao webhook registrado).
 */
const express = require("express");
const qrcode = require("qrcode");
const pino = require("pino");
const {
  default: makeWASocket,
  useMultiFileAuthState,
  DisconnectReason,
  fetchLatestBaileysVersion,
} = require("@whiskeysockets/baileys");

const PORT = process.env.PORT || 3000;
const API_KEY = process.env.API_KEY || "";
const DEFAULT_WEBHOOK = process.env.WEBHOOK_URL || "";
const AUTH_ROOT = process.env.AUTH_DIR || "/data/auth";

const logger = pino({ level: process.env.LOG_LEVEL || "warn" });
const sessions = {}; // id -> { sock, status, qr, qrBase64, me, webhook, starting, onReady }

async function postWebhook(id, data) {
  const url = sessions[id]?.webhook || DEFAULT_WEBHOOK;
  if (!url) return;
  try {
    await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event: "message.received", sessionId: id, timestamp: Date.now(), data }),
    });
  } catch (e) {
    logger.warn("webhook falhou: " + e.message);
  }
}

async function startSession(id) {
  const s = sessions[id] || (sessions[id] = { status: "Disconnected" });
  if (s.starting) return s;
  if (s.sock && s.status === "Connected") return s;
  s.starting = true;

  const { state, saveCreds } = await useMultiFileAuthState(`${AUTH_ROOT}/${id}`);
  let version;
  try {
    ({ version } = await fetchLatestBaileysVersion());
  } catch (_) {
    /* usa o padrão da lib se estiver offline */
  }

  const sock = makeWASocket({
    version,
    auth: state,
    printQRInTerminal: false,
    browser: ["Claudio", "Chrome", "1.0"],
    logger,
  });
  s.sock = sock;
  s.status = "Connecting";
  s.starting = false;

  sock.ev.on("creds.update", saveCreds);

  sock.ev.on("connection.update", async (u) => {
    const { connection, lastDisconnect, qr } = u;
    if (qr) {
      s.qr = qr;
      s.qrBase64 = await qrcode.toDataURL(qr);
      s.status = "Connecting";
      if (s.onReady) { s.onReady(); s.onReady = null; }
    }
    if (connection === "open") {
      s.status = "Connected";
      s.me = sock.user;
      s.qr = null;
      s.qrBase64 = null;
      logger.warn(`[${id}] conectado como ${sock.user && sock.user.id}`);
      if (s.onReady) { s.onReady(); s.onReady = null; }
    } else if (connection === "close") {
      s.status = "Disconnected";
      const code = lastDisconnect && lastDisconnect.error && lastDisconnect.error.output
        ? lastDisconnect.error.output.statusCode : undefined;
      if (code !== DisconnectReason.loggedOut) {
        setTimeout(() => startSession(id), 2500); // reconecta
      } else {
        logger.warn(`[${id}] deslogado — apague /data/auth/${id} para novo pareamento`);
      }
    }
  });

  sock.ev.on("messages.upsert", async ({ messages, type }) => {
    if (type !== "notify") return;
    for (const m of messages) {
      if (!m.message || (m.key && m.key.fromMe)) continue;
      const text = m.message.conversation || (m.message.extendedTextMessage && m.message.extendedTextMessage.text);
      if (!text) continue;
      await postWebhook(id, { fromMe: false, sender: m.key.remoteJid, content: { text } });
    }
  });

  // Espera o 1º QR (ou conexão) para que o GET /qr logo em seguida já encontre algo.
  await new Promise((resolve) => {
    if (s.qrBase64 || s.status === "Connected") return resolve();
    s.onReady = resolve;
    setTimeout(resolve, 20000);
  });
  return s;
}

const app = express();
app.use(express.json({ limit: "2mb" }));

app.get("/health", (_req, res) => res.json({ ok: true }));

// Autenticação simples por chave de API (sem painel)
app.use("/api", (req, res, next) => {
  if (API_KEY && req.get("X-API-Key") !== API_KEY) {
    return res.status(401).json({ error: "Unauthorized - Invalid or missing API key" });
  }
  next();
});

app.post("/api/sessions", (req, res) => {
  const id = (req.body && (req.body.sessionId || req.body.name)) || "default";
  if (!sessions[id]) sessions[id] = { status: "Disconnected" };
  res.json({ status: sessions[id].status, sessionId: id, name: req.body && req.body.name });
});

app.post("/api/sessions/:id/:action", async (req, res) => {
  const { id, action } = req.params;
  try {
    if (action === "start" || action === "restart") {
      await startSession(id);
    } else if (action === "stop") {
      if (sessions[id] && sessions[id].sock) sessions[id].sock.end(undefined);
      if (sessions[id]) sessions[id].status = "Disconnected";
    } else if (action === "logout") {
      if (sessions[id] && sessions[id].sock) await sessions[id].sock.logout();
      if (sessions[id]) sessions[id].status = "Disconnected";
    }
    res.json({ status: (sessions[id] && sessions[id].status) || "Disconnected", action });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

app.get("/api/sessions/:id/qr", (req, res) => {
  const s = sessions[req.params.id];
  if (!s) return res.status(404).json({ error: "QR not available yet" });
  if (s.status === "Connected") return res.status(400).json({ error: "Already connected" });
  if (!s.qrBase64) return res.status(404).json({ error: "QR not available yet" });
  res.json({ data: { qr: s.qr, base64: s.qrBase64 } });
});

app.get("/api/sessions/:id", (req, res) => {
  const s = sessions[req.params.id] || { status: "Disconnected" };
  res.json({ data: { status: s.status, me: s.me || null, hasInstance: !!s.sock } });
});

app.get("/api/sessions", (_req, res) => {
  res.json({ data: Object.keys(sessions).map((id) => ({ sessionId: id, status: sessions[id].status })) });
});

app.post("/api/messages/:sessionId/:jid/send", async (req, res) => {
  const s = sessions[req.params.sessionId];
  if (!s || !s.sock || s.status !== "Connected") {
    return res.status(409).json({ status: false, error: "Sessão não conectada" });
  }
  const text = req.body && req.body.message && req.body.message.text;
  if (!text) return res.status(400).json({ status: false, error: "message.text obrigatório" });
  try {
    const r = await s.sock.sendMessage(req.params.jid, { text });
    res.json({ status: true, data: { key: r.key } });
  } catch (e) {
    res.status(500).json({ status: false, error: e.message });
  }
});

app.post("/api/chat/:sessionId/:jid/presence", async (req, res) => {
  const s = sessions[req.params.sessionId];
  if (!s || !s.sock) return res.status(409).json({ status: false, error: "Sessão não conectada" });
  try {
    await s.sock.sendPresenceUpdate((req.body && req.body.presence) || "composing", req.params.jid);
    res.json({ status: true });
  } catch (e) {
    res.json({ status: false, error: e.message });
  }
});

app.post("/api/webhooks/:sessionId", (req, res) => {
  const id = req.params.sessionId;
  const s = sessions[id] || (sessions[id] = { status: "Disconnected" });
  s.webhook = req.body && req.body.url;
  res.json({ status: true, url: s.webhook, events: (req.body && req.body.events) || [] });
});

app.listen(PORT, () => logger.warn(`Cláudio WA gateway ouvindo na porta ${PORT}`));
