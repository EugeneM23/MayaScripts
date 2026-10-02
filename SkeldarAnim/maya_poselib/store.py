"""maya_poselib.store - the pose library on disk. Stdlib only.

A CARD is a folder `<Name>.pose/` holding `pose.json` (the pose) and `thumbnail.jpg`; a CATALOG
is a plain folder, nested as deep as the animator likes. Files, not a database: a colleague
receives the library with the build and the animator commits it from the repo. The library root
is the optionVar `skeldarPoseLibraryRoot` when it names a folder, else `<plugin>/poses/`.

The rules this module keeps, so the window above it can be simple:
  - every path it returns uses "/" (Windows takes both; the cards, the tree and the details
    text then compare equal);
  - a card is written ATOMICALLY (`pose.json.part`, then `os.replace`) and a card that fails
    half way is not left behind, so a reader never sees a half file;
  - nothing is deleted: `remove` moves a card or a folder into a trash folder, stamped;
  - a card that cannot be read is REPORTED (`cards` returns it in `broken`), never raised, so
    one bad file from a colleague's merge does not blank the library;
  - what `write` / `make_folder` can name, `cards` / `folders` can list: names that the walk
    skips (`.git`, `_trash...`) and names that would read as a card are refused up front.

No `maya`, no Qt, no clock but `time` for stamps: the pure halves (`safe_name`, `filter_cards`,
`sort_cards`) are plain tests.

Spec: docs/superpowers/specs/2026-10-02-pose-library-design.md
"""

import json
import os
import re
import shutil
import time
from collections import namedtuple

ROOT_VAR = "skeldarPoseLibraryRoot"   # the optionVar holding the library folder
CARD_SUFFIX = ".pose"
POSE_FILE = "pose.json"
THUMB_FILE = "thumbnail.jpg"
FORMAT = "skeldar.pose"
VERSION = 1
SORTS = ("name", "newest", "character")

NAME_MAX = 80                         # a card's or a folder's name, before its suffix
TRASH_PREFIX = "_trash"               # folders starting with this (or ".") are never listed
TRASH_FOLDER = "SkeldarPoses_trash"   # under the Maya user folder, outside any library

_BAD_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_DEVICES = set(["CON", "PRN", "AUX", "NUL"]
               + ["COM%d" % i for i in range(1, 10)]
               + ["LPT%d" % i for i in range(1, 10)])

#  What the grid and the details show of a card, read once per refresh: `label` is the source
#  character's catalog label ("Manny [rig]") or "objects"; `count` the bones (or objects) the
#  pose holds; `thumbnail` the image's path or "" when the card has none.
Card = namedtuple("Card", "path folder name created author label kind count regions thumbnail")


# ---------------------------------------------------------------- paths and names

def _fwd(path):
    """`path` with forward slashes and no trailing one (a drive or filesystem root keeps its own,
    so "C:/" never turns into the drive-relative "C:")."""
    text = (path or "").replace("\\", "/")
    trimmed = text.rstrip("/")
    if not trimmed or trimmed.endswith(":"):
        return text
    return trimmed


def default_root(plugin_dir):
    """The library inside the plugin: `<plugin>/poses`."""
    return plugin_dir.replace("\\", "/").rstrip("/") + "/poses"


def library_root(option_value, plugin_dir):
    """The library folder: the optionVar's value when it names an existing folder (the animator
    points it at the repo's `SkeldarAnim/poses` once, so an install never touches their poses),
    else the plugin's own."""
    if option_value and os.path.isdir(option_value):
        return _fwd(option_value)
    return default_root(plugin_dir)


def safe_name(text, fallback="Pose"):
    """A name a card or a folder can wear on Windows: whitespace collapsed, the characters
    Windows forbids (and control characters) turned into "_", leading dots and trailing dots
    and spaces dropped (Windows drops those silently, and the name then no longer matches),
    capped at 80, a device name (CON, NUL, COM1 ...) prefixed - no file may be called that.
    Empty comes back as `fallback`."""
    text = " ".join((text or "").split())
    text = _BAD_NAME.sub("_", text)
    text = text.lstrip(". ")
    text = text[:NAME_MAX].rstrip(". ")
    if not text:
        return fallback
    if text.split(".")[0].strip().upper() in _DEVICES:
        text = ("_" + text)[:NAME_MAX].rstrip(". ")
    return text


