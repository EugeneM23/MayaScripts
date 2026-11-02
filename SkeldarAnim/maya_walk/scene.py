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
from . import keyposes as kp
from . import cards as wcards
from . import gait

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(PLUGIN, "assets", "manny_skeleton_template.json")
#  What Fix posture judges a walk's posture against (2026-10-14): the UE5 idle M_Neutral_Stand_Idle_Loop's mean pose
#  over its 302 frames, shipped (without it: the skeleton's rest)
REFERENCE_FILE = os.path.join(PLUGIN, "assets", "walk_reference_ue5.wpose.gz")
#  Every knob the card holds and a walked skeleton remembers: the model's and the clean's (Seam, Smooth - the model
#  never sees them: apply hands each its own)
#  The card's knobs (the engine's own knobs past wm.LEGACY are set by maya_walk.gait, never shown)
ALL_DEFAULTS = dict(dict((k, wm.DEFAULTS[k]) for k in wm.LEGACY), **wc.DEFAULTS)
ALL_RANGES = dict(dict((k, wm.RANGES[k]) for k in wm.LEGACY), **wc.RANGES)
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


REFUSALS = (Refusal, wm.Refusal, wf.Refusal, wt.Refusal, mp.Refusal, kp.Refusal, wcards.Refusal)
#  The pose's bones as a walked skeleton last used them (packed, maya_walk.cards): the walk keeps walking when
#  its Pose Library card is renamed or deleted (2026-10-15)
POSE_COPY = "skeldarWalkPose"
NO_POSE = "(none)"
ALL_PARTS = tuple(part for part, keys in wp.PARTS)
MARKER = "skeldarWalk"
#  The memo: 4 (2026-10-27) the walker's own edits beside it (EDITS_ATTR) and "working" (Pick chose it); 3
#  (2026-10-26) holds the parameters the card set (maya_walk.gait, `params`) beside the model's knobs they gave; 2
#  holds the model's knobs alone - still read, and translated into parameters (memo_params)
VERSION = 4
READ_VERSIONS = (2, 3, 4)
EDITS_ATTR = "skeldarWalkEdits"     # on a walker's top joint: its own edits (2026-10-27)
#  The parameters as a memo and the card hold them: the hand's changes {key: [kind, x]} (gait.stored_change), the
#  keys set by hand (pinned), the macros, the character and its strength, the physics, the pose's share, In place
#  and the clean's knobs (Seam, Smooth)
DEFAULT_PARAMS = {"changes": {}, "pins": [], "macros": {}, "character": "", "strength": 1.0, "physics": True,
                  "pose": 0.0, "in_place": 0.0, "clean": {}, "knee_pops": True}
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
    # the marker asked of Maya once, every namespace (recursive): an attributeQuery on every joint
    # of every tab took 0.13 s on each selection change (2026-10-16)
    for path in cmds.ls("*." + MARKER, recursive=True, objectsOnly=True, type="joint", long=True) or []:
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


WEAPON_HANDS = {"l": "hand_l", "r": "hand_r"}    # the hands Weapon overlap looks in


def weapons_in_hands(root):
    """{side: {"grip": (3,), "tip": (3,)}} - what Weapon overlap swings (model._weapon_swing): every weapon
    the SCENE holds in a hand of the walker under `root`, as two points in that hand's own frame - the
    weapon's own origin (the grip) and the farthest end of its longest axis (the tip), the plugin's blade
    rule, shared with Tools' Aim's target (aim.tip_offset). The weapon's own scale is in them, so the model
    needs no matrix of it.

    A weapon rides its hand rigidly (its weapon space is parent-constrained to the hand with no offset), so
    the relation is read at the current frame and holds over the cycle; a weapon out in the world (on the
    floor, in Connections' World, hung in a 1P chest) is in no hand and is left out, and so is a hand this
    skeleton has not got. {} where the scene holds no weapon of ours, or the plugin's weapon modules are not
    importable.

    Every read goes through the module's own `_cmds()` - the marker lookup too (`commands=`, which a test's
    fake answers): without that the lookup would reach the real `maya.cmds` under a fake and segfault an
    uninitialized mayapy (trap 296). `weaponspace` and `aim` below are reached only once a weapon has been
    found, which under a fake never happens."""
    cmds = _cmds()
    try:
        from maya_scenesetup import bonedrive, weaponspace, aim as weaponaim
        import maya_markers
    except ImportError:
        return {}
    marked = maya_markers.find(bonedrive.MARKER, "transform", commands=cmds)
    if not marked:
        return {}
    joints = cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True) or []
    hands = {}
    for side, leaf in sorted(WEAPON_HANDS.items()):
        for path in joints:
            if path.rsplit("|", 1)[-1].split(":")[-1] == leaf:
                hands[path] = side
                break
    out = {}
    for weapon in marked:
        hand = weaponspace.holding_hand(weapon)
        side = hands.get(hand) if hand else None
        if side is None or side in out:
            continue
        extents = weaponaim.local_extents(weapon)
        tip_local = weaponaim.tip_offset(*extents) if extents else None
        if tip_local is None:
            continue
        rel = (np.array(cmds.getAttr(weapon + ".worldMatrix[0]"), float).reshape(4, 4)
               @ np.linalg.inv(np.array(cmds.getAttr(hand + ".worldMatrix[0]"), float).reshape(4, 4)))
        grip = rel[3, :3]
        out[side] = {"grip": tuple(float(v) for v in grip),
                     "tip": tuple(float(v) for v in (np.asarray(tip_local, float) @ rel[:3, :3] + grip))}
    return out


