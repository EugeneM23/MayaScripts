"""The skill bar's model (2026-10-19): pages, cells, rows, items, their JSON, the grid's geometry and
hits, labels and captions. Stdlib only (a test pins it).

Page 1 (F1) is the Time Bar itself; pages 2..12 (F2..F12) hold cells. A page is
{"name": str, "cells": {"r.c": item}}; an item is a dict with a `kind` (see KINDS) and its fields.
Spec: docs/superpowers/specs/2026-10-19-skill-bar-design.md
"""

import json

VERSION = 1
PAGES = 12                  # F1..F12
TIME_PAGE = 1               # F1: the Time Bar
ROWS = (1,)                 # 2026-10-19: one row of SLOTS cells, as tall as the time rows
DEFAULT_ROWS = 1
SLOTS = 10                  # «давай сделаем что бы их было только 10» (keys 1..0)
MAX_COLS = 64               # how far an older file's cells are read (folded into the SLOTS)

# geometry, logical px
TAB_H = 18                  # the page row
TAB_GAP = 3
TAB_PAD = 7
GAP = 4                     # between cells
CELL_MIN = 22
CELL_MAX = 120
PAD = 6                     # round the cells

# item kinds and the fields each needs
KINDS = {
    "section": ("key",),
    "cmd": ("key",),
    "character": ("model", "char"),
    "card": ("path",),
    "weapon": ("key",),
    "maya": ("command",),
    "script": ("lang", "code"),
    "shelf": ("lang", "code"),
}
LANGS = ("python", "mel")
KIND_NAMES = {
    "section": "Section", "cmd": "Tool", "character": "Character", "card": "Pose card",
    "weapon": "Weapon", "maya": "Maya", "script": "Script", "shelf": "Shelf button",
}

# the pages a first start gets
DEFAULT_PAGES = {
    2: ("Animate", [
        {"kind": "cmd", "key": "tools.knot"},
        {"kind": "cmd", "key": "tools.knot_offset"},
        {"kind": "cmd", "key": "tools.aim"},
        {"kind": "cmd", "key": "tools.snapshot"},
        {"kind": "cmd", "key": "tools.bake"},
        {"kind": "cmd", "key": "tools.bake_layer"},
        {"kind": "cmd", "key": "tools.remove"},
        {"kind": "cmd", "key": "editor.graph"},
        {"kind": "section", "key": "connections"},
        {"kind": "section", "key": "poses"},
    ]),
    3: ("Characters", [
        {"kind": "character", "model": "Manny", "char": "rig"},
        {"kind": "character", "model": "Creep", "char": "rig"},
        {"kind": "character", "model": "Orc_D", "char": "rig"},
        {"kind": "character", "model": "Manny", "char": "skeleton"},
        {"kind": "character", "model": "Creep", "char": "skeleton"},
        {"kind": "character", "model": "UE4_Mannequin", "char": "skeleton"},
        {"kind": "section", "key": "characters"},
        {"kind": "section", "key": "weapons"},
    ]),
    4: ("Editors", [                    # 2026-10-20
        {"kind": "cmd", "key": "editor.script"},
        {"kind": "cmd", "key": "editor.graph"},
        {"kind": "cmd", "key": "editor.outliner"},
        {"kind": "cmd", "key": "editor.component"},
        {"kind": "cmd", "key": "editor.motiontrail"},
    ]),
}
# A cell added to a default page after files holding that page were made: (page, item), given once
# to a page still under its default name, into its first free cell («добавь во вкладку editors
# моушен треил эдитор», 2026-10-20). Remembered by the item's key in the file's `added`.
ADDED_CELLS = (
    (4, {"kind": "cmd", "key": "editor.motiontrail"}),
)
# The default pages a file written before `seeded` existed had already been given.
FIRST_SEEDED = (2, 3)


# ----------------------------------------------------------------- items

