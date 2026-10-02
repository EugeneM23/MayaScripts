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

The fix pass (2026-10-02) added, on both roads:

  variants  a Unity body with 15 % longer legs; a Unity clip whose FIRST FRAME is a
            crouch (its bind in the rotate channels, so the first frame is the rest
            the map would pick), with and without a bindPose; a HumanIK clip whose
            floor-level Reference never moves while the hips travel. The expected
            size is derived from the fixture's own constants (unit x body ratio),
            never with the implementation's formula.
  partial   a UE5 clip with no legs (arms only): the old UE road, not a refusal.
  drop      a CMU clip (0.45 of our size) starting 18 cm off its origin, dropped onto
            a floor point on a new Manny rig and a new Manny skeleton: Main / root on
            the point; two of them laid out in a square by the bridge's press,
            spaced by their BAKED travel.
  UE4       the UE4 Mannequin [skeleton] as a target.
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
SKELETONS = [s for s in os.environ.get("SKELETONS", "Manny,Creep,UE4_Mannequin").split(",") if s]
PHASES = [p for p in os.environ.get("PHASES", "").split(",") if p]
# name: (base convention, options) - see build_source
VARIANTS = [v for v in (
    ("unity_tall", "unity", dict(legs=1.15)),
    ("unity_crouch", "unity", dict(crouch=True)),
    ("unity_crouch_bind", "unity", dict(crouch=True, bind=True)),
    ("hik_reference", "hik", dict(reference=True)),
) if not os.environ.get("VARIANTS") or v[0] in os.environ["VARIANTS"].split(",")]
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
RIG_LEN_TOL = {"Manny_Rig": 0.12}   # CLAUDE.md: "the LEFT leg at 0.06-0.08 cm"; the
                                    # crouch variant bends the knee 120 deg: 0.107 measured
TRAVEL_TOL = 0.05                           # cm
# the size the retarget used against the one derived here from the fixture's constants (a
# wrong size is a 20-60 % error; the two agree to rounding)
SIZE_TOL = 0.005

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


def _longer_legs(rows, expected, k):
    """Every leg joint's height above the hips stretched by k (the torso as it is):
    a body whose proportions are not Manny's."""
    legs = set(src for ours, src in expected.items()
               if ours.startswith(("thigh", "calf", "foot", "ball")))
    below = set(legs)
    parent_of = dict((n, p) for n, p, _pos in rows)
    for name, _p, _pos in rows:          # nubs and toe ends under the legs too
        node = parent_of.get(name)
        while node:
            if node in legs:
                below.add(name)
                break
            node = parent_of.get(node)
    hips_y = fixtures.HIPS[1]
    lift = (k - 1.0) * (hips_y - fixtures.ANKLE[1])      # the ankles back on their height
    out = []
    for name, parent, pos in rows:
        if name in below:
            pos = (pos[0], hips_y + k * (pos[1] - hips_y), pos[2])
        out.append((name, parent, (pos[0], pos[1] + lift, pos[2])))
    return out


def _with_reference(rows, expected, spec):
    """A floor-level root above the hips, the way MotionBuilder writes `Reference`."""
    hips = spec.namespace + spec.hips
    ref = spec.namespace + "Character1_Reference"
    out = [(ref, None, (0.0, 0.0, 0.0))]
    for name, parent, pos in rows:
        out.append((name, ref if name == hips else parent, pos))
    return out


