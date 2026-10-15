"""Scene tabs: the session as data (stdlib only; a subprocess test pins it).

Spec: docs/superpowers/specs/2026-10-15-scene-tabs-design.md (and its addendum).
Every tab is a scene file imported into a namespace of its own. What the scene
code needs to decide without Maya lives here: a tab's namespace, a file's fps
and ranges, the session's JSON, which nodes are Maya's furniture, what a Save
means, and what the bar shows.
"""

import json
import os
import re

import maya_sharerecords

SESSION_NODE = "skeldarSceneTabs"
SESSION_ATTR = "skeldarSceneTabs"
#  Maya keeps ONE root animation layer and remembers it internally; deleting it
#  left the other layers rootless and the next new layer crashed mayapy
#  (measured 2026-10-15). So the session owns the root while tabs are on.
LAYER_ROOT = "skeldarTabsLayerRoot"
TAB_LAYER_ROOT = "AnimLayerRoot"      # Maya's own rename of an imported BaseAnimation
FILE_LAYER_ROOT = "BaseAnimation"
CONFIG_NODE = "sceneConfigurationScriptNode"
CONFIG_SCRIPT_TYPE = 6                # what Maya writes for its configuration node
WORKSPACE_PREFIX = "SkeldarTab_"
TAB_PREFIX = "tab_"
UNTITLED = "untitled"
VERSION = 1
SYSTEM_NAMESPACES = ("UI", "shared")
FILE_TYPES = {".ma": "mayaAscii", ".mb": "mayaBinary"}
RANGE_KEYS = ("minTime", "maxTime", "animationStartTime", "animationEndTime")
_RANGE_FLAGS = (("min", "minTime"), ("max", "maxTime"),
                ("ast", "animationStartTime"), ("aet", "animationEndTime"))

#  The scene's own managers: an import makes copies of them inside the tab's
#  namespace (they clashed with the root's on the first save, measured), and a
#  tab never moves them.
FURNITURE_TYPES = frozenset((
    "lightLinker", "partition", "renderLayer", "renderLayerManager",
    "displayLayerManager", "ikSolver", "ikRPsolver", "ikSCsolver",
    "ikSplineSolver", "ikSystem", "shapeEditorManager", "poseInterpolatorManager",
    "UsdDefaultSettings", "nodeGraphEditorInfo", "hyperLayout", "hyperView",
    "hyperGraphInfo", "time", "sequenceManager", "defaultRenderUtilityList",
    "defaultShaderList", "defaultTextureList", "defaultLightList"))
FURNITURE_NAMES = frozenset(("uiConfigurationScriptNode", "defaultLayer",
                             "sharedReferenceNode"))

_ILLEGAL = re.compile(r"[^A-Za-z0-9_]")
_UNIT_MA = re.compile(r"currentUnit\b[^;]*?-t(?:ime)?\s+([A-Za-z0-9_.]+)")
_UNIT = re.compile(r"^[A-Za-z0-9_.]+$")


# ------------------------------------------------------------------ names

def namespace_for(path, taken):
    """`tab_<stem>`, made legal and free among `taken` (with or without a
    leading colon). The prefix keeps a tab from BEING a namespace its own rig
    moves into on a save (a tab opened from assets/Manny_Rig.ma)."""
    stem = os.path.splitext(os.path.basename(path or ""))[0] or UNTITLED
    base = TAB_PREFIX + _ILLEGAL.sub("_", stem)
    used = set(t.lstrip(":") for t in taken or ())
    if base not in used:
        return base
    number = 1
    while "%s%d" % (base, number) in used:
        number += 1
    return "%s%d" % (base, number)


# ------------------------------------------------------------------ a file's time

def unit_from_ma(text):
    """The time unit of a `.ma` header (`currentUnit ... -t ntsc;`), or ""."""
    match = _UNIT_MA.search(text or "")
    return match.group(1) if match else ""


def unit_from_mb(data):
    """The time unit of a `.mb` header: the TUNI chunk (measured 2026-10-15:
    the tag, 4 bytes, an 8-byte big-endian size, the name), or ""."""
    at = (data or b"").find(b"TUNI")
    if at < 0 or len(data) < at + 16:
        return ""
    size = int.from_bytes(data[at + 8:at + 16], "big")
    if not 0 < size <= 32:
        return ""
    raw = data[at + 16:at + 16 + size].split(b"\0")[0]
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError:
        return ""
    return text if _UNIT.match(text) else ""


def read_unit(path, head=65536):
    """A scene file's time unit read from its header, or "" (unknown kind,
    unreadable, no unit line)."""
    try:
        with open(path, "rb") as handle:
            data = handle.read(head)
    except OSError:
        return ""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".ma":
        return unit_from_ma(data.decode("utf-8", "replace"))
    if ext == ".mb":
        return unit_from_mb(data)
    return ""


def ranges_from_script(text):
    """The playback and animation ranges in a configuration node's MEL,
    parsed, never evaluated."""
    found = maya_sharerecords.playback_from_script(text)
    return {key: found[key] for key in RANGE_KEYS if key in found}


def _number(value):
    text = ("%.6f" % float(value)).rstrip("0").rstrip(".")
    return text if text not in ("", "-0") else "0"


def config_script(ranges):
    """The MEL a tab's configuration node carries into its file."""
    parts = ["-%s %s" % (flag, _number(ranges[key]))
             for flag, key in _RANGE_FLAGS if key in (ranges or {})]
    return ("playbackOptions %s ;" % " ".join(parts)) if parts else ""