def valid_item(item):
    """True for a dict naming a known kind with every field it needs, as non-empty strings."""
    if not isinstance(item, dict):
        return False
    fields = KINDS.get(item.get("kind"))
    if fields is None:
        return False
    for name in fields:
        value = item.get(name)
        if not isinstance(value, str) or not value:
            return False
    if item["kind"] in ("script", "shelf") and item.get("lang") not in LANGS:
        return False
    if item["kind"] == "character" and item.get("char") not in ("rig", "skeleton"):
        return False
    label = item.get("label")
    return label is None or isinstance(label, str)


def clean_item(item):
    """The item with only the fields we keep (strings), or None."""
    if not valid_item(item):
        return None
    keep = ("kind",) + KINDS[item["kind"]] + ("label", "image")
    return dict((k, item[k]) for k in keep if isinstance(item.get(k), str) and item.get(k) != "")


def script_item(code, lang="python", label=""):
    """A script skill from text; None for blank text."""
    code = (code or "").strip("\n")
    if not code.strip():
        return None
    item = {"kind": "script", "lang": lang if lang in LANGS else "python", "code": code}
    label = label or script_label(code)
    if label:
        item["label"] = label
    return item


def script_label(code):
    """A script's own name: its first line that is not blank or a bare comment marker, cut."""
    for line in (code or "").splitlines():
        text = line.strip().lstrip("#/").strip()
        if text:
            return text[:40]
    return "Script"


def same_item(a, b):
    """Whether two items name the same thing (labels aside)."""
    if not (a and b) or a.get("kind") != b.get("kind"):
        return False
    return all(a.get(f) == b.get(f) for f in KINDS.get(a["kind"], ()))


# ------------------------------------------------------------------ cells

def cell_key(row, col):
    return "%d.%d" % (int(row), int(col))


def parse_key(key):
    """(row, col) of "r.c", or None."""
    try:
        r, c = str(key).split(".")
        r, c = int(r), int(c)
    except (ValueError, AttributeError):
        return None
    if r != 0 or c < 0 or c >= SLOTS:
        return None
    return r, c


def _old_key(key):
    """(row, col) of a cell an older file may hold (up to 4 rows, MAX_COLS columns), or None."""
    try:
        r, c = str(key).split(".")
        r, c = int(r), int(c)
    except (ValueError, AttributeError):
        return None
    return (r, c) if 0 <= r < 4 and 0 <= c < MAX_COLS else None


# ------------------------------------------------------------------ model

def blank():
    return {"version": VERSION, "rows": DEFAULT_ROWS, "seeded": [], "added": [],
            "pages": dict((str(n), {"name": "", "cells": {}}) for n in range(2, PAGES + 1))}


def defaults():
    data = blank()
    for n, (name, items) in DEFAULT_PAGES.items():
        page = data["pages"][str(n)]
        page["name"] = name
        for i, item in enumerate(items):
            page["cells"][cell_key(0, i)] = dict(item)
    data["seeded"] = sorted(DEFAULT_PAGES)
    data["added"] = sorted(item["key"] for _n, item in ADDED_CELLS)
    return data


def seed_new(data):
    """(data, changed): a default page added since this file was made goes onto its F-key when
    that page is still empty and unnamed; a page once seeded is never given again (the animator
    may have cleared it)."""
    changed = False
    for n, (name, items) in sorted(DEFAULT_PAGES.items()):
        if n in data["seeded"]:
            continue
        page = data["pages"][str(n)]
        if not page["name"] and not page["cells"]:
            page["name"] = name
            for i, item in enumerate(items):
                page["cells"][cell_key(0, i)] = dict(item)
        data["seeded"] = sorted(set(data["seeded"]) | {n})
        changed = True
    for n, item in ADDED_CELLS:
        if item["key"] in data["added"]:
            continue
        page = data["pages"][str(n)]
        held = [c for c in page["cells"].values() if c.get("key") == item["key"]]
        if not held and page["name"] == DEFAULT_PAGES[n][0]:
            free = [c for c in range(SLOTS) if cell_key(0, c) not in page["cells"]]
            if free:
                page["cells"][cell_key(0, free[0])] = dict(item)
        data["added"] = sorted(set(data["added"]) | {item["key"]})
        changed = True
    return data, changed


