"""The chat server against staging (plan 2026-10-19-chat-server).

    $env:CHAT_SERVER = 'https://skeldar-chat-staging.<sub>.workers.dev'
    mayapy docs/superpowers/plans/verify_chat_server.py all        (or a phase name)

Every user it makes is named zzt_<hex>_<label> and deleted at the end (DELETE /v1/me).
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat"))
import wsclient  # noqa: E402

SERVER = os.environ.get("CHAT_SERVER", "").rstrip("/")
RUN = uuid.uuid4().hex[:6]
GATES = []


def gate(name, ok, detail=""):
    GATES.append((name, bool(ok)))
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, (" - %s" % (detail,)) if detail != "" else ""))


def call(method, path, token=None, body=None, raw=None, ctype=None, timeout=20):
    headers = {"user-agent": "skeldar-chat-verify/1"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["content-type"] = "application/json"
    if raw is not None:
        data = raw
        headers["content-type"] = ctype
    if token:
        headers["authorization"] = "Bearer " + token
    req = urllib.request.Request(SERVER + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as answer:
            return answer.status, answer.read(), answer.headers.get("content-type", "")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), exc.headers.get("content-type", "")


def jcall(method, path, token=None, body=None, raw=None, ctype=None):
    status, data, ctype_ = call(method, path, token, body, raw, ctype)
    return status, (json.loads(data) if data and "json" in ctype_ else data)


class Users(object):
    made = []

    @classmethod
    def make(cls, label):
        nick = "zzt_%s_%s" % (RUN, label)
        status, doc = jcall("POST", "/v1/register", body={"nick": nick, "name": label.title()})
        if status != 200:
            raise RuntimeError("register %s answered %s %s" % (nick, status, doc))
        cls.made.append(doc["token"])
        return doc["token"], doc["user"]

    @classmethod
    def clean(cls):
        for token in cls.made:
            call("DELETE", "/v1/me", token)


def ws(token):
    return wsclient.WS(SERVER.replace("https://", "wss://") + "/v1/ws", token)


# ------------------------------------------------------------------ phases

def phase_signin():
    status, doc = jcall("GET", "/v1/health")
    gate("health answers", status == 200 and doc.get("ok") is True, doc)
    token, user = Users.make("alice")
    gate("register gives a skc_ token and a user", token.startswith("skc_") and user["nick"].endswith("_alice"), user)
    status, doc = jcall("POST", "/v1/register", body={"nick": user["nick"].upper()})
    gate("a taken nick is refused, whatever its case", status == 409 and doc.get("error") == "nick_taken", doc)
    status, doc = jcall("POST", "/v1/register", body={"nick": "a b"})
    gate("a bad nick is refused", status == 400 and doc.get("error") == "bad_nick", doc)
    status, doc = jcall("POST", "/v1/register", body={"nick": "admin"})
    gate("a reserved nick is refused", status == 409 and doc.get("error") == "nick_taken", doc)
    status, doc = jcall("GET", "/v1/me", token)
    gate("the token signs in", status == 200 and doc.get("id") == user["id"], doc)
    status, doc = jcall("GET", "/v1/me", "skc_wrong")
    gate("a wrong token is refused", status == 401 and doc.get("error") == "bad_token", doc)
    status, doc = jcall("GET", "/v1/me")
    gate("no token is refused", status == 401, doc)


PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
       b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82")


def phase_profile():
    token, user = Users.make("bob")
    status, doc = jcall("PATCH", "/v1/me", token, {"name": "  Bob Builder  "})
    gate("a name is trimmed and kept", status == 200 and doc["name"] == "Bob Builder", doc)
    status, doc = jcall("PATCH", "/v1/me", token, {"name": "   "})
    gate("an empty name is refused", status == 400 and doc.get("error") == "bad_name", doc)
    status, doc = jcall("PUT", "/v1/me/avatar", token, raw=PNG, ctype="image/png")
    gate("a PNG avatar is taken, its version up", status == 200 and doc["avatar_v"] == 1, doc)
    status, data, ctype = call("GET", "/v1/avatar/u/" + user["id"], token)
    gate("the avatar comes back byte for byte", status == 200 and data == PNG and ctype == "image/png", ctype)
    status, doc = jcall("PUT", "/v1/me/avatar", token, raw=b"GIF89a....", ctype="image/gif")
    gate("a picture that is not JPEG or PNG is refused", status == 400 and doc.get("error") == "bad_picture", doc)
    status, doc = jcall("PUT", "/v1/me/avatar", token, raw=PNG + b"\0" * (256 * 1024), ctype="image/png")
    gate("an avatar over 256 KB is refused", status == 413 and doc.get("error") == "too_big", doc)


def phase_friends():
    ta, a = Users.make("fa")
    tb, b = Users.make("fb")
    tc, c = Users.make("fc")
    status, doc = jcall("GET", "/v1/users?q=zzt_%s_f" % RUN, ta)
    nicks = sorted(u["nick"] for u in doc.get("users", []))
    gate("search by prefix finds the others, not me", status == 200 and nicks == sorted([b["nick"], c["nick"]]), nicks)
    status, doc = jcall("GET", "/v1/users?q=zzt%25", ta)
    gate("a % in the query is a letter, not a wildcard", status == 200 and doc["users"] == [], doc)
    status, doc = jcall("POST", "/v1/friends/request", ta, {"nick": b["nick"]})
    gate("a request is sent", status == 200 and doc["state"] == "requested", doc)
    status, doc = jcall("GET", "/v1/friends", tb)
    gate("the other sees it incoming", [u["id"] for u in doc["incoming"]] == [a["id"]], doc)
    status, doc = jcall("POST", "/v1/friends/accept", tb, {"user": a["id"]})
    gate("accept", status == 200, doc)
    status, doc = jcall("GET", "/v1/friends", ta)
    gate("they are friends both ways", [u["id"] for u in doc["friends"]] == [b["id"]] and not doc["outgoing"], doc)
    status, doc = jcall("POST", "/v1/friends/request", tc, {"nick": a["nick"]})
    status, doc = jcall("POST", "/v1/friends/request", ta, {"nick": c["nick"]})
    gate("asking someone who already asked you makes you friends", doc.get("state") == "friends", doc)
    status, doc = jcall("DELETE", "/v1/friends/" + c["id"], ta)
    status, doc = jcall("GET", "/v1/friends", tc)
    gate("remove takes the friend off both lists", doc["friends"] == [], doc)
    jcall("POST", "/v1/friends/request", tc, {"nick": b["nick"]})
    status, doc = jcall("POST", "/v1/friends/cancel", tc, {"user": b["id"]})
    status, doc = jcall("GET", "/v1/friends", tb)
    gate("cancel takes the request back", doc["incoming"] == [], doc)
    jcall("POST", "/v1/friends/request", tc, {"nick": b["nick"]})
    jcall("POST", "/v1/friends/decline", tb, {"user": c["id"]})
    status, doc = jcall("GET", "/v1/friends", tc)
    gate("decline clears the sender's outgoing", doc["outgoing"] == [], doc)
    status, doc = jcall("POST", "/v1/friends/request", ta, {"nick": a["nick"]})
    gate("asking yourself is refused", status == 400 and doc.get("error") == "self", doc)
    status, doc = jcall("POST", "/v1/friends/request", ta, {"nick": "zzt_nobody_here"})
    gate("an unknown nick is refused", status == 404 and doc.get("error") == "no_user", doc)


def friends_of(*pairs):
    for (ta, a), (tb, b) in pairs:
        jcall("POST", "/v1/friends/request", ta, {"nick": b["nick"]})
        jcall("POST", "/v1/friends/accept", tb, {"user": a["id"]})


def phase_chats():
    A, B, C, D = (Users.make(x) for x in ("ca", "cb", "cc", "cd"))
    friends_of((A, B), (A, C))
    status, doc = jcall("POST", "/v1/chats", A[0], {"kind": "dm", "with": D[1]["id"]})
    gate("a dm with anybody, no friendship asked (2026-10-20)", status == 200 and doc["kind"] == "dm", doc)
    status, dm = jcall("POST", "/v1/chats", A[0], {"kind": "dm", "with": B[1]["id"]})
    gate("a dm with a friend", status == 200 and dm["kind"] == "dm" and len(dm["members"]) == 2, dm)
    status, again = jcall("POST", "/v1/chats", B[0], {"kind": "dm", "with": A[1]["id"]})
    gate("the same dm from the other side, never a second", again.get("id") == dm["id"], again)
    status, doc = jcall("POST", "/v1/chats", A[0], {"kind": "group", "name": "G", "members": [D[1]["id"]]})
    gate("a group with anybody", status == 200 and len(doc["members"]) == 2, doc)
    status, g = jcall("POST", "/v1/chats", A[0], {"kind": "group", "name": " Crypt anim ", "members": [B[1]["id"]]})
    gate("a group, its creator the admin", status == 200 and g["admin"] == A[1]["id"] and g["name"] == "Crypt anim", g)
    status, doc = jcall("PATCH", "/v1/chats/" + g["id"], B[0], {"name": "Mine"})
    gate("a member who is not admin cannot rename", status == 403 and doc.get("error") == "not_admin", doc)
    status, doc = jcall("PATCH", "/v1/chats/" + g["id"], A[0], {"name": "Crypt"})
    gate("the admin renames", status == 200 and doc["name"] == "Crypt", doc)
    status, doc = jcall("POST", "/v1/chats/%s/members" % g["id"], A[0], {"user": C[1]["id"]})
    gate("the admin adds a friend", status == 200 and len(doc["members"]) == 3, doc)
    status, doc = jcall("POST", "/v1/chats/%s/members" % g["id"], B[0], {"user": A[1]["id"]})
    gate("a non-admin cannot add", status == 403, doc)
    status, doc = jcall("DELETE", "/v1/chats/%s/members/%s" % (g["id"], C[1]["id"]), A[0])
    status, chats = jcall("GET", "/v1/chats", C[0])
    gate("a removed member no longer has the group", g["id"] not in [c["id"] for c in chats["chats"]], chats)
    status, doc = jcall("DELETE", "/v1/chats/%s/members/%s" % (g["id"], A[1]["id"]), A[0])
    status, chats = jcall("GET", "/v1/chats", B[0])
    group = [c for c in chats["chats"] if c["id"] == g["id"]]
    gate("an admin who leaves hands the group on", group and group[0]["admin"] == B[1]["id"], group)
    gate("GET /v1/chats carries the newest event seq", isinstance(chats.get("seq"), int) and chats["seq"] > 0, chats.get("seq"))
    status, doc = jcall("GET", "/v1/chats/%s/messages" % g["id"], A[0])
    gate("someone who left cannot read the history", status == 403 and doc.get("error") == "not_member", doc)
    status, doc = jcall("PUT", "/v1/chats/%s/avatar" % g["id"], B[0], raw=PNG, ctype="image/png")
    status, data, ctype = call("GET", "/v1/avatar/c/" + g["id"], B[0])
    gate("a group avatar", status == 200 and data == PNG, ctype)


def phase_live():
    A, B, S = Users.make("la"), Users.make("lb"), Users.make("ls")
    friends_of((A, B))
    status, dm = jcall("POST", "/v1/chats", A[0], {"kind": "dm", "with": B[1]["id"]})
    seq0 = jcall("GET", "/v1/chats", B[0])[1]["seq"]
    wa, wb = ws(A[0]), ws(B[0])
    wb.send({"type": "hello", "since": seq0})
    done, _ = wb.until(lambda e: e["kind"] == "caught_up")
    gate("hello answers caught_up", done is not None and done["seq"] >= seq0, done)
    wa.send_text("ping")
    seen, deadline = [], time.time() + 5  # a presence event can arrive first
    while time.time() < deadline and "pong" not in seen:
        try:
            seen.append(wa.recv_text(max(0.05, deadline - time.time())))
        except OSError:
            break
    gate("ping answers pong", "pong" in seen, seen[-3:])
    t0 = time.time()
    wa.send({"type": "send", "chat": dm["id"], "cid": "c1", "text": "hello  "})
    ack, _ = wa.until(lambda e: e["kind"] == "ack")
    got, _ = wb.until(lambda e: e["kind"] == "message")
    gate("the other gets the message within 1 s", got is not None and time.time() - t0 < 1.0, round(time.time() - t0, 3))
    gate("the text is trimmed, the ack names it", got and got["message"]["text"] == "hello" and ack["id"] == got["message"]["id"], (ack, got))
    wa.send({"type": "send", "chat": dm["id"], "cid": "c1", "text": "hello"})
    again, _ = wa.until(lambda e: e["kind"] == "ack")
    msgs = jcall("GET", "/v1/chats/%s/messages" % dm["id"], A[0])[1]["messages"]
    gate("the same cid twice is one message", again["id"] == ack["id"] and len(msgs) == 1, len(msgs))
    wa.send({"type": "send", "chat": dm["id"], "cid": "c2", "text": "re", "reply_to": ack["id"]})
    reply, _ = wb.until(lambda e: e["kind"] == "message")
    gate("a reply carries its original", reply and reply["message"]["reply_to"] == ack["id"], reply)
    wa.send({"type": "edit", "chat": dm["id"], "id": ack["id"], "text": "hello there"})
    ed, _ = wb.until(lambda e: e["kind"] == "edited")
    gate("an edit reaches the other", ed and ed["text"] == "hello there" and ed["edited_at"], ed)
    wb.send({"type": "edit", "chat": dm["id"], "id": ack["id"], "text": "mine now"})
    err, _ = wb.until(lambda e: e["kind"] == "error")
    gate("editing someone else's message is refused", err and err["code"] == "not_yours", err)
    wb.send({"type": "read", "chat": dm["id"], "upto": reply["message"]["seq"]})
    rd, _ = wa.until(lambda e: e["kind"] == "read")
    gate("a read mark reaches the sender", rd and rd["user_id"] == B[1]["id"] and rd["upto"] == reply["message"]["seq"], rd)
    wa.send({"type": "typing", "chat": dm["id"]})
    ty, _ = wb.until(lambda e: e["kind"] == "typing")
    gate("typing reaches the other, with no seq", ty and "seq" not in ty, ty)
    wa.send({"type": "delete", "chat": dm["id"], "id": reply["message"]["id"]})
    de, _ = wb.until(lambda e: e["kind"] == "deleted")
    msgs = jcall("GET", "/v1/chats/%s/messages" % dm["id"], B[0])[1]["messages"]
    gate("a delete leaves an empty, deleted message", de and msgs[-1]["deleted"] and msgs[-1]["text"] == "", msgs[-1])
    last_seen = got["seq"]
    wb.close()
    wa.send({"type": "send", "chat": dm["id"], "cid": "c3", "text": "while you were away"})
    wa.until(lambda e: e["kind"] == "ack")
    wb = ws(B[0])
    wb.send({"type": "hello", "since": last_seen})
    done, seen = wb.until(lambda e: e["kind"] == "caught_up")
    texts = [e["message"]["text"] for e in seen if e["kind"] == "message"]
    gate("hello since a seq brings what was missed", "while you were away" in texts and "re" in texts, texts)
    wb.send({"type": "hello", "since": 0})
    rs, _ = wb.until(lambda e: e["kind"] == "resync")
    gate("hello since 0 asks for a resync", rs is not None, rs)
    ws_s = ws(S[0])
    ws_s.send({"type": "send", "chat": dm["id"], "cid": "x", "text": "let me in"})
    err, _ = ws_s.until(lambda e: e["kind"] == "error")
    gate("a stranger cannot write into the chat", err and err["code"] == "not_member", err)
    wa.send({"type": "send", "chat": dm["id"], "cid": "big", "text": "y" * 4001})
    err, _ = wa.until(lambda e: e["kind"] == "error")
    gate("a text over 4000 characters is refused", err and err["code"] == "too_long", err)
    for i in range(25):
        wa.send({"type": "send", "chat": dm["id"], "cid": "flood%d" % i, "text": "x"})
    flood = wa.events(3)
    gate("more than 20 messages in 10 s are refused", any(e["kind"] == "error" and e["code"] == "too_many" for e in flood))
    jcall("DELETE", "/v1/friends/" + B[1]["id"], A[0])
    time.sleep(11)
    wa.events(0.5)
    wa.send({"type": "send", "chat": dm["id"], "cid": "c9", "text": "still?"})
    err, seen9 = wa.until(lambda e: e["kind"] in ("error", "ack"))
    err = err if err and err["kind"] == "error" else None
    gate("a dm keeps going without friendship", err is None, err)
    for w in (wa, wb, ws_s):
        w.close()


def phase_presence():
    A, B = Users.make("pa"), Users.make("pb")
    friends_of((A, B))
    wa = ws(A[0])
    wa.send({"type": "hello", "since": jcall("GET", "/v1/chats", A[0])[1]["seq"]})
    wa.until(lambda e: e["kind"] == "caught_up")
    wb = ws(B[0])
    on, _ = wa.until(lambda e: e["kind"] == "presence" and e["user_id"] == B[1]["id"])
    gate("a friend coming online is announced", on and on["online"] is True, on)
    jcall("PATCH", "/v1/me", B[0], {"name": "Renamed"})
    ev, _ = wa.until(lambda e: e["kind"] == "user" and e["user"]["id"] == B[1]["id"])
    gate("a name change reaches everybody", ev and ev["user"]["name"] == "Renamed", ev)
    wb.close()
    off, _ = wa.until(lambda e: e["kind"] == "presence" and e["user_id"] == B[1]["id"] and not e["online"], 10)
    gate("going offline is announced with last_seen", off and off["last_seen"] > 0, off)
    friends = jcall("GET", "/v1/friends", A[0])[1]["friends"]
    gate("the friends list says offline and when", friends and friends[0]["online"] is False and friends[0]["last_seen"] > 0, friends)
    wa.close()



def phase_people():
    A, B, C = Users.make("qa"), Users.make("qb"), Users.make("qc")
    friends_of((A, B))
    status, doc = jcall("GET", "/v1/people", A[0])
    mine = {u["nick"]: u for u in doc.get("users", []) if u["nick"].startswith("zzt_%s_q" % RUN)}
    gate("people lists everybody but me", status == 200 and sorted(mine) == sorted([B[1]["nick"], C[1]["nick"]]), sorted(mine))
    gate("people says who is a friend", mine.get(B[1]["nick"], {}).get("relation") == "friend"
         and mine.get(C[1]["nick"], {}).get("relation") is None, mine)
    gate("people carries presence", all("online" in u and "last_seen" in u for u in mine.values()), mine)
    wa = ws(A[0])
    wa.send({"type": "hello", "since": jcall("GET", "/v1/chats", A[0])[1]["seq"]})
    wa.until(lambda e: e["kind"] == "caught_up")
    wc = ws(C[0])
    on, _ = wa.until(lambda e: e["kind"] == "presence" and e["user_id"] == C[1]["id"])
    gate("a stranger coming online is heard too", on and on["online"] is True, on)
    wc.close()
    wa.close()


def phase_react():
    A, B, C = Users.make("ra"), Users.make("rb"), Users.make("rc")
    status, dm = jcall("POST", "/v1/chats", A[0], {"kind": "dm", "with": B[1]["id"]})
    wa, wb = ws(A[0]), ws(B[0])
    for w, t in ((wa, A[0]), (wb, B[0])):
        w.send({"type": "hello", "since": jcall("GET", "/v1/chats", t)[1]["seq"]})
        w.until(lambda e: e["kind"] == "caught_up")
    wa.send({"type": "send", "chat": dm["id"], "cid": "r1", "text": "react to me"})
    ack, _ = wa.until(lambda e: e["kind"] == "ack")
    wb.send({"type": "react", "chat": dm["id"], "id": ack["id"], "emoji": "👍", "on": True})
    ev, _ = wa.until(lambda e: e["kind"] == "reaction")
    gate("a reaction reaches the other, with a seq", ev and ev["emoji"] == "👍" and ev["on"]
         and ev["user_id"] == B[1]["id"] and isinstance(ev.get("seq"), int), ev)
    wa.send({"type": "react", "chat": dm["id"], "id": ack["id"], "emoji": "👍", "on": True})
    wa.until(lambda e: e["kind"] == "reaction" and e["user_id"] == A[1]["id"])
    msgs = jcall("GET", "/v1/chats/%s/messages" % dm["id"], A[0])[1]["messages"]
    gate("history carries the reactions in order", msgs[-1].get("reactions") ==
         {"👍": [B[1]["id"], A[1]["id"]]}, msgs[-1].get("reactions"))
    wb.send({"type": "react", "chat": dm["id"], "id": ack["id"], "emoji": "👍", "on": False})
    off, _ = wa.until(lambda e: e["kind"] == "reaction" and not e["on"])
    msgs = jcall("GET", "/v1/chats/%s/messages" % dm["id"], A[0])[1]["messages"]
    gate("a reaction taken off", off and msgs[-1]["reactions"] == {"👍": [A[1]["id"]]}, msgs[-1])
    wb.send({"type": "react", "chat": dm["id"], "id": ack["id"], "emoji": "ok", "on": True})
    err, _ = wb.until(lambda e: e["kind"] == "error")
    gate("a word is not a reaction", err and err["code"] == "bad_emoji", err)
    wc = ws(C[0])
    wc.send({"type": "react", "chat": dm["id"], "id": ack["id"], "emoji": "🔥", "on": True})
    err, _ = wc.until(lambda e: e["kind"] == "error")
    gate("someone outside the chat cannot react", err and err["code"] == "not_member", err)
    wa.send({"type": "delete", "chat": dm["id"], "id": ack["id"]})
    wa.until(lambda e: e["kind"] == "deleted")
    msgs = jcall("GET", "/v1/chats/%s/messages" % dm["id"], A[0])[1]["messages"]
    gate("a deleted message loses its reactions", msgs[-1]["reactions"] == {}, msgs[-1])
    for w in (wa, wb, wc):
        w.close()


def phase_newcomer():
    A = Users.make("na")
    wa = ws(A[0])
    wa.send({"type": "hello", "since": jcall("GET", "/v1/chats", A[0])[1]["seq"]})
    wa.until(lambda e: e["kind"] == "caught_up")
    B = Users.make("nb")
    ev, _ = wa.until(lambda e: e["kind"] == "user" and e["user"]["id"] == B[1]["id"])
    gate("a new account reaches everybody at once", ev is not None and "seq" in ev, ev)
    wa.close()
    status, a = jcall("PUT", "/v1/me/avatar", A[0], raw=PNG, ctype="image/png")
    status2, data, ctype = call("GET", "/v1/avatar/u/" + A[1]["id"], B[0])
    gate("anybody reads my picture", status == 200 and a["avatar_v"] == 1 and data == PNG, (status, status2))


def phase_files():
    """Files (2026-10-22): a 40 MB zip in three parts, only for the chat's members."""
    A, B, C = Users.make("ia"), Users.make("ib"), Users.make("ic")
    status, dm = jcall("POST", "/v1/chats", A[0], {"kind": "dm", "with": B[1]["id"]})
    data = os.urandom(40 * 1024 * 1024)
    meta = {"chat": dm["id"], "name": "Run_Cycle.ma", "kind": "scene", "bytes": 90000000,
            "zip": len(data), "fps": 30, "range": [0, 48]}
    status, doc = jcall("POST", "/v1/files", C[0], dict(meta))
    gate("a stranger cannot start a file in the chat", status == 403 and doc.get("error") == "not_member", doc)
    status, doc = jcall("POST", "/v1/files", A[0], dict(meta, name="virus.exe"))
    gate("only .ma .mb .fbx", status == 400 and doc.get("error") == "bad_name", doc)
    status, doc = jcall("POST", "/v1/files", A[0], dict(meta, zip=2 * 1024 ** 3))
    gate("over 1 GB is refused", status == 413 and doc.get("error") == "too_big", doc)
    status, start = jcall("POST", "/v1/files", A[0], dict(meta))
    gate("an upload begins in 16 MB parts", status == 200 and start.get("parts") == 3
         and start.get("part_size") == 16 * 1024 * 1024, start)
    if status != 200:
        return
    fid, size = start["id"], start["part_size"]
    status, doc = jcall("PUT", "/v1/files/%s/parts/1" % fid, C[0], raw=data[:size], ctype="application/octet-stream")
    gate("a stranger cannot send a part", status == 403, doc)
    status, doc = jcall("PUT", "/v1/files/%s/parts/1" % fid, A[0], raw=data[:100], ctype="application/octet-stream")
    gate("a part of the wrong size is refused", status == 400 and doc.get("error") == "bad_part", doc)
    status, doc = jcall("POST", "/v1/files/%s/complete" % fid, A[0])
    gate("complete before the parts is refused", status == 409 and doc.get("error") == "missing_part", doc)
    t0 = time.time()
    ok = True
    for n in range(1, 4):
        status, doc, _ct = call("PUT", "/v1/files/%s/parts/%d" % (fid, n), A[0], raw=data[(n - 1) * size:n * size],
                           ctype="application/octet-stream", timeout=120)
        ok = ok and status == 200
    status, doc = jcall("POST", "/v1/files/%s/complete" % fid, A[0])
    gate("three parts and complete", ok and status == 200 and doc.get("state") == "ready",
         "%s in %.1f s" % (doc, time.time() - t0))
    status, data_b, _ct = call("GET", "/v1/files/" + fid, B[0])
    gate("not readable until it is in a message", status == 404, status)
    wa, wb = ws(A[0]), ws(B[0])
    for w, t in ((wa, A[0]), (wb, B[0])):
        w.send({"type": "hello", "since": jcall("GET", "/v1/chats", t)[1]["seq"]})
        w.until(lambda e: e["kind"] == "caught_up")
    wa.send({"type": "send", "chat": dm["id"], "cid": "f1", "text": "", "file": fid})
    ack, _ = wa.until(lambda e: e["kind"] in ("ack", "error"))
    got, _ = wb.until(lambda e: e["kind"] == "message")
    f = (got or {}).get("message", {}).get("file") or {}
    gate("a message with the file and no text", ack and ack["kind"] == "ack" and f.get("id") == fid
         and f.get("name") == "Run_Cycle.ma" and f.get("zip") == len(data) and f.get("range") == [0, 48]
         and got["message"]["text"] == "", (ack, f))
    wa.send({"type": "send", "chat": dm["id"], "cid": "f2", "text": "again", "file": fid})
    err, _ = wa.until(lambda e: e["kind"] == "error")
    gate("one file goes in one message", err and err["code"] == "not_ready", err)
    t0 = time.time()
    status, data_b, ctype = call("GET", "/v1/files/" + fid, B[0], timeout=120)
    gate("the other downloads it byte for byte", status == 200 and data_b == data and ctype == "application/zip",
         "%.1f s" % (time.time() - t0))
    status, _d, _c = call("GET", "/v1/files/" + fid, C[0])
    gate("a stranger cannot download it", status == 403, status)
    msgs = jcall("GET", "/v1/chats/%s/messages" % dm["id"], B[0])[1]["messages"]
    gate("history carries the file", (msgs[-1].get("file") or {}).get("id") == fid, msgs[-1].get("file"))
    wa.send({"type": "edit", "chat": dm["id"], "id": ack["id"], "text": "a caption later"})
    ed, _ = wb.until(lambda e: e["kind"] == "edited")
    gate("a file's caption can be edited", ed and ed["text"] == "a caption later", ed)
    wa.send({"type": "delete", "chat": dm["id"], "id": ack["id"]})
    wb.until(lambda e: e["kind"] == "deleted")
    time.sleep(1)
    status, _d, _c = call("GET", "/v1/files/" + fid, B[0])
    gate("deleting the message deletes the file", status == 404, status)
    status, start = jcall("POST", "/v1/files", A[0], dict(meta, zip=10))
    status, doc = jcall("DELETE", "/v1/files/" + start["id"], A[0])
    status2, doc2 = jcall("POST", "/v1/files/%s/complete" % start["id"], A[0])
    gate("a cancelled upload is gone", status == 200 and status2 == 404, (doc, doc2))
    for w in (wa, wb):
        w.close()


