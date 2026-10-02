"""Synthetic humanoid skeletons in every convention maya_skeletonmap knows.

Stdlib only: the unit tests read the joints as (name, parent, world position)
rows, and docs/superpowers/plans/verify_skeleton_conventions.py builds the very
same rows as Maya joints. One body (a 180 cm human, Y up, facing +Z, its left on
+X) wearing each convention's names, hierarchy quirks, rest pose and unit:

    ue5          UE5 Manny: root, pelvis, spine_01..05, neck_01/02, metacarpals,
                 twist bones beside the limbs, ik_ helpers
    ue4          UE4 Mannequin: spine_01..03, one neck, no metacarpals
    mixamo       mixamorig:Hips, Spine/Spine1/Spine2, LeftShoulder, HeadTop_End
    hik          MotionBuilder HumanIK with a Character1_ prefix, Spine..Spine3,
                 roll bones, LeftFingerBase... no, HIK names fingers LeftHandIndex1
    unity        Mecanim names: LeftUpperLeg, LeftLowerArm, UpperChest, Proximal..
    vrm          VRoid: J_Bip_C_Hips, J_Bip_L_UpperArm, A-pose, metres
    rigify       Blender Rigify deform bones: DEF-spine.00N, .001 segments,
                 DEF-pelvis.L, DEF-palm.0N.L, metres under an Armature null
    arp          Auto-Rig Pro export: root.x is the hips, *_stretch.l
    biped        3ds Max Biped: Bip001 (centre of mass) > Bip001 Pelvis, thighs off
                 Bip001 Spine, clavicles off Bip001 Neck, Finger01-style numbers,
                 nubs, a Z-up wrapper
    cc           Character Creator: CC_Base_BoneRoot > Hip > Pelvis / Waist,
                 NeckTwist01/02, twist bones
    daz          Daz Genesis 8: hip > pelvis / abdomenLower..chestUpper, lShldrBend,
                 lShldrTwist, lCarpal1-4
    cmu          CMU BVH (cgspeed): LHipJoint, LowerBack, Neck1, LeftFingerBase,
                 LThumb, BVH units
    xsens        Xsens MVN: Pelvis, L5, L3, T12, T8, RightUpperArm
    synty        Synty: Clavicle_L > Shoulder_L > Elbow_L, side-less finger names
    obfuscated   joint1..jointN, no names at all: only the shape says anything

`build(name)` answers (rows, expected): rows are (joint, parent, (x, y, z)) in the
order a builder can create them, positions in WORLD units; expected is {our UE5
bone: joint} for the bones a recogniser must find.
"""

import math

STATURE = 180.0

# the body, in cm, T-pose, Y up, facing +Z, left on +X
HIPS = (0.0, 95.0, 0.0)
CHEST_TOP = 140.0
NECK_BASE = 147.0
HEAD = (0.0, 160.0, 1.0)
HEAD_END = (0.0, 178.0, 1.0)
CLAVICLE = (3.0, 144.0, 2.0)
SHOULDER = (16.0, 145.0, 0.0)
ELBOW = (43.0, 145.0, -1.0)
WRIST = (69.0, 145.0, 0.0)
HIP = (9.5, 91.0, 0.0)
KNEE = (10.0, 50.0, 1.5)
ANKLE = (10.5, 9.0, -2.0)
BALL = (10.5, 2.0, 12.0)
TOE_END = (10.5, 1.0, 19.0)
FINGER_BASE = {"thumb": (2.5, -2.0, 3.5), "index": (8.5, 0.0, 3.0),
               "middle": (9.0, 0.0, 1.0), "ring": (8.5, 0.0, -1.0),
               "pinky": (7.5, -0.5, -3.0)}
FINGER_STEP = {"thumb": (2.5, -0.5, 1.5)}
META = {"index": (3.5, 0.0, 2.5), "middle": (3.5, 0.0, 0.8),
        "ring": (3.5, 0.0, -0.8), "pinky": (3.2, -0.3, -2.4)}
FINGERS = ("thumb", "index", "middle", "ring", "pinky")


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _mirror(p, side):
    return p if side == "l" else (-p[0], p[1], p[2])


