"""Scene tabs: the session as data (stdlib only; a subprocess test pins it).

Spec: docs/superpowers/specs/2026-10-15-scene-tabs-design.md (and its addendum).
Every tab is a scene file imported into a namespace of its own. What the scene
code needs to decide without Maya lives here: a tab's namespace, a file's fps
and ranges, the session's JSON, which nodes are Maya's furniture, what a Save
means, and what the bar shows.
"""

import json
import math
import os
import re
import struct

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


# ------------------------------------------------------------------ a tab's own cameras

#  2026-10-16, the animator: «камеры перспективы и других направлений общие для всех
#  вкладок». The startup cameras are the scene's, one persp for every tab: an import leaves
#  them as they are and a tab's export wrote none (measured). So each tab keeps what they
#  showed in it: in its record, read from its file when it opens, written into its file on
#  a save. Values are kept CANONICAL here (cm, degrees) and in the scene's units in a record.
STARTUP_CAMERAS = ("persp", "top", "front", "side")
#  (short name in a file, long name, which node, kind): "linear" scales with the linear
#  unit, "angle" with the angle unit, "plain" with neither (tumblePivot is a plain
#  double3 - measured: attributeQuery answers double3 of doubles, the files write it as is)
CAMERA_ATTRS = (
    ("t", "translate", "transform", "linear"),
    ("r", "rotate", "transform", "angle"),
    ("fl", "focalLength", "shape", "plain"),
    ("coi", "centerOfInterest", "shape", "linear"),
    ("ow", "orthographicWidth", "shape", "linear"),
    ("ncp", "nearClipPlane", "shape", "linear"),
    ("fcp", "farClipPlane", "shape", "linear"),
    ("tp", "tumblePivot", "shape", "plain"),
    ("hfa", "horizontalFilmAperture", "shape", "plain"),
    ("vfa", "verticalFilmAperture", "shape", "plain"),
    ("ovr", "overscan", "shape", "plain"),
)
_KIND = {long_name: kind for _short, long_name, _node, kind in CAMERA_ATTRS}
_LONG = {short: long_name for short, long_name, _node, _kind in CAMERA_ATTRS}


def _camera(translate, rotate, coi, ow):
    return {"translate": list(translate), "rotate": list(rotate), "focalLength": 35.0,
            "centerOfInterest": coi, "orthographicWidth": ow, "nearClipPlane": 0.1,
            "farClipPlane": 10000.0, "tumblePivot": [0.0, 0.0, 0.0],
            "horizontalFilmAperture": 1.41732, "verticalFilmAperture": 0.94488, "overscan": 1.0}


#  Maya's own startup cameras in a new scene (measured in mayapy 2027, cm and degrees)
DEFAULT_CAMERAS = {
    "persp": _camera((28.0, 21.0, 28.0), (-27.93835272960238, 45.0, 0.0), 44.82186966202994, 10.0),
    "top": _camera((0.0, 1000.1, 0.0), (-90.0, 0.0, 0.0), 1000.1, 30.0),
    "front": _camera((0.0, 0.0, 1000.1), (0.0, 0.0, 0.0), 1000.1, 30.0),
    "side": _camera((1000.1, 0.0, 0.0), (0.0, 90.0, 0.0), 1000.1, 30.0),
}

_CM = {"mm": 0.1, "millimeter": 0.1, "cm": 1.0, "centimeter": 1.0, "m": 100.0, "meter": 100.0,
       "km": 100000.0, "kilometer": 100000.0, "in": 2.54, "inch": 2.54, "ft": 30.48, "foot": 30.48,
       "yd": 91.44, "yard": 91.44, "mi": 160934.4, "mile": 160934.4}
_DEGREES = {"deg": 1.0, "degree": 1.0, "rad": 180.0 / math.pi, "radian": 180.0 / math.pi,
            "min": 1.0 / 60.0, "sec": 1.0 / 3600.0}
_UNIT_LINEAR = re.compile(r"currentUnit\b[^;]*?-l(?:inear)?\s+([A-Za-z]+)")
_UNIT_ANGLE = re.compile(r"currentUnit\b[^;]*?-a(?:ngle)?\s+([A-Za-z]+)")
_CREATE = re.compile(r"^\s*createNode\s+(\w+)\s+([^;]*);")
_FLAG_NAME = re.compile(r'-n\s+"([^"]+)"')
_FLAG_PARENT = re.compile(r'-p\s+"([^"]+)"')
_SET_ATTR = re.compile(r'^\s*setAttr\s+(?:-\w+(?:\s+(?:on|off|yes|no|true|false))?\s+)*"\.(\w+)"\s+'
                       r'(?:-type\s+"double3"\s+)?([-+0-9.eE ]+?)\s*;\s*$')


