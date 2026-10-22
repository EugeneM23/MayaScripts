"""One chat session per Maya: the account, the state, the live link, the listeners.

The session applies every server event to `state` and the disk cache, then tells its listeners
fn(kind, data) - the window (plan 3) draws from `state` and never talks to the server itself.

A send is kept as a PENDING message (state "sending") and in the outbox until its ack; the message
event that comes before the ack replaces it. A refused send stays pending as "failed" with the
server's text, and `retry(cid)` sends it again.

HTTP calls run where they are called (on Maya's main thread); each is one short request.
"""
import os
import sys
import time
import uuid

from . import api as _api
from . import records
from . import store as _store

TYPING_S = 3     # at most one typing frame a chat this often
HISTORY = 50


class State(object):
    def __init__(self):
        self.status = "signed_out"      # signed_out | connecting | online | offline
        self.me = None
        self.chats = {}                 # id -> chat
        self.messages = {}              # chat id -> [message] by seq
        self.pending = {}               # chat id -> [local message, "state" sending | failed]
        self.friends = {"friends": [], "incoming": [], "outgoing": []}
        self.people = []                # everybody but me, read by read_people()
        self.online = {}                # user id -> {"online", "last_seen"}
        self.typing = {}                # chat id -> {user id: monotonic time}
        self.reads = {}                 # chat id -> {user id: upto}
        self.downloads = {}             # file id -> {state, progress, error, then} (files.py)


def _now_ms():
    return int(time.time() * 1000)