def phase_previews():
    """Previews and pictures (2026-10-22): a file's thumb with an animation's grid, only its
    sender puts it, only the chat's members read it; a picture is a file."""
    A, B, C = Users.make("wa"), Users.make("wb"), Users.make("wc")
    status, dm = jcall("POST", "/v1/chats", A[0], {"kind": "dm", "with": B[1]["id"]})
    data = os.urandom(2000)
    meta = {"chat": dm["id"], "name": "Walk.anim", "kind": "anim", "bytes": 5000, "zip": len(data)}
    status, start = jcall("POST", "/v1/files", A[0], dict(meta))
    fid = start["id"]
    jpeg = bytes([0xff, 0xd8, 0xff, 0xe0]) + os.urandom(3000)
    status, doc = jcall("PUT", "/v1/files/%s/thumb" % fid, B[0], raw=jpeg, ctype="image/jpeg")
    gate("only the sender puts a preview", status == 403, doc)
    status, doc = jcall("PUT", "/v1/files/%s/thumb" % fid, A[0], raw=b"not a picture", ctype="image/jpeg")
    gate("a preview is a JPEG or a PNG", status == 400 and doc.get("error") == "bad_picture", doc)
    status, doc = jcall("PUT", "/v1/files/%s/thumb" % fid, A[0], raw=bytes([0xff, 0xd8, 0xff]) + b"x" * (300 * 1024),
                        ctype="image/jpeg")
    gate("a preview is at most 256 KB", status == 413, doc)
    status, doc = jcall("PUT", "/v1/files/%s/thumb?cells=24&columns=5&step=2&fps=30" % fid, A[0],
                        raw=jpeg, ctype="image/jpeg")
    gate("the sender's preview with its grid", status == 200 and doc.get("thumb_v") == 1, doc)
    call("PUT", "/v1/files/%s/parts/1" % fid, A[0], raw=data, ctype="application/octet-stream")
    jcall("POST", "/v1/files/%s/complete" % fid, A[0])
    status, got, _ct = call("GET", "/v1/files/%s/thumb" % fid, B[0])
    gate("not readable before its message", status == 404, status)
    wa = ws(A[0])
    wa.send({"type": "hello", "since": jcall("GET", "/v1/chats", A[0])[1]["seq"]})
    wa.until(lambda e: e["kind"] == "caught_up")
    wa.send({"type": "send", "chat": dm["id"], "cid": "p1", "text": "", "file": fid})
    ack, _ = wa.until(lambda e: e["kind"] in ("ack", "error"))
    msgs = jcall("GET", "/v1/chats/%s/messages" % dm["id"], B[0])[1]["messages"]
    f = msgs[-1].get("file") or {}
    gate("the file says it has a preview and its grid", f.get("thumb_v") == 1 and f.get("sheet") ==
         {"cells": 24, "columns": 5, "step": 2, "fps": 30}, f)
    status, got, ctype = call("GET", "/v1/files/%s/thumb" % fid, B[0])
    gate("the other reads the preview byte for byte", status == 200 and got == jpeg and ctype == "image/jpeg",
         (status, ctype))
    status, _g, _c = call("GET", "/v1/files/%s/thumb" % fid, C[0])
    gate("a stranger cannot", status == 403, status)
    status, doc = jcall("PUT", "/v1/files/%s/thumb" % fid, A[0], raw=jpeg, ctype="image/jpeg")
    gate("no new preview once it is sent", status == 409, doc)
    status, start = jcall("POST", "/v1/files", A[0], {"chat": dm["id"], "name": "ref shot.jpeg", "kind": "image",
                                                      "bytes": 10, "zip": 10})
    gate("a picture is a file", status == 200 and start.get("id"), start)
    if status == 200:
        jcall("DELETE", "/v1/files/" + start["id"], A[0])
    status, doc = jcall("POST", "/v1/files", A[0], {"chat": dm["id"], "name": "a.gif", "kind": "image",
                                                    "bytes": 10, "zip": 10})
    gate("but only a .png or a .jpg", status == 400, doc)
    wa.close()


