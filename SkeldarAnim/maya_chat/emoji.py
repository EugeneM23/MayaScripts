"""The chat's emoji: the shipped index (names, groups, tones), splitting text, search, the quick reactions and the recently used. Stdlib only.

Spec: docs/superpowers/specs/2026-10-20-chat-everyone-emoji-avatars-design.md
      docs/superpowers/specs/2026-10-22-chat-emoji-fluent-design.md
"""
import json
import os
import re

#  The six on a message's menu, and the first row of «Недавние» before anything was used.
QUICK = ("👍", "❤️", "😂", "😮", "😢", "🔥")
RECENT_MAX = 24
RECENT_VAR = "skeldarChatEmojiRecent"
FONT = "Segoe UI Emoji"          # Windows' colour emoji font, a fallback after the UI font


#  An emoji character: the pictographic planes and the old symbols, plus the joiners and
#  modifiers that build sequences (variation selector, ZWJ, skin tones, keycap).
_PICTO = re.compile(
    "[\U0001F000-\U0001FAFF☀-➿⬀-⯿←-⇿⌀-⏿"
    "〰〽㊗㊙‼⁉™ℹⓂ▪-◾⤴⤵"
    "️‍⃣\U0001F3FB-\U0001F3FF\U000E0020-\U000E007F]")
_JOIN = re.compile("[️‍⃣\U0001F3FB-\U0001F3FF\U000E0020-\U000E007F]")


VS16 = "️"
TONE_VAR = "skeldarChatEmojiTone"
_INDEXES = {}
_SPLIT = re.compile(r"[\s:_\-,.!?()\"'/]+")


def _default_path():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(here), "assets", "emoji", "emoji.json")


def _words(text):
    return [w for w in _SPLIT.split(str(text or "").casefold()) if w]


class Index(object):
    """The shipped emoji: records in emojibase order, every glyph (and toned glyph) found."""

    def __init__(self, data):
        self.groups = [tuple(g) for g in data.get("groups") or []]
        self.records = list(data.get("emoji") or [])
        self.by_glyph = {}
        self._words = {}
        for rec in self.records:
            self._add(rec["g"], rec, 0)
            for tone, (_sheet, _cell, glyph) in (rec.get("tones") or {}).items():
                self._add(glyph, rec, int(tone))
        self.longest = max([len(k) for k in self.by_glyph] or [1])
        self.starts = frozenset(k[0] for k in self.by_glyph)

    def _add(self, glyph, rec, tone):
        if glyph and glyph not in self.by_glyph:
            self.by_glyph[glyph] = (rec, tone)
        bare = glyph.replace(VS16, "")
        # a sequence often travels without its selectors; a single symbol without one is text
        if len(bare) > 1 and bare not in self.by_glyph:
            self.by_glyph[bare] = (rec, tone)

    def find(self, glyph):
        if not glyph:
            return None
        return self.by_glyph.get(glyph) or self.by_glyph.get(str(glyph).replace(VS16, ""))

    def cell(self, glyph):
        found = self.find(glyph)
        if not found:
            return None
        _g, sheet, cell = toned(*found)
        return sheet, cell

    def of_group(self, key):
        return [r for r in self.records if r.get("grp") == key]

    def words(self, rec):
        held = self._words.get(id(rec))
        if held is None:
            label = _words(rec.get("ru")) + _words(rec.get("en"))
            every_word = label + [w for k in rec.get("kw") or [] for w in _words(k)]
            held = self._words[id(rec)] = (label, every_word)
        return held


def index(path=None):
    """The index at `path` (the shipped one by default), read once; empty when unreadable."""
    path = path or _default_path()
    held = _INDEXES.get(path)
    if held is None:
        try:
            with open(path, encoding="utf-8") as f:
                held = Index(json.load(f))
        except (OSError, ValueError):
            held = Index({})
        _INDEXES[path] = held
    return held


def tokens(text, idx=None):
    """The text as [(kind, piece)]: "emoji" for the longest known emoji at each place (a
    selector right after it belongs to it), "text" for runs of the rest."""
    idx = idx or index()
    text = str(text or "")
    out, run, i, n = [], [], 0, len(text)
    starts = idx.starts
    while i < n:
        size = 0
        if text[i] not in starts:
            run.append(text[i])
            i += 1
            continue
        for k in range(min(idx.longest, n - i), 0, -1):
            if text[i:i + k] in idx.by_glyph:
                size = k
                break
        if not size:
            run.append(text[i])
            i += 1
            continue
        end = i + size
        if end < n and text[end] == VS16:
            end += 1
        if run:
            out.append(("text", "".join(run)))
            run = []
        out.append(("emoji", text[i:end]))
        i = end
    if run:
        out.append(("text", "".join(run)))
    return out


def search(query, limit=200, idx=None):
    """Records whose names or keywords (ru or en) have a word starting with every word of the
    query; name matches first, then the index's order."""
    idx = idx or index()
    want = _words(query)
    if not want:
        return []
    first, rest = [], []
    for rec in idx.records:
        label, every_word = idx.words(rec)
        if all(any(w.startswith(q) for w in every_word) for q in want):
            if all(any(w.startswith(q) for w in label) for q in want):
                first.append(rec)
            else:
                rest.append(rec)
    return (first + rest)[:limit]


def toned(rec, tone):
    """(glyph, sheet, cell) of `rec` in skin tone 1..5; the base for 0 or a missing tone."""
    t = (rec.get("tones") or {}).get(str(int(tone or 0)))
    if t:
        return t[2], t[0], t[1]
    return rec["g"], rec["sheet"], rec["cell"]


def every():
    """Every base emoji of the index, in order."""
    return [r["g"] for r in index().records]


def is_emoji(text):
    """Whether the text is a reaction the server takes: 1-16 UTF-16 units, no ASCII letter,
    digit or space, and emoji only (known ones, or pictographs)."""
    text = str(text or "")
    units = len(text.encode("utf-16-le")) // 2
    if not 0 < units <= 16 or any(ch.isascii() and (ch.isalnum() or ch.isspace()) for ch in text):
        return False
    parts = tokens(text)
    if parts and all(kind == "emoji" for kind, _p in parts):
        return True
    return all(_PICTO.match(ch) for ch in text)


def count(text):
    """How many emoji the text is (a sequence counts as one), or 0 when anything else is in
    it (spaces aside)."""
    text = "".join(str(text or "").split())
    if not text:
        return 0
    parts = tokens(text)
    if parts and all(kind == "emoji" for kind, _p in parts):
        return len(parts)
    if all(_PICTO.match(ch) for ch in text):
        return sum(1 for ch in text if not _JOIN.match(ch))
    return 0


def only_emoji(text, most=3):
    """1..most emoji alone: drawn big in the feed."""
    return 0 < count(text) <= most


def recent(raw):
    """The recently used, read from the optionVar's JSON; the quick ones when none."""
    try:
        items = json.loads(raw) if raw else []
    except (TypeError, ValueError):
        items = []
    items = [e for e in items if isinstance(e, str) and is_emoji(e)][:RECENT_MAX]
    return items or list(QUICK)


def used(raw, emoji):
    """The optionVar's JSON after `emoji` was used: it goes first, once."""
    items = [e for e in recent(raw) if e != emoji] if raw else []
    return json.dumps([emoji] + items[:RECENT_MAX - 1], ensure_ascii=False)


def pills(reactions, me_id):
    """A message's reactions as [(emoji, count, mine)], the order they came in."""
    out = []
    for e, ids in (reactions or {}).items():
        if ids:
            out.append((e, len(ids), me_id in ids))
    return out