def build_source(convention, ns, legs=1.0, crouch=False, bind=False, reference=False,
                 travel_x=0.0, start=(0.0, 0.0)):
    """(top joint path, {our bone: source path}, spec) - the convention's rows as
    Maya joints in namespace `ns`, oriented, rest moved where the convention keeps
    it, keyed. Options (the fix pass): `legs` stretches the legs, `crouch` makes
    frame 0 a deep crouch, `bind` saves a bindPose at the rest first, `reference`
    puts a static floor root above the hips, `travel_x` adds that much travel along
    +X by frame 20 and `start` moves the whole clip's travel (x, z) off its origin,
    both in the source's own units."""
    rows, expected = fixtures.build(convention)
    spec = fixtures.SPECS.get(convention, fixtures.SPECS["mixamo"])
    if legs != 1.0:
        rows = _longer_legs(rows, expected, legs)
    if reference:
        rows = _with_reference(rows, expected, spec)
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
    if bind:
        cmds.dagPose([path(n) for n in made], save=True, bindPose=True,
                     name="%s:bindPose1" % ns)
    _animate(by_ours, spec.scale, travel_x=travel_x, start=start)
    if crouch:
        _crouch(by_ours, spec.scale)
    return top, by_ours, spec


def _crouch(by_ours, scale):
    """Frame 0 a deep crouch: the thighs 70 deg forward, the calves 120 back, the
    pelvis 30 cm lower. The keys at 10 and 20 stay."""
    cmds.currentTime(0)
    for side in ("l", "r"):
        for bone, turn in (("thigh_", 70.0), ("calf_", -120.0)):
            joint = by_ours.get(bone + side)
            if joint:
                cmds.rotate(turn, 0, 0, joint, relative=True, worldSpace=True)
                cmds.setKeyframe(joint, attribute=["rotateX", "rotateY", "rotateZ"], time=0)
    pelvis = by_ours["pelvis"]
    world = cmds.xform(pelvis, query=True, worldSpace=True, translation=True)
    cmds.xform(pelvis, worldSpace=True, translation=[world[0], world[1] - 30.0 * scale, world[2]])
    cmds.setKeyframe(pelvis, attribute=["translateX", "translateY", "translateZ"], time=0)
    cmds.currentTime(0)


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


def _animate(by_ours, scale, travel_x=0.0, start=(0.0, 0.0)):
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
    for frame, delta in ((0, (0, 0, 0)), (10, (10 + travel_x / 2.0, -4, 30)),
                         (20, (-6 + travel_x, 0, 70))):
        delta = (delta[0] + start[0], delta[1], delta[2] + start[1])
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


def target_by_ours(root):
    """{our bone: path} of a target skeleton, read the way the transfer reads it (a
    UE4 Mannequin's three spine joints are our spine_01, _03, _05)."""
    paths = [root] + (cmds.listRelatives(root, allDescendents=True, type="joint",
                                         fullPath=True) or [])
    found = skelmap.recognize(paths, dict((p, tuple(pos(p))) for p in paths))
    return dict(found.mapping)


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


def target_size(bones, floor):
    """(standing height, leg length) of one of OUR targets at its rest, by plain
    measurement: the pelvis over its floor (its root's height), and thigh->calf->foot
    averaged over the sides."""
    p = dict((n, pos(path)) for n, path in bones.items())
    stand = p["pelvis"][1] - floor
    legs = sum(math.sqrt(sum(c * c for c in sub(p["calf_" + s], p["thigh_" + s])))
               + math.sqrt(sum(c * c for c in sub(p["foot_" + s], p["calf_" + s])))
               for s in "lr") / 2.0
    return stand, legs


def fixture_size(spec, legs=1.0):
    """(standing height, leg length) of the fixture body, from tests/skeleton_conventions'
    own constants: the hips over the ankle, and the two leg bones, in the convention's
    unit, the legs stretched by `legs` as `_longer_legs` does (the body lifted so the
    ankles keep their height): the hips over the floor, and the two leg bones."""
    hip, knee, ankle = fixtures.HIP, fixtures.KNEE, fixtures.ANKLE
    hips_y = fixtures.HIPS[1]

    def stretched(point):
        return (point[0], hips_y + legs * (point[1] - hips_y), point[2])
    hip, knee, ankle = stretched(hip), stretched(knee), stretched(ankle)
    stand = (hips_y + (legs - 1.0) * (hips_y - fixtures.ANKLE[1])) * spec.scale
    bones = (math.sqrt(sum(c * c for c in sub(knee, hip)))
             + math.sqrt(sum(c * c for c in sub(ankle, knee)))) * spec.scale
    return stand, bones


