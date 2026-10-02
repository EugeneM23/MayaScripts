"""Unity projects read off the disk - no editor, no plugin. stdlib only.

2026-10-02, the animator: «возможность подключаться не только к анриал
енжину а и к Unity». Unity keeps everything a listing needs in text:

- **Unity Hub's recent projects**: `%APPDATA%/UnityHub/projects-v1.json`
  (measured on this machine: `{"schema_version": "v1", "data": {path:
  {"title", "path", "version", "lastModified", ...}}}`, one project listed
  twice under two spellings of the drive letter - `c:\\` and `C:\\`).
- **An open project**: the editor writes `Library/EditorInstance.json`
  (`process_id`) while it runs; a project is "open" when that pid is alive.
  No command line of another process is read.
- **A model's clips**: `<file>.meta`, YAML; `ModelImporter.animations.
  clipAnimations` lists each clip the animator split a take into - `name`,
  `takeName`, `firstFrame`, `lastFrame` (frames of the file's own rate);
  empty means Unity's default, one clip per take.
- **An AnimationClip** (`.anim`, YAML): GENERIC clips carry transform
  curves by hierarchy path (`m_RotationCurves` quaternions,
  `m_PositionCurves`, `m_ScaleCurves`, `m_EulerCurves`), each key a Hermite
  point (`time`, `value`, `inSlope`, `outSlope`); a HUMANOID clip carries
  MUSCLE curves (`m_FloatCurves` with empty paths and attributes like
  `RootT.x`, `Spine Front-Back`) that only Unity's avatar can turn into
  bones - refused by name.

Unity is LEFT-handed: its FBX import negates X. A Unity value becomes a
Maya one by negating it back (`to_maya_position` / `to_maya_rotation`).

The YAML read here is Unity's own dialect, line-based and indentation-
driven; this is a reader of exactly the keys above, not a YAML library.
"""

import json
import os
import re

HUB_PROJECTS = os.path.join("UnityHub", "projects-v1.json")
MODEL_EXTENSIONS = (".fbx", ".dae")          # Unity's model files we can import
ANIM_EXTENSION = ".anim"
MUSCLE_MARKERS = ("RootT.", "RootQ.", "Front-Back", "Left-Right", "Twist Left",
                  "In-Out", "Stretch", "Down-Up", "Close", "Open")

HUMANOID = ("a Humanoid muscle clip - Unity's avatar turns it into bones; "
            "export it as FBX from Unity")
COMPRESSED = "a compressed clip - untick Anim. Compression in Unity, or export FBX"


class UnityError(ValueError):
    """A Unity file we cannot read honestly."""


# ------------------------------------------------------------------ projects

def hub_projects(appdata=None):
    """Unity Hub's recent projects [(title, path, version, modified)], most
    recently modified first, one per folder (the drive letter's case does
    not make two). Missing or broken file: []."""
    appdata = appdata if appdata is not None else os.environ.get("APPDATA", "")
    try:
        with open(os.path.join(appdata, HUB_PROJECTS), "r", encoding="utf-8") as h:
            payload = json.load(h)
    except (OSError, IOError, ValueError):
        return []
    return projects_from_hub(payload)


def projects_from_hub(payload):
    """The pure half of `hub_projects`."""
    seen, out = set(), []
    data = (payload or {}).get("data") or {}
    rows = sorted(data.values(), key=lambda p: -(p.get("lastModified") or 0))
    for project in rows:
        path = project.get("path") or ""
        key = os.path.normcase(os.path.normpath(path))
        if not path or key in seen:
            continue
        seen.add(key)
        out.append((project.get("title") or os.path.basename(path), path,
                    project.get("version") or "", project.get("lastModified") or 0))
    return out


def editor_pid(project):
    """The pid in `<project>/Library/EditorInstance.json`, or None."""
    try:
        with open(os.path.join(project, "Library", "EditorInstance.json"),
                  "r", encoding="utf-8") as handle:
            return int(json.load(handle).get("process_id"))
    except (OSError, IOError, ValueError, TypeError):
        return None


def pid_alive(pid):
    """True while a process with that id runs (Windows: OpenProcess)."""
    if not pid:
        return False
    try:
        import ctypes
        kernel = ctypes.windll.kernel32
        handle = kernel.OpenProcess(0x1000, False, int(pid))   # QUERY_LIMITED
        if not handle:
            return False
        code = ctypes.c_ulong()
        kernel.GetExitCodeProcess(handle, ctypes.byref(code))
        kernel.CloseHandle(handle)
        return code.value == 259                                # STILL_ACTIVE
    except Exception:                                           # noqa: BLE001
        return False


