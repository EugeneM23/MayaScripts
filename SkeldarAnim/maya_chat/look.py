"""The chat window's rules a test can pin without Qt (plan docs/superpowers/plans/2026-10-20-chat-window.md).

Stdlib only. Times are milliseconds since the epoch (the server's `at`), read in local time.
"""
import time
import zlib

from . import records

DEFAULT_SIZE = (760, 520)
LEAST_SIZE = (520, 360)
ONE_COLUMN = 600          # logical px: narrower than this shows one column
LIST_W = 250              # the left column
UNSENT_MS = 10 * 60 * 1000
JOIN_MS = 5 * 60 * 1000   # one sender's messages this close are one run
TYPING_S = 5.0            # a typing mark lives this long
MAX_LINES = 6             # the composer grows to this many lines
MINE = "#5a3922"

MONTHS = ("января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа",
          "сентября", "октября", "ноября", "декабря")

#  muted colours for initials, picked by the user's id
COLOURS = ("#c0703a", "#4f8a8b", "#7a6bb0", "#5f8f4e", "#b05c74", "#4d78b0",
           "#a08a3c", "#6b7f8f")


def initials(user):
    """Up to two letters of a user's name, else of the nick."""
    user = user or {}
    words = [w for w in str(user.get("name") or "").replace("_", " ").split() if w]
    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()
    if words:
        return words[0][:2].upper()
    nick = str(user.get("nick") or "?")
    return nick[:2].upper()


def user_colour(user_id):
    return COLOURS[zlib.crc32(str(user_id or "").encode("utf-8")) % len(COLOURS)]


def display_name(user):
    user = user or {}
    return str(user.get("name") or "").strip() or "@" + str(user.get("nick") or "?")


def _local(ms):
    return time.localtime(float(ms) / 1000.0)


def _day(ms):
    t = _local(ms)
    return (t.tm_year, t.tm_yday)


def _yesterday(ms, now_ms):
    return _day(ms) == _day(now_ms - 86400000)


def clock(ms, now_ms):
    """A row's time: «14:32» today, «вчера», «12.10» this year, «12.10.25» before."""
    if not ms:
        return ""
    t = _local(ms)
    if _day(ms) == _day(now_ms):
        return "%02d:%02d" % (t.tm_hour, t.tm_min)
    if _yesterday(ms, now_ms):
        return "вчера"
    if t.tm_year == _local(now_ms).tm_year:
        return "%02d.%02d" % (t.tm_mday, t.tm_mon)
    return "%02d.%02d.%02d" % (t.tm_mday, t.tm_mon, t.tm_year % 100)


def hm(ms):
    t = _local(ms)
    return "%02d:%02d" % (t.tm_hour, t.tm_min)


def day_label(ms, now_ms):
    """A day separator: «Сегодня», «Вчера», «12 октября», «12 октября 2025»."""
    if _day(ms) == _day(now_ms):
        return "Сегодня"
    if _yesterday(ms, now_ms):
        return "Вчера"
    t = _local(ms)
    text = "%d %s" % (t.tm_mday, MONTHS[t.tm_mon - 1])
    if t.tm_year != _local(now_ms).tm_year:
        text += " %d" % t.tm_year
    return text


def last_seen(ms, now_ms):
    if not ms:
        return "не в сети"
    if _day(ms) == _day(now_ms):
        return "был(а) в " + hm(ms)
    if _yesterday(ms, now_ms):
        return "был(а) вчера в " + hm(ms)
    return "был(а) " + clock(ms, now_ms)


def status_title(status):
    return {"online": "в сети", "connecting": "подключение…",
            "offline": "offline — переподключение…"}.get(status, "")


def other(chat, me_id):
    """A dm's other member, or None."""
    if not chat or chat.get("kind") != "dm":
        return None
    for m in chat.get("members", []):
        if m.get("id") != me_id:
            return m
    return None


def chat_title(chat, me_id):
    if chat.get("kind") == "group":
        return chat.get("name") or "Группа"
    return display_name(other(chat, me_id))