def _is_card(name):
    """True for a folder name that is a card (`Fist.pose`)."""
    return name.lower().endswith(CARD_SUFFIX)


def _hidden(name):
    """True for a folder the library never lists or descends into: `.git`, a trash kept inside
    the library (`_trash...`)."""
    return name.startswith(".") or name.lower().startswith(TRASH_PREFIX)


def _folder_name(name):
    """A catalog's own name, safe - or ValueError when the library could not list it again."""
    leaf = safe_name(name, fallback="Folder")
    if _is_card(leaf):
        raise ValueError("a folder cannot end with %s" % CARD_SUFFIX)
    if _hidden(leaf):
        raise ValueError("a name cannot start with %s" % TRASH_PREFIX)
    return leaf


def _clean_folder(folder):
    """`folder` (relative, "/" or "\\" separated) as a clean relative path - or ValueError for
    anything that would leave the library or that the walk would never show: "..", a drive, a
    hidden name, a card."""
    parts = [part for part in (folder or "").replace("\\", "/").split("/") if part]
    for part in parts:
        if part in (".", "..") or ":" in part or _hidden(part) or _is_card(part):
            raise ValueError("not a library folder: %r" % (folder,))
    return "/".join(parts)


def _abs(root, folder):
    """The folder on the disk (`folder` already clean)."""
    return _fwd(root) + ("/" + folder if folder else "")


def _same(a, b):
    """True when two paths name one place (a case-insensitive disk included)."""
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def _iso(stamp):
    """An epoch time as the card's ISO text (local time, to the second)."""
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(stamp))


def unique_name(root, folder, name):
    """`name` made safe and free in `folder`: "Fist", then "Fist 2", "Fist 3" ..."""
    folder = _clean_folder(folder)
    base = safe_name(name)
    here = _abs(root, folder)
    if not os.path.exists(here + "/" + base + CARD_SUFFIX):
        return base
    number = 2
    while True:
        suffix = " %d" % number
        candidate = base[:NAME_MAX - len(suffix)].rstrip(". ") + suffix
        if not os.path.exists(here + "/" + candidate + CARD_SUFFIX):
            return candidate
        number += 1


# ---------------------------------------------------------------- walking the library

def _scan(root, folder="", recursive=True):
    """Yield `(relative folder, [subfolder names], [card folder names])` for `folder` and, when
    `recursive`, every catalog below it, parents first, each level sorted case-insensitively.
    A card is never descended into; hidden folders and symbolic links are skipped (a link
    could loop). A folder that is not there yields nothing."""
    base = _abs(root, folder)
    try:
        names = sorted(os.listdir(base), key=str.lower)
    except OSError:
        return
    subs, found = [], []
    for name in names:
        path = base + "/" + name
        if _hidden(name) or os.path.islink(path) or not os.path.isdir(path):
            continue
        (found if _is_card(name) else subs).append(name)
    yield folder, subs, found
    if recursive:
        for name in subs:
            yield from _scan(root, folder + "/" + name if folder else name, True)


def folders(root):
    """Every catalog under `root` as a relative "/" path - "A", "A/B" - sorted case-insensitively
    with a catalog's children right after it; never "" (the root itself) and never a card."""
    found = [rel for rel, _subs, _cards in _scan(root) if rel]
    return sorted(found, key=lambda rel: [part.lower() for part in rel.split("/")])


# ---------------------------------------------------------------- reading cards

