"""maya_walk.scene - the parametric walk in Maya: save a walk cycle, put it on any skeleton, tune it there.

Save walk: a bone of a walk cycle selected - the cycle goes to a file in the walks folder (`folder()`). Apply:
any skeleton selected (UE5/UE4, Mixamo, HumanIK, Unity, Biped ...) - the walk is keyed onto it, in its own
proportions, from where it stands; a released knob re-keys it. A walked skeleton carries its walk, pose and
knobs (`MARKER`), so selecting it reads them back. The hub card is maya_walk.panel.

The model: maya_walk.model; the saved walk: maya_walk.files; the transfer onto a skeleton: maya_walk.target
(the Pose Library's posemath plus the legs by IK); a character pose under the walk: maya_walk.pose. The design:
docs/superpowers/specs/2026-10-12-parametric-walk-design.md, 2026-10-12-walk-onto-any-skeleton-design.md and
2026-10-13-walk-builder-card-design.md.
"""
import json
import math
import os
import shutil
import sys
import time

import numpy as np

from . import model as wm
from . import files as wf
from . import target as wt
from . import pose as wp
from . import clean as wc
from . import meanpose as mp
from . import cards as wcards

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(PLUGIN, "assets", "manny_skeleton_template.json")
#  What Fix posture judges a walk's posture against (2026-10-14): the UE5 idle M_Neutral_Stand_Idle_Loop's mean pose
#  over its 302 frames, shipped (without it: the skeleton's rest)
REFERENCE_FILE = os.path.join(PLUGIN, "assets", "walk_reference_ue5.wpose.gz")
#  Every knob the card holds and a walked skeleton remembers: the model's and the clean's (Seam, Smooth - the model
#  never sees them: apply hands each its own)
ALL_DEFAULTS = dict(wm.DEFAULTS, **wc.DEFAULTS)
ALL_RANGES = dict(wm.RANGES, **wc.RANGES)
#  Where the walks and the poses live: this override (a verify's temporary folder), else the optionVar, else
#  <userAppDir>/SkeldarWalks - outside the plugin folder, which an install replaces.
WALKS = None
FOLDER_OPTIONVAR = "skeldarWalkFolder"
FOLDER_NAME = "SkeldarWalks"


def folder():
    """The walks folder (made on the first save)."""
    if WALKS:
        return WALKS
    cmds = _cmds()
    if cmds.optionVar(exists=FOLDER_OPTIONVAR):
        chosen = cmds.optionVar(query=FOLDER_OPTIONVAR)
        if chosen:
            return chosen
    return os.path.join(cmds.internalVar(userAppDir=True), FOLDER_NAME)


class Refusal(Exception):
    """What a press does not do, and why (the status line shows it)."""


REFUSALS = (Refusal, wm.Refusal, wf.Refusal, wt.Refusal, mp.Refusal, wcards.Refusal)
#  The pose's bones as a walked skeleton last used them (packed, maya_walk.cards): the walk keeps walking when
#  its Pose Library card is renamed or deleted (2026-10-15)
POSE_COPY = "skeldarWalkPose"
NO_POSE = "(none)"
ALL_PARTS = tuple(part for part, keys in wp.PARTS)
MARKER = "skeldarWalk"
VERSION = 2
CHANNELS = ("translateX", "translateY", "translateZ", "rotateX", "rotateY", "rotateZ")
TRANSLATE = CHANNELS[:3]
ROTATE = CHANNELS[3:]
FPS = {"game": 15, "film": 24, "pal": 25, "ntsc": 30, "show": 48, "palf": 50, "ntscf": 60}


def _cmds():
    import maya.cmds as cmds
    return cmds


def _om():
    import maya.api.OpenMaya as om
    return om


def _oma():
    import maya.api.OpenMayaAnim as oma
    return oma


def _state():
    """Per session, on sys (a reloaded module must find it): the loaded walks by file and the skeleton
    the card works on (its root's UUID)."""
    state = getattr(sys, "_skeldar_walk", None)
    if state is None or "loaded" not in state:
        state = {"loaded": {}, "target": None}
        sys._skeldar_walk = state
    if state.get("model") is not wm or state.get("clean") is not wc:
        # the walks and poses read by a model loaded earlier: their methods are the old code's (an install
        # purges and reloads the package, and an old Walk's evaluate() took no pose) - read them again
        state["loaded"] = {}
        state["model"] = wm
        state["clean"] = wc
    return state


def _short(path):
    return path.rsplit("|", 1)[-1]


def _long(node):
    found = _cmds().ls(node, long=True)
    if not found:
        raise Refusal("%s is gone from the scene" % node)
    return found[0]


def _fps():
    unit = _cmds().currentUnit(query=True, time=True)
    if unit in FPS:
        return float(FPS[unit])
    if unit.endswith("fps"):
        return float(unit[:-3])
    raise Refusal("the scene's time unit %s is not a frame rate this tool knows" % unit)


# ---- which skeleton ----