class Session(object):
    def __init__(self, server, store, api_factory=_api.Api, link_factory=None):
        from . import link as _link
        self.server = server
        self.store = store
        self.api_factory = api_factory
        self.link_factory = link_factory or _link.QtLink
        self._link_module = _link
        self.state = State()
        self.api = None
        self.link = None
        self.protocol = None
        self.listeners = []
        self._typed = {}

    # ---------------------------------------------------------------- listeners
    def listen(self, fn):
        if fn not in self.listeners:
            self.listeners.append(fn)

    def unlisten(self, fn):
        if fn in self.listeners:
            self.listeners.remove(fn)

    def tell(self, kind, data=None):
        for fn in list(self.listeners):
            try:
                fn(kind, data)
            except Exception as exc:  # a listener's failure must not stop the session
                sys.stderr.write("maya_chat: a listener failed on %s: %s\n" % (kind, exc))

    # ---------------------------------------------------------------- the account
    def start(self):
        """Signed in from the cache when it holds a token; the live link and a fresh read."""
        token = self.store.token()
        if not token:
            self._status("signed_out")
            return False
        self._load_cache()
        self._connect(token)
        try:
            self.resync()
        except _api.ChatError as exc:
            if exc.code == "bad_token":
                self.sign_out()
                return False
        return True

    def sign_in(self, nick, name=None):
        folded = records.nick(nick)
        if folded is None:
            raise _api.ChatError("bad_nick", "A nick is 3-24 letters a-z, digits or _")
        answer = self.api_factory(self.server).register(folded)
        return self._signed_in(answer["token"], answer["user"])

    def sign_in_code(self, code):
        """The token from another machine (its code)."""
        token = str(code or "").strip()
        me = self.api_factory(self.server, token).me()
        return self._signed_in(token, me)

    def _signed_in(self, token, me):
        self.stop()
        self.state = State()
        self.store.set_token(token)
        self.store.set_me(records.user(me))
        self.store.set_since(0)
        self.store.set_outbox([])
        self.start()
        return self.state.me

    def code(self):
        """This account's sign-in code, to sign in on another machine."""
        return self.store.token()

    def sign_out(self):
        self.stop()
        self.store.forget()
        self.state = State()
        self._status("signed_out")

    def stop(self):
        if self.link is not None:
            self.link.stop()
        self.link = None
        self.protocol = None

    def _status(self, status):
        if self.state.status != status:
            self.state.status = status
            self.tell("status", status)

    # ---------------------------------------------------------------- the cache
    def _load_cache(self):
        st = self.state
        st.me = self.store.me()
        st.chats = {c["id"]: c for c in self.store.chats() if isinstance(c, dict) and "id" in c}
        st.messages = {cid: self.store.messages(cid) for cid in st.chats}
        st.pending = {}
        for msg in self.store.outbox():
            st.pending.setdefault(msg["chat"], []).append(self._pending_of(msg))

    def _pending_of(self, msg):
        return {"cid": msg["cid"], "chat": msg["chat"], "text": msg["text"],
                "reply_to": msg.get("reply_to"), "at": msg.get("at") or _now_ms(),
                "from_id": (self.state.me or {}).get("id"), "state": "sending", "error": None,
                "file": records.file(msg.get("file_meta")) if msg.get("file") else None,
                "upload": None}

    def _save_chats(self):
        self.store.set_chats(self.state.chats.values())

    def _save_outbox(self):
        if self.protocol is not None:
            self.store.set_outbox(self.protocol.outbox)

    # ---------------------------------------------------------------- the link
    def _connect(self, token):
        self.api = self.api_factory(self.server, token)
        p = self._link_module.Protocol(since=self.store.since(), outbox=self.store.outbox())
        p.on_event = self._event
        p.on_ack = self._ack
        p.on_error = self._error
        p.on_resync = self._resync_frame
        p.on_caught_up = self._caught_up
        p.on_state = self._link_state
        self.protocol = p
        self._status("connecting")
        self.link = self.link_factory(self.server, token, p)
        self.link.start()

    def _link_state(self, state):
        self._status({"open": "online", "connecting": "connecting"}.get(state, "offline"))

    def _caught_up(self, seq):
        self.store.set_since(self.protocol.since)
        self.tell("caught_up", seq)

    def _resync_frame(self):
        try:
            self.resync()
        except _api.ChatError as exc:
            self.tell("error", {"code": exc.code, "text": exc.text})

    def resync(self):
        """Everything again over HTTP: me, the chats, the newest messages, the friends."""
        st = self.state
        me = records.user(self.api.me())
        st.me = me
        self.store.set_me(me)
        answer = self.api.chats()
        chats = {}
        for raw in answer.get("chats", []):
            try:
                c = records.chat(raw)
            except records.Bad:
                continue
            chats[c["id"]] = c
        st.chats = chats
        for cid in list(st.messages):
            if cid not in chats:
                st.messages.pop(cid, None)
        for cid in chats:
            fresh = [records.message(m) for m in self.api.history(cid, limit=HISTORY)]
            st.messages[cid] = records.merge(st.messages.get(cid, []), fresh)
            self.store.set_messages(cid, st.messages[cid])
        self._save_chats()
        try:
            self.read_people(tell=False)
        except _api.ChatError:
            pass
        seq = int(answer.get("seq") or 0)
        if self.protocol is not None:
            self.protocol.since = max(self.protocol.since, seq)
            self.store.set_since(self.protocol.since)
        self.tell("resync")

    def _read_friends(self):
        answer = self.api.friends()
        st = self.state
        st.friends = {k: [records.user(u) for u in answer.get(k, [])]
                      for k in ("friends", "incoming", "outgoing")}
        for u in st.friends["friends"]:
            if "online" in u:
                st.online[u["id"]] = {"online": u["online"], "last_seen": u["last_seen"]}

    def read_people(self, tell=True):
        """Everybody in the studio but me, with presence."""
        if self.api is None or self.state.me is None:
            raise _api.ChatError("signed_out", "Sign in first")
        st = self.state
        st.people = [records.user(u) for u in self.api.people()]
        for u in st.people:
            if "online" in u:
                st.online[u["id"]] = {"online": u["online"], "last_seen": u["last_seen"]}
        if tell:
            self.tell("people")
        return st.people

    # ---------------------------------------------------------------- events
    def _event(self, e):
        handler = getattr(self, "_on_" + e["kind"], None)
        if handler is not None:
            handler(e)
        if "seq" in e and self.protocol is not None:
            self.store.set_since(self.protocol.since)
        self.tell(e["kind"], e)

    def _on_message(self, e):
        m = e["message"]
        st = self.state
        chat = m["chat"]
        known = any(x["id"] == m["id"] for x in st.messages.get(chat, []))
        st.messages[chat] = records.merge(st.messages.get(chat, []), [m])
        self.store.set_messages(chat, st.messages[chat])
        mine = st.me is not None and m["from_id"] == st.me["id"]
        if mine and m.get("cid"):
            self._drop_pending(chat, m["cid"])
        c = st.chats.get(chat)
        if c is None:
            self._refresh_chats()
            return
        if not c.get("last") or c["last"]["seq"] <= m["seq"]:
            c["last"] = m
        if mine:
            c["read_upto"] = max(c.get("read_upto", 0), m["seq"])
        elif not known:
            c["unread"] = c.get("unread", 0) + 1
        self.state.typing.get(chat, {}).pop(m["from_id"], None)
        self._save_chats()

    def _change(self, chat, mid, **fields):
        msgs = self.state.messages.get(chat, [])
        for i, m in enumerate(msgs):
            if m["id"] == mid:
                msgs[i] = dict(m, **fields)
                c = self.state.chats.get(chat)
                if c and c.get("last") and c["last"]["id"] == mid:
                    c["last"] = msgs[i]
                    self._save_chats()
                self.store.set_messages(chat, msgs)
                return

    def _on_edited(self, e):
        self._change(e["chat_id"], e["id"], text=e["text"], edited_at=e["edited_at"])

    def _on_deleted(self, e):
        self._change(e["chat_id"], e["id"], text="", deleted=True)

    def _on_read(self, e):
        chat = e["chat_id"]
        st = self.state
        st.reads.setdefault(chat, {})[e["user_id"]] = e["upto"]
        c = st.chats.get(chat)
        if c is not None and st.me is not None and e["user_id"] == st.me["id"]:
            c["read_upto"] = max(c.get("read_upto", 0), e["upto"])
            c["unread"] = records.unread(c, st.messages.get(chat, []), st.me["id"])
            self._save_chats()

    def _on_chat(self, e):
        c = e["chat"]
        old = self.state.chats.get(c["id"], {})
        for key in ("last", "unread", "read_upto"):
            if key not in c and key in old:
                c[key] = old[key]
        c.setdefault("unread", 0)
        c.setdefault("read_upto", 0)
        self.state.chats[c["id"]] = c
        self.state.messages.setdefault(c["id"], self.store.messages(c["id"]))
        self._save_chats()

    def _on_member_added(self, e):
        c = self.state.chats.get(e["chat_id"])
        if c is None:
            self._refresh_chats()
            return
        if not any(u["id"] == e["user"]["id"] for u in c["members"]):
            c["members"].append(e["user"])
            self._save_chats()

    def _on_member_removed(self, e):
        st = self.state
        chat = e["chat_id"]
        if st.me is not None and e["user_id"] == st.me["id"]:
            st.chats.pop(chat, None)
            st.messages.pop(chat, None)
            st.pending.pop(chat, None)
        elif chat in st.chats:
            c = st.chats[chat]
            c["members"] = [u for u in c["members"] if u["id"] != e["user_id"]]
            c["admin"] = e.get("admin")
        self._save_chats()

    def _friend_lists(self, user=None, drop=None):
        lists = self.state.friends
        for key in lists:
            lists[key] = [u for u in lists[key] if u["id"] not in (drop or ())]
        return lists

    def _on_friend_request(self, e):
        self._friend_lists(drop=[e["user"]["id"]])["incoming"].append(e["user"])

    def _on_request_sent(self, e):
        self._friend_lists(drop=[e["user"]["id"]])["outgoing"].append(e["user"])

    def _on_friend_added(self, e):
        self._friend_lists(drop=[e["user"]["id"]])["friends"].append(e["user"])

    def _on_friend_removed(self, e):
        self._friend_lists(drop=[e["user_id"]])

    def _on_request_cancelled(self, e):
        me = (self.state.me or {}).get("id")
        other = e["to_id"] if e["from_id"] == me else e["from_id"]
        lists = self.state.friends
        lists["incoming"] = [u for u in lists["incoming"] if u["id"] != other]
        lists["outgoing"] = [u for u in lists["outgoing"] if u["id"] != other]

    def _on_user(self, e):
        u = e["user"]
        st = self.state
        if st.me is not None and st.me["id"] == u["id"]:
            st.me = dict(st.me, **u)
            self.store.set_me(st.me)
        for lst in list(st.friends.values()) + [st.people]:
            for i, x in enumerate(lst):
                if x["id"] == u["id"]:
                    lst[i] = dict(x, **u)
        if (st.me is None or st.me["id"] != u["id"])                 and not any(x["id"] == u["id"] for x in st.people):
            st.people.append(dict(u))           # a newcomer: everybody sees everybody
        for c in st.chats.values():
            for i, x in enumerate(c["members"]):
                if x["id"] == u["id"]:
                    c["members"][i] = dict(x, **u)
        self._save_chats()

    def _on_presence(self, e):
        st = self.state
        seen = {"online": e["online"], "last_seen": e["last_seen"]}
        st.online[e["user_id"]] = seen
        for lst in (list(st.friends.values()) + [st.people]
                    + [c["members"] for c in st.chats.values()]):
            for i, x in enumerate(lst):
                if x["id"] == e["user_id"]:
                    lst[i] = dict(x, **seen)

    def _on_reaction(self, e):
        self._react_local(e["chat_id"], e["id"], e["emoji"], e["user_id"], e["on"])

    def _react_local(self, chat, mid, emoji, user_id, on):
        st = self.state
        msgs = st.messages.get(chat, [])
        for i, m in enumerate(msgs):
            if m["id"] == mid:
                msgs[i] = dict(m, reactions=records.toggled(m.get("reactions"), emoji, user_id, on))
                self.store.set_messages(chat, msgs)
                c = st.chats.get(chat)
                if c is not None and (c.get("last") or {}).get("id") == mid:
                    c["last"] = msgs[i]
                return msgs[i]
        return None

    def react(self, chat, message_id, emoji):
        """My reaction on a message toggled; answers whether it is on now (None offline)."""
        self._need()
        m = next((x for x in self.state.messages.get(chat, []) if x["id"] == message_id), None)
        if m is None or m.get("deleted"):
            return None
        me = self.state.me["id"]
        on = me not in (m.get("reactions") or {}).get(emoji, [])
        if not self.protocol.push({"type": "react", "chat": chat, "id": message_id,
                                   "emoji": emoji, "on": on}):
            return None
        self._react_local(chat, message_id, emoji, me, on)
        self.tell("reaction", {"chat_id": chat, "id": message_id, "user_id": me,
                               "emoji": emoji, "on": on, "local": True})
        return on

    def set_avatar(self, data, content_type="image/jpeg"):
        """My picture uploaded; the server's user event brings avatar_v to everybody."""
        self._need()
        me = records.user(self.api.put_avatar(data, content_type))
        self.state.me = dict(self.state.me, **me)
        self.store.set_me(self.state.me)
        self._on_user({"user": me})
        self.tell("user", {"user": me})
        return me

    def _on_typing(self, e):
        self.state.typing.setdefault(e["chat_id"], {})[e["user_id"]] = time.monotonic()

    def _refresh_chats(self):
        try:
            answer = self.api.chats()
        except _api.ChatError:
            return
        for raw in answer.get("chats", []):
            try:
                c = records.chat(raw)
            except records.Bad:
                continue
            if c["id"] not in self.state.chats:
                self.state.chats[c["id"]] = c
                self.state.messages[c["id"]] = [records.message(m) for m in self.api.history(c["id"])]
                self.store.set_messages(c["id"], self.state.messages[c["id"]])
        self._save_chats()

    # ---------------------------------------------------------------- acks and refusals
    def _drop_pending(self, chat, cid):
        rows = self.state.pending.get(chat, [])
        self.state.pending[chat] = [p for p in rows if p["cid"] != cid]
        if not self.state.pending[chat]:
            self.state.pending.pop(chat, None)

    def _find_pending(self, cid):
        for rows in self.state.pending.values():
            for p in rows:
                if p["cid"] == cid:
                    return p
        return None

    def _ack(self, e):
        p = self._find_pending(e["cid"])
        if p is not None:
            self._drop_pending(p["chat"], e["cid"])
        self._save_outbox()
        self.tell("ack", e)

    def _error(self, e):
        p = self._find_pending(e["cid"]) if e.get("cid") else None
        if p is not None:
            p["state"] = "failed"
            p["error"] = e["text"]
            self._save_outbox()
            self.tell("failed", dict(e, chat=p["chat"]))
        else:
            self.tell("error", e)
        if e.get("code") == "bad_token":
            self.sign_out()

    # ---------------------------------------------------------------- what the animator does
    def _need(self):
        if self.protocol is None or self.state.me is None:
            raise _api.ChatError("signed_out", "Sign in first")

    def send(self, chat, text, reply_to=None):
        """The message's cid; it shows at once as pending and goes when the link is up."""
        self._need()
        text = str(text or "").strip()
        if not text:
            return None
        cid = uuid.uuid4().hex
        msg = {"type": "send", "chat": chat, "cid": cid, "text": text, "reply_to": reply_to,
               "at": _now_ms()}
        self.state.pending.setdefault(chat, []).append(self._pending_of(msg))
        self.protocol.queue(msg)
        self._save_outbox()
        self.tell("pending", {"chat": chat, "cid": cid})
        return cid

    # ---------------------------------------------------------------- files (2026-10-22)
    def add_upload(self, chat, cid, text, f, local):
        """A file message pending while its file uploads (files.py drives it)."""
        self._need()
        p = {"cid": cid, "chat": chat, "text": str(text or "").strip(), "reply_to": None,
             "at": _now_ms(), "from_id": (self.state.me or {}).get("id"), "state": "sending",
             "error": None, "file": f,
             "upload": {"local": local, "id": None, "phase": "zip", "progress": 0.0,
                        "cancelled": False}}
        self.state.pending.setdefault(chat, []).append(p)
        self.tell("pending", {"chat": chat, "cid": cid})
        return p

    def upload_done(self, cid, f):
        """The file is on the server: the message goes out like any other (and into the outbox)."""
        p = self._find_pending(cid)
        if p is None:
            return False
        p["upload"] = None
        p["file"] = f
        self.protocol.queue(self._frame(p))
        self._save_outbox()
        self.tell("pending", {"chat": p["chat"], "cid": cid})
        return True

    def upload_failed(self, cid, text):
        p = self._find_pending(cid)
        if p is None:
            return False
        p["state"], p["error"] = "failed", text
        self.tell("failed", {"chat": p["chat"], "cid": cid, "text": text})
        return True

    def drop_upload(self, cid):
        p = self._find_pending(cid)
        if p is None:
            return False
        self._drop_pending(p["chat"], cid)
        self.tell("pending", {"chat": p["chat"], "cid": cid})
        return True

    def _frame(self, p):
        msg = {"type": "send", "chat": p["chat"], "cid": p["cid"], "text": p["text"],
               "reply_to": p["reply_to"], "at": p["at"]}
        if p.get("file") and p["file"].get("id"):
            msg["file"] = p["file"]["id"]
            msg["file_meta"] = dict(p["file"])
        return msg

    def retry(self, cid):
        p = self._find_pending(cid)
        if p is None or p["state"] != "failed":
            return False
        if p.get("upload"):
            from . import files
            return files.start(self, cid)
        p["state"], p["error"] = "sending", None
        self.protocol.queue(self._frame(p))
        self._save_outbox()
        self.tell("pending", {"chat": p["chat"], "cid": cid})
        return True

    def discard(self, cid):
        """A failed (or still waiting) message thrown away."""
        p = self._find_pending(cid)
        if p is None:
            return False
        if p.get("upload"):
            from . import files
            files.cancel(self, cid)
            if p.get("state") != "failed":
                return True       # the thread stops at its next part, then the pending goes
        self._drop_pending(p["chat"], cid)
        if self.protocol is not None:
            self.protocol.outbox = [m for m in self.protocol.outbox if m.get("cid") != cid]
        self._save_outbox()
        self.tell("pending", {"chat": p["chat"], "cid": cid})
        return True

    def edit(self, chat, message_id, text):
        self._need()
        return self.protocol.push({"type": "edit", "chat": chat, "id": message_id, "text": text})

    def delete(self, chat, message_id):
        self._need()
        return self.protocol.push({"type": "delete", "chat": chat, "id": message_id})

    def read(self, chat):
        """Everything in the chat read; False when nothing new or offline."""
        self._need()
        c = self.state.chats.get(chat)
        msgs = self.state.messages.get(chat, [])
        if c is None or not msgs:
            return False
        upto = msgs[-1]["seq"]
        if upto <= c.get("read_upto", 0):
            return False
        if not self.protocol.push({"type": "read", "chat": chat, "upto": upto}):
            return False
        c["read_upto"] = upto
        c["unread"] = 0
        self._save_chats()
        self.tell("read_local", {"chat_id": chat, "upto": upto})
        return True

    def typing(self, chat):
        self._need()
        now = time.monotonic()
        if now - self._typed.get(chat, -TYPING_S) < TYPING_S:
            return False
        if self.protocol.push({"type": "typing", "chat": chat}):
            self._typed[chat] = now
            return True
        return False

    def open_dm(self, user_id):
        self._need()
        c = records.chat(self.api.dm(user_id))
        self.state.chats[c["id"]] = dict(self.state.chats.get(c["id"], {}), **c)
        self.state.messages.setdefault(c["id"], [])
        self._save_chats()
        self.tell("chat", {"chat": c})
        return c["id"]

    def load_history(self, chat):
        """Older messages before the oldest held; how many came."""
        self._need()
        msgs = self.state.messages.get(chat, [])
        before = msgs[0]["seq"] if msgs else None
        older = [records.message(m) for m in self.api.history(chat, before=before, limit=HISTORY)]
        self.state.messages[chat] = records.merge(msgs, older)
        self.store.set_messages(chat, self.state.messages[chat])
        self.tell("history", {"chat": chat, "count": len(older)})
        return len(older)


# -------------------------------------------------------------------- one per Maya
def _base():
    try:
        from maya import cmds
        return os.path.join(cmds.internalVar(userAppDir=True), "SkeldarChat")
    except Exception:
        return os.path.join(os.path.expanduser("~"), "SkeldarChat")


def get():
    """The session of this Maya, kept on sys (module reloads keep it)."""
    held = getattr(sys, "_skeldar_chat", None)
    if held is not None:
        return held
    from . import server
    url = server()
    made = Session(url, _store.Store.for_server(_base(), url))
    sys._skeldar_chat = made
    made.start()
    return made


def close():
    held = getattr(sys, "_skeldar_chat", None)
    if held is not None:
        held.stop()
        del sys._skeldar_chat