def expected_scale(spec, target, legs=1.0, by_legs=False):
    """The size the retarget must use, derived independently of the implementation:
    the target's pelvis over its floor against the fixture's (its legs when no
    candidate rest stands - a crouched first frame with no bind), 1.0 within 2 %."""
    mine = fixture_size(spec, legs)
    ratio = target[1] / mine[1] if by_legs else target[0] / mine[0]
    return 1.0 if abs(ratio - 1.0) <= 0.02 else ratio


def used_scale(text):
    """The travel scale the rig road reports in its status line, 1.0 when none."""
    import re
    found = re.search(r"travel scaled by ([0-9.]+)", text or "")
    return float(found.group(1)) if found else 1.0


def size_ok(used, expected):
    return abs(used / expected - 1.0) <= SIZE_TOL


def source_scale(source_ours, target_pelvis_height, origin_y=0.0):
    """Kept for the rest-choice phase: our pelvis height over the source's at frame 0."""
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
        size = target_size(ours, pos(rig.skeleton_root)[1])
        for name, convention, options in [(c, c, {}) for c in CONVENTIONS] + VARIANTS:
            ns = "src_" + name
            top, src, spec = build_source(convention, ns, **options)
            scale = expected_scale(spec, size, options.get("legs", 1.0),
                                   by_legs=options.get("crouch") and not options.get("bind"))
            # the size the rig road will use, read off its own plan (the status line
            # carries the connect's first line only) - at the build pose, as the button
            # reads it: the rig still carries the last convention's take here
            maya_asretarget.reset_build_pose(rig=rig)
            plan = maya_asretarget._plan(source_root=top, rig=rig)
            used = getattr(plan.schema, "scale", 1.0)
            t0 = time.time()
            ok, text = maya_rig_retarget.run_retarget(source_root=top, rig=rig)
            took = time.time() - t0
            fk_mode(rig)
            expected, scale = scale, used
            pairs = gate_pairs(src, ours, game_paths, hand_middle=True)
            src_travel = "root" if "root" in src else "pelvis"
            worst, length, pelvis_err, root_err = measure(src, ours, pairs, scale, src_travel,
                                                          rig.skeleton_root)
            control = measure(src, ours, pairs, scale, src_travel, rig.skeleton_root,
                              frames=(10,), shift=10)[0][0]
            REPORT.setdefault(key, {})[name] = dict(
                ok=ok, seconds=round(took, 1), worst=worst, length=length, pelvis=pelvis_err,
                root=root_err, control=control, pairs=len(pairs), scale=scale, expected=expected)
            read = [line for line in text.split("  |  ") if "source read as" in line or "schema" in line]
            gate("%s <- %s" % (key, name),
                 ok and worst[0] <= RIG_TOL[key] and length <= RIG_LEN_TOL.get(key, LEN_TOL) and pelvis_err <= TRAVEL_TOL
                 and root_err <= TRAVEL_TOL and control > 5.0 and size_ok(scale, expected),
                 "%d pairs, worst %.4f deg (%s), length %.6f cm, pelvis %.4f / root %.4f cm "
                 "at x%.4g (derived x%.4g), control %.1f deg, %.1fs%s"
                 % (len(pairs), worst[0], worst[1], length, pelvis_err, root_err, scale,
                    expected, control, took, "" if ok else "  REFUSED: " + text[:300]))
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
            phase_partial_on_rig(rig, ours, game_paths)


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
        size = target_size(bones_under(root), pos(root)[1])
        for name, convention, options in ([(c, c, {}) for c in CONVENTIONS] + VARIANTS
                                          + [("sweep_fall", "sweep_fall", {})]):
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
                ns = "src_" + name
                top, src, spec = build_source(convention, ns, **options)
                start, end = 0, 20
            scale = source_scale(src, height) if convention == "sweep_fall" else expected_scale(
                spec, size, options.get("legs", 1.0),
                by_legs=options.get("crouch") and not options.get("bind"))
            t0 = time.time()
            result = skeletonimport.transfer(top, root, start, end)
            took = time.time() - t0
            expected = scale
            scale = result.get("scale") or 1.0
            game = target_by_ours(root)
            pairs = gate_pairs(src, game, list(game.values()), hand_middle=False)
            src_travel = "root" if "root" in src else "pelvis"
            frames = FRAMES if convention != "sweep_fall" else tuple(
                int(round(start + (end - start) * i / 5.0)) for i in range(6))
            worst, length, pelvis_err, root_err = measure(src, game, pairs, scale, src_travel,
                                                          root, frames=frames)
            control = measure(src, game, pairs, scale, src_travel, root, frames=(frames[2],),
                              shift=frames[4] - frames[2])[0][0]
            cmds.currentTime(start)
            # the pelvis is constrained ABSOLUTELY on this road: it stands at the
            # scaled source's height (sinking or floating is a wrong size)
            sink = abs(pos(game["pelvis"])[1] - scale * pos(src["pelvis"])[1])
            REPORT.setdefault(key, {})[name] = dict(
                moved=result.get("moved"), convention=result.get("convention"),
                rest=result.get("rest"), worst=worst, length=length, pelvis=pelvis_err,
                root=root_err, control=control, pairs=len(pairs), scale=result.get("scale"),
                expected_scale=expected, sized=result.get("sized"), sink=sink,
                root_note=result.get("root"))
            # a real file's body is unknown: its size is the transfer's, gated by the
            # pelvis standing at the scaled height and the travel following it
            scale_ok = size_ok(scale, expected) if convention != "sweep_fall" else True
            extra = True
            if options.get("reference"):
                # the static Reference is no root: the root takes the hips' travel
                extra = "never moves" in (result.get("root") or "")
            gate("%s <- %s" % (key, name),
                 result.get("moved", 0) > 20 and worst[0] <= DIR_TOL_SKELETON and length <= LEN_TOL
                 and pelvis_err <= TRAVEL_TOL and root_err <= TRAVEL_TOL and control > 5.0
                 and scale_ok and sink <= TRAVEL_TOL and extra,
                 "%d bones, read as %s, rest %s, worst %.4f deg (%s), length %.6f, pelvis %.4f / "
                 "root %.4f cm, height %.4f cm at x%.4g (derived x%.4g, %s), control %.1f deg, %.1fs%s"
                 % (result.get("moved", 0), result.get("convention"), result.get("rest"), worst[0],
                    worst[1], length, pelvis_err, root_err, sink, scale, expected,
                    result.get("sized"), control, took,
                    ("; " + result.get("root")) if options.get("reference") else ""))
            cmds.namespace(removeNamespace=ns, deleteNamespaceContent=True)
            _reset(rest, uuids)
        top = quadruped("quad")
        result = skeletonimport.transfer(top, root, 0, 20)
        gate("%s refuses a quadruped" % key, result.get("moved") == 0 and result.get("refusal"),
             str(result.get("refusal")))
        cmds.namespace(removeNamespace="quad", deleteNamespaceContent=True)
        if key == "Creep":
            phase_rest_choice(root)
        if key == "Manny":
            phase_partial_on_skeleton(root)


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