def skeleton_root_of(node):
    """The topmost joint of the skeleton `node` belongs to (a joint, a mesh skinned to it, a group above
    it). A rig of ours is refused: its game skeleton is driven by constraints."""
    cmds = _cmds()
    path = _long(node)
    try:
        import maya_rigs
        if maya_rigs.rig_of(path, maya_rigs.rigs()) is not None:
            raise Refusal("%s belongs to a rig - this version puts a walk on skeletons only" % _short(path))
    except ImportError:
        pass
    if cmds.nodeType(path) != "joint":
        shapes = cmds.listRelatives(path, shapes=True, fullPath=True) or []
        skins = [s for shape in shapes for s in (cmds.listHistory(shape, pruneDagObjects=True) or [])
                 if cmds.nodeType(s) == "skinCluster"]
        if skins:
            path = _long((cmds.skinCluster(skins[0], query=True, influence=True) or [path])[0])
        else:
            below = cmds.listRelatives(path, allDescendents=True, type="joint", fullPath=True) or []
            if not below:
                raise Refusal("%s holds no skeleton - select a bone of a skeleton" % _short(path))
            path = min(below, key=lambda p: p.count("|"))
    while True:
        above = cmds.listRelatives(path, parent=True, fullPath=True)
        if not above or cmds.nodeType(above[0]) != "joint":
            return path
        path = above[0]


def selected_root():
    selection = _cmds().ls(selection=True, long=True)
    if not selection:
        raise Refusal("select a bone of a skeleton first")
    return skeleton_root_of(selection[0])


def selected_roots():
    """Every skeleton the selection names (selected_root's rule per node), each once, in selection order."""
    selection = _cmds().ls(selection=True, long=True)
    if not selection:
        raise Refusal("select a bone of a skeleton first")
    roots = []
    for node in selection:
        root = skeleton_root_of(node)
        if root not in roots:
            roots.append(root)
    return roots


# ---- the list of walkers (2026-10-16: several cycles on several characters at once) ----

def walkers():
    """The card's list: every walked top joint (the MARKER, v2) in the active tab not unlisted, sorted by
    label. Read from the scene each time - nothing else stores the list."""
    cmds = _cmds()
    found = []
    for path in cmds.ls(type="joint", long=True) or []:
        if not cmds.attributeQuery(MARKER, node=path, exists=True):
            continue
        above = cmds.listRelatives(path, parent=True, fullPath=True)
        if above and cmds.nodeType(above[0]) == "joint":
            continue
        memo = memo_of(path)
        if memo.get("walk") and memo.get("listed", True):
            found.append(path)
    try:
        from maya_scenetabs import scope
        found = scope.active_only(found, cmds)
    except ImportError:
        pass
    return sorted(found, key=lambda p: (walker_label(p).lower(), p))


def set_listed(root, listed):
    """The walker `root` in (True) or out of (False) the card's list; its keys stay."""
    memo = memo_of(root)
    if memo:
        memo["listed"] = bool(listed)
        _set_memo(root, memo)


def walker_label(root):
    """The character a walker is: its character group without _Character, else its namespace, else its
    top's short name, else the joint's."""
    leaf = _short(root)
    top = root.lstrip("|").split("|")[0]
    try:
        from maya_scenetabs import scope
        top = scope.local(top, _cmds()).lstrip("|").split("|")[0]
        leaf = scope.local(leaf, _cmds()).rsplit("|", 1)[-1]
    except ImportError:
        pass
    if top != root.lstrip("|") and top.endswith("_Character"):
        return top[:-len("_Character")]
    if ":" in leaf:
        return leaf.rsplit(":", 1)[0]
    if top != leaf:
        return top
    return leaf


def read_bones(root):
    """The skeleton as the Pose Library reads it ({leaf: bone}, scene.skeleton) with this tool's rest rule:
    an unskinned skeleton whose bones are Manny's rests at Manny's bind (the plugin's template). Returns
    (bones, a note or "")."""
    from maya_poselib import scene
    cmds = _cmds()
    ref = scene.skeleton_ref(root)
    bones, convention = scene.skeleton(ref)
    skinned = any(cmds.listConnections(b["path"] + ".worldMatrix[0]", source=False, destination=True,
                                       type="skinCluster") for b in bones.values())
    if skinned:
        return bones, ""
    positions = dict((leaf, tuple(b["rest"][12:15])) for leaf, b in bones.items())
    parents = dict((leaf, b["parent"]) for leaf, b in bones.items())
    rests = wf.template_rests(positions, parents, wf.read_template(TEMPLATE)) if os.path.exists(TEMPLATE) else None
    if rests is None:
        return bones, "%s has no skin: its rest is read as it stands" % _short(root)
    for leaf, rest in rests.items():
        bones[leaf]["rest"] = list(rest)
    return bones, ""


# ---- saving a walk ----

