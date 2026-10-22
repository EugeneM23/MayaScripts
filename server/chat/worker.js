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
// Files (2026-10-22): one zip a file in R2, uploaded in equal parts, kept 30 days.
const PART = 16 * 1024 * 1024;
const FILE_MAX = 1024 * 1024 * 1024;
const FILE_KEEP = 30 * DAY;
const UPLOADS_EACH = 4;
// A scene, an fbx, or a Pose Library card (a .pose / .anim folder, zipped) - 2026-10-22.
const FILE_NAME = /^[^\\/:*?"<>|\x00-\x1f.][^\\/:*?"<>|\x00-\x1f]{0,115}\.(ma|mb|fbx|pose|anim)$/i;
const FILE_KINDS = new Set(["scene", "fbx", "pose", "anim"]);

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
  `CREATE TABLE IF NOT EXISTS reactions (chat TEXT NOT NULL, msg TEXT NOT NULL, uid TEXT NOT NULL,
     emoji TEXT NOT NULL, at INTEGER NOT NULL, PRIMARY KEY (msg, uid, emoji))`,
  `CREATE INDEX IF NOT EXISTS reactions_chat ON reactions (chat)`,
  `CREATE TABLE IF NOT EXISTS files (id TEXT PRIMARY KEY, chat TEXT NOT NULL, uid TEXT NOT NULL, name TEXT NOT NULL,
     kind TEXT NOT NULL, bytes INTEGER NOT NULL, zip INTEGER NOT NULL, fps REAL, range TEXT, upload TEXT,
     parts TEXT NOT NULL DEFAULT '{}', state TEXT NOT NULL, msg TEXT, at INTEGER NOT NULL)`,
  `CREATE INDEX IF NOT EXISTS files_chat ON files (chat)`,
];
const REACTIONS_EACH = 8;
// An emoji: 1-16 UTF-16 units, no ASCII letter, digit or space.
const EMOJI = /^[^A-Za-z0-9\s]{1,16}$/u;