def range_text(ranges):
    ranges = ranges or {}
    if "minTime" not in ranges or "maxTime" not in ranges:
        return "?"
    return "%s-%s" % (_number(ranges["minTime"]), _number(ranges["maxTime"]))


def is_furniture(leaf, node_type):
    """A node of the scene's own, never a tab's."""
    return node_type in FURNITURE_TYPES or leaf in FURNITURE_NAMES


# ------------------------------------------------------------------ the session

def empty_state():
    return {"version": VERSION, "active": "", "session": "", "tabs": []}


def new_tab(namespace, path, unit, ranges, mtime=0.0):
    return {"ns": namespace, "path": path or "", "mtime": float(mtime or 0.0),
            "unit": unit or "", "ranges": dict(ranges or {}), "frame": None,
            "modified": False, "layout": WORKSPACE_PREFIX + namespace,
            "views": [], "selection": []}


def dumps(state):
    return json.dumps(state, sort_keys=True)


def loads(text):
    """The state in a session node, or an empty one for anything else."""
    try:
        state = json.loads(text or "")
    except ValueError:
        return empty_state()
    if not isinstance(state, dict) or state.get("version") != VERSION \
            or not isinstance(state.get("tabs"), list):
        return empty_state()
    out = empty_state()
    for item in state["tabs"]:
        if not isinstance(item, dict) or not item.get("ns"):
            continue
        tab = new_tab(item["ns"], item.get("path"), item.get("unit"),
                      item.get("ranges"), item.get("mtime"))
        for key in ("frame", "modified", "layout", "views", "selection"):
            if key in item:
                tab[key] = item[key]
        out["tabs"].append(tab)
    names = [t["ns"] for t in out["tabs"]]
    out["active"] = state.get("active") if state.get("active") in names else (names[0] if names else "")
    out["session"] = state.get("session") or ""
    return out


def tab(state, namespace):
    for item in state["tabs"]:
        if item["ns"] == namespace:
            return item
    return None


def with_tab(state, item, index=None):
    """A new state holding `item`: in its old place when the namespace is
    there, else at `index` (the end by default)."""
    out = dict(state, tabs=list(state["tabs"]))
    for position, old in enumerate(out["tabs"]):
        if old["ns"] == item["ns"]:
            out["tabs"][position] = item
            return out
    if index is None:
        out["tabs"].append(item)
    else:
        out["tabs"].insert(index, item)
    return out


def neighbour(state, namespace):
    """The tab that takes over when `namespace` closes: the right-hand one,
    else the left-hand one, else none."""
    names = [t["ns"] for t in state["tabs"]]
    if namespace not in names:
        return state.get("active", "")
    at = names.index(namespace)
    if at + 1 < len(names):
        return names[at + 1]
    return names[at - 1] if at > 0 else ""


def removed(state, namespace):
    out = dict(state, tabs=[t for t in state["tabs"] if t["ns"] != namespace])
    if state.get("active") == namespace:
        out["active"] = neighbour(state, namespace)
    return out


def title(item):
    stem = os.path.splitext(os.path.basename(item.get("path") or ""))[0] or UNTITLED
    return stem + ("*" if item.get("modified") else "")


def bar_items(state, scene_name="", scene_modified=False):
    """What the bar shows: one item per tab, or the one open scene."""
    if not state["tabs"]:
        stem = os.path.splitext(os.path.basename(scene_name or ""))[0] or UNTITLED
        return [{"ns": "", "text": stem + ("*" if scene_modified else ""),
                 "tip": scene_name or "not saved yet", "active": True, "closable": False}]
    items = []
    for item in state["tabs"]:
        active = item["ns"] == state["active"]
        modified = bool(item.get("modified") or (active and scene_modified))
        items.append({"ns": item["ns"], "text": title(dict(item, modified=modified)),
                      "tip": "%s\n%s, %s" % (item.get("path") or "not saved yet",
                                              item.get("unit") or "?", range_text(item.get("ranges"))),
                      "active": active, "closable": True})
    return items


# ------------------------------------------------------------------ saving

def same_file(first, second):
    norm = lambda p: os.path.normcase(os.path.normpath(p or ""))    # noqa: E731
    return bool(first and second) and norm(first) == norm(second)


def save_plan(target, session_name):
    """What Maya's Save means while tabs are on: the session's own name (or
    none) is Save (the active tab into its own file); any other name is Save As."""
    if not target or same_file(target, session_name):
        return "save", ""
    return "save_as", target


def is_autosave(target, folder):
    if not target or not folder:
        return False
    norm = lambda p: os.path.normcase(os.path.normpath(p))          # noqa: E731
    return norm(target).startswith(norm(folder).rstrip("\\/") + os.sep)


def changed_on_disk(path, mtime):
    """The file was written by somebody else since the tab read or saved it."""
    if not mtime or not path or not os.path.isfile(path):
        return False
    return abs(os.path.getmtime(path) - float(mtime)) > 1e-3


def holds_session(path, chunk=1 << 22):
    """The file holds a session node: a session saved by autosave or a crash."""
    needle = SESSION_NODE.encode("ascii")
    tail = b""
    try:
        with open(path, "rb") as handle:
            while True:
                data = handle.read(chunk)
                if not data:
                    return False
                if needle in tail + data:
                    return True
                tail = data[-len(needle):]
    except OSError:
        return False


def session_name(folder, stamp):
    return "%s/session_%s.ma" % (folder.replace("\\", "/").rstrip("/"), stamp)
