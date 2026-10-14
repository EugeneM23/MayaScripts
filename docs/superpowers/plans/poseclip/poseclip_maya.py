"""poseclip_maya - our poses onto a locomotion clip: the scene. A part of the character carrying the clip
selected, from the Script Editor:

    import sys; sys.path.insert(0, r"C:/!!!Work/MayaScripts/docs/superpowers/plans/poseclip")
    import poseclip_maya as pc
    pc.apply("goblin")                                   # every part, share 1, motion 1
    pc.apply("two_handed_sword", share=0.7, motion=0.8, parts=("torso", "pelvis", "arms", "feet"))

A copy of the character (its group duplicated with everything upstream of it - the skins follow the copy's
joints) stands `offset` cm to its right (a negative offset: to its left) with the pose on the clip; the original
is never written. The next apply of the same pose to the same character replaces that copy. One undo step.

Poses: Walk Builder's (`<userAppDir>/SkeldarWalks/<name>.wpose.gz`, or the folder in the optionVar
`skeldarWalkFolder`) or a path to one. Spec: docs/superpowers/specs/2026-10-14-pose-on-clip-design.md
"""
import gzip
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import poseclip as model  # noqa: E402

TEMPLATE = os.path.join(HERE, "manny_skeleton_template.json")
MARK = "skeldarPoseClip"
POSE_FORMAT = "skeldar.walkpose"
POSE_SUFFIX = ".wpose.gz"
CHANNELS = ("translateX", "translateY", "translateZ", "rotateX", "rotateY", "rotateZ")
CYCLE_START = "(the cycle's posture)"   # the start pose that is the cycle's own mean posture (addendum 4)
FPS = {"game": 15, "film": 24, "pal": 25, "ntsc": 30, "show": 48, "palf": 50, "ntscf": 60}
Refusal = model.Refusal


def _cmds():
    import maya.cmds as cmds
    return cmds


def _om():
    import maya.api.OpenMaya as om
    return om


def _short(path):
    return path.rsplit("|", 1)[-1]


def _leaf(path):
    return _short(path).split(":")[-1]


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

def top_joint(node):
    """The topmost joint of the skeleton `node` belongs to: a joint, a mesh skinned to it, anything else in the
    character's group (its clip label, the group itself) - the shallowest joint under the top node above it."""
    cmds = _cmds()
    path = _long(node)
    if cmds.nodeType(path) != "joint":
        shapes = cmds.listRelatives(path, shapes=True, fullPath=True) or []
        skins = [s for shape in shapes for s in (cmds.listHistory(shape, pruneDagObjects=True) or [])
                 if cmds.nodeType(s) == "skinCluster"]
        if skins:
            path = _long((cmds.skinCluster(skins[0], query=True, influence=True) or [path])[0])
        else:
            below = cmds.listRelatives(path, allDescendents=True, type="joint", fullPath=True) or []
            if not below:
                below = cmds.listRelatives(_top_node(path), allDescendents=True, type="joint", fullPath=True) or []
            if not below:
                raise Refusal("%s holds no skeleton - select a bone or a mesh of the character" % _short(path))
            path = min(below, key=lambda p: (p.count("|"), p))
    while True:
        above = cmds.listRelatives(path, parent=True, fullPath=True)
        if not above or cmds.nodeType(above[0]) != "joint":
            return path
        path = above[0]


def _source_of_copy(root):
    """A root inside one of this tool's copies answers the original's root (the copy's memo names it by UUID);
    any other root answers itself."""
    cmds = _cmds()
    top = _top_node(root)
    if cmds.attributeQuery(MARK, node=top, exists=True):
        try:
            source = json.loads(cmds.getAttr(top + "." + MARK) or "{}").get("source")
        except ValueError:
            source = None
        found = cmds.ls(source, long=True) if source else []
        if found:
            return found[0]
    return root