def _lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def _a_pose(p, side, pivot):
    """The arm turned 45 deg down about the shoulder (an A-pose)."""
    if p[1] < 120.0 or abs(p[0]) < abs(pivot[0]) - 1e-9:
        return p
    sign = 1.0 if side == "l" else -1.0
    dx, dy = p[0] - pivot[0], p[1] - pivot[1]
    c = math.cos(math.radians(-45.0 * sign))
    s = math.sin(math.radians(-45.0 * sign))
    return (pivot[0] + dx * c - dy * s, pivot[1] + dx * s + dy * c, p[2])


class Spec(object):
    """What one convention calls things, and how its hierarchy differs."""

    def __init__(self, **kwargs):
        self.root = None
        self.root_at_floor = True
        self.hips = "Hips"
        self.extra_hip = None            # a node between hips and the thighs (CC, Daz)
        self.spine = ["Spine", "Spine1", "Spine2"]
        self.neck = ["Neck"]
        self.head = "Head"
        self.head_end = None
        self.clavicle_parent = "chest"   # "chest" | "neck"
        self.thigh_parent = "hips"       # "hips" | "spine" | "extra" | "offset"
        self.offset = None               # fn(side): CMU's LHipJoint
        self.limb = None                 # fn(part, side) -> name
        self.finger = None               # fn(finger, segment, side) -> name
        self.meta = None                 # fn(finger, side) -> name, or None
        self.palm = None                 # fn(side): one palm bone over the fingers
        self.fingers = FINGERS
        self.twist = None                # fn(part, side) -> twist child name
        self.segments = None             # fn(part, side) -> .001 segment name
        self.nub = None                  # fn(name) -> end nub name
        self.extras = None               # fn(side) -> [(name, parent part, offset)]
        self.pose = "T"
        self.scale = 1.0
        self.wrapper = None
        self.namespace = ""
        for key, value in kwargs.items():
            if not hasattr(self, key):
                raise KeyError(key)
            setattr(self, key, value)


def _ue_limb(part, side):
    return {"clav": "clavicle", "upper": "upperarm", "fore": "lowerarm", "hand": "hand",
            "thigh": "thigh", "calf": "calf", "foot": "foot", "toe": "ball"}[part] + "_" + side


def _ue_finger(finger, segment, side):
    return "%s_%02d_%s" % (finger, segment, side)


def _hik_limb(part, side):
    s = "Left" if side == "l" else "Right"
    return s + {"clav": "Shoulder", "upper": "Arm", "fore": "ForeArm", "hand": "Hand",
                "thigh": "UpLeg", "calf": "Leg", "foot": "Foot", "toe": "ToeBase"}[part]


def _hik_finger(finger, segment, side):
    return "%sHand%s%d" % ("Left" if side == "l" else "Right", finger.capitalize(), segment)


def _unity_limb(part, side):
    s = "Left" if side == "l" else "Right"
    return s + {"clav": "Shoulder", "upper": "UpperArm", "fore": "LowerArm", "hand": "Hand",
                "thigh": "UpperLeg", "calf": "LowerLeg", "foot": "Foot", "toe": "Toes"}[part]


def _unity_finger(finger, segment, side):
    return "%s%s%s" % ("Left" if side == "l" else "Right",
                       {"pinky": "Little"}.get(finger, finger.capitalize()),
                       ("Proximal", "Intermediate", "Distal")[segment - 1])


def _vrm_limb(part, side):
    return "J_Bip_%s_%s" % (side.upper(), {
        "clav": "Shoulder", "upper": "UpperArm", "fore": "LowerArm", "hand": "Hand",
        "thigh": "UpperLeg", "calf": "LowerLeg", "foot": "Foot", "toe": "ToeBase"}[part])


def _vrm_finger(finger, segment, side):
    return "J_Bip_%s_%s%d" % (side.upper(), {"pinky": "Little"}.get(finger, finger.capitalize()),
                              segment)


def _rigify_limb(part, side):
    return "DEF-%s.%s" % ({"clav": "shoulder", "upper": "upper_arm", "fore": "forearm",
                           "hand": "hand", "thigh": "thigh", "calf": "shin", "foot": "foot",
                           "toe": "toe"}[part], side.upper())


