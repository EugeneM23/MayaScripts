"""The Longsword moveset's combo trees as data: the graph the page reads, the
shared state (statuses, assignees, people), the trees laid out. Stdlib only:
a test pins it.

The page (`mockups/design-b-v3.html` in the moveset folder) and this card read
the same two files beside each other: `graph.json` (made from the editor, never
written here) and `state.json` - the page's localStorage keys as raw strings,
written by the page through `serve.py` and by this card directly. The folder is
the animator's own (`Documents/AtoneExperiments/LongswordMoveset`); nothing of
it ships with the plugin.
"""
import collections
import json
import os
import re
import tempfile

FOLDER_VAR = "skeldarMovesetFolder"
GRAPH = "graph.json"
STATE = "state.json"
PREFIX = "longswordMoveset."
#  the chosen weapon is shared state: the card and the page read the same key
STATE_WEAPON = "weapon"
#  `graph.json` is the Longsword's, written before a graph declared its weapon
LONGSWORD = ("longsword", "Longsword")
LONGSWORD_PREFIX = "AM_Longsword_Attack_"

KIND_ORDER = ("release", "chain", "jump", "dodge", "sprint")
TYPES = (("hold", "Hold"), ("light", "Light"), ("sprint", "Sprint"),
         ("jump", "Jump"), ("dodge", "Dodge"))
COLOURS = {"hold": "#d0605e", "light": "#22b5a0", "sprint": "#e6c229",
           "jump": "#a35cf0", "dodge": "#f08a24", "chain": "#4e79ff"}
STATUSES = (("backlog", "Backlog", "#8a8f98"), ("progress", "In progress", "#e6c229"),
            ("done", "Done", "#3fbf6a"))
VIEWS = ("3p", "1p")
SITUATIONS = {"onfoot": "On foot", "sprint_short": "Sprint (just started)",
              "sprint_long": "Sprint (run-up)", "air": "In air", "dodge": "After dodge",
              "jumpwindup": "Jump wind-up", "exhausted": "Low stamina",
              "parry": "From parry"}

#  the page's layout, in its px: a column a depth, a row a leaf
COL, ROW, CARD_W, CARD_H = 236, 178, 176, 160


def default_folder():
    return os.path.join(os.path.expanduser("~"), "Documents", "AtoneExperiments",
                        "LongswordMoveset")


def attack_type(node_id):
    """The card's colour, read off the montage's name (the page's rule). The
    Longsword's names say the type in words; another weapon's graph declares it
    per node instead - see `node_type`."""
    for kind, word in (("sprint", "Sprint"), ("jump", "Jump"), ("dodge", "Dodge"),
                       ("light", "Light"), ("hold", "Hold")):
        if word in node_id:
            return kind
    return ""


def node_type(graph, node_id):
    """The attack's type: what its graph says, else its name (the sword's rule,
    and every card of the animator's own, which no graph holds)."""
    node = graph.get("nodes", {}).get(node_id) or {}
    return node.get("type") or attack_type(node_id)


def types_in(graph):
    """The rows of TYPES the graph actually holds - the dagger has no Dodge, so
    the card shows no Dodge chip."""
    held = set(node_type(graph, node_id) for node_id in graph.get("nodes", {}))
    return [(key, text) for key, text in TYPES if key in held]


def is_custom(node_id):
    return node_id.startswith("custom-")


def label(node_id, custom=(), prefix=LONGSWORD_PREFIX):
    """The card's name: the weapon's own prefix off the montage's id, as the
    project names it («NLt NLt NHd»), so it can still be searched for."""
    if is_custom(node_id):
        for card in custom:
            if card.get("id") == node_id:
                return card.get("name") or "New attack"
        return "New attack"
    for head in (prefix, "AM_"):
        if head and node_id.startswith(head):
            return node_id[len(head):].replace("_", " ")
    return node_id.replace("_", " ")


def skey(node_id, view):
    return "{0}|{1}".format(node_id, view)


def initials(name):
    return "".join(w[0] for w in name.split() if w)[:2].upper()


# ---- files -------------------------------------------------------------------

def load_graph(folder, graph=GRAPH):
    with open(os.path.join(folder, graph), encoding="utf-8") as handle:
        return json.load(handle)


# ---- the folder's weapons ----------------------------------------------------

#  key: «dagger»; label: what the card's segment says; graph: the file; media:
#  the subfolder of `media` holding its previews ("" = `media` itself); prefix:
#  what `label` strips off a node id.
Weapon = collections.namedtuple("Weapon", ["key", "label", "graph", "media", "prefix"])


def _file_key(name):
    """«graph.dagger.json» -> «dagger»; the plain «graph.json» is the Longsword's,
    written before a graph declared its weapon."""
    middle = name[len("graph."):-len(".json")]
    return middle or LONGSWORD[0]


