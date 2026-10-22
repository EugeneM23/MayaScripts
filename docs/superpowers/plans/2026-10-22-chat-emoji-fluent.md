# Chat Emoji in Fluent 3D Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The chat shows the whole Unicode emoji set as Microsoft's Fluent 3D pictures (feed, reactions, previews, toasts, picker with Russian/English search and skin tones), and plays Google's Noto animation for an emoji sent alone and for reactions.

**Architecture:** A dev script builds picture sheets (96 px WebP, one per group) and an index `emoji.json` into `SkeldarAnim/assets/emoji/`. `maya_chat/emoji.py` (stdlib) reads the index: splitting text into words and emoji, search, tones. A new `maya_chat/emojiart.py` (Qt) cuts pictures from the sheets, builds rich text with `<img>` resources, draws one-line text with pictures, and downloads/decodes Noto animations on a thread. `maya_chat/window.py` uses it in the feed, pills, list previews, quotes, quick reactions and a rebuilt picker; `toast.py` in its cards.

**Tech Stack:** Maya 2027 mayapy (Python 3, PySide6 6.8.3, Qt's `qwebp` image plugin), stdlib `unittest`, offscreen Qt for tests.

Spec: `docs/superpowers/specs/2026-10-22-chat-emoji-fluent-design.md`.

## Global Constraints

- Sources pinned: `emojibase-data` **18.0.0** (`https://cdn.jsdelivr.net/npm/emojibase-data@18.0.0/...`), `microsoft/fluentui-emoji` commit **`1ffb34c752ecf5d402f04cfb4b392c77f57c54bc`**, Noto Animated Emoji catalog committed as `sources/emoji/noto_animated.json`, animations from `https://fonts.gstatic.com/s/e/notoemoji/latest/<cp>/512.webp`.
- Pictures 96 px cells, 64 columns a sheet, WebP quality 90; sheets `sheet_<group>.webp`; groups in this order: smileys, people, animals, food, travel, activities, objects, symbols. `component` and flags are left out.
- `maya_chat/emoji.py` stays stdlib only (no Qt, no Maya).
- Licences: Fluent and emojibase MIT, Noto CC BY 4.0 with credit, all in `SkeldarAnim/assets/emoji/LICENSE.txt`.
- An animation plays once the first time it is painted since the window opened, again when the mouse enters it; at rest it stands on its first frame. ⋮ → Interface animations off (`maya_hubmotion.enabled()` False): no animation, no hover lift.
- The composer (`QPlainTextEdit`) keeps Windows' glyphs. The server does not change.
- Animation cache: `<session.store.root>/emoji_anim/<cp>.webp`; decoded frames kept for the last 24 (cp, px) pairs.
- No `python`/`pytest` on this machine: tests run with `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest <module> -v` from the repo root, with `$env:QT_QPA_PLATFORM = 'offscreen'`. Avoid `2>&1` in PowerShell.
- Commit with `git commit -F <file>` (message in a file), stage only your own files (other sessions work in this repo), never push. End each message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## File Structure

| file | what it does |
|---|---|
| `docs/superpowers/plans/make_emoji_sheets.py` (create) | dev tool: downloads the pinned sources, writes the sheets, `emoji.json`, `LICENSE.txt`; `--check` compares with a fresh build |
| `sources/emoji/noto_animated.json` (create) | the Noto catalog as fetched, pinned |
| `SkeldarAnim/assets/emoji/` (create, generated) | `sheet_*.webp`, `emoji.json`, `LICENSE.txt` |
| `SkeldarAnim/maya_chat/emoji.py` (modify) | index, `tokens`, `search`, `toned`, `cell`, `count`/`only_emoji`/`is_emoji` on tokens; `CATEGORIES` removed in Task 6 |
| `SkeldarAnim/maya_chat/emojiart.py` (create) | Qt: `image`, `pixmap`, `url`, `rich`, `register`, `draw_line`, `Animated`, `decode`, `frame_at`, `animated()` |
| `SkeldarAnim/maya_chat/window.py` (modify) | feed docs with pictures, big lone emoji, pills, previews, quotes, quick reactions, new picker |
| `SkeldarAnim/maya_chat/toast.py` (modify) | the card's text line through `draw_line` |
| `tests/test_chat_emoji_assets.py`, `tests/test_chat_emoji.py`, `tests/test_chat_emojiart.py` (create) | tests |
| `tests/test_chat_extras.py`, `tests/test_chat_window.py` (modify) | tests that knew the old set |
| `docs/superpowers/plans/render_chat_emoji.py` (create) | filmstrip of the picker and a feed |
| `CLAUDE.md` (modify) | a section on what was built |

---

### Task 1: The build tool and the shipped sheets

**Files:**
- Create: `docs/superpowers/plans/make_emoji_sheets.py`
- Create: `sources/emoji/noto_animated.json`
- Create (generated): `SkeldarAnim/assets/emoji/sheet_*.webp`, `emoji.json`, `LICENSE.txt`
- Test: `tests/test_chat_emoji_assets.py`

**Interfaces:**
- Produces `emoji.json`: `{"version": 1, "sources": {...}, "groups": [[key, tab_glyph, ru_title], ...], "emoji": [record, ...]}`. A record: `{"g": glyph, "grp": group_key, "sheet": "sheet_<group>.webp", "cell": int, "ru": str, "en": str, "kw": [str, ...] lower case, "tones": {"1".."5": [sheet, cell, glyph]} (only where Fluent has the tone), "anim": noto codepoint string (e.g. "1f602", "1f636_200d_1f32b_fe0f") or ""}`. Note: `anim` is the Noto codepoint string rather than the spec's `true`, because the download URL needs it; empty means none.

- [ ] **Step 1: Write the failing test**

`tests/test_chat_emoji_assets.py`:

```python
"""The shipped emoji sheets and index (built by docs/superpowers/plans/make_emoji_sheets.py)."""
import json
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tests  # noqa: F401  (puts SkeldarAnim/ on sys.path)

FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "SkeldarAnim", "assets", "emoji")
GROUPS = ["smileys", "people", "animals", "food", "travel", "activities", "objects", "symbols"]
CELL, COLS = 96, 64


def _index():
    with open(os.path.join(FOLDER, "emoji.json"), encoding="utf-8") as f:
        return json.load(f)


class Shipped(unittest.TestCase):
    def test_the_groups_in_order_and_no_flags(self):
        data = _index()
        self.assertEqual([g[0] for g in data["groups"]], GROUPS)
        self.assertNotIn("\U0001F1F7\U0001F1FA", [r["g"] for r in data["emoji"]])

    def test_the_whole_set_is_there(self):
        data = _index()
        self.assertGreater(len(data["emoji"]), 1300)
        glyphs = set(r["g"] for r in data["emoji"])
        for g in ("\U0001F600", "\U0001F44D", "\U0001F525", "\u2764\ufe0f", "\U0001F431"):
            self.assertIn(g, glyphs)
        self.assertGreater(sum(len(r.get("tones") or {}) for r in data["emoji"]), 500)

    def test_russian_names_and_keywords(self):
        cat = next(r for r in _index()["emoji"] if r["g"] == "\U0001F431")
        self.assertIn("кот", (cat["ru"] + " " + " ".join(cat["kw"])).lower())
        self.assertIn("cat", (cat["en"] + " " + " ".join(cat["kw"])).lower())

    def test_every_cell_fits_its_sheet(self):
        from PySide6 import QtGui
        sizes = {}
        for g in GROUPS:
            img = QtGui.QImage(os.path.join(FOLDER, "sheet_%s.webp" % g))
            self.assertFalse(img.isNull(), g)
            self.assertEqual(img.width(), CELL * COLS)
            sizes["sheet_%s.webp" % g] = img.height()
        for r in _index()["emoji"]:
            cells = [(r["sheet"], r["cell"])] + [(t[0], t[1]) for t in (r.get("tones") or {}).values()]
            for sheet, cell in cells:
                self.assertLess((cell // COLS + 1) * CELL, sizes[sheet] + 1, r["g"])

    def test_animations_are_named_where_noto_has_them(self):
        anim = {r["g"]: r["anim"] for r in _index()["emoji"]}
        self.assertEqual(anim["\U0001F602"], "1f602")
        self.assertGreater(sum(1 for v in anim.values() if v), 700)

    def test_the_licence_credits_all_three(self):
        with open(os.path.join(FOLDER, "LICENSE.txt"), encoding="utf-8") as f:
            text = f.read()
        for name in ("Fluent Emoji", "emojibase", "Noto", "CC BY 4.0", "MIT"):
            self.assertIn(name, text)
```

- [ ] **Step 2: Run it to see it fail**

Run: `$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_chat_emoji_assets -v`
Expected: FAIL / ERROR with `FileNotFoundError ... emoji.json`.

- [ ] **Step 3: Pin the Noto catalog**

```powershell
New-Item -ItemType Directory -Force sources\emoji | Out-Null
& curl.exe -sL -A skeldar-build "https://googlefonts.github.io/noto-emoji-animation/data/api.json" -o sources\emoji\noto_animated.json
```

Check it parses and holds 881 icons:
`& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -I -c "import json; d=json.load(open('sources/emoji/noto_animated.json')); print(len(d['icons']))"` → `881` (a different count is fine if it is the catalog's current; write it down in the commit).

- [ ] **Step 4: Write the build tool**

`docs/superpowers/plans/make_emoji_sheets.py`:

```python
"""Build the chat's emoji sheets and index (spec 2026-10-22-chat-emoji-fluent-design.md).

    mayapy make_emoji_sheets.py            write SkeldarAnim/assets/emoji/
    mayapy make_emoji_sheets.py --check    build into a temp folder and compare

Downloads (cached under %TEMP%/skeldar_emoji_build): emojibase-data 18.0.0 (ru, en, en
shortcodes), the Fluent Emoji tree and every metadata.json and 3D png at a pinned commit.
The Noto catalog is read from sources/emoji/noto_animated.json. Refuses (writes nothing)
when an index record has no picture or a sheet would pass WebP's 16383 px.
"""
import concurrent.futures
import json
import os
import shutil
import sys
import tempfile
import urllib.parse
import urllib.request

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
OUT = os.path.join(REPO, "SkeldarAnim", "assets", "emoji")
NOTO = os.path.join(REPO, "sources", "emoji", "noto_animated.json")
CACHE = os.path.join(tempfile.gettempdir(), "skeldar_emoji_build")

EMOJIBASE = "https://cdn.jsdelivr.net/npm/emojibase-data@18.0.0/"
FLUENT_SHA = "1ffb34c752ecf5d402f04cfb4b392c77f57c54bc"
FLUENT_TREE = ("https://api.github.com/repos/microsoft/fluentui-emoji/git/trees/%s?recursive=1"
               % FLUENT_SHA)
FLUENT_RAW = "https://raw.githubusercontent.com/microsoft/fluentui-emoji/%s/" % FLUENT_SHA
UA = {"User-Agent": "skeldar-emoji-build"}

CELL, COLS, QUALITY, MAX_SIDE = 96, 64, 90, 16383
# emojibase group number -> (our key, the tab's glyph, the Russian title); 2 (component) and
# 9 (flags) are left out.
GROUPS = {0: ("smileys", "\U0001F600", "Смайлы"),
          1: ("people", "\U0001F44B", "Люди"),
          3: ("animals", "\U0001F431", "Природа"),
          4: ("food", "\U0001F355", "Еда"),
          5: ("travel", "\U0001F697", "Места"),
          6: ("activities", "\u26BD", "Занятия"),
          7: ("objects", "\U0001F4A1", "Предметы"),
          8: ("symbols", "\u2764\ufe0f", "Символы")}
TONES = ("Default", "Light", "Medium-Light", "Medium", "Medium-Dark", "Dark")

LICENSE = """Emoji in the SkeldarAnim chat

Pictures: Fluent Emoji by Microsoft, https://github.com/microsoft/fluentui-emoji
(commit {sha}), MIT License, Copyright (c) Microsoft Corporation.

Names, keywords and groups: emojibase-data 18.0.0, https://emojibase.dev, MIT License,
Copyright (c) 2017-2019 Miles Johnson.

Animations (downloaded when first used, not shipped): Noto Animated Emoji by Google,
https://googlefonts.github.io/noto-emoji-animation/, licensed CC BY 4.0
(https://creativecommons.org/licenses/by/4.0/).

MIT License: Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal in the
Software without restriction, including without limitation the rights to use, copy,
modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to the following
conditions: The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT
WARRANTY OF ANY KIND, EXPRESS OR IMPLIED.
"""


def get(url):
    """The bytes at `url`, cached on disk by the url."""
    name = urllib.parse.quote(url, safe="")[-180:]
    path = os.path.join(CACHE, name)
    if os.path.isfile(path):
        with open(path, "rb") as f:
            return f.read()
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    os.makedirs(CACHE, exist_ok=True)
    with open(path + ".part", "wb") as f:
        f.write(data)
    os.replace(path + ".part", path)
    return data


def norm(code):
    """A codepoint sequence, any spelling ("1F44D-1F3FB", "1f44d 1f3fb", "1f636_200d_..."),
    as lower-case hex joined by '-' with the variation selector dropped."""
    parts = code.replace("_", " ").replace("-", " ").lower().split()
    return "-".join(p for p in parts if p != "fe0f")


def fluent_pictures():
    """{norm(code): png path in the repo} for every base and toned 3D picture."""
    tree = json.loads(get(FLUENT_TREE).decode("utf-8"))
    paths = [t["path"] for t in tree["tree"] if t["type"] == "blob"]
    pngs = {}
    for p in paths:
        parts = p.split("/")
        if p.endswith(".png") and len(parts) >= 4 and parts[-2] == "3D":
            folder, tone = parts[1], (parts[2] if len(parts) == 5 else None)
            pngs[(folder, tone)] = p
    folders = sorted(set(p.split("/")[1] for p in paths
                         if p.startswith("assets/") and p.endswith("/metadata.json")))

    def meta(folder):
        url = FLUENT_RAW + urllib.parse.quote("assets/%s/metadata.json" % folder)
        return folder, json.loads(get(url).decode("utf-8"))

    out = {}
    with concurrent.futures.ThreadPoolExecutor(16) as pool:
        for folder, m in pool.map(meta, folders):
            toned = m.get("unicodeSkintones")
            if toned:
                for tone, code in zip(TONES, toned):
                    path = pngs.get((folder, tone))
                    if path:
                        out[norm(code)] = path
            else:
                path = pngs.get((folder, None))
                if path and m.get("unicode"):
                    out[norm(m["unicode"])] = path
    return out


def records(pictures, noto):
    """The index records and, per group, the png paths in cell order."""
    ru = json.loads(get(EMOJIBASE + "ru/data.json").decode("utf-8"))
    en = {e["hexcode"]: e for e in json.loads(get(EMOJIBASE + "en/data.json").decode("utf-8"))}
    codes = json.loads(get(EMOJIBASE + "en/shortcodes/emojibase.json").decode("utf-8"))
    sheets = dict((key, []) for key, _g, _t in GROUPS.values())
    out = []

    def place(key, path):
        sheets[key].append(path)
        return "sheet_%s.webp" % key, len(sheets[key]) - 1

    for e in sorted(ru, key=lambda x: x.get("order", 10 ** 9)):
        group = GROUPS.get(e.get("group"))
        path = pictures.get(norm(e["hexcode"]))
        if group is None or path is None:
            continue
        key = group[0]
        sheet, cell = place(key, path)
        eng = en.get(e["hexcode"], {})
        short = codes.get(e["hexcode"]) or []
        short = [short] if isinstance(short, str) else list(short)
        kw = sorted(set(w.lower() for w in (e.get("tags") or []) + (eng.get("tags") or [])
                        + short))
        tones = {}
        for skin in e.get("skins") or []:
            tone = skin.get("tone")
            spath = pictures.get(norm(skin["hexcode"]))
            if isinstance(tone, int) and spath:
                s_sheet, s_cell = place(key, spath)
                tones[str(tone)] = [s_sheet, s_cell, skin["emoji"]]
        out.append({"g": e["emoji"], "grp": key, "sheet": sheet, "cell": cell,
                    "ru": e.get("label", ""), "en": eng.get("label", ""), "kw": kw,
                    "tones": tones, "anim": noto.get(norm(e["hexcode"]), "")})
    return out, sheets


def write_sheets(sheets, folder):
    from PySide6 import QtCore, QtGui
    app = QtGui.QGuiApplication.instance() or QtGui.QGuiApplication([])  # noqa: F841
    for key, paths in sheets.items():
        rows = max(1, (len(paths) + COLS - 1) // COLS)
        if rows * CELL > MAX_SIDE:
            raise SystemExit("sheet %s needs %d px, over %d" % (key, rows * CELL, MAX_SIDE))
        sheet = QtGui.QImage(COLS * CELL, rows * CELL, QtGui.QImage.Format_ARGB32)
        sheet.fill(QtCore.Qt.transparent)
        p = QtGui.QPainter(sheet)
        p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        def load(path):
            return get(FLUENT_RAW + urllib.parse.quote(path))
        with concurrent.futures.ThreadPoolExecutor(16) as pool:
            blobs = list(pool.map(load, paths))
        for i, data in enumerate(blobs):
            img = QtGui.QImage.fromData(data)
            if img.isNull():
                raise SystemExit("unreadable picture %s" % paths[i])
            img = img.scaled(CELL, CELL, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            x = (i % COLS) * CELL + (CELL - img.width()) // 2
            y = (i // COLS) * CELL + (CELL - img.height()) // 2
            p.drawImage(x, y, img)
        p.end()
        if not sheet.save(os.path.join(folder, "sheet_%s.webp" % key), "WEBP", QUALITY):
            raise SystemExit("could not write sheet %s" % key)


def build(folder):
    with open(NOTO, encoding="utf-8") as f:
        noto = dict((norm(i["codepoint"]), i["codepoint"]) for i in json.load(f)["icons"])
    pictures = fluent_pictures()
    recs, sheets = records(pictures, noto)
    os.makedirs(folder, exist_ok=True)
    write_sheets(sheets, folder)
    data = {"version": 1,
            "sources": {"emojibase": "18.0.0", "fluent": FLUENT_SHA, "noto": "noto_animated.json"},
            "groups": [list(g) for _n, g in sorted(GROUPS.items())],
            "emoji": recs}
    with open(os.path.join(folder, "emoji.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(folder, "LICENSE.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(LICENSE.format(sha=FLUENT_SHA))
    return data


def check():
    """A fresh build equals the shipped one: the same index, sheets of the same size whose
    pixels differ by less than 1 on average."""
    from PySide6 import QtGui
    tmp = tempfile.mkdtemp(prefix="skeldar_emoji_check_")
    try:
        build(tmp)
        with open(os.path.join(tmp, "emoji.json"), encoding="utf-8") as f:
            fresh = json.load(f)
        with open(os.path.join(OUT, "emoji.json"), encoding="utf-8") as f:
            shipped = json.load(f)
        bad = [] if fresh == shipped else ["emoji.json differs"]
        for key, _g, _t in GROUPS.values():
            name = "sheet_%s.webp" % key
            a, b = QtGui.QImage(os.path.join(tmp, name)), QtGui.QImage(os.path.join(OUT, name))
            if a.size() != b.size():
                bad.append("%s size %s against %s" % (name, a.size(), b.size()))
                continue
            a = a.convertToFormat(QtGui.QImage.Format_RGBA8888)
            b = b.convertToFormat(QtGui.QImage.Format_RGBA8888)
            da, db = bytes(a.constBits()), bytes(b.constBits())
            step = max(1, len(da) // 200000)
            diff = sum(abs(da[i] - db[i]) for i in range(0, len(da), step)) / float(len(da) // step)
            if diff >= 1.0:
                bad.append("%s pixels differ %.2f" % (name, diff))
        print("\n".join(bad) if bad else "the shipped emoji equal a fresh build")
        return not bad
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(0 if check() else 1)
    data = build(OUT)
    print("%d emoji, %d with tones" % (len(data["emoji"]),
                                       sum(len(r["tones"]) for r in data["emoji"])))
```

- [ ] **Step 5: Run the build**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -I docs\superpowers\plans\make_emoji_sheets.py` (several minutes the first time: ~5,000 downloads, cached afterwards).
Expected: a line like `1500 emoji, 1800 with tones`; `SkeldarAnim\assets\emoji\` holds 8 sheets, `emoji.json`, `LICENSE.txt`; the folder about 10 MB (`(Get-ChildItem SkeldarAnim\assets\emoji | Measure-Object Length -Sum).Sum`). If the GitHub tree call answers 403 (rate limit), wait and rerun; everything fetched is cached.

- [ ] **Step 6: Run the tests, and the check**

Run: `$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_chat_emoji_assets -v` → all PASS.
Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -I docs\superpowers\plans\make_emoji_sheets.py --check` → `the shipped emoji equal a fresh build`.

- [ ] **Step 7: Commit**

```powershell
git add docs/superpowers/plans/make_emoji_sheets.py sources/emoji/noto_animated.json SkeldarAnim/assets/emoji tests/test_chat_emoji_assets.py
git commit -F msg.txt
```
Message: `feat(chat emoji): the Fluent 3D sheets and the index, built from pinned sources` + attribution line. Delete `msg.txt` after.

---

### Task 2: The index in `emoji.py`: tokens, search, tones

**Files:**
- Modify: `SkeldarAnim/maya_chat/emoji.py`
- Test: `tests/test_chat_emoji.py` (create)

**Interfaces:**
- Consumes: `SkeldarAnim/assets/emoji/emoji.json` (Task 1).
- Produces:
  - `emoji.VS16 = "\ufe0f"`, `emoji.TONE_VAR = "skeldarChatEmojiTone"`.
  - `class Index(data)`: `.groups` list of `(key, tab_glyph, ru_title)`, `.records` list of dicts, `.by_glyph` {glyph: (record, tone int)}, `.find(glyph) -> (record, tone) | None`, `.cell(glyph) -> (sheet, cell) | None`, `.of_group(key) -> [record]`, `.words(record) -> (label_words, all_words)`.
  - `index(path=None) -> Index` (cached by path; an empty `Index` when the file cannot be read).
  - `tokens(text, idx=None) -> [(kind, piece)]` with kind `"text"` or `"emoji"`.
  - `search(query, limit=200, idx=None) -> [record]`.
  - `toned(record, tone) -> (glyph, sheet, cell)`.
  - `count(text)`, `only_emoji(text, most=3)`, `is_emoji(text)` now read `tokens`.
  - `every()` returns every base glyph of the index (keycaps included); `CATEGORIES` stays until Task 6.

- [ ] **Step 1: Write the failing tests**

`tests/test_chat_emoji.py`:

```python
"""maya_chat.emoji on the shipped index."""
import unittest

import tests  # noqa: F401  (puts SkeldarAnim/ on sys.path)

from maya_chat import emoji

THUMB, TONE3 = "\U0001F44D", "\U0001F44D\U0001F3FD"
ASTRO = "\U0001F469\u200D\U0001F680"          # woman astronaut (ZWJ)
HEART = "\u2764\ufe0f"


class Index(unittest.TestCase):
    def test_loaded_with_its_groups(self):
        idx = emoji.index()
        self.assertEqual(idx.groups[0][0], "smileys")
        self.assertEqual(len(idx.groups), 8)
        self.assertTrue(idx.of_group("animals"))

    def test_a_toned_glyph_finds_its_record_and_tone(self):
        rec, tone = emoji.index().find(TONE3)
        self.assertEqual(rec["g"], THUMB)
        self.assertEqual(tone, 3)

    def test_a_missing_file_is_an_empty_index(self):
        idx = emoji.index("C:/nowhere/emoji.json")
        self.assertEqual(idx.records, [])
        self.assertEqual(emoji.tokens("hi 🔥", idx), [("text", "hi 🔥")])


class Tokens(unittest.TestCase):
    def test_text_and_emoji(self):
        self.assertEqual(emoji.tokens("огонь 🔥🔥!"),
                         [("text", "огонь "), ("emoji", "🔥"), ("emoji", "🔥"), ("text", "!")])

    def test_sequences_stay_whole(self):
        self.assertEqual(emoji.tokens(ASTRO + TONE3), [("emoji", ASTRO), ("emoji", TONE3)])

    def test_a_heart_with_or_without_its_selector(self):
        self.assertEqual(emoji.tokens(HEART), [("emoji", HEART)])

    def test_a_plain_digit_or_copyright_stays_text(self):
        self.assertEqual(emoji.tokens("1 ©"), [("text", "1 ©")])

    def test_empty(self):
        self.assertEqual(emoji.tokens(""), [])


class Search(unittest.TestCase):
    def test_russian(self):
        found = [r["g"] for r in emoji.search("кот")]
        self.assertIn("\U0001F431", found)

    def test_english_and_prefix(self):
        self.assertIn("🔥", [r["g"] for r in emoji.search("fir")])

    def test_every_word_must_match(self):
        self.assertEqual(emoji.search("кот zzzz"), [])

    def test_empty_query_finds_nothing(self):
        self.assertEqual(emoji.search("   "), [])

    def test_limit(self):
        self.assertLessEqual(len(emoji.search("a", limit=5)), 5)


class Tones(unittest.TestCase):
    def test_toned_and_base(self):
        rec, _t = emoji.index().find(THUMB)
        self.assertEqual(emoji.toned(rec, 3)[0], TONE3)
        self.assertEqual(emoji.toned(rec, 0)[0], THUMB)

    def test_no_tones_gives_the_base(self):
        rec, _t = emoji.index().find("🔥")
        self.assertEqual(emoji.toned(rec, 4)[0], "🔥")


class Count(unittest.TestCase):
    def test_sequences_count_as_one(self):
        self.assertEqual(emoji.count(ASTRO + " " + TONE3), 2)
        self.assertTrue(emoji.only_emoji(ASTRO))

    def test_text_is_none(self):
        self.assertEqual(emoji.count("ok 🔥"), 0)

    def test_is_emoji_mirrors_the_server(self):
        self.assertTrue(emoji.is_emoji(ASTRO))
        self.assertTrue(emoji.is_emoji(TONE3))
        self.assertFalse(emoji.is_emoji("1\ufe0f\u20e3"))      # a keycap: the server refuses digits
        self.assertFalse(emoji.is_emoji("🔥a"))
```

- [ ] **Step 2: Run them to see them fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_chat_emoji -v`
Expected: ERROR `module 'maya_chat.emoji' has no attribute 'index'`.

- [ ] **Step 3: Implement**

In `SkeldarAnim/maya_chat/emoji.py` add `import os`, keep everything already there, and add after `_JOIN`:

```python
VS16 = "\ufe0f"
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

    def _add(self, glyph, rec, tone):
        if glyph and glyph not in self.by_glyph:
            self.by_glyph[glyph] = (rec, tone)
        bare = glyph.replace(VS16, "")
        # a sequence often travels without its selectors; a single symbol without one is text
        if len(bare) > 1 and bare not in self.by_glyph:
            self.by_glyph[bare] = (rec, tone)

    def find(self, glyph):
        return self.by_glyph.get(glyph) or self.by_glyph.get(str(glyph or "").replace(VS16, "")) \
            if glyph else None

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
            every = label + [w for k in rec.get("kw") or [] for w in _words(k)]
            held = self._words[id(rec)] = (label, every)
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
    while i < n:
        size = 0
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
```

Replace `every`, `is_emoji` and `count` with:

```python
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
```

Update the module docstring's first line to: `"""The chat's emoji: the shipped index (names, groups, tones), splitting text, search, the quick reactions and the recently used. Stdlib only.` and add the spec line `docs/superpowers/specs/2026-10-22-chat-emoji-fluent-design.md`.

- [ ] **Step 4: Run the new and the old emoji tests**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_chat_emoji tests.test_chat_extras -v`
Expected: `test_chat_emoji` PASS. In `test_chat_extras`, `test_every_emoji_is_a_reaction_the_server_takes` now sees keycaps: change its loop to skip them:

```python
    def test_every_emoji_is_a_reaction_the_server_takes(self):
        for e in emoji.every():
            if "\u20e3" in e:            # keycaps carry an ASCII digit: the server refuses them
                continue
            self.assertTrue(emoji.is_emoji(e), e)
        for e in emoji.QUICK:
            self.assertTrue(emoji.is_emoji(e), e)
```
Rerun → all PASS.

- [ ] **Step 5: Commit**

`git add SkeldarAnim/maya_chat/emoji.py tests/test_chat_emoji.py tests/test_chat_extras.py`; message `feat(chat emoji): the index - text split into emoji, search in Russian and English, skin tones`.

---

### Task 3: `emojiart.py`: pictures, rich text, one line with pictures

**Files:**
- Create: `SkeldarAnim/maya_chat/emojiart.py`
- Test: `tests/test_chat_emojiart.py`

**Interfaces:**
- Consumes: `emoji.index()`, `emoji.tokens()`, `emoji.toned()`, `records.runs()`.
- Produces:
  - `CELL = 96`, `COLS = 64`.
  - `image(glyph) -> QImage | None` (96 px).
  - `pixmap(glyph, px) -> QPixmap | None`.
  - `url(glyph) -> str` (`"emoji:1f44d-1f3fd"`).
  - `rich(text, px) -> str` (HTML: escaped text, `<a href>` links, `<img src=url width=px height=px>` for known emoji, `<br>` for new lines).
  - `register(doc, text, px)` adds every needed image to a `QTextDocument`.
  - `draw_line(painter, rect, text, font, color) -> float` (width used; elided with "…"); `line_width(text, font) -> float`.

- [ ] **Step 1: Write the failing tests**

`tests/test_chat_emojiart.py`:

```python
"""maya_chat.emojiart offscreen."""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tests  # noqa: F401  (puts SkeldarAnim/ on sys.path)

from PySide6 import QtCore, QtGui, QtWidgets

from maya_chat import emoji
from maya_chat import emojiart as A


def _app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _ink(img):
    img = img.convertToFormat(QtGui.QImage.Format_ARGB32)
    return sum(1 for y in range(0, img.height(), 3) for x in range(0, img.width(), 3)
               if img.pixelColor(x, y).alpha() > 40)


class Pictures(unittest.TestCase):
    def setUp(self):
        _app()

    def test_every_record_has_ink(self):
        for rec in emoji.index().records[::25]:
            img = A.image(rec["g"])
            self.assertIsNotNone(img, rec["g"])
            self.assertGreater(_ink(img), 30, rec["g"])

    def test_a_tone_is_another_picture(self):
        base, toned = A.image("\U0001F44D"), A.image("\U0001F44D\U0001F3FF")
        self.assertNotEqual(base.constBits().tobytes(), toned.constBits().tobytes())

    def test_unknown_is_none(self):
        self.assertIsNone(A.image("x"))
        self.assertIsNone(A.pixmap("x", 20))

    def test_pixmap_size_and_cache(self):
        pm = A.pixmap("🔥", 24)
        self.assertEqual((pm.width(), pm.height()), (24, 24))
        self.assertIs(A.pixmap("🔥", 24), pm)


class Rich(unittest.TestCase):
    def setUp(self):
        _app()

    def test_images_links_and_escapes(self):
        out = A.rich("a<b> 🔥 https://x.io/y\nz", 20)
        self.assertIn("a&lt;b&gt; ", out)
        self.assertIn('<img src="emoji:1f525" width="20" height="20"', out)
        self.assertIn('<a href="https://x.io/y">', out)
        self.assertIn("<br>z", out)

    def test_a_document_draws_the_picture(self):
        doc = QtGui.QTextDocument()
        A.register(doc, "🔥", 32)
        doc.setHtml(A.rich("🔥", 32))
        self.assertFalse(doc.resource(QtGui.QTextDocument.ImageResource,
                                      QtCore.QUrl("emoji:1f525")) is None)
        img = QtGui.QImage(64, 64, QtGui.QImage.Format_ARGB32)
        img.fill(QtCore.Qt.transparent)
        p = QtGui.QPainter(img)
        doc.drawContents(p)
        p.end()
        self.assertGreater(_ink(img), 20)


class Line(unittest.TestCase):
    def setUp(self):
        _app()
        self.font = QtGui.QFont()
        self.font.setPixelSize(14)

    def _draw(self, text, width):
        img = QtGui.QImage(width, 24, QtGui.QImage.Format_ARGB32)
        img.fill(QtCore.Qt.transparent)
        p = QtGui.QPainter(img)
        used = A.draw_line(p, QtCore.QRectF(0, 0, width, 24), text, self.font, QtGui.QColor("white"))
        p.end()
        return used, img

    def test_fits_and_draws(self):
        used, img = self._draw("ok 🔥", 200)
        self.assertAlmostEqual(used, A.line_width("ok 🔥", self.font), delta=1)
        self.assertGreater(_ink(img), 5)

    def test_elides_to_the_rect(self):
        used, _img = self._draw("long " * 40 + "🔥", 80)
        self.assertLessEqual(used, 80)
```

- [ ] **Step 2: Run them to see them fail**

Run: `$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_chat_emojiart -v`
Expected: ERROR `No module named 'maya_chat.emojiart'`.

- [ ] **Step 3: Implement**

`SkeldarAnim/maya_chat/emojiart.py`:

```python
"""The chat's emoji pictures (spec docs/superpowers/specs/2026-10-22-chat-emoji-fluent-design.md):
cells cut from the shipped Fluent 3D sheets, text with pictures for a QTextDocument, one line
of text and pictures drawn with a painter, and Noto's animations downloaded on first use.
"""
import html
import os

from . import emoji

CELL = 96
COLS = 64
ELLIPSIS = u"\u2026"

_SHEETS = {}
_PIX = {}
_PIX_MAX = 3000


def _qt():
    import maya_hubqt
    return maya_hubqt.qt()


def folder():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(here), "assets", "emoji")


def _sheet(name):
    img = _SHEETS.get(name)
    if img is None:
        img = _SHEETS[name] = _qt().QtGui.QImage(os.path.join(folder(), name))
    return img


def image(glyph):
    """The glyph's 96 px picture, or None when it is not a known emoji."""
    found = emoji.index().cell(glyph) if glyph else None
    if not found:
        return None
    sheet = _sheet(found[0])
    if sheet.isNull():
        return None
    cell = found[1]
    return sheet.copy((cell % COLS) * CELL, (cell // COLS) * CELL, CELL, CELL)


def pixmap(glyph, px):
    """The picture at `px` physical pixels, smooth, cached."""
    key = (glyph, int(px))
    held = _PIX.get(key)
    if held is None:
        img = image(glyph)
        if img is None:
            return None
        q = _qt()
        if len(_PIX) > _PIX_MAX:
            _PIX.clear()
        held = _PIX[key] = q.QtGui.QPixmap.fromImage(img.scaled(
            int(px), int(px), q.QtCore.Qt.KeepAspectRatio, q.QtCore.Qt.SmoothTransformation))
    return held


def url(glyph):
    return "emoji:" + "-".join("%x" % ord(ch) for ch in glyph if ch != emoji.VS16)


def _known(part):
    return emoji.index().cell(part) is not None


def rich(text, px):
    """The message's text as HTML: escaped, links as anchors, known emoji as images `px`
    square, new lines kept."""
    from . import records
    out = []
    for kind, piece in records.runs(text or ""):
        if kind == "link":
            out.append('<a href="{0}">{1}</a>'.format(html.escape(piece, quote=True),
                                                      html.escape(piece)))
            continue
        for part_kind, part in emoji.tokens(piece):
            if part_kind == "emoji" and _known(part):
                out.append('<img src="{0}" width="{1}" height="{1}" '
                           'style="vertical-align: middle">'.format(url(part), int(px)))
            else:
                out.append(html.escape(part))
    return "".join(out).replace("\n", "<br>")


def register(doc, text, px):
    """Every known emoji of `text` added to `doc` as an image resource at `px`."""
    q = _qt()
    for kind, part in emoji.tokens(text or ""):
        if kind == "emoji":
            pm = pixmap(part, px)
            if pm is not None:
                doc.addResource(q.QtGui.QTextDocument.ImageResource, q.QtCore.QUrl(url(part)),
                                pm.toImage())


def _parts(text, font):
    q = _qt()
    fm = q.QtGui.QFontMetricsF(font)
    side = fm.height()
    out = []
    for kind, piece in emoji.tokens(" ".join(str(text or "").split())):
        if kind == "emoji" and _known(piece):
            out.append(("emoji", piece, side))
        else:
            out.append(("text", piece, fm.horizontalAdvance(piece)))
    return out, fm, side


def line_width(text, font):
    parts, _fm, _side = _parts(text, font)
    return sum(w for _k, _p, w in parts)


def draw_line(p, rect, text, font, color):
    """One line of text and emoji pictures (a picture as tall as the font's line) inside
    `rect`, vertically centred, elided with "…" at the right. The width used."""
    q = _qt()
    QtCore = q.QtCore
    parts, fm, side = _parts(text, font)
    width = rect.width()
    if sum(w for _k, _pc, w in parts) > width:
        ell = fm.horizontalAdvance(ELLIPSIS)
        kept, used = [], 0.0
        for kind, piece, w in parts:
            if used + w + ell <= width:
                kept.append((kind, piece, w))
                used += w
                continue
            if kind == "text":
                cut = fm.elidedText(piece, QtCore.Qt.ElideRight, max(0.0, width - used))
                kept.append(("text", cut, fm.horizontalAdvance(cut)))
            elif used + ell <= width:
                kept.append(("text", ELLIPSIS, ell))
            break
        parts = kept
    p.save()
    p.setFont(font)
    p.setPen(color)
    p.setRenderHint(q.QtGui.QPainter.SmoothPixmapTransform)
    x = rect.left()
    base = rect.top() + (rect.height() + fm.ascent() - fm.descent()) / 2.0
    for kind, piece, w in parts:
        if kind == "emoji":
            pm = pixmap(piece, max(1, int(round(side))))
            if pm is not None:
                p.drawPixmap(QtCore.QRectF(x, rect.center().y() - side / 2.0, side, side),
                             pm, QtCore.QRectF(pm.rect()))
        else:
            p.drawText(QtCore.QPointF(x, base), piece)
        x += w
    p.restore()
    return x - rect.left()
```

- [ ] **Step 4: Run them to see them pass**

Run: `$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_chat_emojiart -v` → PASS.

- [ ] **Step 5: Commit**

`git add SkeldarAnim/maya_chat/emojiart.py tests/test_chat_emojiart.py`; message `feat(chat emoji): emojiart - pictures from the sheets, text with pictures`.

---

### Task 4: Noto animations: download, decode, play

**Files:**
- Modify: `SkeldarAnim/maya_chat/emojiart.py`
- Test: `tests/test_chat_emojiart.py` (add)

**Interfaces:**
- Consumes: the `anim` codepoint of an index record.
- Produces:
  - `NOTO = "https://fonts.gstatic.com/s/e/notoemoji/latest/{}/512.webp"`.
  - `decode(path, px) -> [(QImage, end_ms)]`.
  - `frame_at(frames, ms) -> (QImage | None, done bool)`: before the end the frame playing; at or past it the first frame and `done` True.
  - `class Animated(folder, fetch=None, spawn=None, keep=24)`: `.frames(cp, px) -> list | None` (None until ready; starts a download/decode once), `.take_changed() -> bool`, `.failed` set.
  - `anim_of(glyph) -> str` (the record's `anim` or "").
  - `animated(session=None) -> Animated | None` (one per Maya on `sys._skeldar_chat_emoji_anim`, folder `<session.store.root>/emoji_anim`).

- [ ] **Step 1: Write the failing tests** (append to `tests/test_chat_emojiart.py`)

```python
import shutil
import tempfile


def _webp_bytes():
    """A one-frame WebP standing in for Noto's file."""
    img = QtGui.QImage(8, 8, QtGui.QImage.Format_ARGB32)
    img.fill(QtGui.QColor("red"))
    buf = QtCore.QBuffer()
    buf.open(QtCore.QIODevice.WriteOnly)
    img.save(buf, "WEBP", 90)
    return bytes(buf.data())


class Animation(unittest.TestCase):
    def setUp(self):
        _app()
        self.dir = tempfile.mkdtemp()
        self.fetched = []

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _anim(self, fail=False):
        def fetch(u):
            self.fetched.append(u)
            if fail:
                raise IOError("no")
            return _webp_bytes()
        return A.Animated(self.dir, fetch=fetch, spawn=lambda fn: fn())

    def test_downloads_once_then_has_frames(self):
        a = self._anim()
        frames = a.frames("1f525", 32)
        if frames is None:                      # spawn ran inline: the second ask has them
            frames = a.frames("1f525", 32)
        self.assertTrue(frames)
        self.assertEqual(self.fetched, [A.NOTO.format("1f525")])
        self.assertTrue(os.path.isfile(os.path.join(self.dir, "1f525.webp")))
        self.assertTrue(a.take_changed())
        self.assertFalse(a.take_changed())
        a.frames("1f525", 32)
        self.assertEqual(len(self.fetched), 1)

    def test_a_failure_is_not_asked_again(self):
        a = self._anim(fail=True)
        self.assertIsNone(a.frames("1f602", 32))
        self.assertIsNone(a.frames("1f602", 32))
        self.assertEqual(len(self.fetched), 1)
        self.assertIn("1f602", a.failed)

    def test_keeps_the_last_ones_only(self):
        a = self._anim()
        a.keep = 2
        for cp in ("a1", "a2", "a3"):
            a.frames(cp, 16)
        self.assertEqual(len(a._frames), 2)

    def test_frame_at_plays_once_and_rests_on_the_first(self):
        f0, f1 = QtGui.QImage(1, 1, QtGui.QImage.Format_ARGB32), QtGui.QImage(2, 2, QtGui.QImage.Format_ARGB32)
        frames = [(f0, 40), (f1, 80)]
        self.assertEqual(A.frame_at(frames, 10), (f0, False))
        self.assertEqual(A.frame_at(frames, 50), (f1, False))
        self.assertEqual(A.frame_at(frames, 80), (f0, True))
        self.assertEqual(A.frame_at([], 0), (None, True))

    def test_anim_of(self):
        self.assertEqual(A.anim_of("\U0001F602"), "1f602")
        self.assertEqual(A.anim_of("x"), "")
```

- [ ] **Step 2: Run them to see them fail**

Run: `$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_chat_emojiart.Animation -v`
Expected: ERROR `module ... has no attribute 'Animated'`.

- [ ] **Step 3: Implement** (append to `emojiart.py`; add `import collections`, `import sys`, `import threading`, `import urllib.request` at the top)

```python
NOTO = "https://fonts.gstatic.com/s/e/notoemoji/latest/{}/512.webp"
_ANIM_ATTR = "_skeldar_chat_emoji_anim"
FRAME_MS = 33


def anim_of(glyph):
    """Noto's codepoint for the glyph's animation, or ""."""
    found = emoji.index().find(glyph) if glyph else None
    return (found[0].get("anim") or "") if found else ""


def _fetch(address):
    req = urllib.request.Request(address, headers={"User-Agent": "skeldar-chat/1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def _spawn(fn):
    threading.Thread(target=fn, daemon=True).start()


def decode(path, px):
    """Every frame of an animated picture at `px` square, with the time each one ends."""
    q = _qt()
    reader = q.QtGui.QImageReader(path)
    reader.setScaledSize(q.QtCore.QSize(int(px), int(px)))
    out, t = [], 0
    while True:
        img = reader.read()
        if img.isNull():
            break
        delay = reader.nextImageDelay()
        t += delay if delay > 0 else FRAME_MS
        out.append((img, t))
    return out


def frame_at(frames, ms):
    """The frame to draw `ms` into a play: the one playing, or at the end the first one
    (it rests there) and True."""
    if not frames:
        return None, True
    if ms >= frames[-1][1]:
        return frames[0][0], True
    for img, end in frames:
        if ms < end:
            return img, False
    return frames[0][0], True


class Animated(object):
    """Noto's animations under `folder`, fetched once each on a thread and decoded there at
    the size drawn; the frames of the last `keep` kept in memory."""

    def __init__(self, folder, fetch=None, spawn=None, keep=24):
        self.folder = folder
        self.fetch = fetch or _fetch
        self.spawn = spawn or _spawn
        self.keep = keep
        self.lock = threading.Lock()
        self.failed = set()
        self.busy = set()
        self.changed = False
        self._frames = collections.OrderedDict()

    def path(self, cp):
        return os.path.join(self.folder, cp + ".webp")

    def frames(self, cp, px):
        key = (cp, int(px))
        with self.lock:
            held = self._frames.get(key)
            if held is not None:
                self._frames.move_to_end(key)
                return held
            if cp in self.failed or key in self.busy:
                return None
            self.busy.add(key)
        self.spawn(lambda: self._load(cp, key))
        with self.lock:
            return self._frames.get(key)

    def _load(self, cp, key):
        try:
            path = self.path(cp)
            if not os.path.isfile(path):
                data = self.fetch(NOTO.format(cp))
                os.makedirs(self.folder, exist_ok=True)
                with open(path + ".part", "wb") as f:
                    f.write(data)
                os.replace(path + ".part", path)
            frames = decode(path, key[1])
            if not frames:
                raise ValueError("no frames in " + path)
            with self.lock:
                self._frames[key] = frames
                while len(self._frames) > self.keep:
                    self._frames.popitem(last=False)
                self.changed = True
        except Exception:                                    # noqa: BLE001
            with self.lock:
                self.failed.add(cp)
        finally:
            with self.lock:
                self.busy.discard(key)

    def take_changed(self):
        with self.lock:
            changed, self.changed = self.changed, False
            return changed


def animated(session=None):
    """This Maya's animations (on sys, so a module reload keeps what was decoded)."""
    held = getattr(sys, _ANIM_ATTR, None)
    if isinstance(held, Animated) and session is None:
        return held
    if session is None:
        try:
            from . import session as _session
            session = _session.get()
        except Exception:                                    # noqa: BLE001
            return None
    root = getattr(getattr(session, "store", None), "root", None)
    if not root:
        return None
    folder = os.path.join(root, "emoji_anim")
    if not isinstance(held, Animated) or held.folder != folder:
        held = Animated(folder)
        setattr(sys, _ANIM_ATTR, held)
    return held
```

Note for `test_keeps_the_last_ones_only`: the fake fetch returns the same bytes for every codepoint, so three codepoints decode to three entries and the LRU trims to two.

- [ ] **Step 4: Run them to see them pass**

Run: `$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_chat_emojiart -v` → PASS.

- [ ] **Step 5: Commit**

`git add SkeldarAnim/maya_chat/emojiart.py tests/test_chat_emojiart.py`; message `feat(chat emoji): Noto animations - fetched once, decoded on a thread, played once`.

---

### Task 5: The feed, pills, previews, quotes, toasts and quick reactions draw pictures

**Files:**
- Modify: `SkeldarAnim/maya_chat/window.py` (`rich` ~250, `Box` ~477, `Feed.__init__` ~512, `_doc` ~584, `_layout` ~612, `_pill_font`/`_lay_pills` ~858, `tick` ~895, `paintEvent` pills ~1023 and doc ~1009, `box_at` ~1048, `mouseMoveEvent` ~1116, `leaveEvent` ~1174, `ChatList.paintEvent` preview ~453, `_quick_reactions` ~2589, `_each_second` ~2966)
- Modify: `SkeldarAnim/maya_chat/toast.py` (~264)
- Test: `tests/test_chat_window.py` (add class `EmojiPictures`)

**Interfaces:**
- Consumes: `emojiart.rich`, `register`, `pixmap`, `draw_line`, `anim_of`, `animated`, `frame_at`; `emoji.tokens`, `emoji.only_emoji`.
- Produces on `Box`: `bigs` — `[(QRectF, glyph)]` for a message of 1-3 emoji alone (then `doc` is None). On `Feed`: `plays` {(message key, glyph, where): started ms}, `played` set of the same keys, `BIG = 64` logical px; `box_at` answers `"big:<glyph>"`. Pills keep `(rect, emoji, count, mine)`.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_chat_window.py`)

```python
class EmojiPictures(Base):
    @staticmethod
    def _paint(widget):
        """Run paintEvent even when the window is not exposed offscreen."""
        img = QtGui.QImage(max(1, widget.width()), max(1, widget.height()),
                           QtGui.QImage.Format_ARGB32)
        widget.render(img)

    def setUp(self):
        Base.setUp(self)
        self.win.open_chat("dm")

    def _send_in(self, text, mid="e1", seq=50):
        self.ses.state.messages["dm"].append(msg(mid, seq, text=text))
        self.win.refresh()
        return next(b for b in self.win.feed.boxes
                    if b.item.kind == "msg" and b.item.message.get("id") == mid)

    def test_text_with_emoji_has_its_picture_in_the_document(self):
        box = self._send_in("огонь 🔥")
        self.assertIsNotNone(box.doc)
        res = box.doc.resource(QtGui.QTextDocument.ImageResource, QtCore.QUrl("emoji:1f525"))
        self.assertIsNotNone(res)

    def test_emoji_alone_are_big_pictures(self):
        box = self._send_in("🔥😂")
        self.assertIsNone(box.doc)
        self.assertEqual([g for _r, g in box.bigs], ["🔥", "😂"])
        side = box.bigs[0][0].width()
        self.assertAlmostEqual(side, self.win.px(W.BIG_EMOJI), delta=1)
        found, where = self.win.feed.box_at(box.bigs[1][0].center())
        self.assertEqual(where, "big:😂")

    def test_an_animated_big_emoji_plays_once_then_on_hover(self):
        box = self._send_in("😂")
        feed = self.win.feed
        frames = [(QtGui.QImage(4, 4, QtGui.QImage.Format_ARGB32), 50)]

        class FakeAnim(object):
            def frames(self, cp, px):
                return frames

            def take_changed(self):
                return False
        feed.anim = FakeAnim()
        with mock.patch.object(hubmotion, "enabled", return_value=True):
            self._paint(feed)
            key = (box.item.key(), "😂", "big")
            self.assertIn(key, feed.plays)
            self.assertIn(key, feed.played)
            feed.plays.clear()
            self._paint(feed)
            self.assertNotIn(key, feed.plays)            # once only
            ev = QtGui.QMouseEvent(QtCore.QEvent.MouseMove, box.bigs[0][0].center(),
                                   box.bigs[0][0].center(), QtCore.Qt.NoButton,
                                   QtCore.Qt.NoButton, QtCore.Qt.NoModifier)
            feed.mouseMoveEvent(ev)
            self.assertIn(key, feed.plays)               # the mouse plays it again

    def test_no_animation_when_animations_are_off(self):
        box = self._send_in("😂")
        feed = self.win.feed

        class FakeAnim(object):
            def frames(self, cp, px):
                return [(QtGui.QImage(4, 4, QtGui.QImage.Format_ARGB32), 50)]

            def take_changed(self):
                return False
        feed.anim = FakeAnim()
        with mock.patch.object(hubmotion, "enabled", return_value=False):
            self._paint(feed)
        self.assertFalse(feed.plays)

    def test_a_pill_is_a_picture_and_a_count(self):
        self.ses.state.messages["dm"][0]["reactions"] = {"🔥": ["bob"]}
        self.win.refresh()
        box = next(b for b in self.win.feed.boxes if b.pills)
        rect, e, n, mine = box.pills[0]
        self.assertEqual((e, n, mine), ("🔥", 1, False))
        self.assertLess(rect.width(), self.win.px(70))
```

- [ ] **Step 2: Run them to see them fail**

Run: `$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_chat_window.EmojiPictures -v`
Expected: FAIL (`box.doc.resource` None; `Box` has no `bigs`).

- [ ] **Step 3: Implement in `window.py`**

3a. Constants beside `PLAY_MS`:

```python
BIG_EMOJI = 64        # an emoji sent alone (1-3 of them), logical px (2026-10-22)
PILL_EMOJI = 16       # a reaction's picture in its pill
```

3b. `rich(text)` keeps its name for other callers but goes through emojiart:

```python
def rich(text, px=None):
    """A message's text as HTML: escaped, links as anchors, emoji as pictures `px` square
    (the line's height when None), new lines kept."""
    from . import emojiart
    return emojiart.rich(text, px or 16)
```

3c. `Box.__slots__` gains `"bigs"`, and `__init__` sets `self.bigs = []`.

3d. `Feed.__init__` adds:

```python
                self.plays = {}           # (message key, glyph, "big"|"pill") -> started ms
                self.played = set()       # the same keys, played once since the window opened
                self.anim = None          # emojiart.Animated (the window sets it)
```

3e. `_doc` builds pictures; a message of 1-3 emoji alone has no document:

```python
            def _big(self, item):
                """The glyphs of a message of 1-3 emoji alone, each with a picture; else []."""
                from . import emoji as _emoji
                from . import emojiart
                if not _emoji.only_emoji(item.text):
                    return []
                parts = [p for k, p in _emoji.tokens("".join(item.text.split()))]
                return parts if all(emojiart.image(p) is not None for p in parts) else []

            def _doc(self, item, width):
                key = (item.key(), item.text, int(width))
                doc = self.docs.get(key)
                if doc is None:
                    from . import emoji as _emoji
                    from . import emojiart
                    doc = QtGui.QTextDocument()
                    doc.setDocumentMargin(0)
                    big = _emoji.only_emoji(item.text)
                    font = _font(self.font(), hubstyle.px(30 if big else 11, self.win.scale))
                    font.setFamilies([font.family(), _emoji.FONT])
                    doc.setDefaultFont(font)
                    side = int(QtGui.QFontMetrics(font).height() * 1.2)
                    emojiart.register(doc, item.text, side)
                    doc.setDefaultStyleSheet("a {{ color: {0}; }}".format(
                        hubstyle.TOKENS["accent_text"]))
                    doc.setHtml('<span style="color:{0}">{1}</span>'.format(
                        hubstyle.TOKENS["text"], rich(item.text, side)))
                    doc.setTextWidth(width)
                    ideal = doc.idealWidth()
                    if ideal + 1 < width:
                        doc.setTextWidth(ideal + 1)
                    if len(self.docs) > 400:
                        self.docs.clear()
                    self.docs[key] = doc
                return doc
```

3f. In `_layout`, replace

```python
                    if f and not item.text:
                        doc, doc_w, doc_h = None, 0, -px(2)
                    else:
                        doc = self._doc(item, inner)
                        doc_w, doc_h = doc.size().width(), doc.size().height()
                    box.doc = doc
```
with
```python
                    bigs = [] if f else self._big(item)
                    if f and not item.text:
                        doc, doc_w, doc_h = None, 0, -px(2)
                    elif bigs:
                        side, gap_b = px(BIG_EMOJI), px(4)
                        doc = None
                        doc_w = len(bigs) * side + (len(bigs) - 1) * gap_b
                        doc_h = side
                    else:
                        doc = self._doc(item, inner)
                        doc_w, doc_h = doc.size().width(), doc.size().height()
                    box.doc = doc
```
and right after `box.doc_at = QtCore.QPointF(cx, cy)` add:
```python
                    if bigs:
                        side, gap_b = px(BIG_EMOJI), px(4)
                        box.bigs = [(QtCore.QRectF(cx + i * (side + gap_b), cy, side, side), g)
                                    for i, g in enumerate(bigs)]
```

3g. Pills: replace `_pill_font` and the width line in `_lay_pills`:

```python
            def _pill_font(self):
                return _font(self.font(), hubstyle.px(10.5, self.win.scale), True)
```
and in `_lay_pills` replace `w = fm.horizontalAdvance("%s %d" % (e, n)) + px(14)` with
```python
                    w = px(PILL_EMOJI) + px(4) + fm.horizontalAdvance(str(n)) + px(14)
```

3h. Animation helpers on `Feed` (beside `tick`):

```python
            def _start(self, key, glyph):
                """Play `glyph`'s animation now when it has one and its frames are ready."""
                from . import emojiart
                if self.anim is None or not hubmotion.enabled():
                    return False
                cp = emojiart.anim_of(glyph)
                if not cp:
                    return False
                px = int(hubstyle.px(BIG_EMOJI if key[2] == "big" else PILL_EMOJI, self.win.scale))
                if not self.anim.frames(cp, px):
                    return False
                self.plays[key] = _now_ms()
                self.played.add(key)
                self.win.animate()
                return True

            def _emoji_frame(self, key, glyph, side, now):
                """The image to draw for an emoji picture at `side`: its animation's frame while
                it plays (starting it the first time it is painted), else its still picture."""
                from . import emojiart
                if key not in self.played:
                    self._start(key, glyph)
                start = self.plays.get(key)
                if start is not None and self.anim is not None:
                    frames = self.anim.frames(emojiart.anim_of(glyph), int(side))
                    img, done = emojiart.frame_at(frames, now - start)
                    if done:
                        self.plays.pop(key, None)
                    if img is not None:
                        return img
                pm = emojiart.pixmap(glyph, int(side))
                return pm.toImage() if pm is not None else None
```

In `tick`, add `self.plays` to `busy`: change the `busy = bool(...)` line to include `or self.plays`.

3i. In `paintEvent`, after the `if box.doc is not None:` block add:

```python
                    for rect, glyph in box.bigs:
                        img = self._emoji_frame((key, glyph, "big"), glyph, rect.width(), now)
                        if img is not None:
                            p.drawImage(rect, img, QtCore.QRectF(img.rect()))
```

and replace the pill text drawing line `p.drawText(r, QtCore.Qt.AlignCenter, "%s %d" % (e, n))` with:

```python
                            side = px(PILL_EMOJI)
                            pic = QtCore.QRectF(r.left() + px(7), r.center().y() - side / 2.0,
                                                side, side)
                            img = self._emoji_frame((key, e, "pill"), e, side, now)
                            if img is not None:
                                p.drawImage(pic, img, QtCore.QRectF(img.rect()))
                            else:
                                p.drawText(pic, QtCore.Qt.AlignCenter, e)
                            p.drawText(QtCore.QRectF(pic.right() + px(4), r.top(),
                                                     r.right() - pic.right() - px(4), r.height()),
                                       QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, str(n))
```
Add `p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)` once near the start of `paintEvent` (after the painter is made). `key` is the variable `key = item.key()` already set in the message branch; `now` is already defined there.

3j. `box_at`: before the `bubble` check add:

```python
                    for rect, glyph in box.bigs:
                        if rect.contains(point):
                            return box, "big:" + glyph
```

3k. `mouseMoveEvent`: after `box, _where = self.box_at(pos)` add:

```python
                self._hover_emoji(box, _where)
```
and add the method:

```python
            def _hover_emoji(self, box, where):
                """The mouse entering an animated emoji (a big one, a pill) plays it again."""
                hit = None
                if box is not None and (where.startswith("big:") or where.startswith("pill:")):
                    kind, glyph = where.split(":", 1)
                    hit = (box.item.key(), glyph, kind)
                if hit != getattr(self, "_emoji_hover", None):
                    self._emoji_hover = hit
                    if hit is not None and hit not in self.plays:
                        self._start(hit, hit[1])
```
and in `leaveEvent` add `self._emoji_hover = None`.

3l. Chat list preview (`ChatList.paintEvent`, the `sub = pfm.elidedText(...)` and `p.drawText(... sub)` lines) becomes:

```python
                    from . import emojiart
                    width_left = right - x0 - badge_w - px(6)
                    emojiart.draw_line(p, QtCore.QRectF(x0, top + px(41) + lift - pfm.ascent(),
                                                        width_left, pfm.height()),
                                       r["preview"], p.font(), p.pen().color())
```

3m. Reply quote text (in `paintEvent`, the second `p.drawText(... fm2.elidedText(qtext ...))`) becomes:

```python
                        from . import emojiart
                        emojiart.draw_line(p, QtCore.QRectF(qrect.left() + px(7),
                                                            qrect.bottom() - fm2.height() - px(2),
                                                            qrect.width() - px(10), fm2.height()),
                                           qtext, p.font(), p.pen().color())
```

3n. `_quick_reactions`: replace `b.setText(e)` / `b.setFont(font)` with:

```python
            from . import emojiart
            pm = emojiart.pixmap(e, self.px(22))
            if pm is not None:
                b.setIcon(q.QtGui.QIcon(pm))
                b.setIconSize(q.QtCore.QSize(self.px(22), self.px(22)))
            else:
                b.setText(e)
                b.setFont(font)
            b.setToolTip(e)
```

3o. The window gives the feed its animations and repaints when frames arrive. Where the window builds `self.feed` (search `feed_class()(`), right after add:

```python
        from . import emojiart
        self.feed.anim = emojiart.animated(self.session)
```
In `_each_second`, after the avatar block add:

```python
        anim = self.feed.anim
        if anim is not None and anim.take_changed():
            self.feed.update()
```

- [ ] **Step 4: The toast's text line**

In `SkeldarAnim/maya_chat/toast.py` replace the second `p.drawText(QtCore.QRectF(tx, card.y() + self.px(27), ...), ..., fm.elidedText(self.text, ...))` with:

```python
            from . import emojiart
            emojiart.draw_line(p, QtCore.QRectF(tx, card.y() + self.px(27), right - tx, self.px(16)),
                               self.text, p.font(), p.pen().color())
```

- [ ] **Step 5: Run the window tests**

Run: `$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_chat_window tests.test_chat_emojiart tests.test_chat_emoji -v`
Expected: all PASS (the old `Reactions` tests too: the pill's `(e, n, mine)` and `box_at` are unchanged).

- [ ] **Step 6: Commit**

`git add SkeldarAnim/maya_chat/window.py SkeldarAnim/maya_chat/toast.py tests/test_chat_window.py`; message `feat(chat emoji): the feed, reactions, previews, quotes and toasts draw Fluent pictures, animated once`.

---

### Task 6: The picker rebuilt: search, tones, groups, scrolling grid

**Files:**
- Modify: `SkeldarAnim/maya_chat/window.py` (`PICK_*` and `picker_class` ~1188-1321, `pick_emoji` ~2638)
- Modify: `SkeldarAnim/maya_chat/emoji.py` (remove `CATEGORIES`)
- Test: `tests/test_chat_window.py` (add class `Picker`)

**Interfaces:**
- Consumes: `emoji.index()`, `emoji.search()`, `emoji.toned()`, `emoji.recent()`, `emoji.TONE_VAR`, `emojiart.pixmap()`, `hubmotion.enabled()`, `look_approach()` (window).
- Produces: `EmojiPicker(win, picked)` with `.search` (QLineEdit, object name `skeldarChatEmojiSearch`), `.set_query(text)`, `.set_tone(t)` (0..5, remembered), `.sections() -> [(key, title, [glyph])]`, `.items() -> [glyph]` (every glyph listed, in order), `.pick(glyph)`, `.scroll_to(key)`, `.hit(point) -> ("tone", t) | ("tab", key) | ("emoji", glyph) | None`. Constants `PICK_COLS = 9`, `PICK_CELL = 32`, `PICK_ROWS = 8`.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_chat_window.py`)

```python
class Picker(Base):
    def setUp(self):
        Base.setUp(self)
        W._VARS.pop("skeldarChatEmojiTone", None)
        self.win.open_chat("dm")
        self.picker = self.win.pick_emoji()

    def tearDown(self):
        self.picker.close()
        Base.tearDown(self)

    def test_recent_then_the_eight_groups(self):
        keys = [k for k, _t, _items in self.picker.sections()]
        self.assertEqual(keys, ["recent", "smileys", "people", "animals", "food", "travel",
                                "activities", "objects", "symbols"])
        self.assertGreater(len(self.picker.items()), 1300)

    def test_search_in_russian(self):
        self.picker.search.setText("кот")
        self.assertEqual([k for k, _t, _i in self.picker.sections()], ["found"])
        self.assertIn("\U0001F431", self.picker.items())

    def test_nothing_found(self):
        self.picker.set_query("zzzzqq")
        self.assertEqual(self.picker.items(), [])

    def test_enter_picks_the_first_result(self):
        self.picker.set_query("огонь")
        first = self.picker.items()[0]
        enter = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, QtCore.Qt.Key_Return,
                                QtCore.Qt.NoModifier)
        self.picker.search.keyPressEvent(enter)
        self.assertEqual(self.win.composer.toPlainText(), first)

    def test_esc_clears_then_closes(self):
        self.picker.set_query("кот")
        esc = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, QtCore.Qt.Key_Escape, QtCore.Qt.NoModifier)
        self.picker.search.keyPressEvent(esc)
        self.assertEqual(self.picker.search.text(), "")
        self.assertTrue(self.picker.isVisible())
        self.picker.search.keyPressEvent(esc)
        self.assertFalse(self.picker.isVisible())

    def test_a_tone_is_applied_and_remembered(self):
        self.picker.set_tone(3)
        self.assertIn("\U0001F44D\U0001F3FD", self.picker.items())
        self.assertEqual(int(W.get_var("skeldarChatEmojiTone")), 3)
        again = self.win.pick_emoji()
        self.assertIn("\U0001F44D\U0001F3FD", again.items())
        again.close()

    def test_a_toned_pick_goes_into_the_composer_and_recent(self):
        self.picker.set_tone(5)
        self.picker.pick("\U0001F44D\U0001F3FF")
        self.assertEqual(self.win.composer.toPlainText(), "\U0001F44D\U0001F3FF")
        self.assertIn("\U0001F44D\U0001F3FF", W.get_var("skeldarChatEmojiRecent"))

    def test_a_tab_scrolls_to_its_group(self):
        self.picker.scroll_to("food")
        self.assertGreater(self.picker.scroll, 0)
        top = self.picker.section_top("food")
        self.assertAlmostEqual(self.picker.scroll, min(top, self.picker.max_scroll()), delta=1)
```


- [ ] **Step 2: Run them to see them fail**

Run: `$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_chat_window.Picker -v`
Expected: FAIL (`EmojiPicker` has no `sections`).

- [ ] **Step 3: Replace the picker in `window.py`**

Replace from `PICK_COLS = 10` through `return _CLASSES["picker"]` (the end of `picker_class`) with:

```python
PICK_COLS = 9
PICK_ROWS = 8
PICK_CELL = 32
PICK_HEAD = 18        # a section's title row
PICK_LIFT = 1.10      # a cell under the mouse grows 10 % (the Time Bar's hover)
PICK_TONES = ("#ffc93a", "#f7d7c4", "#e0b291", "#bf8f68", "#9b643d", "#594539")


def picker_class():
    """EmojiPicker(window, picked): a search field over tone swatches, group tabs and a
    scrolling painted grid; a click (or Enter on the search) calls picked(emoji) and closes it."""
    if "picker" not in _CLASSES:
        q = _q()
        QtCore, QtGui, QtWidgets = q.QtCore, q.QtGui, q.QtWidgets
        from . import emoji as _emoji
        from . import emojiart

        class Search(QtWidgets.QLineEdit):
            def __init__(self, picker):
                super(Search, self).__init__(picker)
                self.picker = picker

            def keyPressEvent(self, event):                # noqa: N802
                if event.key() == QtCore.Qt.Key_Escape:
                    if self.text():
                        self.clear()
                    else:
                        self.picker.close()
                    return
                if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
                    items = self.picker.items()
                    if items:
                        self.picker.pick(items[0])
                    return
                super(Search, self).keyPressEvent(event)

        class EmojiPicker(QtWidgets.QWidget):

            def __init__(self, win, picked, parent=None):
                super(EmojiPicker, self).__init__(parent or win.root,
                                                  QtCore.Qt.Popup | QtCore.Qt.FramelessWindowHint)
                self.win, self.picked = win, picked
                self.setObjectName("skeldarChatEmojiPicker")
                self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
                self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
                self.setMouseTracking(True)
                px = win.px
                self.pad = px(8)
                self.cell = px(PICK_CELL)
                self.head = px(PICK_HEAD)
                self.idx = _emoji.index()
                try:
                    self.tone = int(get_var(_emoji.TONE_VAR) or 0)
                except (TypeError, ValueError):
                    self.tone = 0
                self.query = ""
                self.scroll = 0.0
                self.hover = None
                self.levels = {}          # hovered cell -> its lift, 0..1
                self._last = time.monotonic()
                self.timer = QtCore.QTimer(self)
                self.timer.setInterval(TICK_MS)
                self.timer.timeout.connect(self._tick)
                width = 2 * self.pad + PICK_COLS * self.cell
                self.search = Search(self)
                self.search.setObjectName("skeldarChatEmojiSearch")
                self.search.setPlaceholderText(u"Поиск: кот, огонь, fire…")
                self.search.setGeometry(self.pad, self.pad, width - 2 * self.pad, px(26))
                self.search.textChanged.connect(self.set_query)
                self.top_tones = self.pad + px(26) + px(6)
                self.top_tabs = self.top_tones + px(20)
                self.top_grid = self.top_tabs + self.cell + px(4)
                self.setFixedSize(width, self.top_grid + PICK_ROWS * self.cell + self.pad)
                self.font_ = QtGui.QFont(self.font())
                self.font_.setFamilies([self.font_.family(), _emoji.FONT])
                self.font_.setPixelSize(px(19))
                self._layout()
                self.search.setFocus()

            # ------------------------------------------------------ what is listed
            def _glyph(self, rec):
                return _emoji.toned(rec, self.tone)[0]

            def sections(self):
                """[(key, title, [glyph])] as last laid out."""
                return self._sections

            def _fresh_sections(self):
                """The results of a search, else Recent and the groups."""
                if self.query.strip():
                    return [("found", u"Найдено",
                             [self._glyph(r) for r in _emoji.search(self.query, idx=self.idx)])]
                out = [("recent", u"Недавние", _emoji.recent(get_var(_emoji.RECENT_VAR)))]
                for key, _tab, title in self.idx.groups:
                    out.append((key, title, [self._glyph(r) for r in self.idx.of_group(key)]))
                return out

            def items(self):
                return [g for _k, _t, glyphs in self.sections() for g in glyphs]

            def _layout(self):
                """Each section's top and each cell's rect, in grid coordinates (scroll 0)."""
                self._sections = self._fresh_sections()
                self.tops, self.cells, y = {}, [], 0
                for key, title, glyphs in self._sections:
                    self.tops[key] = y
                    y += self.head
                    for i, g in enumerate(glyphs):
                        self.cells.append((QtCore.QRectF(self.pad + (i % PICK_COLS) * self.cell,
                                                         y + (i // PICK_COLS) * self.cell,
                                                         self.cell, self.cell), g))
                    y += ((len(glyphs) + PICK_COLS - 1) // PICK_COLS) * self.cell
                self.height_ = y
                self.scroll = max(0.0, min(self.scroll, self.max_scroll()))
                self.update()

            def max_scroll(self):
                return max(0.0, self.height_ - PICK_ROWS * self.cell)

            def section_top(self, key):
                return self.tops.get(key, 0)

            def scroll_to(self, key):
                self.scroll = max(0.0, min(float(self.section_top(key)), self.max_scroll()))
                self.update()

            def set_query(self, text):
                self.query = text or ""
                if self.search.text() != self.query:
                    self.search.setText(self.query)
                self.scroll = 0.0
                self._layout()

            def set_tone(self, tone):
                self.tone = max(0, min(5, int(tone)))
                set_var(_emoji.TONE_VAR, str(self.tone))
                self._layout()

            # ------------------------------------------------------ hits
            def _tabs(self):
                keys = ["recent"] + [g[0] for g in self.idx.groups]
                glyphs = [u"\U0001F558"] + [g[1] for g in self.idx.groups]
                return [(QtCore.QRectF(self.pad + i * self.cell, self.top_tabs, self.cell,
                                       self.cell), k, g)
                        for i, (k, g) in enumerate(zip(keys, glyphs))]

            def _tone_rects(self):
                s = self.win.px(14)
                return [(QtCore.QRectF(self.pad + i * (s + self.win.px(6)),
                                       self.top_tones + self.win.px(3), s, s), i)
                        for i in range(6)]

            def hit(self, pos):
                for rect, t in self._tone_rects():
                    if rect.contains(pos):
                        return ("tone", t)
                for rect, key, _g in self._tabs():
                    if rect.contains(pos):
                        return ("tab", key)
                if pos.y() < self.top_grid or pos.y() > self.top_grid + PICK_ROWS * self.cell:
                    return None
                gp = QtCore.QPointF(pos.x(), pos.y() - self.top_grid + self.scroll)
                for rect, g in self.cells:
                    if rect.contains(gp):
                        return ("emoji", g)
                return None

            # ------------------------------------------------------ input
            def wheelEvent(self, event):                   # noqa: N802
                dy = event.angleDelta().y()
                self.scroll = max(0.0, min(self.scroll - dy / 120.0 * self.cell * 1.5,
                                           self.max_scroll()))
                self.update()

            def mouseMoveEvent(self, event):              # noqa: N802
                pos = event.position() if hasattr(event, "position") else QtCore.QPointF(event.pos())
                h = self.hit(pos)
                if h != self.hover:
                    self.hover = h
                    if h is not None and h[0] == "emoji" and not hubmotion.enabled():
                        self.levels = {h: 1.0}
                    self._wake()
                    self.update()

            def leaveEvent(self, event):                   # noqa: N802
                self.hover = None
                self._wake()

            def mousePressEvent(self, event):              # noqa: N802
                pos = event.position() if hasattr(event, "position") else QtCore.QPointF(event.pos())
                if not self.rect().contains(pos.toPoint()):
                    self.close()
                    return
                h = self.hit(pos)
                if h is None:
                    return
                if h[0] == "tone":
                    self.set_tone(h[1])
                elif h[0] == "tab":
                    if self.query:
                        self.set_query("")
                    self.scroll_to(h[1])
                else:
                    self.pick(h[1])

            def pick(self, e):
                self.close()
                try:
                    self.picked(e)
                except Exception:                            # noqa: BLE001
                    traceback.print_exc()

            # ------------------------------------------------------ motion
            def _wake(self):
                if hubmotion.enabled() and not self.timer.isActive():
                    self._last = time.monotonic()
                    self.timer.start()
                elif not hubmotion.enabled():
                    self.levels = {self.hover: 1.0} if self.hover else {}
                    self.update()

            def _tick(self):
                now = time.monotonic()
                dt = (now - self._last) * 1000.0
                self._last = now
                keys = set(self.levels) | ({self.hover} if self.hover else set())
                busy = False
                for k in keys:
                    goal = 1.0 if k == self.hover else 0.0
                    v = look_approach(self.levels.get(k, 0.0), goal, dt, HOVER_MS)
                    if v <= 0.0:
                        self.levels.pop(k, None)
                    else:
                        self.levels[k] = v
                    busy = busy or v != goal
                self.update()
                if not busy:
                    self.timer.stop()

            # ------------------------------------------------------ paint
            def paintEvent(self, event):                   # noqa: N802
                p = QtGui.QPainter(self)
                try:
                    self._paint(p)
                except Exception:                            # noqa: BLE001
                    traceback.print_exc()
                finally:
                    p.end()

            def _active_tab(self):
                if self.query:
                    return None
                active = "recent"
                for key, top in sorted(self.tops.items(), key=lambda kv: kv[1]):
                    if top <= self.scroll + self.head:
                        active = key
                return active

            def _paint(self, p):
                px = self.win.px
                p.setRenderHint(QtGui.QPainter.Antialiasing)
                p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
                p.setPen(QtGui.QPen(_colour("line"), 1))
                p.setBrush(_colour("panel"))
                p.drawRoundedRect(QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5),
                                  px(8), px(8))
                for rect, t in self._tone_rects():
                    p.setPen(QtGui.QPen(_colour("accent") if t == self.tone else _colour("line"),
                                        px(1.5) if t == self.tone else 1))
                    p.setBrush(QtGui.QColor(PICK_TONES[t]))
                    p.drawEllipse(rect)
                active = self._active_tab()
                for rect, key, glyph in self._tabs():
                    if key == active:
                        p.setPen(QtCore.Qt.NoPen)
                        p.setBrush(_colour("card_active"))
                        p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), px(6), px(6))
                        p.setPen(QtGui.QPen(_colour("accent"), 1.5))
                        p.drawLine(QtCore.QPointF(rect.left() + px(6), rect.bottom() - 1),
                                   QtCore.QPointF(rect.right() - px(6), rect.bottom() - 1))
                    elif self.hover == ("tab", key):
                        p.setPen(QtCore.Qt.NoPen)
                        p.setBrush(_colour("hover"))
                        p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), px(6), px(6))
                    pm = emojiart.pixmap(glyph, px(20))
                    if pm is not None:
                        p.drawPixmap(rect.center() - QtCore.QPointF(px(10), px(10)), pm)
                    else:
                        p.setFont(self.font_)
                        p.setPen(_colour("text"))
                        p.drawText(rect, QtCore.Qt.AlignCenter, glyph)
                grid = QtCore.QRectF(0, self.top_grid, self.width(), PICK_ROWS * self.cell)
                p.save()
                p.setClipRect(grid)
                p.translate(0, self.top_grid - self.scroll)
                title_font = _font(self.font(), px(9), True)
                for key, title, glyphs in self.sections():
                    top = self.tops[key]
                    p.setFont(title_font)
                    p.setPen(_colour("muted"))
                    p.drawText(QtCore.QRectF(self.pad, top, self.width() - 2 * self.pad, self.head),
                               QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, title.upper())
                    if not glyphs and key == "found":
                        p.drawText(QtCore.QRectF(self.pad, top + self.head,
                                                 self.width() - 2 * self.pad, self.cell),
                                   QtCore.Qt.AlignCenter, u"Ничего не нашлось")
                lo, hi = self.scroll - self.cell, self.scroll + grid.height() + self.cell
                side = px(24)
                for rect, g in self.cells:
                    if rect.bottom() < lo or rect.top() > hi:
                        continue
                    lift = self.levels.get(("emoji", g), 0.0)
                    if lift > 0.0:
                        p.setPen(QtCore.Qt.NoPen)
                        p.setBrush(_colour("hover", lift))
                        p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), px(6), px(6))
                    k = 1.0 + (PICK_LIFT - 1.0) * lift
                    s = side * k
                    target = QtCore.QRectF(rect.center().x() - s / 2.0, rect.center().y() - s / 2.0, s, s)
                    pm = emojiart.pixmap(g, int(round(side * PICK_LIFT)))
                    if pm is not None:
                        p.drawPixmap(target, pm, QtCore.QRectF(pm.rect()))
                    else:
                        p.setFont(self.font_)
                        p.setPen(_colour("text"))
                        p.drawText(rect, QtCore.Qt.AlignCenter, g)
                p.restore()

        _CLASSES["picker"] = EmojiPicker
    return _CLASSES["picker"]