def is_open(project):
    return pid_alive(editor_pid(project))


def is_project(path):
    """A folder Unity would open: Assets/ and ProjectSettings/ in it."""
    return (os.path.isdir(os.path.join(path, "Assets"))
            and os.path.isdir(os.path.join(path, "ProjectSettings")))


# ------------------------------------------------------------------ yaml bits

def _scalar(text):
    text = text.strip()
    if text.startswith(("'", '"')) and text.endswith(text[0]) and len(text) > 1:
        return text[1:-1]
    return text


def number(text):
    """A Unity YAML number: `.5`, `-.25`, `Infinity`, `-Infinity`. Pure."""
    text = text.strip()
    try:
        return float(text)
    except ValueError:
        low = text.lower()
        if low in ("infinity", "inf"):
            return float("inf")
        if low in ("-infinity", "-inf"):
            return float("-inf")
        raise


def flow(text):
    """`{x: 1, y: .5, z: 0}` -> {"x": 1.0, ...}. Pure."""
    body = text.strip().strip("{}")
    out = {}
    for part in body.split(","):
        if ":" in part:
            key, value = part.split(":", 1)
            try:
                out[key.strip()] = number(value)
            except ValueError:
                out[key.strip()] = value.strip()
    return out


def meta_clips(text):
    """The `clipAnimations` of a model's .meta: [(name, takeName,
    firstFrame, lastFrame)]. Pure; [] when the list is empty or absent."""
    lines = text.splitlines()
    out = []
    start = None
    for i, line in enumerate(lines):
        if line.strip() == "clipAnimations:":
            start, indent = i + 1, len(line) - len(line.lstrip())
            break
        if line.strip().startswith("clipAnimations: []"):
            return []
    if start is None:
        return []
    current = None
    for line in lines[start:]:
        if not line.strip():
            continue
        depth = len(line) - len(line.lstrip())
        stripped = line.strip()
        if depth < indent or (depth == indent and not stripped.startswith("-")):
            break
        if stripped.startswith("- ") and depth == indent:
            if current:
                out.append(current)
            current = {}
            stripped = stripped[2:]
        if current is None or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        if key in ("name", "takeName", "firstFrame", "lastFrame") and key not in current:
            current[key] = _scalar(value)
    if current:
        out.append(current)
    clips = []
    for c in out:
        try:
            clips.append((c.get("name") or "", c.get("takeName") or "",
                          number(c.get("firstFrame", "0")),
                          number(c.get("lastFrame", "0"))))
        except ValueError:
            continue
    return clips


def meta_value(text, key):
    """The first `key: value` in a .meta, or None. Pure."""
    match = re.search(r"^\s*" + re.escape(key) + r":\s*(.*)$", text, re.M)
    return _scalar(match.group(1)) if match else None


# ------------------------------------------------------------------ .anim

_SECTIONS = {"m_RotationCurves": "r", "m_PositionCurves": "t",
             "m_ScaleCurves": "s", "m_EulerCurves": "e"}


def anim_summary(text):
    """What a list row says about an .anim, cheaply: {"name", "rate",
    "start", "stop", "kind" ("generic" / "humanoid" / "compressed" /
    "empty"), "paths"}. Pure."""
    name = meta_value(text, "m_Name") or ""
    rate = meta_value(text, "m_SampleRate")
    start = meta_value(text, "m_StartTime")
    stop = meta_value(text, "m_StopTime")
    paths = set(re.findall(r"^\s{4}path:\s*(.*)$", text, re.M))
    curves = any(re.search(r"^  " + s + r":\s*$", text, re.M) for s in _SECTIONS)
    compressed = meta_value(text, "m_Compressed") == "1"
    humanoid = bool(re.search(r"attribute:\s*(RootT|RootQ|MotionT|MotionQ)\.", text)) \
        or any(("attribute: " + m) in text for m in MUSCLE_MARKERS[2:])
    if compressed:
        kind = "compressed"
    elif curves:
        kind = "generic"
    elif humanoid:
        kind = "humanoid"
    else:
        kind = "empty"
    try:
        rate = number(rate) if rate is not None else None
        start = number(start) if start is not None else None
        stop = number(stop) if stop is not None else None
    except ValueError:
        rate = start = stop = None
    return {"name": _scalar(name), "rate": rate, "start": start, "stop": stop,
            "kind": kind, "paths": sorted(p.strip() for p in paths)}


