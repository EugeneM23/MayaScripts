"""maya_walk.cards - Walk Builder's pose is a Pose Library card (2026-10-15).

The animator: «вместо строчки pose окошко для карточек которые будем перекидывать драгом прямо из библиотеки
поз» - and, asked, the walk follows the card (its Update from selection is taken on the next re-key) with a copy
of the pose's bones kept on the walked skeleton, so a card renamed or deleted still walks. The old `.wpose` poses
go into the library once, as cards of the folder `Walk poses`.

A pose card's bones are a `.wpose`'s ({leaf: {parent, canonical, rest, world}}) plus `rotateOrder` and, saved
from a rig, `drive` - which `posemath.Transfer` already reads where the walk's skeleton cannot carry the roll.
stdlib only, but for `maya_poselib.store` (stdlib too).
The design: docs/superpowers/specs/2026-10-15-walk-pose-card-well-design.md.
"""
import base64
import gzip
import json
import os

from maya_poselib import store

from . import files as wf

MIGRATED_FOLDER = "Walk poses"          # where the old .wpose poses land in the library
MIGRATED_LIST = "library_poses.json"   # in the walks folder: the .wpose poses already moved (never made again)
GONE = "pose card %s is gone - using the copy on the skeleton"


class Refusal(Exception):
    """A card the well does not take; the message says why."""


def plugin_dir():
    """The plugin folder (the one holding maya_walk and maya_poselib)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")


def library_root(cmds=None):
    """The Pose Library's folder - its optionVar when it names a folder, else the plugin's own (store's rule)."""
    value = ""
    if cmds is not None:
        try:
            if cmds.optionVar(exists=store.ROOT_VAR):
                value = cmds.optionVar(query=store.ROOT_VAR) or ""
        except Exception:                                    # noqa: BLE001 - a fake without optionVar
            value = ""
    return store.library_root(value, plugin_dir())


def relative(path, root):
    """`path` (a card folder) relative to the library `root`, forward slashes; the absolute path when it lies
    outside it."""
    path = os.path.abspath(path).replace("\\", "/").rstrip("/")
    root = os.path.abspath(root).replace("\\", "/").rstrip("/")
    if path.lower().startswith(root.lower() + "/"):
        return path[len(root) + 1:]
    return path


def absolute(rel, root):
    """A card's path from what `relative` gave."""
    if not rel:
        return ""
    if os.path.isabs(rel):
        return rel.replace("\\", "/")
    return root.replace("\\", "/").rstrip("/") + "/" + rel


def card_name(path):
    """A card's name: its folder's, without `.pose`."""
    leaf = os.path.basename(path.replace("\\", "/").rstrip("/"))
    return leaf[:-len(store.CARD_SUFFIX)] if leaf.endswith(store.CARD_SUFFIX) else leaf


def read_card(path):
    """(name, bones) of the pose card at `path`. Refused: an animation card, an objects card, a card with no
    bones, one that cannot be read."""
    if store.is_anim(path):
        raise Refusal("%s is an animation card - the walk takes a pose card of a character" % card_name(path))
    try:
        data = store.read(path)
    except ValueError as error:
        raise Refusal("%s cannot be read (%s)" % (card_name(path), error))
    if (data.get("kind") or "character") != "character":
        raise Refusal("%s is a card of objects - the walk takes a pose card of a character" % card_name(path))
    bones = data.get("bones") or {}
    if not isinstance(bones, dict) or not bones:
        raise Refusal("%s holds no bones" % card_name(path))
    for leaf, bone in bones.items():
        if not isinstance(bone, dict) or len(bone.get("world") or ()) != 16 or len(bone.get("rest") or ()) != 16:
            raise Refusal("%s: the bone %s is not whole" % (card_name(path), leaf))
    return card_name(path), bones


def stamp(path):
    """The card's pose.json time (a re-key reads the card again when it changed), or None."""
    try:
        return os.path.getmtime(os.path.join(path, store.POSE_FILE))
    except OSError:
        return None


def pack(bones):
    """The pose's bones as one string: gzip of their JSON, base64 (a string attribute on the skeleton)."""
    raw = json.dumps(bones, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(gzip.compress(raw, 6)).decode("ascii")


def unpack(text):
    """What `pack` gave, or None when it is not that."""
    if not text:
        return None
    try:
        bones = json.loads(gzip.decompress(base64.b64decode(text)).decode("utf-8"))
    except (ValueError, OSError, TypeError):
        return None
    return bones if isinstance(bones, dict) and bones else None


def resolve(card_rel, copy_text, legacy_name, library, folder):
    """(name, bones, note) of a walked skeleton's pose: the card when it reads; else the copy kept on the
    skeleton (the note says the card is gone); else - a skeleton walked before the cards - the old pose's name:
    its migrated card, then its .wpose file. (None, None, "") with no pose at all."""
    if card_rel:
        path = absolute(card_rel, library)
        note = GONE % card_name(card_rel)
        if os.path.isdir(path):
            try:
                name, bones = read_card(path)
                return name, bones, ""
            except Refusal as refusal:
                note = "%s - using the copy on the skeleton" % refusal
        bones = unpack(copy_text)
        if bones is not None:
            return card_name(card_rel), bones, note
        return None, None, note.replace(" - using the copy on the skeleton", "")
    if legacy_name:
        migrated = absolute(legacy_card(legacy_name), library)
        if os.path.isdir(migrated):
            name, bones = read_card(migrated)
            return name, bones, ""
        old = wf.pose_path_for(folder, legacy_name)
        if os.path.exists(old):
            name, bones = wf.load_pose(old)
            return name, bones, ""
        bones = unpack(copy_text)
        if bones is not None:
            return legacy_name, bones, GONE % legacy_name
    return None, None, ""


def legacy_card(legacy_name):
    """The migrated card's relative path of an old pose name (Pick of a skeleton walked before the cards)."""
    return MIGRATED_FOLDER + "/" + store.safe_name(legacy_name) + store.CARD_SUFFIX


# ---- the old poses into the library ----

def _done(folder):
    try:
        with open(os.path.join(folder, MIGRATED_LIST), encoding="utf-8") as handle:
            data = json.load(handle)
        return set(data) if isinstance(data, list) else set()
    except (OSError, ValueError):
        return set()


def migrate(folder, library, author=""):
    """Every `.wpose` pose in the walks `folder` not moved yet becomes the card `Walk poses/<name>.pose` of the
    library (every bone a member, no thumbnail); listed in `folder`/library_poses.json so a card deleted later is
    not made again. A name already taken in the library is listed and left. Answers the names made."""
    names = wf.pose_names_in(folder)
    done = _done(folder)
    todo = [n for n in names if n not in done]
    if not todo:
        return []
    made = []
    for name in todo:
        try:
            title, bones = wf.load_pose(wf.pose_path_for(folder, name))
        except wf.Refusal:
            done.add(name)
            continue
        data = {"format": store.FORMAT, "version": store.VERSION, "kind": "character", "name": name,
                "created": "", "author": author, "scene": name + wf.POSE_SUFFIX, "frame": 0.0, "fps": "",
                "character": {"label": title or name}, "bones": bones, "members": sorted(bones),
                "regions": [], "objects": []}
        try:
            store.write(library, MIGRATED_FOLDER, name, data)
            made.append(name)
        except (ValueError, OSError):
            pass                                             # taken: the animator's card stands
        done.add(name)
    try:
        with open(os.path.join(folder, MIGRATED_LIST), "w", encoding="utf-8") as handle:
            json.dump(sorted(done), handle)
    except OSError:
        pass
    return made