def read_clip(root):
    """The cycle under `root` as a walkmodel.Clip: every joint's world on every whole frame of its keys."""
    cmds = _cmds()
    if cmds.currentUnit(query=True, linear=True) != "cm":
        raise Refusal("the scene is not in centimetres")
    joints = [root] + (cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True) or [])
    joints.sort(key=lambda p: (p.count("|"), p))
    index = dict((p, i) for i, p in enumerate(joints))
    parents = []
    for path in joints:
        above = cmds.listRelatives(path, parent=True, fullPath=True)
        parents.append(index.get(above[0], -1) if above else -1)
    times = set()
    for path in joints:
        for ch in CHANNELS:
            times.update(cmds.keyframe(path, attribute=ch, query=True, timeChange=True) or [])
    if not times:
        raise Refusal("%s carries no keys - select a bone of a walk cycle" % _short(root))
    start, end = min(times), max(times)
    if abs(start - round(start)) > 1e-6 or abs(end - round(end)) > 1e-6:
        raise Refusal("the keys run %g-%g: a cycle starts and ends on whole frames" % (start, end))
    start, end = int(round(start)), int(round(end))
    worlds = np.array([[cmds.getAttr(p + ".worldMatrix[0]", time=t) for t in range(start, end + 1)]
                       for p in joints]).reshape(len(joints), end - start + 1, 4, 4)
    up = (0.0, 1.0, 0.0) if cmds.upAxis(query=True, axis=True) == "y" else (0.0, 0.0, 1.0)
    from maya_scenetabs import scope
    scene = os.path.splitext(os.path.basename(scope.scene_name(cmds)))[0]
    above = cmds.listRelatives(root, parent=True, fullPath=True)
    name = scene or _short(above[0] if above else root)
    return wm.Clip([_short(p).split(":")[-1] for p in joints], parents, worlds, _fps(), up, name), start


def _reference():
    """The UE5 idle's pose bones, or None without the shipped file."""
    return wf.load_pose(REFERENCE_FILE)[1] if os.path.exists(REFERENCE_FILE) else None


def _clean_data(data, knobs, posture_fix=False):
    """(the clean clip, its Report) of a walk's data (files.load's dict) under the clean knobs; `posture_fix` sets
    its posture right against the UE5 idle carried onto the walk's skeleton (Fix posture)."""
    ref, why = None, None
    if posture_fix:
        bones = _reference()
        if bones is not None:
            try:
                ref = wp.carried(data["names"], np.asarray(data["worlds"])[:, 0], data["statics"], bones, wt)
            except wt.Refusal as error:          # a skeleton the idle cannot stand on: judged by its rest
                why = "the UE5 idle was not used (%s) - judged against the rest" % error
    clip, report = wc.clean(wf.clip_of(data, wm), data["statics"], ref, knobs, posture_fix=posture_fix)
    if why:
        report.note(why)
    return clip, report


def _cleaned(path, stamp, data, given):
    """_clean_data of a loaded walk file, cached by the file's time and the knobs."""
    knobs = wc.knobs(given)
    key = ("clean", path, stamp, tuple(sorted(knobs.items())))
    cached = _state()["loaded"].get(key)
    if cached is None:
        cached = _clean_data(data, knobs)
        _cache(key, cached)
    return cached


CACHED_READINGS = 6       # a walk's readings kept (each knob value released is one - the oldest goes)


def _cache(key, value):
    """A reading of a walk (`key` = (kind, path, ...)) kept, at most CACHED_READINGS of its kind and path."""
    loaded = _state()["loaded"]
    same = [k for k in loaded if isinstance(k, tuple) and k[:2] == key[:2]]
    for old in same[:max(0, len(same) - CACHED_READINGS + 1)]:
        del loaded[old]
    loaded[key] = value


def save_walk(root, name=None):
    """The clip under `root` saved to the walks folder as <name>.walk.gz AS IT STANDS - a cycle or not: it is
    looped when it is read (maya_walk.clean) - after reading it the way it will be read (the clean at its
    defaults, then the model's refusals). Returns (the walk's name, the status line)."""
    clip, start = read_clip(root)
    bones, note = read_bones(root)
    statics = dict((leaf, {"parent": b["parent"], "canonical": b["canonical"], "rest": b["rest"]})
                   for leaf, b in bones.items() if leaf in clip.names)
    missing = [n for n in clip.names if n not in statics]
    if missing:
        raise Refusal("%d bones of the cycle read twice or unnamed: %s" % (len(missing), ", ".join(missing[:4])))
    data = {"names": clip.names, "parents": clip.parents, "worlds": clip.worlds, "fps": clip.fps, "up": clip.up,
            "name": clip.name, "statics": statics, "start": start}
    cleaned, report = _clean_data(data, wc.knobs())
    walk = wm.analyse(cleaned)
    name = wf.safe_name(name or clip.name)
    clip.name = name
    path = wf.path_for(folder(), name)
    wf.save(path, clip, statics, start)
    _forget(path)
    line = "saved %s | %s" % (os.path.basename(path), walk.summary())
    if report.changed:
        line += " | " + report.short()
    return name, line + (" | " + note if note else "")


def _forget(path):
    """Every cached reading of a walk file (a fresh save replaces it)."""
    loaded = _state()["loaded"]
    for key in list(loaded):
        if key == path or (isinstance(key, tuple) and path in key[:2]):
            loaded.pop(key, None)


#  A walk is named two ways (2026-10-15): a file of the walks folder by its name, or a Pose Library animation card
#  by CARD + its path relative to the library. A card is read into a walk file of its own under CARD_CACHE
#  (`walk_path`), read again when the card changes; Fix posture and the mean pose's correction live beside that
#  file as beside any walk's.
CARD = "card:"
CARD_CACHE = "cards"
CARD_SOURCE = ".source"          # beside a card's walk file: which card, at what time


def is_card(name):
    return bool(name) and name.startswith(CARD)


def walk_label(name):
    """A walk's name as the animator reads it: a card's name, a file's name."""
    return wcards.card_name(name[len(CARD):]) if is_card(name) else (name or "")


def card_walk(rel):
    """The walk name of the animation card `rel` (relative to the library)."""
    return CARD + rel


