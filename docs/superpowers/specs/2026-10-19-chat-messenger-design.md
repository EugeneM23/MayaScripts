# Chat: a messenger inside Maya (first version)

2026-10-19. The animator: «Давай изучим возможности создания внутреннего месенджера прямо через наш
плагин ... похожий на телеграмм, что бы можно было отправлять не только сообщения но и файлы, позы,
fbx, риги и все с чем мы работаем + обмениватся смайликами и сообщениями. Добавлять друзей и создавать
группы».

## Decisions taken in the brainstorm

- **Our own server** («Давай делать нормально через свой сервер»), after a serverless road over
  Shared's ntfy.sh / temp.sh with per-chat secret channels was designed and set aside: it cannot
  deliver what was sent while a Maya was closed for more than 12 hours, and it depends on other
  people's free services.
- **Cloudflare: Workers + Durable Objects** (R2 later, see "Files").
- **Sign-in is a nick and nothing else** («максимально упростим регистрацию просто ввел ник и вошел»).
  Registration is open: anyone with the plugin (the repository is public) can join. So friends are by
  request, and only a friend can be written to.
- **A floating window like Telegram Desktop**, a rail icon with the unread count. Live mockup, approved
  as it stands: https://claude.ai/artifact/Y68L5ZeK5mgoRHUmmwUm6h
- **No end-to-end encryption in v1**: the server is ours, the transport is TLS.
- **The whole idea is three specs**. This one is the messenger itself. Spec 2: attachments (files,
  scenes, FBX, Pose Library cards, rigs, weapons, opened or applied with one press). Spec 3: emoji,
  reactions, stickers.

## Scope of v1

1. Sign in by nick; a profile (display name, avatar picture); a login code to use the same account on
   another machine.
2. Friends: search by nick, request, accept / decline / cancel, remove.
3. Chats: one-to-one and groups. A group's creator is its admin: adds and removes members, renames
   it, sets its avatar. Any member may leave.
4. Messages: text, reply to a message, edit and delete one's own, delivered / read marks, «typing…».
5. Notifications in Maya: the unread count on the rail icon, a message in the viewport, an optional
   sound.

Not in v1: attachments, emoji / reactions, search in message text, calls, deleting an account from
the window, changing one's nick.

## Server

**One Worker, `skeldar-chat`, one Durable Object class `Studio`, one instance** (`idFromName("studio")`)
holding the whole studio:

- **SQLite inside the object** (SQLite-backed Durable Objects, available on the free plan):

  | table | columns |
  |---|---|
  | `users` | `id` (random 16 hex), `nick` (unique, lower case), `name`, `token_hash` (sha256), `avatar` (blob ≤ 256 KB, nullable), `avatar_v`, `created`, `last_seen` |
  | `friends` | `a`, `b` (a < b), `since` |
  | `requests` | `from_id`, `to_id`, `at` |
  | `chats` | `id`, `kind` (`dm` / `group`), `name`, `admin`, `avatar`, `avatar_v`, `created`; a dm's id is derived from its two user ids so there is only ever one |
  | `members` | `chat`, `user`, `joined`, `read_upto` (a message seq) |
  | `messages` | `seq` (per chat, monotone), `chat`, `id`, `from_id`, `cid`, `text`, `reply_to`, `at`, `edited_at`, `deleted` |
  | `events` | `seq` (global, monotone), `chat` or `user` (audience), `kind`, `payload` (JSON), `at`; kept 30 days |

- **The WebSockets live in the same object**, through the Hibernation API: while nobody sends
  anything the object sleeps and its duration is not billed. A user's sockets are tagged with their
  id; a socket's attachment holds the user id.
- One object is plenty for a studio (a Durable Object serves on the order of a thousand requests a
  second). Chats can move to objects of their own later without the client noticing.