def typers(typing, chat_id, me_id, now):
    """The ids typing in a chat within TYPING_S (monotonic `now`)."""
    marks = (typing or {}).get(chat_id, {})
    return [uid for uid, at in marks.items() if uid != me_id and now - at < TYPING_S]


def _member(chat, uid):
    for m in chat.get("members", []):
        if m.get("id") == uid:
            return m
    return {"id": uid}


def presence(chat, me_id, online, typing, now, now_ms):
    """The chat header's second line."""
    typing_ids = typers(typing, chat["id"], me_id, now)
    if chat.get("kind") == "dm":
        if typing_ids:
            return "печатает…"
        o = other(chat, me_id) or {}
        seen = (online or {}).get(o.get("id"), {})
        on = seen.get("online", o.get("online"))
        if on:
            return "в сети"
        return last_seen(seen.get("last_seen", o.get("last_seen", 0)), now_ms)
    if typing_ids:
        return display_name(_member(chat, typing_ids[0])) + " печатает…"
    members = chat.get("members", [])
    count = sum(1 for m in members
                if (online or {}).get(m.get("id"), {}).get("online", m.get("online")))
    return "%d участников, %d в сети" % (len(members), count)


CLIP = u"\U0001F4CE"


def message_text(message):
    """A message as one line of text: a file's message is «📎 name», its caption after a dash."""
    note = (message or {}).get("call")
    if note:
        from . import calls
        return calls.ICON + " " + calls.note_text(note)
    text = " ".join(str((message or {}).get("text") or "").split())
    f =(message or {}).get("file")
    if f and f.get("name"):
        return CLIP + " " + f["name"] + ((" - " + text) if text else "")
    return text


FILE_TAGS = {".ma": "MA", ".mb": "MB", ".fbx": "FBX", ".pose": "POSE", ".anim": "ANIM",
             ".png": "PNG", ".jpg": "JPG", ".jpeg": "JPG"}
KIND_WORDS = {"scene": u"сцена", "fbx": "fbx", "pose": u"поза", "anim": u"анимация",
              "image": u"картинка"}
PREVIEW_H = 132       # logical px: a file's preview over its card (2026-10-22)
PICTURE_H = 220       # ... a picture's


def preview_height(f, pending_thumb=False):
    """How tall the preview over a file's card stands (logical px): 0 with none. Pure."""
    f = f or {}
    if not (int(f.get("thumb_v") or 0) > 0 or pending_thumb):
        return 0
    return PICTURE_H if f.get("kind") == "image" else PREVIEW_H


def fitted(width, height, box_w, box_h):
    """(x, y, w, h): a `width` x `height` picture fitted inside a `box_w` x `box_h` box, centred,
    its aspect kept. Pure."""
    if width <= 0 or height <= 0 or box_w <= 0 or box_h <= 0:
        return (0.0, 0.0, 0.0, 0.0)
    k = min(float(box_w) / width, float(box_h) / height)
    w, h = width * k, height * k
    return ((box_w - w) / 2.0, (box_h - h) / 2.0, w, h)


def file_tag(f):
    """The card's tile: MA, MB or FBX."""
    import os
    return FILE_TAGS.get(os.path.splitext((f or {}).get("name") or "")[1].lower(), "FILE")


def file_line(f):
    """The card's second line: «12.3 MB · scene · 30 fps · 0-48»."""
    from . import files
    f = f or {}
    parts = [files.size_text(f.get("bytes") or 0), KIND_WORDS.get(f.get("kind"), "")]
    if f.get("fps"):
        parts.append(u"%g fps" % f["fps"])
    rng = f.get("range")
    if rng:
        parts.append(u"%g-%g" % (rng[0], rng[1]))
    return u" · ".join(parts)