def _card_cache(rel):
    return os.path.join(folder(), CARD_CACHE, wf.safe_name(rel.replace("/", "__")) + wf.SUFFIX)


def walk_path(name):
    """The walk file a walk `name` reads: a saved walk's, or the one an animation card is read into - written
    when it is missing or the card changed (a card gone keeps the walk it gave). Refused: no such walk."""
    if not is_card(name):
        return wf.path_for(folder(), name)
    rel = name[len(CARD):]
    card = wcards.absolute(rel, wcards.library_root(_cmds()))
    cache = _card_cache(rel)
    source = cache + CARD_SOURCE
    stamp = wcards.walk_stamp(card) if os.path.isdir(card) else None
    if stamp is None:
        if os.path.exists(cache):
            return cache
        raise Refusal("the walk card %s is gone from the library" % walk_label(name))
    try:
        with open(source, encoding="utf-8") as handle:
            known = json.load(handle).get("stamp")
    except (OSError, ValueError, AttributeError):
        known = None
    if known == stamp and os.path.exists(cache):
        return cache
    template = wf.read_template(TEMPLATE) if os.path.exists(TEMPLATE) else None
    data = wcards.walk_data(card, template)
    clip = wf.clip_of(data, wm)
    wf.save(cache, clip, data["statics"], data["start"])
    with open(source, "w", encoding="utf-8") as handle:
        json.dump({"card": rel, "stamp": stamp}, handle)
    #  a walk moved into the library (cards.migrate_walks) keeps the mean pose correction its file had
    legacy = wcards.card_name(rel)
    old_fix = mp.path_for(wf.path_for(folder(), legacy))
    if rel == wcards.walk_card(legacy) and os.path.exists(old_fix) and not os.path.exists(mp.path_for(cache)):
        shutil.copy2(old_fix, mp.path_for(cache))
    _forget(cache)
    return cache


def walk_exists(name):
    """Whether the walk `name` can be read (a saved file, or a card that reads or once read)."""
    if not name:
        return False
    if not is_card(name):
        return os.path.exists(wf.path_for(folder(), name))
    try:
        return os.path.exists(walk_path(name))
    except REFUSALS:
        return False


def save_walk_card(root, name=None):
    """The clip under `root` saved as an animation card of the library's `Walk cycles` folder (Walk Builder's
    Save), after reading it the way it will be read; a still taken where a viewport stands. Returns (the walk's
    name - CARD + the card's path - and the status line)."""
    clip, start = read_clip(root)
    bones, note = read_bones(root)
    statics = dict((leaf, {"parent": b["parent"], "canonical": b["canonical"], "rest": b["rest"]})
                   for leaf, b in bones.items() if leaf in clip.names)
    missing = [n for n in clip.names if n not in statics]
    if missing:
        raise Refusal("%d bones of the cycle read twice or unnamed: %s" % (len(missing), ", ".join(missing[:4])))
    data = {"names": clip.names, "parents": clip.parents, "worlds": clip.worlds, "fps": clip.fps, "up": clip.up,
            "name": wf.safe_name(name or clip.name), "statics": statics, "start": start}
    cleaned, report = _clean_data(data, wc.knobs())
    walk = wm.analyse(cleaned)
    from maya_poselib import store
    library = wcards.library_root(_cmds())
    title = store.unique_name(library, wcards.WALK_FOLDER, data["name"])
    data["name"] = title
    header, frames = wcards.card_of_walk(data)
    thumbnail = os.path.join(folder(), CARD_CACHE, "still.part.jpg")
    try:
        from maya_poselib import capture
        if not os.path.isdir(os.path.dirname(thumbnail)):
            os.makedirs(os.path.dirname(thumbnail))
        ok = capture.thumbnail(thumbnail, kind="anim")[0]
    except Exception:                                        # noqa: BLE001 - no viewport: a card with no still
        ok = False
    try:
        path = store.write(library, wcards.WALK_FOLDER, title, header, frames=frames,
                           thumbnail=thumbnail if ok and os.path.exists(thumbnail) else None)
    finally:
        if os.path.exists(thumbnail):
            os.remove(thumbnail)
    line = "saved the walk card %s/%s | %s" % (wcards.WALK_FOLDER, title, walk.summary())
    if report.changed:
        line += " | " + report.short()
    return card_walk(wcards.relative(path, library)), line + (" | " + note if note else "")


def load_walk(name, given=None):
    """(Walk, statics, first frame, clean Report) of a saved walk (or an animation card, `walk_path`) read under
    the clean knobs in `given`, cached by the file's time and the knobs."""
    path = walk_path(name)
    if not os.path.exists(path):
        raise Refusal("no saved walk named %s" % name)
    stamp = os.path.getmtime(path)
    loaded = _state()["loaded"].get(path)
    if loaded is None or loaded[0] != stamp:
        loaded = (stamp, wf.load(path))
        _state()["loaded"][path] = loaded
    data = loaded[1]
    knobs = wc.knobs(given)
    fix_path = mp.path_for(path)
    fix_stamp = os.path.getmtime(fix_path) if os.path.exists(fix_path) else None
    key = ("walk", path, stamp, tuple(sorted(knobs.items())), fix_stamp)
    walk = _state()["loaded"].get(key)
    report = _cleaned(path, stamp, data, knobs)[1]
    if walk is None:
        # the animator's correction of the mean pose (the Mean pose rig, maya_walk.meanrig): the upper body's in
        # the frames before the analysis, the legs' on the walk
        fix = mp.load(fix_path)
        walk = wm.analyse(mp.correct(_cleaned(path, stamp, data, knobs)[0], fix))
        walk.fix = mp.model_fix(fix)
        _cache(key, walk)
    return walk, data["statics"], int(data["start"]), report


