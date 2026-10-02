"""Every common source convention onto our rigs and skeletons, in mayapy STANDALONE.

Never in the animator's Maya: it adds rigs and skeletons into empty scenes. Run:

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/verify_skeleton_conventions.py

Spec: docs/superpowers/specs/2026-10-02-skeleton-conventions-design.md

For each convention of tests/skeleton_conventions.py (but Unreal's own, whose road is
verify_rig_pipeline's) a synthetic source is BUILT as Maya joints - its names, its
hierarchy quirks, its joint-axis convention, its rest (in jointOrient, or in the
rotate channels where game exports keep it), its unit and its wrapper - and keyed
(arms raised, knees bent, the spine twisted, the root travelling). Then:

  rigs      Manny_Rig, Creep_Rig, Orc_D_Rig (Add Character into an empty scene),
            the clip through the Retarget button (maya_rig_retarget.run_retarget):
            every mapped bone of the rig's game skeleton POINTS where the source's
            bone points (FK), no bone changes length, the pelvis and the root
            travel as the source's scaled to the rig's size.
  skeletons Manny UE5 [skeleton], Creep [skeleton]: skeletonimport.transfer, the
            same gates.
  rest      the rest choice sets the ROLL only: forced to either candidate, the
            directions still match while the frames differ.
  real      `Downloads/Sweep Fall.fbx` (the animator's Mixamo clip, when present):
            still the MIXAMO schema on the rig, and now onto a skeleton too.
  refusal   a four-legged chain is refused with the map's reason, both roads.
  control   our bones at frame 10 against the source at frame 20: the gate can fail.
"""

import json
import math
import os
import sys
import tempfile
import time
import traceback

import maya.standalone
maya.standalone.initialize(name="python")

import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
PLUGIN = os.path.join(ROOT, "SkeldarAnim").replace("\\", "/")
TESTS = os.path.join(ROOT, "tests").replace("\\", "/")
for path in (TESTS, PLUGIN):
    if path in sys.path:
        sys.path.remove(path)
    sys.path.insert(0, path)
for plugin in ("matrixNodes", "quatNodes", "fbxmaya"):
    cmds.loadPlugin(plugin, quiet=True)

import skeleton_conventions as fixtures  # noqa: E402
import maya_rig_retarget  # noqa: E402
import maya_rigs  # noqa: E402
import maya_skeletonmap as skelmap  # noqa: E402
from maya_scenesetup import catalog, character  # noqa: E402
from maya_uebridge import animimport, rigimport, skeletonimport  # noqa: E402

FRAMES = (0, 5, 10, 15, 20)
ONLY = [c for c in os.environ.get("CONVENTIONS", "").split(",") if c]
SKIP = ("ue5", "ue4")                       # Unreal's own road: verify_rig_pipeline
CONVENTIONS = [c for c in fixtures.CONVENTIONS if c not in SKIP and (not ONLY or c in ONLY)]
RIGS = [r for r in os.environ.get("RIGS", "Manny_Rig,Creep_Rig,Orc_D_Rig").split(",") if r]
SKELETONS = [s for s in os.environ.get("SKELETONS", "Manny,Creep").split(",") if s]
SWEEP = "C:/Users/MY PC/Downloads/Sweep Fall.fbx"
ORIENT = {"mixamo": "yzx", "hik": "yzx", "unity": "yzx", "vrm": "yzx", "rigify": "yzx",
          "arp": "yzx", "cmu": "yzx", "xsens": "yzx", "obfuscated": "yzx",
          "biped": "xzy", "cc": "xyz", "daz": "xyz", "synty": "xyz"}
REST_IN_ROTATE = ("cc", "synty", "unity")   # game exports keep the bind in rotate
DIR_TOL_SKELETON = 0.1                      # deg
LEN_TOL = 1e-3                              # cm
# the Manny rig's own left leg: FKKnee_L stands 0.0637 cm off calf_l (a mirrored fit over
# Manny's 0.068 cm asymmetric calf) and AS's knee does not roll with the bone, so that
# offset wanders with the knee (CLAUDE.md, the twin's Addendum 2) - a rig fact, measured on
# every source alike, not a retarget one
RIG_LEN_TOL = {"Manny_Rig": 0.08}   # CLAUDE.md: "the LEFT leg at 0.06-0.08 cm"
TRAVEL_TOL = 0.05                           # cm

