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
    """A card's name: its folder's, without `.pose` / `.anim`."""
    leaf = os.path.basename(path.replace("\\", "/").rstrip("/"))
    for suffix in store.CARD_SUFFIXES:
        if leaf.endswith(suffix):
            return leaf[:-len(suffix)]
    return leaf


def read_card(path):
    """(name, bones) of the pose card at `path`. Refused: an animation card, an objects card, a card with no
    bones, one that cannot be read."""
    if store.is_anim(path):
        raise Refusal("%s is an animation card - drop it into the walk well; the pose takes a pose card"
                      % card_name(path))
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


# ---- the walk cycles: Pose Library animation cards (2026-10-15) ----
#
# The animator: «для циклов походок тоже добавим возможность применять карточки» - asked, an ANIMATION card of
# the library (+ Save > Animation, or Walk Builder's Save) dropped into the walk well is the walk. An animation
# card holds every bone's static half (parent, canonical, rest) and its world on every frame of its range, which
# is all a saved walk is; `walk_data` reads one as `files.load` reads a walk file, `card_of_walk` the other way.

WALK_FOLDER = "Walk cycles"               # where the old .walk.gz walks land in the library
WALKS_LIST = "library_walks.json"         # in the walks folder: the walks already moved (never made again)
#  a time unit as a card names it -> frames a second (scene.FPS's table, kept here: this module needs no Maya)
UNIT_FPS = {"game": 15, "film": 24, "pal": 25, "ntsc": 30, "show": 48, "palf": 50, "ntscf": 60}


def unit_of(fps):
    """The time unit's name of `fps` frames a second (a card's `fps` field); Maya's "<n>fps" otherwise."""
    for unit, value in UNIT_FPS.items():
        if abs(value - float(fps)) < 1e-6:
            return unit
    return "%gfps" % float(fps)


def fps_of(unit):
    """Frames a second of a card's time unit: the table's, a "<n>fps" spelling, else 30."""
    unit = str(unit or "")
    if unit in UNIT_FPS:
        return float(UNIT_FPS[unit])
    if unit.endswith("fps"):
        try:
            return float(unit[:-3])
        except ValueError:
            pass
    return 30.0


def walk_stamp(path):
    """The animation card's file times [header, frames] - the walk is read again when either changes - or None."""
    try:
        return [os.path.getmtime(os.path.join(path, store.ANIM_FILE)),
                os.path.getmtime(os.path.join(path, store.FRAMES_FILE))]
    except OSError:
        return None


def _depth(leaf, parents):
    depth, seen = 0, set()
    while parents.get(leaf) and leaf not in seen:
        seen.add(leaf)
        leaf = parents[leaf]
        depth += 1
    return depth


def walk_data(path, template=None):
    """The animation card at `path` as `files.load`'s dict: names (a parent before its children), parents (index,
    -1 at the top), worlds (J, F, 4, 4), fps, up (+Y), name, start, statics {leaf: parent, canonical, rest}.
    `template` (files.read_template's) gives a skeleton of Manny's bones Manny's bind as its rest - the walk
    tool's own rest rule. Refused: a pose card, a card of objects, one with no bones or one frame, one that
    cannot be read."""
    import numpy as np
    from maya_poselib import animdata
    name = card_name(path)
    if not store.is_anim(path):
        raise Refusal("%s is a pose card - drop it into the pose well; the walk takes an animation card" % name)
    try:
        header = store.read(path)
        frames = store.read_frames(path)
    except ValueError as error:
        raise Refusal("%s cannot be read (%s)" % (name, error))
    if (header.get("kind") or "character") != "character":
        raise Refusal("%s is a card of objects - the walk takes an animation card of a character" % name)
    statics = header.get("bones") or {}
    slot = dict((leaf, i) for i, leaf in enumerate(frames.get("bones") or []))
    leaves = [leaf for leaf in statics if leaf in slot]
    rows = frames.get("world") or []
    if not leaves or len(rows) < 2:
        raise Refusal("%s holds %s - a walk is a cycle of frames" % (name, "no bones" if not leaves else "one frame"))
    parents = dict((leaf, statics[leaf].get("parent") if statics[leaf].get("parent") in slot else None)
                   for leaf in leaves)
    seen = set()
    for leaf in leaves:                                      # the frames' order kept when a parent comes first
        if parents[leaf] and parents[leaf] not in seen:
            leaves.sort(key=lambda each: (_depth(each, parents), each))
            break
        seen.add(leaf)
    index = dict((leaf, i) for i, leaf in enumerate(leaves))
    worlds = np.empty((len(leaves), len(rows), 4, 4))
    for f, row in enumerate(rows):
        for j, leaf in enumerate(leaves):
            i = slot[leaf]
            worlds[j, f] = np.array(animdata.decode(row[7 * i:7 * i + 7])).reshape(4, 4)
    rests = dict((leaf, [float(v) for v in statics[leaf]["rest"]]) for leaf in leaves)
    if template:
        positions = dict((leaf, tuple(rests[leaf][12:15])) for leaf in leaves)
        manny = wf.template_rests(positions, parents, template)
        if manny:
            rests.update((leaf, list(rest)) for leaf, rest in manny.items() if leaf in rests)
    return {"names": leaves, "parents": [index[parents[leaf]] if parents[leaf] else -1 for leaf in leaves],
            "worlds": worlds, "fps": fps_of(header.get("fps")), "up": [0.0, 1.0, 0.0], "name": name,
            "start": int(round(float(header.get("start") or 0))),
            "statics": dict((leaf, {"parent": parents[leaf], "canonical": statics[leaf].get("canonical"),
                                    "rest": rests[leaf]}) for leaf in leaves)}