def preview(chat, me_id, typing, now):
    """A list row's second line."""
    if typers(typing, chat["id"], me_id, now):
        return "печатает…"
    last = chat.get("last")
    if not last:
        return "нет сообщений"
    if last.get("deleted"):
        text = "сообщение удалено"
    else:
        text = message_text(last)
    if last.get("from_id") == me_id:
        return "Вы: " + text
    if chat.get("kind") == "group":
        return display_name(_member(chat, last.get("from_id"))) + ": " + text
    return text


def last_at(chat):
    last = chat.get("last") or {}
    return last.get("at") or 0


def ordered(chats):
    """Chats newest first (by their last message), ties by title-independent id."""
    return sorted(chats, key=lambda c: (-last_at(c), c.get("id", "")))


def matches(chat, query, me_id):
    query = (query or "").strip().lower().lstrip("@")
    if not query:
        return True
    words = [chat_title(chat, me_id)]
    for m in chat.get("members", []):
        if m.get("id") != me_id:
            words += [m.get("nick") or "", m.get("name") or ""]
    return any(query in w.lower() for w in words)


def count_text(n):
    return "99+" if n > 99 else str(int(n))


def nick_problem(text):
    """None for a good nick, else what is wrong."""
    if records.nick(text) is None:
        return "3–24 символа: a-z, 0-9, _"
    return None


def one_column(width, scale=1.0):
    return width < ONE_COLUMN * scale


class Item(object):
    """A line of the feed: a day separator or a message."""
    __slots__ = ("kind", "text", "message", "mine", "first", "last", "tick", "pending")

    def __init__(self, kind, text="", message=None, mine=False, first=True, last=True,
                 tick="", pending=False):
        self.kind, self.text, self.message = kind, text, message
        self.mine, self.first, self.last = mine, first, last
        self.tick, self.pending = tick, pending

    def key(self):
        if self.kind == "day":
            return "day:" + self.text
        m = self.message
        return m.get("cid") or m.get("id") if self.pending else m.get("id")


def read_by_others(chat, reads, me_id):
    """The highest seq every other member has read (for ✓✓ in a dm: the other's mark)."""
    marks = (reads or {}).get(chat["id"], {}) if chat else {}
    others = [m.get("id") for m in (chat or {}).get("members", []) if m.get("id") != me_id]
    if not others:
        return 0
    # a group's ✓✓ once anyone read it, as Telegram does
    return max([marks.get(uid, 0) for uid in others] or [0])


def tick_of(message, mine, pending, read_upto, now_ms):
    if not mine:
        return ""
    if pending:
        if message.get("state") == "failed" or now_ms - (message.get("at") or now_ms) > UNSENT_MS:
            return "failed"
        return "clock"
    return "read" if message.get("seq", 0) <= read_upto else "sent"


def feed(messages, pending, me_id, chat, reads, now_ms):
    """The chat's lines: day separators, messages (deleted ones left out), then the pending."""
    read_upto = read_by_others(chat, reads, me_id)
    rows = [(m, False) for m in messages or [] if not m.get("deleted")]
    rows += [(p, True) for p in pending or []]
    out = []
    prev = None
    for msg, is_pending in rows:
        at = msg.get("at") or now_ms
        if prev is None or _day(prev.get("at") or now_ms) != _day(at):
            out.append(Item("day", day_label(at, now_ms)))
            prev_msg_item = None
        else:
            prev_msg_item = out[-1] if out and out[-1].kind == "msg" else None
        sender = me_id if is_pending else msg.get("from_id")
        mine = sender == me_id
        first = True
        if prev_msg_item is not None:
            prev_sender = me_id if prev_msg_item.pending else prev_msg_item.message.get("from_id")
            if prev_sender == sender and at - (prev.get("at") or at) <= JOIN_MS:
                first = False
                prev_msg_item.last = False
        out.append(Item("msg", msg.get("text") or "", msg, mine, first, True,
                        tick_of(msg, mine, is_pending, read_upto, now_ms), is_pending))
        prev = msg
    return out


def last_mine(messages, me_id):
    """My newest message that is not deleted, for ↑ in an empty composer."""
    for m in reversed(messages or []):
        if m.get("from_id") == me_id and not m.get("deleted"):
            return m
    return None