RESULTS = []
REPORT = {}


def gate(label, ok, text):
    RESULTS.append(bool(ok))
    print("%s %-34s %s" % ("PASS" if ok else "FAIL", label, text))
    sys.stdout.flush()
    return ok


# ------------------------------------------------------------------ building

def _ensure_namespace(full):
    parts = full.split(":")
    for i in range(1, len(parts) + 1):
        name = ":".join(parts[:i])
        if not cmds.namespace(exists=":" + name):
            cmds.namespace(add=parts[i - 1], parent=":" + ":".join(parts[:i - 1]))


def build_source(convention, ns):
    """(top joint path, {our bone: source path}, spec) - the convention's rows as
    Maya joints in namespace `ns`, oriented, rest moved where the convention keeps
    it, keyed."""
    rows, expected = fixtures.build(convention)
    spec = fixtures.SPECS.get(convention, fixtures.SPECS["mixamo"])
    _ensure_namespace(ns)
    wrapper = None
    if spec.wrapper:
        wrapper = cmds.createNode("transform", name="%s:%s" % (ns, spec.wrapper), skipSelect=True)
        if spec.wrapper == "BipedZup":
            cmds.setAttr(wrapper + ".rotateX", -90.0)
    made = {}
    for name, parent, pos in rows:
        full = "%s:%s" % (ns, name)
        if ":" in name:
            _ensure_namespace(full.rpartition(":")[0])
        under = made.get(parent) or wrapper
        joint = cmds.createNode("joint", name=full, parent=under, skipSelect=True) if under \
            else cmds.createNode("joint", name=full, skipSelect=True)
        joint = cmds.ls(joint, long=True)[0]
        cmds.xform(joint, worldSpace=True, translation=pos)
        made[name] = cmds.ls(cmds.ls(joint, uuid=True)[0], long=True)[0]
    uuids = dict((n, cmds.ls(p, uuid=True)[0]) for n, p in made.items())

    def path(name):
        return cmds.ls(uuids[name], long=True)[0]
    top = path(rows[0][0])
    cmds.joint(top, edit=True, orientJoint=ORIENT.get(convention, "xyz"),
               secondaryAxisOrient="yup", children=True, zeroScaleOrient=True)
    if convention in REST_IN_ROTATE:
        for name in made:
            j = path(name)
            jo = cmds.getAttr(j + ".jointOrient")[0]
            cmds.setAttr(j + ".jointOrient", 0, 0, 0)
            cmds.setAttr(j + ".rotate", *jo)
    by_ours = dict((o, path(n)) for o, n in expected.items())
    _animate(by_ours, spec.scale)
    return top, by_ours, spec


POSES = {   # our bone: (frame 10 delta, frame 20 delta), degrees on the local channels
    "upperarm_l": ((10, 25, -40), (-20, -10, 30)), "upperarm_r": ((-15, 20, 35), (25, -10, -20)),
    "lowerarm_l": ((0, 40, 10), (5, 60, -5)), "lowerarm_r": ((10, -35, 0), (-5, -50, 10)),
    "clavicle_l": ((0, 10, 12), (0, -5, -8)), "hand_r": ((20, 0, 25), (-30, 10, 0)),
    "thigh_l": ((35, 5, 0), (-25, 0, 10)), "thigh_r": ((-30, 0, 8), (20, 10, 0)),
    "calf_l": ((0, 0, 50), (0, 0, 20)), "calf_r": ((40, 0, 0), (15, 0, 0)),
    "foot_l": ((10, 0, 15), (-15, 5, 0)), "spine_01": ((5, 20, 0), (-5, -15, 5)),
    "spine_05": ((0, -10, 8), (10, 15, 0)), "neck_01": ((10, 0, 0), (-10, 10, 0)),
    "head": ((15, 10, 0), (-10, -20, 5)), "index_01_l": ((0, 0, 30), (0, 10, 45)),
    "thumb_01_l": ((20, 0, 0), (-10, 15, 0)), "pelvis": ((5, 15, 0), (-8, -20, 4)),
}


