# Chat Calls Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Voice and video calls with screen sharing, up to 4 people, inside the SkeldarAnim chat, from Maya.

**Architecture:** WebRTC runs in one Chromium web view per call (Maya's QtWebEngine) on a page shipped in the plugin; everyone in a call connects to everyone else (mesh). The chat's Durable Object keeps the calls (ringing, live, ended), relays the connection set-up messages between two members over the existing WebSockets, posts a call line in the chat when a call ends, and hands out Cloudflare TURN credentials. Python owns the socket and bridges it to the page through QWebChannel.

**Tech Stack:** Cloudflare Workers + SQLite Durable Object (`server/chat/worker.js`), Cloudflare Realtime TURN, Maya 2027 mayapy (Python 3, PySide6 6.8.3: QtWebEngineWidgets, QtWebEngineCore, QtWebChannel), plain JavaScript (Chromium 122), stdlib `unittest`.

Spec: `docs/superpowers/specs/2026-10-22-chat-calls-design.md`.

## Global Constraints

- At most **4** people in a call; any group chat may start one; the 5th join is refused `call_full`.
- A ringing call nobody answers ends after **45 s**; a member whose sockets are all gone for **30 s** leaves.
- When a call ends the server posts a message in the chat from its starter carrying `call: {id, kind, answered, seconds}`; the feed reads «Пропущенный звонок» (not answered) or «Звонок · N мин» (answered; under a minute «Звонок · N с»).
- Set-up messages (`call_signal`) are relayed live only, never stored, only between two members of the call, `data` at most 64 KB as JSON.
- The call page loads at base URL **`https://skeldar.call/`**; camera, microphone and screen permissions are granted only to that origin.
- TURN: `POST https://rtc.live.cloudflare.com/v1/turn/keys/<TURN_KEY_ID>/credentials/generate-ice-servers` with `Authorization: Bearer <TURN_KEY_TOKEN>`, body `{"ttl": 86400}`; URLs on port 53 dropped. Without the secrets (or on failure) `/v1/turn` answers Cloudflare's STUN only, `turn: false`.
- Secrets `TURN_KEY_ID`, `TURN_KEY_TOKEN` reach the Worker as `secret_text` bindings at upload; `deploy.py turn` creates the key (`POST /accounts/<id>/calls/turn_keys`, needs the token's **Calls Write** right).
- optionVars: `skeldarChatCallMic`, `skeldarChatCallCam`, `skeldarChatCallPos`, `skeldarChatCallSize`.
- The incoming-call ring plays regardless of the interface-sounds switch (`force=True`), looped until answered, declined, ended or 45 s.
- With ⋮ → Interface animations off (`maya_hubmotion.enabled()` False) the call window and card appear and go at once.
- Copy is Russian where the chat's copy is Russian (buttons, card, lines); code, names and comments English.
- `maya_chat/records.py` and the new `maya_chat/calls.py` stay stdlib only (no Qt, no Maya).
- No system Python here: tests run with `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest <module> -v` from the repo (worktree) root with `$env:QT_QPA_PLATFORM='offscreen'`. Avoid `2>&1` in PowerShell. Python source through the Write/Edit tools, never shell heredocs.
- Staging server: `https://skeldar-chat-staging.skeldar.workers.dev`; deploy with `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' server\chat\deploy.py staging` (credentials already saved by the animator). Production (`deploy.py production`) only in the last task.
- Commits: message in a file (`git commit -F msg.txt`, then delete it), stage only your own files (other sessions work in the main checkout), end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, never push.

## Wire protocol (shared by every task)

Client → server frames (over the chat socket):

| frame | fields |
|---|---|
| `call_start` | `chat`, `kind` ("audio"\|"video"), `cid` (the client's id, ≤ 64 chars) |
| `call_join` | `call` |
| `call_leave` | `call` |
| `call_decline` | `call` |
| `call_signal` | `call`, `to` (a user id), `data` (an object) |

Server → client:

- Stored event `call` (it has a `seq`, replays on reconnect): `{seq, kind: "call", call: <view>}`, delivered to every member of the call's chat.
  `<view>` = `{id, chat, by, kind, cid, state: "ringing"|"live"|"ended", members: [uid...], declined: [uid...], started_at, answered_at|null, ended_at|null}`.
  `members` are the people in the call now (the starter is in it from the start).
- Live event `call_signal` (no seq): `{kind: "call_signal", call, from, data}` to `to`'s sockets.
- Refusals as every frame's: `{kind: "error", cid, code, text}` with codes `call_exists`, `call_full`, `no_call`, `not_in_call`, `bad_request`, `too_many`.
- A message's view gains `call`: `null` or `{id, kind, answered, seconds}`.

Who sends the offer: a person who **joins** a call sends a WebRTC offer to every member already in it; members already in it wait for that offer. So the starter never offers; the second person offers to the starter; the third to both; etc.

## File Structure

| file | responsibility |
|---|---|
| `server/chat/worker.js` (modify) | calls tables, the five frames, `call` events, the call line, the timer for ring/gone, `GET /v1/turn` |
| `server/chat/deploy.py` (modify) | `turn` command; secrets as bindings |
| `tests/test_chat_deploy.py` (modify) | the secrets bindings and the `turn` command |
| `docs/superpowers/plans/verify_chat_server.py` (modify) | phases `calls`, `turn` |
| `SkeldarAnim/maya_chat/records.py` (modify) | parse `call` / `call_signal` events and a message's `call` |
| `SkeldarAnim/maya_chat/calls.py` (create, stdlib) | the call rules and texts: who to offer to, which calls ring for me, my call, duration text |
| `SkeldarAnim/maya_chat/look.py` (modify) | previews and feed items for call lines |
| `SkeldarAnim/maya_chat/api.py`, `session.py` (modify) | `turn()`, `state.calls`, the call frames, ICE server cache |
| `SkeldarAnim/assets/call/call.html`, `call.css`, `call.js` (create) | the WebRTC mesh page |
| `SkeldarAnim/maya_chat/callpage.py` (create, Qt) | the page's HTML composition, the QWebChannel bridge, the web page (permissions, screen requests) |
| `SkeldarAnim/maya_chat/callview.py` (create, Qt) | the call window, the folded tile, the screen picker, the session wiring, the one-call singleton |
| `SkeldarAnim/maya_chat/toast.py` (modify) | the incoming-call card |
| `SkeldarAnim/maya_hubsound.py`, `SkeldarAnim/assets/sounds/ring.wav` (modify/create) | the ring and looped playing |
| `SkeldarAnim/maya_chat/notify.py` (modify) | ring + card on an incoming call |
| `SkeldarAnim/maya_hubicons.py` (modify) | icons phone, phone-off, video, video-off, microphone, microphone-off, screen-share, screen-share-off, minimize |
| `SkeldarAnim/maya_chat/window.py` (modify) | the call buttons in a chat's header, the call line in the feed |
| `tests/test_chat_calls.py`, `tests/test_chat_callpage.py`, `tests/test_chat_callview.py` (create) | tests |
| `docs/superpowers/plans/verify_call_page.py`, `verify_chat_calls.py` (create) | headless media checks |

---

### Task 1: The server's calls

**Files:**
- Modify: `server/chat/worker.js` (constants ~line 14-35, `SCHEMA` ~57-84, the constructor ~89-103, `alarm` ~189-193, `messageView` ~573, `connect` ~735, `webSocketMessage` dispatch ~758, `webSocketClose` ~769)
- Modify: `docs/superpowers/plans/verify_chat_server.py` (a phase `calls`, registered in `PHASES`)

**Interfaces:**
- Produces: the wire protocol above (frames, `call` / `call_signal` events, `message.call`). Later tasks rely on exactly these names.

No JS unit tests exist for the Worker: it is proven against staging by `verify_chat_server.py`, as every server change so far.

- [ ] **Step 1: Write the verify phase first (it will fail against the current staging)**

In `docs/superpowers/plans/verify_chat_server.py`, read `phase_react` and the helpers (`Users.make`, `jcall`, `ws`, `gate`, `WS.until`) and the way a phase says hello and waits for `caught_up`; follow them exactly. Add:

```python
def _hello(w, token):
    """Say hello at the newest seq and wait for caught_up (as phase_react does)."""
    st, chats = jcall("GET", "/v1/chats", token)
    since = max([c.get("seq", 0) for c in (chats.get("chats") if isinstance(chats, dict) else chats) or []] + [1])
    w.send({"type": "hello", "since": since})
    w.until(lambda e: e.get("kind") == "caught_up", 10)


def _call_ev(w, call_id=None, state=None, seconds=8):
    def test(e):
        if e.get("kind") != "call":
            return False
        c = e["call"]
        return (call_id is None or c["id"] == call_id) and (state is None or c["state"] == state)
    ev, _ = w.until(test, seconds)
    return ev["call"] if ev else None


def _error(w, seconds=5):
    ev, _ = w.until(lambda e: e.get("kind") == "error", seconds)
    return ev


def phase_calls():
    A, B, C = Users.make("ca"), Users.make("cb"), Users.make("cc")
    st, dm = jcall("POST", "/v1/chats", A[0], {"kind": "dm", "with": B[1]["id"]})
    wa, wb, wc = ws(A[0]), ws(B[0]), ws(C[0])
    for w, t in ((wa, A[0]), (wb, B[0]), (wc, C[0])):
        _hello(w, t)

    # ring, a second call refused, a stranger refused
    wa.send({"type": "call_start", "chat": dm["id"], "kind": "video", "cid": "c1"})
    c = _call_ev(wb, state="ringing")
    gate("a call rings for the other person", c is not None and c["members"] == [A[1]["id"]]
         and c["by"] == A[1]["id"] and c["kind"] == "video" and c["cid"] == "c1")
    cid = c["id"] if c else ""
    wa.send({"type": "call_start", "chat": dm["id"], "kind": "audio", "cid": "c2"})
    err = _error(wa)
    gate("a second call in the chat is refused", bool(err) and err["code"] == "call_exists")
    wc.send({"type": "call_join", "call": cid})
    err = _error(wc)
    gate("a stranger cannot join", bool(err) and err["code"] == "not_member", str(err))

    # join -> live, signals between the two only
    wb.send({"type": "call_join", "call": cid})
    c = _call_ev(wa, cid, "live")
    gate("the call goes live with both", c is not None and sorted(c["members"]) ==
         sorted([A[1]["id"], B[1]["id"]]) and c["answered_at"])
    wb.send({"type": "call_signal", "call": cid, "to": A[1]["id"], "data": {"sdp": "offer-x"}})
    ev, _ = wa.until(lambda e: e.get("kind") == "call_signal", 5)
    gate("a signal reaches the other member", bool(ev) and ev["from"] == B[1]["id"]
         and ev["data"] == {"sdp": "offer-x"} and "seq" not in ev)
    wb.send({"type": "call_signal", "call": cid, "to": C[1]["id"], "data": {"x": 1}})
    err = _error(wb)
    gate("a signal to someone outside the call is refused", bool(err) and err["code"] == "not_in_call")
    wb.send({"type": "call_signal", "call": cid, "to": A[1]["id"], "data": {"x": "y" * 70000}})
    err = _error(wb)
    gate("a signal over 64 KB is refused", bool(err) and err["code"] == "too_big")

    # leave -> ended, the call line
    wb.send({"type": "call_leave", "call": cid})
    c = _call_ev(wa, cid, "ended")
    gate("the last but one leaving ends the call", c is not None and c["ended_at"])
    ev, _ = wa.until(lambda e: e.get("kind") == "message" and (e["message"].get("call") or {}).get("id") == cid, 5)
    note = ev["message"]["call"] if ev else {}
    gate("the call line lands in the chat", bool(ev) and note.get("answered") is True
         and note.get("kind") == "video" and isinstance(note.get("seconds"), int)
         and ev["message"]["from_id"] == A[1]["id"] and ev["message"]["text"] == "")

    # decline -> ended, not answered
    wa.send({"type": "call_start", "chat": dm["id"], "kind": "audio", "cid": "c3"})
    c = _call_ev(wb, state="ringing")
    wb.send({"type": "call_decline", "call": c["id"]})
    c2 = _call_ev(wa, c["id"], "ended")
    ev, _ = wa.until(lambda e: e.get("kind") == "message" and (e["message"].get("call") or {}).get("id") == c["id"], 5)
    gate("a declined call ends, not answered", c2 is not None and bool(ev)
         and ev["message"]["call"]["answered"] is False)

    # nobody answers -> ended after 45 s
    wa.send({"type": "call_start", "chat": dm["id"], "kind": "audio", "cid": "c4"})
    c = _call_ev(wb, state="ringing")
    c2 = _call_ev(wa, c["id"], "ended", seconds=70)
    gate("a call nobody answers ends after 45 s", c2 is not None
         and 44000 <= c2["ended_at"] - c2["started_at"] <= 70000,
         str(c2 and c2["ended_at"] - c2["started_at"]))

    # a member gone for 30 s leaves
    wa.send({"type": "call_start", "chat": dm["id"], "kind": "audio", "cid": "c5"})
    c = _call_ev(wb, state="ringing")
    wb.send({"type": "call_join", "call": c["id"]})
    _call_ev(wa, c["id"], "live")
    wb.close()
    c2 = _call_ev(wa, c["id"], "ended", seconds=70)
    gate("a member gone for 30 s leaves, and alone the call ends", c2 is not None)

    # the 5th person is refused
    more = [Users.make("cd"), Users.make("ce")]
    group = _make_group(A[0], [B[1]["id"], C[1]["id"]] + [m[1]["id"] for m in more])
    socks = [ws(t) for t, _u in [B, C] + more]
    for w, (t, _u) in zip(socks, [B, C] + more):
        _hello(w, t)
    wa.send({"type": "call_start", "chat": group["id"], "kind": "audio", "cid": "c6"})
    c = _call_ev(socks[0], state="ringing")
    for w in socks[:3]:
        w.send({"type": "call_join", "call": c["id"]})
    full = _call_ev(wa, c["id"], "live", seconds=8)
    socks[3].send({"type": "call_join", "call": c["id"]})
    err = _error(socks[3])
    gate("a 5th person is refused", bool(err) and err["code"] == "call_full")
    for w in socks:
        w.send({"type": "call_leave", "call": c["id"]})
    wa.send({"type": "call_leave", "call": c["id"]})
    for w in [wa, wc] + socks:
        try:
            w.close()
        except Exception:
            pass
```

`_make_group(token, member_ids)` creates a group chat the way this file already does (search the file for `"kind": "group"` and reuse that call exactly; if no phase creates a group, use `jcall("POST", "/v1/chats", token, {"kind": "group", "name": "zzt calls", "members": member_ids})` after checking `server/chat/worker.js`'s chat-creation handler for the field names). `_hello` must use the same way of reading the newest seq that `phase_react` uses; adjust it to match. Register `"calls": phase_calls` in `PHASES`.

- [ ] **Step 2: Run the phase against staging to see it fail**

Run: `$env:CHAT_SERVER='https://skeldar-chat-staging.skeldar.workers.dev'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs\superpowers\plans\verify_chat_server.py calls`
Expected: FAIL gates (`Unknown message call_start`).

- [ ] **Step 3: Implement the calls in `worker.js`**

Constants beside the others:

```js
// Calls (2026-10-22): voice/video/screen through WebRTC between the members; the server keeps the
// call and relays the set-up messages. Spec: docs/superpowers/specs/2026-10-22-chat-calls-design.md
const CALL_MAX = 4;
const RING_MS = 45000;
const GONE_MS = 30000;
const SIGNAL_MAX = 64 * 1024;
```

Two tables in `SCHEMA`:

```js
  `CREATE TABLE IF NOT EXISTS calls (id TEXT PRIMARY KEY, chat TEXT NOT NULL, by TEXT NOT NULL, kind TEXT NOT NULL,
     cid TEXT, state TEXT NOT NULL, started_at INTEGER NOT NULL, answered_at INTEGER, ended_at INTEGER)`,
  `CREATE INDEX IF NOT EXISTS calls_chat ON calls (chat, state)`,
  `CREATE TABLE IF NOT EXISTS call_members (call TEXT NOT NULL, uid TEXT NOT NULL, joined_at INTEGER NOT NULL,
     left_at INTEGER, gone_at INTEGER, declined INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (call, uid))`,
```

In the constructor, beside the `file` column:

```js
    try { this.sql.exec("ALTER TABLE messages ADD COLUMN call TEXT"); } catch { /* there already */ }
```

`messageView` gains the call line:

```js
                  deleted: !!r.deleted, file: r.file && !r.deleted ? this.fileView(r.file) : null,
                  call: r.call ? JSON.parse(r.call) : null };
```

The dispatch table in `webSocketMessage`:

```js
      const handler = { hello: this.onHello, send: this.onSend, edit: this.onEdit, delete: this.onDelete,
                        read: this.onRead, typing: this.onTyping, react: this.onReact,
                        call_start: this.onCallStart, call_join: this.onCallJoin, call_leave: this.onCallLeave,
                        call_decline: this.onCallDecline, call_signal: this.onCallSignal }[msg.type];
```

`connect` clears the person's gone marks (after `acceptWebSocket`):

```js
    this.sql.exec("UPDATE call_members SET gone_at = NULL WHERE uid = ? AND left_at IS NULL", me.id);
```

`webSocketClose`, inside `if (!others.length && ...)`, after `announce`:

```js
      const now = Date.now();
      const marked = this.sql.exec(`UPDATE call_members SET gone_at = ? WHERE uid = ? AND left_at IS NULL AND gone_at IS NULL
         AND call IN (SELECT id FROM calls WHERE state != 'ended') RETURNING call`, now, uid).toArray();
      if (marked.length) this.wake(now + GONE_MS);
```

`webSocketClose` is not async today; `wake` returns a promise the runtime finishes (a DO keeps running unawaited storage calls in order); if the implementer prefers, make `webSocketClose` `async` and `await` it — both are fine.

The calls section (put it after the reactions handlers):

```js
  // ---------------------------------------------------------------- calls
  callView(id) {
    const c = this.sql.exec("SELECT * FROM calls WHERE id = ?", id).toArray()[0];
    if (!c) return null;
    const rows = this.sql.exec("SELECT uid, left_at, declined FROM call_members WHERE call = ? ORDER BY joined_at", id).toArray();
    return { id: c.id, chat: c.chat, by: c.by, kind: c.kind, cid: c.cid, state: c.state,
             members: rows.filter((r) => r.left_at == null && !r.declined).map((r) => r.uid),
             declined: rows.filter((r) => r.declined).map((r) => r.uid),
             started_at: c.started_at, answered_at: c.answered_at ?? null, ended_at: c.ended_at ?? null };
  }

  emitCall(id) {
    const view = this.callView(id);
    if (view) this.emit({ chat: view.chat, kind: "call", payload: { call: view } });
  }

  liveCall(id) {
    const c = this.sql.exec("SELECT * FROM calls WHERE id = ?", id).toArray()[0];
    if (!c || c.state === "ended") refuse("no_call", "This call has ended", 404);
    return c;
  }

  async onCallStart(ws, me, msg) {
    this.limit(me.id + ":call", 10);
    const chat = String(msg.chat ?? "");
    const kind = msg.kind === "video" || msg.kind === "audio" ? msg.kind : refuse("bad_request", "A call is audio or video");
    const cid = String(msg.cid ?? "").slice(0, 64);
    this.writable(chat, me);
    if (this.sql.exec("SELECT 1 FROM calls WHERE chat = ? AND state != 'ended'", chat).toArray().length) {
      refuse("call_exists", "This chat already has a call - join it");
    }
    const id = randomHex(8);
    const now = Date.now();
    this.sql.exec("INSERT INTO calls (id, chat, by, kind, cid, state, started_at) VALUES (?, ?, ?, ?, ?, 'ringing', ?)",
      id, chat, me.id, kind, cid, now);
    this.sql.exec("INSERT INTO call_members (call, uid, joined_at) VALUES (?, ?, ?)", id, me.id, now);
    this.emitCall(id);
    await this.wake(now + RING_MS);
  }

  onCallJoin(ws, me, msg) {
    this.limit(me.id + ":call", 10);
    const c = this.liveCall(String(msg.call ?? ""));
    this.member(c.chat, me.id);
    const view = this.callView(c.id);
    if (view.members.includes(me.id)) return;
    if (view.members.length >= CALL_MAX) refuse("call_full", "A call holds at most " + CALL_MAX + " people");
    const now = Date.now();
    this.sql.exec(`INSERT INTO call_members (call, uid, joined_at) VALUES (?, ?, ?)
       ON CONFLICT (call, uid) DO UPDATE SET joined_at = excluded.joined_at, left_at = NULL, gone_at = NULL, declined = 0`,
      c.id, me.id, now);
    if (c.state === "ringing") this.sql.exec("UPDATE calls SET state = 'live', answered_at = ? WHERE id = ?", now, c.id);
    this.emitCall(c.id);
  }

  onCallDecline(ws, me, msg) {
    const c = this.liveCall(String(msg.call ?? ""));
    this.member(c.chat, me.id);
    if (this.callView(c.id).members.includes(me.id)) return;       // in it: hang up instead
    const now = Date.now();
    this.sql.exec(`INSERT INTO call_members (call, uid, joined_at, left_at, declined) VALUES (?, ?, ?, ?, 1)
       ON CONFLICT (call, uid) DO UPDATE SET declined = 1, left_at = excluded.left_at`, c.id, me.id, now, now);
    const declined = new Set(this.callView(c.id).declined);
    const others = this.memberIds(c.chat).filter((u) => u !== c.by);
    if (c.state === "ringing" && others.every((u) => declined.has(u))) this.endCall(c.id);
    else this.emitCall(c.id);
  }

  onCallLeave(ws, me, msg) {
    const c = this.liveCall(String(msg.call ?? ""));
    this.leaveCall(c.id, me.id);
  }

  // Someone leaves; a ringing call ends when its caller hangs up, a live one when one person is left in it.
  leaveCall(id, uid) {
    const c = this.sql.exec("SELECT * FROM calls WHERE id = ?", id).toArray()[0];
    if (!c || c.state === "ended") return;
    this.sql.exec("UPDATE call_members SET left_at = ? WHERE call = ? AND uid = ? AND left_at IS NULL", Date.now(), id, uid);
    const view = this.callView(id);
    if ((c.state === "ringing" && uid === c.by) || (c.state === "live" && view.members.length <= 1)
        || !view.members.length) this.endCall(id);
    else this.emitCall(id);
  }

  endCall(id) {
    const c = this.sql.exec("SELECT * FROM calls WHERE id = ?", id).toArray()[0];
    if (!c || c.state === "ended") return;
    const now = Date.now();
    this.sql.exec("UPDATE calls SET state = 'ended', ended_at = ? WHERE id = ?", now, id);
    this.sql.exec("UPDATE call_members SET left_at = ? WHERE call = ? AND left_at IS NULL", now, id);
    this.emitCall(id);
    const answered = c.answered_at != null;
    this.postCallLine(c.chat, c.by, { id, kind: c.kind, answered,
                                       seconds: answered ? Math.round((now - c.answered_at) / 1000) : 0 });
  }

  // The call's line in the chat: a message from the caller with no text and the call's note.
  postCallLine(chat, by, note) {
    if (!this.sql.exec("SELECT 1 FROM chats WHERE id = ?", chat).toArray().length) return;
    const message = this.ctx.storage.transactionSync(() => {
      const seq = this.sql.exec("UPDATE chats SET last_seq = last_seq + 1 WHERE id = ? RETURNING last_seq", chat).one().last_seq;
      const id = randomHex(8);
      this.sql.exec("INSERT INTO messages (chat, seq, id, from_id, cid, text, reply_to, at, call) VALUES (?, ?, ?, ?, ?, '', NULL, ?, ?)",
        chat, seq, id, by, "call:" + note.id, Date.now(), JSON.stringify(note));
      return this.messageView(this.sql.exec("SELECT * FROM messages WHERE id = ?", id).one());
    });
    this.emit({ chat, kind: "message", payload: { message } });
  }

  onCallSignal(ws, me, msg) {
    this.limit(me.id + ":signal", 200);
    const c = this.liveCall(String(msg.call ?? ""));
    const members = this.callView(c.id).members;
    const to = String(msg.to ?? "");
    if (to === me.id || !members.includes(me.id) || !members.includes(to)) {
      refuse("not_in_call", "Both people must be in the call");
    }
    if (!msg.data || typeof msg.data !== "object" || Array.isArray(msg.data)) refuse("bad_request", "A signal carries an object");
    if (JSON.stringify(msg.data).length > SIGNAL_MAX) refuse("too_big", "A signal is at most 64 KB");
    this.deliver({ kind: "call_signal", call: c.id, from: me.id, data: msg.data }, [to]);
  }

  // The timer: the earliest of the next daily sweep and the next call deadline.
  async wake(at) {
    const current = await this.ctx.storage.getAlarm();
    if (current == null || at < current) await this.ctx.storage.setAlarm(at);
  }

  sweepCalls(now) {
    for (const c of this.sql.exec("SELECT id FROM calls WHERE state = 'ringing' AND started_at <= ?", now - RING_MS).toArray()) {
      this.endCall(c.id);
    }
    const gone = this.sql.exec(`SELECT call, uid FROM call_members WHERE left_at IS NULL AND gone_at IS NOT NULL AND gone_at <= ?
       AND call IN (SELECT id FROM calls WHERE state != 'ended')`, now - GONE_MS).toArray();
    for (const m of gone) this.leaveCall(m.call, m.uid);
  }

  nextCallDeadline(now) {
    const ring = this.sql.exec("SELECT MIN(started_at) AS t FROM calls WHERE state = 'ringing'").one().t;
    const gone = this.sql.exec(`SELECT MIN(gone_at) AS t FROM call_members WHERE left_at IS NULL AND gone_at IS NOT NULL
       AND call IN (SELECT id FROM calls WHERE state != 'ended')`).one().t;
    const times = [ring != null ? ring + RING_MS : null, gone != null ? gone + GONE_MS : null].filter((t) => t != null);
    return times.length ? Math.max(now + 1000, Math.min(...times)) : null;
  }
```

Replace `alarm()`:

```js
  async alarm() {
    const now = Date.now();
    this.sweepCalls(now);
    let daily = (await this.ctx.storage.get("daily_at")) ?? 0;
    if (daily <= now) {
      this.sql.exec("DELETE FROM events WHERE at < ?", now - KEEP_EVENTS);
      try { await this.sweepFiles(now); } catch { /* the next alarm tries again */ }
      daily = now + DAY;
      await this.ctx.storage.put("daily_at", daily);
    }
    const next = this.nextCallDeadline(now);
    await this.ctx.storage.setAlarm(next != null ? Math.min(daily, next) : daily);
  }
```

Notes on behaviour the spec states differently: the spec says "a call ends when its last member leaves"; here a **live** call also ends when one person is left in it (alone there is nobody to talk to; a 1:1 call ends when either hangs up). Keep it: the verify gates encode it.

- [ ] **Step 4: Deploy to staging and run the phase, then everything**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' server\chat\deploy.py staging`
Run: `$env:CHAT_SERVER='https://skeldar-chat-staging.skeldar.workers.dev'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs\superpowers\plans\verify_chat_server.py calls` → every gate PASS (it takes about 2 minutes: the 45 s ring and the 30 s gone wait).
Run the same with `all` → 0 failed (the old phases still pass).
If the deploy refuses, read the Cloudflare error it prints (a syntax error in `worker.js` comes back as a 10021-style validation error with the line) and fix.

- [ ] **Step 5: Commit**

`git add server/chat/worker.js docs/superpowers/plans/verify_chat_server.py`; message `feat(chat server): calls - ring, join, leave, decline, relayed set-up messages, the call line`.

---

### Task 2: TURN credentials and the key

**Files:**
- Modify: `server/chat/worker.js` (`ROUTES` ~925, a `turn` handler)
- Modify: `server/chat/deploy.py` (`metadata`, `deploy`, a `turn` command, the saved keys)
- Modify: `tests/test_chat_deploy.py`
- Modify: `docs/superpowers/plans/verify_chat_server.py` (phase `turn`)

**Interfaces:**
- Produces: `GET /v1/turn` → `{"ice_servers": [{"urls": [...], "username"?: str, "credential"?: str}, ...], "ttl": int seconds, "turn": bool}`; `deploy.metadata(with_migration, bucket=None, secrets=None)`; `deploy.turn(env=os.environ, opener=urlopen)`; the saved keys file gains `turn_key_id`, `turn_key_token`.

- [ ] **Step 1: Failing tests for deploy.py**

Read `tests/test_chat_deploy.py` (its `Opener` fake, `ok()`, `bad()`, `Metadata`, and how `keys`/`saved` are tested with a temp `KEYS_FILE`). Add:

```python
class Secrets(unittest.TestCase):
    def test_no_secrets_keeps_the_bindings_as_they_were(self):
        self.assertEqual(deploy.metadata(True)["bindings"],
                         [{"type": "durable_object_namespace", "name": "STUDIO", "class_name": "Studio"}])

    def test_secrets_are_secret_text_bindings(self):
        meta = deploy.metadata(False, secrets={"TURN_KEY_ID": "k1", "TURN_KEY_TOKEN": "t1"})
        self.assertIn({"type": "secret_text", "name": "TURN_KEY_ID", "text": "k1"}, meta["bindings"])
        self.assertIn({"type": "secret_text", "name": "TURN_KEY_TOKEN", "text": "t1"}, meta["bindings"])


class TurnKey(unittest.TestCase):
    def test_creates_the_key_and_saves_it(self):
        # an Opener answering POST .../calls/turn_keys with {"result": {"uid": "u"*32, "key": "k"*64}}
        ...
```

Write `test_creates_the_key_and_saves_it` concretely with this file's `Opener` (route `("POST", "/accounts/acc1/calls/turn_keys")` → `ok({"uid": "u" * 32, "key": "k" * 64, "name": "skeldar-chat"})`), the account and token supplied the way the existing `keys`/`deploy` tests supply them, and a temp keys file; assert `deploy.saved()["turn_key_id"] == "u" * 32` and `["turn_key_token"] == "k" * 64`. Add `test_a_token_without_calls_rights_says_so`: the Opener answers that URL with `bad(10000, "Authentication error")` (use the file's `bad` helper with whatever arguments it takes) and `deploy.turn(...)` raises `DeployError` whose text names "Calls Write". Add `test_deploy_sends_saved_turn_secrets`: with the keys file holding both, the multipart upload's metadata (capture it in the Opener) contains the two `secret_text` bindings.

- [ ] **Step 2: Run them to see them fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_chat_deploy -v` → the new tests FAIL / ERROR.

- [ ] **Step 3: Implement in deploy.py**

```python
def metadata(with_migration, bucket=None, secrets=None):
    ...existing body building meta...
    for name, text in sorted((secrets or {}).items()):
        if text:
            meta["bindings"].append({"type": "secret_text", "name": name, "text": text})
    return meta


TURN_NAME = "skeldar-chat"


def turn(env=os.environ, opener=urlopen):
    """Make a Cloudflare Realtime TURN key and keep it beside the account keys. Needs the API
    token's Calls Write right."""
    token, account = _credentials(env)            # use the helper the other commands use
    try:
        result = request("POST", "%s/accounts/%s/calls/turn_keys" % (API, account), token,
                         {"name": TURN_NAME}, opener=opener)
    except DeployError as exc:
        raise DeployError("Could not make a TURN key (%s). Give the API token the "
                          "'Calls Write' permission (dash.cloudflare.com -> My Profile -> API Tokens) "
                          "and run `deploy.py turn` again." % exc)
    held = saved()
    held.update({"turn_key_id": result["uid"], "turn_key_token": result["key"]})
    _write_saved(held)                            # the function save() uses to write KEYS_FILE
    return result["uid"]
```

Match the real helper names in deploy.py (`_credentials`, `saved`, how `save()` writes the file; if `save()` takes fixed arguments, add a small writer beside it and use it in both). `deploy()` passes `secrets={"TURN_KEY_ID": held.get("turn_key_id"), "TURN_KEY_TOKEN": held.get("turn_key_token")}` from `saved()` into `metadata`. `main` gains `turn`; the docstring's usage lists it. A `DeployError` constructed with one message must still work wherever `.codes` is read (give it a default).

- [ ] **Step 4: The `/v1/turn` route**

In `ROUTES`: `["GET", /^\/v1\/turn$/, "turn"],`. The handler:

```js
  // Connection servers for a call: Cloudflare TURN credentials when the server holds a TURN key,
  // else Cloudflare's STUN alone.
  async turn({ me }) {
    const stun = [{ urls: ["stun:stun.cloudflare.com:3478"] }];
    const id = this.env && this.env.TURN_KEY_ID;
    const token = this.env && this.env.TURN_KEY_TOKEN;
    if (!id || !token) return json({ ice_servers: stun, ttl: 86400, turn: false });
    try {
      const r = await fetch(`https://rtc.live.cloudflare.com/v1/turn/keys/${id}/credentials/generate-ice-servers`, {
        method: "POST", headers: { authorization: "Bearer " + token, "content-type": "application/json" },
        body: JSON.stringify({ ttl: 86400 }) });
      if (!r.ok) throw new Error("HTTP " + r.status);
      const body = await r.json();
      const servers = [].concat(body.iceServers || []).map((s) => ({ ...s,
        urls: [].concat(s.urls || []).filter((u) => !/:53(\?|$)/.test(u)) })).filter((s) => s.urls.length);
      return json({ ice_servers: servers, ttl: 86400, turn: true });
    } catch (e) {
      return json({ ice_servers: stun, ttl: 3600, turn: false, text: "TURN unavailable: " + e.message });
    }
  }
```

- [ ] **Step 5: Verify phase `turn`**

```python
def phase_turn():
    T = Users.make("tu")
    st, body = jcall("GET", "/v1/turn", T[0])
    urls = [u for s in body.get("ice_servers", []) for u in s.get("urls", [])]
    gate("turn answers ICE servers", st == 200 and any(u.startswith("stun:") for u in urls), str(body)[:200])
    if body.get("turn"):
        turns = [s for s in body["ice_servers"] if any(u.startswith("turn") for u in s["urls"])]
        gate("a TURN server with credentials", bool(turns) and all(s.get("username") and s.get("credential") for s in turns))
        gate("no port 53", not any(":53?" in u or u.endswith(":53") for u in urls))
    else:
        print("  (no TURN key on this server: STUN only)", body.get("text", ""))
    st, _ = jcall("GET", "/v1/turn", None)
    gate("turn needs signing in", st == 401)
```

Register `"turn": phase_turn`.

- [ ] **Step 6: Make the key and deploy to staging**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' server\chat\deploy.py turn`. If it fails for the Calls Write right, continue without it (STUN only) and say so in the report — the animator adds the right later; do not ask for or handle any token yourself.
Run: `deploy.py staging`, then `verify_chat_server.py turn calls` against staging → PASS (STUN-only passes too).
Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_chat_deploy -v` → PASS except the known `Keys.test_saved_variables_fill_the_process_environment`, which fails on this machine because the animator's real keys are saved (note it, do not change it).

- [ ] **Step 7: Commit**

`git add server/chat/worker.js server/chat/deploy.py tests/test_chat_deploy.py docs/superpowers/plans/verify_chat_server.py`; message `feat(chat server): TURN credentials for calls, deploy.py makes the key`.

---

### Task 3: Records, the call rules, the preview text

**Files:**
- Modify: `SkeldarAnim/maya_chat/records.py`
- Create: `SkeldarAnim/maya_chat/calls.py`
- Modify: `SkeldarAnim/maya_chat/look.py` (`message_text`)
- Test: `tests/test_chat_calls.py` (create), `tests/test_chat_records.py` (modify: the kinds it pins)

**Interfaces:**
- Consumes: the wire protocol (Task 1).
- Produces:
  - `records.call(d) -> dict` (raises `records.Bad`), `records.call_note(value) -> dict | None`; `records.event()` answers `{"kind": "call", "seq", "call": <view>}` and `{"kind": "call_signal", "call", "from", "data": dict}`; `records.message()` keeps `"call": <note>|None`.
  - `calls.MAX = 4`, `calls.RING_S = 45`, `calls.ICON = "\U0001F4DE"`;
    `calls.merge(calls_by_id, view) -> dict`; `calls.of_chat(calls_by_id, chat) -> view|None` (the chat's call that has not ended);
    `calls.mine(calls_by_id, me) -> view|None` (the call I am in); `calls.ringing_for(calls_by_id, me, now_ms) -> [view]`;
    `calls.can_join(view, me) -> bool`; `calls.start_args(view, me, names, ice_servers, video, mic="", cam="") -> dict`;
    `calls.peer_commands(before, after, me) -> [(name, args)]`; `calls.duration_text(seconds) -> str`; `calls.note_text(note) -> str`.

- [ ] **Step 1: Failing tests**

`tests/test_chat_calls.py`:

```python
"""maya_chat.calls and the call records."""
import subprocess
import sys
import unittest

import tests  # noqa: F401

from maya_chat import calls, records

NOW = 1_800_000_000_000


def view(id="c1", chat="dm", by="a", state="ringing", members=("a",), declined=(), kind="video",
         started=NOW - 5000, answered=None, ended=None, cid="x1"):
    return {"id": id, "chat": chat, "by": by, "kind": kind, "cid": cid, "state": state,
            "members": list(members), "declined": list(declined), "started_at": started,
            "answered_at": answered, "ended_at": ended}


class Records(unittest.TestCase):
    def test_a_call_view(self):
        self.assertEqual(records.call(view()), view())

    def test_a_bad_call_is_bad(self):
        for bad in (dict(view(), state="paused"), dict(view(), kind="fax"), dict(view(), members="a"),
                    {k: v for k, v in view().items() if k != "chat"}):
            with self.assertRaises(records.Bad):
                records.call(bad)

    def test_the_events(self):
        e = records.event({"kind": "call", "seq": 7, "call": view()})
        self.assertEqual((e["kind"], e["seq"], e["call"]["id"]), ("call", 7, "c1"))
        s = records.event({"kind": "call_signal", "call": "c1", "from": "b", "data": {"sdp": "x"}})
        self.assertEqual((s["call"], s["from"], s["data"]), ("c1", "b", {"sdp": "x"}))
        self.assertIsNone(records.event({"kind": "call_signal", "call": "c1", "from": "b", "data": "x"}))
        self.assertIsNone(records.event({"kind": "call", "call": view()}))      # a stored event needs its seq

    def test_a_message_keeps_its_call_note(self):
        m = records.message({"id": "m", "chat": "dm", "seq": 3, "from_id": "a", "cid": "call:c1", "text": "",
                             "reply_to": None, "at": NOW, "edited_at": None, "deleted": False,
                             "call": {"id": "c1", "kind": "audio", "answered": True, "seconds": 75}})
        self.assertEqual(m["call"], {"id": "c1", "kind": "audio", "answered": True, "seconds": 75})
        self.assertIsNone(records.call_note({"id": "c1"}))
        self.assertIsNone(records.call_note(None))


class Rules(unittest.TestCase):
    def test_merge_and_of_chat(self):
        by_id = calls.merge({}, view())
        self.assertEqual(calls.of_chat(by_id, "dm")["id"], "c1")
        by_id = calls.merge(by_id, view(state="ended", ended=NOW))
        self.assertIsNone(calls.of_chat(by_id, "dm"))

    def test_mine(self):
        by_id = calls.merge({}, view(state="live", members=("a", "b")))
        self.assertEqual(calls.mine(by_id, "b")["id"], "c1")
        self.assertIsNone(calls.mine(by_id, "z"))

    def test_ringing_for_me(self):
        by_id = calls.merge({}, view())
        self.assertEqual([c["id"] for c in calls.ringing_for(by_id, "b", NOW)], ["c1"])
        self.assertEqual(calls.ringing_for(by_id, "a", NOW), [])                  # my own call
        self.assertEqual(calls.ringing_for(calls.merge({}, view(declined=("b",))), "b", NOW), [])
        self.assertEqual(calls.ringing_for(calls.merge({}, view(started=NOW - 46000)), "b", NOW), [])
        self.assertEqual(calls.ringing_for(calls.merge({}, view(state="live", members=("a", "c"))), "b", NOW), [])

    def test_can_join(self):
        self.assertTrue(calls.can_join(view(state="live", members=("a", "c")), "b"))
        self.assertFalse(calls.can_join(view(state="live", members=("a", "c", "d", "e")), "b"))
        self.assertFalse(calls.can_join(view(state="ended"), "b"))
        self.assertFalse(calls.can_join(view(members=("a", "b")), "b"))

    def test_the_joiner_offers_to_everyone_already_in(self):
        args = calls.start_args(view(state="live", members=("a", "c", "b")), "b", {"a": "Ann"},
                                [{"urls": ["stun:x"]}], True, mic="m1")
        self.assertEqual(args["me"], "b")
        self.assertEqual(sorted(args["peers"]), ["a", "c"])
        self.assertEqual(sorted(args["offer_to"]), ["a", "c"])
        self.assertEqual((args["video"], args["mic"], args["cam"]), (True, "m1", ""))
        self.assertEqual(calls.start_args(view(), "a", {}, [], False)["peers"], [])

    def test_peer_commands(self):
        cmds = calls.peer_commands(["a", "b"], ["a", "b", "c"], "a")
        self.assertEqual(cmds, [("add_peer", {"uid": "c", "offer": False})])
        cmds = calls.peer_commands(["a", "b", "c"], ["a", "c"], "a")
        self.assertEqual(cmds, [("remove_peer", {"uid": "b"})])
        self.assertEqual(calls.peer_commands(["a"], ["a"], "a"), [])

    def test_texts(self):
        self.assertEqual(calls.duration_text(42), "42 с")
        self.assertEqual(calls.duration_text(61), "1 мин")
        self.assertEqual(calls.duration_text(3600 + 120), "62 мин")
        self.assertEqual(calls.note_text({"id": "c", "kind": "audio", "answered": True, "seconds": 300}),
                         "Звонок · 5 мин")
        self.assertEqual(calls.note_text({"id": "c", "kind": "video", "answered": False, "seconds": 0}),
                         "Пропущенный звонок")
        self.assertEqual(calls.note_text(None), "")

    def test_stdlib_only(self):
        code = "import sys; import maya_chat.calls, maya_chat.records; " \
               "print([m for m in sys.modules if m.startswith(('PySide', 'maya.', 'shiboken'))])"
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                             cwd=tests.PLUGIN if hasattr(tests, "PLUGIN") else None)
        self.assertEqual(out.stdout.strip(), "[]", out.stderr)
```

For `test_stdlib_only`, copy how `tests/test_chat_records.py::test_imports_nothing_of_maya_or_qt` runs its subprocess (its cwd / sys.path setup) instead of the guess above.

Also in `tests/test_chat_look.py` (or this file) add:

```python
    def test_the_preview_of_a_call_line(self):
        from maya_chat import look
        m = {"id": "m", "text": "", "call": {"id": "c", "kind": "audio", "answered": False, "seconds": 0}}
        self.assertEqual(look.message_text(m), "\U0001F4DE Пропущенный звонок")
```

- [ ] **Step 2: Run them to see them fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_chat_calls -v` → ERROR (`No module named maya_chat.calls`).

- [ ] **Step 3: records.py**

Read the module's helpers (`_str`, `_int`, `_opt_str`, `_dict`, `Bad`) and use them; the shape to produce:

```python
CALL_STATES = ("ringing", "live", "ended")
CALL_KINDS = ("audio", "video")


def _uids(value):
    if not isinstance(value, list) or not all(isinstance(u, str) and u for u in value):
        raise Bad("a list of user ids")
    return list(value)


def call(d):
    """A call's view: {id, chat, by, kind, cid, state, members, declined, started_at, answered_at,
    ended_at}. Raises Bad."""
    if not isinstance(d, dict):
        raise Bad("call")
    state, kind = d.get("state"), d.get("kind")
    if state not in CALL_STATES or kind not in CALL_KINDS:
        raise Bad("call state or kind")
    out = {"id": _str(d, "id"), "chat": _str(d, "chat"), "by": _str(d, "by"), "kind": kind,
           "cid": d.get("cid") if isinstance(d.get("cid"), str) else "", "state": state,
           "members": _uids(d.get("members")), "declined": _uids(d.get("declined") or []),
           "started_at": _int(d, "started_at"),
           "answered_at": d.get("answered_at") if isinstance(d.get("answered_at"), int) else None,
           "ended_at": d.get("ended_at") if isinstance(d.get("ended_at"), int) else None}
    return out


def call_note(value):
    """A message's call line {id, kind, answered, seconds}, or None (a bad one too)."""
    if not isinstance(value, dict) or not isinstance(value.get("id"), str) \
            or value.get("kind") not in CALL_KINDS or not isinstance(value.get("answered"), bool) \
            or not isinstance(value.get("seconds"), int) or value["seconds"] < 0:
        return None
    return {"id": value["id"], "kind": value["kind"], "answered": value["answered"], "seconds": value["seconds"]}
```

(Adapt `_str(d, "id")` / `_int(...)` to the helpers' real signatures.) Add `"call"` to `SEQ_KINDS`, `"call_signal"` to `LIVE_KINDS`; in `event()`:

```python
        elif kind == "call":
            out["call"] = call(d.get("call"))
        elif kind == "call_signal":
            if not isinstance(d.get("data"), dict):
                raise Bad("signal data")
            out.update({"call": _str(d, "call"), "from": _str(d, "from"), "data": d["data"]})
```

`message()` adds `"call": call_note(d.get("call"))`. Update `tests/test_chat_records.py`'s pinned kind lists for the two new kinds.

- [ ] **Step 4: calls.py**

```python
"""The chat's calls: rules over the server's call views. Stdlib only.

Spec: docs/superpowers/specs/2026-10-22-chat-calls-design.md
"""
MAX = 4
RING_S = 45
ICON = "\U0001F4DE"


def merge(calls, view):
    """The calls by id with `view` put in."""
    out = dict(calls or {})
    out[view["id"]] = view
    return out


def of_chat(calls, chat):
    """The chat's call that has not ended, newest first; None."""
    found = [c for c in (calls or {}).values() if c["chat"] == chat and c["state"] != "ended"]
    return max(found, key=lambda c: c["started_at"]) if found else None


def mine(calls, me):
    """The call I am in; None."""
    found = [c for c in (calls or {}).values() if c["state"] != "ended" and me in c["members"]]
    return max(found, key=lambda c: c["started_at"]) if found else None


def ringing_for(calls, me, now_ms):
    """Calls ringing for me: somebody else's, not answered by me, not declined, under RING_S old."""
    return sorted((c for c in (calls or {}).values()
                   if c["state"] == "ringing" and c["by"] != me and me not in c["members"]
                   and me not in c["declined"] and now_ms - c["started_at"] < RING_S * 1000),
                  key=lambda c: c["started_at"])


def can_join(view, me):
    return bool(view) and view["state"] != "ended" and me not in view["members"] \
        and len(view["members"]) < MAX


def start_args(view, me, names, ice_servers, video, mic="", cam=""):
    """The page's `start` command when I come into `view` (my own join already in it): I offer to
    everybody already there."""
    others = [u for u in view["members"] if u != me]
    return {"me": me, "names": dict(names or {}), "ice_servers": list(ice_servers or []),
            "video": bool(video), "peers": others, "offer_to": list(others), "mic": mic or "",
            "cam": cam or ""}


def peer_commands(before, after, me):
    """The page's commands when the members change: a newcomer offers to me (add_peer, offer False);
    one who left goes."""
    before, after = [u for u in before if u != me], [u for u in after if u != me]
    out = [("add_peer", {"uid": u, "offer": False}) for u in after if u not in before]
    out += [("remove_peer", {"uid": u}) for u in before if u not in after]
    return out


def duration_text(seconds):
    seconds = max(0, int(seconds or 0))
    return "%d с" % seconds if seconds < 60 else "%d мин" % (seconds // 60)


def note_text(note):
    """A call line's words: «Звонок · 5 мин» or «Пропущенный звонок»."""
    if not note:
        return ""
    if note.get("answered"):
        return "Звонок · " + duration_text(note.get("seconds"))
    return "Пропущенный звонок"
```

- [ ] **Step 5: look.message_text**

At the top of `look.message_text(message)`:

```python
    note = message.get("call")
    if note:
        from . import calls
        return calls.ICON + " " + calls.note_text(note)
```

- [ ] **Step 6: Run the tests**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_chat_calls tests.test_chat_records tests.test_chat_look -v` → PASS.

- [ ] **Step 7: Commit**

`git add SkeldarAnim/maya_chat/records.py SkeldarAnim/maya_chat/calls.py SkeldarAnim/maya_chat/look.py tests/test_chat_calls.py tests/test_chat_records.py tests/test_chat_look.py`; message `feat(chat calls): the call records and rules`.

---

### Task 4: The session's calls

**Files:**
- Modify: `SkeldarAnim/maya_chat/api.py` (`turn`), `SkeldarAnim/maya_chat/session.py`
- Test: `tests/test_chat_session.py` (add a class `Calls`)

**Interfaces:**
- Consumes: `records.call`, `calls.merge` (Task 3).
- Produces:
  - `Api.turn() -> dict` (`GET /v1/turn`).
  - `State.calls: dict` (id → view).
  - `Session.start_call(chat, kind) -> cid` (raises `ChatError("offline", ...)` when the socket is down);
    `Session.join_call(call_id) -> cid`; `Session.decline_call(call_id) -> cid`;
    `Session.leave_call(call_id) -> bool` (False offline, no raise); `Session.call_signal(call_id, to, data) -> bool`;
    `Session.turn_servers(now=None) -> (ice_servers list, turn bool)`.
  - Listeners hear `("call", event)` for every call view and `("call_signal", event)` for relayed messages; a refusal of a call frame arrives as `("error", event)` with the frame's `cid`.

- [ ] **Step 1: Failing tests**

In `tests/test_chat_session.py` (use its `Base.session()`, `FakeLink.frames()`, `Base.frame()`; give `FakeApi` a `turn()` returning `{"ice_servers": [{"urls": ["turn:x"], "username": "u", "credential": "p"}], "ttl": 86400, "turn": True}` and counting calls):

```python
class Calls(Base):
    def setUp(self):
        Base.setUp(self)
        self.ses = self.session()
        self.frame(self.ses, {"kind": "caught_up", "seq": 1})

    def view(self, **kw):
        v = {"id": "c1", "chat": "dm", "by": "me", "kind": "video", "cid": "x", "state": "ringing",
             "members": ["me"], "declined": [], "started_at": 1, "answered_at": None, "ended_at": None}
        v.update(kw)
        return v

    def test_start_sends_the_frame_with_a_cid(self):
        cid = self.ses.start_call("dm", "video")
        sent = [f for f in self.ses.link.frames() if f.get("type") == "call_start"]
        self.assertEqual(sent, [{"type": "call_start", "chat": "dm", "kind": "video", "cid": cid}])

    def test_join_decline_leave_signal(self):
        self.ses.join_call("c1")
        self.ses.decline_call("c2")
        self.assertTrue(self.ses.leave_call("c1"))
        self.assertTrue(self.ses.call_signal("c1", "bob", {"sdp": "o"}))
        kinds = [(f["type"], f.get("call")) for f in self.ses.link.frames() if f["type"].startswith("call_")]
        self.assertEqual(kinds, [("call_join", "c1"), ("call_decline", "c2"), ("call_leave", "c1"),
                                 ("call_signal", "c1")])
        sig = [f for f in self.ses.link.frames() if f["type"] == "call_signal"][0]
        self.assertEqual((sig["to"], sig["data"]), ("bob", {"sdp": "o"}))

    def test_offline_start_raises_and_leave_is_quiet(self):
        self.ses.protocol.open = False        # use whatever marks the Protocol closed in link.py
        with self.assertRaises(Exception):
            self.ses.start_call("dm", "audio")
        self.assertFalse(self.ses.leave_call("c1"))

    def test_call_events_keep_the_state_and_are_told(self):
        self.frame(self.ses, {"kind": "call", "seq": 2, "call": self.view()})
        self.assertEqual(self.ses.state.calls["c1"]["state"], "ringing")
        self.frame(self.ses, {"kind": "call", "seq": 3, "call": self.view(state="live", members=["me", "bob"])})
        self.assertEqual(self.ses.state.calls["c1"]["members"], ["me", "bob"])
        self.assertIn("call", self.told)

    def test_signals_are_told_not_kept(self):
        self.frame(self.ses, {"kind": "call_signal", "call": "c1", "from": "bob", "data": {"ice": {}}})
        self.assertIn("call_signal", self.told)

    def test_turn_servers_are_cached(self):
        servers, turn = self.ses.turn_servers(now=1000.0)
        servers2, _ = self.ses.turn_servers(now=2000.0)
        self.assertTrue(turn)
        self.assertEqual(servers, servers2)
        self.assertEqual(self.ses.api.turn_calls, 1)
        self.ses.turn_servers(now=1000.0 + 86400 - 3000)     # within an hour of expiry: asked again
        self.assertEqual(self.ses.api.turn_calls, 2)

    def test_turn_failure_falls_back_to_stun(self):
        def boom():
            from maya_chat.api import ChatError
            raise ChatError("offline", "no")
        self.ses.api.turn = boom
        servers, turn = self.ses.turn_servers(now=5.0)
        self.assertFalse(turn)
        self.assertEqual(servers, [{"urls": ["stun:stun.cloudflare.com:3478"]}])
```

Adapt `test_offline_start_raises_and_leave_is_quiet` to how `Protocol.push` reports "not open" (read `link.py`: `push` returns False when the socket is not open — set whatever field makes it so, or stop the link).

- [ ] **Step 2: Run to see them fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_chat_session.Calls -v` → ERROR.

- [ ] **Step 3: Implement**

`api.py`: `def turn(self): return self.call("GET", "/v1/turn")`.

`session.py`:

```python
STUN = [{"urls": ["stun:stun.cloudflare.com:3478"]}]
TURN_EARLY_S = 3600          # ask again an hour before the credentials expire
TURN_RETRY_S = 300           # after a failure, STUN for five minutes
```

`State.__init__` gains `self.calls = {}`. In `Session`:

```python
    # ------------------------------------------------------------ calls (2026-10-22)
    def _call_frame(self, frame, must=True):
        self._need()
        frame = dict(frame, cid="call-" + uuid.uuid4().hex[:16])
        if not self.protocol.push(frame):
            if must:
                raise _api.ChatError("offline", "Нет связи с сервером")
            return None
        return frame["cid"]

    def start_call(self, chat, kind):
        return self._call_frame({"type": "call_start", "chat": chat, "kind": kind})

    def join_call(self, call_id):
        return self._call_frame({"type": "call_join", "call": call_id})

    def decline_call(self, call_id):
        return self._call_frame({"type": "call_decline", "call": call_id}, must=False)

    def leave_call(self, call_id):
        try:
            return self._call_frame({"type": "call_leave", "call": call_id}, must=False) is not None
        except _api.ChatError:
            return False

    def call_signal(self, call_id, to, data):
        if self.protocol is None:
            return False
        return bool(self.protocol.push({"type": "call_signal", "call": call_id, "to": to, "data": data}))

    def turn_servers(self, now=None):
        now = time.time() if now is None else now
        held = getattr(self, "_turn", None)
        if held and now < held[0]:
            return held[1], held[2]
        try:
            body = self.api.turn()
            servers = list(body.get("ice_servers") or STUN)
            ttl = int(body.get("ttl") or 3600)
            self._turn = (now + max(60, ttl - TURN_EARLY_S), servers, bool(body.get("turn")))
        except Exception:                                   # noqa: BLE001 - a call goes on without TURN
            self._turn = (now + TURN_RETRY_S, list(STUN), False)
        return self._turn[1], self._turn[2]

    def _on_call(self, e):
        from . import calls as _calls
        self.state.calls = _calls.merge(self.state.calls, e["call"])
```

(`uuid`, `time` already imported? add if not.) `call_signal` uses the protocol without `_need` so a hang-up during sign-out does not raise. `_on_call_signal` is not needed: `_event` tells every kind.

- [ ] **Step 4: Run the session tests**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_chat_session tests.test_chat_api -v` → PASS.

- [ ] **Step 5: Commit**

`git add SkeldarAnim/maya_chat/api.py SkeldarAnim/maya_chat/session.py tests/test_chat_session.py`; message `feat(chat calls): the session starts, joins and leaves calls and relays their set-up`.

---

### Task 5: The call page and its bridge

**Files:**
- Create: `SkeldarAnim/assets/call/call.html`, `call.css`, `call.js`
- Create: `SkeldarAnim/maya_chat/callpage.py`
- Test: `tests/test_chat_callpage.py`
- Create: `docs/superpowers/plans/verify_call_page.py`

**Interfaces:**
- Produces:
  - `callpage.ORIGIN = "https://skeldar.call"`; `callpage.compose(tokens=None) -> str` (the page with CSS, JS and `qwebchannel.js` inlined, the hub's colours as CSS variables);
  - `callpage.bridge_class()` → `Bridge(on_ready, on_signal, on_state, parent=None)`: a QObject named `bridge` on the channel with Qt signal `command(str, str)` and slots `ready()`, `signal(str to, str data_json)`, `state(str json)`, `log(str)`; method `send(name, args_dict)`.
  - `callpage.page_class()` → `CallPage(profile, parent=None)` (QWebEnginePage) granting permissions only to `ORIGIN` (`allowed(origin_url) -> bool`), with a Qt signal `screen_requested(object)` carrying the `QWebEngineDesktopMediaRequest`.
  - `callpage.make_view(bridge, parent=None) -> (QWebEngineView, CallPage)` loading `compose()` at `ORIGIN + "/"` with the bridge on a `QWebChannel`.
  - Page commands (Python → page, `bridge.send(name, args)`): `start` (`calls.start_args`), `add_peer {uid, offer}`, `remove_peer {uid}`, `signal {from, data}`, `mute {on}`, `camera {on}`, `screen {on}`, `devices {mic, cam}`, `names {uid: name}`, `end {}`.
  - Page state (page → Python, `state(json)`), a dict: `{me, mic: bool (on), cam: bool, screen: bool, error: str, note: str, devices: {mics: [{id, label}], cams: [...]}, peers: {uid: {state: "new"|"connecting"|"connected"|"disconnected"|"failed"|"closed", speaking: bool, mic: bool, cam: bool, screen: bool, lost: bool (failed or disconnected over 20 s), bytes: {audio_in, video_in, audio_out, video_out}}}, speaking: bool}`.

- [ ] **Step 1: Failing tests**

`tests/test_chat_callpage.py`:

```python
"""maya_chat.callpage offscreen: the composed page, the bridge, the permissions."""
import json
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tests  # noqa: F401

from PySide6 import QtCore, QtWidgets

from maya_chat import callpage


def _app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


class Compose(unittest.TestCase):
    def test_everything_is_inlined(self):
        _app()
        html = callpage.compose()
        for mark in ("/*CSS*/", "/*JS*/", "/*QWEBCHANNEL*/", "<script src", "<link"):
            self.assertNotIn(mark, html)
        self.assertIn("QWebChannel", html)
        self.assertIn("RTCPeerConnection", html)
        self.assertIn("--accent:", html)


class BridgeTests(unittest.TestCase):
    def test_slots_and_send(self):
        _app()
        got = []
        b = callpage.bridge_class()(lambda: got.append("ready"), lambda to, d: got.append((to, d)),
                                    lambda s: got.append(s))
        sent = []
        b.command.connect(lambda name, args: sent.append((name, json.loads(args))))
        b.ready()
        b.signal("bob", json.dumps({"sdp": "x"}))
        b.state(json.dumps({"mic": True}))
        b.send("mute", {"on": True})
        self.assertEqual(got, ["ready", ("bob", {"sdp": "x"}), {"mic": True}])
        self.assertEqual(sent, [("mute", {"on": True})])

    def test_a_bad_json_from_the_page_is_ignored(self):
        _app()
        got = []
        b = callpage.bridge_class()(lambda: None, lambda to, d: got.append(d), lambda s: got.append(s))
        b.signal("bob", "{not json")
        b.state("nope")
        self.assertEqual(got, [])


class Permissions(unittest.TestCase):
    def test_only_our_origin(self):
        self.assertTrue(callpage.allowed(QtCore.QUrl("https://skeldar.call/")))
        self.assertTrue(callpage.allowed(QtCore.QUrl("https://skeldar.call")))
        self.assertFalse(callpage.allowed(QtCore.QUrl("https://evil.example/")))
        self.assertFalse(callpage.allowed(QtCore.QUrl("http://skeldar.call/")))
```

- [ ] **Step 2: Run to see them fail**

Run: `$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_chat_callpage -v` → ERROR.

- [ ] **Step 3: The page**

`SkeldarAnim/assets/call/call.html`:

```html
<!doctype html>
<html><head><meta charset="utf-8"><title>call</title><style>/*CSS*/</style></head>
<body>
<div id="grid"></div>
<div id="note"></div>
<script>/*QWEBCHANNEL*/</script>
<script>/*JS*/</script>
</body></html>
```

`SkeldarAnim/assets/call/call.css` (the variables come from `compose`):

```css
html, body { margin: 0; height: 100%; background: var(--panel); color: var(--text);
  font: 13px "Segoe UI", sans-serif; overflow: hidden; user-select: none; }
#grid { position: absolute; inset: 6px; display: grid; gap: 6px; grid-template-columns: 1fr; grid-auto-rows: 1fr; }
#grid.n2 { grid-template-columns: 1fr 1fr; }
#grid.n3, #grid.n4 { grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; }
#grid.focus { grid-template-columns: repeat(3, 1fr); grid-template-rows: 1fr 96px; }
#grid.focus .tile.screen { grid-column: 1 / -1; }
.tile { position: relative; background: var(--card); border-radius: 8px; overflow: hidden;
  box-shadow: 0 0 0 1px var(--line) inset; transition: box-shadow 120ms; }
.tile.speaking { box-shadow: 0 0 0 2px var(--accent) inset, 0 0 14px var(--accent); }
.tile video { width: 100%; height: 100%; object-fit: cover; display: block; background: #000; }
.tile.screen video { object-fit: contain; }
.tile.nocam video { display: none; }
.tile .face { position: absolute; inset: 0; display: none; align-items: center; justify-content: center; }
.tile.nocam .face { display: flex; }
.tile .face span { width: 64px; height: 64px; border-radius: 50%; background: var(--accent);
  color: var(--on_accent); display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: 600; }
.tile .name { position: absolute; left: 8px; bottom: 6px; padding: 2px 8px; border-radius: 10px;
  background: rgba(0,0,0,.55); color: #fff; font-size: 12px; }
.tile .muted { display: none; margin-left: 6px; color: var(--danger); }
.tile.micoff .muted { display: inline; }
.tile .lost { position: absolute; inset: 0; display: none; align-items: center; justify-content: center;
  background: rgba(0,0,0,.55); color: #fff; }
.tile.lost .lost { display: flex; }
#note { position: absolute; left: 50%; top: 8px; transform: translateX(-50%); padding: 3px 10px;
  border-radius: 10px; background: rgba(0,0,0,.6); color: #fff; font-size: 12px; display: none; }
#note.on { display: block; }
@media (prefers-reduced-motion: reduce) { .tile { transition: none; } }
```

`SkeldarAnim/assets/call/call.js`:

```js
// The call page (spec docs/superpowers/specs/2026-10-22-chat-calls-design.md): a WebRTC mesh driven
// by Python through the QWebChannel object `bridge`. The joiner offers; the others answer.
"use strict";
const S = { me: null, names: {}, ice: [], peers: new Map(), local: null, camTrack: null, screenTrack: null,
            mic: true, cam: false, screen: false, devices: { mic: "", cam: "" }, list: { mics: [], cams: [] },
            error: "", note: "", bridge: null, audio: null, levels: new Map(), timer: null };
const LOST_MS = 20000;
const SPEAK = 0.035;

function send(to, data) { if (S.bridge) S.bridge.signal(to, JSON.stringify(data)); }
function others(data) { for (const p of S.peers.values()) send(p.uid, data); }

function snapshot() {
  const peers = {};
  for (const p of S.peers.values()) {
    peers[p.uid] = { state: p.pc.connectionState, speaking: !!p.speaking, mic: p.mic, cam: p.cam,
                     screen: p.screen, lost: !!(p.failedAt && Date.now() - p.failedAt > LOST_MS), bytes: p.bytes };
  }
  return { me: S.me, mic: S.mic, cam: S.cam, screen: S.screen, error: S.error, note: S.note,
           devices: S.list, peers, speaking: !!S.speakingMe };
}
let reportQueued = false;
function report() {
  if (reportQueued) return;
  reportQueued = true;
  setTimeout(() => { reportQueued = false; if (S.bridge) S.bridge.state(JSON.stringify(snapshot())); }, 30);
}
function note(text) {
  S.note = text || "";
  const el = document.getElementById("note");
  el.textContent = S.note; el.classList.toggle("on", !!S.note);
  report();
}

// ------------------------------------------------------------------ tiles
function initials(uid) {
  const name = S.names[uid] || uid || "?";
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join("");
}
function tile(uid) {
  let t = document.getElementById("t-" + uid);
  if (!t) {
    t = document.createElement("div");
    t.className = "tile nocam"; t.id = "t-" + uid;
    t.innerHTML = '<video autoplay playsinline></video><div class="face"><span></span></div>' +
                  '<div class="name"><b></b><span class="muted">&#x1F507;</span></div><div class="lost">нет соединения</div>';
    document.getElementById("grid").appendChild(t);
  }
  t.querySelector(".face span").textContent = initials(uid);
  t.querySelector(".name b").textContent = uid === S.me ? (S.names[uid] || "Вы") + " (вы)" : (S.names[uid] || uid);
  layout();
  return t;
}
function showStream(uid, stream, muted) {
  const v = tile(uid).querySelector("video");
  if (v.srcObject !== stream) v.srcObject = stream;
  v.muted = !!muted;
  v.play().catch(() => {});
}
function setTile(uid, flags) {
  const t = tile(uid);
  for (const [cls, on] of Object.entries(flags)) t.classList.toggle(cls, !!on);
  layout();
}
function layout() {
  const g = document.getElementById("grid");
  const n = g.children.length;
  const focus = !!g.querySelector(".tile.screen");
  g.className = focus ? "focus" : "n" + Math.min(4, Math.max(1, n));
}
function dropTile(uid) { const t = document.getElementById("t-" + uid); if (t) t.remove(); layout(); }

// ------------------------------------------------------------------ media
async function userMedia(video) {
  const audio = S.devices.mic ? { deviceId: { exact: S.devices.mic } } : true;
  const cam = S.devices.cam ? { deviceId: { exact: S.devices.cam } } : { width: { ideal: 1280 }, height: { ideal: 720 } };
  if (!video) return navigator.mediaDevices.getUserMedia({ audio });
  try { return await navigator.mediaDevices.getUserMedia({ audio, video: cam }); }
  catch (e) { note("Камера недоступна: " + e.name); return navigator.mediaDevices.getUserMedia({ audio }); }
}
async function listDevices() {
  try {
    const all = await navigator.mediaDevices.enumerateDevices();
    S.list = { mics: all.filter((d) => d.kind === "audioinput").map((d) => ({ id: d.deviceId, label: d.label || "Микрофон" })),
               cams: all.filter((d) => d.kind === "videoinput").map((d) => ({ id: d.deviceId, label: d.label || "Камера" })) };
  } catch (e) { S.list = { mics: [], cams: [] }; }
  report();
}
function videoSender(p) {
  const t = p.pc.getTransceivers().find((x) => x.receiver.track && x.receiver.track.kind === "video");
  return t ? t.sender : null;
}
function audioSender(p) {
  const t = p.pc.getTransceivers().find((x) => x.receiver.track && x.receiver.track.kind === "audio");
  return t ? t.sender : null;
}
function outgoingVideo() { return S.screen && S.screenTrack ? S.screenTrack : (S.cam ? S.camTrack : null); }
async function pushVideo() {
  const track = outgoingVideo();
  for (const p of S.peers.values()) { const s = videoSender(p); if (s) await s.replaceTrack(track); }
  const local = new MediaStream([track].filter(Boolean));
  showStream(S.me, local, true);
  setTile(S.me, { nocam: !track, screen: S.screen });
  others({ cam: !!track, screen: S.screen });
}

// ------------------------------------------------------------------ speaking light
function watchLevel(uid, stream) {
  if (!stream.getAudioTracks().length) return;
  if (!S.audio) S.audio = new AudioContext();
  const src = S.audio.createMediaStreamSource(stream);
  const an = S.audio.createAnalyser(); an.fftSize = 512; src.connect(an);
  S.levels.set(uid, { an, buf: new Float32Array(an.fftSize), since: 0, on: false });
}
function tickLevels() {
  const now = Date.now();
  for (const [uid, l] of S.levels) {
    l.an.getFloatTimeDomainData(l.buf);
    let sum = 0; for (const x of l.buf) sum += x * x;
    const loud = Math.sqrt(sum / l.buf.length) > SPEAK && (uid !== S.me || S.mic);
    if (loud) l.since = now;
    const on = now - l.since < 300;
    if (on !== l.on) {
      l.on = on; setTile(uid, { speaking: on });
      if (uid === S.me) S.speakingMe = on; else if (S.peers.get(uid)) S.peers.get(uid).speaking = on;
      report();
    }
  }
}

// ------------------------------------------------------------------ peers
function addPeer(uid, offer) {
  if (S.peers.has(uid) || uid === S.me) return;
  const pc = new RTCPeerConnection({ iceServers: S.ice });
  const p = { uid, pc, offer, stream: new MediaStream(), pending: [], failedAt: 0, mic: true, cam: false,
              screen: false, speaking: false, bytes: { audio_in: 0, video_in: 0, audio_out: 0, video_out: 0 } };
  S.peers.set(uid, p);
  const audio = S.local.getAudioTracks()[0];
  pc.addTransceiver(audio || "audio", { direction: "sendrecv", streams: [S.local] });
  pc.addTransceiver(outgoingVideo() || "video", { direction: "sendrecv", streams: [S.local] });
  pc.onicecandidate = (ev) => { if (ev.candidate) send(uid, { ice: ev.candidate.toJSON() }); };
  pc.ontrack = (ev) => {
    if (!p.stream.getTracks().includes(ev.track)) p.stream.addTrack(ev.track);
    showStream(uid, p.stream, false);
    if (ev.track.kind === "audio") watchLevel(uid, new MediaStream([ev.track]));
    report();
  };
  pc.onconnectionstatechange = () => {
    const st = pc.connectionState;
    if (st === "failed" || st === "disconnected") { p.failedAt = p.failedAt || Date.now(); if (st === "failed" && p.offer) makeOffer(p, true); }
    else if (st === "connected") { p.failedAt = 0; send(uid, { mic: S.mic, cam: !!outgoingVideo(), screen: S.screen }); }
    setTile(uid, { lost: false });
    report();
  };
  tile(uid);
  setTile(uid, { nocam: true });
  if (offer) makeOffer(p, false);
  report();
}
async function makeOffer(p, restart) {
  const o = await p.pc.createOffer(restart ? { iceRestart: true } : undefined);
  await p.pc.setLocalDescription(o);
  send(p.uid, { sdp: p.pc.localDescription.toJSON() });
}
async function onSignal(from, data) {
  if (!S.local) return;
  let p = S.peers.get(from);
  if (!p) { addPeer(from, false); p = S.peers.get(from); if (!p) return; }
  try {
    if (data.sdp) {
      await p.pc.setRemoteDescription(data.sdp);
      if (data.sdp.type === "offer") {
        const a = await p.pc.createAnswer();
        await p.pc.setLocalDescription(a);
        send(from, { sdp: p.pc.localDescription.toJSON() });
      }
      for (const c of p.pending.splice(0)) await p.pc.addIceCandidate(c).catch(() => {});
    } else if (data.ice) {
      if (p.pc.remoteDescription) await p.pc.addIceCandidate(data.ice).catch(() => {});
      else p.pending.push(data.ice);
    }
    if ("mic" in data) { p.mic = !!data.mic; setTile(from, { micoff: !p.mic }); }
    if ("cam" in data) { p.cam = !!data.cam; setTile(from, { nocam: !p.cam }); }
    if ("screen" in data) { p.screen = !!data.screen; setTile(from, { screen: p.screen }); }
  } catch (e) { S.error = "signal: " + e.message; }
  report();
}
function removePeer(uid) {
  const p = S.peers.get(uid);
  if (!p) return;
  try { p.pc.close(); } catch (e) { /* closed */ }
  S.peers.delete(uid); S.levels.delete(uid); dropTile(uid); report();
}
async function stats() {
  for (const p of S.peers.values()) {
    try {
      const r = await p.pc.getStats();
      const b = { audio_in: 0, video_in: 0, audio_out: 0, video_out: 0 };
      r.forEach((s) => {
        if (s.type === "inbound-rtp") b[s.kind + "_in"] += s.bytesReceived || 0;
        if (s.type === "outbound-rtp") b[s.kind + "_out"] += s.bytesSent || 0;
      });
      p.bytes = b;
    } catch (e) { /* closed */ }
    const lost = !!(p.failedAt && Date.now() - p.failedAt > LOST_MS);
    setTile(p.uid, { lost });
  }
  report();
}

// ------------------------------------------------------------------ commands
const COMMANDS = {
  async start(a) {
    S.me = a.me; S.names = a.names || {}; S.ice = a.ice_servers || []; S.devices = { mic: a.mic || "", cam: a.cam || "" };
    try { S.local = await userMedia(!!a.video); }
    catch (e) { S.error = "Микрофон недоступен: " + e.name; report(); return; }
    S.camTrack = S.local.getVideoTracks()[0] || null;
    S.cam = !!S.camTrack;
    showStream(S.me, new MediaStream(S.local.getVideoTracks()), true);
    setTile(S.me, { nocam: !S.cam });
    watchLevel(S.me, S.local);
    for (const uid of a.peers || []) addPeer(uid, (a.offer_to || []).includes(uid));
    S.timer = setInterval(tickLevels, 80);
    setInterval(stats, 2000);
    await listDevices();
  },
  add_peer(a) { addPeer(a.uid, !!a.offer); },
  remove_peer(a) { removePeer(a.uid); },
  signal(a) { return onSignal(a.from, a.data || {}); },
  mute(a) {
    S.mic = !a.on;
    for (const t of (S.local ? S.local.getAudioTracks() : [])) t.enabled = S.mic;
    setTile(S.me, { micoff: !S.mic }); others({ mic: S.mic }); report();
  },
  async camera(a) {
    if (a.on && !S.camTrack) {
      try {
        const s = await navigator.mediaDevices.getUserMedia({ video: S.devices.cam ? { deviceId: { exact: S.devices.cam } } : true });
        S.camTrack = s.getVideoTracks()[0];
      } catch (e) { note("Камера недоступна: " + e.name); return; }
    }
    S.cam = !!a.on && !!S.camTrack;
    if (S.camTrack) S.camTrack.enabled = S.cam;
    await pushVideo(); report();
  },
  async screen(a) {
    if (a.on) {
      try {
        const s = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: false });
        S.screenTrack = s.getVideoTracks()[0];
        S.screenTrack.onended = () => COMMANDS.screen({ on: false });
        S.screen = true;
      } catch (e) { note(""); S.screen = false; report(); return; }
    } else {
      if (S.screenTrack) { S.screenTrack.onended = null; S.screenTrack.stop(); }
      S.screenTrack = null; S.screen = false;
    }
    await pushVideo(); report();
  },
  async devices(a) {
    S.devices = { mic: a.mic || "", cam: a.cam || "" };
    if (a.mic !== undefined && S.local) {
      try {
        const s = await navigator.mediaDevices.getUserMedia({ audio: S.devices.mic ? { deviceId: { exact: S.devices.mic } } : true });
        const t = s.getAudioTracks()[0]; t.enabled = S.mic;
        for (const old of S.local.getAudioTracks()) { S.local.removeTrack(old); old.stop(); }
        S.local.addTrack(t);
        for (const p of S.peers.values()) { const snd = audioSender(p); if (snd) await snd.replaceTrack(t); }
        watchLevel(S.me, S.local);
      } catch (e) { note("Микрофон не переключился: " + e.name); }
    }
    if (a.cam !== undefined && S.cam) {
      if (S.camTrack) S.camTrack.stop();
      S.camTrack = null;
      await COMMANDS.camera({ on: true });
    }
    report();
  },
  names(a) { S.names = a || {}; for (const t of document.querySelectorAll(".tile")) tile(t.id.slice(2)); },
  end() {
    for (const uid of [...S.peers.keys()]) removePeer(uid);
    for (const t of (S.local ? S.local.getTracks() : [])) t.stop();
    if (S.screenTrack) S.screenTrack.stop();
    if (S.timer) clearInterval(S.timer);
    report();
  },
};

new QWebChannel(qt.webChannelTransport, (channel) => {
  S.bridge = channel.objects.bridge;
  S.bridge.command.connect((name, args) => {
    const fn = COMMANDS[name];
    if (!fn) return;
    let a = {};
    try { a = JSON.parse(args || "{}"); } catch (e) { return; }
    Promise.resolve(fn(a)).catch((e) => { S.error = name + ": " + e.message; report(); });
  });
  S.bridge.ready();
});
```

The page never signals a peer before it has local media: `onSignal` returns until `start` has run; Python sends `start` before any `signal` for a call (Task 6 holds signals that arrive earlier and replays them after `start`).

- [ ] **Step 4: callpage.py**

```python
"""The call page's host: the composed HTML, the QWebChannel bridge, the web page that grants the
camera, microphone and screen to our own page only.

Spec: docs/superpowers/specs/2026-10-22-chat-calls-design.md
"""
import json
import os

import maya_hubqt as hubqt
import maya_hubstyle as hubstyle

ORIGIN = "https://skeldar.call"
_CLASSES = {}


def _q():
    return hubqt.qt()


def folder():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(here), "assets", "call")


def _read(name):
    with open(os.path.join(folder(), name), encoding="utf-8") as f:
        return f.read()


def _qwebchannel_js():
    q = _q()
    f = q.QtCore.QFile(":/qtwebchannel/qwebchannel.js")
    if not f.open(q.QtCore.QIODevice.ReadOnly):
        raise RuntimeError("qwebchannel.js is not in this Qt")
    try:
        return bytes(f.readAll()).decode("utf-8")
    finally:
        f.close()


def compose(tokens=None):
    """The page with its CSS, JS and qwebchannel.js inlined and the hub's colours as CSS variables."""
    tokens = tokens or hubstyle.TOKENS
    names = ("panel", "card", "line", "text", "muted", "accent", "on_accent", "danger")
    variables = ":root{" + "".join("--%s:%s;" % (n, tokens.get(n, "#888")) for n in names) + "}"
    html = _read("call.html")
    html = html.replace("/*CSS*/", variables + _read("call.css"))
    html = html.replace("/*QWEBCHANNEL*/", _qwebchannel_js())
    return html.replace("/*JS*/", _read("call.js"))


def allowed(origin):
    """Whether a page at `origin` (a QUrl) may have the camera, microphone or screen."""
    q = _q()
    url = q.QtCore.QUrl(origin) if not isinstance(origin, q.QtCore.QUrl) else origin
    return url.scheme() == "https" and url.host() == "skeldar.call"


def bridge_class():
    if "bridge" not in _CLASSES:
        q = _q()
        QtCore = q.QtCore

        class Bridge(QtCore.QObject):
            command = QtCore.Signal(str, str)

            def __init__(self, on_ready, on_signal, on_state, parent=None):
                super(Bridge, self).__init__(parent)
                self.on_ready, self.on_signal, self.on_state = on_ready, on_signal, on_state

            @QtCore.Slot()
            def ready(self):
                self.on_ready()

            @QtCore.Slot(str, str)
            def signal(self, to, data):
                try:
                    value = json.loads(data)
                except ValueError:
                    return
                if isinstance(value, dict):
                    self.on_signal(to, value)

            @QtCore.Slot(str)
            def state(self, text):
                try:
                    value = json.loads(text)
                except ValueError:
                    return
                if isinstance(value, dict):
                    self.on_state(value)

            @QtCore.Slot(str)
            def log(self, text):
                print("[call page] " + text)

            def send(self, name, args=None):
                self.command.emit(name, json.dumps(args or {}))

        _CLASSES["bridge"] = Bridge
    return _CLASSES["bridge"]


def page_class():
    if "page" not in _CLASSES:
        q = _q()
        QtCore = q.QtCore
        from PySide6 import QtWebEngineCore

        class CallPage(QtWebEngineCore.QWebEnginePage):
            screen_requested = QtCore.Signal(object)

            def __init__(self, profile, parent=None):
                super(CallPage, self).__init__(profile, parent)
                self.permissionRequested.connect(self._permission)
                self.desktopMediaRequested.connect(self.screen_requested.emit)

            def _permission(self, permission):
                if allowed(permission.origin()):
                    permission.grant()
                else:
                    permission.deny()

            def javaScriptConsoleMessage(self, level, message, line, source):   # noqa: N802
                if level >= QtWebEngineCore.QWebEnginePage.JavaScriptConsoleMessageLevel.WarningMessageLevel:
                    print("[call page] %s (%s:%s)" % (message, source, line))

        _CLASSES["page"] = CallPage
    return _CLASSES["page"]


def make_view(bridge, parent=None):
    """A web view with our page and the bridge on its channel."""
    q = _q()
    from PySide6 import QtWebChannel, QtWebEngineCore, QtWebEngineWidgets
    view = QtWebEngineWidgets.QWebEngineView(parent)
    profile = QtWebEngineCore.QWebEngineProfile(view)        # off the record, its own
    page = page_class()(profile, view)
    channel = QtWebChannel.QWebChannel(page)
    channel.registerObject("bridge", bridge)
    page.setWebChannel(channel)
    view.setPage(page)
    page.setHtml(compose(), q.QtCore.QUrl(ORIGIN + "/"))
    return view, page
```

If `QFile(":/qtwebchannel/qwebchannel.js")` cannot open in this Qt, take the file from PySide6's package (`<PySide6>/resources` or the Qt WebEngine resources) — search the Maya install for `qwebchannel.js` and, if it is nowhere, ship a copy of Qt's file (LGPL, Qt's own) under `assets/call/qwebchannel.js` with its licence header intact and read that. Say which in the report.

- [ ] **Step 5: Run the unit tests**

Run: `$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_chat_callpage -v` → PASS.

- [ ] **Step 6: The headless media check**

`docs/superpowers/plans/verify_call_page.py` — two pages in one mayapy, their bridges wired to each other directly (no server), Chromium's fake camera and microphone:

```python
"""Two call pages in one headless mayapy, wired to each other, Chromium's fake devices: the call
connects, audio and video flow both ways, mute and camera reach the other side, a screen share
replaces the video, end stops everything.

    $env:QT_QPA_PLATFORM='offscreen'; mayapy docs/superpowers/plans/verify_call_page.py
"""
import os
import sys
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = ("--use-fake-ui-for-media-stream --use-fake-device-for-media-stream "
                                            "--autoplay-policy=no-user-gesture-required")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))

from PySide6 import QtCore, QtWidgets  # noqa: E402
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

from maya_chat import callpage  # noqa: E402

GATES = []


def gate(name, ok, detail=""):
    GATES.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + (" - " + str(detail) if detail else ""))