def clip_roots():
    """The roots of the skeletons in the scene that carry keys, this tool's copies left out."""
    cmds = _cmds()
    out = []
    for path in cmds.ls(type="joint", long=True) or []:
        above = cmds.listRelatives(path, parent=True, fullPath=True)
        if above and cmds.nodeType(above[0]) == "joint":
            continue
        if cmds.attributeQuery(MARK, node=_top_node(path), exists=True):
            continue
        joints = _joints(path)
        if any(cmds.keyframe(j, attribute=ch, query=True, keyframeCount=True) for j in joints[:20]
               for ch in ("translateX", "rotateX")):
            out.append(path)
    return out


def character_root(node=None):
    """The root of the skeleton carrying the clip: `node`'s, else the selection's, else the only keyed
    skeleton in the scene. A copy this tool made answers its original."""
    cmds = _cmds()
    if node is None:
        selection = cmds.ls(selection=True, long=True)
        if selection:
            node = selection[0]
    if node is not None:
        return _source_of_copy(top_joint(node))
    roots = clip_roots()
    if len(roots) == 1:
        return roots[0]
    if not roots:
        raise Refusal("no skeleton in the scene carries keys - import a clip first")
    raise Refusal("%d skeletons carry keys (%s) - select a bone or a mesh of the one you mean"
                  % (len(roots), ", ".join(_short(_top_node(r)) for r in roots)))


def _joints(root):
    cmds = _cmds()
    paths = [root] + (cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True) or [])
    paths.sort(key=lambda p: (p.count("|"), p))
    return paths


def _refuse_a_rig(joints):
    cmds = _cmds()
    for path in joints:
        if cmds.listConnections(path, source=True, destination=False, type="constraint"):
            raise Refusal("%s is driven by a constraint (a rig's game skeleton?) - this version keys skeletons only"
                          % _short(path))


# ---- reading ----

def read_clip(root):
    """The clip under `root` as poseclip.Clip (every joint's world on every whole frame of its keys) and its
    first frame."""
    cmds = _cmds()
    if cmds.currentUnit(query=True, linear=True) != "cm":
        raise Refusal("the scene is not in centimetres")
    joints = _joints(root)
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
        raise Refusal("%s carries no keys - select a character carrying a clip" % _short(root))
    start, end = int(math.floor(min(times) + 1e-6)), int(math.ceil(max(times) - 1e-6))
    worlds = np.array([[cmds.getAttr(p + ".worldMatrix[0]", time=t) for t in range(start, end + 1)]
                       for p in joints]).reshape(len(joints), end - start + 1, 4, 4)
    return model.Clip([_leaf(p) for p in joints], parents, worlds, _fps(), _clip_name(root)), start, joints


def _clip_name(root):
    """The clip's name: the character's clip label when it has one, else the scene's name, else the root."""
    cmds = _cmds()
    top = _top_node(root)
    for t in cmds.listRelatives(top, allDescendents=True, type="transform", fullPath=True) or []:
        if cmds.attributeQuery("skeldarClipLabel", node=t, exists=True):
            value = cmds.getAttr(t + ".skeldarClipLabel")
            if value:
                return value.split(" + ")[0]
    scene = os.path.splitext(os.path.basename(cmds.file(query=True, sceneName=True) or ""))[0]
    return scene or _short(root)


def _rest_world(joint):
    """The joint's bind: the inverse of a skinCluster's bindPreMatrix for it, else None."""
    cmds, om = _cmds(), _om()
    for plug in cmds.listConnections(joint + ".worldMatrix[0]", source=False, destination=True, plugs=True,
                                     type="skinCluster") or []:
        node, attr = plug.split(".", 1)
        if not attr.startswith("matrix["):
            continue
        index = attr[len("matrix["):].split("]")[0]
        bpm = cmds.getAttr("{0}.bindPreMatrix[{1}]".format(node, index))
        if bpm:
            return list(om.MMatrix(bpm).inverse())
    return None


