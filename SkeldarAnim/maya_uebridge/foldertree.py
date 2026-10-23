"""Animation Setup's list as a folder tree (2026-10-23).

The animator: «сделать режим в котором я буду видеть структуру папок». The tree
is drawn as rows of the same Maya list (`window._repopulate`), so the selection,
the drag and the import keep working; a folder row only opens and closes.

Pure: stdlib and `records` only, so it is testable with no Maya at all.
"""

import collections
import json
import re

from maya_uebridge import records

MODE_VAR = "ueAnimBridgeListMode"        # "list" / "folders"
OPEN_VAR = "ueAnimBridgeOpenFolders"     # JSON [[place key, [folder paths]], ...]
MODES = ("list", "folders")
MAX_PLACES = 20
OPEN_MARK = "▾"
CLOSED_MARK = "▸"
INDENT = "  "

Row = collections.namedtuple("Row", "kind depth path label record count opened")


class Node(object):
    """One folder: its own name, its path from the top, its subfolders (by
    lower-case name), the animations right in it, and how many below it."""

    def __init__(self, name, path):
        self.name = name
        self.path = path
        self.folders = {}
        self.anims = []
        self.count = 0


def _slashed(path):
    return (path or "").replace("\\", "/")


def folder_of(record, root=""):
    """The folder `record` lives in, slashes forward, "" for the top.

    Unreal: the package without its last part (`/Game/A/Walk` -> `Game/A`).
    A file (Unity, a folder): its folder relative to `root`, the project or
    the chosen folder; outside `root` its whole folder."""
    if record.source == "unreal" or not record.path:
        package = (record.package or "").lstrip("/")
        return package.rsplit("/", 1)[0] if "/" in package else ""
    path = _slashed(record.path)
    folder = path.rsplit("/", 1)[0] if "/" in path else ""
    base = _slashed(root).rstrip("/")
    if base:
        if folder.lower() == base.lower():
            return ""
        if folder.lower().startswith(base.lower() + "/"):
            return folder[len(base) + 1:]
    return folder


def _clean(path):
    """`path` with forward slashes and no trailing slash ("" stays "")."""
    text = _slashed(path)
    return text.rstrip("/") if text.strip("/") else text


def disk_path(row, source, root, content_dir):
    """Where the list row `row` lives on disk, "" when it has no place.

    A folder: Unreal's `Game/<rest>` under `content_dir` (another mount, or no
    `content_dir` from an old cache, has none); a file source's under `root`
    (the chosen folder, the Unity project). An animation: its uasset, or its
    file. Slashes forward, no trailing slash."""
    if row is None:
        return ""
    if row.kind != "folder":
        record = row.record
        if record is None:
            return ""
        if source == "unreal" or not record.path:
            if not content_dir:
                return ""
            return _clean(records.uasset_path_of(record.package, content_dir))
        return _clean(record.path)
    if source == "unreal":
        parts = [p for p in _slashed(row.path).split("/") if p]
        if not content_dir or not parts or parts[0].lower() != "game":
            return ""
        base = _clean(content_dir)
        return "/".join([base] + parts[1:])
    if not root:
        return ""
    base = _clean(root)
    rest = _slashed(row.path).strip("/")
    return base + "/" + rest if rest else base


_BAD_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_DEVICES = set(["CON", "PRN", "AUX", "NUL"]
               + ["COM%d" % n for n in range(1, 10)]
               + ["LPT%d" % n for n in range(1, 10)])


def safe_file_name(text, ext, allowed=()):
    """A file name from what the animator typed: whitespace collapsed, a typed
    `ext` (or one of `allowed`, which then wins) not doubled, Windows'
    forbidden characters as "_", leading and trailing dots and spaces gone, a
    device name prefixed with "_", nothing at all named "animation"."""
    name = " ".join((text or "").split())
    chosen = ext
    for known in tuple(allowed) + (ext,):
        if name.lower().endswith(known.lower()):
            name = name[:-len(known)]
            chosen = known.lower()
            break
    name = _BAD_NAME.sub("_", name).strip(". ")
    if not name:
        name = "animation"
    if name.split(".")[0].strip().upper() in _DEVICES:
        name = "_" + name
    return name + chosen


def build(record_list, root=""):
    """The tree of `record_list`: a nameless top node."""
    top = Node("", "")
    for record in record_list:
        node = top
        for part in [p for p in folder_of(record, root).split("/") if p]:
            key = part.lower()
            if key not in node.folders:
                node.folders[key] = Node(
                    part, node.path + "/" + part if node.path else part)
            node = node.folders[key]
        node.anims.append(record)
    _count(top)
    return top


def _count(node):
    node.count = len(node.anims) + sum(_count(c) for c in node.folders.values())
    return node.count


def rows(tree, open_paths=None):
    """The rows top down. A chain of folders holding one folder and no
    animation is one row, named by the chain and kept by its deepest path.
    `open_paths` None opens every folder (a search shows its matches)."""
    out = []

    def walk(node, depth):
        for child in sorted(node.folders.values(), key=lambda n: n.name.lower()):
            label = child.name
            while len(child.folders) == 1 and not child.anims:
                only = next(iter(child.folders.values()))
                label += "/" + only.name
                child = only
            opened = open_paths is None or child.path in open_paths
            out.append(Row("folder", depth, child.path, label, None,
                           child.count, opened))
            if opened:
                walk(child, depth + 1)
        for record in sorted(node.anims, key=lambda r: r.name.lower()):
            out.append(Row("anim", depth, "", record.name, record, 1, False))

    walk(tree, 0)
    return out


def row_text(row):
    """The list's line: a folder's arrow, name and count; an animation under
    its folder's name, then its length."""
    pad = INDENT * row.depth
    if row.kind == "folder":
        mark = OPEN_MARK if row.opened else CLOSED_MARK
        return "{0}{1} {2}  ({3})".format(pad, mark, row.label, row.count)
    record = row.record
    frames = "{0} fr".format(record.frames) if record.frames is not None else ""
    return "{0}{1}{2:<{3}} {4}".format(
        pad, INDENT, records._middle(record.name, records.NAME_WIDTH),
        records.NAME_WIDTH, frames).rstrip()


def toggled(open_paths, path):
    """`open_paths` with `path` opened when it was closed, closed when open."""
    paths = set(open_paths or ())
    if path in paths:
        paths.discard(path)
    else:
        paths.add(path)
    return paths


def place_key(source, place):
    """Which memory a list uses: its source and its project / folder."""
    return "{0}:{1}".format(source, _slashed(place).lower())


def _pairs(text):
    try:
        data = json.loads(text or "[]")
    except (TypeError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    out = []
    for item in data:
        if (isinstance(item, list) and len(item) == 2
                and isinstance(item[0], str) and isinstance(item[1], list)):
            out.append((item[0], [p for p in item[1] if isinstance(p, str)]))
    return out


def read_open(text, key):
    """The open folders the memory `text` keeps for `key`; a broken or
    missing memory is none."""
    for name, paths in _pairs(text):
        if name == key:
            return set(paths)
    return set()


def write_open(text, key, paths):
    """`text` with `key`'s open folders set; the place goes last, and only
    the last MAX_PLACES places are kept."""
    pairs = [(name, p) for name, p in _pairs(text) if name != key]
    pairs.append((key, sorted(paths)))
    return json.dumps([[name, p] for name, p in pairs[-MAX_PLACES:]])