def _weapon_in(folder, name):
    """The weapon a graph file declares, filled in where it declares nothing.
    None for a file that cannot be read - a half-written graph is not a weapon."""
    try:
        with open(os.path.join(folder, name), encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    meta = (data.get("meta") or {}).get("weapon") if isinstance(data, dict) else None
    meta = meta if isinstance(meta, dict) else {}
    plain = name == GRAPH
    key = meta.get("key") or (LONGSWORD[0] if plain else _file_key(name))
    return Weapon(key,
                  meta.get("label") or (LONGSWORD[1] if plain else key.capitalize()),
                  name,
                  meta.get("media", "" if plain else key),
                  meta.get("prefix") or (LONGSWORD_PREFIX if plain else ""))


def weapons(folder):
    """The weapons the folder holds, `graph.json` first and the rest by file
    name. The data says which weapons there are; no table here names one."""
    try:
        names = os.listdir(folder)
    except OSError:
        return []
    files = sorted(n for n in names
                   if n.startswith("graph.") and n.endswith(".json") and n != GRAPH)
    if GRAPH in names:
        files.insert(0, GRAPH)
    found = [_weapon_in(folder, name) for name in files]
    return [w for w in found if w is not None]


def weapon_of(folder, key):
    for weapon in weapons(folder):
        if weapon.key == key:
            return weapon
    return None


def chosen_weapon(state, available):
    """The weapon the shared state names, else the first one there is."""
    for weapon in available:
        if weapon.key == state.get(STATE_WEAPON):
            return weapon
    return available[0] if available else None


def _raw(folder):
    path = os.path.join(folder, STATE)
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _parsed(raw, key, empty):
    try:
        value = json.loads(raw.get(PREFIX + key, ""))
    except (TypeError, ValueError):
        return empty
    return value if isinstance(value, type(empty)) else empty


def read_state(folder):
    """What the card needs of the shared state, parsed; empty where missing."""
    raw = _raw(folder)
    return {"status": _parsed(raw, "status", {}),
            "assignee": _parsed(raw, "assignee", {}),
            "people": _parsed(raw, "people", []),
            "icons": _parsed(raw, "icons", {}),
            "custom": _parsed(raw, "custom", []),
            "hidden": _parsed(raw, "hidden", []),
            STATE_WEAPON: _parsed(raw, STATE_WEAPON, "")}


def state_mtime(folder):
    try:
        return os.path.getmtime(os.path.join(folder, STATE))
    except OSError:
        return 0.0


def write_state(folder, **values):
    """Write `values` (status=..., assignee=...) into state.json, keeping every
    other key the page wrote; atomic, so the page's server never reads half."""
    raw = _raw(folder)
    for key, value in values.items():
        raw[PREFIX + key] = json.dumps(value, ensure_ascii=False)
    path = os.path.join(folder, STATE)
    handle, temp = tempfile.mkstemp(dir=folder, suffix=".part")
    with os.fdopen(handle, "w", encoding="utf-8") as out:
        json.dump(raw, out, ensure_ascii=False, indent=1)
    os.replace(temp, path)


def set_status(state, node_id, view, status):
    """A copy of `state["status"]` with one card's status ("" = not planned)."""
    table = dict(state["status"])
    if status:
        table[skey(node_id, view)] = status
    else:
        table.pop(skey(node_id, view), None)
    return table


def set_assignee(state, node_id, view, person):
    table = dict(state["assignee"])
    if person:
        table[skey(node_id, view)] = person
    else:
        table.pop(skey(node_id, view), None)
    return table


# ---- trees -------------------------------------------------------------------

class Node(object):
    __slots__ = ("key", "id", "depth", "x", "y", "link", "via", "dirs", "parent",
                 "children", "kind")

    def __init__(self, key, node_id):
        self.key, self.id = key, node_id
        self.depth, self.x, self.y = 0, 0.0, 0.0
        self.link, self.via, self.dirs, self.parent = "", "", [], None
        self.children = []
        self.kind = attack_type(node_id)


class Tree(object):
    def __init__(self, root, titles):
        self.root, self.titles = root, titles
        self.nodes, self.wires = [], []
        self.width, self.height = 0.0, 0.0


def _kids(graph, state, mode):
    kids = {}
    for edge in graph.get("edges", []):
        kind = edge.get("kind")
        if kind == "fresh" or (mode == "combos" and kind != "chain"):
            continue
        rows = kids.setdefault(edge["from"], [])
        row = next((r for r in rows if r["to"] == edge["to"] and r["kind"] == kind), None)
        if row is None:
            row = {"to": edge["to"], "kind": kind, "dirs": []}
            rows.append(row)
        for d in edge.get("directions") or []:
            if d not in row["dirs"]:
                row["dirs"].append(d)
    for card in state["custom"]:
        if card.get("parent"):
            kids.setdefault(card["parent"], []).append({"to": card["id"], "kind": "chain", "dirs": []})
    hidden = set(state["hidden"])
    for key in kids:
        kids[key] = sorted((r for r in kids[key] if r["to"] not in hidden),
                           key=lambda r: KIND_ORDER.index(r["kind"]) if r["kind"] in KIND_ORDER else 9)
    return kids


def _roots(graph, state, mode):
    roots = {}
    order = []
    for entry in graph.get("entries", []):
        target = entry["target"]
        if target not in roots:
            roots[target] = []
            order.append(target)
        roots[target].append(SITUATIONS.get(entry["situation"], entry["situation"]))
    for card in state["custom"]:
        if not card.get("parent"):
            roots[card["id"]] = ["Custom"]
            order.append(card["id"])
    if mode == "combos":
        openers = set(e["target"] for e in graph.get("entries", []))
        for edge in graph.get("edges", []):
            if edge.get("kind") == "release" and edge["from"] in openers and edge["to"] not in roots:
                roots[edge["to"]] = ["Tap"]
                order.append(edge["to"])
    hidden = set(state["hidden"])
    return [(r, roots[r]) for r in order if r not in hidden]


def trees(graph, state, mode="combos"):
    """One Tree per opener, laid out as the page lays it: breadth-first, each
    attack expanded once a tree, later copies and loops leaf links."""
    kids = _kids(graph, state, mode)
    roots = _roots(graph, state, mode)
    root_ids = set(r for r, _t in roots)
    result = []
    counter = [0]
    for root_id, titles in roots:
        tree = Tree(root_id, sorted(set(titles), key=titles.index))
        counter[0] += 1
        top = Node("n{0}".format(counter[0]), root_id)
        expanded = {root_id}
        queue = [top]
        while queue:
            node = queue.pop(0)
            for k in kids.get(node.id, []):
                counter[0] += 1
                child = Node("n{0}".format(counter[0]), k["to"])
                if k["kind"] not in ("release", "chain") and k["to"] in root_ids:
                    child.link = "conv"
                elif k["to"] in expanded:
                    child.link = "repeat"
                else:
                    expanded.add(k["to"])
                    queue.append(child)
                child.via, child.dirs, child.parent = k["kind"], k["dirs"], node
                node.children.append(child)
        _place(tree, top)
        result.append(tree)
    return result


def _leaves(node):
    return sum(_leaves(c) for c in node.children) if node.children else 1


def _place(tree, top):
    def place(node, depth, row_top):
        node.depth = depth
        node.x = depth * COL
        node.y = row_top + (_leaves(node) - 1) * ROW / 2.0
        tree.nodes.append(node)
        tree.width = max(tree.width, node.x + CARD_W)
        cur = row_top
        lanes = len(node.children)
        for lane, child in enumerate(node.children):
            place(child, depth + 1, cur)
            tree.wires.append((node, child, lane, lanes))
            cur += _leaves(child) * ROW
    place(top, 0, 0.0)
    tree.height = _leaves(top) * ROW - 18


def kept(tree, state, types=(), who=None):
    """The keys of the cards a type / assignee filter keeps: a match, the path
    up to the root, and everything under it. None when nothing filters."""
    types = set(types)
    if not types and who is None:
        return None
    keep = set()

    def matches(node):
        if types and node.kind not in types:
            return False
        if who is not None:
            names = [state["assignee"].get(skey(node.id, v)) for v in VIEWS]
            if who == "":
                return not all(names)
            return who in names
        return True

    def under(node):
        keep.add(node.key)
        for c in node.children:
            under(c)

    for node in tree.nodes:
        if matches(node):
            under(node)
            p = node.parent
            while p is not None:
                keep.add(p.key)
                p = p.parent
    return keep


# ---- one node's data, for the Open press --------------------------------------

def package_of(path):
    """«/Game/A/AM_X.AM_X» -> «/Game/A/AM_X»: the montage list's package."""
    return path.split(".", 1)[0] if path else ""


def slot_of(graph, node_id, view):
    """The montage's slot for a view: the graph's own, else None."""
    node = graph.get("nodes", {}).get(node_id) or {}
    return node.get("slot1p" if view == "1p" else "slot") or None


def thumbnail(folder, node_id, view="3p", media=""):
    """The preview, from the weapon's own subfolder of `media` ("" = `media`
    itself, the Longsword's). "" when the file is not there - a weapon whose
    previews have not been rendered yet draws cards without them."""
    where = os.path.join(folder, "media", media) if media else os.path.join(folder, "media")
    if view == "1p":
        path = os.path.join(where, "1p", node_id + ".jpg")
        if os.path.isfile(path):
            return path
    path = os.path.join(where, node_id + ".jpg")
    return path if os.path.isfile(path) else ""
