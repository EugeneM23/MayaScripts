"""What the chat server sends, parsed strictly. Stdlib only - no Maya, no Qt (a test pins it).

Shapes are the server's own (server/chat/worker.js): a user, a message, a chat, an event. Anything
malformed is refused here, so nothing downstream ever draws a half-read record.
"""
import re

NICK = re.compile(r"^[a-z0-9_]{3,24}$")
LINK = re.compile(r"https?://[^\s<>\"']+")
TRAILING = ".,;:!?)]}'\""

# Events that carry a global seq, and the ones that never do.
SEQ_KINDS = ("message", "edited", "deleted", "read", "chat", "member_added", "member_removed",
             "friend_request", "request_sent", "friend_added", "friend_removed",
             "request_cancelled", "user", "reaction")
LIVE_KINDS = ("typing", "presence", "ack", "error", "resync", "caught_up")


class Bad(ValueError):
    pass


def nick(text):
    """The nick folded to lower case, or None when it breaks the rule."""
    folded = str(text or "").strip().lstrip("@").lower()
    return folded if NICK.match(folded) else None


def _str(d, key, empty=True):
    value = d.get(key)
    if not isinstance(value, str) or (not empty and not value):
        raise Bad("%s is not text" % key)
    return value


def _int(d, key, default=None):
    value = d.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise Bad("%s is not a whole number" % key)
    return value


def _opt_str(d, key):
    value = d.get(key)
    if value is not None and not isinstance(value, str):
        raise Bad("%s is not text" % key)
    return value


def _dict(value):
    if not isinstance(value, dict):
        raise Bad("not a record")
    return value


def user(d):
    d = _dict(d)
    out = {"id": _str(d, "id", empty=False), "nick": _str(d, "nick", empty=False),
           "name": _str(d, "name"), "avatar_v": _int(d, "avatar_v", 0)}
    if "online" in d:
        out["online"] = bool(d["online"])
        out["last_seen"] = _int(d, "last_seen", 0)
    if "joined" in d:
        out["joined"] = _int(d, "joined", 0)
    if "relation" in d:
        out["relation"] = _opt_str(d, "relation")
    return out


def reactions(value):
    """{emoji: [user id, ...]} - anything not that shape is dropped, an empty list too."""
    out = {}
    if not isinstance(value, dict):
        return out
    for emoji, people in value.items():
        if not isinstance(emoji, str) or not emoji or not isinstance(people, list):
            continue
        ids = []
        for uid in people:
            if isinstance(uid, str) and uid and uid not in ids:
                ids.append(uid)
        if ids:
            out[emoji] = ids
    return out


FILE_KINDS = ("scene", "fbx", "pose", "anim")


def file(value):
    """A message's file {id, name, kind, bytes, zip, fps, range, expired}, or None for anything
    that is not one (the message keeps its text)."""
    if not isinstance(value, dict):
        return None
    try:
        out = {"id": _str(value, "id", empty=False), "name": _str(value, "name", empty=False),
               "kind": _str(value, "kind", empty=False), "bytes": _int(value, "bytes", 0),
               "zip": _int(value, "zip", 0), "expired": bool(value.get("expired"))}
    except Bad:
        return None
    if out["kind"] not in FILE_KINDS:
        return None
    fps = value.get("fps")
    out["fps"] = float(fps) if isinstance(fps, (int, float)) and not isinstance(fps, bool) else None
    rng = value.get("range")
    out["range"] = ([float(rng[0]), float(rng[1])] if isinstance(rng, list) and len(rng) == 2
                    and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in rng)
                    else None)
    return out


def message(d):
    d = _dict(d)
    edited = d.get("edited_at")
    if edited is not None:
        edited = _int(d, "edited_at")
    return {"id": _str(d, "id", empty=False), "chat": _str(d, "chat", empty=False),
            "seq": _int(d, "seq"), "from_id": _str(d, "from_id", empty=False),
            "cid": _opt_str(d, "cid"), "text": _str(d, "text"),
            "reply_to": _opt_str(d, "reply_to"), "at": _int(d, "at"),
            "edited_at": edited, "deleted": bool(d.get("deleted")),
            "reactions": reactions(d.get("reactions")), "file": file(d.get("file"))}