def normalised(data):
    """A model to trust: one row of SLOTS cells (an older file's extra cells folded in), pages 2..12 each with a name and valid cells."""
    out = blank()
    if not isinstance(data, dict):
        return out
    seeded = data.get("seeded", list(FIRST_SEEDED))
    if isinstance(seeded, list):
        out["seeded"] = sorted(set(n for n in seeded if isinstance(n, int) and n in DEFAULT_PAGES))
    added = data.get("added", [])
    known = set(item["key"] for _n, item in ADDED_CELLS)
    if isinstance(added, list):
        out["added"] = sorted(set(k for k in added if k in known))
    pages = data.get("pages")
    if not isinstance(pages, dict):
        return out
    for n in range(2, PAGES + 1):
        page = pages.get(str(n))
        if not isinstance(page, dict):
            continue
        name = page.get("name")
        out["pages"][str(n)]["name"] = name.strip()[:24] if isinstance(name, str) else ""
        cells = page.get("cells")
        if not isinstance(cells, dict):
            continue
        kept, extra = out["pages"][str(n)]["cells"], []
        for key, item in sorted(cells.items(), key=lambda kv: (_old_key(kv[0]) or (9, 0))[::-1]):
            place = _old_key(key)
            item = clean_item(item)
            if place is None or item is None:
                continue
            if parse_key(cell_key(*place)) is not None:
                kept[cell_key(*place)] = item
            else:
                extra.append(item)          # a cell past the SLOTS: into a free one, leftmost first
        free = [c for c in range(SLOTS) if cell_key(0, c) not in kept]
        for item, c in zip(extra, free):
            kept[cell_key(0, c)] = item
    return out


def encode(data):
    return json.dumps(normalised(data), indent=1, sort_keys=True, ensure_ascii=False)


def decode(text):
    """The model in `text`; raises ValueError for text that is not ours."""
    data = json.loads(text)
    if not isinstance(data, dict) or "pages" not in data:
        raise ValueError("not a skill bar file")
    return normalised(data)


def is_skill_page(n):
    return isinstance(n, int) and 2 <= n <= PAGES


def page_of(data, n):
    return data["pages"][str(n)] if is_skill_page(n) else None


def item_at(data, n, row, col):
    page = page_of(data, n)
    return page["cells"].get(cell_key(row, col)) if page else None


def put(data, n, row, col, item):
    """A copy of `data` with `item` in the cell (None empties it)."""
    out = normalised(data)
    page = page_of(out, n)
    if page is None or parse_key(cell_key(row, col)) is None:
        return out
    item = clean_item(item) if item is not None else None
    key = cell_key(row, col)
    if item is None:
        page["cells"].pop(key, None)
    else:
        page["cells"][key] = item
    return out


def take(data, n, row, col):
    return put(data, n, row, col, None)


def swap(data, a, b):
    """A copy with the cells a=(n, row, col) and b swapped (either may be empty)."""
    first, second = item_at(data, *a), item_at(data, *b)
    out = put(data, a[0], a[1], a[2], second)
    return put(out, b[0], b[1], b[2], first)


def first_free(data, n, cols=SLOTS):
    """(0, col) of the first empty cell of page n within `cols` (at most SLOTS), or None."""
    page = page_of(data, n)
    if page is None:
        return None
    for c in range(max(1, min(SLOTS, cols))):
        if cell_key(0, c) not in page["cells"]:
            return 0, c
    return None


def put_on_page(data, n, item, cols):
    """(data, place) with `item` in page n's first free cell; place None when the page is full."""
    place = first_free(data, n, cols)
    if place is None:
        return normalised(data), None
    return put(data, n, place[0], place[1], item), place


def rename_page(data, n, name):
    out = normalised(data)
    page = page_of(out, n)
    if page is not None:
        page["name"] = (name or "").strip()[:24]
    return out


def clear_page(data, n):
    out = normalised(data)
    page = page_of(out, n)
    if page is not None:
        page["cells"] = {}
    return out


