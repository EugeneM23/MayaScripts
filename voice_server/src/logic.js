// The pure rules of the voice server: names, rooms, the media header, the
// control messages. No Cloudflare API in here, so `npm test` runs it in Node.
// Mirrors SkeldarAnim/maya_voice/protocol.py - change both together.

export const MAX_MEMBERS = 30;
export const MAX_MESSAGE_BYTES = 2 * 1024 * 1024;
export const NAME_MAX = 24;
export const LOBBY_MAX_AGE_MS = 24 * 60 * 60 * 1000;
const ROOM_RE = /^[a-z0-9][a-z0-9_-]{0,39}$/;
const TYPE_AUDIO = 0x41; // 'A'
const TYPE_VIDEO = 0x56; // 'V'

// The room name as the URL gives it, lowercased, or null when it is not one.
export function validRoom(name) {
  const room = String(name ?? "").toLowerCase();
  return ROOM_RE.test(room) ? room : null;
}

// A display name: whitespace collapsed, at most NAME_MAX characters, never empty.
export function cleanName(name) {
  const text = String(name ?? "").split(/\s+/).filter(Boolean).join(" ");
  const cut = text.slice(0, NAME_MAX).trimEnd();
  return cut || "Guest";
}

// The lowest id no current member has, 1..65535, or null when the room is
// somehow full of ids.
export function freeId(used) {
  for (let id = 1; id <= 65535; id++) {
    if (!used.has(id)) return id;
  }
  return null;
}

// A copy of a media frame with the sender id (bytes 1-2, big endian) set to
// the id the server gave this socket. Null for anything that is not media.
export function stampSender(bytes, id) {
  const view = new Uint8Array(bytes);
  if (view.length < 7) return null;
  if (view[0] !== TYPE_AUDIO && view[0] !== TYPE_VIDEO) return null;
  const out = new Uint8Array(view.length);
  out.set(view);
  out[1] = (id >> 8) & 0xff;
  out[2] = id & 0xff;
  return out;
}

// The control message as an object, or null when it is not one.
export function parseControl(text) {
  let msg;
  try {
    msg = JSON.parse(text);
  } catch (_err) {
    return null;
  }
  if (msg && typeof msg === "object" && typeof msg.t === "string") return msg;
  return null;
}

// What a state message may change: three booleans, nothing else.
export function cleanState(msg) {
  return {
    muted: Boolean(msg.muted),
    deafened: Boolean(msg.deafened),
    sharing: Boolean(msg.sharing),
  };
}

// The public view of one member, as the roster carries it.
export function publicMember(att) {
  return {
    id: att.id,
    name: att.name,
    muted: Boolean(att.muted),
    deafened: Boolean(att.deafened),
    sharing: Boolean(att.sharing),
  };
}

export function welcomeMessage(id, room) {
  return JSON.stringify({ t: "welcome", id, room });
}

export function rosterMessage(members) {
  return JSON.stringify({ t: "roster", members });
}

export function errorMessage(msg) {
  return JSON.stringify({ t: "error", msg });
}

// The lobby's record of one room: its member names, or nothing when empty.
export function lobbyUpdate(rooms, room, names, now) {
  const next = { ...rooms };
  if (!names || names.length === 0) {
    delete next[room];
  } else {
    next[room] = { members: names.slice(), updated: now };
  }
  return next;
}

// The lobby's list for the client: rooms sorted by name, old entries dropped.
export function lobbyList(rooms, now) {
  return Object.entries(rooms)
    .filter(([, v]) => now - (v.updated ?? 0) <= LOBBY_MAX_AGE_MS)
    .map(([room, v]) => ({ room, members: v.members }))
    .sort((a, b) => (a.room < b.room ? -1 : a.room > b.room ? 1 : 0));
}