**Avatars** are resized by the client to 256 px (JPEG) and kept in `users.avatar` / `chats.avatar`
(a SQLite value may be up to 2 MB; ours ≤ 256 KB). v1 needs no R2. R2 comes with spec 2, and
activating it on a Cloudflare account asks for a payment method even on the free tier: that is a
decision for spec 2.

### Sign-in

- `POST /v1/register {nick}`: nick `^[a-z0-9_]{3,24}$` (case folded), free → `{token, user}`. The token
  is 32 random bytes, base64url, prefixed `skc_`; the server keeps only its sha256.
- Every other request carries `Authorization: Bearer <token>`; a WebSocket upgrade too.
- The login code shown in Settings **is** the token. «Sign in by code» on another machine checks it
  with `GET /v1/me`.
- Reserved nicks (`admin`, `skeldar`, `system`, ...) are refused.

### HTTP API (JSON)

| request | does |
|---|---|
| `GET /v1/me`, `PATCH /v1/me {name}` | profile |
| `PUT /v1/me/avatar` (image/jpeg ≤ 256 KB) | avatar; `avatar_v` + 1 |
| `GET /v1/avatar/u/<id>` , `GET /v1/avatar/c/<id>` | the picture (cacheable by `?v=`) |
| `GET /v1/users?q=<prefix>` | up to 20 users by nick prefix: id, nick, name, avatar_v |
| `GET /v1/friends` | `{friends, incoming, outgoing}` with presence |
| `POST /v1/friends/request {nick}` / `accept {user}` / `decline {user}` / `cancel {user}`, `DELETE /v1/friends/<user>` | friends; a request to someone who already asked you is an accept |
| `GET /v1/chats` | every chat of mine: members, last message, unread count, my `read_upto` |
| `POST /v1/chats {kind:"dm", with}` | the dm with a friend (existing or new) |
| `POST /v1/chats {kind:"group", name, members}` | a new group, me its admin; members must be my friends |
| `PATCH /v1/chats/<id> {name}`, `PUT /v1/chats/<id>/avatar` | admin only |
| `POST /v1/chats/<id>/members {user}` | admin only, a friend of the admin |
| `DELETE /v1/chats/<id>/members/<user>` | admin, or the member themself (leave). An admin who leaves hands the group to its oldest member |
| `GET /v1/chats/<id>/messages?before=<seq>&limit=50` | history, newest last |

Errors: `{error: <code>, text: <one line for the animator>}` with a 4xx status (`nick_taken`,
`bad_nick`, `not_friend`, `not_member`, `not_admin`, `too_many`, `too_big`, `bad_token`, ...).

### WebSocket `GET /v1/ws`

Client → server (JSON lines):

| message | does |
|---|---|
| `hello {since}` | send every event of mine after `since` (global seq); `since` 0 or older than the kept 30 days → `{resync: true}` and the client reloads chats and history over HTTP |
| `send {chat, cid, text, reply_to?}` | a message; `cid` is the client's id: the same `cid` again returns the same message, never a second one |
| `edit {chat, id, text}`, `delete {chat, id}` | one's own message |
| `read {chat, upto}` | my read mark |
| `typing {chat}` | ephemeral, never stored; the client sends it at most every 3 s while typing |
| `ping` | keep-alive; the client pings every 25 s |

Server → client: `ack {cid, id, seq}`; `error {cid?, code, text}`; and events, each with its global
`seq` (except `typing` and `presence`): `message`, `edited`, `deleted`, `read`, `chat` (created,
renamed, avatar), `member_added`, `member_removed`, `friend_request`, `friend_added`,
`friend_removed`, `request_cancelled`, `typing`, `presence {user, online, last_seen}`; after a `hello`
the catch-up ends with `caught_up {seq}`.

An event's audience: a chat's events go to its members at the time; a personal event to its user.
A member removed from a group gets `member_removed` for themself and nothing after it.

### Limits, checked by the server

