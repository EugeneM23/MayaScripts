// The two Durable Objects of the voice server.
//
// Room - one per room name. Holds its members in the WebSocket attachments
// (the hibernation API keeps them across restarts), gives each member a
// numeric id, relays media frames to the others, and rebroadcasts the roster.
// Nothing is written to storage.
//
// Lobby - one for the whole server. The rooms report their member names to
// it, and GET /rooms reads the list back.

import {
  MAX_MEMBERS,
  MAX_MESSAGE_BYTES,
  cleanName,
  cleanState,
  errorMessage,
  freeId,
  lobbyList,
  lobbyUpdate,
  parseControl,
  publicMember,
  rosterMessage,
  stampSender,
  welcomeMessage,
} from "./logic.js";

export class Room {
  constructor(state, env) {
    this.state = state;
    this.env = env;
  }

  async fetch(request) {
    if (request.headers.get("Upgrade") !== "websocket") {
      return new Response("expected a WebSocket", { status: 426 });
    }
    const pair = new WebSocketPair();
    const client = pair[0];
    const server = pair[1];
    this.state.acceptWebSocket(server);
    server.serializeAttachment({
      room: request.headers.get("x-room") || "",
      id: null,
      name: "",
      muted: false,
      deafened: false,
      sharing: false,
    });
    return new Response(null, { status: 101, webSocket: client });
  }

  // Sockets that have joined, with their attachments. `except` is left out
  // (a socket that is closing is still listed while its close runs).
  members(except) {
    const out = [];
    for (const ws of this.state.getWebSockets()) {
      if (ws === except) continue;
      const att = ws.deserializeAttachment();
      if (att && att.id != null) out.push({ ws, att });
    }
    return out;
  }

  async webSocketMessage(ws, message) {
    if (typeof message === "string") {
      await this.control(ws, message);
      return;
    }
    const att = ws.deserializeAttachment();
    if (!att || att.id == null) return;
    if (message.byteLength > MAX_MESSAGE_BYTES) return;
    const stamped = stampSender(message, att.id);
    if (!stamped) return;
    for (const { ws: other } of this.members(ws)) {
      if (other !== ws) other.send(stamped);
    }
  }

  async control(ws, text) {
    const msg = parseControl(text);
    if (!msg) {
      ws.send(errorMessage("bad message"));
      return;
    }
    const att = ws.deserializeAttachment();
    if (msg.t === "join") {
      if (att.id != null) return;
      const others = this.members(ws);
      if (others.length >= MAX_MEMBERS) {
        ws.send(errorMessage("room full"));
        return;
      }
      const id = freeId(new Set(others.map((m) => m.att.id)));
      if (id == null) {
        ws.send(errorMessage("room full"));
        return;
      }
      ws.serializeAttachment({ ...att, id, name: cleanName(msg.name) });
      ws.send(welcomeMessage(id, att.room));
      await this.changed(att.room);
    } else if (msg.t === "state") {
      if (att.id == null) return;
      ws.serializeAttachment({ ...att, ...cleanState(msg) });
      await this.changed(att.room);
    }
  }

  async webSocketClose(ws) {
    await this.leave(ws);
  }

  async webSocketError(ws) {
    await this.leave(ws);
  }

  async leave(ws) {
    const att = ws.deserializeAttachment();
    if (!att || att.id == null) return;
    ws.serializeAttachment({ ...att, id: null });
    await this.changed(att.room, ws);
  }

  // Everyone who has joined gets the new roster; the lobby gets the names.
  async changed(room, except) {
    const members = this.members(except);
    const roster = rosterMessage(members.map((m) => publicMember(m.att)));
    for (const { ws } of members) ws.send(roster);
    const names = members.map((m) => m.att.name);
    const update = this.reportLobby(room, names);
    this.state.waitUntil(update);
  }

  reportLobby(room, names) {
    if (!room) return Promise.resolve();
    const stub = this.env.LOBBY.get(this.env.LOBBY.idFromName("lobby"));
    return stub
      .fetch("https://lobby/update", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ room, names }),
      })
      .catch(() => {});
  }
}

export class Lobby {
  constructor(state) {
    this.state = state;
  }

  async fetch(request) {
    const url = new URL(request.url);
    if (url.pathname === "/update" && request.method === "POST") {
      const body = await request.json();
      const rooms = (await this.state.storage.get("rooms")) ?? {};
      const names = Array.isArray(body.names) ? body.names.map(String) : [];
      const next = lobbyUpdate(rooms, String(body.room), names, Date.now());
      await this.state.storage.put("rooms", next);
      return new Response("ok");
    }
    if (url.pathname === "/list") {
      const rooms = (await this.state.storage.get("rooms")) ?? {};
      return Response.json({ rooms: lobbyList(rooms, Date.now()) });
    }
    return new Response("not found", { status: 404 });
  }
}