def weapons_key(weapons):
    """A weapon reading as the evaluation cache's key (evaluated): stable, and a hair's difference in a
    reading does not cost an evaluation."""
    return repr([(side, tuple(round(float(v), 4) for v in weapons[side]["grip"]),
                  tuple(round(float(v), 4) for v in weapons[side]["tip"])) for side in sorted(weapons or {})])


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


def _cleaned(path, stamp, data, given, posture=False):
    """_clean_data of a loaded walk file, cached by the file's time, the knobs and the posture fix."""
    knobs = wc.knobs(given)
    key = ("clean", path, stamp, tuple(sorted(knobs.items())), bool(posture))
    cached = _state()["loaded"].get(key)
    if cached is None:
        cached = _clean_data(data, knobs, posture_fix=bool(posture))
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


#  ...and a third way (2026-10-16, «pick должен брать цикл у каждого скелета и обрабатывать его отдельно»): a
#  skeleton's OWN cycle, read off its keys on its first Pick and kept on its top joint (SOURCE_ATTR: the walk file's
#  gzip bytes, base64) - so it travels with the scene - named OWN + the bytes' digest and read into a walk file of
#  its own under OWN_CACHE (the mean pose's correction and Fix posture live beside that file).
OWN = "own:"
OWN_CACHE = "own"
SOURCE_ATTR = "skeldarWalkSource"


def is_own(name):
    return bool(name) and name.startswith(OWN)


def walk_label(name):
    """A walk's name as the animator reads it: a card's name, a file's name, «<character>'s cycle»."""
    if is_own(name):
        owner = _state().setdefault("own_labels", {}).get(name[len(OWN):])
        return "%s's cycle" % owner if owner else "own cycle"
    return wcards.card_name(name[len(CARD):]) if is_card(name) else (name or "")


def has_source(root):
    """Whether `root` keeps its own cycle (its first Pick read it)."""
    return bool(_cmds().attributeQuery(SOURCE_ATTR, node=root, exists=True))


def _own_cache(digest):
    return os.path.join(folder(), OWN_CACHE, digest + wf.SUFFIX)


def own_name(root):
    """The walk name of the cycle `root` keeps, its walk file written when missing."""
    import base64
    import hashlib
    raw = _cmds().getAttr(root + "." + SOURCE_ATTR) or ""
    if not raw:
        raise Refusal("%s keeps no cycle of its own" % _short(root))
    digest = hashlib.sha1(raw.encode("ascii")).hexdigest()[:16]
    _state().setdefault("own_labels", {})[digest] = walker_label(root)
    cache = _own_cache(digest)
    if not os.path.exists(cache):
        if not os.path.isdir(os.path.dirname(cache)):
            os.makedirs(os.path.dirname(cache))
        with open(cache + ".part", "wb") as handle:
            handle.write(base64.b64decode(raw))
        os.replace(cache + ".part", cache)
        _forget(cache)
    return OWN + digest


def has_keys(root):
    """Whether any joint under `root` carries translate / rotate keys."""
    cmds = _cmds()
    joints = [root] + (cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True) or [])
    return any(cmds.keyframe(j, attribute=CHANNELS, query=True, keyframeCount=True) for j in joints)


def keys_print(root):
    """{bone leaf: a digest of its keys on the BASE layer} for every joint under `root` (base_input: an animation
    layer the animator keys corrections on does not count). apply() keeps it on the marker, so new animation put on
    a walked skeleton - a clip imported onto it - is told from the walk's own keys (keys_changed).

    A bone any of whose channels something else DRIVES is left out: the walk writes nothing there, so its keys are
    nobody's to compare (2026-10-29 - it used to be one hash over the whole skeleton, and Add Weapon taking
    weapon_r's curves then read as a new take for ever). A bone with no keys at all is left out too."""
    import hashlib
    cmds = _cmds()
    joints = [root] + (cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True) or [])
    rows, driven = {}, set()
    for joint in joints:
        leaf = _short(joint).split(":")[-1]
        parts = []
        for ch in CHANNELS:
            try:
                curve = base_input(joint + "." + ch)[1]
            except Refusal:                                  # driven by something else: not keys
                driven.add(leaf)
                break
            if not curve:
                continue
            times = cmds.keyframe(curve, query=True, timeChange=True) or []
            values = cmds.keyframe(curve, query=True, valueChange=True) or []
            parts.append(repr((leaf, ch, [round(t, 3) for t in times], [round(v, 4) for v in values])))
        if parts:
            rows.setdefault(leaf, []).extend(parts)          # two joints of one leaf: one row, order-free
    return dict((leaf, hashlib.sha1("".join(sorted(parts)).encode("utf-8")).hexdigest()[:8])
                for leaf, parts in rows.items() if leaf not in driven)