def walk_fix(name):
    """(the correction of the saved walk `name`, its file's path)."""
    path = mp.path_for(walk_path(name))
    return mp.load(path), path


BACKUP = ".orig"          # Fix posture keeps the walk's file as it was beside it: <name>.walk.gz.orig


def fix_posture(name, given=None):
    """Fix posture (the card's button): the saved walk `name` read as it will be read (looped, its seam closed at
    the Seam in `given`, not smoothed), its posture set right against the UE5 idle, and written back into its
    file - the file as it was kept once beside it (BACKUP). Nothing out of place: the file untouched. Returns
    (the clean Report, the status line)."""
    path = walk_path(name)
    if not os.path.exists(path):
        raise Refusal("no saved walk named %s" % name)
    data = wf.load(path)
    knobs = wc.knobs(dict(given or {}, smooth=0.0))
    clip, report = _clean_data(data, knobs, posture_fix=True)
    fixed = [text for step, text, _ in report.lines if step == "posture"]
    if not fixed:
        why = ("; " + report.notes[0]) if report.notes else ""
        return report, "Fix posture: %s - nothing out of place%s" % (walk_label(name), why)
    backup = path + BACKUP
    if not os.path.exists(backup):
        shutil.copy2(path, backup)
    clip.name = data.get("name") or name
    wf.save(path, clip, data["statics"], int(data["start"]))
    _forget(path)
    return report, "Fix posture: %s %s | saved, the original in %s" % (walk_label(name), "; ".join(fixed),
                                                                       os.path.basename(backup))


def walk_names():
    return wf.names_in(folder())


# ---- poses ----

def pose_names():
    return wf.pose_names_in(folder())


def save_pose(root, name=None):
    """The skeleton under `root` as it stands at the current frame, saved to the walks folder as <name>.wpose.gz (the
    tool's rest rule). Returns (the pose's name, the status line)."""
    bones, note = read_bones(root)
    name = wf.safe_name(name or _short(root).split(":")[-1] + "_pose")
    path = wf.pose_path_for(folder(), name)
    wf.save_pose(path, name, bones)
    _state()["loaded"].pop(path, None)
    line = "saved %s: %d bones of %s at frame %g" % (os.path.basename(path), len(bones), _short(root),
                                                     _cmds().currentTime(query=True))
    return name, line + (" | " + note if note else "")


def prepared_pose(walk_name, pose_name, given=None, bones=None, ident=None):
    """The pose carried onto the walk `walk_name`'s skeleton (walkpose.prepare) - the walk read under the clean
    knobs in `given` - cached by the walk's file time, the pose's and the walk's reading. The pose: `bones`
    (a Pose Library card's, or the copy on a skeleton - `ident` names it for the cache, with its time), else the
    saved `.wpose` pose `pose_name`."""
    walk, statics = load_walk(walk_name, given)[:2]
    walk_file = walk_path(walk_name)
    if bones is None:
        path = wf.pose_path_for(folder(), pose_name)
        if not os.path.exists(path):
            raise Refusal("no saved pose named %s" % pose_name)
        ident = (path, os.path.getmtime(path))
    key = ("pose", walk_file, ident[0], id(walk))
    stamp = (os.path.getmtime(walk_file), ident[1])
    cached = _state()["loaded"].get(key)
    if cached is None or cached[0] != stamp or cached[2] is not walk:   # an id is reused once a walk is evicted
        if bones is None:
            bones = wf.load_pose(ident[0])[1]
        cached = (stamp, wp.prepare(walk, statics, bones, wm, wt), walk)
        _cache(key, cached)
    return cached[1]


def pose_copy(root):
    """The packed pose copy a walked skeleton keeps (POSE_COPY), or ""."""
    cmds = _cmds()
    if root and cmds.attributeQuery(POSE_COPY, node=root, exists=True):
        return cmds.getAttr(root + "." + POSE_COPY) or ""
    return ""


def card_pose(pose_card=None, pose_name=None, root=None):
    """(name, bones, note, ident) of the pose a press means: the Pose Library card `pose_card` (relative to the
    library), else the copy on `root`'s skeleton; or an old `.wpose` pose `pose_name` (a skeleton walked before
    the cards: its migrated card first). (None, None, note, None) with none."""
    library = wcards.library_root(_cmds())
    copy = pose_copy(root)
    name, bones, note = wcards.resolve(pose_card, copy, pose_name, library, folder())
    if bones is None:
        return None, None, note, None
    if pose_card and not note:
        path = wcards.absolute(pose_card, library)
        return name, bones, note, (path, wcards.stamp(path))
    if not pose_card and pose_name and not note:
        migrated = wcards.absolute(wcards.legacy_card(pose_name), library)
        if os.path.isdir(migrated):
            return name, bones, note, (migrated, wcards.stamp(migrated))
        path = wf.pose_path_for(folder(), pose_name)
        return name, bones, note, (path, os.path.getmtime(path))
    return name, bones, note, ("copy:" + (pose_card or pose_name or ""), hash(copy))