# ------------------------------------------------------------------ the fix pass's phases

LEGS = ("thigh_l", "thigh_r")


def _arms_only(source_root, ns):
    """A UE5 clip with no legs (an upper-body take), on Manny's OWN joints - so its
    axes are Unreal's, as every clip from the editor has them: a copy of the
    skeleton under `source_root`, its thighs deleted, its arms keyed.
    (top, {our bone: path})."""
    _ensure_namespace(ns)
    copy = cmds.duplicate(source_root, name=ns + ":root", returnRootsOnly=True)[0]
    copy = cmds.ls(copy, long=True)[0]
    for node in cmds.listRelatives(copy, allDescendents=True, fullPath=True) or []:
        if cmds.objExists(node) and cmds.objectType(node) != "joint":
            cmds.delete(node)
    bones = bones_under(copy)
    for leg in LEGS:
        if leg in bones and cmds.objExists(bones[leg]):
            cmds.delete(bones[leg])
    bones = bones_under(copy)
    for node in bones.values():
        curves = cmds.listConnections(node, type="animCurve", source=True, destination=False) or []
        if curves:
            cmds.delete(curves)
    for bone, a, b in (("upperarm_l", (0, 30, -40), (20, -25, 10)),
                       ("lowerarm_l", (0, 0, 50), (10, 0, 20)),
                       ("upperarm_r", (15, -30, 35), (-20, 25, -10)),
                       ("lowerarm_r", (0, 0, -45), (-5, 0, -20))):
        rest = cmds.getAttr(bones[bone] + ".rotate")[0]
        for frame, delta in ((0, (0, 0, 0)), (10, a), (20, b)):
            for axis, base, d in zip("XYZ", rest, delta):
                cmds.setKeyframe(bones[bone], attribute="rotate" + axis, time=frame, value=base + d)
    cmds.currentTime(0)
    return copy, bones