def card_of_walk(data, author=""):
    """(header, frames) of an animation card holding the walk `data` (`files.load`'s dict, or what Save reads):
    every bone a member, a key on every frame, no thumbnail - what `walk_data` reads back as the same walk (the
    worlds' scale dropped, as every animation card drops it)."""
    from maya_poselib import animdata
    names = list(data["names"])
    worlds = data["worlds"]
    count = len(worlds[0])
    start = int(data.get("start") or 0)
    statics = data["statics"]
    world = []
    for f in range(count):
        row = []
        for j in range(len(names)):
            row.extend(animdata.encode([float(v) for v in worlds[j][f].reshape(16)]))
        world.append(row)
    label = data.get("name") or "Walk"
    header = {"format": store.ANIM_FORMAT, "version": store.VERSION, "kind": "character", "name": label,
              "created": "", "author": author, "scene": label + wf.SUFFIX, "fps": unit_of(data.get("fps") or 30),
              "start": float(start), "end": float(start + count - 1), "frames": count,
              "key_times": [float(start + f) for f in range(count)], "character": {"label": label},
              "bones": dict((leaf, {"parent": statics[leaf].get("parent"), "canonical": statics[leaf].get("canonical"),
                                    "rest": [float(v) for v in statics[leaf]["rest"]], "rotateOrder": 0})
                            for leaf in names),
              "members": sorted(names), "regions": [], "rig_source": False, "objects": []}
    return header, {"bones": names, "world": world, "drive": {}}


def walk_card(name):
    """The library path (relative) of an old walk name's migrated card (a skeleton walked before the cards)."""
    return WALK_FOLDER + "/" + store.safe_name(name) + store.ANIM_SUFFIX


def migrate_walks(folder, library, author=""):
    """Every `.walk.gz` walk in the walks `folder` not moved yet becomes the card `Walk cycles/<name>.anim`;
    listed in `folder`/library_walks.json so a card deleted later is not made again. A name taken in the library
    is listed and left. Answers the names made."""
    names = wf.names_in(folder)
    try:
        with open(os.path.join(folder, WALKS_LIST), encoding="utf-8") as handle:
            done = set(json.load(handle))
    except (OSError, ValueError, TypeError):
        done = set()
    todo = [n for n in names if n not in done]
    if not todo:
        return []
    made = []
    for name in todo:
        done.add(name)
        try:
            data = wf.load(wf.path_for(folder, name))
        except wf.Refusal:
            continue
        data["name"] = name
        header, frames = card_of_walk(data, author)
        try:
            store.write(library, WALK_FOLDER, name, header, frames=frames)
            made.append(name)
        except (ValueError, OSError):
            pass                                             # taken: the animator's card stands
    try:
        with open(os.path.join(folder, WALKS_LIST), "w", encoding="utf-8") as handle:
            json.dump(sorted(done), handle)
    except OSError:
        pass
    return made