def keys_changed(root):
    """Whether a walked skeleton's keys are no longer the ones the walk wrote (new animation put on it), read bone
    by bone: a bone the marker knew, still carrying keys of its own, must hold the same ones. Left out of the
    question - the walk keys them again on the next press anyway: a bone whose curves something else has taken
    since (Add Weapon on weapon_r, Camera Setup on camera_root, a Tools knot) and a bone with no keys at all. A
    marker from before the per-bone digest (one hash of the whole skeleton) answers False: it cannot tell."""
    memo = memo_of(root)
    known = memo.get("keys")
    if not memo.get("walk") or not isinstance(known, dict) or not known:
        return False
    now = keys_print(root)
    return any(leaf in now and now[leaf] != digest for leaf, digest in known.items())


def drop_source(root):
    """The cycle `root` kept goes (its keys are new animation now: the next Pick reads them)."""
    cmds = _cmds()
    if cmds.attributeQuery(SOURCE_ATTR, node=root, exists=True):
        cmds.deleteAttr(root + "." + SOURCE_ATTR)


def capture_source(root):
    """`root`'s own keys read as its cycle (read_clip, the Save rule) and kept on it - once: a second call answers
    the cycle already kept. Returns the walk name."""
    import base64
    if has_source(root):
        return own_name(root)
    clip, start = read_clip(root)
    bones, _note = read_bones(root)
    statics = dict((leaf, {"parent": b["parent"], "canonical": b["canonical"], "rest": b["rest"]})
                   for leaf, b in bones.items() if leaf in clip.names)
    missing = [n for n in clip.names if n not in statics]
    if missing:
        raise Refusal("%d bones of %s read twice or unnamed: %s"
                      % (len(missing), _short(root), ", ".join(missing[:4])))
    clip.name = wf.safe_name(walker_label(root))
    temporary = os.path.join(folder(), OWN_CACHE, "capture.part" + wf.SUFFIX)
    wf.save(temporary, clip, statics, start)
    with open(temporary, "rb") as handle:
        raw = base64.b64encode(handle.read()).decode("ascii")
    os.remove(temporary)
    cmds = _cmds()
    cmds.addAttr(root, longName=SOURCE_ATTR, dataType="string")
    cmds.setAttr(root + "." + SOURCE_ATTR, raw, type="string")
    return own_name(root)


def _sync_own(digest):
    """The walk file of an own cycle written from whichever skeleton in the scene keeps it."""
    cmds = _cmds()
    for path in cmds.ls(type="joint", long=True) or []:
        if cmds.attributeQuery(SOURCE_ATTR, node=path, exists=True):
            try:
                if own_name(path) == OWN + digest:
                    return True
            except Refusal:
                pass
    return False


def restore_source(root):
    """`root`'s own cycle keyed back as it was read (every joint, every frame) and the walk taken off: the marker
    and the kept cycle go. One undo step. Returns the line."""
    if not has_source(root):
        raise Refusal("%s keeps no original cycle (it took a walk card on no keys of its own)" % walker_label(root))
    data = wf.load(walk_path(own_name(root)))
    bones, _note = read_bones(root)
    om = _om()
    names = [n for n in data["names"] if n in bones]
    index = dict((n, i) for i, n in enumerate(data["names"]))
    worlds = data["worlds"]
    frames = [dict((n, om.MMatrix([float(v) for v in worlds[index[n], f].reshape(16)])) for n in names)
              for f in range(worlds.shape[1])]
    values, static = channel_values(bones, frames, names, set(names))
    cmds = _cmds()
    with _Chunk("skeldarWalkRestore"):
        write_curves(values, static, int(data.get("start", 0)))
        for attr in (MARKER, SOURCE_ATTR, POSE_COPY):
            if cmds.attributeQuery(attr, node=root, exists=True):
                cmds.deleteAttr(root + "." + attr)
    return "%s: its original keys back (%d frames), out of the list" % (walker_label(root), worlds.shape[1])


def card_walk(rel):
    """The walk name of the animation card `rel` (relative to the library)."""
    return CARD + rel


def _card_cache(rel):
    return os.path.join(folder(), CARD_CACHE, wf.safe_name(rel.replace("/", "__")) + wf.SUFFIX)


def walk_path(name):
    """The walk file a walk `name` reads: a saved walk's, or the one an animation card is read into - written
    when it is missing or the card changed (a card gone keeps the walk it gave). Refused: no such walk."""
    if is_own(name):
        cache = _own_cache(name[len(OWN):])
        if os.path.exists(cache) or _sync_own(name[len(OWN):]):
            return cache
        raise Refusal("no skeleton in the scene keeps %s" % walk_label(name))
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
    if is_own(name):
        try:
            return os.path.exists(walk_path(name))
        except REFUSALS:
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