def _animate(by_ours, scale):
    travel = by_ours.get("root") or by_ours["pelvis"]
    rest_t = cmds.getAttr(travel + ".translate")[0]
    rest_w = cmds.xform(travel, query=True, worldSpace=True, translation=True)
    for ours, (pose_a, pose_b) in POSES.items():
        joint = by_ours.get(ours)
        if not joint:
            continue
        rest = cmds.getAttr(joint + ".rotate")[0]
        for frame, delta in ((0, (0, 0, 0)), (10, pose_a), (20, pose_b)):
            for axis, base, d in zip("XYZ", rest, delta):
                cmds.setKeyframe(joint, attribute="rotate" + axis, time=frame, value=base + d)
    for frame, delta in ((0, (0, 0, 0)), (10, (10, -4, 30)), (20, (-6, 0, 70))):
        cmds.xform(travel, worldSpace=True, translation=[r + d * scale for r, d in zip(rest_w, delta)])
        for axis, value in zip("XYZ", cmds.getAttr(travel + ".translate")[0]):
            cmds.setKeyframe(travel, attribute="translate" + axis, time=frame, value=value)
    cmds.setAttr(travel + ".translate", *rest_t)
    cmds.playbackOptions(minTime=0, maxTime=20, animationStartTime=0, animationEndTime=20)
    cmds.currentTime(0)


def quadruped(ns):
    _ensure_namespace(ns)
    body = cmds.createNode("joint", name=ns + ":body", skipSelect=True)
    cmds.setAttr(body + ".translateY", 50)
    for i, x in enumerate((-20, 20, -20, 20)):
        leg = cmds.createNode("joint", name="%s:leg%d" % (ns, i), parent=body, skipSelect=True)
        cmds.setAttr(leg + ".translate", x, -50, 30 if i < 2 else -30)
    parent = body
    for i in range(5):
        parent = cmds.createNode("joint", name="%s:tail%d" % (ns, i), parent=parent, skipSelect=True)
        cmds.setAttr(parent + ".translateZ", -10)
    cmds.setKeyframe(body, attribute="translateZ", time=0, value=0)
    cmds.setKeyframe(body, attribute="translateZ", time=20, value=50)
    return cmds.ls(body, long=True)[0]


# ------------------------------------------------------------------ measuring

def pos(path):
    return cmds.xform(path, query=True, worldSpace=True, translation=True)


def sub(a, b):
    return [x - y for x, y in zip(a, b)]


def angle(a, b):
    la = math.sqrt(sum(x * x for x in a))
    lb = math.sqrt(sum(x * x for x in b))
    if la < 1e-9 or lb < 1e-9:
        return 0.0
    c = sum(x * y for x, y in zip(a, b)) / (la * lb)
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def bones_under(root):
    out = {}
    for p in [root] + (cmds.listRelatives(root, allDescendents=True, type="joint",
                                          fullPath=True) or []):
        out.setdefault(skelmap.leaf(p), p)
    return out


def gate_pairs(source_ours, target_ours, target_paths, hand_middle=None):
    """[(bone, child)]: each bone both sides map and the child its direction is read
    toward (the target's mapped hierarchy, as the retargets read it: a hand at its
    middle metacarpal where both have one, else its middle finger).
    `hand_middle` is unused, kept for the call sites."""
    common = dict((o, target_ours[o]) for o in source_ours if o in target_ours and o != "root")
    parents = skelmap.canonical_parents(common, skelmap.parent_map(target_paths))
    return sorted(skelmap.direction_children(parents).items())


