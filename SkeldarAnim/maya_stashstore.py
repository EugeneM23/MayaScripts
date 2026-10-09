"""maya_stashstore - the Stash section's folder, as data. Stdlib only.

Stash is the local shelf of drafts and intermediate files: a scene or an FBX
is copied into `<userAppDir>/SkeldarStash/` and listed there, and nothing
leaves the machine (the animator's ask, 2026-10-09: «быстро сохранять какие-то
черновики и промежуточные файлы а потом их открывать или импортировать»).
The folder is the truth: one file per item, no index beside it, so a file a
person drops in or deletes by hand is simply there or not there.

This module is the rules: which files are items, what an item is called
when the name is taken, what a row says, what a delete asks. No `maya`, no
disk writes -- `entries` only reads a folder listing, and `now` is always
passed in. The name and size rules are Shared's (`maya_sharerecords`), on
purpose: a draft and a sent file are named by the same rules.

Spec: docs/superpowers/specs/2026-10-09-stash-design.md
"""

import os
import time

import maya_sharerecords as records

FOLDER = "SkeldarStash"
KINDS = (".ma", ".mb", ".fbx")
NAME_WIDTH = 40
KIND_WIDTH = 5
SIZE_WIDTH = 8
WHEN_WIDTH = 11
DELETE_NAMES = 5             # the files a delete question names


def is_item(name):
    """True for a file name the list shows: a scene or an FBX, not a
    leftover `.part` of an interrupted copy."""
    if not name or name.startswith("."):
        return False
    return os.path.splitext(name)[1].lower() in KINDS


def kind_of(name):
    """"scene" for .ma/.mb, "fbx" for .fbx, None for anything else."""
    return records.kind_of(name)


def unique_name(name, taken):
    """`name`, or `name` with ` (2)`, ` (3)` ... before its extension, the
    first that no taken name answers to. Case does not count (Windows folds
    it), and `taken` is every name in the folder."""
    folded = set(t.lower() for t in taken)
    if name.lower() not in folded:
        return name
    stem, ext = os.path.splitext(name)
    number = 2
    while True:
        candidate = "{0} ({1}){2}".format(stem, number, ext)
        if candidate.lower() not in folded:
            return candidate
        number += 1


def draft_name(scene_path, now):
    """The name a stash scene gets when none is typed: the scene's own stem
    with the time of the stash (`shot_1432.ma`), `untitled_1432.ma` for a
    scene never saved. The extension is the scene's own type."""
    own, _file_type = records.scene_file_name(scene_path, now)
    if not (scene_path or "").strip():
        return own                   # already `untitled_<HHMM>.ma`
    stem, ext = os.path.splitext(own)
    return "{0}_{1}{2}".format(stem, time.strftime("%H%M", time.localtime(now)),
                               ext)


def short_name(node):
    """A scene node's own name: `|Manny_Rig:Main|hand` -> `hand`, and the
    namespace goes (`Manny_Rig:Main` -> `Main`). Pure."""
    leaf = (node or "").split("|")[-1]
    return leaf.split(":")[-1] or "selection"


def selection_name(nodes, now):
    """The FBX an object stash is called when no name is typed: the one
    object's own name, or `selection` for several, with the time of the
    stash (`Main_1432.fbx`, `selection_1432.fbx`)."""
    shorts = [short_name(n) for n in nodes]
    base = shorts[0] if len(shorts) == 1 else "selection"
    return "{0}_{1}.fbx".format(base, time.strftime("%H%M",
                                                   time.localtime(now)))


def entries(names_and_stats):
    """The items among `(name, size, mtime)` triples, newest first, as dicts
    {"name", "kind", "bytes", "mtime"}. Anything that is not an item is
    dropped; ties keep their name order."""
    out = []
    for name, size, mtime in names_and_stats:
        if not is_item(name):
            continue
        out.append({"name": name, "kind": kind_of(name), "bytes": int(size),
                    "mtime": float(mtime)})
    out.sort(key=lambda e: e["name"].lower())
    out.sort(key=lambda e: e["mtime"], reverse=True)
    return out


def _fit(text, width):
    text = " ".join((text or "").split())
    if len(text) > width:
        return text[:width - 2] + ".."
    return text


def row_text(entry, now):
    """One line of the list: name, kind, size, when."""
    return "{0:<{a}} {1:<{b}} {2:>{c}}  {3:<{d}}".format(
        _fit(entry["name"], NAME_WIDTH), entry["kind"], records.size_text(
            entry["bytes"]), when_text(entry["mtime"], now),
        a=NAME_WIDTH, b=KIND_WIDTH, c=SIZE_WIDTH, d=WHEN_WIDTH).rstrip()


def when_text(mtime, now):
    """«14:12» today, «08.10 14:12» another day, in local time."""
    return records.when_text(mtime, now)


def subtitle(count):
    """The card's subtitle: how many items, and that none of them leaves."""
    return "{0} file{1} on this machine - nothing is sent".format(
        count, "" if count == 1 else "s")


def picked_text(count):
    """The status line when several rows are picked."""
    return ("{0} files picked - Delete takes them off this disk; Open, "
            "Import and Save to... take one".format(count))


def delete_question(names):
    """The confirm before a delete: which files, and that they are gone for
    good (this disk only, no host keeps them)."""
    count = len(names)
    shown = ["  " + name for name in names[:DELETE_NAMES]]
    if count > DELETE_NAMES:
        shown.append("  and {0} more".format(count - DELETE_NAMES))
    return ("Delete {0} file{1} from the stash?\n\n{2}\n\nThey are removed "
            "from this disk. This cannot be undone.".format(
                count, "" if count == 1 else "s", "\n".join(shown)))


def open_refusal(name):
    """The line when a delete is asked for the scene open in this Maya."""
    return ("{0} is the scene open in this Maya - Save As it somewhere else "
            "first; nothing deleted for it.".format(name))