def load_walk(name, given=None, edits=None):
    """(Walk, statics, first frame, clean Report) of a saved walk (or an animation card, `walk_path`) read under
    the clean knobs in `given` and a walker's `edits` (edits_of: its Fix posture, its mean pose correction) - none:
    the walk as the library has it. Nothing beside the walk's file is read: a walker's edits are its own
    (2026-10-27, «Текущая походка загруженная из библиотеки не должна пострадать»). The key poses' edits go on the
    evaluated animation (keyposes.on_result), not here. Cached by the file's time, the knobs and the edits."""
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
    edits = edits or {}
    fix = edits.get("fix") or mp.empty()
    posture = bool(edits.get("posture"))
    key = ("walk", path, stamp, tuple(sorted(knobs.items())), json.dumps(mp.dumps(fix), sort_keys=True), posture)
    walk = _state()["loaded"].get(key)
    report = _cleaned(path, stamp, data, knobs, posture)[1]
    if walk is None:
        walk = wm.analyse(mp.correct(_cleaned(path, stamp, data, knobs, posture)[0], fix))
        steps, note = None, ""
        try:
            steps = kp.find(walk)
        except kp.Refusal as error:
            note = str(error)
        walk.key_steps, walk.key_note = steps, note
        walk.fix = mp.model_fix(fix)
        _cache(key, walk)
    return walk, data["statics"], int(data["start"]), report


def walk_fix(name):
    """(the correction of the saved walk `name`, its file's path)."""
    path = mp.path_for(walk_path(name))
    return mp.load(path), path


def walk_keys(name):
    """(the key poses' edits of the saved walk `name`, their file's path)."""
    path = kp.path_for(walk_path(name))
    return kp.load(path), path


BACKUP = ".orig"          # Fix posture keeps the walk's file as it was beside it: <name>.walk.gz.orig


def fix_posture(name, given=None):
    """What Fix posture sets right on the walk `name` - read as it will be read (looped, its seam closed at the
    Seam in `given`, not smoothed), its posture against the UE5 idle: (the clean Report, the status line, whether
    anything was out of place). Nothing is written: the working walkers take it as their edit (edits "posture",
    2026-10-27 - the library's walk is never touched)."""
    path = walk_path(name)
    if not os.path.exists(path):
        raise Refusal("no saved walk named %s" % name)
    data = wf.load(path)
    knobs = wc.knobs(dict(given or {}, smooth=0.0))
    report = _clean_data(data, knobs, posture_fix=True)[1]
    fixed = [text for step, text, _ in report.lines if step == "posture"]
    if not fixed:
        why = ("; " + report.notes[0]) if report.notes else ""
        return report, "Fix posture: %s - nothing out of place%s" % (walk_label(name), why), False
    return report, "Fix posture: %s %s" % (walk_label(name), "; ".join(fixed)), True


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
    if not isinstance(memo, dict):        # JSON, but no memo: one such attribute broke `walkers()` (2026-10-27)
        return {}
    return memo if memo.get("version") in READ_VERSIONS else {}


def _set_memo(root, memo):
    cmds = _cmds()
    if not cmds.attributeQuery(MARKER, node=root, exists=True):
        cmds.addAttr(root, longName=MARKER, dataType="string")
    cmds.setAttr(root + "." + MARKER, json.dumps(memo), type="string")


# ---- the walkers Pick chose, and their own edits (2026-10-27) ----

def working():
    """The walkers Pick chose (or rows clicked in the card's list): every change the card makes keys them,
    whatever is selected (2026-10-27, «все наши изменения попадут на нее в независимости от выделения»)."""
    return [r for r in walkers() if memo_of(r).get("working")]


def set_working(roots):
    """`roots` the working walkers, every other walker not (unrecorded)."""
    keep = set()
    for root in roots or ():
        try:
            keep.add(_long(root))
        except Refusal:
            pass
    with Unrecorded():
        for root in walkers():
            memo = memo_of(root)
            want = root in keep
            if memo and bool(memo.get("working")) != want:
                memo["working"] = want
                _set_memo(root, memo)


def empty_edits(walk=""):
    return {"walk": walk or "", "fix": mp.empty(), "keys": kp.empty(), "posture": False}


def edits_empty(edits):
    return (not edits or (mp.is_empty(edits.get("fix") or mp.empty()) and kp.is_empty(edits.get("keys"))
                          and not edits.get("posture")))


def edits_of(root):
    """The walker `root`'s own edits {"walk", "fix" (the mean pose's correction), "keys" (the key poses'),
    "posture" (Fix posture on)}, or None when it keeps none."""
    cmds = _cmds()
    if not root or not cmds.objExists(root) or not cmds.attributeQuery(EDITS_ATTR, node=root, exists=True):
        return None
    try:
        raw = json.loads(cmds.getAttr(root + "." + EDITS_ATTR) or "{}")
    except ValueError:
        return None
    if not isinstance(raw, dict):
        return None
    out = empty_edits(raw.get("walk"))
    # each read on its own (2026-10-27): a correction this build cannot read took the key poses' edits with it
    try:
        out["fix"] = mp.loads(raw.get("fix") or {})
    except mp.Refusal:
        pass
    try:
        out["keys"] = kp.loads(raw.get("keys") or {})
    except kp.Refusal:
        pass
    out["posture"] = bool(raw.get("posture", False))
    return out