# ---- the marker on a walked skeleton ----

def memo_of(root):
    cmds = _cmds()
    if not cmds.attributeQuery(MARKER, node=root, exists=True):
        return {}
    try:
        memo = json.loads(cmds.getAttr(root + "." + MARKER) or "{}")
    except ValueError:
        return {}
    return memo if memo.get("version") == VERSION else {}


def _set_memo(root, memo):
    cmds = _cmds()
    if not cmds.attributeQuery(MARKER, node=root, exists=True):
        cmds.addAttr(root, longName=MARKER, dataType="string")
    cmds.setAttr(root + "." + MARKER, json.dumps(memo), type="string")


# ---- the keys ----

def _parent_world(bones, leaf, final):
    """The world the bone's local is read against: its parent bone's new world, or - the top joint - the
    node above it as it stands."""
    parent = bones[leaf]["parent"]
    if parent in final:
        return final[parent]
    above = _cmds().listRelatives(bones[leaf]["path"], parent=True, fullPath=True)
    om = _om()
    return om.MMatrix(_cmds().getAttr(above[0] + ".worldMatrix[0]")) if above else om.MMatrix()


def channel_values(bones, frames, written, translated):
    """{path: {channel: [value a frame]}}: rotate for every written bone, translate for the translated
    ones (radians for rotations - the curves' internal unit), each frame's euler nearest the frame before;
    and {path: (tx, ty, tz)} - the written bones whose translation is static (their rest local)."""
    from maya_poselib import skelsolve
    cmds = _cmds()
    tops = {}
    out, static = {}, {}
    for leaf in written:
        bone = bones[leaf]
        path = bone["path"]
        current = [float(v) for v in cmds.getAttr(path + ".rotate")[0]]
        values = dict((ch, []) for ch in (CHANNELS if leaf in translated else ROTATE))
        for final in frames:
            if bone["parent"] not in final and leaf not in tops:
                tops[leaf] = _parent_world(bones, leaf, final)
            parent = final[bone["parent"]] if bone["parent"] in final else tops[leaf]
            local = final[leaf] * parent.inverse()
            turn = skelsolve.joint_channels(local, bone["jointOrient"], bone["rotateAxis"],
                                            bone["rotateOrder"], current)
            current = list(turn)
            for i, ch in enumerate(ROTATE):
                values[ch].append(math.radians(turn[i]))
            if leaf in translated:
                for i, ch in enumerate(TRANSLATE):
                    values[ch].append(float(local[12 + i]))
        out[path] = values
        if leaf not in translated:
            first = frames[0]
            parent = first[bone["parent"]] if bone["parent"] in first else tops[leaf]
            local = first[leaf] * parent.inverse()
            static[path] = (local[12], local[13], local[14])
    return out, static


_BLEND_INPUT = {"outputX": "inputAX", "outputY": "inputAY", "outputZ": "inputAZ", "output": "inputA"}


def base_input(plug):
    """(the plug the walk's curve drives, the curve standing there or None): the channel itself, or - under
    animation layers - the base layer's input at the bottom of its blend chain, so a layer the animator keys
    corrections on stays on top of every re-key. A channel driven by anything else (a constraint, an
    expression) is refused by name."""
    cmds = _cmds()
    dest = plug
    for _ in range(64):
        source = cmds.listConnections(dest, source=True, destination=False, plugs=True,
                                      skipConversionNodes=True) or []
        if not source:
            return dest, None
        node, attr = source[0].split(".", 1)
        kind = cmds.nodeType(node)
        if kind.startswith("animCurve"):
            return dest, node
        if not kind.startswith("animBlendNode") or attr not in _BLEND_INPUT:
            raise Refusal("%s is driven by %s (%s) - the walk keys only channels that are free, keyed or under "
                          "animation layers" % (_short(plug), node, kind))
        dest = node + "." + _BLEND_INPUT[attr]
    raise Refusal("%s: an animation layer chain this tool cannot follow" % _short(plug))


def _rekey(curve, kind):
    """The curve `curve` emptied of its keys through the API (a cmds cut that empties a curve deletes it, trap
    210) - when it is a plain unreferenced curve of `kind`; answers whether it was."""
    cmds, om, oma = _cmds(), _om(), _oma()
    if cmds.nodeType(curve) != kind or cmds.referenceQuery(curve, isNodeReferenced=True):
        return False
    selection = om.MSelectionList()
    selection.add(curve)
    fn = oma.MFnAnimCurve(selection.getDependNode(0))
    for i in range(fn.numKeys - 1, -1, -1):
        fn.remove(i)
    return True