def phase_person():
    """A person's files (2026-10-22): what they sent in the chats I am in, newest first."""
    A, B, C = Users.make("xa"), Users.make("xb"), Users.make("xc")
    status, dm = jcall("POST", "/v1/chats", A[0], {"kind": "dm", "with": B[1]["id"]})
    status, other = jcall("POST", "/v1/chats", A[0], {"kind": "dm", "with": C[1]["id"]})
    wa = ws(A[0])
    wa.send({"type": "hello", "since": jcall("GET", "/v1/chats", A[0])[1]["seq"]})
    wa.until(lambda e: e["kind"] == "caught_up")
    sent = []
    for chat, name, kind in ((dm["id"], "Walk.anim", "anim"), (dm["id"], "Shot.ma", "scene"),
                             (other["id"], "Secret.ma", "scene")):
        data = os.urandom(50)
        status, start = jcall("POST", "/v1/files", A[0], {"chat": chat, "name": name, "kind": kind,
                                                          "bytes": 50, "zip": len(data)})
        call("PUT", "/v1/files/%s/parts/1" % start["id"], A[0], raw=data, ctype="application/octet-stream")
        jcall("POST", "/v1/files/%s/complete" % start["id"], A[0])
        wa.send({"type": "send", "chat": chat, "cid": "x" + name, "text": "t " + name, "file": start["id"]})
        ack, _ = wa.until(lambda e: e["kind"] in ("ack", "error"))
        sent.append((name, ack))
        time.sleep(0.05)
    wa.send({"type": "send", "chat": dm["id"], "cid": "plain", "text": "no file"})
    wa.until(lambda e: e["kind"] in ("ack", "error"))
    status, doc = jcall("GET", "/v1/users/%s/files" % A[1]["id"], B[0])
    names = [f["file"]["name"] for f in doc.get("files", [])]
    gate("B sees what A sent in their chat, newest first, and no more", status == 200
         and names == ["Shot.ma", "Walk.anim"], names)
    first = (doc.get("files") or [{}])[0]
    gate("each with its chat and message", first.get("chat") == dm["id"] and first.get("msg") == sent[1][1]["id"]
         and first.get("chat_kind") == "dm" and first.get("text") == "t Shot.ma", first)
    gate("and the person", doc.get("user", {}).get("id") == A[1]["id"], doc.get("user"))
    status, doc = jcall("GET", "/v1/users/%s/files" % B[1]["id"], A[0])
    names = [(f["file"]["name"], f.get("from_id")) for f in doc.get("files", [])]
    gate("B's card, read by A, holds what A sent B (not what A sent C)", status == 200
         and names == [("Shot.ma", A[1]["id"]), ("Walk.anim", A[1]["id"])], names)
    status, doc = jcall("GET", "/v1/users/%s/files" % A[1]["id"], A[0])
    gate("A sees all its own", [f["file"]["name"] for f in doc["files"]] == ["Secret.ma", "Shot.ma", "Walk.anim"],
         [f["file"]["name"] for f in doc["files"]])
    status, doc = jcall("GET", "/v1/users/%s/files?before=%d" % (A[1]["id"], doc["files"][1]["at"]), A[0])
    gate("before pages back", [f["file"]["name"] for f in doc["files"]] == ["Walk.anim"], doc)
    wa.send({"type": "delete", "chat": dm["id"], "id": sent[1][1]["id"]})
    wa.until(lambda e: e["kind"] == "deleted")
    status, doc = jcall("GET", "/v1/users/%s/files" % A[1]["id"], B[0])
    gate("a deleted message's file is gone from the list", [f["file"]["name"] for f in doc["files"]] == ["Walk.anim"],
         [f["file"]["name"] for f in doc["files"]])
    status, doc = jcall("GET", "/v1/users/%s/files" % ("0" * 16), B[0])
    gate("no such person", status == 404, doc)
    wa.close()