def chat(d):
    d = _dict(d)
    kind = _str(d, "kind")
    if kind not in ("dm", "group"):
        raise Bad("a chat is a dm or a group")
    members = d.get("members")
    if not isinstance(members, list):
        raise Bad("members is not a list")
    out = {"id": _str(d, "id", empty=False), "kind": kind, "name": _str(d, "name"),
           "admin": _opt_str(d, "admin"), "avatar_v": _int(d, "avatar_v", 0),
           "members": [user(m) for m in members]}
    if "last" in d:
        out["last"] = message(d["last"]) if d["last"] is not None else None
    if "unread" in d:
        out["unread"] = _int(d, "unread")
    if "read_upto" in d:
        out["read_upto"] = _int(d, "read_upto")
    return out


def event(d):
    """A server frame as a clean dict, or None for anything malformed or unknown."""
    try:
        d = _dict(d)
        kind = d.get("kind")
        out = {"kind": kind}
        if kind in SEQ_KINDS:
            out["seq"] = _int(d, "seq")
        elif kind not in LIVE_KINDS:
            return None
        if kind == "message":
            out["message"] = message(d.get("message"))
        elif kind == "edited":
            out.update(chat_id=_str(d, "chat_id", False), id=_str(d, "id", False),
                       text=_str(d, "text"), edited_at=_int(d, "edited_at"))
        elif kind == "deleted":
            out.update(chat_id=_str(d, "chat_id", False), id=_str(d, "id", False))
        elif kind == "read":
            out.update(chat_id=_str(d, "chat_id", False), user_id=_str(d, "user_id", False),
                       upto=_int(d, "upto"))
        elif kind == "chat":
            out["chat"] = chat(d.get("chat"))
        elif kind == "member_added":
            out.update(chat_id=_str(d, "chat_id", False), user=user(d.get("user")))
        elif kind == "member_removed":
            out.update(chat_id=_str(d, "chat_id", False), user_id=_str(d, "user_id", False),
                       admin=_opt_str(d, "admin"))
        elif kind in ("friend_request", "request_sent", "friend_added", "user"):
            out["user"] = user(d.get("user"))
        elif kind == "friend_removed":
            out["user_id"] = _str(d, "user_id", False)
        elif kind == "request_cancelled":
            out.update(from_id=_str(d, "from_id", False), to_id=_str(d, "to_id", False))
        elif kind == "reaction":
            out.update(chat_id=_str(d, "chat_id", False), id=_str(d, "id", False),
                       user_id=_str(d, "user_id", False), emoji=_str(d, "emoji", False),
                       on=bool(d.get("on", True)))
        elif kind == "typing":
            out.update(chat_id=_str(d, "chat_id", False), user_id=_str(d, "user_id", False))
        elif kind == "presence":
            out.update(user_id=_str(d, "user_id", False), online=bool(d.get("online")),
                       last_seen=_int(d, "last_seen", 0))
        elif kind == "ack":
            out.update(cid=_str(d, "cid", False), id=_str(d, "id", False), seq=_int(d, "seq"))
        elif kind == "error":
            out.update(cid=_opt_str(d, "cid"), code=_str(d, "code"), text=_str(d, "text"))
        elif kind == "caught_up":
            out["seq"] = _int(d, "seq")
        return out
    except Bad:
        return None


def toggled(reacts, emoji, user_id, on):
    """A copy of {emoji: [ids]} with user_id put on or taken off emoji (no-op when already so)."""
    out = dict((k, list(v)) for k, v in (reacts or {}).items())
    ids = out.get(emoji, [])
    if on and user_id not in ids:
        out[emoji] = ids + [user_id]
    elif not on and user_id in ids:
        ids = [u for u in ids if u != user_id]
        if ids:
            out[emoji] = ids
        else:
            out.pop(emoji, None)
    return out


def merge(old, new):
    """Messages by seq, one per id; a later copy of an id (an edit, a delete) wins."""
    by_id = {}
    for m in list(old) + list(new):
        by_id[m["id"]] = m
    return sorted(by_id.values(), key=lambda m: (m["seq"], m["id"]))


def unread(chat_record, messages, me):
    upto = chat_record.get("read_upto", 0)
    return sum(1 for m in messages
               if m["seq"] > upto and m["from_id"] != me and not m.get("deleted"))


def runs(text):
    """The text as [(kind, piece)]: "link" for http(s) addresses, "text" for the rest."""
    out, at = [], 0
    for found in LINK.finditer(text or ""):
        url = found.group(0).rstrip(TRAILING)
        start, end = found.start(), found.start() + len(url)
        if not url or url.endswith("//"):
            continue
        if start > at:
            out.append(("text", text[at:start]))
        out.append(("link", url))
        at = end
    if at < len(text or ""):
        out.append(("text", text[at:]))
    return out
