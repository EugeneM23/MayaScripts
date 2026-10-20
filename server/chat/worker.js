// The Skeldar chat server: one Worker, one SQLite Durable Object "Studio" holding the whole studio.
// Spec: docs/superpowers/specs/2026-10-19-chat-messenger-design.md
import { DurableObject } from "cloudflare:workers";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (!url.pathname.startsWith("/v1/")) return json({ error: "not_found", text: "No such address" }, 404);
    const stub = env.STUDIO.get(env.STUDIO.idFromName("studio"));
    return stub.fetch(request);
  },
};

const NICK = /^[a-z0-9_]{3,24}$/;
const RESERVED = new Set(["admin", "skeldar", "system", "support", "root", "chat", "null", "undefined"]);
const DAY = 86400000;
const KEEP_EVENTS = 30 * DAY;
const TEXT_MAX = 4000;
const NAME_MAX = 40;
const GROUP_NAME_MAX = 60;
const GROUP_MAX = 50;
const AVATAR_MAX = 256 * 1024;

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status, headers: { "content-type": "application/json; charset=utf-8" },
  });
}

class Refusal extends Error {
  constructor(code, text, status) { super(text); this.code = code; this.status = status; }
}
function refuse(code, text, status = 400) { throw new Refusal(code, text, status); }