def measure(source_ours, target_ours, pairs, scale, src_travel, ours_root, frames=FRAMES,
            shift=0):
    """Worst direction angle (deg, and which), worst length change (cm), pelvis and
    root travel error (cm) over `frames`."""
    worst = (0.0, "")
    lengths = {}
    first = {}
    for frame in frames:
        cmds.currentTime(frame)
        ours_now = dict((o, pos(p)) for o, p in target_ours.items())
        cmds.currentTime(frame + shift)
        src_now = dict((o, pos(p)) for o, p in source_ours.items())
        cmds.currentTime(frame)
        for bone, child in pairs:
            a = angle(sub(ours_now[child], ours_now[bone]), sub(src_now[child], src_now[bone]))
            if a > worst[0]:
                worst = (a, "%s@%d" % (bone, frame))
        for bone, child in pairs:
            if bone in ("pelvis",):
                continue
            lengths.setdefault(child, []).append(
                math.sqrt(sum(x * x for x in cmds.getAttr(target_ours[child] + ".translate")[0])))
        first.setdefault("pelvis_src", src_now["pelvis"])
        first.setdefault("pelvis_ours", ours_now["pelvis"])
        first.setdefault("travel_src", src_now[src_travel])
        first.setdefault("root_ours", pos(ours_root))
        first.setdefault("pelvis_err", 0.0)
        first.setdefault("root_err", 0.0)
        d_src = sub(src_now["pelvis"], first["pelvis_src"])
        d_ours = sub(ours_now["pelvis"], first["pelvis_ours"])
        first["pelvis_err"] = max(first["pelvis_err"],
                                  max(abs(o - scale * s) for o, s in zip(d_ours, d_src)))
        t_src = sub(src_now[src_travel], first["travel_src"])
        r_ours = sub(pos(ours_root), first["root_ours"])
        first["root_err"] = max(first["root_err"], abs(r_ours[0] - scale * t_src[0]),
                                abs(r_ours[2] - scale * t_src[2]))
    spans = sorted(((max(v) - min(v), k) for k, v in lengths.items()), reverse=True)
    length = spans[0][0] if spans else 0.0
    if length > LEN_TOL:
        print("    lengths changing: " + ", ".join("%s %.4f" % (k, d) for d, k in spans[:5]))
    return worst, length, first["pelvis_err"], first["root_err"]


def fk_mode(rig):
    for node in cmds.ls(maya_rigs.node(rig, "FKIK*"), type="transform") or []:
        if cmds.attributeQuery("FKIKBlend", node=node, exists=True):
            try:
                cmds.setAttr(node + ".FKIKBlend", 0)
            except RuntimeError:
                pass


def source_scale(source_ours, target_pelvis_height, origin_y=0.0):
    """Our pelvis height over the source's at frame 0 - and, as the retargets do,
    1.0 when within 2 % (a size within 2 % of ours IS our size)."""
    cmds.currentTime(0)
    ratio = target_pelvis_height / (pos(source_ours["pelvis"])[1] - origin_y)
    return 1.0 if abs(ratio - 1.0) <= 0.02 else ratio


def entry_of(key):
    return next((c for c in catalog.CHARACTERS if c.key == key), None)


# ------------------------------------------------------------------ phases

def phase_rigs():
    for key in [k for k in RIGS if entry_of(k)]:
        cmds.file(new=True, force=True)
        cmds.currentUnit(time="ntsc")
        before = set(r.namespace for r in maya_rigs.rigs())
        t0 = time.time()
        character.add_character(entry_of(key))
        rig = next(r for r in maya_rigs.rigs() if r.namespace not in before)
        import maya_asretarget
        print("--- %s added in %.1fs (rotation only: %s)" % (
            key, time.time() - t0, maya_asretarget.rotation_mode(rig)))
        game = bones_under(rig.skeleton_root)
        game_paths = list(game.values())
        cmds.currentTime(0)
        ours = dict((o, p) for o, p in game.items())
        height = pos(ours["pelvis"])[1] - pos(rig.skeleton_root)[1]
        for convention in CONVENTIONS:
            ns = "src_" + convention
            top, src, spec = build_source(convention, ns)
            scale = source_scale(src, height)
            t0 = time.time()
            ok, text = maya_rig_retarget.run_retarget(source_root=top, rig=rig)
            took = time.time() - t0
            fk_mode(rig)
            pairs = gate_pairs(src, ours, game_paths, hand_middle=True)
            src_travel = "root" if "root" in src else "pelvis"
            worst, length, pelvis_err, root_err = measure(src, ours, pairs, scale, src_travel,
                                                          rig.skeleton_root)
            control = measure(src, ours, pairs, scale, src_travel, rig.skeleton_root,
                              frames=(10,), shift=10)[0][0]
            REPORT.setdefault(key, {})[convention] = dict(
                ok=ok, seconds=round(took, 1), worst=worst, length=length, pelvis=pelvis_err,
                root=root_err, control=control, pairs=len(pairs), scale=scale)
            read = [line for line in text.split("  |  ") if "source read as" in line or "schema" in line]
            gate("%s <- %s" % (key, convention),
                 ok and worst[0] <= RIG_TOL[key] and length <= RIG_LEN_TOL.get(key, LEN_TOL) and pelvis_err <= TRAVEL_TOL
                 and root_err <= TRAVEL_TOL and control > 5.0,
                 "%d pairs, worst %.4f deg (%s), length %.6f cm, pelvis %.4f / root %.4f cm "
                 "at x%.4g, control %.1f deg, %.1fs%s"
                 % (len(pairs), worst[0], worst[1], length, pelvis_err, root_err, scale,
                    control, took, "" if ok else "  REFUSED: " + text[:300]))
            if not ok:
                print("    " + text[:600])
            cmds.namespace(removeNamespace=ns, deleteNamespaceContent=True)
        # the refusal, on the button's road
        top = quadruped("quad")
        ok, text = maya_rig_retarget.run_retarget(source_root=top, rig=rig)
        gate("%s refuses a quadruped" % key, not ok and "not a humanoid" in text, text[:200])
        cmds.namespace(removeNamespace="quad", deleteNamespaceContent=True)
        if key == "Manny_Rig":
            phase_sweep_on_rig(rig, ours, game_paths)