def read_statics(joints, clip, frame):
    """{leaf: {"parent", "canonical", "rest"}} of the clip's skeleton: a skinned joint rests at its bind; an
    unskinned one under a rested parent keeps its local (at `frame`) on its parent's rest; a skeleton with no
    skin whose bones are Manny's rests at Manny's bind (the template); anything else as it stands at `frame`.
    Returns (statics, a note or "")."""
    binds = dict((p, _rest_world(p)) for p in joints)
    note = ""
    template = {}
    if not any(binds.values()) and os.path.exists(TEMPLATE):
        with open(TEMPLATE) as handle:
            template = dict((j["name"], j["world_matrix"]) for j in json.load(handle)["joints"])
        note = "no skin: the rest is Manny's bind (the template)"
    statics, rests = {}, {}
    for i, path in enumerate(joints):
        leaf, p = clip.names[i], clip.parents[i]
        now = clip.worlds[i, frame]
        if binds.get(path):
            rest = np.array(binds[path]).reshape(4, 4)
        elif leaf in template:
            rest = np.array(template[leaf], float).reshape(4, 4)
        elif p >= 0 and p in rests:
            rest = now @ np.linalg.inv(clip.worlds[p, frame]) @ rests[p]
        else:
            rest = now
        rests[i] = rest
        statics[leaf] = {"parent": clip.names[p] if p >= 0 else None, "canonical": leaf,
                         "rest": [float(v) for v in rest.reshape(16)]}
    return statics, note


# ---- poses ----

def pose_folder():
    cmds = _cmds()
    if cmds.optionVar(exists="skeldarWalkFolder"):
        folder = cmds.optionVar(query="skeldarWalkFolder")
        if folder:
            return folder
    return os.path.join(cmds.internalVar(userAppDir=True), "SkeldarWalks")


def pose_names():
    folder = pose_folder()
    if not os.path.isdir(folder):
        return []
    return sorted(f[:-len(POSE_SUFFIX)] for f in os.listdir(folder) if f.endswith(POSE_SUFFIX))


def load_pose(name):
    """(name, bones) of a Walk Builder pose: its name in the walks folder, or a path."""
    path = name if os.path.isfile(name) else os.path.join(pose_folder(), name + POSE_SUFFIX)
    if not os.path.isfile(path):
        raise Refusal("no pose %s (the poses: %s)" % (name, ", ".join(pose_names()) or "none"))
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        data = json.load(handle)
    if data.get("format") != POSE_FORMAT:
        raise Refusal("%s is not a Walk Builder pose" % os.path.basename(path))
    return data["name"], data["bones"]


# ---- the copy ----

def _top_node(root):
    cmds = _cmds()
    path = root
    while True:
        above = cmds.listRelatives(path, parent=True, fullPath=True)
        if not above:
            return path
        path = above[0]


def _uuids(nodes):
    cmds = _cmds()
    return set(cmds.ls(nodes, uuid=True) or []) if nodes else set()


def copies(source_uuid, pose=None, tool=None):
    """{copy top: its memo} of the copies made of the character whose root is `source_uuid`: with the pose
    `pose` (None: any), the window's own (`tool` True), the script's (False) or either (None)."""
    cmds = _cmds()
    out = {}
    for t in cmds.ls("*.%s" % MARK, objectsOnly=True, long=True, recursive=True) or []:
        try:
            memo = json.loads(cmds.getAttr(t + "." + MARK) or "{}")
        except ValueError:
            continue
        if memo.get("source") != source_uuid or (pose is not None and memo.get("pose") != pose):
            continue
        if tool is not None and bool(memo.get("tool")) != tool:
            continue
        out[t] = memo
    return out


def remove_copies(source_uuid, pose=None, tool=None):
    """Every copy `copies` names, and the nodes made with it."""
    cmds = _cmds()
    removed = 0
    for t, memo in copies(source_uuid, pose, tool).items():
        nodes = [n for n in (cmds.ls(memo.get("nodes", []), long=True) or [])]
        for node in [t] + nodes:
            if cmds.objExists(node):
                for plug in ("translate", "rotate", "scale"):
                    try:
                        cmds.setAttr(node + "." + plug, lock=False)
                    except RuntimeError:
                        pass
        leftovers = [n for n in nodes if cmds.objExists(n)]
        if cmds.objExists(t):
            cmds.delete(t)
        leftovers = [n for n in leftovers if cmds.objExists(n)]
        if leftovers:
            cmds.delete(leftovers)
        removed += 1
    return removed


