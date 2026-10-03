"""maya_poselib.store - the pose library on disk. Stdlib only.

Two kinds of CARD, side by side in the same library and catalogs:
  - a POSE, a folder `<Name>.pose/` holding `pose.json` (the pose) and `thumbnail.jpg`;
  - an ANIMATION (2026-10-03), a folder `<Name>.anim/` (Studio Library's suffix) holding
    `anim.json` (the HEADER - small, read by every listing), `frames.json.gz` (the per-frame
    data, gzip of compact JSON - read only by Apply, Blend and Update, `read_frames`),
    `thumbnail.jpg` (the still) and `preview.jpg` (the sprite sheet a card plays on hover).
A CATALOG is a plain folder, nested as deep as the animator likes. Files, not a database: a
colleague receives the library with the build and the animator commits it from the repo. The
library root is the optionVar `skeldarPoseLibraryRoot` when it names a folder, else
`<plugin>/poses/`.

The rules this module keeps, so the window above it can be simple:
  - every path it returns uses "/" (Windows takes both; the cards, the tree and the details
    text then compare equal);
  - a card is written ATOMICALLY (each file through `<file>.part`, then `os.replace`), its
    main file (`pose.json` / `anim.json`) LAST, and a card that fails half way is not left
    behind, so a reader never sees a half card;
  - a name is free in a folder only when NEITHER suffix holds it, so a pose and an animation
    never share a name there;
  - nothing is deleted: `remove` moves a card or a folder into a trash folder, stamped;
  - a card that cannot be read is REPORTED (`cards` returns it in `broken`), never raised, so
    one bad file from a colleague's merge does not blank the library;
  - what `write` / `make_folder` can name, `cards` / `folders` can list: names that the walk
    skips (`.git`, `_trash...`) and names that would read as a card are refused up front.

No `maya`, no Qt, no clock but `time` for stamps: the pure halves (`safe_name`, `filter_cards`,
`sort_cards`, `of_type`) are plain tests.

Spec: docs/superpowers/specs/2026-10-02-pose-library-design.md,
      docs/superpowers/specs/2026-10-03-pose-library-animation-design.md
"""

import gzip
import json
import os
import re
import shutil
import time
import zlib
from collections import namedtuple

ROOT_VAR = "skeldarPoseLibraryRoot"   # the optionVar holding the library folder
CARD_SUFFIX = ".pose"
ANIM_SUFFIX = ".anim"
CARD_SUFFIXES = (CARD_SUFFIX, ANIM_SUFFIX)
POSE_FILE = "pose.json"
ANIM_FILE = "anim.json"               # an animation card's header
FRAMES_FILE = "frames.json.gz"        # an animation card's per-frame data
THUMB_FILE = "thumbnail.jpg"
PREVIEW_FILE = "preview.jpg"          # an animation card's sprite sheet
FORMAT = "skeldar.pose"
ANIM_FORMAT = "skeldar.anim"
VERSION = 1
SORTS = ("name", "newest", "character")
TYPES = ("all", "pose", "anim")       # the window's type filter (`of_type`)

NAME_MAX = 80                         # a card's or a folder's name, before its suffix
TRASH_PREFIX = "_trash"               # folders starting with this (or ".") are never listed
TRASH_FOLDER = "SkeldarPoses_trash"   # under the Maya user folder, outside any library

_BAD_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_DEVICES = set(["CON", "PRN", "AUX", "NUL"]
               + ["COM%d" % i for i in range(1, 10)]
               + ["LPT%d" % i for i in range(1, 10)])

#  What the grid and the details show of a card, read once per refresh: `label` is the source
#  character's catalog label ("Manny [rig]") or "objects"; `count` the bones (or objects) the
#  card holds; `thumbnail` the image's path or "" when the card has none. The last six are an
#  animation's (2026-10-03) and DEFAULTED, so every positional construction of the ten above
#  keeps working: `type` "pose" | "anim", `frames` the clip's frame count (0 for a pose),
#  `preview` the sprite sheet's path or "", `fps` the time unit string ("ntsc"), `start` /
#  `end` the source frames.
Card = namedtuple("Card", "path folder name created author label kind count regions thumbnail "
                          "type frames preview fps start end",
                  defaults=("pose", 0, "", "", 0.0, 0.0))


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
    """True for a folder name that is a card of either type (`Fist.pose`, `Walk.anim`)."""
    return name.lower().endswith(CARD_SUFFIXES)


def card_suffix(path):
    """The card suffix of the card folder at `path`: ".anim" for an animation, else ".pose" (a
    trailing slash and either slash style are fine)."""
    return ANIM_SUFFIX if _fwd(path).lower().endswith(ANIM_SUFFIX) else CARD_SUFFIX