def filled(data, n):
    page = page_of(data, n)
    return len(page["cells"]) if page else 0


# ------------------------------------------------------------------ texts

def fkey(n):
    return "F%d" % n


def page_name(data, n):
    if n == TIME_PAGE:
        return "Time"
    page = page_of(data, n)
    return page["name"] if page else ""


def tab_text(data, n):
    """("F3", "Characters") - the page's key and its name ("" for an unnamed page)."""
    return fkey(n), page_name(data, n)


def initials(text, count=2):
    """The first letters of a name's words, upper case: «Knot Offset» -> «KO»."""
    words = [w for w in "".join(ch if ch.isalnum() else " " for ch in (text or "")).split() if w]
    if not words:
        return "?"
    if len(words) == 1:
        return words[0][:count].capitalize()
    return "".join(w[0] for w in words[:count]).upper()


def cell_caption(n, row, col):
    return "skill %s · cell %d" % (fkey(n), col + 1)


def drop_caption(label, aim):
    """The ghost's caption while a drag is over the bar: aim = ("cell", n, r, c) / ("tab", n) / None."""
    if not aim:
        return label
    if aim[0] == "cell":
        return "%s · %s" % (label, cell_caption(aim[1], aim[2], aim[3]))
    if aim[0] == "tab":
        return "%s · onto %s" % (label, fkey(aim[1]))
    return label


# --------------------------------------------------------------- geometry

def cell_size(height, rows=1, ui=1.0):
    """A square cell's side for `rows` rows in `height` px (the room under the page row)."""
    gap, pad = GAP * ui, PAD * ui
    side = (height - 2 * pad - gap * (rows - 1)) / float(rows)
    return max(CELL_MIN * ui, min(CELL_MAX * ui, side))


def grid_height(rows=1, ui=1.0, side=None):
    side = side if side is not None else 34 * ui
    return 2 * PAD * ui + rows * side + (rows - 1) * GAP * ui


def columns(width, side, ui=1.0):
    """How many cells fit across `width` px, at most SLOTS."""
    gap, pad = GAP * ui, PAD * ui
    room = width - 2 * pad + gap
    return max(1, min(SLOTS, int(room // (side + gap))))


def row_left(width, cols, side, ui=1.0):
    """The x where a row of `cols` cells starts so it stands in the middle of `width`."""
    gap, pad = GAP * ui, PAD * ui
    used = cols * side + (cols - 1) * gap
    return max(0.0, (width - used) / 2.0 - pad)


def cell_rect(row, col, side, ui=1.0, x0=0.0):
    """(x, y, w, h) of a cell in the grid's own px; `x0` shifts the row (row_left)."""
    gap, pad = GAP * ui, PAD * ui
    return (x0 + pad + col * (side + gap), pad + row * (side + gap), side, side)


def cell_at(x, y, rows, cols, side, ui=1.0, x0=0.0):
    """(row, col) of the cell under (x, y), or None (the gaps too)."""
    gap, pad = GAP * ui, PAD * ui
    fx, fy = x - pad - x0, y - pad
    if fx < 0 or fy < 0:
        return None
    col, row = int(fx // (side + gap)), int(fy // (side + gap))
    if col >= cols or row >= rows:
        return None
    if fx - col * (side + gap) > side or fy - row * (side + gap) > side:
        return None
    return row, col


def tab_rects(texts, measure, ui=1.0, x0=0.0):
    """[(x, w)] of the page tabs; `texts` [(key, name)], `measure(text)` its width in px."""
    out, x = [], x0
    for key, name in texts:
        w = measure(key) + 2 * TAB_PAD * ui
        if name:
            w += 5 * ui + measure(name)
        out.append((x, w))
        x += w + TAB_GAP * ui
    return out


def tab_at(x, rects):
    """The 1-based page of the tab under x, or None."""
    for i, (x0, w) in enumerate(rects):
        if x0 <= x <= x0 + w:
            return i + 1
    return None