def write_curves(values, static, start, in_place=False):
    """Each written channel's old curve deleted and a new one keyed on frames start..start+N (auto
    tangents): nodes through cmds (Ctrl+Z removes them and puts deleted ones back), keys through
    MFnAnimCurve.addKeys (trap 224). Under animation layers the base layer is what is re-keyed (base_input):
    the layers above it - an animator's corrections - stay. A static translate: its curves deleted, the value
    set. `in_place` (an unrecorded re-key, the Mean pose rig's): a standing curve keeps its node and only its
    keys are written again - no node made or deleted behind the undo queue's back, so an older undo step still
    finds the nodes it made. A channel something else drives (a weapon's link on weapon_r, the animator's
    constraint) is left to its driver: answers (channels written, {bone: what drives it} left alone)."""
    cmds, om, oma = _cmds(), _om(), _oma()
    written = 0
    plans, held = {}, {}
    keys = [(path, ch) for path, channels in values.items() for ch in channels]
    keys += [(path, ch) for path in static for ch in TRANSLATE]
    for path, ch in keys:
        try:
            plans[(path, ch)] = base_input(path + "." + ch)
        except Refusal:
            source = cmds.listConnections(path + "." + ch, source=True, destination=False,
                                          skipConversionNodes=True) or ["?"]
            held.setdefault(_short(path), source[0])
    for path, channels in values.items():
        for ch, vals in channels.items():
            plug = path + "." + ch
            if (path, ch) not in plans:
                continue
            dest, old = plans[(path, ch)]
            kind = "animCurveTL" if ch in TRANSLATE else "animCurveTA"
            if old and in_place and _rekey(old, kind):
                curve = old
            else:
                if old:
                    cmds.delete(old)
                if dest == plug and cmds.getAttr(plug, lock=True):
                    cmds.setAttr(plug, lock=False)
                curve = cmds.createNode(kind, name="%s_%s" % (_short(path).split(":")[-1], ch))
                cmds.connectAttr(curve + ".output", dest)
            times = om.MTimeArray([om.MTime(float(start + f), om.MTime.uiUnit()) for f in range(len(vals))])
            selection = om.MSelectionList()
            selection.add(curve)
            oma.MFnAnimCurve(selection.getDependNode(0)).addKeys(
                times, om.MDoubleArray(vals), oma.MFnAnimCurve.kTangentAuto, oma.MFnAnimCurve.kTangentAuto)
            written += 1
    for path, value in static.items():
        for ch, v in zip(TRANSLATE, value):
            plug = path + "." + ch
            if (path, ch) not in plans:
                continue
            dest, old = plans[(path, ch)]
            if old:
                cmds.delete(old)
            if dest == plug and cmds.getAttr(plug, lock=True):
                cmds.setAttr(plug, lock=False)
            cmds.setAttr(dest, v)
    return written, held


class _Chunk(object):
    """One undo step for a press."""

    def __init__(self, name):
        self.name = name

    def __enter__(self):
        _cmds().undoInfo(openChunk=True, chunkName=self.name)

    def __exit__(self, *exc):
        _cmds().undoInfo(closeChunk=True)
        return False


class Unrecorded(object):
    """Undo recording off for the block, without the flush `undoInfo(state=False)` does, and back as it was (the
    Pose Library's rule). Only outside a chunk: toggled inside one it breaks that chunk (trap 145)."""

    def __enter__(self):
        cmds = _cmds()
        self.was = bool(cmds.undoInfo(query=True, state=True))
        if self.was:
            cmds.undoInfo(stateWithoutFlush=False)

    def __exit__(self, *exc):
        if self.was:
            _cmds().undoInfo(stateWithoutFlush=True)
        return False


# ---- apply, pick ----

def model_knobs(given):
    """The model's share of the card's knobs (a side's own values included): what evaluate() takes."""
    return dict((k, v) for k, v in (given or {}).items() if k in wm.DEFAULTS or k in wm.SIDE_KNOBS)