```

- [ ] **Step 4: Style the search field and keep the picker inside the screen**

In `pick_emoji`, after `picker = picker_class()(self, picked)`, give the field the hub's recessed look:

```python
        picker.search.setStyleSheet(
            "QLineEdit {{ background: {0}; border: 1px solid {1}; border-radius: {2}px;"
            " color: {3}; padding: 0 {4}px; }}".format(
                hubstyle.TOKENS["track"], hubstyle.TOKENS["track_edge"], self.px(5),
                hubstyle.TOKENS["text"], self.px(6)))
```
and after `picker.move(...)`, add `picker.search.setFocus()`.

- [ ] **Step 5: Remove `CATEGORIES`**

Delete the `CATEGORIES = (...)` tuple and its comment from `emoji.py`. Run `git grep -n CATEGORIES -- SkeldarAnim tests` → no hits.

- [ ] **Step 6: Run the chat tests**

Run: `$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_chat_window tests.test_chat_emoji tests.test_chat_emojiart tests.test_chat_extras -v`
Expected: all PASS, the old `Reactions` picker tests included (`picker.items()` non-empty, `pick("🔥")`, `pick("😂")`).

- [ ] **Step 7: Commit**

`git add SkeldarAnim/maya_chat/window.py SkeldarAnim/maya_chat/emoji.py tests/test_chat_window.py`; message `feat(chat emoji): the picker - search in Russian and English, skin tones, every group in one scrolling grid`.

---

### Task 7: The filmstrip, the whole suite, CLAUDE.md

**Files:**
- Create: `docs/superpowers/plans/render_chat_emoji.py`
- Modify: `CLAUDE.md` (a section after "Chat: scenes and files in a chat")

- [ ] **Step 1: Write the filmstrip**

`docs/superpowers/plans/render_chat_emoji.py`:

```python
"""Draw the chat's emoji offscreen at 150 %: a feed with text, a big lone emoji and pills,
and the picker (all, a search, a tone). Writes docs/superpowers/plans/chat_emoji.png.

    $env:QT_QPA_PLATFORM='offscreen'; mayapy docs/superpowers/plans/render_chat_emoji.py
"""
import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))
sys.path.insert(0, REPO)