def _arm_worst(src, ours, frames=FRAMES):
    worst = (0.0, "")
    pairs = [("upperarm_l", "lowerarm_l"), ("lowerarm_l", "hand_l"),
             ("upperarm_r", "lowerarm_r"), ("lowerarm_r", "hand_r")]
    for frame in frames:
        cmds.currentTime(frame)
        for bone, child in pairs:
            a = angle(sub(pos(ours[child]), pos(ours[bone])), sub(pos(src[child]), pos(src[bone])))
            if a > worst[0]:
                worst = (a, "%s@%d" % (bone, frame))
    return worst


def phase_partial_on_rig(rig, ours, game_paths):
    """The review's finding 4: a UE clip missing its legs used to retarget the bones
    it has; the conventions build sent it to the generic road, which refused it."""
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    character.add_character(entry_of("Manny_Rig"))
    rig = maya_rigs.rigs()[0]
    ours = bones_under(rig.skeleton_root)
    before = set(cmds.ls(type="joint", long=True) or [])
    character.add_character(entry_of("Manny"))
    fresh = [j for j in (cmds.ls(type="joint", long=True) or []) if j not in before]
    manny = min(fresh, key=lambda p: (p.count("|"), p))
    top, src = _arms_only(manny, "partial")
    ok, text = maya_rig_retarget.run_retarget(source_root=top, rig=rig)
    fk_mode(rig)
    worst = _arm_worst(src, ours) if ok else (999.0, "refused")
    gate("Manny_Rig <- an arms-only UE clip", ok and "schema ue5" in text and worst[0] <= 2.0,
         "%s; the arms point as the clip's, worst %.4f deg (%s)"
         % ("retargeted on the UE road" if ok else "REFUSED: " + text[:200], worst[0], worst[1]))
    REPORT.setdefault("Manny_Rig", {})["ue5_arms_only"] = dict(ok=ok, worst=worst, text=text[:400])
    cmds.namespace(removeNamespace="partial", deleteNamespaceContent=True)


def phase_partial_on_skeleton(root):
    game = bones_under(root)
    rest = dict((p, list(cmds.getAttr(p + ".worldMatrix[0]"))) for p in game.values())
    uuids = dict((p, cmds.ls(p, uuid=True)[0]) for p in game.values())
    top, src = _arms_only(root, "partial")
    result = skeletonimport.transfer(top, root, 0, 20)
    worst = _arm_worst(src, bones_under(root)) if result.get("moved") else (999.0, "refused")
    gate("Manny <- an arms-only UE clip",
         result.get("moved", 0) > 10 and not result.get("refusal") and worst[0] <= DIR_TOL_SKELETON
         and result.get("twin"),
         "%d bones moved as a twin %s, refusal %r, the arms point as the clip's, worst %.4f deg "
         "(%s), missing %d (the legs)" % (result.get("moved", 0), result.get("twin"),
                                          result.get("refusal"), worst[0], worst[1],
                                          len(result.get("missing", []))))
    REPORT.setdefault("Manny", {})["ue5_arms_only"] = dict(
        moved=result.get("moved"), worst=worst, missing=result.get("missing"))
    cmds.namespace(removeNamespace="partial", deleteNamespaceContent=True)
    _reset(rest, uuids)