def anim_curves(text):
    """Every transform curve of a GENERIC .anim: {path: {"r"/"t"/"s"/"e":
    [(time, value tuple, in slope tuple, out slope tuple)]}}. Pure."""
    out = {}
    section = None
    keys, path, key = [], None, None
    for line in text.splitlines():
        stripped = line.strip()
        depth = len(line) - len(line.lstrip())
        if depth == 2 and stripped and not stripped.startswith("-"):
            section = _SECTIONS.get(stripped.split(":", 1)[0])
            continue
        if section is None:
            continue
        if stripped.startswith("- curve:"):
            keys, path, key = [], None, None
            continue
        if stripped.startswith("- serializedVersion:") and depth >= 6:
            key = {}                    # a newer key: its time follows
            keys.append(key)
            continue
        if stripped.startswith("- time:") or stripped.startswith("time:"):
            at = number(stripped.split(":", 1)[1])
            if stripped.startswith("time:") and key is not None and "time" not in key:
                key["time"] = at
            else:
                key = {"time": at}
                keys.append(key)
            continue
        if key is not None and stripped.startswith(("value:", "inSlope:", "outSlope:")):
            field, value = stripped.split(":", 1)
            key[field] = flow(value)
            continue
        if stripped.startswith("path:") and depth == 4:
            path = _scalar(stripped.split(":", 1)[1])
            axes = ("x", "y", "z", "w") if section == "r" else ("x", "y", "z")
            rows = []
            for k in keys:
                if "time" not in k or "value" not in k:
                    continue
                rows.append((k["time"],
                             tuple(k["value"].get(a, 0.0) for a in axes),
                             tuple(k.get("inSlope", {}).get(a, 0.0) for a in axes),
                             tuple(k.get("outSlope", {}).get(a, 0.0) for a in axes)))
            out.setdefault(path, {})[section] = rows
            keys, key = [], None
    return out


def hermite(rows, at):
    """A Unity curve's value at time `at`: per component, cubic Hermite
    between the two keys around it from their slopes; an infinite slope is
    a step. Pure."""
    if not rows:
        return None
    if at <= rows[0][0]:
        return rows[0][1]
    if at >= rows[-1][0]:
        return rows[-1][1]
    for k in range(len(rows) - 1):
        t0, v0, _i0, o0 = rows[k]
        t1, v1, i1, _o1 = rows[k + 1]
        if t0 <= at <= t1:
            break
    dt = t1 - t0
    if dt <= 0:
        return v1
    u = (at - t0) / dt
    h00 = 2 * u ** 3 - 3 * u ** 2 + 1
    h10 = u ** 3 - 2 * u ** 2 + u
    h01 = -2 * u ** 3 + 3 * u ** 2
    h11 = u ** 3 - u ** 2
    out = []
    for a, b, m0, m1 in zip(v0, v1, o0, i1):
        if m0 in (float("inf"), float("-inf")) or m1 in (float("inf"), float("-inf")):
            out.append(a)
            continue
        out.append(h00 * a + h10 * dt * m0 + h01 * b + h11 * dt * m1)
    return tuple(out)


def to_maya_position(p, units=1.0):
    """A Unity localPosition -> Maya's (X negated back), scaled. Pure."""
    return (-p[0] * units, p[1] * units, p[2] * units)


def to_maya_rotation(q):
    """A Unity localRotation (x, y, z, w) -> the same rotation in Maya's
    right-handed frame: X mirrored, so y and z flip sign. Pure."""
    n = sum(c * c for c in q) ** 0.5 or 1.0
    return (q[0] / n, -q[1] / n, -q[2] / n, q[3] / n)


def unity_euler_quat(e):
    """Unity's euler degrees (applied Z, then X, then Y) as a Unity
    quaternion (x, y, z, w). Pure."""
    import math

    def axis(a, deg):
        h = math.radians(deg) / 2.0
        s = math.sin(h)
        return (s if a == 0 else 0.0, s if a == 1 else 0.0, s if a == 2 else 0.0,
                math.cos(h))

    def mul(a, b):        # Hamilton product a*b (b applied first)
        ax, ay, az, aw = a
        bx, by, bz, bw = b
        return (aw * bx + ax * bw + ay * bz - az * by,
                aw * by - ax * bz + ay * bw + az * bx,
                aw * bz + ax * by - ay * bx + az * bw,
                aw * bw - ax * bx - ay * by - az * bz)
    # Unity: q = qY * qX * qZ (Z applied first)
    return mul(axis(1, e[1]), mul(axis(0, e[0]), axis(2, e[2])))


def leaves_in_bytes(data, leaves):
    """How many of the hierarchy leaves appear as names in a model file's
    raw bytes - a cheap test that a model carries a clip's bones. Pure."""
    found = 0
    for leaf in leaves:
        if leaf and leaf.encode("utf-8") in data:
            found += 1
    return found