def make_copy(root, name):
    """The character's top node duplicated with everything upstream of it (the skins then follow the copy's
    joints), the copy's animation curves deleted. Returns (copy top, {original joint path: copy joint path},
    every node the duplicate made)."""
    cmds = _cmds()
    top = _top_node(root)
    before = set(cmds.ls(long=True))
    copy = _long(cmds.duplicate(top, upstreamNodes=True, name=name)[0])
    made = [n for n in cmds.ls(long=True) if n not in before]
    curves = [n for n in made if cmds.nodeType(n).startswith("animCurve")]
    if curves:
        cmds.delete(curves)
    made = [n for n in made if cmds.objExists(n)]
    mapping = {}
    for path in _joints(root):
        twin = copy + path[len(top):]
        if cmds.objExists(twin):
            mapping[path] = twin
    return copy, mapping, made


# ---- writing ----

def joint_channels(local, joint_orient, rotate_axis, rotate_order, current):
    """(rx, ry, rz) degrees: `R = RA^-1 . rot(local) . JO^-1` in `rotate_order`, nearest `current` (skelsolve's)."""
    om = _om()
    jo = om.MEulerRotation(*[math.radians(v) for v in joint_orient]).asMatrix()
    ra = om.MEulerRotation(*[math.radians(v) for v in rotate_axis]).asMatrix()
    rot = om.MTransformationMatrix(om.MMatrix([float(v) for v in local.reshape(16)])).asRotateMatrix()
    turn = ra.inverse() * rot * jo.inverse()
    euler = om.MTransformationMatrix(turn).rotation().reorder(int(rotate_order))
    previous = om.MEulerRotation(*([math.radians(v) for v in current] + [int(rotate_order)]))
    euler = euler.closestSolution(previous)
    return (math.degrees(euler.x), math.degrees(euler.y), math.degrees(euler.z))


def write_worlds(paths, worlds, start, kept=None):
    """Key the joints `paths` (parents first; each one's parent either among them or above the skeleton) on
    worlds (J, F, 4, 4) from frame `start`: translate and rotate on every frame (their old curves deleted, scale
    set to 1). Keys through MFnAnimCurve.addKeys (trap 224). A channel something else drives (a weapon's
    constraint on weapon_r, the animator's own) is left to it, its joint added to `kept`. Returns the curves
    made."""
    import maya.api.OpenMayaAnim as oma
    cmds, om = _cmds(), _om()
    J, F = worlds.shape[:2]
    index = dict((p, i) for i, p in enumerate(paths))
    made = 0
    for i, path in enumerate(paths):
        above = cmds.listRelatives(path, parent=True, fullPath=True)
        if above and above[0] in index:
            parent = worlds[index[above[0]]]
        else:
            m = np.array(cmds.getAttr(above[0] + ".worldMatrix[0]")).reshape(4, 4) if above else np.eye(4)
            parent = np.tile(m, (F, 1, 1))
        jo = [float(v) for v in cmds.getAttr(path + ".jointOrient")[0]]
        ra = [float(v) for v in cmds.getAttr(path + ".rotateAxis")[0]]
        order = int(cmds.getAttr(path + ".rotateOrder"))
        current = [float(v) for v in cmds.getAttr(path + ".rotate")[0]]
        values = dict((ch, []) for ch in CHANNELS)
        for f in range(F):
            local = worlds[i, f] @ np.linalg.inv(parent[f])
            turn = joint_channels(local, jo, ra, order, current)
            current = list(turn)
            for k, ch in enumerate(CHANNELS[3:]):
                values[ch].append(math.radians(turn[k]))
            for k, ch in enumerate(CHANNELS[:3]):
                values[ch].append(float(local[3, k]))
        for ch in CHANNELS:
            plug = path + "." + ch
            for old in cmds.listConnections(plug, source=True, destination=False) or []:
                if cmds.nodeType(old).startswith("animCurve"):
                    cmds.delete(old)
            if cmds.listConnections(plug, source=True, destination=False):
                if kept is not None and _leaf(path) not in kept:
                    kept.append(_leaf(path))
                continue
            if cmds.getAttr(plug, lock=True):
                cmds.setAttr(plug, lock=False)
            curve = cmds.createNode("animCurveTL" if ch.startswith("translate") else "animCurveTA",
                                    name="%s_%s" % (_leaf(path), ch))
            cmds.connectAttr(curve + ".output", plug)
            times = om.MTimeArray([om.MTime(float(start + f), om.MTime.uiUnit()) for f in range(F)])
            selection = om.MSelectionList()
            selection.add(curve)
            oma.MFnAnimCurve(selection.getDependNode(0)).addKeys(
                times, om.MDoubleArray(values[ch]), oma.MFnAnimCurve.kTangentAuto, oma.MFnAnimCurve.kTangentAuto)
            made += 1
        for axis in "XYZ":
            plug = path + ".scale" + axis
            if not cmds.listConnections(plug, source=True, destination=False) and not cmds.getAttr(plug, lock=True):
                cmds.setAttr(plug, 1.0)
    return made