def _rigify_finger(finger, segment, side):
    base = "thumb" if finger == "thumb" else "f_" + finger
    return "DEF-%s.%02d.%s" % (base, segment, side.upper())


def _arp_limb(part, side):
    return {"clav": "shoulder", "upper": "arm_stretch", "fore": "forearm_stretch",
            "hand": "hand", "thigh": "thigh_stretch", "calf": "leg_stretch",
            "foot": "foot", "toe": "toes_01"}[part] + "." + side


def _arp_finger(finger, segment, side):
    return "%s%d.%s" % (finger, segment, side)


def _biped_limb(part, side):
    return "Bip001_%s_%s" % (side.upper(), {
        "clav": "Clavicle", "upper": "UpperArm", "fore": "Forearm", "hand": "Hand",
        "thigh": "Thigh", "calf": "Calf", "foot": "Foot", "toe": "Toe0"}[part])


def _biped_finger(finger, segment, side):
    number = FINGERS.index(finger)
    return "Bip001_%s_Finger%d%s" % (side.upper(), number,
                                    "" if segment == 1 else str(segment - 1))


def _cc_limb(part, side):
    return "CC_Base_%s_%s" % (side.upper(), {
        "clav": "Clavicle", "upper": "Upperarm", "fore": "Forearm", "hand": "Hand",
        "thigh": "Thigh", "calf": "Calf", "foot": "Foot", "toe": "ToeBase"}[part])


def _cc_finger(finger, segment, side):
    return "CC_Base_%s_%s%d" % (side.upper(), {"middle": "Mid"}.get(finger, finger.capitalize()),
                               segment)


def _daz_limb(part, side):
    return side + {"clav": "Collar", "upper": "ShldrBend", "fore": "ForearmBend",
                   "hand": "Hand", "thigh": "ThighBend", "calf": "Shin", "foot": "Foot",
                   "toe": "Toe"}[part]


def _daz_finger(finger, segment, side):
    return "%s%s%d" % (side, {"middle": "Mid"}.get(finger, finger.capitalize()), segment)


def _cmu_limb(part, side):
    return _hik_limb(part, side)


def _cmu_finger(finger, segment, side):
    if finger == "thumb":
        return "%sThumb" % side.upper() if segment == 1 else None
    if finger == "index" and segment == 1:
        return "%sHandIndex1" % ("Left" if side == "l" else "Right")
    return None


def _xsens_limb(part, side):
    s = "Left" if side == "l" else "Right"
    return s + {"clav": "Shoulder", "upper": "UpperArm", "fore": "ForeArm", "hand": "Hand",
                "thigh": "UpperLeg", "calf": "LowerLeg", "foot": "Foot", "toe": "Toe"}[part]


def _synty_limb(part, side):
    return {"clav": "Clavicle", "upper": "Shoulder", "fore": "Elbow", "hand": "Hand",
            "thigh": "UpperLeg", "calf": "LowerLeg", "foot": "Ankle", "toe": "Ball"}[part] \
        + "_" + side.upper()


def _synty_finger(finger, segment, side):
    base = {"thumb": "Thumb", "index": "IndexFinger", "middle": "Finger"}.get(finger)
    if base is None:
        return None
    # the left hand's fingers carry no side (the parent's is inherited); the
    # right ones a suffix, so every row stays a unique name
    return "%s_%02d" % (base, segment) + ("" if side == "l" else "_R")