def apply(root, walk_name, given=None, pose_name=None, parts=ALL_PARTS, record=True, pose_card=None):
    """The saved walk `walk_name` - read under the clean knobs in `given` - keyed onto the
    skeleton under `root` with the model's knobs in `given` (and the pose `pose_name`'s `parts` - walkpose.PARTS
    - at the knob `pose`'s share), from the place it stood when a walk was first put on it (else where it
    stands). One undo step; `record` False (the Mean pose rig's live update): no undo step at all, the curves
    re-keyed in place - Ctrl+Z belongs to the rig. The pose: the Pose Library card `pose_card` (relative to the
    library; the copy kept on the skeleton when the card is gone), else an old saved pose `pose_name`. Returns
    (Result, info, the status line)."""
    started = time.time()
    root = _long(root)
    walk, statics, start, report = load_walk(walk_name, given)
    bones, note = read_bones(root)
    memo = memo_of(root)
    retarget = wt.Retarget(walk, statics, bones, memo.get("place"))
    pose = None
    knobs = model_knobs(given)
    pose_label, pose_note, packed = pose_name or "", "", None
    if not pose_card and pose_name:         # an old pose name: its card when it was moved into the library
        migrated = wcards.legacy_card(pose_name)
        if os.path.isdir(wcards.absolute(migrated, wcards.library_root(_cmds()))):
            pose_card = migrated
    if pose_card:
        pose_label = wcards.card_name(pose_card)
    if (pose_card or pose_name) and wm.knobs(**knobs)["pose"] > 0.0:
        pose_label, pose_bones, pose_note, ident = card_pose(pose_card, pose_name, root)
        if pose_bones is None:
            raise Refusal(pose_note or "no pose to walk in")
        pose = wp.filtered(prepared_pose(walk_name, pose_label, given, bones=pose_bones, ident=ident), parts)
        packed = wcards.pack(pose_bones)
    result = walk.evaluate(knobs, pose)
    frames, info = retarget.frames(result)
    written, translated = retarget.written(), set(retarget.translated())
    values, static = channel_values(bones, frames, written, translated)
    with (_Chunk("skeldarWalkApply") if record else Unrecorded()):
        _, driven = write_curves(values, static, start, in_place=not record)
        if packed is not None and packed != pose_copy(root):
            if not _cmds().attributeQuery(POSE_COPY, node=root, exists=True):
                _cmds().addAttr(root, longName=POSE_COPY, dataType="string")
            _cmds().setAttr(root + "." + POSE_COPY, packed, type="string")
        _set_memo(root, {"walk": walk_name, "pose": pose_label or "", "pose_card": pose_card or "",
                         "parts": list(parts),
                         "knobs": dict(result.info["knobs"], **wc.knobs(given)),
                         "place": wt.pm.flat(retarget.place), "start": start, "version": VERSION,
                         "listed": True})
    _state()["target"] = _cmds().ls(root, uuid=True)[0]
    target_stride = result.info["stride_cm"] * info["scale"]
    #  short: the card's status line holds three lines (2026-10-13, «интерфейс рисуй компактным»)
    text = ("%s on %s, %d bones x%.2f | %d fr (%d-%d), stride %.0f cm, %.2f m/s"
            % (walk_label(walk_name), _short(root), len(written), info["scale"], result.frames, start, start + result.frames,
               target_stride, result.info["speed"] * info["scale"]))
    if pose is not None:
        text += " | pose %s x%.2f%s" % (pose_label, result.info["knobs"]["pose"],
                                         "" if tuple(parts) == ALL_PARTS else " (%s)" % (", ".join(parts) or "no part"))
    matched = result.info.get("leg_match") or {}
    if pose is not None and matched.get("on"):
        text += " | legs matched x%.2f" % matched["keep"]
        if abs(matched.get("hips_deg", 0.0)) >= 1.0:
            text += ", hips %.0f deg to the spine" % abs(matched["hips_deg"])
    if max(info["drop"]) > 0.05:
        text += " | pelvis down %.1f cm where the legs fall short" % max(info["drop"])
    if result.info["lowered"] > 0.05:
        text += " | the walk sinks %.1f cm at the contacts" % result.info["lowered"]
    if info["short"] > 0.05:
        text += " | a foot falls %.1f cm short" % info["short"]
    held = [got for steps in (result.info.get("ground") or {}).values() for asked, got in steps]
    asked = result.info["knobs"]["ground_time"]
    if held and max(abs(g - asked) for g in held) > 0.02:       # the swing's room or both feet up stopped it
        text += " | feet down x%.2f-%.2f of x%.2f asked" % (min(held), max(held), asked)
    balance = result.info.get("balance") or {}
    if balance.get("note"):
        text += " | no balance: " + balance["note"]
    elif balance.get("carry", 0.0) > 0.1:
        text += " | balance carries the pelvis %.1f cm" % balance["carry"]
    used = result.info["knobs"]
    if used.get("in_place", 0.0) >= 0.5:
        text += " | in place"
    fix = walk_fix(walk_name)[0]
    if not mp.is_empty(fix):
        text += " | mean pose corrected (%s)" % mp.summary(fix)
    if report.changed:
        text += " | " + report.short()
    if pose_note:
        text += " | " + pose_note
    if driven:
        text += " | left to their drivers: " + ", ".join("%s (%s)" % item for item in sorted(driven.items()))
    if note:
        text += " | " + note
    info["clean"] = report
    return result, info, text + " | %.1f s" % (time.time() - started)


def selected_top():
    """The topmost joint of what the first selected node belongs to (a joint, a mesh skinned to a skeleton),
    else None - cheap, for the card's selection job (no rig check: Apply makes it)."""
    cmds = _cmds()
    selection = cmds.ls(selection=True, long=True) or []
    if not selection:
        return None
    path = selection[0]
    if cmds.nodeType(path) != "joint":
        shapes = cmds.listRelatives(path, shapes=True, fullPath=True, noIntermediate=True) or []
        skins = [s for shape in shapes for s in (cmds.listHistory(shape, pruneDagObjects=True) or [])
                 if cmds.nodeType(s) == "skinCluster"]
        if not skins:
            return None
        found = cmds.ls((cmds.skinCluster(skins[0], query=True, influence=True) or [None])[0], long=True)
        if not found:
            return None
        path = found[0]
    while True:
        above = cmds.listRelatives(path, parent=True, fullPath=True)
        if not above or cmds.nodeType(above[0]) != "joint":
            return path
        path = above[0]


def set_target(root):
    """The skeleton a released knob re-keys."""
    _state()["target"] = _cmds().ls(root, uuid=True)[0] if root else None


def pick(root):
    """(walk name, knobs, pose name, pose parts) a walked skeleton carries; the card's target becomes it."""
    root = _long(root)
    memo = memo_of(root)
    if not memo.get("walk"):
        raise Refusal("%s carries no walk of this tool - Pick one first" % _short(root))
    _state()["target"] = _cmds().ls(root, uuid=True)[0]
    stored = memo.get("knobs", {})
    knobs = wm.knobs(**model_knobs(stored))      # a side's own values too
    knobs.update(wc.knobs(stored))               # the clean's
    return memo["walk"], knobs, memo.get("pose") or None, tuple(memo.get("parts", ALL_PARTS))


def target_root():
    uuid = _state().get("target")
    found = _cmds().ls(uuid, long=True) if uuid else []
    if not found:
        raise Refusal("select a skeleton and press Pick first")
    return found[0]