- text ≤ 4000 characters; name ≤ 40; group name ≤ 60; a group ≤ 50 members;
- per user, at most 20 messages and 30 HTTP requests in any 10 s (`too_many`);
- a dm only between friends, a message only by a member, admin actions only by the admin;
- everything is stored and sent as plain text; the client never renders HTML from it.

### Code and deployment

- `server/chat/worker.js` (ES module: the Worker and the `Studio` class), `server/chat/deploy.py`
  (stdlib: uploads the script through Cloudflare's HTTP API with its Durable Object binding and the
  `new_sqlite_classes` migration, enables the workers.dev route). No Node or wrangler.
- `server/` is beside the plugin and never ships (the 2026-10-10 root rule bends for it: it is what
  the plugin talks to; a test pins that `install.payload()` holds nothing of it).
- Credentials only from the environment: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`. The
  animator creates the Cloudflare account and the token; nothing is typed into chat or committed.
- Two Workers: `skeldar-chat-staging` (tests) and `skeldar-chat` (colleagues).

## Client: `SkeldarAnim/maya_chat/` (a payload row)

| module | does | imports |
|---|---|---|
| `records.py` | users, chats, messages, events: strict parsing of what the server sends, merging history, unread counts, nick rule, text → runs (plain / link) for drawing | stdlib only (a subprocess test pins it) |
| `api.py` | the HTTP calls; network failures and server errors → `ChatError(code, text)` | stdlib (`urllib`, `json`) |
| `store.py` | the cache in `<userAppDir>/SkeldarChat/<server host>/`: `token`, `me.json`, `chats.json`, `messages/<chat>.jsonl` (last 500 a chat), `avatars/`, `outbox.json`, `since` | stdlib |
| `link.py` | the live connection: `PySide6.QtWebSockets.QWebSocket` with the `Authorization` header, reconnect after 1, 2, 4 … 30 s, ping every 25 s, `hello {since}` on every open, the outbox resent in order, acks matched by `cid` | Qt |
| `session.py` | one session per Maya on `sys._skeldar_chat` (trap 111): the link, the state, listeners; survives a plugin update without a second connection | stdlib + `link` |
| `notify.py` | the rail badge, the viewport message, the sound (`maya_hubsound`, off by default) | Qt, cmds |
| `window.py` | the window (below) | Qt |
| `__init__.py` | `show()`, `ensure()`; imports nothing heavy | — |

- **Start**: the hub's build calls `maya_chat.ensure()` (deferred). With a token on disk the session
  connects at once, so the rail shows unread messages before the window was ever opened. Without one
  nothing happens until the rail icon is pressed.
- **Never lose, never double**: the client remembers the last global `seq` it applied; every open
  sends `hello {since}`. A message being sent has a `cid` and a clock on its bubble until its `ack`;
  offline it waits in `outbox.json` and goes after the reconnect; the server answers a repeated `cid`
  with the first message.
- **The server's address**: `maya_chat.SERVER` (the production Worker's workers.dev URL), overridden by
  the optionVar `skeldarChatServer` (the staging tests and the animator's own checks).
- **The rail**: a row in `maya_hub.SECTIONS`, `chat` «Chat», Tabler `message-circle`; like Pose
  Library it opens its own window instead of a card. The icon carries the unread count (the accent
  badge, a pop when it changes).

## The window

As in the mockup: a floating window of the hub (`maya_hubwindow.WindowFrame`, look B), title «Chat»
with the connection state («в сети» / «offline — переподключение…»), ⧉ and ✕; out of the rail icon
and back into it. Place and size remembered (`skeldarChatWindowPos`, `skeldarChatWindowSize`), default
760 × 520, least 520 × 360. Drawn by our own widgets and QPainter, not Maya's controls. Below 600 px
wide it shows one column at a time (the list, or the chat with a back button).

- **Sign-in**: a card «Ваш ник» with `@` and a field, live checking (format, then free / taken by
  `GET /v1/users?q=`), Войти; «Войти по коду» with the login code.
- **Left column (~250 px)**: search over chats and people, ✎ (new chat / new group), rows (avatar —
  picture, or initials on the user's colour —, name, last message or «… печатает…», time, unread
  count); at the bottom my avatar and name, 👤 Friends with the incoming request count, ⚙ Settings.
- **The chat**: header (avatar, name, «в сети» / «был(а) в 14:32» / «печатает…»; a group: members and
  how many online, a click opens the members drawer: rename, add a friend, remove — admin only);
  the feed (bubbles, mine on the right in `#5a3922`, others' on the left; in a group the sender's
  name and avatar; consecutive messages from one sender joined; day separators; links clickable;
  `изм.`; ✓ delivered, ✓✓ in the accent read); the right button on a message: Reply, Copy, Edit and
  Delete for one's own; a reply's quote scrolls to its original; history loaded 50 at a time when
  scrolled to the top; «↓» with the count of new messages while scrolled up.