RIG_TOL = {"Manny_Rig": 0.5, "Creep_Rig": 1.5, "Orc_D_Rig": 1.5}


def _sweep_source(ns):
    if not os.path.isfile(SWEEP):
        return None
    animimport.import_clip(SWEEP, ns, set_timeline=True, merge=False)
    nodes = cmds.namespaceInfo(ns, listOnlyDependencyNodes=True, recurse=True, dagPath=True) or []
    return rigimport.source_root_in(nodes, lambda p: cmds.objectType(p) == "joint")


def phase_sweep_on_rig(rig, ours, game_paths):
    top = _sweep_source("sweep")
    if top is None:
        print("SKIP Sweep Fall.fbx not on this disk")
        return
    paths = [top] + (cmds.listRelatives(top, allDescendents=True, type="joint", fullPath=True) or [])
    found = skelmap.recognize(paths, dict((p, tuple(pos(p))) for p in paths))
    ok, text = maya_rig_retarget.run_retarget(source_root=top, rig=rig)
    fk_mode(rig)
    src = dict((o, p) for o, p in found.mapping.items())
    pairs = gate_pairs(src, ours, game_paths, hand_middle=True)
    first = cmds.findKeyframe(paths, which="first")
    last = cmds.findKeyframe(paths, which="last")
    frames = [first + (last - first) * i / 5.0 for i in range(6)]
    frames = [int(round(f)) for f in frames]
    worst = (0.0, "")
    for frame in frames:
        cmds.currentTime(frame)
        for bone, child in pairs:
            a = angle(sub(pos(ours[child]), pos(ours[bone])), sub(pos(src[child]), pos(src[bone])))
            if a > worst[0]:
                worst = (a, "%s@%d" % (bone, frame))
    gate("Manny_Rig <- Sweep Fall (Mixamo)", ok and "schema mixamo" in text and worst[0] <= 0.5,
         "still the MIXAMO schema: %s; worst %.4f deg (%s) over %d pairs"
         % ("schema mixamo" in text, worst[0], worst[1], len(pairs)))
    REPORT.setdefault("Manny_Rig", {})["sweep_fall"] = dict(ok=ok, worst=worst, pairs=len(pairs))
    cmds.namespace(removeNamespace="sweep", deleteNamespaceContent=True)


