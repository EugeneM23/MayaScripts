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


def _newest(found):
    return max(found, key=lambda c: c["started_at"]) if found else None


def of_chat(calls, chat):
    """The chat's call that has not ended, newest first; None."""
    return _newest([c for c in (calls or {}).values()
                    if c["chat"] == chat and c["state"] != "ended"])


def mine(calls, me):
    """The call I am in; None."""
    return _newest([c for c in (calls or {}).values()
                    if c["state"] != "ended" and me in c["members"]])


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
    return u"%d с" % seconds if seconds < 60 else u"%d мин" % (seconds // 60)


def note_text(note):
    """A call line's words: «Звонок · 5 мин» or «Пропущенный звонок»."""
    if not note:
        return ""
    if note.get("answered"):
        return u"Звонок · " + duration_text(note.get("seconds"))
    return u"Пропущенный звонок"