DROP_START = (40.0, 20.0)     # the CMU clip's travel starts this far off its origin (its units)
DROP_TRAVEL_X = 60.0          # ... and runs this much further along +X by frame 20


def _cmu_fbx(name):
    """A CMU clip (0.45 of our size, no root bone) starting off its origin, exported
    to an FBX the bridge's own import reads back. (path, its top joint's world track
    at frames 0..20 in the source's world, the spec)."""
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    top, src, spec = build_source("cmu", name, start=DROP_START, travel_x=DROP_TRAVEL_X)
    joints = [top] + (cmds.listRelatives(top, allDescendents=True, type="joint", fullPath=True) or [])
    track = []
    for frame in range(0, 21):
        cmds.currentTime(frame)
        track.append(tuple(pos(top)))
    path = os.path.join(tempfile.gettempdir(), "verify_conventions_%s.fbx" % name).replace("\\", "/")
    cmds.select(joints, replace=True)
    mel.eval("FBXResetExport")
    mel.eval("FBXExportBakeComplexAnimation -v true")
    mel.eval("FBXExportBakeComplexStart -v 0")
    mel.eval("FBXExportBakeComplexEnd -v 20")
    mel.eval('FBXExport -f "%s" -s' % path)
    return path, track, spec


def _pick_character(model, kind):
    cmds.optionVar(stringValue=("mayaSceneSetup_characterModel", model))
    cmds.optionVar(stringValue=("mayaSceneSetup_characterKind", kind))


def _manny_size():
    """Manny's standing height and legs, from the shipped template - the size the
    rig's and the skeleton's travel is baked at (both stand on Manny's legs)."""
    data = json.load(open(os.path.join(PLUGIN, "assets", "manny_skeleton_template.json")))
    p = dict((j["name"], tuple(j["world_position"])) for j in data["joints"])
    stand = p["pelvis"][1] - p["root"][1]
    legs = sum(math.sqrt(sum(c * c for c in sub(p["calf_" + s], p["thigh_" + s])))
               + math.sqrt(sum(c * c for c in sub(p["foot_" + s], p["calf_" + s])))
               for s in "lr") / 2.0
    return stand, legs


