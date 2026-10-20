"""The chat's emoji: the picker's sets, the quick reactions, the recently used. Stdlib only.

Spec: docs/superpowers/specs/2026-10-20-chat-everyone-emoji-avatars-design.md
"""
import json
import re

#  The six on a message's menu, and the first row of «Недавние» before anything was used.
QUICK = ("👍", "❤️", "😂", "😮", "😢", "🔥")
RECENT_MAX = 24
RECENT_VAR = "skeldarChatEmojiRecent"
FONT = "Segoe UI Emoji"          # Windows' colour emoji font, a fallback after the UI font

#  (key, the tab's emoji, title, emoji)
CATEGORIES = (
    ("smileys", "😀", "Смайлы", (
        "😀", "😃", "😄", "😁", "😆", "😅", "🤣", "😂", "🙂", "🙃", "😉", "😊", "😇", "🥰",
        "😍", "🤩", "😘", "😋", "😛", "😜", "🤪", "😝", "🤑", "🤗", "🤭", "🤫", "🤔", "🤐",
        "🤨", "😐", "😑", "😶", "😏", "😒", "🙄", "😬", "😌", "😔", "😪", "😴", "😷", "🤒",
        "🤕", "🤢", "🤮", "🥵", "🥶", "😵", "🤯", "🤠", "🥳", "😎", "🤓", "🧐", "😕", "😟",
        "🙁", "😮", "😯", "😲", "😳", "🥺", "😦", "😧", "😨", "😰", "😥", "😢", "😭", "😱",
        "😖", "😣", "😞", "😓", "😩", "😫", "🥱", "😤", "😡", "😠", "🤬", "😈", "💀", "🤡",
        "👻", "👽", "🤖", "💩")),
    ("gestures", "👍", "Жесты", (
        "👍", "👎", "👌", "🤌", "✌️", "🤞", "🤟", "🤘", "🤙", "👈", "👉", "👆", "👇", "☝️",
        "✋", "🤚", "🖐️", "🖖", "👋", "👏", "🙌", "👐", "🤲", "🤝", "🙏", "✍️", "💪", "🦾",
        "👀", "👁️", "🧠", "🫡", "🤷", "🤦", "🙋", "🙅", "🙆", "💁", "🧍", "🏃", "🕺", "💃")),
    ("hearts", "❤️", "Сердца", (
        "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "🤎", "💔", "❣️", "💕", "💞", "💓",
        "💗", "💖", "💘", "💝", "💯", "💢", "💥", "💫", "💦", "💨", "🔥", "✨", "⭐", "🌟",
        "⚡", "💤", "💬", "💭", "❗", "❓", "‼️", "⁉️", "✅", "❌", "⭕", "🚫", "⚠️", "🆗")),
    ("animals", "🐱", "Природа", (
        "🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼", "🐨", "🐯", "🦁", "🐮", "🐷", "🐸",
        "🐵", "🙈", "🙉", "🙊", "🐔", "🐧", "🐦", "🦆", "🦅", "🦉", "🐺", "🐗", "🐴", "🦄",
        "🐝", "🐛", "🦋", "🐌", "🐞", "🕷️", "🐢", "🐍", "🦎", "🐙", "🦑", "🦀", "🐠", "🐬",
        "🐳", "🦈", "🐊", "🦍", "🐘", "🦒", "🌵", "🌲", "🌴", "🌱", "🍀", "🍁", "🍄", "🌸",
        "🌹", "🌻", "🌞", "🌝", "🌙", "🌈", "☁️", "❄️", "☃️", "🌊")),
    ("food", "🍕", "Еда", (
        "🍏", "🍎", "🍐", "🍊", "🍋", "🍌", "🍉", "🍇", "🍓", "🍒", "🍑", "🥭", "🍍", "🥥",
        "🥝", "🍅", "🥑", "🌶️", "🌽", "🥕", "🥔", "🥐", "🍞", "🧀", "🥚", "🍳", "🥓", "🍔",
        "🍟", "🍕", "🌭", "🥪", "🌮", "🌯", "🍜", "🍣", "🍩", "🍪", "🎂", "🍰", "🍫", "🍬",
        "🍿", "☕", "🍵", "🍺", "🍻", "🥂", "🍷", "🥃", "🍹", "🧃")),
    ("work", "🎬", "Работа", (
        "🎬", "🎥", "📹", "📷", "🎞️", "🖥️", "💻", "⌨️", "🖱️", "🎮", "🕹️", "🎨", "🖌️", "✏️",
        "📝", "📌", "📎", "✂️", "🗂️", "📁", "📊", "📈", "📉", "🗓️", "⏰", "⏳", "⌛", "🔔",
        "🔕", "🔒", "🔓", "🔑", "🔧", "🔨", "⚙️", "🛠️", "🧲", "🧪", "💡", "🔍", "📦", "🚀",
        "🛸", "🏁", "🏆", "🥇", "🎯", "🎲", "🧩", "🎉", "🎊", "🎁", "🎵", "🎧", "📣", "☎️")),
    ("travel", "🚗", "Разное", (
        "🚗", "🚕", "🚌", "🏎️", "🚓", "🚑", "🚒", "🚲", "🛴", "🏍️", "✈️", "🚁", "⛵", "🚢",
        "🗺️", "🏠", "🏢", "🏰", "⛺", "🌋", "🗿", "⚔️", "🗡️", "🛡️", "🏹", "🪓", "💣", "🧨",
        "💎", "💰", "💸", "🪙", "👑", "🎩", "👓", "🕶️", "🧢", "👟", "🥾", "🧤", "🧣", "👕")),
)

#  An emoji character: the pictographic planes and the old symbols, plus the joiners and
#  modifiers that build sequences (variation selector, ZWJ, skin tones, keycap).
_PICTO = re.compile(
    "[\U0001F000-\U0001FAFF☀-➿⬀-⯿←-⇿⌀-⏿"
    "〰〽㊗㊙‼⁉™ℹⓂ▪-◾⤴⤵"
    "️‍⃣\U0001F3FB-\U0001F3FF\U000E0020-\U000E007F]")
_JOIN = re.compile("[️‍⃣\U0001F3FB-\U0001F3FF\U000E0020-\U000E007F]")


def every():
    """Every emoji of the picker, in order, once."""
    seen, out = set(), []
    for _key, _tab, _title, items in CATEGORIES:
        for e in items:
            if e not in seen:
                seen.add(e)
                out.append(e)
    return out


def is_emoji(text):
    """Whether the text is a reaction the server takes: 1-16 UTF-16 units, emoji only."""
    text = str(text or "")
    units = len(text.encode("utf-16-le")) // 2
    return 0 < units <= 16 and all(_PICTO.match(ch) for ch in text)


def count(text):
    """How many emoji the text is, or 0 when anything else is in it (spaces aside)."""
    text = "".join(str(text or "").split())
    if not text or not all(_PICTO.match(ch) for ch in text):
        return 0
    return sum(1 for ch in text if not _JOIN.match(ch))


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