def set_edits(root, edits):
    """The walker `root`'s own edits written - unrecorded (Ctrl+Z is the rig's, or the press's own)."""
    cmds = _cmds()
    data = {"walk": (edits or {}).get("walk") or "", "fix": mp.dumps((edits or {}).get("fix") or mp.empty()),
            "keys": kp.dumps((edits or {}).get("keys") or {}), "posture": bool((edits or {}).get("posture"))}
    with Unrecorded():
        if not cmds.attributeQuery(EDITS_ATTR, node=root, exists=True):
            cmds.addAttr(root, longName=EDITS_ATTR, dataType="string")
        cmds.setAttr(root + "." + EDITS_ATTR, json.dumps(data), type="string")


def walker_edits(root, walk_name):
    """(the edits `root` walks `walk_name` with, a note): its own; another walk's dropped (a new walk starts clean,
    said); none kept by a walker keyed before them (memo version under 4): its cycle's old mean pose file, once, so
    it walks as it did (the old key pose files were read with a measure that misread the rigs, 2026-10-27 - not
    carried)."""
    edits = edits_of(root)
    note = ""
    if edits is None:
        memo = memo_of(root)
        edits = empty_edits(walk_name)
        if memo.get("walk") == walk_name and int(memo.get("version", 0) or 0) < VERSION and walk_exists(walk_name):
            try:
                legacy = mp.load(mp.path_for(walk_path(walk_name)))
            except mp.Refusal:
                legacy = mp.empty()
            if not mp.is_empty(legacy):
                edits["fix"] = legacy
                note = "the cycle's old mean pose correction carried onto %s" % walker_label(root)
        return edits, note
    if edits.get("walk") and edits["walk"] != walk_name:
        if not edits_empty(edits):
            note = "%s's edits of %s dropped (another walk)" % (walker_label(root), walk_label(edits["walk"]))
        return empty_edits(walk_name), note
    edits["walk"] = walk_name
    return edits, note


def edits_line(edits):
    """«mean pose corrected (...) | key poses: Contact edited | posture fixed» - what a walker's edits hold."""
    parts = []
    if edits and not mp.is_empty(edits.get("fix") or mp.empty()):
        parts.append("mean pose corrected (%s)" % mp.summary(edits["fix"]))
    if edits and not kp.is_empty(edits.get("keys")):
        parts.append("key poses: %s" % kp.summary(edits["keys"]))
    if edits and edits.get("posture"):
        parts.append("posture fixed")
    return " | ".join(parts)


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
                curve = cmds.createNode(kind, name="%s_%s" % (_short(path).split(":")[-1], ch),
                                        skipSelect=True)      # a press leaves the animator's selection as it was
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

def normal_params(params):
    """`params` (a memo's, the card's) with every field in its kind: changes {key: (kind, x)} of known keys only,
    pins a sorted list, the rest filled from DEFAULT_PARAMS."""
    out = dict(DEFAULT_PARAMS)
    out.update(params or {})
    keys = set(gait.keys())
    changes = {}
    for key, change in (out.get("changes") or {}).items():
        try:
            kind, x = change
            if key in keys and kind in ("ratio", "offset"):
                changes[key] = (str(kind), float(x))
        except (TypeError, ValueError):
            continue
    out["changes"] = changes
    out["pins"] = sorted(k for k in (out.get("pins") or ()) if k in keys)
    out["macros"] = dict((k, float(v)) for k, v in (out.get("macros") or {}).items()
                         if k in ("weight", "speed") and v not in (None, ""))
    out["character"] = out.get("character") if out.get("character") in gait.CHARACTER else ""
    out["strength"] = float(out.get("strength", 1.0) or 0.0)
    out["physics"] = bool(out.get("physics", True))
    out["knee_pops"] = bool(out.get("knee_pops", True))
    out["pose"] = float(out.get("pose", 0.0) or 0.0)
    out["in_place"] = 1.0 if float(out.get("in_place", 0.0) or 0.0) >= 0.5 else 0.0
    out["clean"] = wc.knobs(out.get("clean") or {})
    return out


def shift_params(params, common):
    """`params` (normal_params) with the parameters in `common` ({"height": cm, "forward": cm} - what the key rigs
    moved alike on all four keys, keyposes.split_common) moved by that many cm, each an offset change pinned
    (2026-10-27, «цикл должен измениться по умному»)."""
    out = normal_params(params)
    changes, pins = dict(out["changes"]), set(out["pins"])
    for key, d in (common or {}).items():
        if abs(float(d)) < 1e-9 or key not in gait.P:
            continue
        kind, x = changes.get(key, ("offset", 0.0))
        changes[key] = ("offset", (float(x) if kind == "offset" else 0.0) + float(d))
        pins.add(key)
    out["changes"], out["pins"] = changes, sorted(pins)
    return out