def _hello(w, token):
    """Say hello at the newest seq and wait for caught_up (as phase_react does)."""
    w.send({"type": "hello", "since": jcall("GET", "/v1/chats", token)[1]["seq"]})
    w.until(lambda e: e.get("kind") == "caught_up", 10)


def _call_ev(w, call_id=None, state=None, seconds=8, members=None):
    def test(e):
        if e.get("kind") != "call":
            return False
        c = e["call"]
        return ((call_id is None or c["id"] == call_id) and (state is None or c["state"] == state)
                and (members is None or len(c["members"]) == members))
    ev, _ = w.until(test, seconds)
    return ev["call"] if ev else None


def _error(w, seconds=5):
    ev, _ = w.until(lambda e: e.get("kind") == "error", seconds)
    return ev


def _make_group(token, member_ids):
    status, g = jcall("POST", "/v1/chats", token, {"kind": "group", "name": "zzt calls", "members": member_ids})
    if status != 200:
        raise RuntimeError("group answered %s %s" % (status, g))
    return g


def phase_turn():
    T = Users.make("tu")
    st, body = jcall("GET", "/v1/turn", T[0])
    servers = body.get("ice_servers", []) if isinstance(body, dict) else []
    urls = [u for s in servers for u in s.get("urls", [])]
    gate("turn answers ICE servers", st == 200 and any(u.startswith("stun:") for u in urls), str(body)[:200])
    if body.get("turn"):
        turns = [s for s in servers if any(u.startswith("turn") for u in s["urls"])]
        gate("a TURN server with credentials", bool(turns) and all(s.get("username") and s.get("credential") for s in turns))
        gate("no port 53", not any(":53?" in u or u.endswith(":53") for u in urls))
    else:
        print("  (no TURN key on this server: STUN only)", body.get("text", ""))
        gate("without a TURN key it says turn is false", body.get("turn") is False and not any(u.startswith("turn") for u in urls))
    st, _ = jcall("GET", "/v1/turn", None)
    gate("turn needs signing in", st == 401)