class _Chunk(object):
    def __init__(self, name):
        self.name = name

    def __enter__(self):
        _cmds().undoInfo(openChunk=True, chunkName=self.name)

    def __exit__(self, *exc):
        _cmds().undoInfo(closeChunk=True)
        return False


def _right_of(analysis):
    """The character's right on the floor at the reference (from the left thigh to the right one)."""
    a = analysis
    ix = a.clip.index
    v = a.pos[ix["thigh_r"], a.mid] - a.pos[ix["thigh_l"], a.mid]
    v[1] = 0.0
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-9 else np.array([-1.0, 0.0, 0.0])


def _set_text(plug, text):
    """A string attribute set through its lock (the plugin locks its label's), the lock put back; False when it
    cannot be (driven)."""
    cmds = _cmds()
    locked = cmds.getAttr(plug, lock=True)
    try:
        if locked:
            cmds.setAttr(plug, lock=False)
        cmds.setAttr(plug, text, type="string")
        return True
    except RuntimeError:
        return False
    finally:
        if locked:
            cmds.setAttr(plug, lock=True)


def _label(copy, text):
    """The copy's clip label (the plugin's, when the character carries one) reads `text`."""
    cmds = _cmds()
    for t in cmds.listRelatives(copy, allDescendents=True, type="transform", fullPath=True) or []:
        if cmds.attributeQuery("skeldarClipLabel", node=t, exists=True):
            _set_text(t + ".skeldarClipLabel", text)
            for shape in cmds.listRelatives(t, shapes=True, fullPath=True) or []:
                if cmds.nodeType(shape) == "annotationShape":
                    _set_text(shape + ".text", text)