def pump(seconds, until=None):
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents(QtCore.QEventLoop.AllEvents, 50)
        if until and until():
            return True
        time.sleep(0.01)
    return bool(until and until())


class Side(object):
    def __init__(self, me):
        self.me, self.ready, self.state, self.other = me, False, {}, None
        self.bridge = callpage.bridge_class()(self._ready, self._signal, self._state)
        self.view, self.page = callpage.make_view(self.bridge)
        self.view.resize(640, 360)
        self.view.show()
        self.page.screen_requested.connect(self._screen)

    def _ready(self):
        self.ready = True

    def _signal(self, to, data):
        self.other.bridge.send("signal", {"from": self.me, "data": data})

    def _state(self, s):
        self.state = s

    def _screen(self, request):
        screens = request.screensModel()
        if screens is not None and screens.rowCount() > 0:
            request.selectScreen(screens.index(0, 0))
        else:
            request.cancel()

    def peer(self):
        return (self.state.get("peers") or {}).get(self.other.me) or {}


def main():
    a, b = Side("a"), Side("b")
    a.other, b.other = b, a
    gate("both pages load and open their channel", pump(20, lambda: a.ready and b.ready))
    ice = [{"urls": ["stun:stun.cloudflare.com:3478"]}]
    a.bridge.send("start", {"me": "a", "names": {"a": "Ann", "b": "Bob"}, "ice_servers": ice, "video": True,
                            "peers": [], "offer_to": []})
    pump(3)
    a.bridge.send("add_peer", {"uid": "b", "offer": False})
    b.bridge.send("start", {"me": "b", "names": {"a": "Ann", "b": "Bob"}, "ice_servers": ice, "video": True,
                            "peers": ["a"], "offer_to": ["a"]})
    gate("the two connect", pump(30, lambda: a.peer().get("state") == "connected" and b.peer().get("state") == "connected"),
         (a.peer().get("state"), b.peer().get("state")))
    def flowing():
        ba, bb = a.peer().get("bytes") or {}, b.peer().get("bytes") or {}
        return all((ba.get(k, 0) > 2000 and bb.get(k, 0) > 2000) for k in ("audio_in", "video_in"))
    gate("audio and video flow both ways", pump(20, flowing), (a.peer().get("bytes"), b.peer().get("bytes")))
    gate("the devices are listed", (a.state.get("devices") or {}).get("mics"), a.state.get("devices"))
    a.bridge.send("mute", {"on": True})
    gate("a muted microphone reaches the other side", pump(10, lambda: b.peer().get("mic") is False))
    a.bridge.send("camera", {"on": False})
    gate("a camera turned off reaches the other side", pump(10, lambda: b.peer().get("cam") is False))
    a.bridge.send("camera", {"on": True})
    gate("and on again", pump(10, lambda: b.peer().get("cam") is True))
    a.bridge.send("screen", {"on": True})
    shared = pump(15, lambda: b.peer().get("screen") is True)
    if a.state.get("screen") or shared:
        gate("a screen share reaches the other side", shared)
    else:
        print("SKIP the screen share: this headless Qt offers no screen (%s)" % a.state.get("note"))
    a.bridge.send("end", {})
    gate("end closes the call", pump(10, lambda: not (a.state.get("peers") or {})))
    failed = GATES.count(False)
    print("%d of %d gates failed" % (failed, len(GATES)))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