from PySide6 import QtCore, QtGui, QtWidgets  # noqa: E402

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
font_dir = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
for name in ("segoeui.ttf", "seguiemj.ttf"):
    QtGui.QFontDatabase.addApplicationFont(os.path.join(font_dir, name))

from tests import test_chat_window as T  # noqa: E402
from maya_chat import window as W  # noqa: E402


def grab(widget):
    img = QtGui.QImage(widget.size(), QtGui.QImage.Format_ARGB32)
    img.fill(QtGui.QColor("#1b1c1f"))
    widget.render(img)
    return img


def main():
    W._scale = lambda: 1.5
    base = T.Base("run")
    base.setUp()
    win, ses = base.win, base.ses
    ses.state.messages["dm"] += [
        T.msg("e1", 40, text=u"Сцену с ударом залил 🚀 глянь, там рука 🤔"),
        T.msg("e2", 41, frm="me", text=u"Огонь 🔥🔥 поправлю завтра 🙏🏽"),
        T.msg("e3", 42, text=u"😂"),
        T.msg("e4", 43, frm="me", text=u"🎉😎"),
    ]
    ses.state.messages["dm"][-2]["reactions"] = {"👍": ["me", "bob"], "❤️": ["bob"]}
    win.open_chat("dm")
    win.root.resize(760, 620)
    win.root.show()
    app.processEvents()
    feed = grab(win.root)
    shots = [feed]
    picker = win.pick_emoji()
    app.processEvents()
    shots.append(grab(picker))
    picker.set_query(u"кот")
    app.processEvents()
    shots.append(grab(picker))
    picker.set_query("")
    picker.set_tone(3)
    picker.scroll_to("people")
    app.processEvents()
    shots.append(grab(picker))
    picker.close()
    width = sum(s.width() for s in shots) + 20 * (len(shots) + 1)
    height = max(s.height() for s in shots) + 40
    sheet = QtGui.QImage(width, height, QtGui.QImage.Format_ARGB32)
    sheet.fill(QtGui.QColor("#17181b"))
    p = QtGui.QPainter(sheet)
    x = 20
    for s in shots:
        p.drawImage(x, 20, s)
        x += s.width() + 20
    p.end()
    out = os.path.join(HERE, "chat_emoji.png")
    sheet.save(out)
    print(out)
    base.tearDown()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Render and look at it**