export class Studio extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.sql = ctx.storage.sql;
    for (const statement of SCHEMA) this.sql.exec(statement);
    try { this.sql.exec("ALTER TABLE messages ADD COLUMN file TEXT"); } catch { /* there already */ }
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
    try { await this.sweepFiles(Date.now()); } catch { /* the next alarm tries again */ }
    await this.ctx.storage.setAlarm(Date.now() + DAY);
  }

  // ---------------------------------------------------------------- files (R2)
  bucket() {
    if (!this.env || !this.env.FILES) refuse("no_files", "Files are not set up on this server", 503);
    return this.env.FILES;
  }

  fileRow(id) {
    const row = this.sql.exec("SELECT * FROM files WHERE id = ?", String(id ?? "")).toArray()[0];
    if (!row) refuse("no_file", "No such file", 404);
    return row;
  }

  fileView(id) {
    const row = this.sql.exec("SELECT * FROM files WHERE id = ?", id).toArray()[0];
    if (!row) return null;
    let range = null;
    try { range = row.range ? JSON.parse(row.range) : null; } catch { range = null; }
    return { id: row.id, name: row.name, kind: row.kind, bytes: row.bytes, zip: row.zip,
             fps: row.fps, range, expired: row.state === "expired" };
  }

  partsOf(row) { return Math.max(1, Math.ceil(row.zip / PART)); }

  // The object (or the unfinished upload) and the row gone; never fails.
  async dropFile(row) {
    try {
      const bucket = this.bucket();
      if (row.upload && row.state === "uploading") {
        await bucket.resumeMultipartUpload("f/" + row.id, row.upload).abort();
      } else {
        await bucket.delete("f/" + row.id);
      }
    } catch { /* already gone */ }
    this.sql.exec("DELETE FROM files WHERE id = ?", row.id);
  }

  async sweepFiles(now) {
    if (!this.env || !this.env.FILES) return;
    for (const row of this.sql.exec("SELECT * FROM files WHERE state = 'attached' AND at < ?", now - FILE_KEEP).toArray()) {
      try { await this.env.FILES.delete("f/" + row.id); } catch { /* gone */ }
      this.sql.exec("UPDATE files SET state = 'expired' WHERE id = ?", row.id);
    }
    const doomed = this.sql.exec(
      `SELECT * FROM files WHERE (state IN ('uploading', 'ready') AND at < ?)
         OR chat NOT IN (SELECT id FROM chats)
         OR (state IN ('attached', 'expired') AND (msg IS NULL OR msg NOT IN (SELECT id FROM messages WHERE deleted = 0)))`,
      now - DAY).toArray();
    for (const row of doomed) await this.dropFile(row);
  }

  async fileStart({ request, me }) {
    const bucket = this.bucket();
    const b = await this.body(request);
    const chat = String(b.chat ?? "");
    this.writable(chat, me);
    const name = String(b.name ?? "").trim();
    if (!FILE_NAME.test(name)) refuse("bad_name", "A file is a .ma, .mb, .fbx or a pose card with a plain name");
    const kind = String(b.kind ?? "");
    if (!FILE_KINDS.has(kind)) refuse("bad_request", "A file is a scene, an fbx or a pose card");
    const zip = Number(b.zip);
    const bytes = Number(b.bytes);
    if (!Number.isInteger(zip) || zip < 1) refuse("bad_request", "The zip's size is missing");
    if (zip > FILE_MAX) refuse("too_big", "A file is at most 1 GB zipped", 413);
    if (!Number.isInteger(bytes) || bytes < 0) refuse("bad_request", "The file's size is missing");
    const open = this.sql.exec("SELECT COUNT(*) AS n FROM files WHERE uid = ? AND state IN ('uploading', 'ready')", me.id).one().n;
    if (open >= UPLOADS_EACH) refuse("too_many", "At most " + UPLOADS_EACH + " files on the way at once", 429);
    const fps = b.fps !== null && b.fps !== undefined && Number.isFinite(Number(b.fps)) ? Number(b.fps) : null;
    const range = Array.isArray(b.range) && b.range.length === 2 && b.range.every((v) => Number.isFinite(Number(v)))
      ? JSON.stringify(b.range.map(Number)) : null;
    const id = randomHex(8);
    const upload = await bucket.createMultipartUpload("f/" + id, { httpMetadata: { contentType: "application/zip" } });
    this.sql.exec(`INSERT INTO files (id, chat, uid, name, kind, bytes, zip, fps, range, upload, state, at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'uploading', ?)`,
      id, chat, me.id, name, kind, bytes, zip, fps, range, upload.uploadId, Date.now());
    return json({ id, part_size: PART, parts: Math.max(1, Math.ceil(zip / PART)) });
  }

  mineUploading(id, me) {
    const row = this.fileRow(id);
    if (row.uid !== me.id) refuse("not_yours", "Only your own upload", 403);
    if (row.state !== "uploading") refuse("not_uploading", "That file is not being uploaded", 409);
    return row;
  }

  async filePart({ request, me, params }) {
    const bucket = this.bucket();
    const row = this.mineUploading(params[0], me);
    const n = Number(params[1]);
    const count = this.partsOf(row);
    if (!(n >= 1 && n <= count)) refuse("bad_part", "No such part");
    const want = n < count ? PART : row.zip - PART * (count - 1);
    const body = await request.arrayBuffer();
    if (body.byteLength !== want) refuse("bad_part", "Part " + n + " is " + want + " bytes, not " + body.byteLength);
    const part = await bucket.resumeMultipartUpload("f/" + row.id, row.upload).uploadPart(n, body);
    const fresh = this.fileRow(row.id);
    const parts = JSON.parse(fresh.parts || "{}");
    parts[n] = part.etag;
    this.sql.exec("UPDATE files SET parts = ? WHERE id = ?", JSON.stringify(parts), row.id);
    return json({ ok: true, part: n });
  }

  async fileComplete({ me, params }) {
    const bucket = this.bucket();
    const row = this.mineUploading(params[0], me);
    const parts = JSON.parse(row.parts || "{}");
    const count = this.partsOf(row);
    const list = [];
    for (let n = 1; n <= count; n++) {
      if (!parts[n]) refuse("missing_part", "Part " + n + " has not arrived", 409);
      list.push({ partNumber: n, etag: parts[n] });
    }
    const object = await bucket.resumeMultipartUpload("f/" + row.id, row.upload).complete(list);
    if (object && object.size !== row.zip) {
      await this.dropFile({ ...row, state: "ready" });
      refuse("bad_size", "The file arrived the wrong size", 409);
    }
    this.sql.exec("UPDATE files SET state = 'ready', upload = NULL WHERE id = ?", row.id);
    return json({ id: row.id, state: "ready" });
  }

  async fileCancel({ me, params }) {
    const row = this.fileRow(params[0]);
    if (row.uid !== me.id) refuse("not_yours", "Only your own upload", 403);
    if (row.state === "attached" || row.state === "expired") refuse("attached", "Delete its message instead", 409);
    await this.dropFile(row);
    return json({ ok: true });
  }

  async fileGet({ me, params }) {
    const bucket = this.bucket();
    const row = this.fileRow(params[0]);
    this.member(row.chat, me.id);
    if (row.state === "expired") refuse("expired", "This file has expired", 410);
    if (row.state !== "attached" && row.uid !== me.id) refuse("no_file", "No such file", 404);
    if (row.state === "uploading") refuse("not_ready", "The file is still uploading", 409);
    const object = await bucket.get("f/" + row.id);
    if (!object) refuse("expired", "This file has expired", 410);
    return new Response(object.body, { headers: {
      "content-type": "application/zip", "content-length": String(object.size),
      "cache-control": "private, no-store" } });
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
    const user = { id, nick, name, avatar_v: 0 };
    // Everybody's list gains the newcomer at once (there are no friends to ask).
    this.emit({ kind: "user", payload: { user: { ...user, online: false, last_seen: 0 } } });
    return json({ token, user });
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
    this.sql.exec("DELETE FROM reactions WHERE uid = ?", uid);
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

  messageView(r, reactions) {
    const out = { id: r.id, chat: r.chat, seq: r.seq, from_id: r.from_id, cid: r.cid,
                  text: r.deleted ? "" : r.text, reply_to: r.reply_to, at: r.at, edited_at: r.edited_at,
                  deleted: !!r.deleted, file: r.file && !r.deleted ? this.fileView(r.file) : null };
    out.reactions = reactions ? (reactions.get(r.id) || {}) : this.reactionsOf([r.id]).get(r.id) || {};
    return out;
  }

  // {message id: {emoji: [user id, ...]}} for these messages, each emoji's people in reaction order.
  reactionsOf(ids) {
    const out = new Map();
    for (let i = 0; i < ids.length; i += 90) {
      const part = ids.slice(i, i + 90);
      if (!part.length) continue;
      const rows = this.sql.exec(
        `SELECT msg, uid, emoji FROM reactions WHERE msg IN (${part.map(() => "?").join(",")}) ORDER BY at, uid`,
        ...part).toArray();
      for (const r of rows) {
        const m = out.get(r.msg) || {};
        (m[r.emoji] = m[r.emoji] || []).push(r.uid);
        out.set(r.msg, m);
      }
    }
    return out;
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
    for (const id of others) this.userById(id);
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
      this.sql.exec("DELETE FROM reactions WHERE chat = ?", chat);
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
    const reactions = this.reactionsOf(rows.map((r) => r.id));
    return json({ messages: rows.reverse().map((r) => this.messageView(r, reactions)) });
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
                        read: this.onRead, typing: this.onTyping, react: this.onReact }[msg.type];
      if (!handler) refuse("bad_request", "Unknown message " + msg.type);
      await handler.call(this, ws, me, msg);
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
    if (row.kind === "dm" && !this.memberIds(chat).some((id) => id !== me.id)) {
      refuse("no_user", "The other person has left", 403);
    }
    return row;
  }

  // A file's caption: may be empty.
  caption(raw) {
    const text = String(raw ?? "").replace(/^\s+|\s+$/gu, "");
    if (text.length > TEXT_MAX) refuse("too_long", "A message is at most " + TEXT_MAX + " characters");
    return text;
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
    const fileId = msg.file ? String(msg.file) : null;
    if (fileId) {
      const f = this.sql.exec("SELECT * FROM files WHERE id = ?", fileId).toArray()[0];
      if (!f || f.uid !== me.id || f.chat !== chat) refuse("no_file", "No such file", 404);
      if (f.state !== "ready") refuse("not_ready", "The file has not finished uploading", 409);
    }
    const text = fileId ? this.caption(msg.text) : this.text(msg.text);
    let reply = msg.reply_to ? String(msg.reply_to) : null;
    if (reply && !this.sql.exec("SELECT 1 FROM messages WHERE chat = ? AND id = ?", chat, reply).toArray().length) reply = null;
    const message = this.ctx.storage.transactionSync(() => {
      const seq = this.sql.exec("UPDATE chats SET last_seq = last_seq + 1 WHERE id = ? RETURNING last_seq", chat).one().last_seq;
      const id = randomHex(8);
      const at = Date.now();
      this.sql.exec("INSERT INTO messages (chat, seq, id, from_id, cid, text, reply_to, at, file) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        chat, seq, id, me.id, cid, text, reply, at, fileId);
      if (fileId) this.sql.exec("UPDATE files SET state = 'attached', msg = ?, at = ? WHERE id = ?", id, at, fileId);
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
    const text = row.file ? this.caption(msg.text) : this.text(msg.text);
    const at = Date.now();
    this.sql.exec("UPDATE messages SET text = ?, edited_at = ? WHERE id = ?", text, at, row.id);
    this.emit({ chat, kind: "edited", payload: { chat_id: chat, id: row.id, text, edited_at: at } });
  }

  async onDelete(ws, me, msg) {
    const chat = String(msg.chat ?? "");
    const row = this.own(chat, msg.id, me);
    this.sql.exec("UPDATE messages SET deleted = 1, text = '' WHERE id = ?", row.id);
    this.sql.exec("DELETE FROM reactions WHERE msg = ?", row.id);
    this.emit({ chat, kind: "deleted", payload: { chat_id: chat, id: row.id } });
    const file = row.file ? this.sql.exec("SELECT * FROM files WHERE id = ?", row.file).toArray()[0] : null;
    if (file) await this.dropFile(file);
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

  onReact(ws, me, msg) {
    const chat = String(msg.chat ?? "");
    this.member(chat, me.id);
    const id = String(msg.id ?? "");
    const row = this.sql.exec("SELECT * FROM messages WHERE chat = ? AND id = ?", chat, id).toArray()[0];
    if (!row || row.deleted) refuse("no_message", "No such message", 404);
    const emoji = String(msg.emoji ?? "");
    if (!EMOJI.test(emoji)) refuse("bad_emoji", "A reaction is one emoji");
    const on = msg.on !== false;
    const had = this.sql.exec("SELECT 1 FROM reactions WHERE msg = ? AND uid = ? AND emoji = ?", id, me.id, emoji)
      .toArray().length > 0;
    if (on === had) return;
    this.limit(me.id + ":react", 30);
    if (on) {
      const n = this.sql.exec("SELECT COUNT(*) AS n FROM reactions WHERE msg = ? AND uid = ?", id, me.id).one().n;
      if (n >= REACTIONS_EACH) refuse("too_many", "At most " + REACTIONS_EACH + " reactions on one message");
      this.sql.exec("INSERT INTO reactions (chat, msg, uid, emoji, at) VALUES (?, ?, ?, ?, ?)",
        chat, id, me.id, emoji, Date.now());
    } else {
      this.sql.exec("DELETE FROM reactions WHERE msg = ? AND uid = ? AND emoji = ?", id, me.id, emoji);
    }
    this.emit({ chat, kind: "reaction", payload: { chat_id: chat, id, user_id: me.id, emoji, on } });
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
  ["POST", /^\/v1\/files$/, "fileStart"],
  ["PUT", /^\/v1\/files\/([0-9a-f]{16})\/parts\/(\d{1,5})$/, "filePart"],
  ["POST", /^\/v1\/files\/([0-9a-f]{16})\/complete$/, "fileComplete"],
  ["DELETE", /^\/v1\/files\/([0-9a-f]{16})$/, "fileCancel"],
  ["GET", /^\/v1\/files\/([0-9a-f]{16})$/, "fileGet"],
];
