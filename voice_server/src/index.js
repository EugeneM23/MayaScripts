// The door of the voice server.
//
//   GET /            a health line
//   GET /rooms       the lobby: [{room, members:[names]}]
//   GET /room/<name> a WebSocket into that room (one Room object per name)

import { validRoom } from "./logic.js";

export { Room, Lobby } from "./room.js";

function lobby(env) {
  return env.LOBBY.get(env.LOBBY.idFromName("lobby"));
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/") {
      return new Response("skeldar voice ok\n");
    }
    if (url.pathname === "/rooms" && request.method === "GET") {
      return lobby(env).fetch("https://lobby/list");
    }
    const match = url.pathname.match(/^\/room\/([^/]+)$/);
    if (!match) {
      return new Response("not found", { status: 404 });
    }
    const room = validRoom(decodeURIComponent(match[1]));
    if (!room) {
      return new Response("bad room name", { status: 400 });
    }
    if (request.headers.get("Upgrade") !== "websocket") {
      return new Response("expected a WebSocket", { status: 426 });
    }
    //  the room's name travels with the request: a Durable Object only
    //  knows its id, and the lobby is keyed by the name
    const headers = new Headers(request.headers);
    headers.set("x-room", room);
    const stub = env.ROOMS.get(env.ROOMS.idFromName(room));
    return stub.fetch(new Request(request, { headers }));
  },
};