SPECS = {
    "ue5": Spec(root="root", hips="pelvis",
                spine=["spine_01", "spine_02", "spine_03", "spine_04", "spine_05"],
                neck=["neck_01", "neck_02"], head="head", limb=_ue_limb, finger=_ue_finger,
                meta=lambda f, s: "%s_metacarpal_%s" % (f, s),
                twist=lambda part, s: {"upper": "upperarm_twist_01_" + s,
                                       "fore": "lowerarm_twist_01_" + s,
                                       "thigh": "thigh_twist_01_" + s}.get(part),
                extras=lambda s: [("ik_foot_" + s, "root", (10.0 if s == "l" else -10.0, 9.0, 0.0))],
                pose="A"),
    "ue4": Spec(root="root", hips="pelvis", spine=["spine_01", "spine_02", "spine_03"],
                neck=["neck_01"], head="head", limb=_ue_limb, finger=_ue_finger, pose="A"),
    "mixamo": Spec(namespace="mixamorig:", limb=_hik_limb, finger=_hik_finger,
                   head_end="HeadTop_End", nub=lambda n: n.replace("3", "4") if n[-1] == "3" else None),
    "hik": Spec(namespace="", hips="Character1_Hips",
                spine=["Character1_Spine", "Character1_Spine1", "Character1_Spine2",
                       "Character1_Spine3"],
                neck=["Character1_Neck"], head="Character1_Head",
                limb=lambda p, s: "Character1_" + _hik_limb(p, s),
                finger=lambda f, g, s: "Character1_" + _hik_finger(f, g, s),
                twist=lambda part, s: {"upper": "Character1_%sArmRoll" % ("Left" if s == "l" else "Right"),
                                       "fore": "Character1_%sForeArmRoll" % ("Left" if s == "l" else "Right")}.get(part)),
    "unity": Spec(spine=["Spine", "Chest", "UpperChest"], limb=_unity_limb,
                  finger=_unity_finger),
    "vrm": Spec(hips="J_Bip_C_Hips", spine=["J_Bip_C_Spine", "J_Bip_C_Chest", "J_Bip_C_UpperChest"],
                neck=["J_Bip_C_Neck"], head="J_Bip_C_Head", limb=_vrm_limb, finger=_vrm_finger,
                pose="A", scale=0.01),
    "rigify": Spec(hips="DEF-spine", spine=["DEF-spine.001", "DEF-spine.002", "DEF-spine.003"],
                   neck=["DEF-spine.004", "DEF-spine.005"], head="DEF-spine.006",
                   limb=_rigify_limb, finger=_rigify_finger,
                   meta=lambda f, s: "DEF-palm.%02d.%s" % (("index", "middle", "ring", "pinky").index(f) + 1,
                                                          s.upper()),
                   segments=lambda part, s: (_rigify_limb(part, s) + ".001")
                   if part in ("upper", "fore", "thigh", "calf") else None,
                   extras=lambda s: [("DEF-pelvis." + s.upper(), "hips", (6.0 if s == "l" else -6.0, 93.0, 3.0))],
                   scale=0.01, wrapper="Armature"),
    "arp": Spec(hips="root.x", spine=["spine_01.x", "spine_02.x", "spine_03.x"],
                neck=["neck.x"], head="head.x", limb=_arp_limb, finger=_arp_finger,
                twist=lambda part, s: {"upper": "arm_twist." + s, "fore": "forearm_twist." + s,
                                       "thigh": "thigh_twist." + s}.get(part)),
    "biped": Spec(root="Bip001", root_at_floor=False, hips="Bip001_Pelvis",
                  spine=["Bip001_Spine", "Bip001_Spine1", "Bip001_Spine2"],
                  neck=["Bip001_Neck"], head="Bip001_Head", head_end="Bip001_HeadNub",
                  clavicle_parent="neck", thigh_parent="spine", limb=_biped_limb,
                  finger=_biped_finger, nub=lambda n: n + "Nub" if n.endswith("Toe0") else None,
                  wrapper="BipedZup"),
    "cc": Spec(root="CC_Base_BoneRoot", hips="CC_Base_Hip", extra_hip="CC_Base_Pelvis",
               spine=["CC_Base_Waist", "CC_Base_Spine01", "CC_Base_Spine02"],
               neck=["CC_Base_NeckTwist01", "CC_Base_NeckTwist02"], head="CC_Base_Head",
               thigh_parent="extra", limb=_cc_limb, finger=_cc_finger,
               twist=lambda part, s: {"upper": "CC_Base_%s_UpperarmTwist01" % s.upper(),
                                      "fore": "CC_Base_%s_ForearmTwist01" % s.upper(),
                                      "thigh": "CC_Base_%s_ThighTwist01" % s.upper()}.get(part)),
    "daz": Spec(root="Genesis8Female", hips="hip", extra_hip="pelvis",
                spine=["abdomenLower", "abdomenUpper", "chestLower", "chestUpper"],
                neck=["neckLower", "neckUpper"], head="head", thigh_parent="extra",
                limb=_daz_limb, finger=_daz_finger,
                meta=lambda f, s: "%sCarpal%d" % (s, ("index", "middle", "ring", "pinky").index(f) + 1),
                twist=lambda part, s: {"upper": s + "ShldrTwist", "fore": s + "ForearmTwist",
                                       "thigh": s + "ThighTwist"}.get(part)),
    "cmu": Spec(spine=["LowerBack", "Spine", "Spine1"], neck=["Neck", "Neck1"],
                thigh_parent="offset", offset=lambda s: "%sHipJoint" % s.upper(),
                limb=_cmu_limb, finger=_cmu_finger,
                palm=lambda s: "%sFingerBase" % ("Left" if s == "l" else "Right"),
                scale=0.45),
    "xsens": Spec(hips="Pelvis", spine=["L5", "L3", "T12", "T8"], neck=["Neck"],
                  limb=_xsens_limb, finger=lambda f, g, s: None),
    "synty": Spec(root="Root", spine=["Spine_01", "Spine_02", "Spine_03"], neck=["Neck"],
                  limb=_synty_limb, finger=_synty_finger, fingers=("thumb", "index", "middle")),
}