def phase_skeletons():
    for key in [k for k in SKELETONS if entry_of(k)]:
        cmds.file(new=True, force=True)
        cmds.currentUnit(time="ntsc")
        before = set(cmds.ls(type="joint", long=True) or [])
        character.add_character(entry_of(key))
        fresh = [j for j in (cmds.ls(type="joint", long=True) or []) if j not in before]
        root = min(fresh, key=lambda p: (p.count("|"), p))
        cmds.currentTime(0)
        rest = dict((p, list(cmds.getAttr(p + ".worldMatrix[0]"))) for p in fresh)
        uuids = dict((p, cmds.ls(p, uuid=True)[0]) for p in fresh)
        height = pos(bones_under(root)["pelvis"])[1] - pos(root)[1]
        for convention in CONVENTIONS + ["sweep_fall"]:
            if convention == "sweep_fall":
                top = _sweep_source("sweep")
                if top is None:
                    continue
                ns = "sweep"
                paths = [top] + (cmds.listRelatives(top, allDescendents=True, type="joint",
                                                    fullPath=True) or [])
                src = dict(skelmap.recognize(paths, dict((p, tuple(pos(p))) for p in paths)).mapping)
                start = cmds.findKeyframe(paths, which="first")
                end = cmds.findKeyframe(paths, which="last")
            else:
                ns = "src_" + convention
                top, src, spec = build_source(convention, ns)
                start, end = 0, 20
            scale = source_scale(src, height)
            t0 = time.time()
            result = skeletonimport.transfer(top, root, start, end)
            took = time.time() - t0
            game = bones_under(root)
            pairs = gate_pairs(src, game, list(game.values()), hand_middle=False)
            src_travel = "root" if "root" in src else "pelvis"
            frames = FRAMES if convention != "sweep_fall" else tuple(
                int(round(start + (end - start) * i / 5.0)) for i in range(6))
            worst, length, pelvis_err, root_err = measure(src, game, pairs, scale, src_travel,
                                                          root, frames=frames)
            control = measure(src, game, pairs, scale, src_travel, root, frames=(frames[2],),
                              shift=frames[4] - frames[2])[0][0]
            REPORT.setdefault(key, {})[convention] = dict(
                moved=result.get("moved"), convention=result.get("convention"),
                rest=result.get("rest"), worst=worst, length=length, pelvis=pelvis_err,
                root=root_err, control=control, pairs=len(pairs), scale=result.get("scale"),
                expected_scale=scale)
            scale_ok = abs((result.get("scale") or 1.0) - scale) < 0.02 * scale or \
                (result.get("scale") == 1.0 and abs(scale - 1) <= 0.02)
            gate("%s <- %s" % (key, convention),
                 result.get("moved", 0) > 20 and worst[0] <= DIR_TOL_SKELETON and length <= LEN_TOL
                 and pelvis_err <= TRAVEL_TOL and root_err <= TRAVEL_TOL and control > 5.0 and scale_ok,
                 "%d bones, read as %s, rest %s, worst %.4f deg (%s), length %.6f, pelvis %.4f / "
                 "root %.4f cm at x%.4g (map x%s), control %.1f deg, %.1fs"
                 % (result.get("moved", 0), result.get("convention"), result.get("rest"), worst[0],
                    worst[1], length, pelvis_err, root_err, scale, result.get("scale"), control, took))
            cmds.namespace(removeNamespace=ns, deleteNamespaceContent=True)
            _reset(rest, uuids)
        top = quadruped("quad")
        result = skeletonimport.transfer(top, root, 0, 20)
        gate("%s refuses a quadruped" % key, result.get("moved") == 0 and result.get("refusal"),
             str(result.get("refusal")))
        cmds.namespace(removeNamespace="quad", deleteNamespaceContent=True)
        if key == "Creep":
            phase_rest_choice(root)


def _reset(rest, uuids):
    """The skeleton back at rest, its keys cut, for the next convention."""
    for path, uuid in uuids.items():
        now = cmds.ls(uuid, long=True)
        if not now:
            continue
        curves = cmds.listConnections(now[0], type="animCurve", source=True, destination=False) or []
        if curves:
            cmds.delete(curves)
    for path, uuid in sorted(uuids.items(), key=lambda kv: kv[0].count("|")):
        now = cmds.ls(uuid, long=True)
        if now:
            cmds.xform(now[0], worldSpace=True, matrix=rest[path])