def plain_params(params):
    """The parameters as JSON holds them (a change a list)."""
    out = normal_params(params)
    out["changes"] = dict((k, [kind, x]) for k, (kind, x) in out["changes"].items())
    return out


def param_values(walk, params):
    """(the walk's own parameters, the parameters' values {key: value}) of `params` on `walk`."""
    params = normal_params(params)
    own = gait.own(walk)
    return own, gait.values(own, params["changes"], params["pins"], params["macros"], params["character"] or None,
                            params["strength"])


def output_fps():
    """Frames a second the keyed cycle lands at: the scene's own time unit (what Arm overlap's milliseconds
    are counted in), 30 where there is no Maya to ask."""
    try:
        return wcards.fps_of(_cmds().currentUnit(q=True, time=True))
    except Exception:
        return 30.0


def params_knobs(walk, params):
    """(maya_walk.model's knobs, the parameters' values) for the parameters `params` on `walk`: gait.engine_knobs,
    the pose's share and In place beside them."""
    params = normal_params(params)
    own, vals = param_values(walk, params)
    knobs = gait.engine_knobs(walk, own, vals, pins=params["pins"], physics=params["physics"],
                              fps_out=output_fps())
    knobs["pose"] = params["pose"]
    if params["in_place"]:
        knobs["in_place"] = 1.0
    return knobs, vals


def memo_params(root=None, memo=None, translate=True):
    """The parameters a walked skeleton carries: a version 3 memo's own; a version 2's (the model's knobs) read as
    parameters through gait.from_legacy - `translate` False: None for those. None for a skeleton walked by none."""
    memo = memo_of(root) if memo is None else memo
    if not memo.get("walk"):
        return None
    if isinstance(memo.get("params"), dict):
        return normal_params(memo["params"])
    if not translate:
        return None
    knobs = memo.get("knobs") or {}
    params = normal_params({"pose": knobs.get("pose", 0.0), "in_place": knobs.get("in_place", 0.0),
                            "clean": wc.knobs(knobs)})
    try:
        walk = load_walk(memo["walk"], knobs)[0]
        changes, pins, macros = gait.from_legacy(walk, model_knobs(knobs))
    except REFUSALS + (IOError, OSError, ValueError, KeyError):
        return params
    params.update(normal_params({"changes": changes, "pins": sorted(pins), "macros": macros}))
    params["pose"] = float(knobs.get("pose", 0.0) or 0.0)
    params["in_place"] = 1.0 if float(knobs.get("in_place", 0.0) or 0.0) >= 0.5 else 0.0
    params["clean"] = wc.knobs(knobs)
    return params


def diagnosis(walk, result, own=None):
    """(the result's measured parameters, gait.diagnose's findings)."""
    measured = gait.of_result(walk, result)
    findings = gait.diagnose(measured, own if own is not None else gait.own(walk), result.info,
                             leg=getattr(walk, "leg_length", 0.0), fps=getattr(walk, "fps", 30.0))
    return measured, findings


def model_knobs(given):
    """The model's share of the card's knobs (a side's own values included): what evaluate() takes."""
    return dict((k, v) for k, v in (given or {}).items() if k in wm.DEFAULTS or k in wm.SIDE_KNOBS)


EVALS_KEPT = 4            # a walk's evaluations kept on it, the last ones (two pose cards switched hit them)


def evaluated(walk, knobs, pose, prepared=None, parts=(), weapons=None):
    """walk.evaluate(knobs, pose, weapons) - kept on the walk object, so a re-key asking for knobs, a pose and
    weapons already evaluated skips the model: two pose cards switched back and forth over several walkers
    (2026-10-16; the model is 85 % of a re-key). The key: the model's knobs, the weapons the scene holds
    (weapons_key), and the pose as its prepared object (prepared_pose's, one object while the card and the walk
    stand; held by the entry, so its id is never reused) with its parts. A walk object is one reading of a walk
    file under its clean knobs and correction - a new object when any of them changes - so its entries go with
    it. The last EVALS_KEPT are kept."""
    key = (repr(sorted((knobs or {}).items())), None if pose is None else (id(prepared), tuple(parts)),
           weapons_key(weapons))
    kept = walk.__dict__.setdefault("_skeldar_evals", [])
    for entry in kept:
        if entry[0] == key and entry[1] is (prepared if pose is not None else None):
            kept.remove(entry)
            kept.append(entry)
            return entry[2]
    result = walk.evaluate(knobs, pose, weapons=weapons)
    kept.append((key, prepared if pose is not None else None, result))
    del kept[:-EVALS_KEPT]
    return result


class Animation(object):
    """What a walker walks, read and evaluated (animate): the walk, its statics and first frame, the clean Report,
    the knobs and the parameters asked, the pose's label / note / packed bones, the walker's edits and their notes,
    the evaluated Result (In place in, the key poses' edits on it), `moving` - its frames before In place - and the
    result read as a walk (`rw`) with its key poses (`steps`; None when the result could not be read)."""

    def __init__(self, **kw):
        self.__dict__.update(kw)


