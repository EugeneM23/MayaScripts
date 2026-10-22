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
          6: ("activities", "⚽", "Занятия"),
          7: ("objects", "\U0001F4A1", "Предметы"),
          8: ("symbols", "❤️", "Символы")}
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
