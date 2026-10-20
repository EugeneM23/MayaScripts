# Chat client core (plan 2 of 3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** the messenger's client inside Maya without its window: sign in, the cache, the live
connection with catch-up and an outbox, one session per Maya - proven headless against staging.

**Architecture:** `SkeldarAnim/maya_chat/` (a payload row). Pure parsing (`records`), HTTP (`api`),
the disk cache (`store`), the WebSocket split into a pure `Protocol` and a thin `QtLink`, and a
`Session` on `sys._skeldar_chat` that applies events to its state and tells listeners. Plan 3 draws
the window on the session.

**Tech Stack:** Python 3 stdlib, PySide6 `QtWebSockets` (Maya 2027 ships it, OpenSSL 3.5), unittest
under mayapy.

## Global Constraints

- The spec: `docs/superpowers/specs/2026-10-19-chat-messenger-design.md` ("Client" and "Errors").
- The server is `server/chat/worker.js`; its shapes are what it sends, read off the code:
  - user `{id, nick, name, avatar_v}`, plus `online`, `last_seen` with presence;
  - message `{id, chat, seq, from_id, cid, text, reply_to, at, edited_at, deleted}`;
  - chat `{id, kind, name, admin, avatar_v, members[], last, unread, read_upto}`;
  - an event `{seq, kind, ...payload}`; `typing`, `presence`, `ack`, `error`, `resync`, `caught_up`
    carry no seq.
- **Every request sends its own User-Agent** (`skeldar-chat/1`): Cloudflare refuses Python-urllib's
  default with 403 «error code: 1010» (measured 2026-10-20).
- `records.py`, `api.py`, `store.py` import nothing of Maya or Qt (a subprocess test pins it).
- The server's address: `maya_chat.SERVER`, overridden by the optionVar `skeldarChatServer`. Until
  plan 3 makes production, SERVER is the staging Worker.
- The cache: `<userAppDir>/SkeldarChat/<host>/` - `token`, `me.json`, `chats.json`,
  `messages/<chat>.jsonl` (the last 500), `outbox.json`, `since`. Writes are atomic (tmp + replace).
- Reconnect after 1, 2, 4, 8, 16, 30 s (then 30); ping (the text frame `ping`) every 25 s;
  `hello {since}` on every open, then the outbox in order.
- No modal dialog anywhere; no window in this plan.

## Files

| file | does |
|---|---|
| `SkeldarAnim/maya_chat/__init__.py` | `SERVER`, `server()`, `session()`; imports nothing heavy |
| `SkeldarAnim/maya_chat/records.py` | nick rule, strict parse of users / messages / chats / events, merge, unread, text runs |
| `SkeldarAnim/maya_chat/api.py` | `Api` over urllib, `ChatError(code, text, status)` |
| `SkeldarAnim/maya_chat/store.py` | `Store` - the disk cache |
| `SkeldarAnim/maya_chat/link.py` | `Protocol` (pure: hello, outbox, acks, backoff, ping) and `QtLink` (QWebSocket) |
| `SkeldarAnim/maya_chat/session.py` | `Session`: sign in / out, state, events applied, send / edit / delete / read / typing, listeners; `get()` / `close()` on `sys` |
| `SkeldarAnim/install.py` | the payload row `maya_chat` |
| `tests/test_chat_records.py`, `_api.py`, `_store.py`, `_link.py`, `_session.py` | unit tests |
| `docs/superpowers/plans/verify_chat_client.py` | headless, two sessions against staging |

### Task 1: records

**Interfaces - Produces:** `nick(text) -> str | None`; `user(d)`, `message(d)`, `chat(d)` (raise
`Bad`); `event(d) -> dict | None` (None for anything malformed or unknown); `merge(old, new) -> list`
(by seq, one per id, the later wins); `unread(chat, messages, me) -> int`; `runs(text) -> [(kind, s)]`
kind "text" / "link".

Tests: a nick folded and refused; each shape parsed, a wrong type refused; an unknown kind and a
message event without its message -> None; merge keeps order and replaces an edit; unread skips mine
and deleted; links with trailing punctuation; the module imports no Maya / Qt.

### Task 2: api

**Produces:** `ChatError(code, text, status=0)`; `Api(server, token=None, opener=urlopen)`:
`register(nick)`, `me()`, `rename(name)`, `users(q)`, `friends()`, `request(nick)`,
`answer(verb, user)` (accept / decline / cancel), `unfriend(user)`, `chats()`, `dm(user)`,
`group(name, members)`, `rename_chat(chat, name)`, `add_member(chat, user)`,
`remove_member(chat, user)`, `history(chat, before=None, limit=50)`. A network failure ->
`ChatError("offline", ...)`.

Tests on a fake opener: the URL, method, body, Authorization and User-Agent; a 4xx's
`{error, text}` raised; offline; history's query.

### Task 3: store

**Produces:** `Store(root)`, `Store.for_server(base, server)`; `token` / `set_token`, `me` /
`set_me`, `chats` / `set_chats`, `messages(chat)` / `set_messages(chat, list)` (last 500),
`outbox` / `set_outbox`, `since` / `set_since`, `forget()` (token and me only).

Tests in a temp folder: round trips, the 500 cut, a broken file reads as empty, the host folder.

### Task 4: link

**Produces:** `Protocol(send, since=0, outbox=())` with `opened()`, `closed() -> delay`,
`received(text)`, `tick(now)`, `queue(msg)`, callbacks `on_event`, `on_ack`, `on_error`,
`on_resync`, `on_caught_up`, `on_state`; `BACKOFF`, `PING_S`. `QtLink(server, token, protocol)`:
`start()`, `stop()`, `connected`.

Tests: hello with since then the outbox in order; an ack drops its cid; caught_up moves since; the
backoff 1, 2, 4 ... 30; ping every 25 s while open, none while closed; a broken frame ignored.

### Task 5: session

**Produces:** `Session(server, store, api_factory=Api, link_factory=QtLink)`; `start()`,
`sign_in(nick)`, `sign_in_code(code)`, `sign_out()`, `send(chat, text, reply_to=None) -> cid`,
`edit`, `delete`, `read(chat)`, `typing(chat)`, `open_dm(user)`, `load_history(chat)`, `resync()`;
`state` (`me`, `chats`, `messages`, `friends`, `pending`, `online`, `typing`); `listen(fn)` /
`unlisten(fn)`, fn(kind, data). `get()` / `close()` keep it on `sys._skeldar_chat`.

Tests on fake api and link: a send waits in the outbox (store too) and its ack turns it into the
server's message; a message event from another merges and counts unread; edited / deleted /
read / chat / member_removed / friend events; resync reloads; sign_out forgets the token; a second
`get()` is the same session.

### Task 6: headless proof against staging

`verify_chat_client.py`: two sessions, each its own store folder, a QCoreApplication loop; register
two users, befriend over HTTP, a dm; A sends, B gets it within 1 s, A's pending becomes the
message; B offline, A sends, B back gets it by `hello {since}`; A offline sends, the outbox goes on
reconnect; the same cid twice is one message; read marks reach A; both accounts deleted at the end.

### Task 7: record

CLAUDE.md: a section on the client core.