def animate(root, walk_name, given=None, pose_name=None, parts=ALL_PARTS, pose_card=None, params=None,
            with_steps=False):
    """The walker `root`'s animation of the saved walk `walk_name` (an Animation), nothing written: the walk read
    under its clean knobs and the walker's own edits (walker_edits: its Fix posture, its mean pose correction),
    evaluated with the parameters (or the model's knobs in `given`), the pose `pose_card` / `pose_name`'s `parts`;
    then the walker's key poses' edits put on the evaluated frames (keyposes.on_result: after the parameters, the
    pose and the physics - the walker shows at each key what its rig shows), In place last. `with_steps`: the
    result read as a walk even with no key edit (the key rigs stand in it)."""
    root = _long(root)
    if params is not None:              # the clean's knobs: the parameters' own, else `given`'s - kept on them
        raw = dict((params or {}).get("clean") or {})
        params = normal_params(dict(params, clean=dict(wc.knobs(given), **raw)))
        given = dict(given or {}, **params["clean"])
    edits, edits_note = walker_edits(root, walk_name)
    walk, statics, start, report = load_walk(walk_name, given, edits)
    if params is not None:
        knobs, values_asked = params_knobs(walk, params)
    else:
        knobs, values_asked = model_knobs(given), None
    pose = prepared = None
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
        prepared = prepared_pose(walk_name, pose_label, given, bones=pose_bones, ident=ident)  # clean: given
        pose = wp.filtered(prepared, parts)
        packed = wcards.pack(pose_bones)
    keys = edits.get("keys") or {}
    amount = float(wm.knobs(**knobs).get("in_place", 0.0))
    rw = steps = None
    layer_note = ""
    weapons = weapons_in_hands(root)       # what Weapon overlap swings (the hands' own weapons)
    if kp.is_empty(keys) and not with_steps:
        result = evaluated(walk, knobs, pose, prepared, parts, weapons)
        moving = result.worlds if amount <= 0.0 else None
    else:
        base = evaluated(walk, dict(knobs, in_place=0.0), pose, prepared, parts, weapons)
        moving, rw, steps, layer_note = kp.on_result(walk, base.worlds, keys)
        worlds = kp.in_place(moving, walk, amount) if amount > 0.0 else moving
        result = wm.Result(worlds, base.frames, dict(base.info, knobs=dict(base.info["knobs"], in_place=amount),
                                                     in_place=amount))
    return Animation(root=root, walk_name=walk_name, given=given, params=params, walk=walk, statics=statics,
                     start=start, report=report, knobs=knobs, values_asked=values_asked, pose=pose,
                     weapons=weapons,
                     pose_label=pose_label, pose_note=pose_note, packed=packed, parts=tuple(parts), edits=edits,
                     edits_note=edits_note, result=result, moving=moving, rw=rw, steps=steps,
                     layer_note=layer_note, pose_card=pose_card)


def walker_animation(root, with_steps=True):
    """The walker `root`'s animation as it was keyed last (its own memo - its walk, settings, pose and parts):
    what the rig poses stand in (maya_walk.keyrig)."""
    memo = memo_of(root)
    if not memo.get("walk"):
        raise Refusal("%s walks nothing of this tool - Pick puts a walk on it" % walker_label(root))
    return animate(root, memo["walk"], memo.get("knobs"), memo.get("pose") or None,
                   tuple(memo.get("parts", ALL_PARTS)), pose_card=memo.get("pose_card") or None,
                   params=memo_params(root, memo, translate=False), with_steps=with_steps)