- **The composer**: grows to 6 lines; Enter sends, Shift+Enter a new line, ↑ in an empty field edits
  my last message, Esc cancels a reply / edit; a bar above it for «Ответ …» / «Изменение сообщения».
- **Friends**, **New chat / group**, **Settings** (name, avatar from a file, the login code hidden
  until «Показать», «Скопировать», notifications, «Выйти на этой машине») take the right column.
- **Motion** (`docs/interface-motion.md`): a new message enters from below with a small overshoot;
  hover lifts and glows 110 ms; a count pops 200 ms when it changes; a sent message flashes 120 ms; a
  deleted one folds; the window bursts out of the rail icon and folds back into it. The data is
  instant; ⋮ → Interface animations off makes it all instant.

## Errors

- **Offline / server down**: the title says so; history from the cache; sending waits with a clock;
  after 10 minutes unsent a bubble reads «не отправлено — повторить».
- **A token refused** (`bad_token`): the sign-in screen; the cache stays on disk.
- **Refusals** show as one line where the press was (under the composer, in the friends pane, in the
  drawer). Removed from a group: the chat stays, read-only, with a line saying so.
- **No modal dialog anywhere** (a modal blocks Maya's idle queue).
- **A plugin update with the window open**: the session on `sys` closes its socket and the fresh
  modules open one; the window is rebuilt by name (traps 102, 111).
- **Two Mayas on one account**: each its own socket, both get everything; a read in one clears the
  count in the other.

## Proof

- **Unit tests** (mayapy): `records` (parsing, refusing malformed events, merging, unread, the nick
  rule, link runs), `store`, `link` on a fake socket (reconnect, `hello` with `since`, the outbox
  resent in order, an ack by `cid`), `session`, the window offscreen on a fake session (the list, a
  sent message with its clock then ✓ then ✓✓, reply, edit, delete, the badge).
- **`docs/superpowers/plans/verify_chat_server.py`** against staging, its users made and removed by
  the run: register and a taken nick; friends (request, accept, decline, cancel, remove); a dm to a
  stranger refused; a group (create, add, remove, a non-admin refused, leave, the admin handover);
  messages (order, `hello {since}` after a disconnect, the same `cid` twice → one message, edit,
  delete, read marks); limits; two clients: an event reaches the second in under 1 s.
- **Live in Maya is the animator's** (2026-10-09): after Check update, two accounts write to each
  other.

## Order of work

1. The server and staging, with `verify_chat_server.py` green.
2. The client without the window (`records`, `api`, `store`, `link`, `session`), unit tests and a
   headless run against staging.
3. The window and the rail.
4. The production Worker; `maya_chat.SERVER` pointed at it; a build.

## What the animator does once

Create a Cloudflare account; create an API token with «Workers Scripts: Edit» and «Account Settings:
Read» for it; put it and the account id in the environment variables `CLOUDFLARE_API_TOKEN` and
`CLOUDFLARE_ACCOUNT_ID` on this machine. Nothing else; colleagues set up nothing.