def find(messages, message_id):
    for m in messages or []:
        if m.get("id") == message_id:
            return m
    return None


def total_unread(chats):
    return sum(int(c.get("unread") or 0) for c in chats)


def relation(user_id, friends):
    """friend | incoming | outgoing | None, read from the friend lists (fresher than the server's
    answer to /v1/people, which only the next read would update)."""
    for key in ("friends", "incoming", "outgoing"):
        if any(u.get("id") == user_id for u in (friends or {}).get(key, [])):
            return "friend" if key == "friends" else key
    return None


def people_rows(people, friends, online, query=""):
    """The People pane: everybody but me, filtered by name or nick, online first, then by name."""
    q = str(query or "").strip().lower().lstrip("@")
    rows = []
    for u in people or []:
        name = display_name(u)
        if q and q not in name.lower() and q not in str(u.get("nick") or "").lower():
            continue
        seen = (online or {}).get(u.get("id"), {})
        on = bool(seen.get("online", u.get("online")))
        rows.append(dict(u, online=on, last_seen=int(seen.get("last_seen", u.get("last_seen")) or 0),
                         relation=relation(u.get("id"), friends)))
    rows.sort(key=lambda r: (not r["online"], display_name(r).lower(), r.get("nick") or ""))
    return rows


def people_count(rows):
    on = sum(1 for r in rows if r["online"])
    return "%d в сети из %d" % (on, len(rows))


# ------------------------------------------------------------------ the message toasts
# A message heard while the chat window is shut shows as a small card at the viewport's
# bottom-left, just above the Time Bar (2026-10-20, «с левой части экрана над таймслайдером»).
TOAST_W = 300            # logical px
TOAST_H = 56
TOAST_GAP = 6
TOAST_MARGIN = 10
TOAST_MAX = 3            # the oldest goes when a fourth comes
TOAST_IN_MS = 280        # unrolls out of its left edge
TOAST_FLASH_MS = 520     # the accent ring's flash, a key set's
TOAST_STAY_MS = 6000     # held while the mouse is over it
TOAST_OUT_MS = 220
TOAST_MOVE_MS = 180      # a card moving up when a newer one comes under it


def toast_left(area, obstacles, margin):
    """The cards' left edge: past anything of ours standing on the viewport's left
    (the hub's rail) whose span reaches the area's bottom."""
    x, y, w, h = area
    left = x
    for ox, oy, ow, oh in obstacles or ():
        if ox <= x + margin and ox + ow > left and oy < y + h and oy + oh > y + h * 0.5:
            left = ox + ow
    return left + margin


def toast_rect(area, left, size, index, margin, gap):
    """Card `index` (0 the newest, at the bottom) in global px."""
    x, y, w, h = area
    tw, th = size
    bottom = y + h - margin
    return (int(left), int(bottom - (index + 1) * th - index * gap), int(tw), int(th))


def ease_out(u, power=5):
    u = max(0.0, min(1.0, u))
    return 1.0 - (1.0 - u) ** power


def toast_look(age_ms, leaving_ms=None):
    """(reveal 0..1 of the width, opacity, flash 0..1, slide px left) at an age."""
    reveal = ease_out(age_ms / float(TOAST_IN_MS))
    opacity = min(1.0, max(0.0, age_ms / (TOAST_IN_MS * 0.6)))
    flash = max(0.0, 1.0 - age_ms / float(TOAST_FLASH_MS)) ** 1.5 if age_ms >= 0 else 0.0
    slide = 0.0
    if leaving_ms is not None:
        u = max(0.0, min(1.0, leaving_ms / float(TOAST_OUT_MS)))
        opacity *= 1.0 - u
        slide = 14.0 * u * u
    return reveal, opacity, flash, slide


def toast_text(text, limit=90):
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[:limit - 1] + "…"


# ------------------------------------------------------------------ everybody in the list
# 2026-10-20, «добавлять в друзья не нужно мы просто сразу всех видим»: the left column holds
# every chat, then everybody I have no dm with yet; a click on a person opens the dm.