def _scaled(long_name, value, linear, angle):
    """`value` times the factor its kind takes (a list element by element)."""
    factor = {"linear": linear, "angle": angle}.get(_KIND.get(long_name), 1.0)
    if isinstance(value, (list, tuple)):
        return [float(v) * factor for v in value]
    return float(value) * factor


def _numbers(text):
    try:
        values = [float(part) for part in text.split()]
    except ValueError:
        return None
    if len(values) == 1:
        return values[0]
    return values if len(values) == 3 else None


def cameras_from_ma(text):
    """{camera: {long name: value}} of a `.ma`'s startup cameras, in cm and degrees,
    only what the file writes (it leaves defaults out). The cameras are the file's
    first nodes: the read stops at the first other node after them. Pure."""
    text = text or ""
    found = _UNIT_LINEAR.search(text)
    linear = _CM.get(found.group(1), 1.0) if found else 1.0
    found = _UNIT_ANGLE.search(text)
    angle = _DEGREES.get(found.group(1), 1.0) if found else 1.0
    out, owner, seen = {}, None, False
    for line in text.splitlines():
        created = _CREATE.match(line)
        if created:
            flags = created.group(2)
            name = _FLAG_NAME.search(flags)
            parent = _FLAG_PARENT.search(flags)
            shared = re.search(r"(^|\s)-s(\s|$)", flags) is not None
            owner = None
            if shared and created.group(1) == "transform" and name and name.group(1) in STARTUP_CAMERAS:
                owner = name.group(1)
            elif shared and created.group(1) == "camera" and parent and parent.group(1) in STARTUP_CAMERAS:
                owner = parent.group(1)
            if owner is None and seen:
                break
            seen = seen or owner is not None
            continue
        if owner is None:
            continue
        match = _SET_ATTR.match(line)
        if not match or match.group(1) not in _LONG:
            continue
        value = _numbers(match.group(2))
        if value is None:
            continue
        long_name = _LONG[match.group(1)]
        out.setdefault(owner, {})[long_name] = _scaled(long_name, value, linear, angle)
    return out