def is_anim(path):
    """True when `path` is an animation card (`<Name>.anim`)."""
    return card_suffix(path) == ANIM_SUFFIX


def _main_file(path):
    """The card's main file name - the one written last and read by every listing."""
    return ANIM_FILE if is_anim(path) else POSE_FILE


def _format_of(path):
    """The `format` the card's main file must carry."""
    return ANIM_FORMAT if is_anim(path) else FORMAT


def _stem(name):
    """A card folder's name without its suffix (`Walk.anim` -> `Walk`)."""
    return name[:-len(card_suffix(name))] if _is_card(name) else name


def _taken(here, name):
    """True when the folder `here` already holds a card called `name` of EITHER type - a pose
    and an animation never share a name in one folder."""
    return any(os.path.exists(here + "/" + name + suffix) for suffix in CARD_SUFFIXES)


def _hidden(name):
    """True for a folder the library never lists or descends into: `.git`, a trash kept inside
    the library (`_trash...`)."""
    return name.startswith(".") or name.lower().startswith(TRASH_PREFIX)


def _folder_name(name):
    """A catalog's own name, safe - or ValueError when the library could not list it again."""
    leaf = safe_name(name, fallback="Folder")
    if _is_card(leaf):
        raise ValueError("a folder cannot end with %s" % " or ".join(CARD_SUFFIXES))
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
    """`name` made safe and free in `folder`: "Fist", then "Fist 2", "Fist 3" ... - free of
    BOTH types, so a pose and an animation never share a name."""
    folder = _clean_folder(folder)
    base = safe_name(name)
    here = _abs(root, folder)
    if not _taken(here, base):
        return base
    number = 2
    while True:
        suffix = " %d" % number
        candidate = base[:NAME_MAX - len(suffix)].rstrip(". ") + suffix
        if not _taken(here, candidate):
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
    """The main dict of the card at `path` - a pose card's pose, an animation card's HEADER (its
    frames stay in `frames.json.gz`, `read_frames`). ValueError when the file is missing, is not
    JSON or is not one of ours (an `.anim` folder must carry `skeldar.anim`, a `.pose` one
    `skeldar.pose`) - the caller shows the animator which card, nothing else breaks."""
    target = _fwd(path) + "/" + _main_file(path)
    expected = _format_of(path)
    try:
        with open(target, encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except OSError as exc:
        raise ValueError("%s: cannot be read (%s)" % (target, exc))
    except ValueError as exc:       # a JSON error, or bytes that are not UTF-8
        raise ValueError("%s: not a %s file (%s)" % (target, expected, exc))
    if not isinstance(data, dict) or data.get("format") != expected:
        raise ValueError("%s: not a %s file" % (target, expected))
    return data


#  `read_frames`' cache: ONE entry, {(path, mtime_ns, size): data}. An Apply, a Blend preview and
#  an Update read the same card's frames again and again; a library of many clips must not keep
#  every one of them in memory.
_FRAMES = {}


def read_frames(path):
    """The per-frame data of the animation card at `path`: {"bones": [leaf...], "world":
    [[q7 per bone] per frame], "drive": {leaf: [[q7] per frame]}} decoded from its
    `frames.json.gz`. Cached - one entry, keyed by the file's path, time and size, so a card
    written again is read again; the answer is the cached object, read it, never change it.
    ValueError when the file is missing, is not gzip JSON or is not that shape."""
    target = _fwd(path) + "/" + FRAMES_FILE
    try:
        stat = os.stat(target)
    except OSError as exc:
        raise ValueError("%s: cannot be read (%s)" % (target, exc))
    key = (os.path.normcase(os.path.abspath(target)), stat.st_mtime_ns, stat.st_size)
    if key in _FRAMES:
        return _FRAMES[key]
    try:
        with gzip.open(target, "rt", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, EOFError, zlib.error, ValueError) as exc:
        #  not gzip, cut short, a damaged stream, not JSON
        raise ValueError("%s: not an animation's frames (%s)" % (target, exc))
    if not (isinstance(data, dict) and isinstance(data.get("bones"), list)
            and isinstance(data.get("world"), list)
            and isinstance(data.get("drive", {}), dict)):
        raise ValueError("%s: not an animation's frames" % target)
    _FRAMES.clear()
    _FRAMES[key] = data
    return data


def _card(path, folder, name):
    """The `Card` for the card folder at `path` (ValueError when it cannot be read). The name is
    the FOLDER's: the card is addressed by its path, so a rename done in Explorer shows at once.
    An animation's header adds its frame count, range, time unit and preview sheet."""
    data = read(path)
    anim = is_anim(path)
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
        if anim:
            frames = int(data.get("frames") or 0)
            start = float(data.get("start") or 0.0)
            end = float(data.get("end") or 0.0)
            fps = str(data.get("fps") or "")
    except (AttributeError, TypeError, OSError) as exc:
        raise ValueError("%s: unreadable fields (%s)" % (path, exc))
    image = path + "/" + THUMB_FILE
    thumbnail = image if os.path.isfile(image) else ""
    if not anim:
        return Card(path, folder, name, created, author, label, kind, count, regions, thumbnail)
    sheet = path + "/" + PREVIEW_FILE
    return Card(path, folder, name, created, author, label, kind, count, regions, thumbnail,
                "anim", frames, sheet if os.path.isfile(sheet) else "", fps, start, end)


def cards(root, folder="", recursive=True):
    """`(cards, broken)`: every readable card in `folder` (and below, when `recursive`), by
    folder then name, and the paths of the cards that could not be read."""
    folder = _clean_folder(folder)
    found, broken = [], []
    for rel, _subs, names in _scan(root, folder, recursive):
        for name in names:
            path = _abs(root, rel) + "/" + name
            try:
                found.append(_card(path, rel, _stem(name)))
            except ValueError:
                broken.append(path)
    found.sort(key=lambda card: (card.folder.lower(), card.name.lower()))
    return found, broken


# ---------------------------------------------------------------- writing cards

def _dump_json(part, data):
    """`data` as compact JSON into the file `part`. Compact on purpose - this is machine data
    (hundreds of floats a bone), not a file to read."""
    with open(part, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, separators=(",", ":"))


def _dump_frames(part, frames):
    """`frames` as compact JSON, gzipped, into the file `part` (level 6: zlib's own default -
    nearly level 9's size on float text, in a fraction of its time)."""
    with gzip.open(part, "wt", encoding="utf-8", compresslevel=6) as handle:
        json.dump(frames, handle, ensure_ascii=False, separators=(",", ":"))


def _write_json(card, data):
    """`data` into `card`'s main file (`pose.json` / `anim.json`): written whole to a `.part`
    file, then swapped in."""
    target = card + "/" + _main_file(card)
    part = target + ".part"
    try:
        _dump_json(part, data)
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


def write(root, folder, name, data, thumbnail=None, replace=False, frames=None, preview=None):
    """Write a card into `folder` of the library and answer its path: `<name>.anim` when
    `data["format"]` is `ANIM_FORMAT` (an animation's header), else `<name>.pose`. `data` is
    copied (the caller's dict is not touched) and gets the card's own `name` (the safe one, so
    the file and the card always agree) and, if missing, `format` / `version`. `thumbnail` and
    `preview` are paths of images to copy in, `frames` an animation's per-frame data (written
    as `frames.json.gz`); a pose card given either of the last two is refused before anything
    is written.

    A name is taken when a card of EITHER type wears it: refused. An existing card of the same
    type is refused unless `replace` - then what is given is swapped in and every file NOT
    given (the still, the preview, the frames) is kept. Every file is staged as `<file>.part`
    first and only then swapped in, the main file LAST: a reader sees the main file only when
    the card is whole, and a write that fails while staging leaves an existing card as it was
    and removes a new one again."""
    folder = _clean_folder(folder)
    name = safe_name(name)
    if _hidden(name):
        raise ValueError("a name cannot start with %s" % TRASH_PREFIX)
    anim = data.get("format") == ANIM_FORMAT
    if not anim and (frames is not None or preview):
        raise ValueError("a pose card takes no frames and no preview")
    here = _abs(root, folder)
    suffix, other = (ANIM_SUFFIX, CARD_SUFFIX) if anim else (CARD_SUFFIX, ANIM_SUFFIX)
    card = here + "/" + name + suffix
    existed = os.path.isdir(card)
    if (existed and not replace) or os.path.exists(here + "/" + name + other):
        raise ValueError("%s already exists in %s" % (name, folder or "the library"))
    data = dict(data)
    data.setdefault("format", FORMAT)
    data.setdefault("version", VERSION)
    data["name"] = name
    os.makedirs(card, exist_ok=True)
    staged = []                         # (part, target), in the order they are swapped in

    def stage(file_name, writer):
        target = card + "/" + file_name
        staged.append((target + ".part", target))   # before writing: a half part is cleaned
        writer(target + ".part")

    try:
        if frames is not None:
            stage(FRAMES_FILE, lambda part: _dump_frames(part, frames))
        if thumbnail:
            stage(THUMB_FILE, lambda part: shutil.copy2(thumbnail, part))
        if preview:
            stage(PREVIEW_FILE, lambda part: shutil.copy2(preview, part))
        stage(_main_file(card), lambda part: _dump_json(part, data))   # last: the card is whole
        for part, target in staged:
            os.replace(part, target)
    except BaseException:
        for part, _target in staged:
            try:
                os.remove(part)
            except OSError:
                pass
        if not existed:
            shutil.rmtree(card, ignore_errors=True)
        raise
    return card


def set_thumbnail(path, image):
    """Replace the thumbnail of the card at `path` with the image file `image`."""
    _copy_atomic(image, _fwd(path) + "/" + THUMB_FILE)


def set_preview(path, image):
    """Replace the preview sheet of the animation card at `path` with the image file `image`
    (Replace thumbnail on an animation takes both again). ValueError for a pose card."""
    if not is_anim(path):
        raise ValueError("%s: a pose card has no preview" % _fwd(path))
    _copy_atomic(image, _fwd(path) + "/" + PREVIEW_FILE)


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


def _other_suffix(suffix):
    """The other card type's suffix."""
    return CARD_SUFFIX if suffix == ANIM_SUFFIX else ANIM_SUFFIX


def rename(path, name):
    """Rename the card at `path` (either type, its suffix kept) to `name` (made safe): the folder
    AND the `name` inside its main file. ValueError for a name a card of either type holds there
    (or an unreadable card, before anything moves). Answers the new path."""
    path = _fwd(path)
    new = safe_name(name)
    if _hidden(new):
        raise ValueError("a name cannot start with %s" % TRASH_PREFIX)
    data = read(path)
    suffix = card_suffix(path)
    parent = _fwd(os.path.dirname(path))
    target = parent + "/" + new + suffix
    clash = parent + "/" + new + _other_suffix(suffix)
    if not _same(path, target) and os.path.exists(clash):
        raise ValueError("%s already exists" % os.path.basename(clash))
    _rename_dir(path, target)
    data["name"] = new
    _write_json(target, data)
    return target


def move(path, root, folder):
    """Move the card at `path` (either type) into the catalog `folder` of the library `root`
    (which must exist); ValueError when a card of that name - of either type - is already
    there. Answers the new path."""
    path = _fwd(path)
    folder = _clean_folder(folder)
    where = _abs(root, folder)
    if not os.path.isdir(where):
        raise ValueError("no folder %r in the library" % (folder,))
    leaf = os.path.basename(path)
    target = where + "/" + leaf
    if _same(path, target):
        return target
    if os.path.exists(target) or _taken(where, _stem(leaf)):
        raise ValueError("%s already has %s" % (folder or "the library", _stem(leaf)))
    shutil.move(path, target)
    return target


def trash_dir(user_app_dir):
    """The trash folder for a Maya user folder: beside the animator's prefs, outside every
    library, so an install and a `git status` never see it."""
    return _fwd(user_app_dir) + "/" + TRASH_FOLDER


def remove(path, trash):
    """Delete the card (or catalog) at `path` the safe way: moved into `trash` under a name
    stamped with the time (`20261002_181530_Fist.pose`, `..._Walk.anim`), so a mistake is a move
    back; a second removal of one name in that second takes `_2`, the card's own suffix kept.
    Answers where it went."""
    path = _fwd(path)
    trash = _fwd(trash)
    os.makedirs(trash, exist_ok=True)
    base = "%s_%s" % (time.strftime("%Y%m%d_%H%M%S"), os.path.basename(path))
    stem, suffix = (_stem(base), base[len(_stem(base)):]) if _is_card(base) else (base, "")
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
    in the card's name, folder, character label or type word - "pose" or "animation" ("fist
    creep" narrows to Creep's fists, "walk animation" to the walks that are clips)."""
    terms = (query or "").lower().split()
    if not terms:
        return list(cards)
    kept = []
    for card in cards:
        word = "animation" if card.type == "anim" else "pose"
        hay = ("%s %s %s %s" % (card.name, card.folder, card.label, word)).lower()
        if all(term in hay for term in terms):
            kept.append(card)
    return kept


def of_type(cards, type_name):
    """The cards of one of `TYPES`: `all` every card, `pose` the poses, `anim` the animations
    (the window's type filter, beside the search). ValueError for another name."""
    if type_name not in TYPES:
        raise ValueError("a type of %s, not %r" % (", ".join(TYPES), type_name))
    if type_name == "all":
        return list(cards)
    return [card for card in cards if card.type == type_name]


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