def _obfuscate():
    names = {}

    def name(real):
        if real not in names:
            names[real] = "joint%d" % (len(names) + 1)
        return names[real]
    return name


def build(convention):
    """(rows, expected) for one convention; see the module docstring."""
    if convention == "obfuscated":
        rows, expected = build("mixamo")
        rename = _obfuscate()
        rows = [(rename(n), rename(p) if p else None, pos) for n, p, pos in rows]
        expected = dict((ours, rename(src)) for ours, src in expected.items()
                        if not any(ours.startswith(f) for f in FINGERS))
        return rows, expected
    spec = SPECS[convention]
    ns = spec.namespace
    rows, expected = [], {}

    def add(name, parent, pos, ours=None):
        if name is None:
            return None
        rows.append((ns + name, (ns + parent) if parent else None, pos))
        if ours:
            expected[ours] = ns + name
        return name

    if spec.root:
        add(spec.root, None, (0.0, 0.0, 0.0) if spec.root_at_floor else HIPS,
            "root" if spec.root_at_floor else None)
    add(spec.hips, spec.root, HIPS, "pelvis")
    hip_parent = spec.hips
    if spec.extra_hip:
        add(spec.extra_hip, spec.hips, (0.0, 93.0, 0.0))
    spine_ours = _distribute(spec.spine, ("spine_01", "spine_02", "spine_03", "spine_04", "spine_05"))
    parent = spec.hips
    for i, joint in enumerate(spec.spine):
        y = HIPS[1] + 5.0 + (CHEST_TOP - HIPS[1] - 5.0) * i / max(1, len(spec.spine) - 1)
        add(joint, parent, (0.0, y, 0.0), spine_ours.get(joint))
        parent = joint
    chest = parent
    neck_ours = _distribute(spec.neck, ("neck_01", "neck_02"))
    for i, joint in enumerate(spec.neck):
        y = NECK_BASE + 6.0 * i / max(1, len(spec.neck))
        add(joint, parent, (0.0, y, 0.0), neck_ours.get(joint))
        parent = joint
    add(spec.head, parent, HEAD, "head")
    if spec.head_end:
        add(spec.head_end, spec.head, HEAD_END)
    for side in ("l", "r"):
        _arm(spec, side, chest, add)
        _leg(spec, side, hip_parent, add)
    if spec.extras:
        for side in ("l", "r"):
            for name, part, pos in spec.extras(side):
                add(name, {"root": spec.root, "hips": spec.hips}[part], pos)
    rows = _scaled(rows, spec.scale)
    return rows, expected