def _pad8(size):
    return ((size + 7) // 8) * 8


def cameras_from_mb(data):
    """{camera: {long name: value}} of a `.mb`'s startup cameras, in cm and degrees.
    The layout as measured on Maya 2027's files: a node is a FOR8 group of type XFRM
    (a transform) or DCAM (a camera shape) whose first chunk is CREA (a flag byte, the
    name, a shape's parent, the uuid); its attributes follow, DBLE (a double) and DBL3
    (three), each a tag, 4 flag bytes, an 8-byte big-endian size and the body (the
    attribute's name, a flag byte, the doubles), padded to 8. A binary file holds
    internal units whatever the scene's: cm, and radians for rotations. Pure."""
    data = data or b""
    out = {}
    at = 0
    while True:
        at = data.find(b"CREA", at)
        if at < 0:
            return out
        size = int.from_bytes(data[at + 8:at + 16], "big")
        if not 0 < size < 4096 or at < 4:
            at += 4
            continue
        kind = data[at - 4:at]
        strings = data[at + 17:at + 16 + size].split(b"\0")
        owner = None
        if kind == b"XFRM" and strings[0].decode("ascii", "replace") in STARTUP_CAMERAS:
            owner = strings[0].decode("ascii")
        elif kind == b"DCAM" and len(strings) > 1 \
                and strings[1].decode("ascii", "replace") in STARTUP_CAMERAS:
            owner = strings[1].decode("ascii")
        at = at + 16 + _pad8(size)
        if owner is None:
            continue
        values = out.setdefault(owner, {})
        spot = at
        while spot + 16 <= len(data):
            tag = data[spot:spot + 4]
            if tag in (b"FOR8", b"FOR4", b"LIS8", b"LIS4", b"CREA"):
                break
            chunk = int.from_bytes(data[spot + 8:spot + 16], "big")
            if chunk <= 0 or chunk > 1 << 20:
                break
            body = data[spot + 16:spot + 16 + chunk]
            name = body.split(b"\0")[0].decode("ascii", "replace")
            payload = body[len(name) + 2:]
            if name in _LONG and tag in (b"DBLE", b"DBL3"):
                count = 1 if tag == b"DBLE" else 3
                if len(payload) >= 8 * count:
                    numbers = struct.unpack(">%dd" % count, payload[:8 * count])
                    value = numbers[0] if count == 1 else list(numbers)
                    long_name = _LONG[name]
                    values[long_name] = _scaled(long_name, value, 1.0, 180.0 / math.pi)
            spot += 16 + _pad8(chunk)


def with_defaults(found):
    """Maya's defaults with what a file holds over them, every startup camera."""
    out = {}
    for name in STARTUP_CAMERAS:
        camera = {k: (list(v) if isinstance(v, list) else v) for k, v in DEFAULT_CAMERAS[name].items()}
        camera.update((found or {}).get(name) or {})
        out[name] = camera
    return out


def read_cameras(path, head=1 << 18):
    """A scene file's startup cameras (cm, degrees), its defaults where the file says
    nothing or cannot be read."""
    try:
        with open(path, "rb") as handle:
            data = handle.read(head)
    except OSError:
        return with_defaults({})
    ext = os.path.splitext(path)[1].lower()
    if ext == ".ma":
        return with_defaults(cameras_from_ma(data.decode("utf-8", "replace")))
    if ext == ".mb":
        return with_defaults(cameras_from_mb(data))
    return with_defaults({})


def cameras_in_units(cameras, linear="cm", angle="deg"):
    """Canonical cameras (cm, degrees) in the scene's units, as getAttr answers."""
    lin = 1.0 / _CM.get(linear, 1.0)
    ang = 1.0 / _DEGREES.get(angle, 1.0)
    return {name: {k: _scaled(k, v, lin, ang) for k, v in values.items()}
            for name, values in (cameras or {}).items()}


def foreign_camera(path, namespace, tabs):
    """A camera of another tab than `namespace` (a model panel looking through it
    shows a hidden tab). Pure."""
    leaf = (path or "").split("|")[-1]
    if ":" not in leaf:
        return False
    owner = leaf.lstrip(":").split(":")[0]
    return owner != namespace and owner in set(tabs or ())


# ------------------------------------------------------------------ the session

def empty_state():
    return {"version": VERSION, "active": "", "session": "", "tabs": []}


def new_tab(namespace, path, unit, ranges, mtime=0.0):
    return {"ns": namespace, "path": path or "", "mtime": float(mtime or 0.0),
            "unit": unit or "", "ranges": dict(ranges or {}), "frame": None,
            "modified": False, "views": [], "selection": [], "cameras": {},
            "camera_curves": {}}


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
        for key in ("frame", "modified", "views", "selection", "cameras", "camera_curves"):
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


def is_emergency(target, temp):
    """Maya's own emergency / crash save: straight into the temp folder (not
    a folder inside it - a tool's working files live there), or a name with
    `[Recovered` / `Recovered-` in it (trap 148:
    `%TEMP%/Manny_Rig[Recovered-MY PC.2026-10-01-11.55].ma`). Let through
    like an autosave."""
    if not target:
        return False
    target = target.replace("\\", "/")
    name = os.path.basename(target)
    if "[Recovered" in name or "Recovered-" in name:
        return True
    if not temp:
        return False
    norm = lambda p: os.path.normcase(os.path.normpath(p))          # noqa: E731
    return norm(os.path.dirname(target)) == norm(temp)


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


_SESSION_FILE = re.compile(r"^session_\d{8}_\d{6}\.ma$", re.IGNORECASE)


def is_session_file(path, folder):
    """`path` is a session file of ours (`<folder>/session_<stamp>.ma`). Maya
    cannot make a scene untitled again (`file -rename ""` names it `scenes/`),
    so an untitled scene that went into tabs and came back to one keeps the
    session's name - the scene is untitled all the same (2026-10-15). Pure."""
    if not path or not folder:
        return False
    norm = lambda p: os.path.normcase(os.path.normpath(p))          # noqa: E731
    return (norm(os.path.dirname(path)) == norm(folder)
            and bool(_SESSION_FILE.match(os.path.basename(path))))