def phase_calls():
    A, B, C = Users.make("cla"), Users.make("clb"), Users.make("clc")
    st, dm = jcall("POST", "/v1/chats", A[0], {"kind": "dm", "with": B[1]["id"]})
    wa, wb, wc = ws(A[0]), ws(B[0]), ws(C[0])
    for w, t in ((wa, A[0]), (wb, B[0]), (wc, C[0])):
        _hello(w, t)

    # ring, a second call refused, a stranger refused
    wa.send({"type": "call_start", "chat": dm["id"], "kind": "video", "cid": "c1"})
    c = _call_ev(wb, state="ringing")
    gate("a call rings for the other person", c is not None and c["members"] == [A[1]["id"]]
         and c["by"] == A[1]["id"] and c["kind"] == "video" and c["cid"] == "c1", c)
    cid = c["id"] if c else ""
    wa.send({"type": "call_start", "chat": dm["id"], "kind": "audio", "cid": "c2"})
    err = _error(wa)
    gate("a second call in the chat is refused", bool(err) and err["code"] == "call_exists", err)
    wc.send({"type": "call_join", "call": cid})
    err = _error(wc)
    gate("a stranger cannot join", bool(err) and err["code"] == "not_member", str(err))

    # join -> live, signals between the two only
    wb.send({"type": "call_join", "call": cid})
    c = _call_ev(wa, cid, "live")
    gate("the call goes live with both", c is not None and sorted(c["members"]) ==
         sorted([A[1]["id"], B[1]["id"]]) and c["answered_at"], c)
    wb.send({"type": "call_signal", "call": cid, "to": A[1]["id"], "data": {"sdp": "offer-x"}})
    ev, _ = wa.until(lambda e: e.get("kind") == "call_signal", 5)
    gate("a signal reaches the other member", bool(ev) and ev["from"] == B[1]["id"]
         and ev["data"] == {"sdp": "offer-x"} and "seq" not in ev, ev)
    wb.send({"type": "call_signal", "call": cid, "to": C[1]["id"], "data": {"x": 1}})
    err = _error(wb)
    gate("a signal to someone outside the call is refused", bool(err) and err["code"] == "not_in_call", err)
    wb.send({"type": "call_signal", "call": cid, "to": A[1]["id"], "data": {"x": "y" * 70000}})
    err = _error(wb)
    gate("a signal over 64 KB is refused", bool(err) and err["code"] == "too_big", err)

    # leave -> ended, the call line
    wb.send({"type": "call_leave", "call": cid})
    c = _call_ev(wa, cid, "ended")
    gate("the last but one leaving ends the call", c is not None and c["ended_at"], c)
    ev, _ = wa.until(lambda e: e.get("kind") == "message" and (e["message"].get("call") or {}).get("id") == cid, 5)
    note = ev["message"]["call"] if ev else {}
    gate("the call line lands in the chat", bool(ev) and note.get("answered") is True
         and note.get("kind") == "video" and isinstance(note.get("seconds"), int) and note["seconds"] >= 0
         and ev["message"]["from_id"] == A[1]["id"], ev)
    secs = note.get("seconds", 0)
    words = u"\U0001F4DE Звонок · " + (u"%d с" % secs if secs < 60 else u"%d мин" % (secs // 60))
    gate("the call line's text is the note in words, for older clients",
         bool(ev) and ev["message"]["text"] == words, ev and ev["message"]["text"])

    # decline -> ended, not answered
    wa.send({"type": "call_start", "chat": dm["id"], "kind": "audio", "cid": "c3"})
    c = _call_ev(wb, state="ringing")
    wb.send({"type": "call_decline", "call": c["id"]})
    c2 = _call_ev(wa, c["id"], "ended")
    ev, _ = wa.until(lambda e: e.get("kind") == "message" and (e["message"].get("call") or {}).get("id") == c["id"], 5)
    gate("a declined call ends, not answered", c2 is not None and bool(ev)
         and ev["message"]["call"]["answered"] is False, ev)

    # nobody answers -> ended after 45 s
    wa.send({"type": "call_start", "chat": dm["id"], "kind": "audio", "cid": "c4"})
    c = _call_ev(wb, state="ringing")
    c2 = _call_ev(wa, c["id"], "ended", seconds=70)
    gate("a call nobody answers ends after 45 s", c2 is not None
         and 44000 <= c2["ended_at"] - c2["started_at"] <= 70000,
         str(c2 and c2["ended_at"] - c2["started_at"]))
    ev, _ = wa.until(lambda e: e.get("kind") == "message" and (e["message"].get("call") or {}).get("id") == c["id"], 5)
    gate("an unanswered call's line says not answered", bool(ev) and ev["message"]["call"]["answered"] is False, ev)

    # Maya restarted mid-call: back within 30 s it hears the call it is still in; a second join
    # answers the view again
    wa.send({"type": "call_start", "chat": dm["id"], "kind": "audio", "cid": "c5r"})
    c = _call_ev(wb, state="ringing")
    wb.send({"type": "call_join", "call": c["id"]})
    _call_ev(wa, c["id"], "live")
    _call_ev(wb, c["id"], "live")
    wb.send({"type": "call_join", "call": c["id"]})
    again = _call_ev(wb, c["id"], "live", seconds=5)
    gate("joining a call one is in answers its view again", again is not None
         and B[1]["id"] in again["members"], again)
    seq = jcall("GET", "/v1/chats", B[0])[1]["seq"]
    wb.close()
    time.sleep(2)
    wb = ws(B[0])
    wb.send({"type": "hello", "since": seq})
    back = _call_ev(wb, c["id"], "live", seconds=10)
    gate("back within 30 s, the call one is still in is heard again", back is not None
         and B[1]["id"] in back["members"], back)
    wb.until(lambda e: e.get("kind") == "caught_up", 10)
    wb.send({"type": "call_leave", "call": c["id"]})
    gate("and it can be left", _call_ev(wa, c["id"], "ended") is not None)

    # a member gone for 30 s leaves
    wa.send({"type": "call_start", "chat": dm["id"], "kind": "audio", "cid": "c5"})
    c = _call_ev(wb, state="ringing")
    wb.send({"type": "call_join", "call": c["id"]})
    _call_ev(wa, c["id"], "live")
    wb.close()
    t0 = time.time()
    c2 = _call_ev(wa, c["id"], "ended", seconds=70)
    gate("a member gone for 30 s leaves, and alone the call ends", c2 is not None
         and time.time() - t0 >= 25, "%.1f s" % (time.time() - t0))

    # the 5th person is refused
    more = [Users.make("cld"), Users.make("cle")]
    group = _make_group(A[0], [B[1]["id"], C[1]["id"]] + [m[1]["id"] for m in more])
    socks = [ws(t) for t, _u in [B, C] + more]
    for w, (t, _u) in zip(socks, [B, C] + more):
        _hello(w, t)
    wa.send({"type": "call_start", "chat": group["id"], "kind": "audio", "cid": "c6"})
    c = _call_ev(socks[0], state="ringing")
    for w in socks[:3]:
        w.send({"type": "call_join", "call": c["id"]})
    full = _call_ev(wa, c["id"], "live", seconds=8, members=4)
    gate("four people in a group call", full is not None, full)
    socks[3].send({"type": "call_join", "call": c["id"]})
    err = _error(socks[3])
    gate("a 5th person is refused", bool(err) and err["code"] == "call_full", err)
    # one at a time: leaves sent at once on four sockets may arrive in any order, and one that
    # comes after the call ended leaves a stale no_call error on its socket
    for w in socks[:3]:
        w.send({"type": "call_leave", "call": c["id"]})
        _call_ev(wa, c["id"], None, seconds=5)          # the last of them ends it

    # a member removed from the group mid-call leaves the call
    wa.send({"type": "call_start", "chat": group["id"], "kind": "audio", "cid": "c7"})
    c = _call_ev(socks[0], state="ringing")
    for w in socks[:3]:
        w.send({"type": "call_join", "call": c["id"]})
    _call_ev(wa, c["id"], "live", seconds=8, members=4)
    status, _ = jcall("DELETE", "/v1/chats/%s/members/%s" % (group["id"], C[1]["id"]), A[0])
    gate("the admin removes a member", status == 200, status)
    after = _call_ev(wa, c["id"], None, seconds=8)
    gate("a removed member leaves the running call", after is not None
         and C[1]["id"] not in after["members"] and len(after["members"]) == 3, after)
    socks[1].send({"type": "call_signal", "call": c["id"], "to": A[1]["id"], "data": {"x": 1}})
    err = _error(socks[1])
    gate("a removed member cannot signal", bool(err) and err["code"] == "not_in_call", err)

    # an account deleted mid-call leaves the call
    call("DELETE", "/v1/me", more[0][0])
    after = _call_ev(wa, c["id"], None, seconds=8)
    gate("a deleted account leaves the running call", after is not None
         and more[0][1]["id"] not in after["members"], after)
    for w in [wa, wc] + socks:
        try:
            w.close()
        except OSError as exc:
            print("  (close: %s)" % exc)


PHASES = {"signin": phase_signin, "profile": phase_profile, "friends": phase_friends,
          "chats": phase_chats, "live": phase_live, "presence": phase_presence,
          "people": phase_people, "react": phase_react, "newcomer": phase_newcomer,
          "files": phase_files, "previews": phase_previews,
          "person": phase_person, "calls": phase_calls, "turn": phase_turn}


def main(argv):
    if not SERVER:
        print("Set CHAT_SERVER to the staging URL first")
        return 2
    names = list(PHASES) if argv[1:] in ([], ["all"]) else argv[1:]
    try:
        for name in names:
            print("--- " + name)
            PHASES[name]()
    finally:
        Users.clean()
    failed = [n for n, ok in GATES if not ok]
    print("%d of %d gates failed" % (len(failed), len(GATES)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