def phase_rest_choice(root):
    """The same Unity clip (its bind in the rotate channels) onto the Creep twice, the
    rest FORCED to each candidate: the directions match both times, the frames do not."""
    real = skelmap.choose_rest
    frames = {}
    worsts = {}
    game = bones_under(root)
    rest = dict((p, list(cmds.getAttr(p + ".worldMatrix[0]"))) for p in game.values())
    uuids = dict((p, cmds.ls(p, uuid=True)[0]) for p in game.values())
    try:
        for forced in ("jointOrient", "firstFrame"):
            skelmap.choose_rest = (lambda name: (lambda cands, rig, prefer=None: (name, {})))(forced)
            top, src, _spec = build_source("unity", "rest_" + forced)
            height = pos(game["pelvis"])[1] - pos(root)[1]
            skeletonimport.transfer(top, root, 0, 20)
            pairs = gate_pairs(src, game, list(game.values()), hand_middle=False)
            worsts[forced] = measure(src, game, pairs, source_scale(src, height),
                                     "root" if "root" in src else "pelvis", root)[0]
            cmds.currentTime(10)
            frames[forced] = cmds.xform(game["upperarm_l"], query=True, worldSpace=True, matrix=True)
            cmds.namespace(removeNamespace="rest_" + forced, deleteNamespaceContent=True)
            _reset(rest, uuids)
    finally:
        skelmap.choose_rest = real

    def frame_angle(a, b):
        axes = [(a[i * 4:i * 4 + 3], b[i * 4:i * 4 + 3]) for i in range(3)]
        return max(angle(x, y) for x, y in axes)
    roll = frame_angle(frames["jointOrient"], frames["firstFrame"])
    gate("rest choice sets the roll only",
         worsts["jointOrient"][0] <= DIR_TOL_SKELETON and worsts["firstFrame"][0] <= DIR_TOL_SKELETON
         and roll > 1.0,
         "directions %.4f / %.4f deg with the rest forced to jointOrient / firstFrame; "
         "upperarm_l's frame differs by %.2f deg" % (worsts["jointOrient"][0],
                                                    worsts["firstFrame"][0], roll))


def phase_playermale():
    """The PlayerMale module's generic schema, on a Biped and a Daz figure, against a
    rest of the PlayerMale's own names (the rig's asset is not in the plugin, so its
    connect is not run here): the UE rows re-keyed, the spine onto its four, the
    drive plan whole."""
    import maya_pmretarget as pm
    cmds.file(new=True, force=True)
    rows, _e = fixtures.build("ue5")
    ue_pos = dict((n, p) for n, _parent, p in rows)
    rig_rest = {}
    for ours, ue in pm.ue_names_of_ours().items():
        if ue in ue_pos:
            m = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0] + [c * 0.1 for c in ue_pos[ue]] + [1]
            rig_rest[ours] = m
    for convention, spine in (("biped", ["Bip001_Spine", "Bip001_Spine1", "Bip001_Spine2"]),
                              ("daz", ["abdomenLower", "abdomenUpper", "chestLower", "chestUpper"])):
        top, _src, _spec = build_source(convention, "pm_" + convention)
        schema, refusal = pm.generic_schema(top, rig_rest)
        # the controls this rig HAS: those standing on a PlayerMale bone
        controls = [c for c in pm.candidates(schema) if pm.our_bone(c) in rig_rest] if schema else []
        drives, missing = pm.drive_plan(controls, list(schema.bones) if schema else [], schema) \
            if schema else ([], [])
        rows_by = dict(schema.rows) if schema else {}
        chain = [skelmap.leaf(schema.bones[rows_by[b]]) for b in ("Spine1", "Spine2", "Spine3", "Chest")
                 if b in rows_by] if schema else []
        expected_chain = spine           # 3 onto 4: Spine1, Spine3, Chest; 4 onto 4: all
        gate("PlayerMale generic <- %s" % convention,
             schema is not None and not missing and len(drives) > 40
             and chain == expected_chain and schema.rest == "given",
             "%s; %d drives, %d missing, spine %s, rest %s" % (
                 refusal or schema.name, len(drives), len(missing), chain,
                 getattr(schema, "rest_choice", None)))
        cmds.namespace(removeNamespace="pm_" + convention, deleteNamespaceContent=True)


def main():
    t_all = time.time()
    try:
        phase_playermale()
        phase_skeletons()
        phase_rigs()
    except Exception:                                       # noqa: BLE001
        traceback.print_exc()
        RESULTS.append(False)
    out = os.path.join(tempfile.gettempdir(), "verify_skeleton_conventions.json")
    with open(out, "w") as fh:
        json.dump(REPORT, fh, indent=1, default=str)
    print("\n%d of %d gates passed in %.0fs (report: %s)" % (
        sum(RESULTS), len(RESULTS), time.time() - t_all, out))


if __name__ == "__main__":
    main()
    try:
        maya.standalone.uninitialize()
    except Exception:                                       # noqa: BLE001
        pass
    os._exit(0 if all(RESULTS) else 1)