def dm_partners(chats, me_id):
    """The ids I already have a dm with."""
    out = set()
    for c in chats or []:
        o = other(c, me_id)
        if o is not None:
            out.add(o.get("id"))
    return out


def person_matches(user, query):
    q = str(query or "").strip().lower().lstrip("@")
    if not q:
        return True
    return q in display_name(user).lower() or q in str(user.get("nick") or "").lower()


def person_line(user, online, now_ms):
    """A person row's second line: «в сети» or when last seen, then the nick."""
    seen = (online or {}).get(user.get("id"), {})
    on = bool(seen.get("online", user.get("online")))
    state = "в сети" if on else last_seen(seen.get("last_seen", user.get("last_seen", 0)), now_ms)
    return "@%s · %s" % (user.get("nick") or "?", state), on


def directory(chats, people, me_id, online, query, now_ms):
    """(chat rows' chats, person rows) for the left column: chats newest first, then everybody
    without a dm - online first, then by name."""
    shown = [c for c in ordered(chats or []) if matches(c, query, me_id)]
    have = dm_partners(chats, me_id)
    persons = []
    for u in people or []:
        if u.get("id") == me_id or u.get("id") in have or not person_matches(u, query):
            continue
        line, on = person_line(u, online, now_ms)
        persons.append(dict(u, online=on, line=line))
    persons.sort(key=lambda r: (not r["online"], display_name(r).lower(), r.get("nick") or ""))
    return shown, persons


def everybody(people, me_id, query=""):
    """Everybody but me (New chat, a group's Add), filtered, by name."""
    rows = [u for u in people or [] if u.get("id") != me_id and person_matches(u, query)]
    rows.sort(key=lambda r: (display_name(r).lower(), r.get("nick") or ""))
    return rows


# ---------------------------------------------------------------------- a person's files (2026-10-22)

PROFILE_KINDS = (("all", u"Все"), ("pose", u"Позы"), ("anim", u"Анимации"), ("scene", u"Сцены"),
                 ("fbx", "FBX"), ("image", u"Картинки"))


def profile_counts(entries):
    """{kind: how many} of a person's files, "all" included. Pure."""
    out = dict((k, 0) for k, _label in PROFILE_KINDS)
    for e in entries or ():
        kind = ((e or {}).get("file") or {}).get("kind")
        out["all"] += 1
        if kind in out:
            out[kind] += 1
    return out


def profile_rows(entries, kind="all", query=""):
    """A person's files of `kind` ("all": every one) whose name, caption or chat holds `query`,
    newest first. Pure."""
    q = (query or "").strip().lower()
    out = []
    for e in entries or ():
        f = (e or {}).get("file") or {}
        if kind != "all" and f.get("kind") != kind:
            continue
        if q and q not in u" ".join([f.get("name") or "", e.get("text") or "",
                                     e.get("chat_name") or ""]).lower():
            continue
        out.append(e)
    out.sort(key=lambda e: -int(e.get("at") or 0))
    return out


def profile_line(e, chats=None, now_ms=None, me=None, owner=None):
    """A file row's second line: «анимация · 12.3 MB · 14 окт · в «Fights»»; on another's card
    (`owner` not `me`) a file I sent starts «от вас». Pure."""
    from . import files
    f = (e or {}).get("file") or {}
    parts = [KIND_WORDS.get(f.get("kind"), ""), files.size_text(f.get("bytes") or 0)]
    if me and owner != me and (e or {}).get("from_id") == me:
        parts.insert(0, u"от вас")
    at = e.get("at")
    if at:
        import time as _time
        parts.append(clock(int(at), now_ms if now_ms is not None else int(_time.time() * 1000)))
    if e.get("chat_kind") == "group" and e.get("chat_name"):
        parts.append(u"в «%s»" % e["chat_name"])
    if f.get("expired"):
        parts.append(u"истёк")
    return u" · ".join(p for p in parts if p)