def _arm(spec, side, chest, add):
    m = lambda p: _a_pose(_mirror(p, side), side, _mirror(SHOULDER, side)) \
        if spec.pose == "A" else _mirror(p, side)
    parent = spec.neck[0] if spec.clavicle_parent == "neck" else chest
    clav = add(spec.limb("clav", side), parent, m(CLAVICLE), "clavicle_" + side)
    upper = add(spec.limb("upper", side), clav, m(SHOULDER), "upperarm_" + side)
    last = upper
    if spec.segments:
        last = add(spec.segments("upper", side), upper, m(_lerp(SHOULDER, ELBOW, 0.5)))
    if spec.twist and spec.twist("upper", side):
        add(spec.twist("upper", side), upper, m(_lerp(SHOULDER, ELBOW, 0.4)))
    fore = add(spec.limb("fore", side), last, m(ELBOW), "lowerarm_" + side)
    last = fore
    if spec.segments:
        last = add(spec.segments("fore", side), fore, m(_lerp(ELBOW, WRIST, 0.5)))
    if spec.twist and spec.twist("fore", side):
        add(spec.twist("fore", side), fore, m(_lerp(ELBOW, WRIST, 0.6)))
    hand = add(spec.limb("hand", side), last, m(WRIST), "hand_" + side)
    finger_parent = hand
    if spec.palm:
        # one palm bone over the index (CMU's FingerBase): it plays the index metacarpal
        finger_parent = add(spec.palm(side), hand, m(_add(WRIST, (3.0, 0.0, 0.0))),
                            "index_metacarpal_" + side)
    for finger in spec.fingers:
        base = _add(WRIST, FINGER_BASE[finger])
        step = FINGER_STEP.get(finger, (3.0, -0.3, 0.0))
        parent = finger_parent if finger != "thumb" else hand
        if spec.meta and finger != "thumb":
            meta = add(spec.meta(finger, side), finger_parent, m(_add(WRIST, META[finger])),
                       "%s_metacarpal_%s" % (finger, side))
            parent = meta
        for segment in (1, 2, 3):
            name = spec.finger(finger, segment, side)
            if name is None:
                break
            pos = _add(base, tuple(c * (segment - 1) for c in step))
            add(name, parent, m(pos), "%s_%02d_%s" % (finger, segment, side))
            parent = name
        if spec.nub and parent:
            nub = spec.nub(parent) if parent != finger_parent else None
            if nub:
                add(nub, parent, m(_add(base, tuple(c * 3 for c in step))))


def _leg(spec, side, hips, add):
    m = lambda p: _mirror(p, side)
    parent = {"hips": hips, "spine": spec.spine[0], "extra": spec.extra_hip,
              "offset": hips}[spec.thigh_parent]
    if spec.thigh_parent == "offset":
        parent = add(spec.offset(side), hips, m((4.0, 94.0, 0.0)))
    thigh = add(spec.limb("thigh", side), parent, m(HIP), "thigh_" + side)
    last = thigh
    if spec.segments:
        last = add(spec.segments("thigh", side), thigh, m(_lerp(HIP, KNEE, 0.5)))
    if spec.twist and spec.twist("thigh", side):
        add(spec.twist("thigh", side), thigh, m(_lerp(HIP, KNEE, 0.4)))
    calf = add(spec.limb("calf", side), last, m(KNEE), "calf_" + side)
    last = calf
    if spec.segments:
        last = add(spec.segments("calf", side), calf, m(_lerp(KNEE, ANKLE, 0.5)))
    foot = add(spec.limb("foot", side), last, m(ANKLE), "foot_" + side)
    toe = add(spec.limb("toe", side), foot, m(BALL), "ball_" + side)
    if spec.nub:
        nub = spec.nub(spec.limb("toe", side))
        if nub:
            add(nub, toe, m(TOE_END))


def _distribute(sources, targets):
    n, m = len(sources), len(targets)
    if n == 1:
        return {sources[0]: targets[0]}
    if n >= m:
        return dict((sources[int(j * (n - 1) / float(m - 1) + 0.5)], targets[j]) for j in range(m))
    return dict((sources[i], targets[int(i * (m - 1) / float(n - 1) + 0.5)]) for i in range(n))


def _scaled(rows, scale):
    return [(n, p, tuple(c * scale for c in pos)) for n, p, pos in rows]


def paths(rows, top=""):
    """{joint: long DAG path} for rows, under an optional group path `top`."""
    parent_of = dict((n, p) for n, p, _pos in rows)
    out = {}
    for name, _p, _pos in rows:
        chain, node = [], name
        while node:
            chain.append(node)
            node = parent_of.get(node)
        out[name] = top + "".join("|" + n for n in reversed(chain))
    return out


CONVENTIONS = tuple(SPECS) + ("obfuscated",)