```

Run: `$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs\superpowers\plans\verify_call_page.py` → `0 of N gates failed` (the screen gate may SKIP headless). Fix the page until it passes; any change to the page's protocol must update this plan's Task 5 interface block in your report.

- [ ] **Step 7: Commit**

`git add SkeldarAnim/assets/call SkeldarAnim/maya_chat/callpage.py tests/test_chat_callpage.py docs/superpowers/plans/verify_call_page.py`; message `feat(chat calls): the call page - a WebRTC mesh in Maya's Chromium, and its bridge`.

---

### Task 6: The call window

**Files:**
- Create: `SkeldarAnim/maya_chat/callview.py`
- Modify: `SkeldarAnim/maya_hubicons.py` (icons)
- Test: `tests/test_chat_callview.py`

**Interfaces:**
- Consumes: `calls.*` (Task 3); `Session.start_call / join_call / leave_call / call_signal / turn_servers`, `state.calls`, listeners `("call", e)`, `("call_signal", e)`, `("error", e)` (Task 4); `callpage.bridge_class / make_view / ORIGIN` and the page commands and state (Task 5); `maya_hubwindow.frame_class`, `title_icon`, `title_label`, `pill_class` (read `maya_hubwindow.py` for the real names; the chat window builds its frame this way — copy `maya_chat/window.py`'s `_build` top: `root`, `frame`, title row, `hubwindow.dress`).
- Produces:
  - `callview.start(session, chat, kind) -> CallWindow | None` (None when the animator keeps the call they are in);
  - `callview.answer(session, call_id, kind) -> CallWindow | None`;
  - `callview.current() -> CallWindow | None`; `callview.hang_up()`;
  - `CallWindow(session, kind, call_id=None, cid=None, view_factory=None)` with `.call_id`, `.state` (the page's last state dict), `.folded`, `.fold(on)`, `.press(name)` for name in `mic`, `camera`, `screen`, `settings`, `fold`, `hang_up`, `.close_window()`; `view_factory(bridge, parent) -> (widget, page)` (default `callpage.make_view`; tests pass a fake).
  - Icons in `maya_hubicons.ICONS`: `phone`, `phone-off`, `video`, `video-off`, `microphone`, `microphone-off`, `screen-share`, `screen-share-off`, `minimize` (Tabler outline, MIT, the module's existing notice covers them; copy their SVG path data from Tabler Icons v2/v3 exactly as the module's other icons are stored).

- [ ] **Step 1: Failing tests**

`tests/test_chat_callview.py` — a fake session and a fake page so no Chromium runs in the unit tests:

```python
"""maya_chat.callview offscreen on a fake session and a fake page."""
import os
import time
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tests  # noqa: F401

from PySide6 import QtWidgets

import maya_hubmotion as hubmotion
from maya_chat import callview as V
from maya_chat import session as S

ME = {"id": "me", "nick": "me", "name": "Me", "avatar_v": 0}
BOB = {"id": "bob", "nick": "bob", "name": "Bob", "avatar_v": 0}


def _app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def view(state="ringing", members=("me",), cid="c-1", **kw):
    v = {"id": "c1", "chat": "dm", "by": "me", "kind": "video", "cid": cid, "state": state,
         "members": list(members), "declined": [], "started_at": int(time.time() * 1000),
         "answered_at": None, "ended_at": None}
    v.update(kw)
    return v


class FakeSession(object):
    def __init__(self):
        self.state = S.State()
        self.state.me = ME
        self.state.chats = {"dm": {"id": "dm", "kind": "dm", "name": "", "members": [ME, BOB]}}
        self.listeners, self.calls = [], []

    def listen(self, fn):
        self.listeners.append(fn)

    def unlisten(self, fn):
        if fn in self.listeners:
            self.listeners.remove(fn)

    def tell(self, kind, data):
        for fn in list(self.listeners):
            fn(kind, data)

    def start_call(self, chat, kind):
        self.calls.append(("start", chat, kind))
        return "c-1"

    def join_call(self, call_id):
        self.calls.append(("join", call_id))
        return "j-1"

    def leave_call(self, call_id):
        self.calls.append(("leave", call_id))
        return True

    def call_signal(self, call_id, to, data):
        self.calls.append(("signal", call_id, to, data))
        return True

    def turn_servers(self, now=None):
        return [{"urls": ["stun:x"]}], False


class FakePage(object):
    def __init__(self):
        from PySide6 import QtCore

        class Sig(QtCore.QObject):
            screen_requested = QtCore.Signal(object)
        self.sig = Sig()
        self.screen_requested = self.sig.screen_requested


def fake_factory(store):
    def make(bridge, parent):
        store["bridge"] = bridge
        store["sent"] = sent = []
        bridge.command.connect(lambda name, args: sent.append((name, __import__("json").loads(args))))
        return QtWidgets.QWidget(parent), FakePage()
    return make


class Base(unittest.TestCase):
    def setUp(self):
        _app()
        V._VARS.clear()
        self.ses = FakeSession()
        self.store = {}

    def tearDown(self):
        V.destroy()

    def sent(self, name):
        return [a for n, a in self.store.get("sent", []) if n == name]


class Starting(Base):
    def test_start_rings_then_starts_the_page_alone(self):
        w = V.start(self.ses, "dm", "video", view_factory=fake_factory(self.store))
        self.assertEqual(self.ses.calls, [("start", "dm", "video")])
        self.store["bridge"].ready()
        self.ses.tell("call", {"kind": "call", "call": view()})
        self.assertEqual(w.call_id, "c1")
        starts = self.sent("start")
        self.assertEqual(len(starts), 1)
        self.assertEqual((starts[0]["me"], starts[0]["peers"], starts[0]["video"]), ("me", [], True))

    def test_the_answerer_joins_and_offers(self):
        w = V.answer(self.ses, "c1", "audio", view_factory=fake_factory(self.store))
        self.assertEqual(self.ses.calls, [("join", "c1")])
        self.store["bridge"].ready()
        self.ses.tell("call", {"kind": "call", "call": view("live", ("bob", "me"), by="bob")})
        st = self.sent("start")[0]
        self.assertEqual((st["peers"], st["offer_to"], st["video"]), (["bob"], ["bob"], False))

    def test_signals_go_both_ways_and_early_ones_wait_for_start(self):
        w = V.answer(self.ses, "c1", "video", view_factory=fake_factory(self.store))
        self.ses.tell("call_signal", {"kind": "call_signal", "call": "c1", "from": "bob", "data": {"sdp": "o"}})
        self.assertEqual(self.sent("signal"), [])                    # before start: held
        self.store["bridge"].ready()
        self.ses.tell("call", {"kind": "call", "call": view("live", ("bob", "me"), by="bob")})
        self.assertEqual(self.sent("signal"), [{"from": "bob", "data": {"sdp": "o"}}])
        self.store["bridge"].signal("bob", '{"ice": {"candidate": "x"}}')
        self.assertIn(("signal", "c1", "bob", {"ice": {"candidate": "x"}}), self.ses.calls)

    def test_newcomers_and_leavers(self):
        V.start(self.ses, "dm", "video", view_factory=fake_factory(self.store))
        self.store["bridge"].ready()
        self.ses.tell("call", {"kind": "call", "call": view()})
        self.ses.tell("call", {"kind": "call", "call": view("live", ("me", "bob"))})
        self.assertEqual(self.sent("add_peer"), [{"uid": "bob", "offer": False}])
        self.ses.tell("call", {"kind": "call", "call": view("live", ("me",))})
        self.assertEqual(self.sent("remove_peer"), [{"uid": "bob"}])

    def test_the_end_closes_the_window(self):
        w = V.start(self.ses, "dm", "audio", view_factory=fake_factory(self.store))
        self.store["bridge"].ready()
        self.ses.tell("call", {"kind": "call", "call": view()})
        with mock.patch.object(hubmotion, "enabled", return_value=False):
            self.ses.tell("call", {"kind": "call", "call": view("ended", ())})
        self.assertIsNone(V.current())
        self.assertIn("end", [n for n, _a in self.store["sent"]])

    def test_a_refused_start_closes_and_says_why(self):
        w = V.start(self.ses, "dm", "audio", view_factory=fake_factory(self.store))
        with mock.patch.object(hubmotion, "enabled", return_value=False):
            self.ses.tell("error", {"kind": "error", "cid": "c-1", "code": "call_exists", "text": "join it"})
        self.assertIsNone(V.current())
        self.assertIn("join it", w.last_message)


class Buttons(Base):
    def live(self):
        w = V.start(self.ses, "dm", "video", view_factory=fake_factory(self.store))
        self.store["bridge"].ready()
        self.ses.tell("call", {"kind": "call", "call": view("live", ("me", "bob"))})
        self.store["bridge"].state('{"mic": true, "cam": true, "screen": false, "devices": '
                                   '{"mics": [{"id": "m1", "label": "Mic"}], "cams": []}, "peers": {}}')
        return w

    def test_mic_camera_screen(self):
        w = self.live()
        w.press("mic")
        w.press("camera")
        w.press("screen")
        self.assertEqual(self.sent("mute"), [{"on": True}])
        self.assertEqual(self.sent("camera"), [{"on": False}])
        self.assertEqual(self.sent("screen"), [{"on": True}])

    def test_hang_up_leaves(self):
        w = self.live()
        with mock.patch.object(hubmotion, "enabled", return_value=False):
            w.press("hang_up")
        self.assertIn(("leave", "c1"), self.ses.calls)
        self.assertIsNone(V.current())

    def test_fold_and_unfold(self):
        w = self.live()
        w.press("fold")
        self.assertTrue(w.folded)
        self.assertLessEqual(w.root.width(), w.px(260))
        w.fold(False)
        self.assertFalse(w.folded)

    def test_a_device_choice_is_remembered_and_sent(self):
        w = self.live()
        w.choose_device("mic", "m1")
        self.assertEqual(V.get_var(V.MIC_VAR), "m1")
        self.assertEqual(self.sent("devices")[-1], {"mic": "m1", "cam": ""})

    def test_one_call_at_a_time(self):
        self.live()
        with mock.patch.object(V, "_ask_switch", return_value=False):
            self.assertIsNone(V.start(self.ses, "dm", "audio", view_factory=fake_factory({})))
        with mock.patch.object(V, "_ask_switch", return_value=True), \
                mock.patch.object(hubmotion, "enabled", return_value=False):
            w2 = V.start(self.ses, "dm", "audio", view_factory=fake_factory({}))
        self.assertIn(("leave", "c1"), self.ses.calls)
        self.assertIs(V.current(), w2)
```

- [ ] **Step 2: Run to see them fail**

Run: `$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_chat_callview -v` → ERROR.

- [ ] **Step 3: Implement callview.py**

Write it after reading how `maya_chat/window.py` builds its window (`ChatWindow._build`: the `root` Qt.Tool window owned by `_main_window()`, `hubwindow.frame_class()`, the title row from `maya_hubpop._title_class()`, `hubwindow.dress`, `self.px`, `get_var`/`set_var`, `_button(...)`), and reuse those helpers by importing them from `maya_chat.window` (`window._button`, `window.get_var`, `window.set_var`, `window._main_window`, `window._q`) rather than copying them. The module:

```python
"""The call window (spec docs/superpowers/specs/2026-10-22-chat-calls-design.md): the hub's look,
the call page in it, buttons for the microphone, the camera, the screen, the devices, folding
and hanging up. One call at a time; the window follows the session's call events.
"""
import json
import sys
import time
import traceback

import maya_hubmotion as hubmotion
import maya_hubstyle as hubstyle

from . import calls as _calls
from . import window as W

MIC_VAR = "skeldarChatCallMic"
CAM_VAR = "skeldarChatCallCam"
POS_VAR = "skeldarChatCallPos"
SIZE_VAR = "skeldarChatCallSize"
SIZE = (640, 440)          # logical px
LEAST = (420, 300)
TILE = (240, 170)          # folded
_ATTR = "_skeldar_chat_call"
_VARS = W._VARS            # optionVars where there is no Maya (tests)


def get_var(name):
    return W.get_var(name)


def set_var(name, value):
    W.set_var(name, value)


def current():
    held = getattr(sys, _ATTR, None)
    return held if held is not None and not held.closed else None


def _set_current(win):
    setattr(sys, _ATTR, win)


def _ask_switch(win):
    """Whether to end the call in progress for a new one (a question)."""
    q = W._q()
    answer = q.QtWidgets.QMessageBox.question(
        win.root if win else None, "Звонок", "Завершить текущий звонок и начать новый?")
    return answer == q.QtWidgets.QMessageBox.Yes


def _make_room(session):
    held = current()
    if held is None:
        return True
    if not _ask_switch(held):
        return False
    held.hang_up()
    return True


def start(session, chat, kind, view_factory=None):
    if not _make_room(session):
        return None
    win = CallWindow(session, kind, view_factory=view_factory)
    try:
        win.cid = session.start_call(chat, kind)
    except Exception as exc:                                  # noqa: BLE001
        win.fail(getattr(exc, "text", str(exc)))
        return None
    win.chat = chat
    win.show()
    return win


def answer(session, call_id, kind, view_factory=None):
    if not _make_room(session):
        return None
    win = CallWindow(session, kind, call_id=call_id, view_factory=view_factory)
    view = session.state.calls.get(call_id) if hasattr(session.state, "calls") else None
    win.chat = view["chat"] if view else None
    try:
        win.cid = session.join_call(call_id)
    except Exception as exc:                                  # noqa: BLE001
        win.fail(getattr(exc, "text", str(exc)))
        return None
    win.show()
    return win


def hang_up():
    held = current()
    if held is not None:
        held.hang_up()


def destroy():
    held = getattr(sys, _ATTR, None)
    if held is not None:
        held.close_window(at_once=True)
    if hasattr(sys, _ATTR):
        delattr(sys, _ATTR)


class CallWindow(object):
    def __init__(self, session, kind, call_id=None, cid=None, view_factory=None):
        self.session, self.kind, self.call_id, self.cid = session, kind, call_id, cid
        self.chat = None
        self.view_factory = view_factory
        self.page_ready = False
        self.started = False          # the page has had its start command
        self.members = []
        self.held = []                # signals that arrived before start
        self.state = {}
        self.folded = False
        self.closed = False
        self.last_message = ""
        self.answered_at = None
        self.scale = W._scale()
        self._build()
        session.listen(self._heard)
        _set_current(self)

    def px(self, n):
        return hubstyle.px(n, self.scale)

    # -------------------------------------------------- building
    def _build(self):
        q = W._q()
        QtCore, QtWidgets = q.QtCore, q.QtWidgets
        from . import callpage
        self.bridge = callpage.bridge_class()(self._page_ready, self._page_signal, self._page_state)
        # root + frame + title row exactly as maya_chat/window.py's ChatWindow._build makes them
        # (Qt.Tool, frameless, owned by W._main_window(); the title row: an icon "phone", the chat's
        # name, a timer label self.timer_label, a close pill that hangs up)
        ...
        make = self.view_factory or callpage.make_view
        self.view, self.page = make(self.bridge, self.body)
        self.page.screen_requested.connect(self._screen_requested)
        # the buttons row under the view: mic, camera, screen, settings, fold, hang up (danger)
        self.buttons = {}
        for name, icon, tip in (("mic", "microphone", "Микрофон"), ("camera", "video", "Камера"),
                                ("screen", "screen-share", "Показать экран"),
                                ("settings", "settings", "Микрофон и камера"),
                                ("fold", "minimize", "Свернуть"), ("hang_up", "phone-off", "Завершить")):
            b = W._button("", "danger" if name == "hang_up" else "tool", icon, "skeldarChatCall_" + name,
                          self.scale, tip)
            b.clicked.connect(lambda *_a, n=name: self.press(n))
            self.buttons[name] = b
        # size from SIZE_VAR (least LEAST), place from POS_VAR (kept on a screen), else centred on Maya
        ...
        self.clock = QtCore.QTimer(self.root)
        self.clock.setInterval(1000)
        self.clock.timeout.connect(self._tick)
        self.clock.start()
```

The two `...` are the frame/title and the size/place code: write them by copying the chat window's own (`ChatWindow._build` and its place/size helpers with `POS_VAR`/`SIZE_VAR` swapped). Everything else as below:

```python
    def show(self):
        self.root.show()
        self.root.raise_()

    # -------------------------------------------------- the session
    def _heard(self, kind, data):
        try:
            if kind == "call":
                self._call(data["call"])
            elif kind == "call_signal" and data.get("call") == self.call_id:
                if self.started:
                    self.bridge.send("signal", {"from": data["from"], "data": data["data"]})
                else:
                    self.held.append((data["from"], data["data"]))
            elif kind == "error" and data.get("cid") and data.get("cid") == self.cid:
                self.fail(data.get("text") or data.get("code") or "Звонок не удался")
        except Exception:                                     # noqa: BLE001
            traceback.print_exc()

    def _call(self, view):
        me = (self.session.state.me or {}).get("id")
        if self.call_id is None:
            if view.get("cid") != self.cid or view.get("by") != me:
                return
            self.call_id = view["id"]
            self.chat = view["chat"]
        if view["id"] != self.call_id:
            return
        if view["state"] == "ended":
            self.bridge.send("end", {})
            self.close_window()
            return
        if view.get("answered_at"):
            self.answered_at = view["answered_at"]
        if me not in view["members"]:
            return
        if not self.started:
            self.members = list(view["members"])
            self._start_page(view)
            return
        for name, args in _calls.peer_commands(self.members, view["members"], me):
            self.bridge.send(name, args)
        self.members = list(view["members"])

    def _start_page(self, view):
        if not self.page_ready:
            self._pending_view = view
            return
        me = self.session.state.me["id"]
        servers, turn = self.session.turn_servers()
        names = self._names()
        args = _calls.start_args(view, me, names, servers, self.kind == "video",
                                 get_var(MIC_VAR) or "", get_var(CAM_VAR) or "")
        self.bridge.send("start", args)
        self.started = True
        for frm, data in self.held:
            self.bridge.send("signal", {"from": frm, "data": data})
        self.held = []
        if not turn:
            self.say("прямое соединение - через строгую сеть может не пройти")

    def _names(self):
        chat = self.session.state.chats.get(self.chat) or {}
        from . import look
        return dict((u["id"], look.display_name(u)) for u in chat.get("members") or [] if u.get("id"))

    # -------------------------------------------------- the page
    def _page_ready(self):
        self.page_ready = True
        pending = getattr(self, "_pending_view", None)
        if pending is not None:
            self._pending_view = None
            self._start_page(pending)

    def _page_signal(self, to, data):
        if self.call_id:
            self.session.call_signal(self.call_id, to, data)

    def _page_state(self, state):
        self.state = state
        if state.get("error") and not state.get("peers") and "Микрофон" in state["error"]:
            self.fail(state["error"])
            return
        self._paint_buttons()

    def _paint_buttons(self):
        st = self.state
        W._set_icon(self.buttons["mic"], "microphone" if st.get("mic", True) else "microphone-off")
        W._set_icon(self.buttons["camera"], "video" if st.get("cam") else "video-off")
        W._set_icon(self.buttons["screen"], "screen-share-off" if st.get("screen") else "screen-share")
```

`W._set_icon(button, icon_name)`: use the chat window's way of changing a button's icon (search `window.py` for `setIcon(` / `icon_for` / `hubicons`); if there is no helper, add one beside `_button` that sets the hub icon at the button's size. Then:

```python
    # -------------------------------------------------- presses
    def press(self, name):
        st = self.state
        if name == "mic":
            self.bridge.send("mute", {"on": bool(st.get("mic", True))})
        elif name == "camera":
            self.bridge.send("camera", {"on": not st.get("cam", False)})
        elif name == "screen":
            self.bridge.send("screen", {"on": not st.get("screen", False)})
        elif name == "settings":
            self._devices_menu()
        elif name == "fold":
            self.fold(not self.folded)
        elif name == "hang_up":
            self.hang_up()

    def hang_up(self):
        if self.call_id:
            self.session.leave_call(self.call_id)
        self.bridge.send("end", {})
        self.close_window()

    def choose_device(self, kind, device_id):
        set_var(MIC_VAR if kind == "mic" else CAM_VAR, device_id or "")
        self.bridge.send("devices", {"mic": get_var(MIC_VAR) or "", "cam": get_var(CAM_VAR) or ""})

    def _devices_menu(self):
        q = W._q()
        menu = q.QtWidgets.QMenu(self.root)
        devices = self.state.get("devices") or {}
        for kind, title, items, var in (("mic", "Микрофон", devices.get("mics") or [], MIC_VAR),
                                        ("cam", "Камера", devices.get("cams") or [], CAM_VAR)):
            menu.addSection(title)
            chosen = get_var(var) or ""
            for d in items:
                a = menu.addAction(d.get("label") or d.get("id"))
                a.setCheckable(True)
                a.setChecked(d.get("id") == chosen)
                a.triggered.connect(lambda *_a, k=kind, i=d.get("id"): self.choose_device(k, i))
        b = self.buttons["settings"]
        menu.exec(b.mapToGlobal(b.rect().topLeft()))

    def fold(self, on):
        """Folded: a small always-on-top tile of the call; a click on it unfolds."""
        q = W._q()
        QtCore = q.QtCore
        if on == self.folded:
            return
        self.folded = on
        if on:
            self._unfolded = self.root.geometry()
            for b in self.buttons.values():
                b.setVisible(b is self.buttons["fold"] or b is self.buttons["hang_up"])
            self.root.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, True)
            self.root.resize(self.px(TILE[0]), self.px(TILE[1]))
        else:
            for b in self.buttons.values():
                b.setVisible(True)
            self.root.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, False)
            if getattr(self, "_unfolded", None) is not None:
                self.root.setGeometry(self._unfolded)
        self.root.show()

    # -------------------------------------------------- screens
    def _screen_requested(self, request):
        """Our own picker of the screens and windows Qt offers."""
        q = W._q()
        menu = q.QtWidgets.QMenu(self.root)
        chosen = {}
        for title, model, select in (("Экран", request.screensModel(), request.selectScreen),
                                     ("Окно", request.windowsModel(), request.selectWindow)):
            if model is None or model.rowCount() == 0:
                continue
            menu.addSection(title)
            for row in range(model.rowCount()):
                index = model.index(row, 0)
                a = menu.addAction(str(model.data(index) or "%s %d" % (title, row + 1)))
                chosen[a] = (select, index)
        b = self.buttons["screen"]
        action = menu.exec(b.mapToGlobal(b.rect().topLeft())) if chosen else None
        if action in chosen:
            select, index = chosen[action]
            select(index)
        else:
            request.cancel()

    # -------------------------------------------------- the rest
    def _tick(self):
        if self.answered_at and not self.folded:
            seconds = int(time.time() - self.answered_at / 1000.0)
            self.timer_label.setText("%d:%02d" % (seconds // 60, seconds % 60))

    def say(self, text):
        self.last_message = text
        self.note_label.setText(text)          # a muted one-line note under the view (build it in _build)

    def fail(self, text):
        self.say(text)
        try:
            W.say_viewport(text) if hasattr(W, "say_viewport") else None
        except Exception:                                     # noqa: BLE001
            pass
        self.close_window()

    def close_window(self, at_once=False):
        if self.closed:
            return
        self.closed = True
        try:
            self.session.unlisten(self._heard)
        except Exception:                                     # noqa: BLE001
            pass
        self._remember_place()
        try:
            self.clock.stop()
            self.root.hide()
            self.root.deleteLater()
        except RuntimeError:
            pass
        if getattr(sys, _ATTR, None) is self:
            delattr(sys, _ATTR)
```

`_remember_place` writes `POS_VAR`/`SIZE_VAR` (unfolded geometry) the way the chat window remembers its own. With `hubmotion.enabled()` true the window may open with `hubwindow.Burster` like the chat window does; with it false it appears and goes at once (the tests patch it false where they close).

Add the icons to `maya_hubicons.py` (Tabler outline, as its other icons are stored): `phone`, `phone-off`, `video`, `video-off`, `microphone`, `microphone-off`, `screen-share`, `screen-share-off`, `minimize`; `settings` exists already (check; add if not). A test in `tests/test_hubicons.py` (or the existing icon test) that each new name draws.

- [ ] **Step 4: Run the tests**

Run: `$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_chat_callview tests.test_chat_window -v` → PASS.

- [ ] **Step 5: Commit**

`git add SkeldarAnim/maya_chat/callview.py SkeldarAnim/maya_hubicons.py tests/test_chat_callview.py` (and any icon test, and `window.py` if a small `_set_icon` helper was added there); message `feat(chat calls): the call window - tiles, buttons, folding, devices, screen picker`.

---

### Task 7: The incoming call: card and ring

**Files:**
- Modify: `SkeldarAnim/maya_hubsound.py` (a `ring` tone, looped playing), add `SkeldarAnim/assets/sounds/ring.wav` (written by `docs/superpowers/plans/make_hub_sounds.py`)
- Modify: `SkeldarAnim/maya_chat/toast.py` (a call card)
- Modify: `SkeldarAnim/maya_chat/notify.py` (ring + card on `call` events)
- Test: `tests/test_hubsound.py`, `tests/test_chat_window.py` (`Toasts`, `Notify` classes) or a new `tests/test_chat_ring.py`

**Interfaces:**
- Consumes: `calls.ringing_for`, `calls.RING_S` (Task 3); `callview.answer` (Task 6); `Session.decline_call` (Task 4).
- Produces:
  - `maya_hubsound.SOUNDS["ring"]`; `maya_hubsound.loop(name, force=False) -> handle | None` where `handle.stop()` stops it; `maya_hubsound.LOOP_PLAYERS` seam.
  - `toast.show_call(call_view, user, head) -> CallCard`, `toast.dismiss_call(call_id)`, `toast.call_cards() -> [CallCard]`; a CallCard has `.call_id`, `.button_rects() -> {"voice": QRectF, "video": QRectF, "decline": QRectF}`, `.press(name)`; module seams `toast.on_answer = lambda call_id, kind: callview.answer(session, call_id, kind)`-style defaults resolved at press time.
  - `notify.heard(session, "call", event)` shows/dismisses the card and starts/stops the ring; it returns `("call_card", call_id)` / `("call_gone", call_id)` in its `out` list for tests.

- [ ] **Step 1: Failing tests**

```python
# tests/test_hubsound.py, beside the message chime's tests
    def test_the_shipped_ring_is_the_synthesis(self):
        # the same check the file already makes for "message": synthesise SOUNDS["ring"] and compare
        # with SkeldarAnim/assets/sounds/ring.wav within 1 LSB.
        ...

    def test_a_loop_plays_until_stopped(self):
        class P(object):
            def __init__(self):
                self.playing = False
            def play(self):
                self.playing = True
            def stop(self):
                self.playing = False
        made = []
        with mock.patch.object(sound, "make_loop_player", side_effect=lambda path: made.append(P()) or made[-1]):
            handle = sound.loop("ring", force=True)
            self.assertTrue(made[0].playing)
            handle.stop()
            self.assertFalse(made[0].playing)

    def test_a_loop_is_quiet_with_sounds_off_unless_forced(self):
        with mock.patch.object(sound, "enabled", return_value=False), \
                mock.patch.object(sound, "make_loop_player") as make:
            self.assertIsNone(sound.loop("ring"))
            make.assert_not_called()
```

Write the first test concretely by copying the message chime's shipped-file test in `tests/test_hubsound.py` and changing the name.

```python
# tests/test_chat_window.py (or a new tests/test_chat_ring.py using the same FakeSession)
class CallCards(Base):
    def call(self, **kw):
        v = {"id": "c1", "chat": "dm", "by": "bob", "kind": "video", "cid": "x", "state": "ringing",
             "members": ["bob"], "declined": [], "started_at": int(time.time() * 1000),
             "answered_at": None, "ended_at": None}
        v.update(kw)
        return v

    def test_a_card_with_three_buttons(self):
        card = toast.show_call(self.call(), BOB, "Bob")
        self.assertEqual(set(card.button_rects()), {"voice", "video", "decline"})
        self.assertEqual([c.call_id for c in toast.call_cards()], ["c1"])
        toast.dismiss_call("c1")
        self.assertEqual(toast.call_cards(), [])

    def test_the_buttons_answer_or_decline(self):
        got = []
        with mock.patch.object(toast, "answer_call", side_effect=lambda cid, kind: got.append((cid, kind))), \
                mock.patch.object(toast, "decline_call", side_effect=lambda cid: got.append((cid, "no"))):
            toast.show_call(self.call(), BOB, "Bob").press("video")
            toast.show_call(self.call(id="c2"), BOB, "Bob").press("decline")
        self.assertEqual(got, [("c1", "video"), ("c2", "no")])

    def test_notify_rings_and_stops(self):
        self.ses.state.me = ME
        self.ses.state.calls = {}
        rings = []

        class H(object):
            def stop(self):
                rings.append("stop")
        with mock.patch.object(notify, "_loop_ring", side_effect=lambda: rings.append("ring") or H()):
            self.ses.state.calls = {"c1": self.call()}
            out = notify.heard(self.ses, "call", {"kind": "call", "call": self.call()}, out=[])
            self.assertIn(("call_card", "c1"), out)
            self.assertEqual(rings, ["ring"])
            ended = self.call(state="ended", members=[], ended_at=1)
            self.ses.state.calls = {"c1": ended}
            out = notify.heard(self.ses, "call", {"kind": "call", "call": ended}, out=[])
            self.assertIn(("call_gone", "c1"), out)
            self.assertEqual(rings, ["ring", "stop"])
        self.assertEqual(toast.call_cards(), [])

    def test_my_own_call_does_not_ring_me(self):
        self.ses.state.me = ME
        mine = self.call(by="me", members=["me"])
        self.ses.state.calls = {"c1": mine}
        with mock.patch.object(notify, "_loop_ring") as ring:
            out = notify.heard(self.ses, "call", {"kind": "call", "call": mine}, out=[])
        ring.assert_not_called()
        self.assertEqual(toast.call_cards(), [])
```

Adapt to the real `Base`/`FakeSession` of `tests/test_chat_window.py` (give `FakeSession.state` a `calls` dict and a `decline_call` method recording its call).

- [ ] **Step 2: Run them to see them fail**

Run the two modules → FAIL/ERROR.

- [ ] **Step 3: The ring**

In `maya_hubsound.py`: a `SOUNDS["ring"]` Tone — a soft two-note phrase in the chime's family, about 1.6 s with silence after so it loops into a calm ring, e.g. `Tone(partials=((659.25, 1.0, 0.35, 0.0), (1318.5, 0.25, 0.2, 0.0), (783.99, 0.9, 0.4, 0.22), (1567.98, 0.2, 0.25, 0.22)), attack=0.004, length=1.6, fade=0.05, peak=0.25)` (read the module's `Tone` fields and adjust to its real units; keep the peak at the message chime's or below). Run `docs/superpowers/plans/make_hub_sounds.py` to write `assets/sounds/ring.wav`.

Looping:

```python
def make_loop_player(path):
    """A player that loops until stopped: QSoundEffect with an infinite loop count, else winsound
    SND_LOOP | SND_ASYNC (stopped with PlaySound(None))."""
    try:
        from PySide6 import QtCore, QtMultimedia
        effect = QtMultimedia.QSoundEffect()
        effect.setSource(QtCore.QUrl.fromLocalFile(path))
        effect.setLoopCount(QtMultimedia.QSoundEffect.Loop.Infinite)
        effect.setVolume(VOLUME if "VOLUME" in globals() else 1.0)
        return effect
    except Exception:                                         # noqa: BLE001
        import winsound

        class _Win(object):
            def play(self):
                winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)

            def stop(self):
                winsound.PlaySound(None, 0)
        return _Win()


class _Loop(object):
    def __init__(self, player):
        self.player = player

    def stop(self):
        try:
            self.player.stop()
        except Exception:                                     # noqa: BLE001
            pass


def loop(name, force=False):
    """Play `name` over and over until the handle's stop(); None when quiet or impossible."""
    if not (force or enabled()):
        return None
    path = sound_path(name)
    if not os.path.isfile(path):
        return None
    try:
        player = make_loop_player(path)
        player.play()
        return _Loop(player)
    except Exception:                                         # noqa: BLE001
        return None
```

Use the module's real volume constant and how `_qt_pool` sets its effects up; keep the module importable without Qt (imports inside the function).

- [ ] **Step 4: The card**

In `toast.py`, a `call_card_class()` beside `card_class()`: a `CallCard(call_view, user, head, parent=None)` drawn like `Toast` (same flags, same face, avatar, head «Входящий звонок» + the caller's name or the chat's head, a second line «Видеозвонок» / «Звонок» for the call's kind) but taller (`look.TOAST_H + 34` logical px) with a row of three buttons drawn in the card: «Голос» (accent outline), «Видео» (accent fill), «Отклонить» (danger). It does not leave on its own (no `TOAST_STAY_MS`), only when dismissed; hover lights a button (the Time Bar's hover: 110 ms, +10 %, a glow) — or at least lights it at once when animations are off. A press on a button calls `press(name)`:

```python
            def press(self, name):
                self.leave()
                if name == "decline":
                    decline_call(self.call_id)
                else:
                    answer_call(self.call_id, "video" if name == "video" else "audio")
```

Module functions, keyed by call id in the same stack the message toasts use (call cards stand nearest the Time Bar, above the message cards):

```python
def answer_call(call_id, kind):
    from . import callview, session as _session
    callview.answer(_session.get(), call_id, kind)


def decline_call(call_id):
    from . import session as _session
    try:
        _session.get().decline_call(call_id)
    except Exception:                                         # noqa: BLE001
        pass


def show_call(call_view, user, head): ...      # one card a call; a second show updates it
def dismiss_call(call_id): ...
def call_cards(): ...
```

- [ ] **Step 5: notify**

In `notify.heard`, for `kind == "call"`:

```python
    if kind == "call":
        view = (data or {}).get("call") or {}
        me = (session.state.me or {}).get("id")
        ringing = {c["id"] for c in _calls.ringing_for(session.state.calls, me, _now_ms())}
        held = _rings()                       # {call_id: handle} on sys._skeldar_chat_rings
        if view.get("id") in ringing and view["id"] not in held:
            caller = _user(session, view["by"])
            head = look.display_name(caller) if caller else "Звонок"
            toast.show_call(view, caller, head)
            held[view["id"]] = _loop_ring()
            _stop_after(view["id"], _calls.RING_S)        # a single-shot timer that calls _gone(call_id)
            if out is not None:
                out.append(("call_card", view["id"]))
        elif view.get("id") in held and view.get("id") not in ringing:
            _gone(view["id"])
            if out is not None:
                out.append(("call_gone", view["id"]))
        return out
```

with `_loop_ring()` → `maya_hubsound.loop("ring", force=True)` (may be None), `_gone(call_id)` → stop its handle, `toast.dismiss_call(call_id)`, forget it. `_user(session, uid)` finds the member in `session.state.chats` / `people` the way `sender()` does. `_stop_after` uses a `QTimer.singleShot` when Qt is there.

- [ ] **Step 6: Run the tests**

Run: `$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_hubsound tests.test_chat_window -v` (and `tests.test_chat_ring` if you made it) → PASS.

- [ ] **Step 7: Commit**

`git add SkeldarAnim/maya_hubsound.py SkeldarAnim/assets/sounds/ring.wav SkeldarAnim/maya_chat/toast.py SkeldarAnim/maya_chat/notify.py tests/...`; message `feat(chat calls): the incoming call - a ring and a card to answer with voice or video`.

---

### Task 8: Calls in the chat window: header buttons and the call line

**Files:**
- Modify: `SkeldarAnim/maya_chat/window.py` (header buttons, «Присоединиться», the feed's call line)
- Modify: `SkeldarAnim/maya_chat/look.py` (`feed()` makes call items; the list's preview)
- Test: `tests/test_chat_window.py` (class `CallsInWindow`), `tests/test_chat_look.py` (class `CallLine`)

**Interfaces:**
- Consumes: `records.call_note(message) -> dict | None` and `calls.note_text(note) -> str`, `calls.of_chat(state.calls, chat) -> view | None` (the chat's call not ended), `calls.can_join(view, me) -> bool` (Task 3); `callview.start(session, chat, kind)`, `callview.answer(session, call_id, kind)` (Task 6); icons `phone`, `video` (Task 6).
- Produces: `look.Item` with `kind == "call"` and `text` the note's text, `missed` True for a not-answered call; the header's buttons `skeldarChatCallVoice`, `skeldarChatCallVideo`, `skeldarChatCallJoin` (object names, so tests find them).

- [ ] **Step 1: Failing tests**

```python
# tests/test_chat_look.py
class CallLine(unittest.TestCase):
    def msg(self, seq, call, frm="bob"):
        return {"id": "m%d" % seq, "chat": "dm", "seq": seq, "from": frm, "text": "",
                "at": 1000 * seq, "edited_at": None, "deleted": False, "reply_to": None,
                "reactions": {}, "file": None, "call": call}

    def test_a_call_note_is_its_own_item(self):
        items = look.feed([self.msg(1, {"id": "c", "kind": "audio", "answered": True, "seconds": 300})],
                          me="me", pending=[], reads={})
        calls = [i for i in items if i.kind == "call"]
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].text, "Звонок · 5 мин")
        self.assertFalse(calls[0].missed)

    def test_a_missed_call(self):
        items = look.feed([self.msg(1, {"id": "c", "kind": "video", "answered": False, "seconds": 0})],
                          me="me", pending=[], reads={})
        call = [i for i in items if i.kind == "call"][0]
        self.assertEqual(call.text, "Пропущенный звонок")
        self.assertTrue(call.missed)

    def test_the_preview_reads_the_call(self):
        self.assertEqual(look.message_text(self.msg(1, {"id": "c", "kind": "audio", "answered": False,
                                                          "seconds": 0})),
                         "📞 Пропущенный звонок")
```

Adapt the `feed()` call to its real signature (read `look.feed` first); keep the assertions.

```python
# tests/test_chat_window.py
class CallsInWindow(Base):
    def test_header_buttons_start_calls(self):
        w = self.open_dm()                     # the existing helper that opens the window on a dm
        got = []
        with mock.patch("maya_chat.callview.start", side_effect=lambda s, c, k: got.append((c, k))):
            w.root.findChild(QtWidgets.QAbstractButton, "skeldarChatCallVoice").click()
            w.root.findChild(QtWidgets.QAbstractButton, "skeldarChatCallVideo").click()
        self.assertEqual(got, [("dm", "audio"), ("dm", "video")])

    def test_a_running_call_turns_them_into_join(self):
        w = self.open_dm()
        now = int(time.time() * 1000)
        self.ses.state.calls = {"c1": {"id": "c1", "chat": "dm", "by": "bob", "kind": "video", "cid": "x",
                                       "state": "live", "members": ["bob", "carl"], "declined": [],
                                       "started_at": now, "answered_at": now, "ended_at": None}}
        self.ses.tell("call", {"kind": "call", "call": self.ses.state.calls["c1"]})
        join = w.root.findChild(QtWidgets.QAbstractButton, "skeldarChatCallJoin")
        self.assertTrue(join.isVisibleTo(w.root))
        got = []
        with mock.patch("maya_chat.callview.answer", side_effect=lambda s, c, k: got.append((c, k))):
            join.click()
        self.assertEqual(got, [("c1", "video")])

    def test_the_call_line_paints(self):
        w = self.open_dm()
        self.ses.state.messages["dm"] = [{"id": "m1", "chat": "dm", "seq": 1, "from": "bob", "text": "",
                                          "at": 1000, "edited_at": None, "deleted": False,
                                          "reply_to": None, "reactions": {}, "file": None,
                                          "call": {"id": "c", "kind": "audio", "answered": False,
                                                   "seconds": 0}}]
        self.ses.tell("messages", {"chat": "dm"})
        w.feed.relayout() if hasattr(w.feed, "relayout") else None
        image = w.feed.grab().toImage()
        self.assertGreater(image.width(), 0)
        self.assertTrue(any(b.kind == "call" for b in w.feed.boxes))
```

Use the real names of `tests/test_chat_window.py`'s fixtures (`Base`, the fake session, how a test opens a chat, how the feed holds its laid-out items — read the file; the `Box`es are in `w.feed.boxes` or similar). The fake session needs `state.calls = {}`.

- [ ] **Step 2: Run them to see them fail**

`$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_chat_look tests.test_chat_window -v` → FAIL.

- [ ] **Step 3: look.py**

In `feed()`, before a message becomes a text/file item: `note = records.call_note(message)`; when it is not None, append `Item(kind="call", text=calls.note_text(note), message=message, missed=not note["answered"])` (give `Item` a `missed` field defaulting False; a call item never joins a run of one sender and carries no ticks). `message_text` (the list's preview, Task 3 already handles the note) — make sure the preview test passes.

- [ ] **Step 4: window.py — the call line**

In the feed's layout, a `call` item is a centred pill like the day separators: its height `self.px(26)`, text the item's text with the 📞 before it, `muted` colour on a `card` pill with a `line` edge; a missed call's text in `danger`. A click on it starts a call of the same kind in that chat (`callview.start(session, chat, note["kind"])`). Draw it in the paint where day separators are drawn (read how `kind == "day"` is laid out and painted and follow it).

- [ ] **Step 5: window.py — the header**

In the chat header (where the chat's title, presence and the members button stand), add three tool buttons made with the window's own `_button` helper: `skeldarChatCallVoice` (icon `phone`, tip «Голосовой звонок»), `skeldarChatCallVideo` (icon `video`, tip «Видеозвонок»), `skeldarChatCallJoin` (primary, text «Присоединиться», hidden by default). A method `_paint_call_buttons()` runs on opening a chat and on every session `call` event:

```python
    def _paint_call_buttons(self):
        chat = self.current_chat
        me = (self.session.state.me or {}).get("id")
        now = int(time.time() * 1000)
        running = _calls.of_chat(getattr(self.session.state, "calls", {}), chat) if chat else None
        joinable = running if running and _calls.can_join(running, me) else None
        self.call_join.setVisible(bool(joinable))
        self.call_voice.setVisible(chat is not None and not joinable)
        self.call_video.setVisible(chat is not None and not joinable)
        self._joinable = joinable
```

`of_chat` gives the chat's running call and `can_join(view, me)` says whether I may come in. Voice → `callview.start(self.session, chat, "audio")`, video → `"video"`, join → `callview.answer(self.session, self._joinable["id"], self._joinable["kind"])`. Import `callview` inside the slot (`from . import callview`) so the window imports no web engine at load.

- [ ] **Step 6: Run the tests**

Same command → PASS. Also `tests.test_chat_callview tests.test_chat_calls`.

- [ ] **Step 7: Commit**

`git add SkeldarAnim/maya_chat/window.py SkeldarAnim/maya_chat/look.py tests/test_chat_window.py tests/test_chat_look.py`; message `feat(chat calls): call buttons in a chat's header and the call line in the feed`.

---

### Task 9: End to end, production, the record

**Files:**
- Create: `docs/superpowers/plans/verify_chat_calls.py`
- Create: `docs/superpowers/plans/render_chat_calls.py` → `docs/superpowers/plans/chat_calls.png`
- Modify: `CLAUDE.md` (a section «Chat: voice and video calls»)
- Modify: `SkeldarAnim/install.py` only if `payload()` does not already take `assets/call/` (it ships `assets/` whole — check `install.payload()`; a test in `tests/test_install*.py` pins that `assets/call/call.js` is in the payload)

**Interfaces:**
- Consumes: everything above.
- Produces: nothing for later tasks.

- [ ] **Step 1: The payload**

Write a test in the installer tests:

```python
    def test_the_call_page_ships(self):
        names = set(install.payload())
        for leaf in ("call.html", "call.css", "call.js"):
            self.assertTrue(any(n.replace("\\", "/").endswith("assets/call/" + leaf) for n in names), leaf)
```

Run it. If `payload()` already ships `assets/` whole it passes; if not, add the rows.

- [ ] **Step 2: verify_chat_calls.py**

A headless check against a server given on the command line (staging by default), two real accounts made and deleted like `verify_chat_client.py` makes them (read that file and copy its account helpers, its gate printer and its Qt event pumping). Chromium with fake devices: before importing QtWebEngine set `os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--use-fake-device-for-media-stream --use-fake-ui-for-media-stream --autoplay-policy=no-user-gesture-required"` and `QT_QPA_PLATFORM=offscreen`; `QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)` before the QApplication. Two `Session`s (A, B) in two temp stores, each with its `QtLink`. Gates:

1. A `callview.start(A, dm, "video")` → B's `state.calls` has the call ringing within 5 s; `calls.ringing_for` lists it for B.
2. B `callview.answer(B, call_id, "video")` → both windows' `state["peers"]` show the other `connected` within 20 s (print which candidate type won if the page reports it).
3. Bytes flow both ways: each side's page state `peers[other].bytes_in` grows by > 20 000 over 3 s.
4. A presses mute: B's state shows the other's `mic` false within 3 s.
5. B hangs up: A's call view goes `ended` within 5 s and A's window closes.
6. The call line: both `state.messages[dm]` gain a message with `call.answered` true and `seconds` ≥ 1.
7. A starts again and B declines (`B.decline_call`): A's view goes `ended`, and the line reads missed (`answered` false).
8. `B.turn_servers()` returns servers; print whether TURN (`turn: True`) or STUN only.

Pump the Qt event loop between checks (`QApplication.processEvents()` in a loop with `time.sleep(0.02)`) — the links and the pages need it. Exit code = the number of failed gates; delete both accounts at the end in a `finally`.

- [ ] **Step 3: Run it against staging**

Deploy the branch's server to staging first: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' server\chat\deploy.py staging`. Then `$env:PYTHONIOENCODING='utf-8'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs\superpowers\plans\verify_chat_calls.py https://skeldar-chat-staging.skeldar.workers.dev`. Expected: every gate passes (gate 8 may report STUN only — then TURN was not set up; that is a report, not a failure). Fix what fails.

- [ ] **Step 4: The picture**

`render_chat_calls.py` (offscreen Qt, fake session, a fake view factory that draws two coloured tiles with names): the call window live with two people, the folded tile, the incoming-call card, a chat feed holding a call line and a missed one, at 150 %. Writes `docs/superpowers/plans/chat_calls.png`.

- [ ] **Step 5: TURN**

Run `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' server\chat\deploy.py turn`. If it answers that the token lacks the Calls right, leave TURN off and say so in the final report (the animator adds the right and runs `deploy.py turn` again). If it creates the key, deploy staging again and re-run gate 8.

- [ ] **Step 6: Production**

`deploy.py production`, then `verify_chat_server.py all` against production (`https://skeldar-chat.skeldar.workers.dev`) and `verify_chat_calls.py` against production. Both must pass.

- [ ] **Step 7: CLAUDE.md**

Add a section after «Chat: scenes and files in a chat», in the file's own style: the ask, the spec and plan paths, the server's tables and frames, the call page and its bridge, the window, the card and ring, the call line, TURN or STUN-only as it stands, the measured numbers from the verify (time to ring, to connect, bytes), and what was not seen in a GUI Maya. Also a trap entry for anything measured that cost a run.

- [ ] **Step 8: Commit**

`git add docs/superpowers/plans/verify_chat_calls.py docs/superpowers/plans/render_chat_calls.py docs/superpowers/plans/chat_calls.png CLAUDE.md tests/...` (and `install.py` if changed); message `test(chat calls): end to end on staging and production; the record`.