class Session(object):
    """One character's clip read once - the window keeps it between slider moves: the clip, its analysis, its
    skeleton's statics, the poses prepared against it."""

    def __init__(self, root, reference=None):
        cmds = _cmds()
        self.root = _long(root)
        self.uuid = cmds.ls(self.root, uuid=True)[0]
        _refuse_a_rig(_joints(self.root))
        self.clip, self.start, self.joints = read_clip(self.root)
        self.analysis = model.Analysis(self.clip, reference)
        self.statics, self.note = read_statics(self.joints, self.clip, self.analysis.mid)
        self.right = _right_of(self.analysis)
        self.poses = {}

    def alive(self):
        found = _cmds().ls(self.uuid, long=True)
        if found:
            self.root = found[0]
        return bool(found)

    def pose(self, name):
        """(the pose's name, `model.prepare`'s) - prepared once."""
        if name not in self.poses:
            pose_name, bones = load_pose(name)
            self.poses[name] = (pose_name, model.prepare(self.analysis, self.statics, bones))
        return self.poses[name]

    def evaluate(self, pose, k, start=None):
        """The final pose `pose` (and the start pose `start`: a pose's name, CYCLE_START - the cycle's own
        posture -, or None: the final all along) with the knobs `k`, from the cycle when one is set."""
        if start == CYCLE_START:
            if self.posture is None:
                raise Refusal("no cycle to take the posture from - select a looping clip and press Use selected "
                              "as cycle, or pick a start pose")
            begin = self.posture
        else:
            begin = self.pose(start)[1] if start else None
        return model.evaluate(self.analysis, self.pose(pose)[1], k=k, start=begin, cycle=self.cycle)

    def start_label(self, start):
        """How the status line and the copy's label name a start: None, "the cycle's posture", a pose's name."""
        if not start:
            return None
        return "the cycle's posture" if start == CYCLE_START else self.pose(start)[0]

    # -- the cycle the stop starts on --

    cycle = None
    cycle_name = ""
    cycle_uuid = None
    posture = None        # model.CyclePosture: the cycle's mean posture as a start pose

    def use_cycle(self, node):
        """The looping clip on the skeleton `node` belongs to (taken as it is - a copy of ours too) as the cycle
        the stop starts on."""
        root = top_joint(node)
        if _cmds().ls(root, uuid=True)[0] == self.uuid:
            raise Refusal("that is the stop's own character - select the character carrying the cycle")
        clip, _start, joints = read_clip(root)
        self.cycle = model.Cycle(clip)
        statics, _note = read_statics(joints, clip, 0)
        self.posture = model.CyclePosture(self.analysis, self.statics, self.cycle, statics, clip.name)
        self.cycle_name = "%s on %s (%d frames a loop at %g fps)" % (
            clip.name, _short(_top_node(root)), self.cycle.period, clip.fps)
        self.cycle_uuid = _cmds().ls(root, uuid=True)[0]
        return self.cycle_name

    def clear_cycle(self):
        self.cycle, self.cycle_name, self.cycle_uuid, self.posture = None, "", None, None

    def describe(self):
        a = self.analysis
        r0, r1 = a.reference
        contacts = ", ".join("%s %s" % (s.upper(), " ".join("%d-%d" % (self.start + c0, self.start + c1)
                                                           for c0, c1 in a.feet[s]["contacts"])) for s in model.SIDES)
        kind = "still %d-%d (its stance)" % (self.start + r0, self.start + r1) if a.still else \
            "no still stretch - a cycle: its mean"
        return "%s on %s: %d frames from %d | reference %s | contacts %s" % (
            self.clip.name, _short(_top_node(self.root)), self.clip.F, self.start, kind, contacts)

    def key(self, result, pose_name, k, offset, tool=False, start_name=None):
        """The result keyed onto a copy `offset` cm to the character's right: the window's own copy (re-keyed
        in place, its label naming the pose), or - from a script - this pose's copy (made afresh). One undo
        step. Returns (the copy, how many curves, whether an older copy was replaced)."""
        cmds = _cmds()
        worlds = result.worlds.copy()
        worlds[:, :, 3, :3] += float(offset) * self.right
        top = _top_node(self.root)
        base = _short(top)
        base = base[:-len("_Character")] if base.endswith("_Character") else base
        removed = 0
        with _Chunk("skeldarPoseClip"):
            standing = list(copies(self.uuid, tool=True)) if tool else []
            if standing:
                copy, made = standing[0], None
            else:
                removed = remove_copies(self.uuid, None if tool else pose_name, tool=tool)
                name = "%s_posed_Character" % base if tool else "%s_%s_Character" % (base, pose_name)
                copy, _mapping, made = make_copy(self.root, name)
            paths, rows = [], []
            for i, path in enumerate(self.joints):
                twin = copy + path[len(top):]
                if cmds.objExists(twin):
                    paths.append(twin)
                    rows.append(i)
            self.kept = []
            curves = write_worlds(paths, worlds[rows], self.start, self.kept)
            if not cmds.attributeQuery(MARK, node=copy, exists=True):
                cmds.addAttr(copy, longName=MARK, dataType="string")
            memo = {}
            if made is None:
                try:
                    memo = json.loads(cmds.getAttr(copy + "." + MARK) or "{}")
                except ValueError:
                    memo = {}
            memo.update({"source": self.uuid, "pose": pose_name, "start_pose": start_name or "", "tool": bool(tool),
                         "knobs": dict(k), "offset": offset, "reference": list(self.analysis.reference),
                         "start": self.start, "cycle": self.cycle_uuid or ""})
            if made is not None:
                memo["nodes"] = cmds.ls(made, uuid=True) or []
            cmds.setAttr(copy + "." + MARK, json.dumps(memo), type="string")
            first = "cycle" if start_name == "the cycle's posture" else start_name
            _label(copy, "%s + %s" % (self.clip.name, ("%s > %s" % (first, pose_name)) if start_name else pose_name))
        return copy, curves, removed


