const WebSocket = require("ws");
const wss = new WebSocket.Server({ host: '0.0.0.0', port: 8080 });

/** Track room membership */
const meta = new Map(); // ws -> { room, role }

function send(ws, obj) {
  if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
}

wss.on("connection", (ws) => {
  meta.set(ws, { room: null, role: null });

  ws.on("message", (raw) => {
    let msg;
    try { msg = JSON.parse(raw); } catch { return; }

    if (msg.type === "join") {
      meta.set(ws, { room: msg.room, role: msg.role || null });

      // Notify others in the same room that a peer joined (useful if sender waits)
      wss.clients.forEach((c) => {
        if (c !== ws && c.readyState === WebSocket.OPEN) {
          const info = meta.get(c);
          if (info?.room === msg.room) send(c, { type: "peer-joined", role: meta.get(ws).role });
        }
      });
      return;
    }

    // Route any other message to peers in the same room
    const src = meta.get(ws);
    if (!src?.room) return;

    wss.clients.forEach((c) => {
      if (c !== ws && c.readyState === WebSocket.OPEN) {
        const info = meta.get(c);
        if (info?.room === src.room) c.send(JSON.stringify(msg));
      }
    });
  });

  ws.on("close", () => {
    const src = meta.get(ws);
    wss.clients.forEach((c) => {
      if (c !== ws && c.readyState === WebSocket.OPEN) {
        const info = meta.get(c);
        if (info?.room === src?.room) send(c, { type: "peer-left" });
      }
    });
    meta.delete(ws);
  });
});

console.log("✅ Signaling server on ws://0.0.0.0:8080");