def phase_drop():
    """The review's finding 2: a scaled clip whose root starts off its origin, dropped
    onto a floor point, must land ON the point - the scale used to be applied about the
    clip's origin while the drop is read off its unscaled first frame."""
    path, track, spec = _cmu_fbx("cmuDrop")
    scale = expected_scale(spec, _manny_size())
    p0 = track[0]
    off = math.hypot(p0[0], p0[2])
    print("    the CMU clip starts %.2f cm off its origin; baked at x%.4f the old pivot would "
          "have landed it %.2f cm off the point" % (off, scale, (scale - 1.0) * off))

    # the rig road: a new Manny rig on a floor point
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    _pick_character("Manny", "rig")
    point = (150.0, 0.0, -80.0)
    before = set(r.namespace for r in maya_rigs.rigs())
    text = rigimport.import_and_retarget(path, "cmuDrop", target="new_rig", at=point)
    rig = next((r for r in maya_rigs.rigs() if r.namespace not in before), None)
    if rig is None:
        gate("drop: a CMU clip onto a floor point, new rig", False, text[:400])
    else:
        start = cmds.playbackOptions(query=True, minTime=True)
        cmds.currentTime(start)
        main = pos(maya_rigs.node(rig, "Main"))
        miss = math.hypot(main[0] - point[0], main[2] - point[2])
        game = bones_under(rig.skeleton_root)
        cmds.currentTime(start + 20)
        end = pos(maya_rigs.node(rig, "Main"))
        travel = (end[0] - main[0], end[2] - main[2])
        # the press deletes the clip and its line carries no connect notes: the size it
        # used is read off what it baked - Main's travel over the clip's own
        keyed = (track[20][0] - track[0][0], track[20][2] - track[0][2])
        used = math.hypot(*travel) / math.hypot(*keyed)
        want = (used * keyed[0], used * keyed[1])
        err = math.hypot(travel[0] - want[0], travel[1] - want[1])
        gate("drop: a CMU clip onto a floor point, new rig",
             miss <= TRAVEL_TOL and err <= TRAVEL_TOL and off * (scale - 1.0) > 5.0
             and size_ok(used, scale),
             "Main %.4f cm off the point, its travel (%.2f, %.2f) against the clip's x%.4f "
             "(derived x%.4f) (%.2f, %.2f), %.4f off  |  %s"
             % (miss, travel[0], travel[1], used, scale, want[0], want[1], err,
                text.split("  |  ")[0][:160]))
        REPORT.setdefault("drop", {})["rig"] = dict(miss=miss, err=err, scale=scale, used=used,
                                                    text=text)

    # the skeleton road: a new Manny skeleton on a floor point
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    point = (-120.0, 0.0, 60.0)
    before = set(cmds.ls(type="joint", long=True) or [])
    text = skeletonimport.import_onto_skeleton(path, "cmuDropS", at=point, entry=entry_of("Manny"))
    fresh = [j for j in (cmds.ls(type="joint", long=True) or []) if j not in before]
    if not fresh:
        gate("drop: a CMU clip onto a floor point, new skeleton", False, text[:400])
    else:
        root = min(fresh, key=lambda p: (p.count("|"), p))
        start = cmds.playbackOptions(query=True, minTime=True)
        cmds.currentTime(start)
        here = pos(root)
        miss = math.hypot(here[0] - point[0], here[2] - point[2])
        cmds.currentTime(start + 20)
        there = pos(root)
        # the press deletes the clip; the size it used is the rig road's (one reference)
        used = REPORT.get("drop", {}).get("rig", {}).get("used", scale)
        want = (used * (track[20][0] - track[0][0]), used * (track[20][2] - track[0][2]))
        err = math.hypot(there[0] - here[0] - want[0], there[2] - here[2] - want[1])
        gate("drop: a CMU clip onto a floor point, new skeleton",
             miss <= TRAVEL_TOL and err <= TRAVEL_TOL,
             "root %.4f cm off the point, travel %.4f off the clip's x%.4f  |  %s"
             % (miss, err, used, text.split("  |  ")[0][:160]))
        REPORT.setdefault("drop", {})["skeleton"] = dict(miss=miss, err=err, scale=scale, text=text)

    # the positive control: the same drop with the scale about the clip's ORIGIN, as the
    # conventions build had it - the gate above must be able to fail
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    real = skelmap.scale_pivot
    skelmap.scale_pivot = lambda first, origin: tuple(origin)
    try:
        before = set(cmds.ls(type="joint", long=True) or [])
        skeletonimport.import_onto_skeleton(path, "cmuDropC", at=point, entry=entry_of("Manny"))
    finally:
        skelmap.scale_pivot = real
    fresh = [j for j in (cmds.ls(type="joint", long=True) or []) if j not in before]
    if fresh:
        root = min(fresh, key=lambda p: (p.count("|"), p))
        cmds.currentTime(cmds.playbackOptions(query=True, minTime=True))
        here = pos(root)
        old_miss = math.hypot(here[0] - point[0], here[2] - point[2])
        used = REPORT.get("drop", {}).get("rig", {}).get("used", scale)
        gate("drop control: the old pivot misses", abs(old_miss - (used - 1.0) * off) < 0.5,
             "scaled about the clip's origin the root lands %.2f cm off the point "
             "((s - 1) * |p0| = %.2f)" % (old_miss, (used - 1.0) * off))

    # the square: two of them through the bridge's press, spaced by the BAKED travel
    from maya_uebridge import lineimport, lineup
    import types
    paths = {"A": path, "B": _cmu_fbx("cmuDropB")[0]}
    for target, label in (("skeleton", "skeletons"), ("new_rig", "rigs")):
        cmds.file(new=True, force=True)
        cmds.currentUnit(time="ntsc")
        _pick_character("Manny", "skeleton" if target == "skeleton" else "rig")
        before = set(cmds.ls(type="joint", long=True) or [])
        rigs_before = set(r.namespace for r in maya_rigs.rigs())
        records = [types.SimpleNamespace(name=n, package="/Game/" + n) for n in ("A", "B")]
        text = lineimport.run(records, lambda r: (paths[r.name], None), target)
        start = cmds.playbackOptions(query=True, minTime=True)
        if target == "skeleton":
            fresh = [j for j in (cmds.ls(type="joint", long=True) or []) if j not in before]
            tops = sorted(set(p for p in fresh if not cmds.listRelatives(p, parent=True, type="joint")),
                          key=lambda p: pos(p)[0])
            movers = [t for t in tops if skelmap.leaf(t).endswith("root")]
        else:
            new = [r for r in maya_rigs.rigs() if r.namespace not in rigs_before]
            movers = [maya_rigs.node(r, "Main") for r in new]
        paths_baked = []
        for mover in movers:
            seen = []
            for frame in range(int(start), int(start) + 21):
                cmds.currentTime(frame)
                seen.append(tuple(pos(mover)))
            paths_baked.append(seen)
        paths_baked.sort(key=lambda t: t[0][0])
        if len(paths_baked) != 2:
            gate("square: two scaled clips, new %s" % label, False,
                 "%d movers found  |  %s" % (len(paths_baked), text[:300]))
            continue
        gap = min(q[0] for q in paths_baked[1]) - max(q[0] for q in paths_baked[0])
        used = REPORT.get("drop", {}).get("rig", {}).get("used", scale)
        scaled = [[tuple(f + used * (c - f) for c, f in zip(q, track[0])) for q in track]] * 2
        raw = [track, track]
        want = lineup.square_slots((0.0, 0.0, 0.0),
                                   [lineup.side_extent(t, lineup.COLUMNS) for t in scaled],
                                   [lineup.side_extent(t, lineup.ROWS) for t in scaled])
        old = lineup.square_slots((0.0, 0.0, 0.0),
                                  [lineup.side_extent(t, lineup.COLUMNS) for t in raw],
                                  [lineup.side_extent(t, lineup.ROWS) for t in raw])
        firsts = [q[0] for q in paths_baked]
        miss = max(math.hypot(f[0] - w[0], f[2] - w[2]) for f, w in zip(firsts, want))
        reach = max(q[0] for q in paths_baked[0]) - paths_baked[0][0][0]
        old_gap = (old[1][0] - old[0][0]) - reach
        gate("square: two scaled clips, new %s" % label,
             miss <= TRAVEL_TOL and gap >= lineup.STEP - TRAVEL_TOL and old_gap < lineup.STEP - 5.0,
             "on their slots to %.4f cm; the baked paths %.2f cm apart (step %.0f) - read at the "
             "keyed size they would have stood %.2f apart; reach %.2f cm  |  %s"
             % (miss, gap, lineup.STEP, old_gap, reach, text.split("  |  ")[0][:160]))
        REPORT.setdefault("square", {})[target] = dict(miss=miss, gap=gap, old_gap=old_gap,
                                                        reach=reach, text=text)

def main():
    t_all = time.time()
    try:
        for phase, run in (("playermale", phase_playermale), ("skeletons", phase_skeletons),
                           ("rigs", phase_rigs), ("drop", phase_drop)):
            if not PHASES or phase in PHASES:
                run()
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