function hex(bytes) { return [...bytes].map((b) => b.toString(16).padStart(2, "0")).join(""); }
function randomHex(n) { const b = new Uint8Array(n); crypto.getRandomValues(b); return hex(b); }
function b64url(bytes) {
  return btoa(String.fromCharCode(...bytes)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
async function sha256(text) {
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return hex(new Uint8Array(d));
}
function clean(text, most) { return String(text ?? "").replace(/\s+$/u, "").replace(/^\s+/u, "").slice(0, most); }

const SCHEMA = [
  `CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, nick TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
     token_hash TEXT UNIQUE NOT NULL, avatar BLOB, avatar_type TEXT, avatar_v INTEGER NOT NULL DEFAULT 0,
     created INTEGER NOT NULL, last_seen INTEGER NOT NULL DEFAULT 0)`,
  `CREATE TABLE IF NOT EXISTS friends (a TEXT NOT NULL, b TEXT NOT NULL, since INTEGER NOT NULL, PRIMARY KEY (a, b))`,
  `CREATE TABLE IF NOT EXISTS requests (from_id TEXT NOT NULL, to_id TEXT NOT NULL, at INTEGER NOT NULL,
     PRIMARY KEY (from_id, to_id))`,
  `CREATE TABLE IF NOT EXISTS chats (id TEXT PRIMARY KEY, kind TEXT NOT NULL, name TEXT NOT NULL DEFAULT '',
     admin TEXT, avatar BLOB, avatar_type TEXT, avatar_v INTEGER NOT NULL DEFAULT 0, created INTEGER NOT NULL,
     last_seq INTEGER NOT NULL DEFAULT 0)`,
  `CREATE TABLE IF NOT EXISTS members (chat TEXT NOT NULL, uid TEXT NOT NULL, joined INTEGER NOT NULL,
     read_upto INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (chat, uid))`,
  `CREATE INDEX IF NOT EXISTS members_uid ON members (uid)`,
  `CREATE TABLE IF NOT EXISTS messages (chat TEXT NOT NULL, seq INTEGER NOT NULL, id TEXT UNIQUE NOT NULL,
     from_id TEXT NOT NULL, cid TEXT NOT NULL, text TEXT NOT NULL, reply_to TEXT, at INTEGER NOT NULL,
     edited_at INTEGER, deleted INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (chat, seq))`,
  `CREATE UNIQUE INDEX IF NOT EXISTS messages_cid ON messages (from_id, cid)`,
  `CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY AUTOINCREMENT, chat TEXT, uid TEXT,
     kind TEXT NOT NULL, payload TEXT NOT NULL, at INTEGER NOT NULL)`,
  `CREATE INDEX IF NOT EXISTS events_at ON events (at)`,
];

export class Studio extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.sql = ctx.storage.sql;
    for (const statement of SCHEMA) this.sql.exec(statement);
    this.hits = new Map();
    ctx.setWebSocketAutoResponse(new WebSocketRequestResponsePair("ping", "pong"));
    ctx.blockConcurrencyWhile(async () => {
      if ((await ctx.storage.getAlarm()) == null) await ctx.storage.setAlarm(Date.now() + DAY);
    });
  }

  async fetch(request) {
    const url = new URL(request.url);
    try {
      const found = this.route(request.method, url.pathname);
      if (!found) refuse("not_found", "No such address", 404);
      const [handler, params, open] = found;
      const me = open ? null : await this.auth(request);
      if (me) this.limit(me.id + ":http", 30);
      return await handler.call(this, { request, url, params, me });
    } catch (e) {
      if (e instanceof Refusal) return json({ error: e.code, text: e.message }, e.status);
      return json({ error: "server", text: "The server failed: " + e.message }, 500);
    }
  }

  route(method, path) {
    for (const [m, pattern, name, open] of ROUTES) {
      if (m !== method) continue;
      const hit = path.match(pattern);
      if (hit) return [this[name], hit.slice(1), !!open];
    }
    return null;
  }

  async auth(request) {
    const header = request.headers.get("authorization") || "";
    const token = header.startsWith("Bearer ") ? header.slice(7).trim() : "";
    if (!token) refuse("bad_token", "Sign in first", 401);
    const row = this.sql.exec("SELECT * FROM users WHERE token_hash = ?", await sha256(token)).toArray()[0];
    if (!row) refuse("bad_token", "This sign-in code is not valid", 401);
    return row;
  }

  limit(key, most) {
    const now = Date.now();
    const recent = (this.hits.get(key) || []).filter((t) => now - t < 10000);
    if (recent.length >= most) refuse("too_many", "Too fast - wait a few seconds", 429);
    recent.push(now);
    this.hits.set(key, recent);
  }

  async body(request) {
    try { return await request.json(); } catch { refuse("bad_request", "The request is not JSON"); }
  }

  user(row) { return { id: row.id, nick: row.nick, name: row.name, avatar_v: row.avatar_v }; }

  userById(id) {
    const row = this.sql.exec("SELECT * FROM users WHERE id = ?", id).toArray()[0];
    if (!row) refuse("no_user", "No such person", 404);
    return row;
  }

  // ---------------------------------------------------------------- events
  // An event goes to a chat's members (chat), one user (uid), or everybody (neither).
  emit({ chat = null, uid = null, kind, payload }) {
    const row = this.sql.exec(
      "INSERT INTO events (chat, uid, kind, payload, at) VALUES (?, ?, ?, ?, ?) RETURNING seq",
      chat, uid, kind, JSON.stringify(payload), Date.now()).one();
    const event = { seq: row.seq, kind, ...payload };
    if (chat) this.deliver(event, this.memberIds(chat));
    else if (uid) this.deliver(event, [uid]);
    else this.deliver(event, null);
    return row.seq;
  }

  deliver(event, uids) {
    const text = JSON.stringify(event);
    const sockets = uids === null ? this.ctx.getWebSockets() : [...new Set(uids)].flatMap((u) => this.ctx.getWebSockets(u));
    for (const ws of sockets) { try { ws.send(text); } catch { /* a closing socket */ } }
  }

  memberIds(chat) { return this.sql.exec("SELECT uid FROM members WHERE chat = ?", chat).toArray().map((r) => r.uid); }

  friendIds(uid) {
    return this.sql.exec("SELECT b AS id FROM friends WHERE a = ? UNION SELECT a AS id FROM friends WHERE b = ?", uid, uid)
      .toArray().map((r) => r.id);
  }

  presence(uid) {
    const row = this.sql.exec("SELECT last_seen FROM users WHERE id = ?", uid).toArray()[0];
    return { online: this.ctx.getWebSockets(uid).length > 0, last_seen: row ? row.last_seen : 0 };
  }

  async alarm() {
    this.sql.exec("DELETE FROM events WHERE at < ?", Date.now() - KEEP_EVENTS);
    await this.ctx.storage.setAlarm(Date.now() + DAY);
  }

  // ---------------------------------------------------------------- routes: sign-in
  health() { return json({ ok: true }); }

  async register({ request }) {
    this.limit("ip:" + (request.headers.get("cf-connecting-ip") || "?"), 20);
    const b = await this.body(request);
    const nick = String(b.nick ?? "").trim().toLowerCase();
    if (!NICK.test(nick)) refuse("bad_nick", "A nick is 3-24 letters a-z, digits or _");
    if (RESERVED.has(nick) || this.sql.exec("SELECT 1 FROM users WHERE nick = ?", nick).toArray().length) {
      refuse("nick_taken", "@" + nick + " is taken", 409);
    }
    const bytes = new Uint8Array(32);
    crypto.getRandomValues(bytes);
    const token = "skc_" + b64url(bytes);
    const id = randomHex(8);
    const name = clean(b.name, NAME_MAX) || nick;
    this.sql.exec("INSERT INTO users (id, nick, name, token_hash, created) VALUES (?, ?, ?, ?, ?)",
      id, nick, name, await sha256(token), Date.now());
    return json({ token, user: { id, nick, name, avatar_v: 0 } });
  }

  getMe({ me }) { return json(this.user(me)); }

  deleteMe({ me }) {
    this.forget(me.id);
    return json({ ok: true });
  }

  forget(uid) {
    for (const ws of this.ctx.getWebSockets(uid)) { try { ws.close(1000, "account deleted"); } catch { /* gone */ } }
    for (const r of this.sql.exec("SELECT chat FROM members WHERE uid = ?", uid).toArray()) this.leave(r.chat, uid);
    this.sql.exec("DELETE FROM friends WHERE a = ? OR b = ?", uid, uid);
    this.sql.exec("DELETE FROM requests WHERE from_id = ? OR to_id = ?", uid, uid);
    this.sql.exec("DELETE FROM users WHERE id = ?", uid);
  }

  // ---------------------------------------------------------------- routes: profile
  async patchMe({ request, me }) {
    const b = await this.body(request);
    const name = clean(b.name, NAME_MAX);
    if (!name) refuse("bad_name", "A name cannot be empty");
    this.sql.exec("UPDATE users SET name = ? WHERE id = ?", name, me.id);
    const user = this.user(this.userById(me.id));
    this.emit({ kind: "user", payload: { user } });
    return json(user);
  }

  async picture(request) {
    const bytes = new Uint8Array(await request.arrayBuffer());
    if (bytes.length > AVATAR_MAX) refuse("too_big", "A picture is at most 256 KB", 413);
    if (bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) return { bytes, type: "image/jpeg" };
    if (bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4e && bytes[3] === 0x47) return { bytes, type: "image/png" };
    refuse("bad_picture", "A picture is a JPEG or a PNG");
  }

  servePicture(bytes, type) {
    if (!bytes) refuse("no_picture", "No picture", 404);
    return new Response(bytes, { headers: { "content-type": type, "cache-control": "private, max-age=31536000" } });
  }

  async putMyAvatar({ request, me }) {
    const { bytes, type } = await this.picture(request);
    this.sql.exec("UPDATE users SET avatar = ?, avatar_type = ?, avatar_v = avatar_v + 1 WHERE id = ?", bytes, type, me.id);
    const user = this.user(this.userById(me.id));
    this.emit({ kind: "user", payload: { user } });
    return json(user);
  }

  userAvatar({ params }) {
    const row = this.userById(params[0]);
    return this.servePicture(row.avatar, row.avatar_type);
  }

  // ---------------------------------------------------------------- routes: friends
  areFriends(a, b) {
    const [x, y] = a < b ? [a, b] : [b, a];
    return this.sql.exec("SELECT 1 FROM friends WHERE a = ? AND b = ?", x, y).toArray().length > 0;
  }

  relation(me, other) {
    if (this.areFriends(me, other)) return "friend";
    if (this.sql.exec("SELECT 1 FROM requests WHERE from_id = ? AND to_id = ?", other, me).toArray().length) return "incoming";
    if (this.sql.exec("SELECT 1 FROM requests WHERE from_id = ? AND to_id = ?", me, other).toArray().length) return "outgoing";
    return null;
  }

  withPresence(row) { return { ...this.user(row), ...this.presence(row.id) }; }

  searchUsers({ url, me }) {
    const q = String(url.searchParams.get("q") || "").trim().toLowerCase().replace(/^@/, "");
    if (q.length < 1) return json({ users: [] });
    const like = q.replace(/[\\%_]/g, (c) => "\\" + c) + "%";
    const rows = this.sql.exec("SELECT * FROM users WHERE nick LIKE ? ESCAPE '\\' AND id != ? ORDER BY nick LIMIT 20", like, me.id).toArray();
    return json({ users: rows.map((r) => ({ ...this.user(r), relation: this.relation(me.id, r.id) })) });
  }

  // Everybody in the studio but me: who they are, whether they are online, and how they stand to me.
  people({ me }) {
    const rows = this.sql.exec("SELECT * FROM users WHERE id != ? ORDER BY nick LIMIT 2000", me.id).toArray();
    return json({ users: rows.map((r) => ({ ...this.withPresence(r), relation: this.relation(me.id, r.id) })) });
  }

  friends({ me }) {
    const pick = (sql, ...args) => this.sql.exec(sql, ...args).toArray().map((r) => this.withPresence(r));
    return json({
      friends: this.friendIds(me.id).map((id) => this.withPresence(this.userById(id))),
      incoming: pick("SELECT u.* FROM requests r JOIN users u ON u.id = r.from_id WHERE r.to_id = ? ORDER BY r.at", me.id),
      outgoing: pick("SELECT u.* FROM requests r JOIN users u ON u.id = r.to_id WHERE r.from_id = ? ORDER BY r.at", me.id),
    });
  }

  befriend(a, b) {
    const [x, y] = a < b ? [a, b] : [b, a];
    this.sql.exec("DELETE FROM requests WHERE (from_id = ? AND to_id = ?) OR (from_id = ? AND to_id = ?)", a, b, b, a);
    this.sql.exec("INSERT OR IGNORE INTO friends (a, b, since) VALUES (?, ?, ?)", x, y, Date.now());
    this.emit({ uid: a, kind: "friend_added", payload: { user: this.withPresence(this.userById(b)) } });
    this.emit({ uid: b, kind: "friend_added", payload: { user: this.withPresence(this.userById(a)) } });
  }

  async requestFriend({ request, me }) {
    const b = await this.body(request);
    const nick = String(b.nick ?? "").trim().toLowerCase().replace(/^@/, "");
    const other = this.sql.exec("SELECT * FROM users WHERE nick = ?", nick).toArray()[0];
    if (!other) refuse("no_user", "Nobody is called @" + nick, 404);
    if (other.id === me.id) refuse("self", "That is you");
    const rel = this.relation(me.id, other.id);
    if (rel === "friend") return json({ state: "friends" });
    if (rel === "incoming") { this.befriend(me.id, other.id); return json({ state: "friends" }); }
    if (rel !== "outgoing") {
      this.sql.exec("INSERT INTO requests (from_id, to_id, at) VALUES (?, ?, ?)", me.id, other.id, Date.now());
      this.emit({ uid: other.id, kind: "friend_request", payload: { user: this.withPresence(me) } });
      this.emit({ uid: me.id, kind: "request_sent", payload: { user: this.withPresence(other) } });
    }
    return json({ state: "requested" });
  }

  async answerRequest({ request, me, params }) {
    const b = await this.body(request);
    const other = this.userById(String(b.user ?? ""));
    const action = params[0];
    const [from, to] = action === "cancel" ? [me.id, other.id] : [other.id, me.id];
    if (!this.sql.exec("SELECT 1 FROM requests WHERE from_id = ? AND to_id = ?", from, to).toArray().length) {
      refuse("no_request", "There is no such request", 404);
    }
    if (action === "accept") { this.befriend(me.id, other.id); return json({ ok: true }); }
    this.sql.exec("DELETE FROM requests WHERE from_id = ? AND to_id = ?", from, to);
    for (const uid of [from, to]) this.emit({ uid, kind: "request_cancelled", payload: { from_id: from, to_id: to } });
    return json({ ok: true });
  }

  unfriend({ me, params }) {
    const other = this.userById(params[0]);
    const [x, y] = me.id < other.id ? [me.id, other.id] : [other.id, me.id];
    this.sql.exec("DELETE FROM friends WHERE a = ? AND b = ?", x, y);
    this.emit({ uid: me.id, kind: "friend_removed", payload: { user_id: other.id } });
    this.emit({ uid: other.id, kind: "friend_removed", payload: { user_id: me.id } });
    return json({ ok: true });
  }

  // ---------------------------------------------------------------- routes: chats
  chatRow(id) {
    const row = this.sql.exec("SELECT * FROM chats WHERE id = ?", id).toArray()[0];
    if (!row) refuse("no_chat", "No such chat", 404);
    return row;
  }

  member(chat, uid) {
    const row = this.sql.exec("SELECT * FROM members WHERE chat = ? AND uid = ?", chat, uid).toArray()[0];
    if (!row) refuse("not_member", "You are not in this chat", 403);
    return row;
  }

  messageView(r) {
    return { id: r.id, chat: r.chat, seq: r.seq, from_id: r.from_id, cid: r.cid,
             text: r.deleted ? "" : r.text, reply_to: r.reply_to, at: r.at, edited_at: r.edited_at, deleted: !!r.deleted };
  }

  shared(chat) {
    const row = this.chatRow(chat);
    const members = this.sql.exec(
      "SELECT u.*, m.joined FROM members m JOIN users u ON u.id = m.uid WHERE m.chat = ? ORDER BY m.joined, u.nick", chat)
      .toArray().map((r) => ({ ...this.withPresence(r), joined: r.joined }));
    return { id: row.id, kind: row.kind, name: row.name, admin: row.admin, avatar_v: row.avatar_v, members };
  }

  view(chat, uid) {
    const mine = this.member(chat, uid);
    const last = this.sql.exec("SELECT * FROM messages WHERE chat = ? ORDER BY seq DESC LIMIT 1", chat).toArray()[0];
    const unread = this.sql.exec(
      "SELECT COUNT(*) AS n FROM messages WHERE chat = ? AND seq > ? AND from_id != ? AND deleted = 0",
      chat, mine.read_upto, uid).one().n;
    return { ...this.shared(chat), last: last ? this.messageView(last) : null, unread, read_upto: mine.read_upto };
  }

  chats({ me }) {
    const ids = this.sql.exec("SELECT chat FROM members WHERE uid = ?", me.id).toArray().map((r) => r.chat);
    const seq = this.sql.exec("SELECT COALESCE(MAX(seq), 0) AS s FROM events").one().s;
    return json({ seq, chats: ids.map((id) => this.view(id, me.id)) });
  }

  addMember(chat, uid) {
    this.sql.exec("INSERT OR IGNORE INTO members (chat, uid, joined) VALUES (?, ?, ?)", chat, uid, Date.now());
  }

  async createChat({ request, me }) {
    const b = await this.body(request);
    if (b.kind === "dm") {
      const other = this.userById(String(b.with ?? ""));
      if (other.id === me.id) refuse("self", "That is you");
      if (!this.areFriends(me.id, other.id)) refuse("not_friend", "Add them as a friend first", 403);
      const id = "dm_" + [me.id, other.id].sort().join("_");
      if (!this.sql.exec("SELECT 1 FROM chats WHERE id = ?", id).toArray().length) {
        this.sql.exec("INSERT INTO chats (id, kind, created) VALUES (?, 'dm', ?)", id, Date.now());
        this.addMember(id, me.id);
        this.addMember(id, other.id);
        this.emit({ chat: id, kind: "chat", payload: { chat: this.shared(id) } });
      }
      return json(this.view(id, me.id));
    }
    if (b.kind !== "group") refuse("bad_request", "A chat is a dm or a group");
    const name = clean(b.name, GROUP_NAME_MAX);
    if (!name) refuse("bad_name", "Name the group");
    const others = [...new Set((b.members || []).map(String))].filter((id) => id !== me.id);
    if (others.length + 1 > GROUP_MAX) refuse("too_big", "A group holds at most " + GROUP_MAX + " people", 413);
    for (const id of others) {
      this.userById(id);
      if (!this.areFriends(me.id, id)) refuse("not_friend", "Only friends can be added", 403);
    }
    const id = "g_" + randomHex(8);
    this.sql.exec("INSERT INTO chats (id, kind, name, admin, created) VALUES (?, 'group', ?, ?, ?)", id, name, me.id, Date.now());
    this.addMember(id, me.id);
    for (const uid of others) this.addMember(id, uid);
    this.emit({ chat: id, kind: "chat", payload: { chat: this.shared(id) } });
    return json(this.view(id, me.id));
  }

  adminOf(chatId, me) {
    const row = this.chatRow(chatId);
    this.member(chatId, me.id);
    if (row.kind !== "group") refuse("not_group", "Only a group has an admin");
    if (row.admin !== me.id) refuse("not_admin", "Only the group's admin can do that", 403);
    return row;
  }

  async patchChat({ request, me, params }) {
    this.adminOf(params[0], me);
    const name = clean((await this.body(request)).name, GROUP_NAME_MAX);
    if (!name) refuse("bad_name", "Name the group");
    this.sql.exec("UPDATE chats SET name = ? WHERE id = ?", name, params[0]);
    this.emit({ chat: params[0], kind: "chat", payload: { chat: this.shared(params[0]) } });
    return json(this.view(params[0], me.id));
  }

  async putChatAvatar({ request, me, params }) {
    this.adminOf(params[0], me);
    const { bytes, type } = await this.picture(request);
    this.sql.exec("UPDATE chats SET avatar = ?, avatar_type = ?, avatar_v = avatar_v + 1 WHERE id = ?", bytes, type, params[0]);
    this.emit({ chat: params[0], kind: "chat", payload: { chat: this.shared(params[0]) } });
    return json(this.view(params[0], me.id));
  }

  chatAvatar({ me, params }) {
    this.member(params[0], me.id);
    const row = this.chatRow(params[0]);
    return this.servePicture(row.avatar, row.avatar_type);
  }

  async postMember({ request, me, params }) {
    const chat = params[0];
    this.adminOf(chat, me);
    const user = this.userById(String((await this.body(request)).user ?? ""));
    if (!this.areFriends(me.id, user.id)) refuse("not_friend", "Only friends can be added", 403);
    if (this.memberIds(chat).length >= GROUP_MAX) refuse("too_big", "A group holds at most " + GROUP_MAX + " people", 413);
    this.addMember(chat, user.id);
    this.emit({ chat, kind: "member_added", payload: { chat_id: chat, user: this.withPresence(user) } });
    this.emit({ chat, kind: "chat", payload: { chat: this.shared(chat) } });
    return json(this.view(chat, me.id));
  }

  leave(chat, uid) {
    const row = this.chatRow(chat);
    let admin = row.admin;
    if (admin === uid) {
      const next = this.sql.exec("SELECT uid FROM members WHERE chat = ? AND uid != ? ORDER BY joined LIMIT 1", chat, uid).toArray()[0];
      admin = next ? next.uid : null;
      this.sql.exec("UPDATE chats SET admin = ? WHERE id = ?", admin, chat);
    }
    this.emit({ chat, kind: "member_removed", payload: { chat_id: chat, user_id: uid, admin } });
    this.sql.exec("DELETE FROM members WHERE chat = ? AND uid = ?", chat, uid);
    if (!this.memberIds(chat).length) {
      this.sql.exec("DELETE FROM messages WHERE chat = ?", chat);
      this.sql.exec("DELETE FROM chats WHERE id = ?", chat);
    }
  }

  deleteMember({ me, params }) {
    const [chat, uid] = params;
    const row = this.chatRow(chat);
    this.member(chat, me.id);
    if (row.kind !== "group") refuse("not_group", "A dm cannot be left");
    if (uid !== me.id && row.admin !== me.id) refuse("not_admin", "Only the group's admin can do that", 403);
    this.member(chat, uid);
    this.leave(chat, uid);
    return json({ ok: true });
  }

  history({ url, me, params }) {
    this.member(params[0], me.id);
    const before = Number(url.searchParams.get("before")) || Number.MAX_SAFE_INTEGER;
    const limit = Math.max(1, Math.min(100, Number(url.searchParams.get("limit")) || 50));
    const rows = this.sql.exec("SELECT * FROM messages WHERE chat = ? AND seq < ? ORDER BY seq DESC LIMIT ?",
      params[0], before, limit).toArray();
    return json({ messages: rows.reverse().map((r) => this.messageView(r)) });
  }

  // ---------------------------------------------------------------- the live connection
  connect({ request, me }) {
    if ((request.headers.get("upgrade") || "").toLowerCase() !== "websocket") refuse("bad_request", "This address is a WebSocket");
    const pair = new WebSocketPair();
    const [client, server] = Object.values(pair);
    const wasOnline = this.ctx.getWebSockets(me.id).length > 0;
    this.ctx.acceptWebSocket(server, [me.id]);
    server.serializeAttachment({ uid: me.id });
    if (!wasOnline) this.announce(me.id, true);
    return new Response(null, { status: 101, webSocket: client });
  }

  announce(uid, online) {
    const row = this.userById(uid);
    // Everybody online hears it: the People list shows the whole studio, not only friends.
    this.deliver({ kind: "presence", user_id: uid, online, last_seen: row.last_seen }, null);
  }

  async webSocketMessage(ws, raw) {
    const { uid } = ws.deserializeAttachment() || {};
    let msg = {};
    try {
      msg = JSON.parse(typeof raw === "string" ? raw : new TextDecoder().decode(raw));
      const me = this.userById(uid);
      const handler = { hello: this.onHello, send: this.onSend, edit: this.onEdit, delete: this.onDelete,
                        read: this.onRead, typing: this.onTyping }[msg.type];
      if (!handler) refuse("bad_request", "Unknown message " + msg.type);
      handler.call(this, ws, me, msg);
    } catch (e) {
      const code = e instanceof Refusal ? e.code : "server";
      const text = e instanceof Refusal ? e.message : "The server failed: " + e.message;
      try { ws.send(JSON.stringify({ kind: "error", cid: msg.cid ?? null, code, text })); } catch { /* gone */ }
    }
  }

  webSocketClose(ws) {
    const { uid } = ws.deserializeAttachment() || {};
    try { ws.close(1000, "bye"); } catch { /* already closed */ }
    if (!uid) return;
    const others = this.ctx.getWebSockets(uid).filter((s) => s !== ws && s.readyState === WebSocket.OPEN);
    if (!others.length && this.sql.exec("SELECT 1 FROM users WHERE id = ?", uid).toArray().length) {
      this.sql.exec("UPDATE users SET last_seen = ? WHERE id = ?", Date.now(), uid);
      this.announce(uid, false);
    }
  }

  webSocketError(ws) { this.webSocketClose(ws); }

  onHello(ws, me, msg) {
    const since = Number(msg.since) || 0;
    const oldest = this.sql.exec("SELECT MIN(seq) AS s FROM events").one().s;
    const newest = this.sql.exec("SELECT COALESCE(MAX(seq), 0) AS s FROM events").one().s;
    if (since <= 0 || (oldest != null && since < oldest - 1)) {
      ws.send(JSON.stringify({ kind: "resync" }));
    } else {
      let after = since;
      for (;;) {
        const rows = this.sql.exec(
          `SELECT * FROM events WHERE seq > ? AND (uid = ? OR (uid IS NULL AND chat IS NULL)
             OR chat IN (SELECT chat FROM members WHERE uid = ?)) ORDER BY seq LIMIT 500`, after, me.id, me.id).toArray();
        for (const r of rows) ws.send(JSON.stringify({ seq: r.seq, kind: r.kind, ...JSON.parse(r.payload) }));
        if (rows.length < 500) break;
        after = rows[rows.length - 1].seq;
      }
    }
    ws.send(JSON.stringify({ kind: "caught_up", seq: newest }));
  }

  writable(chat, me) {
    const row = this.chatRow(chat);
    this.member(chat, me.id);
    if (row.kind === "dm") {
      const other = this.memberIds(chat).find((id) => id !== me.id);
      if (!other || !this.areFriends(me.id, other)) refuse("not_friend", "You are no longer friends", 403);
    }
    return row;
  }

  text(raw) {
    const text = String(raw ?? "").replace(/^\s+|\s+$/gu, "");
    if (!text) refuse("empty", "An empty message");
    if (text.length > TEXT_MAX) refuse("too_long", "A message is at most " + TEXT_MAX + " characters");
    return text;
  }

  onSend(ws, me, msg) {
    const cid = String(msg.cid ?? "");
    if (!cid || cid.length > 64) refuse("bad_request", "A message needs its cid");
    const chat = String(msg.chat ?? "");
    const known = this.sql.exec("SELECT * FROM messages WHERE from_id = ? AND cid = ?", me.id, cid).toArray()[0];
    if (known) { ws.send(JSON.stringify({ kind: "ack", cid, id: known.id, seq: known.seq })); return; }
    this.limit(me.id + ":msg", 20);
    this.writable(chat, me);
    const text = this.text(msg.text);
    let reply = msg.reply_to ? String(msg.reply_to) : null;
    if (reply && !this.sql.exec("SELECT 1 FROM messages WHERE chat = ? AND id = ?", chat, reply).toArray().length) reply = null;
    const message = this.ctx.storage.transactionSync(() => {
      const seq = this.sql.exec("UPDATE chats SET last_seq = last_seq + 1 WHERE id = ? RETURNING last_seq", chat).one().last_seq;
      const id = randomHex(8);
      const at = Date.now();
      this.sql.exec("INSERT INTO messages (chat, seq, id, from_id, cid, text, reply_to, at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        chat, seq, id, me.id, cid, text, reply, at);
      this.sql.exec("UPDATE members SET read_upto = ? WHERE chat = ? AND uid = ?", seq, chat, me.id);
      return this.messageView(this.sql.exec("SELECT * FROM messages WHERE id = ?", id).one());
    });
    this.emit({ chat, kind: "message", payload: { message } });
    ws.send(JSON.stringify({ kind: "ack", cid, id: message.id, seq: message.seq }));
  }

  own(chat, id, me) {
    this.member(chat, me.id);
    const row = this.sql.exec("SELECT * FROM messages WHERE chat = ? AND id = ?", chat, String(id ?? "")).toArray()[0];
    if (!row || row.deleted) refuse("no_message", "No such message", 404);
    if (row.from_id !== me.id) refuse("not_yours", "Only your own messages", 403);
    return row;
  }

  onEdit(ws, me, msg) {
    const chat = String(msg.chat ?? "");
    const row = this.own(chat, msg.id, me);
    const text = this.text(msg.text);
    const at = Date.now();
    this.sql.exec("UPDATE messages SET text = ?, edited_at = ? WHERE id = ?", text, at, row.id);
    this.emit({ chat, kind: "edited", payload: { chat_id: chat, id: row.id, text, edited_at: at } });
  }

  onDelete(ws, me, msg) {
    const chat = String(msg.chat ?? "");
    const row = this.own(chat, msg.id, me);
    this.sql.exec("UPDATE messages SET deleted = 1, text = '' WHERE id = ?", row.id);
    this.emit({ chat, kind: "deleted", payload: { chat_id: chat, id: row.id } });
  }

  onRead(ws, me, msg) {
    const chat = String(msg.chat ?? "");
    const mine = this.member(chat, me.id);
    const last = this.chatRow(chat).last_seq;
    const upto = Math.min(Number(msg.upto) || 0, last);
    if (upto <= mine.read_upto) return;
    this.sql.exec("UPDATE members SET read_upto = ? WHERE chat = ? AND uid = ?", upto, chat, me.id);
    this.emit({ chat, kind: "read", payload: { chat_id: chat, user_id: me.id, upto } });
  }

  onTyping(ws, me, msg) {
    const chat = String(msg.chat ?? "");
    this.member(chat, me.id);
    this.deliver({ kind: "typing", chat_id: chat, user_id: me.id }, this.memberIds(chat).filter((u) => u !== me.id));
  }
}

// [method, path, Studio method, open (no token)]
const ROUTES = [
  ["GET", /^\/v1\/health$/, "health", true],
  ["POST", /^\/v1\/register$/, "register", true],
  ["GET", /^\/v1\/me$/, "getMe"],
  ["DELETE", /^\/v1\/me$/, "deleteMe"],
  ["PATCH", /^\/v1\/me$/, "patchMe"],
  ["PUT", /^\/v1\/me\/avatar$/, "putMyAvatar"],
  ["GET", /^\/v1\/avatar\/u\/([0-9a-f]{16})$/, "userAvatar"],
  ["GET", /^\/v1\/users$/, "searchUsers"],
  ["GET", /^\/v1\/people$/, "people"],
  ["GET", /^\/v1\/friends$/, "friends"],
  ["POST", /^\/v1\/friends\/request$/, "requestFriend"],
  ["POST", /^\/v1\/friends\/(accept|decline|cancel)$/, "answerRequest"],
  ["DELETE", /^\/v1\/friends\/([0-9a-f]{16})$/, "unfriend"],
  ["GET", /^\/v1\/chats$/, "chats"],
  ["POST", /^\/v1\/chats$/, "createChat"],
  ["PATCH", /^\/v1\/chats\/([\w]+)$/, "patchChat"],
  ["PUT", /^\/v1\/chats\/([\w]+)\/avatar$/, "putChatAvatar"],
  ["GET", /^\/v1\/avatar\/c\/([\w]+)$/, "chatAvatar"],
  ["POST", /^\/v1\/chats\/([\w]+)\/members$/, "postMember"],
  ["DELETE", /^\/v1\/chats\/([\w]+)\/members\/([0-9a-f]{16})$/, "deleteMember"],
  ["GET", /^\/v1\/chats\/([\w]+)\/messages$/, "history"],
  ["GET", /^\/v1\/ws$/, "connect"],
];