def apply(root, walk_name, given=None, pose_name=None, parts=ALL_PARTS, record=True, pose_card=None, params=None):
    """The saved walk `walk_name` - read under the clean knobs in `given` and the walker's own edits - keyed onto
    the skeleton under `root` with the model's knobs in `given` (and the pose `pose_name`'s `parts` - walkpose.PARTS
    - at the knob `pose`'s share), from the place it stood when a walk was first put on it (else where it
    stands). `params` (2026-10-26, the card's parameters - normal_params): the model's knobs are the parameters'
    (params_knobs) and `given` gives only the clean's knobs where `params` has none. One undo step; `record` False
    (the rig poses' Update): no undo step at all, the curves re-keyed in place - Ctrl+Z belongs to the rig. The
    pose: the Pose Library card `pose_card` (relative to the library; the copy kept on the skeleton when the card
    is gone), else an old saved pose `pose_name`. Returns (Result, info, the status line); with `params` info
    carries "values" (the parameters asked), "measured" (the result's, gait.measure) and "diagnosis"."""
    started = time.time()
    root = _long(root)
    anim = animate(root, walk_name, given, pose_name, parts, pose_card, params)
    walk, statics, start, report = anim.walk, anim.statics, anim.start, anim.report
    given, params, result = anim.given, anim.params, anim.result
    bones, note = read_bones(root)
    memo = memo_of(root)
    retarget = wt.Retarget(walk, statics, bones, memo.get("place"))
    knee_pops = True if params is None else bool(params.get("knee_pops", True))
    frames, info = retarget.frames(result, knee_pops=knee_pops)
    written, translated = retarget.written(), set(retarget.translated())
    values, static = channel_values(bones, frames, written, translated)
    with (_Chunk("skeldarWalkApply") if record else Unrecorded()):
        _, driven = write_curves(values, static, start, in_place=not record)
        if anim.packed is not None and anim.packed != pose_copy(root):
            if not _cmds().attributeQuery(POSE_COPY, node=root, exists=True):
                _cmds().addAttr(root, longName=POSE_COPY, dataType="string")
            _cmds().setAttr(root + "." + POSE_COPY, anim.packed, type="string")
        stored = {"walk": walk_name, "pose": anim.pose_label or "", "pose_card": anim.pose_card or "",
                  "parts": list(parts),
                  "knobs": dict(result.info["knobs"], **wc.knobs(given)),
                  "place": wt.pm.flat(retarget.place), "start": start, "version": VERSION,
                  "listed": True, "keys": keys_print(root), "working": bool(memo.get("working"))}
        if params is not None:
            stored["params"] = plain_params(params)
        _set_memo(root, stored)
    if anim.edits_note or edits_of(root) is None:          # an edit carried over or dropped: kept as it now is
        set_edits(root, anim.edits)
    _state()["target"] = _cmds().ls(root, uuid=True)[0]
    target_stride = result.info["stride_cm"] * info["scale"]
    #  short: the card's status line holds three lines (2026-10-13, «интерфейс рисуй компактным»)
    text = ("%s on %s, %d bones x%.2f | %d fr (%d-%d), stride %.0f cm, %.2f m/s"
            % (walk_label(walk_name), _short(root), len(written), info["scale"], result.frames, start, start + result.frames,
               target_stride, result.info["speed"] * info["scale"]))
    if anim.pose is not None:
        text += " | pose %s x%.2f%s" % (anim.pose_label, result.info["knobs"]["pose"],
                                         "" if tuple(parts) == ALL_PARTS else " (%s)" % (", ".join(parts) or "no part"))
    swung = (result.info.get("arms") or {}).get("overlap") or {}
    if swung.get("weapon"):
        text += " | the weapon trails %.1f fr (its tip %.1f cm behind)" % (swung["weapon"], swung["weapon_cm"])
    elif any(abs(float((result.info.get("knobs") or {}).get("weapon_overlap" + s, 0.0) or 0.0))
             >= wm.OVERLAP_QUIET for s in ("", "_l", "_r")):
        text += " | no weapon in the hands: Weapon overlap does nothing"
    matched = result.info.get("leg_match") or {}
    if anim.pose is not None and matched.get("on"):
        text += " | legs matched x%.2f" % matched["keep"]
        if abs(matched.get("hips_deg", 0.0)) >= 1.0:
            text += ", hips %.0f deg to the spine" % abs(matched["hips_deg"])
    if max(info["drop"]) > 0.05:
        text += " | pelvis down %.1f cm where the legs fall short" % max(info["drop"])
    pops = info.get("pops") or {}
    if pops.get("fixed"):
        text += " | " + wt.pops_line(pops)
    if result.info["lowered"] > 0.05:
        text += " | the walk sinks %.1f cm at the contacts" % result.info["lowered"]
    if info["short"] > 0.05:
        text += " | a foot falls %.1f cm short" % info["short"]
    held = [step for steps in (result.info.get("ground") or {}).values() for step in steps]
    if held and max(abs(g - a) for a, g in held) > 0.02:        # the swing's room or both feet up stopped it
        if params is not None:                                # Ground time: shares of a stride
            text += " | feet down %.0f-%.0f %% of %.0f %% asked" % (100.0 * min(g for a, g in held),
                                                                  100.0 * max(g for a, g in held),
                                                                  100.0 * held[0][0])
        else:
            text += " | feet down x%.2f-%.2f of x%.2f asked" % (min(g for a, g in held), max(g for a, g in held),
                                                                held[0][0])
    balance = result.info.get("balance") or {}
    if balance.get("note"):
        text += " | no balance: " + balance["note"]
    elif balance.get("carry", 0.0) > 0.1:
        text += " | balance carries the pelvis %.1f cm" % balance["carry"]
    used = result.info["knobs"]
    if used.get("in_place", 0.0) >= 0.5:
        text += " | in place"
    edited = edits_line(anim.edits)
    if edited:
        text += " | " + edited
    for extra in (anim.edits_note, anim.layer_note):
        if extra:
            text += " | " + extra
    if report.changed:
        text += " | " + report.short()
    if anim.pose_note:
        text += " | " + anim.pose_note
    if driven:
        text += " | left to their drivers: " + ", ".join("%s (%s)" % item for item in sorted(driven.items()))
    if note:
        text += " | " + note
    info["clean"] = report
    if params is not None:
        info["values"] = anim.values_asked
        try:
            info["measured"], info["diagnosis"] = diagnosis(walk, result)
        except Exception:                                    # noqa: BLE001 - a measure never fails the keys
            info["measured"], info["diagnosis"] = {}, []
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