def status(session, result, pose_name, copy, removed, seconds, start_name=None):
    """The line a run leaves: the pose, the copy, what the rules did."""
    info = result.info
    a = session.analysis
    r0, r1 = a.reference
    poses = ("%s > %s" % (start_name, pose_name)) if start_name else pose_name
    text = "%s on %s: %s | reference %d-%d%s | contacts moved L %d, R %d%s | pelvis carried up to %.1f cm" % (
        poses, session.clip.name, _short(copy), session.start + r0, session.start + r1,
        "" if a.still else " (a cycle)", info["moved"]["l"], info["moved"]["r"],
        ", the last onto the pose's stance" if any(v is not None for v in info["final"].values()) else "",
        info["carry"])
    if info["forward"] < 0.99:
        text += " | the clip's forward lean x%.2f (the pose leans %.0f deg, the clip's idle %.0f)" % (
            info["forward"], info["lean"][1], info["lean"][0])
    if info["drop"] > 0.05:
        text += " | sunk %.1f cm where a planted foot was out of reach" % info["drop"]
    if info["short"] > 0.05:
        text += " | a planted foot falls %.1f cm short" % info["short"]
    if start_name:
        held = info.get("start_frames")
        if held is None:
            text += " | the start pose holds no frame (the body never runs past Final pose at)"
        else:
            text += " | the start pose holds frames %d-%d, the final from %d on" % (
                session.start + held[0], session.start + held[1], session.start + held[1] + 1)
    if info["grip"]:
        text += " | two-handed grip held"
    legs = info.get("legs") or {}
    if legs.get("hips", 0.0) > 0.5:
        text += " | legs matched: the hips %.0f deg to the run (the spine takes it back)" % legs["hips"]
    springs = info.get("overlap") or {}
    if springs:
        text += " | overlap: trunk %.0f, head %.0f deg off their frames, hands %.0f cm" % (
            springs.get("torso", 0.0), springs.get("head", 0.0), springs.get("arms", 0.0))
    cyc = info.get("cycle") or {}
    if cyc:
        text += " | starts on the cycle's frame %.2f (%s), into the stop over %d frames" % (
            cyc["phase"], session.cycle_name.split(" (")[0], cyc["frames"])
    kept = getattr(session, "kept", None)
    if kept:
        text += " | left to what drives them: %s" % ", ".join(kept)
    if removed:
        text += " | the previous copy replaced"
    if session.note:
        text += " | " + session.note
    return text + " | %.1f s" % seconds


def apply(pose, share=1.0, motion=1.0, parts=model.PARTS, offset=150.0, reference=None, node=None, **given):
    """The pose `pose` onto the clip carried by the selected character (or `node`'s, or the only keyed one), on
    a copy of it `offset` cm to its right - this pose's copy, made afresh. `share`, `motion` and `parts` are the
    first version's knobs; any knob of `poseclip.KNOBS` by name overrides them. Returns the status line (also
    printed)."""
    started = time.time()
    session = Session(character_root(node), reference)
    k = model.knobs_from(share, motion, parts)
    if given:
        clamped = model.knobs(**given)
        k.update((n, clamped[n]) for n in given)
    pose_name = session.pose(pose)[0]
    result = session.evaluate(pose, k)
    copy, curves, removed = session.key(result, pose_name, k, offset, tool=False)
    text = status(session, result, pose_name, copy, removed, time.time() - started)
    print(text)
    return text