def read(path):
    """The pose dict of the card at `path`. ValueError when the file is missing, is not JSON or
    is not one of ours - the caller shows the animator which card, nothing else breaks."""
    target = _fwd(path) + "/" + POSE_FILE
    try:
        with open(target, encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except OSError as exc:
        raise ValueError("%s: cannot be read (%s)" % (target, exc))
    except ValueError as exc:       # a JSON error, or bytes that are not UTF-8
        raise ValueError("%s: not a pose file (%s)" % (target, exc))
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise ValueError("%s: not a %s file" % (target, FORMAT))
    return data


def _card(path, folder, name):
    """The `Card` for the card folder at `path` (ValueError when it cannot be read). The name is
    the FOLDER's: the card is addressed by its path, so a rename done in Explorer shows at once."""
    data = read(path)
    try:
        kind = str(data.get("kind") or "character")
        if kind == "character":
            label = str((data.get("character") or {}).get("label") or "")
            count = len(data.get("members") or [])
        else:
            label = "objects"
            count = len(data.get("objects") or [])
        created = str(data.get("created") or _iso(os.path.getmtime(path)))
        regions = [str(region) for region in (data.get("regions") or [])]
        author = str(data.get("author") or "")
    except (AttributeError, TypeError, OSError) as exc:
        raise ValueError("%s: unreadable fields (%s)" % (path, exc))
    image = path + "/" + THUMB_FILE
    return Card(path, folder, name, created, author, label, kind, count, regions,
                image if os.path.isfile(image) else "")


def cards(root, folder="", recursive=True):
    """`(cards, broken)`: every readable card in `folder` (and below, when `recursive`), by
    folder then name, and the paths of the cards that could not be read."""
    folder = _clean_folder(folder)
    found, broken = [], []
    for rel, _subs, names in _scan(root, folder, recursive):
        for name in names:
            path = _abs(root, rel) + "/" + name
            try:
                found.append(_card(path, rel, name[:-len(CARD_SUFFIX)]))
            except ValueError:
                broken.append(path)
    found.sort(key=lambda card: (card.folder.lower(), card.name.lower()))
    return found, broken


# ---------------------------------------------------------------- writing cards

def _write_json(card, data):
    """`data` into `card`'s pose.json: written whole to a `.part` file, then swapped in. Compact
    on purpose - this is machine data (hundreds of floats a bone), not a file to read."""
    target = card + "/" + POSE_FILE
    part = target + ".part"
    try:
        with open(part, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, separators=(",", ":"))
        os.replace(part, target)
    except BaseException:
        try:
            os.remove(part)
        except OSError:
            pass
        raise


def _copy_atomic(source, target):
    """`source` copied (with its times) over `target` through a `.part` file."""
    part = target + ".part"
    try:
        shutil.copy2(source, part)
        os.replace(part, target)
    except BaseException:
        try:
            os.remove(part)
        except OSError:
            pass
        raise


def write(root, folder, name, data, thumbnail=None, replace=False):
    """Write a card `<name>.pose` into `folder` of the library and answer its path. `data` is
    copied (the caller's dict is not touched) and gets the card's own `name` (the safe one, so
    the file and the card always agree) and, if missing, `format` / `version`. `thumbnail` is
    the path of an image to copy in. An existing card is refused unless `replace` - then its
    pose is swapped and its thumbnail kept unless a new one is given. A card that fails half
    way is removed again."""
    folder = _clean_folder(folder)
    name = safe_name(name)
    if _hidden(name):
        raise ValueError("a name cannot start with %s" % TRASH_PREFIX)
    card = _abs(root, folder) + "/" + name + CARD_SUFFIX
    existed = os.path.isdir(card)
    if existed and not replace:
        raise ValueError("%s already exists in %s" % (name, folder or "the library"))
    data = dict(data)
    data.setdefault("format", FORMAT)
    data.setdefault("version", VERSION)
    data["name"] = name
    os.makedirs(card, exist_ok=True)
    try:
        if thumbnail:
            _copy_atomic(thumbnail, card + "/" + THUMB_FILE)
        _write_json(card, data)         # last: a reader sees pose.json only when the card is whole
    except BaseException:
        if not existed:
            shutil.rmtree(card, ignore_errors=True)
        raise
    return card


def set_thumbnail(path, image):
    """Replace the thumbnail of the card at `path` with the image file `image`."""
    _copy_atomic(image, _fwd(path) + "/" + THUMB_FILE)


def _rename_dir(old, new):
    """Rename a folder to `new`; ValueError when that is taken by another. Renaming to the same
    name does nothing; a change of case alone (one place on a case-insensitive disk) is done."""
    if _same(old, new):
        if os.path.abspath(old) != os.path.abspath(new):
            os.rename(old, new)
        return
    if os.path.exists(new):
        raise ValueError("%s already exists" % os.path.basename(new))
    os.rename(old, new)


def rename(path, name):
    """Rename the card at `path` to `name` (made safe): the folder AND the `name` inside the
    file. ValueError for a taken name (or an unreadable card, before anything moves). Answers
    the new path."""
    path = _fwd(path)
    new = safe_name(name)
    if _hidden(new):
        raise ValueError("a name cannot start with %s" % TRASH_PREFIX)
    data = read(path)
    target = _fwd(os.path.dirname(path)) + "/" + new + CARD_SUFFIX
    _rename_dir(path, target)
    data["name"] = new
    _write_json(target, data)
    return target


def move(path, root, folder):
    """Move the card at `path` into the catalog `folder` of the library `root` (which must
    exist); ValueError when a card of that name is already there. Answers the new path."""
    path = _fwd(path)
    folder = _clean_folder(folder)
    where = _abs(root, folder)
    if not os.path.isdir(where):
        raise ValueError("no folder %r in the library" % (folder,))
    target = where + "/" + os.path.basename(path)
    if _same(path, target):
        return target
    if os.path.exists(target):
        raise ValueError("%s already has %s" % (folder or "the library",
                                                os.path.basename(path)[:-len(CARD_SUFFIX)]))
    shutil.move(path, target)
    return target


def trash_dir(user_app_dir):
    """The trash folder for a Maya user folder: beside the animator's prefs, outside every
    library, so an install and a `git status` never see it."""
    return _fwd(user_app_dir) + "/" + TRASH_FOLDER


def remove(path, trash):
    """Delete the card (or catalog) at `path` the safe way: moved into `trash` under a name
    stamped with the time (`20261002_181530_Fist.pose`), so a mistake is a move back. Answers
    where it went."""
    path = _fwd(path)
    trash = _fwd(trash)
    os.makedirs(trash, exist_ok=True)
    base = "%s_%s" % (time.strftime("%Y%m%d_%H%M%S"), os.path.basename(path))
    stem, suffix = (base[:-len(CARD_SUFFIX)], CARD_SUFFIX) if _is_card(base) else (base, "")
    target = trash + "/" + base
    number = 2
    while os.path.exists(target):       # two removals of one name in a second
        target = "%s/%s_%d%s" % (trash, stem, number, suffix)
        number += 1
    shutil.move(path, target)
    return target


# ---------------------------------------------------------------- catalogs

def make_folder(root, parent, name):
    """Make the catalog `name` (made safe) inside `parent` ("" for the top). Answers its
    relative path; ValueError when it is there already, or `parent` is not. The library folder
    itself is made on first use."""
    parent = _clean_folder(parent)
    leaf = _folder_name(name)
    rel = parent + "/" + leaf if parent else leaf
    if parent and not os.path.isdir(_abs(root, parent)):
        raise ValueError("no folder %r in the library" % (parent,))
    if os.path.exists(_abs(root, rel)):
        raise ValueError("%s already exists" % rel)
    os.makedirs(_abs(root, rel))
    return rel


def rename_folder(root, rel, name):
    """Rename the catalog `rel` to `name` (made safe), staying under the same parent. Answers
    the new relative path; ValueError for the library root, a missing folder or a taken name."""
    rel = _clean_folder(rel)
    if not rel:
        raise ValueError("the library folder itself cannot be renamed")
    leaf = _folder_name(name)
    parent = rel.rpartition("/")[0]
    new = parent + "/" + leaf if parent else leaf
    old_path = _abs(root, rel)
    if not os.path.isdir(old_path):
        raise ValueError("no folder %r in the library" % (rel,))
    _rename_dir(old_path, _abs(root, new))
    return new


# ---------------------------------------------------------------- search and sort

def filter_cards(cards, query):
    """The cards matching `query`: every whitespace-separated term must occur, case-insensitively,
    in the card's name, folder or character label ("fist creep" narrows to Creep's fists)."""
    terms = (query or "").lower().split()
    if not terms:
        return list(cards)
    kept = []
    for card in cards:
        hay = ("%s %s %s" % (card.name, card.folder, card.label)).lower()
        if all(term in hay for term in terms):
            kept.append(card)
    return kept


def sort_cards(cards, key):
    """`cards` ordered by one of `SORTS`: `name` A-Z; `newest` the latest `created` first (a tie
    by name); `character` by the source's label, then name. ValueError for another key."""
    if key not in SORTS:
        raise ValueError("sort by one of %s, not %r" % (", ".join(SORTS), key))
    if key == "name":
        return sorted(cards, key=lambda card: card.name.lower())
    if key == "newest":
        by_name = sorted(cards, key=lambda card: card.name.lower())
        return sorted(by_name, key=lambda card: card.created, reverse=True)
    return sorted(cards, key=lambda card: (card.label.lower(), card.name.lower()))