Run: `$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs\superpowers\plans\render_chat_emoji.py`
Expected: prints the PNG's path. Open `docs/superpowers/plans/chat_emoji.png` with the Read tool and check: 3D pictures inline in the bubbles, the big 😂 and 🎉😎 at 64 px, pills with pictures and counts, the picker's tones, tabs and grid, «НАЙДЕНО» with cats for «кот», toned hands on the people tab. If `T.Base` needs arguments different from `"run"` (it is a `unittest.TestCase`), use any test method name of `Base`'s subclasses, e.g. `T.Reactions("test_the_menu_offers_a_reaction")`, and call `setUp()` directly.

- [ ] **Step 3: Run the whole suite**

Run: `$env:QT_QPA_PLATFORM='offscreen'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t .`
Expected: OK, except the known `test_chat_deploy.Keys` failure (the animator's saved Cloudflare keys). Any other failure is this work's to fix.

- [ ] **Step 4: The build zip still verifies**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' make_build.py --out $env:TEMP\skeldar_emoji_build_test.zip`
Expected: the archive written and verified (it reopens and compares with the payload), about 10 MB bigger than before. Delete the zip afterwards.

- [ ] **Step 5: CLAUDE.md**

Add after the section "## Chat: scenes and files in a chat (2026-10-22)":

```markdown
## Chat: the whole emoji set in Fluent 3D, animated when sent alone (2026-10-22)

The animator: «добавить больше разных смайликов и эмодзи (найди где-то библеотеки)» (calls next,
in a spec of their own). Mockup https://claude.ai/artifact/BTa4Lm5xuZvu1QBQri1zyh, chosen D. Spec
`docs/superpowers/specs/2026-10-22-chat-emoji-fluent-design.md`, plan beside it.
- **Shipped** `SkeldarAnim/assets/emoji/`: 8 sheets (96 px WebP, 64 columns) of Microsoft's Fluent
  Emoji 3D (MIT, commit 1ffb34c), `emoji.json` (emojibase 18.0.0's names, keywords ru + en, groups,
  skin tones; Noto's animation codepoint), `LICENSE.txt` (Fluent and emojibase MIT, Noto CC BY 4.0).
  Built by `docs/superpowers/plans/make_emoji_sheets.py`; `--check` compares with a fresh build.
  Flags and the component group are left out.
- `maya_chat/emoji.py` (stdlib): `index()`, `tokens(text)` (longest known emoji, sequences whole,
  a lone symbol without VS16 stays text), `search` (every query word starts a name or keyword
  word, ru or en), `toned`, `count`/`only_emoji`/`is_emoji` on tokens.
- `maya_chat/emojiart.py` (Qt): pictures cut from the sheets, `rich`/`register` for the bubbles'
  QTextDocuments, `draw_line` for list previews, quotes and toasts, `Animated` - Noto's 512 px webp
  fetched once into `<store>/emoji_anim/`, frames decoded at the drawn size on a thread, the last
  24 kept.
- **The feed**: emoji in text are pictures; 1-3 alone are 64 px pictures (`Box.bigs`); a reaction
  pill is a 16 px picture and its count. An animated one plays once the first time it is painted
  and again under the mouse; Interface animations off - none.
- **The picker**: a search field (Esc clears then closes, Enter picks the first), six skin tones
  (`skeldarChatEmojiTone`), tabs Recent + 8 groups over one scrolling painted grid, the hover lift.
- Not built: flags, pictures in the composer, `:name` autocomplete, stickers.
```

- [ ] **Step 6: Commit**

`git add docs/superpowers/plans/render_chat_emoji.py docs/superpowers/plans/chat_emoji.png CLAUDE.md`; message `docs(chat emoji): the filmstrip and CLAUDE.md`.
