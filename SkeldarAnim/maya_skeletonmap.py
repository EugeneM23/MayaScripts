"""Which bone of a foreign humanoid skeleton is which of OURS: a pure map.

2026-10-02, the animator: «Нужно проработать ретаргеты для наших ригов ... Так же
я бы хотел что бы ты прошелся по интернету нашел самые часто используемые иерархии
костей для Unity, Mixamo, blender, motionbuilder, 3dmax Unrealengine и сделал
ретаргеты для этих систем на наши риги и скелеты.»

Every retarget here speaks UE5 Manny's names (`pelvis`, `spine_01..05`, `neck_01/02`,
`head`, `clavicle_l`, `upperarm_l`, `lowerarm_l`, `hand_l`, `thumb_01_l` ...,
`thigh_l`, `calf_l`, `foot_l`, `ball_l`). This module takes a source skeleton - its
joints as long DAG paths, so the hierarchy comes with them, and optionally their
world positions at rest - and answers {our name: source path}: which source joint
plays each of our bones. It knows the conventions a game studio actually meets
(the spec lists every one with its sources):

    Unreal (UE4 Mannequin, UE5 Manny)    pelvis, spine_01, upperarm_l, ...
    Mixamo / MotionBuilder HumanIK       mixamorig:Hips, LeftUpLeg, LeftArm, Spine1..9
    Unity Mecanim / Unity-chan           LeftUpperLeg, LeftLowerArm / Character1_*
    VRM / VRoid                          J_Bip_C_Hips, J_Bip_L_UpperArm
    Blender Rigify (deform bones)        DEF-spine.003, DEF-upper_arm.L, DEF-f_index.01.L
    Blender Auto-Rig Pro export          root.x, thigh_stretch.l, arm_stretch.l
    3ds Max Biped / CAT                  Bip001 Pelvis, Bip001 L Thigh, Bip001 L Finger01
    Character Creator / iClone           CC_Base_Hip, CC_Base_L_Upperarm, CC_Base_NeckTwist01
    Daz Genesis 3/8                      hip, abdomenLower, lShldrBend, lForearmBend
    CMU BVH (cgspeed)                    Hips, LHipJoint, LowerBack, Neck1, LThumb
    Xsens MVN / Rokoko                   Pelvis, L5, L3, T12, T8 / HumanIK names
    Synty                                Hips, Spine_01, Clavicle_L, Shoulder_L, Elbow_L

The recognition is by NAME first - tokens after namespaces, known prefixes, case,
separators and camel-case are taken apart, the side read wherever it sits (a
prefix `Left`/`L `/`l`, a suffix `_l`/`.L`, an infix `_L_`) - and the CHAIN decides
what the names cannot: an arm is the path from the spine to a hand, so its first
joint is the clavicle and the one before the forearm the upper arm, whatever they
are called (`Shoulder` is a clavicle in HumanIK and an upper arm in Synty); the
hips are the joint where both legs and the spine meet (Biped hangs its thighs off
`Spine`, Character Creator splits `Hip` into `Pelvis` and `Waist`); N source spine
joints are DISTRIBUTED onto our five with both ends kept (`distribute`). Twist,
roll, end, nub, IK, weapon and camera bones are never mapped. When the names fail
and positions are given, a STRUCTURAL pass finds the same parts from the shape:
the two lowest leaves are the feet, their common ancestor with the top is the
hips, the two leaves furthest out sideways are the hands.

It refuses rather than guesses: no hips, no head, a missing leg or arm is a
refusal that names what was not found.

Stdlib only (a subprocess test pins it): the scene is the caller's.
Spec: docs/superpowers/specs/2026-10-02-skeleton-conventions-design.md
"""

import collections
import math
import re

TARGET_SPINE = ("spine_01", "spine_02", "spine_03", "spine_04", "spine_05")
TARGET_NECK = ("neck_01", "neck_02")
FINGERS = ("thumb", "index", "middle", "ring", "pinky")
SIDES = ("l", "r")
# what a retarget cannot do without: a refusal names the first missing
CORE = ("pelvis", "head",
        "thigh_l", "calf_l", "foot_l", "thigh_r", "calf_r", "foot_r",
        "upperarm_l", "lowerarm_l", "hand_l", "upperarm_r", "lowerarm_r", "hand_r")
WORDS = {
    "pelvis": "Hips/pelvis",
    "head": "Head",
    "thigh": "a thigh (thigh, UpLeg, UpperLeg, ThighBend)",
    "calf": "a lower leg (calf, Leg, LowerLeg, shin, knee)",
    "foot": "a foot (foot, ankle)",
    "upperarm": "an upper arm (upperarm, Arm, UpperArm, ShldrBend)",
    "lowerarm": "a forearm (lowerarm, ForeArm, LowerArm, elbow)",
    "hand": "a hand (hand, wrist)",
}

Result = collections.namedtuple(
    "Result", "mapping convention confidence missing refusal notes chains")
Info = collections.namedtuple("Info", "kind side finger segment")

# ---------------------------------------------------------------- names

_IGNORE = frozenset((
    "twist", "roll", "nub", "end", "site", "tip", "ik", "pole", "target", "weapon",
    "camera", "prop", "props", "eye", "eyes", "jaw", "tongue", "teeth", "breast",
    "ear", "hair", "helper", "corrective", "share", "skirt", "cloth", "cape",
    "attach", "socket", "dummy", "mch", "ctrl", "eyelid", "brow", "lip", "cheek",
    "nose", "chin", "spring", "dynamic", "sec", "bust", "glute", "ribs",
    "pectoral", "interaction", "mass", "foottip", "toetip"))
_DROP = frozenset(("mixamorig", "def", "org", "cc", "base", "j", "bip", "jnt",
                   "bend", "stretch", "f", "c", "x", "m", "character",
                   "bn", "b", "bone", "joint"))
_FINGER_WORDS = {"thumb": "thumb", "index": "index", "middle": "middle",
                 "mid": "middle", "ring": "ring", "pinky": "pinky", "pink": "pinky",
                 "little": "pinky"}
_SPINE_WORDS = frozenset(("spine", "chest", "abdomen", "waist", "torso", "back",
                          "belly", "stomach", "ribcage", "upperchest", "lowerback",
                          "abdomenlower", "abdomenupper", "chestlower",
                          "chestupper", "spline"))
_PALM_WORDS = frozenset(("metacarpal", "carpal", "palm", "metacarpals"))
_XSENS_SPINE = re.compile(r"^(L5|L3|T12|T8|C7)$")
_BIPED_FINGERS = ("thumb", "index", "middle", "ring", "pinky")


def leaf(path):
    """A DAG path's last name without its namespace."""
    return path.split("|")[-1].split(":")[-1]


def tokens(name):
    """The lower-case words of a joint name: namespaces gone, camel case,
    digits and every separator (space _ . - :) taken apart.

    `mixamorig:LeftUpLeg` -> left up leg, `Bip001 L UpperArm` -> bip 001 l upper
    arm, `DEF-upper_arm.L.001` -> def upper arm l 001, `lShldrBend` -> l shldr
    bend, `LHipJoint` -> l hip joint."""
    text = leaf(name)
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    text = re.sub(r"([A-Z])([A-Z][a-z])", r"\1 \2", text)
    text = re.sub(r"([A-Za-z])([0-9])", r"\1 \2", text)
    text = re.sub(r"([0-9])([A-Za-z])", r"\1 \2", text)
    return [part.lower() for part in re.split(r"[\s_.\-:]+", text) if part]


def convention_of(paths):
    """The convention a skeleton's names belong to - for the status line and
    for the one rule that changes meaning by convention (Biped's two-digit
    finger numbers). Pure."""
    leaves = [leaf(p) for p in paths]
    full = " ".join(paths)
    names = set(leaves)
    low = set(n.lower() for n in leaves)
    if "mixamorig" in full.lower():
        return "mixamo"
    if any(n.startswith("J_Bip_") for n in leaves):
        return "vrm"
    if any(n.startswith("CC_Base_") for n in leaves):
        return "character_creator"
    if any(re.match(r"(?i)^bip0*\d+([ _]|$)", n) for n in leaves):
        return "3dsmax_biped"
    if any(n.startswith("DEF-") or n.startswith("DEF_") for n in leaves):
        return "blender_rigify"
    if any(n.endswith(".x") for n in leaves) or any("stretch" in n for n in low) \
            or ("root_x" in names and any(n.endswith("_x") and n != "root_x" for n in leaves)):
        return "blender_autorigpro"
    if {"abdomenLower", "lShldrBend"} & names or {"abdomen", "lShldr"} & names:
        return "daz_genesis"
    if {"LHipJoint", "LowerBack"} & names:
        return "cmu_bvh"
    if {"L5", "T8"} <= names:
        return "xsens"
    if "spine_05" in names and "pelvis" in names:
        return "unreal_ue5"
    if "pelvis" in names and "spine_03" in names and "clavicle_l" in names:
        return "unreal_ue4"
    if any(re.match(r"^(Left|Right)(Upper|Lower)(Leg|Arm)$", n) for n in leaves):
        return "unity_mecanim"
    if any(re.match(r"^(Character\d*_)?(Left|Right)UpLeg$", n) for n in leaves):
        return "motionbuilder_hik"
    if {"UpperLeg_L", "Elbow_L"} & names or {"UpperLeg_R", "Elbow_R"} & names:
        return "synty"
    if any(n.endswith((".L", ".R", ".l", ".r")) for n in leaves):
        return "blender"
    return "generic"


def parse(path, convention="generic"):
    """Info(kind, side, finger, segment) for one joint, from its name alone.

    kind: hips, root, spine, neck, head, clavicle, shoulder (a clavicle or an
    upper arm - the chain decides), upperarm, lowerarm, hand, palm, finger,
    thigh, calf, foot, toe, ignore, or None (unknown). side: "l", "r" or "".
    """
    name = leaf(path)
    if _XSENS_SPINE.match(name):
        return Info("spine", "", None, None)
    words = tokens(path)
    if convention == "blender_rigify":
        rigify = _rigify(name)
        if rigify is not None:
            return rigify
    side = ""
    rest = []
    for word in words:
        if word in ("l", "left", "lt"):
            side = side or "l"
        elif word in ("r", "right", "rt"):
            side = side or "r"
        else:
            rest.append(word)
    if any(word in _IGNORE for word in rest) and "neck" not in rest:
        return Info("ignore", side, None, None)
    body = [w for w in rest if w not in _DROP]
    digits = [w for w in body if w.isdigit()]
    plain = [w for w in body if not w.isdigit()]
    words_set = set(plain)
    if not plain:
        if "bip" in rest or "root" in rest:
            return Info("root", "", None, None)
        return Info(None, side, None, None)

    if words_set & _PALM_WORDS or ("finger" in words_set and "base" in rest):
        finger = next((_FINGER_WORDS[w] for w in plain if w in _FINGER_WORDS), None)
        return Info("palm", side, finger, None)
    finger = next((_FINGER_WORDS[w] for w in plain if w in _FINGER_WORDS), None)
    if finger:
        return Info("finger", side, finger, int(digits[0]) if digits else None)
    if "finger" in words_set:
        if convention == "3dsmax_biped" and digits:
            code = digits[-1]
            which = int(code[0])
            if which < len(_BIPED_FINGERS):
                segment = 1 + (int(code[1:]) if len(code) > 1 else 0)
                return Info("finger", side, _BIPED_FINGERS[which], segment)
        return Info("finger", side, "middle", int(digits[0]) if digits else None)

    if "neck" in words_set:
        return Info("neck", "", None, None)
    if "head" in words_set:
        return Info("head", "", None, None)
    if "clavicle" in words_set or "collar" in words_set or "clav" in words_set \
            or "scapula" in words_set:
        return Info("clavicle", side, None, None)
    if "shoulder" in words_set:
        return Info("shoulder", side, None, None)
    if "shldr" in words_set or "upperarm" in words_set or "humerus" in words_set:
        return Info("upperarm", side, None, None)
    if "forearm" in words_set or "lowerarm" in words_set or "elbow" in words_set \
            or "lowarm" in words_set:
        return Info("lowerarm", side, None, None)
    if "arm" in words_set:
        if words_set & {"fore", "lower", "low"}:
            return Info("lowerarm", side, None, None)
        return Info("upperarm", side, None, None)
    if "hand" in words_set or "wrist" in words_set:
        return Info("hand", side, None, None)
    if "thigh" in words_set or "upleg" in words_set or "upperleg" in words_set \
            or "femur" in words_set:
        return Info("thigh", side, None, None)
    if words_set & {"calf", "shin", "knee", "lowerleg", "lowleg", "tibia"}:
        return Info("calf", side, None, None)
    if "leg" in words_set:
        if words_set & {"up", "upper"}:
            return Info("thigh", side, None, None)
        return Info("calf", side, None, None)
    if "foot" in words_set or "ankle" in words_set:
        return Info("foot", side, None, None)
    if words_set & {"toe", "toes", "ball", "toebase"}:
        return Info("toe", side, None, None)
    if words_set & {"hips", "pelvis", "hip"}:
        if side:                    # a sided hip/pelvis is an offset bone (CMU
            return Info(None, side, None, None)   # LHipJoint, Rigify pelvis.L)
        return Info("hips", "", None, None)
    if words_set & _SPINE_WORDS:
        return Info("spine", "", None, None)
    if "root" in words_set:
        return Info("root", "", None, None)
    return Info(None, side, None, None)


def _rigify(name):
    """Rigify's deform spine is numbered, not named: `spine` is the hips,
    .001-.003 the spine, .004/.005 the neck, .006 the head."""
    # Maya has no '.' or '-' in a node name: an FBX import makes DEF-spine.003 DEF_spine_003
    match = re.match(r"^(?:DEF[-_])?spine(?:[._](\d+))?$", name)
    if not match:
        return None
    number = int(match.group(1) or 0)
    if number == 0:
        return Info("hips", "", None, None)
    if number <= 3:
        return Info("spine", "", None, None)
    if number <= 5:
        return Info("neck", "", None, None)
    if number == 6:
        return Info("head", "", None, None)
    return Info("ignore", "", None, None)


# ---------------------------------------------------------------- the tree

def parent_map(paths):
    """{path: the nearest ANCESTOR path in the set, or None}. Pure."""
    present = set(paths)
    out = {}
    for path in paths:
        up, parent = path, None
        while "|" in up:
            up = up.rsplit("|", 1)[0]
            if up in present:
                parent = up
                break
        out[path] = parent
    return out


def ancestors(path, parents):
    """The ancestors of `path` from its parent up to the top."""
    out, node = [], parents.get(path)
    while node:
        out.append(node)
        node = parents.get(node)
    return out


def is_under(path, top, parents):
    """`path` is `top` or below it."""
    return path == top or top in ancestors(path, parents)


def lca(nodes, parents):
    """The deepest common ancestor-or-self of `nodes`, or None."""
    nodes = [n for n in nodes if n]
    if not nodes:
        return None
    common = None
    chains = [[n] + ancestors(n, parents) for n in nodes]
    for candidate in chains[0]:
        if all(candidate in chain for chain in chains[1:]):
            common = candidate
            break
    return common


def path_between(top, bottom, parents):
    """The joints strictly between `top` and `bottom` (bottom below top), from
    the top down; None when bottom is not below top."""
    chain = ancestors(bottom, parents)
    if top not in chain:
        return None
    out = []
    for node in chain:
        if node == top:
            break
        out.append(node)
    return list(reversed(out))


def depth(path, parents):
    return len(ancestors(path, parents))


# ---------------------------------------------------------------- vectors

def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a):
    length = math.sqrt(_dot(a, a))
    if length < 1e-12:
        return None
    return (a[0] / length, a[1] / length, a[2] / length)


def _dist(a, b):
    return math.sqrt(_dot(_sub(a, b), _sub(a, b)))


def _line_distance(point, a, b):
    """How far `point` stands off the line a-b."""
    axis = _norm(_sub(b, a))
    if axis is None:
        return _dist(point, a)
    rel = _sub(point, a)
    along = _dot(rel, axis)
    return math.sqrt(max(0.0, _dot(rel, rel) - along * along))


def angle(a, b):
    """Degrees between two vectors (0 when either is zero)."""
    na, nb = _norm(a), _norm(b)
    if na is None or nb is None:
        return 0.0
    return math.degrees(math.acos(max(-1.0, min(1.0, _dot(na, nb)))))


# ---------------------------------------------------------------- distribution

def distribute(sources, targets):
    """{target: source}: N source joints onto M targets, both ends kept.

    More sources than targets: every target takes one, evenly spread
    (5 spine joints onto our 4: 1, 2, 4, 5). Fewer: every source takes one
    target and the rest stay at rest - Mixamo's 3 onto our 5 are spine_01,
    spine_03, spine_05, the rule the Mixamo retarget has had since
    2026-09-05. One source takes the first target. Pure."""
    sources, targets = list(sources), list(targets)
    n, m = len(sources), len(targets)
    if not n or not m:
        return {}
    if n == 1:
        return {targets[0]: sources[0]}
    if m == 1:
        return {targets[0]: sources[0]}
    if n >= m:
        return dict((targets[j], sources[int(j * (n - 1) / float(m - 1) + 0.5)])
                    for j in range(m))
    return dict((targets[int(i * (m - 1) / float(n - 1) + 0.5)], sources[i])
                for i in range(n))


# ---------------------------------------------------------------- recognition

def _labels(paths, parents, convention):
    """{path: Info}, a side inherited from the nearest sided ancestor where
    the name carries none (Synty's `Thumb_01` under `Hand_L`)."""
    info = dict((p, parse(p, convention)) for p in paths)
    limbs = ("clavicle", "shoulder", "upperarm", "lowerarm", "hand", "palm",
             "finger", "thigh", "calf", "foot", "toe", None, "ignore")
    for path in sorted(paths, key=lambda p: depth(p, parents)):
        here = info[path]
        if here.side or here.kind not in limbs:
            continue
        parent = parents.get(path)
        if parent is not None and info[parent].side:
            info[path] = here._replace(side=info[parent].side)
    return info


def _shallowest(candidates, parents):
    candidates = list(candidates)
    if not candidates:
        return None
    return min(candidates, key=lambda p: (depth(p, parents), p))


def _of(info, kind, side=None, under=None, parents=None, exclude=()):
    out = []
    for path, here in info.items():
        if here.kind != kind or path in exclude:
            continue
        if side is not None and here.side != side:
            continue
        if under is not None and not is_under(path, under, parents):
            continue
        out.append(path)
    return out


def _knee(chain, top, bottom, positions):
    """The joint of `chain` (between top and bottom) that bends: furthest off
    the top-bottom line when positions are known, else the first."""
    usable = [p for p in chain]
    if not usable:
        return None
    if positions and top in positions and bottom in positions:
        return max(usable, key=lambda p: _line_distance(positions[p], positions[top],
                                                        positions[bottom]))
    return usable[0]


def _leg(side, info, parents, positions, notes):
    thigh = _shallowest(_of(info, "thigh", side), parents)
    if thigh is None:
        return {}
    out = {"thigh": thigh}
    foot = _shallowest(_of(info, "foot", side, under=thigh, parents=parents), parents)
    calf = _shallowest([c for c in _of(info, "calf", side, under=thigh, parents=parents)
                        if c != thigh and (foot is None or is_under(foot, c, parents))],
                       parents)
    if calf is None and foot is not None:
        between = [p for p in path_between(thigh, foot, parents) or []
                   if info[p].kind not in ("ignore", "thigh")]
        calf = _knee(between, thigh, foot, positions)
        if calf:
            notes.append("%s lower leg found by the chain: %s" % (side.upper(), leaf(calf)))
    if calf is not None:
        out["calf"] = calf
    if foot is None and calf is not None:
        below = [c for c, p in parents.items() if p == calf and info[c].kind != "ignore"]
        foot = _shallowest(below, parents)
    if foot is not None:
        out["foot"] = foot
        toe = _shallowest(_of(info, "toe", side, under=foot, parents=parents), parents)
        if toe is not None and toe != foot:
            out["ball"] = toe
    return out


def _main_chain(hips, head, parents):
    """The joints from hips (exclusive) to head (exclusive)."""
    between = path_between(hips, head, parents)
    return between or []


def _arm(side, info, parents, positions, main, notes):
    hand = _shallowest(_of(info, "hand", side), parents)
    if hand is None:
        return {}, None
    up = ancestors(hand, parents)
    branch = next((node for node in up if node in main), None)
    if branch is None:              # a hand hanging off nothing of the body
        return {}, None
    chain = []
    for node in up:
        if node == branch:
            break
        chain.append(node)
    chain = [p for p in reversed(chain) if info[p].kind not in ("ignore", "palm")]
    out = {"hand": hand}
    if not chain:
        return out, branch
    fore = next((p for p in chain if info[p].kind == "lowerarm"), None)
    upper = next((p for p in chain if info[p].kind == "upperarm"), None)
    if upper is None and fore is not None:
        before = chain[:chain.index(fore)]
        upper = before[-1] if before else None
    if upper is None:
        shoulders = [p for p in chain if info[p].kind == "shoulder"]
        clav = [p for p in chain if info[p].kind == "clavicle"]
        if shoulders and clav:
            upper = shoulders[0]
    if fore is None and upper is not None:
        after = chain[chain.index(upper) + 1:]
        fore = _knee(after, upper, hand, positions) if after else None
        if fore:
            notes.append("%s forearm found by the chain: %s" % (side.upper(), leaf(fore)))
    if upper is None and fore is None and len(chain) >= 2:
        upper, fore = chain[-2], chain[-1]
        notes.append("%s arm found by the chain: %s, %s" % (side.upper(), leaf(upper), leaf(fore)))
    if upper is not None:
        out["upperarm"] = upper
        before = [p for p in chain[:chain.index(upper)]]
        clav = next((p for p in before if info[p].kind in ("clavicle", "shoulder")), None)
        if clav is None and before:
            clav = before[0]
        if clav is not None:
            out["clavicle"] = clav
    if fore is not None:
        out["lowerarm"] = fore
    return out, branch


def _fingers(side, hand, info, parents):
    out = {}
    if hand is None:
        return out
    for finger in FINGERS:
        joints = [p for p in _of(info, "finger", side, under=hand, parents=parents)
                  if info[p].finger == finger and p != hand]
        if not joints:
            continue
        joints.sort(key=lambda p: (depth(p, parents), p))
        # one chain: keep the joints that descend from the first one
        first = joints[0]
        chain = [p for p in joints if is_under(p, first, parents)][:3]
        for i, joint in enumerate(chain):
            out["%s_%02d_%s" % (finger, i + 1, side)] = joint
        parent = parents.get(first)
        if finger != "thumb" and parent and parent != hand and is_under(parent, hand, parents) \
                and info[parent].kind in ("palm", None, "finger") \
                and (info[parent].kind != "finger" or info[parent].finger is None):
            out["%s_metacarpal_%s" % (finger, side)] = parent
    return out


def _root(hips, info, parents, positions, notes):
    """The root-motion bone: an ancestor of the hips standing at the FLOOR
    (UE's root, Character Creator's BoneRoot). An ancestor at the hips' height
    (Biped's Bip001, the centre of mass) is no root: our Main is on the floor,
    and Main then takes the hips' horizontal travel instead."""
    above = ancestors(hips, parents)
    if not above:
        return None
    labelled = [p for p in above if info[p].kind == "root"]
    candidate = labelled[0] if labelled else above[-1]
    if positions and candidate in positions and hips in positions:
        floor = min(pos[1] for pos in positions.values())
        hip_height = positions[hips][1] - floor
        if hip_height > 1e-6 and positions[candidate][1] - floor > 0.15 * hip_height:
            notes.append("%s stands at the hips' height, not the floor - no root bone, "
                         "Main takes the hips' travel" % leaf(candidate))
            return None
    elif not labelled:
        return None
    return candidate


def recognize(paths, positions=None, spine_targets=TARGET_SPINE,
              neck_targets=TARGET_NECK):
    """Result(mapping, convention, confidence, missing, refusal, notes, chains).

    paths       -- the source skeleton's joints, long DAG paths
    positions   -- {path: (x, y, z)} world at rest, Y up; optional, used to
                   find an unnamed knee/elbow, the floor and the structural pass
    spine_targets / neck_targets -- OUR spine and neck, bottom up; the source's
                   chains are distributed onto them
    mapping is {our bone: source path}; chains carries the source's ordered
    `spine` and `neck` joints for a caller with other targets. Pure."""
    paths = list(paths)
    positions = dict(positions or {})
    convention = convention_of(paths)
    parents = parent_map(paths)
    info = _labels(paths, parents, convention)
    notes = []
    mapping = _by_names(info, parents, positions, notes, spine_targets, neck_targets)
    confidence = 1.0
    if not _has_core(mapping) and positions:
        structural = _structural(paths, parents, positions, notes,
                                 spine_targets, neck_targets)
        if _has_core(structural):
            # names that DID resolve stay (fingers mostly); the core is the shape's
            for key, value in mapping.items():
                structural.setdefault(key, value)
            mapping, confidence = structural, 0.6
            notes.append("names did not say enough - the parts were found by the "
                         "skeleton's shape")
    chains = {"spine": [], "neck": []}
    if "pelvis" in mapping and "head" in mapping:
        spine, neck = _spine_neck(mapping, info, parents, positions)
        chains = {"spine": spine, "neck": neck}
    missing = [t for t in CORE if t not in mapping]
    refusal = ""
    if missing:
        refusal = "%s: no %s found - not a humanoid this retarget knows" % (
            convention, _word(missing[0]))
        confidence = 0.0
    elif confidence == 1.0:
        named = sum(1 for t in CORE if info[mapping[t]].kind not in (None, "ignore"))
        confidence = round(named / float(len(CORE)), 3)
    return Result(mapping, convention, confidence, missing, refusal, notes, chains)


# the limbs a UE clip always names its way; NOT the head - a first-person UE clip
# (LongSword_Attack_Right_Heavy_1P, 90 joints) carries none, and the first build of
# this guard sent it down the generic road, which refused it (measured 2026-10-02)
UE_LIMBS = ("pelvis", "thigh_l", "calf_l", "foot_l", "thigh_r", "calf_r", "foot_r",
            "upperarm_l", "lowerarm_l", "hand_l", "upperarm_r", "lowerarm_r", "hand_r")


def covers_ue_core(leaf_names):
    """Pure: does a skeleton carry every UE limb bone BY NAME (`pelvis`,
    `thigh_l`, `hand_r` ...)? A UE4 or UE5 clip always does; an Auto-Rig Pro
    export shares `hand_r` and a Daz figure `pelvis` with it and nothing more -
    one shared name made them score as Unreal (measured 2026-10-02)."""
    names = set(leaf_names)
    return all(name in names for name in UE_LIMBS)


def _word(target):
    side = ""
    base = target
    if target.endswith(("_l", "_r")):
        base, side = target[:-2], " (%s)" % ("left" if target.endswith("_l") else "right")
    return WORDS.get(base, base) + side


def _has_core(mapping):
    return all(t in mapping for t in CORE)


def _spine_neck(mapping, info, parents, positions):
    hips, head = mapping["pelvis"], mapping["head"]
    main = [p for p in _main_chain(hips, head, parents) if info[p].kind != "ignore"]
    branch = None
    for side in SIDES:
        clav = mapping.get("clavicle_" + side) or mapping.get("upperarm_" + side)
        if clav and parents.get(clav) in main:
            here = parents.get(clav)
            if branch is None or main.index(here) > main.index(branch):
                branch = here
    necks = [p for p in main if info[p].kind == "neck"]
    if necks:
        first = main.index(necks[0])
        spine, neck = main[:first], main[first:]
    elif branch is not None:
        cut = main.index(branch) + 1
        spine, neck = main[:cut], main[cut:]
    else:
        spine, neck = main, []
    return spine, neck


def _by_names(info, parents, positions, notes, spine_targets, neck_targets):
    mapping = {}
    legs = {}
    for side in SIDES:
        legs[side] = _leg(side, info, parents, positions, notes)
    heads = _of(info, "head")
    head = _shallowest(heads, parents)
    thighs = [legs[s].get("thigh") for s in SIDES]
    hips = None
    if all(thighs) and head:
        meet = lca(thighs + [head], parents)
        named = [p for p in [meet] + ancestors(meet, parents)
                 if p and info[p].kind == "hips"] if meet else []
        hips = named[0] if named else meet
    elif not all(thighs):
        named = _of(info, "hips")
        hips = _shallowest(named, parents)
    if hips is None or head is None:
        if hips:
            mapping["pelvis"] = hips
        return mapping
    mapping["pelvis"] = hips
    mapping["head"] = head
    for side in SIDES:
        for part, path in legs[side].items():
            mapping["%s_%s" % (part, side)] = path
    main = _main_chain(hips, head, parents) + [hips, head]
    for side in SIDES:
        arm, _branch = _arm(side, info, parents, positions, main, notes)
        for part, path in arm.items():
            mapping["%s_%s" % (part, side)] = path
        mapping.update(_fingers(side, arm.get("hand"), info, parents))
    root = _root(hips, info, parents, positions, notes)
    if root:
        mapping["root"] = root
    spine, neck = _spine_neck(mapping, info, parents, positions)
    mapping.update(distribute(spine, spine_targets))
    mapping.update(distribute(neck, neck_targets))
    if len(spine) != len(spine_targets) and spine:
        notes.append("spine: %d source joints onto our %d" % (len(spine), len(spine_targets)))
    if len(neck) != len(neck_targets) and neck:
        notes.append("neck: %d source joints onto our %d" % (len(neck), len(neck_targets)))
    return mapping


# ---------------------------------------------------------------- structural

def _children(parents):
    out = collections.defaultdict(list)
    for child, parent in parents.items():
        if parent:
            out[parent].append(child)
    return out


def _structural(paths, parents, positions, notes, spine_targets, neck_targets):
    """The parts from the shape alone (Y up): the two lowest leaves are the
    feet, the top is the head, their common ancestor the hips, the two leaves
    furthest out sideways above the hips the hands. Fingers are left alone."""
    usable = [p for p in paths if p in positions]
    if len(usable) < 15:
        return {}
    kids = _children(parents)
    leaves = [p for p in usable if not kids.get(p)]
    floor = min(positions[p][1] for p in usable)
    top = max(usable, key=lambda p: positions[p][1])
    stature = positions[top][1] - floor
    if stature <= 1e-9:
        return {}
    head = top
    up_parent = parents.get(top)
    if not kids.get(top) and up_parent and _dist(positions[top], positions[up_parent]) \
            < 0.13 * stature:
        head = up_parent
    low = sorted([p for p in leaves if positions[p][1] - floor < 0.15 * stature],
                 key=lambda p: positions[p][1])
    pair = None
    best = -1.0
    for i, a in enumerate(low):
        for b in low[i + 1:]:
            gap = _dist(positions[a], positions[b])
            if gap > best and lca([a, b], parents) not in (a, b):
                best, pair = gap, (a, b)
    if pair is None:
        return {}
    hips = lca([pair[0], pair[1], head], parents)
    if hips is None:
        return {}
    main = _main_chain(hips, head, parents)
    # the hands: leaves leaving the main chain above the hips, furthest out
    hip_pos = positions[hips]
    arm_leaves = []
    for leaf_path in leaves:
        if leaf_path in pair or is_under(leaf_path, head, parents):
            continue
        branch = next((n for n in ancestors(leaf_path, parents) if n in main), None)
        if branch is None:
            continue
        offset = _sub(positions[leaf_path], positions[branch])
        arm_leaves.append((math.hypot(offset[0], offset[2]), leaf_path, branch))
    arm_leaves.sort(reverse=True)
    if len(arm_leaves) < 2:
        return {}
    first = arm_leaves[0]

    def flat(path):
        offset = _sub(positions[path], hip_pos)
        return (offset[0], 0.0, offset[2])
    second = next((a for a in arm_leaves[1:] if _dot(flat(first[1]), flat(a[1])) < 0), None)
    if second is None:
        return {}
    # left = up x forward; forward from the feet (heel to toe end)
    forward = (0.0, 0.0, 0.0)
    for foot_leaf in pair:
        parent = parents.get(foot_leaf)
        if parent in positions:
            step = _sub(positions[foot_leaf], positions[parent])
            forward = (forward[0] + step[0], 0.0, forward[2] + step[2])
    forward = _norm(forward) or (0.0, 0.0, 1.0)
    left = _cross((0.0, 1.0, 0.0), forward)

    def side_of(path):
        return "l" if _dot(_sub(positions[path], hip_pos), left) > 0 else "r"

    mapping = {"pelvis": hips, "head": head}
    for leg_leaf in pair:
        side = side_of(leg_leaf)
        chain = path_between(hips, leg_leaf, parents) + [leg_leaf]

        def nearest(height, among):
            return min(among, key=lambda p: abs((positions[p][1] - floor) / stature - height))
        thigh = nearest(0.48, chain)
        calf = nearest(0.27, [p for p in chain if depth(p, parents) > depth(thigh, parents)]
                       or chain)
        lower = [p for p in chain if depth(p, parents) > depth(calf, parents)]
        foot = nearest(0.045, lower) if lower else None
        mapping["thigh_" + side] = thigh
        mapping["calf_" + side] = calf
        if foot:
            mapping["foot_" + side] = foot
            toes = [p for p in lower if depth(p, parents) == depth(foot, parents) + 1]
            if toes:
                mapping["ball_" + side] = toes[0]
    for _gap, arm_leaf, branch in (first, second):
        side = side_of(arm_leaf)
        chain = path_between(branch, arm_leaf, parents) + [arm_leaf]
        hand = next((p for p in chain if len(kids.get(p, [])) >= 2), None)
        if hand is None:
            hand = chain[-2] if len(chain) >= 4 else chain[-1]
        before = chain[:chain.index(hand)]
        if len(before) < 2:
            continue
        mapping["hand_" + side] = hand
        mapping["lowerarm_" + side] = before[-1]
        mapping["upperarm_" + side] = before[-2]
        if len(before) >= 3:
            mapping["clavicle_" + side] = before[-3]
    info = dict((p, Info(None, "", None, None)) for p in paths)
    spine, neck = _spine_neck(mapping, info, parents, positions)
    mapping.update(distribute(spine, spine_targets))
    mapping.update(distribute(neck, neck_targets))
    return mapping


# ---------------------------------------------------------------- rest poses

# the bones whose direction says which rest pose a skeleton stands in
REST_PAIRS = (("pelvis", "head"),
              ("upperarm_l", "lowerarm_l"), ("lowerarm_l", "hand_l"),
              ("upperarm_r", "lowerarm_r"), ("lowerarm_r", "hand_r"),
              ("thigh_l", "calf_l"), ("calf_l", "foot_l"),
              ("thigh_r", "calf_r"), ("calf_r", "foot_r"),
              ("clavicle_l", "upperarm_l"), ("clavicle_r", "upperarm_r"))


def body_frame(positions):
    """(lateral, up, forward) unit axes of a skeleton from its own parts:
    up from the pelvis to the head, lateral from the right shoulder to the
    left, forward their cross product. None when the parts are missing."""
    def get(*names):
        for name in names:
            if name in positions:
                return positions[name]
        return None
    pelvis, head = get("pelvis"), get("head", "neck_01")
    left, right = get("upperarm_l", "thigh_l"), get("upperarm_r", "thigh_r")
    if None in (pelvis, head, left, right):
        return None
    up = _norm(_sub(head, pelvis))
    lateral = _sub(left, right)
    if up is None:
        return None
    lateral = _norm(_sub(lateral, tuple(x * _dot(lateral, up) for x in up)))
    if lateral is None:
        return None
    forward = _cross(lateral, up)
    return lateral, up, forward


def _in_frame(vector, frame):
    return tuple(_dot(vector, axis) for axis in frame)


def rest_score(rig_positions, source_positions, pairs=REST_PAIRS):
    """Degrees, summed over the limb bones both skeletons have: how far the
    source's bones point from ours, each read in its own skeleton's body frame
    (so a source facing another way, or lying under a Z-up wrapper, is not
    penalised for it). Lower is a better rest pose for the alignment; None
    when no frame can be read. Pure."""
    ours, theirs = body_frame(rig_positions), body_frame(source_positions)
    if ours is None or theirs is None:
        return None
    total = 0.0
    for first, second in pairs:
        if not all(n in rig_positions and n in source_positions for n in (first, second)):
            continue
        a = _in_frame(_sub(rig_positions[second], rig_positions[first]), ours)
        b = _in_frame(_sub(source_positions[second], source_positions[first]), theirs)
        total += angle(a, b)
    return total


def choose_rest(candidates, rig_positions, prefer=("bindPose", "jointOrient", "firstFrame")):
    """(name, {name: score}): the candidate rest pose whose bone directions
    agree best with the rig's own rest. `candidates` is {name: {our bone:
    (x, y, z)}}. Ties go to `prefer`'s order. Pure."""
    scores = {}
    for name, positions in candidates.items():
        score = rest_score(rig_positions, positions)
        if score is not None:
            scores[name] = score
    if not scores:
        return None, scores
    order = dict((name, i) for i, name in enumerate(prefer))
    best = min(scores, key=lambda n: (round(scores[n], 6), order.get(n, len(order)), n))
    return best, scores


def canonical_parents(mapping, parents):
    """{our bone: the nearest ANCESTOR that is also mapped, as our name}: the
    hierarchy the alignment walks, in our names. Pure."""
    back = dict((src, ours) for ours, src in mapping.items())
    out = {}
    for ours, src in mapping.items():
        node, parent = parents.get(src), None
        while node:
            if node in back:
                parent = back[node]
                break
            node = parents.get(node)
        out[ours] = parent
    return out


HAND_DIRECTION = ("middle_01", "index_01", "ring_01", "pinky_01", "middle_metacarpal",
                  "index_metacarpal", "ring_metacarpal", "pinky_metacarpal", "thumb_01")


def direction_children(parents):
    """{our bone: the child its DIRECTION is read toward}, from a canonical
    hierarchy ({bone: parent bone}, `canonical_parents`). The pelvis and the
    spine point up their own chain (never at a thigh or a clavicle), a hand at
    its middle finger (never the thumb: 30.77 deg of wrist roll, measured
    2026-09-05), anything else at its first child by name. A bone with no
    child is absent: it inherits its parent's alignment. Pure."""
    kids = collections.defaultdict(list)
    for bone, parent in parents.items():
        if parent:
            kids[parent].append(bone)
    out = {}
    for bone, children in kids.items():
        side = bone[-2:] if bone.endswith(("_l", "_r")) else ""
        base = bone[:-2] if side else bone
        if base == "hand":
            prefer = [name + side for name in HAND_DIRECTION]
        elif bone == "pelvis" or base.startswith(("spine", "neck")):
            prefer = sorted(k for k in children if k.startswith(("spine", "neck"))) + ["head"]
        else:
            prefer = []
        choice = next((k for k in prefer if k in children), None)
        out[bone] = choice or sorted(children)[0]
    return out


def scale_ratio(rig_pelvis_height, source_pelvis_height):
    """Our pelvis height over the source's (each above its own floor), 1.0 when
    the source's is not usable. Pure."""
    if source_pelvis_height is None or source_pelvis_height <= 1e-9:
        return 1.0
    return rig_pelvis_height / source_pelvis_height


# ---------------------------------------------------------------- the size, pose-free
# (the fix pass, 2026-10-02). The first build read the size as our pelvis height over
# the source's in whichever rest `choose_rest` picked - and it picks the FIRST FRAME for
# a source whose bind lives in its rotate channels (its jointOrient pose is a straight
# line), so a clip starting in a crouch or a jump read its pelvis 20-60 % low and scaled
# every position drive by the wrong factor.

LEG_SEGMENTS = (("thigh", "calf"), ("calf", "foot"))
STRAIGHT = 0.98        # a leg is straight when hip-to-ankle is 98 % of its two bones
DOWN_DEG = 20.0        # ... standing when it runs within 20 deg of the body's down,
UPRIGHT_DEG = 20.0     # ... the body within 20 deg of the world's up,
ON_FLOOR = 0.25        # ... and the ankles within a quarter of a leg of its floor


def leg_length(positions):
    """The mean over both sides of thigh->calf + calf->foot, from {our bone:
    position}; None without a whole leg. Pose-free: bone lengths do not change
    with the pose. Pure."""
    legs = []
    for side in ("l", "r"):
        names = ["%s_%s" % (bone, side) for bone in ("thigh", "calf", "foot")]
        if all(n in positions for n in names):
            legs.append(_dist(positions[names[0]], positions[names[1]])
                        + _dist(positions[names[1]], positions[names[2]]))
    return sum(legs) / len(legs) if legs else None


def stands(positions, floor=0.0):
    """Pure: does this pose STAND on its floor - both legs straight and running
    down the body (DOWN_DEG of pelvis->head), the body upright (UPRIGHT_DEG of
    world +Y), the ankles near `floor` (ON_FLOOR of a leg)? A crouch, a kneel, a
    straight-line zero pose (a rotate-channel bind with its rotates zeroed), a
    lying pose and a jump with straight legs do not."""
    frame = body_frame(positions)
    legs = leg_length(positions)
    if frame is None or "pelvis" not in positions or not legs:
        return False
    up = frame[1]
    if angle(up, (0.0, 1.0, 0.0)) > UPRIGHT_DEG:
        return False
    down = tuple(-c for c in up)
    seen = 0
    for side in ("l", "r"):
        hip, knee, ankle = (positions.get("%s_%s" % (b, side)) for b in ("thigh", "calf", "foot"))
        if None in (hip, knee, ankle):
            continue
        span = _dist(hip, ankle)
        bones = _dist(hip, knee) + _dist(knee, ankle)
        if bones <= 1e-9 or span < STRAIGHT * bones:
            return False
        if angle(_sub(ankle, hip), down) > DOWN_DEG:
            return False
        if abs(ankle[1] - floor) > ON_FLOOR * legs:
            return False
        seen += 1
    return seen > 0


def standing_height(positions, floor=0.0):
    """The pelvis's height above `floor` (world Y) when the pose `stands` on it,
    else None. Above the FLOOR, not the ankles: a skeleton's pelvis-to-thigh
    offset and its ankle height differ by convention (Mixamo's hips stand 5 cm
    over its thighs, Manny's 2; measured 2026-10-02), and the floor is where the
    feet must land. Pure."""
    if not stands(positions, floor):
        return None
    height = positions["pelvis"][1] - floor
    return height if height > 1e-9 else None


SIZE_ORDER = ("bindPose", "jointOrient", "firstFrame")


def size_ratio(ours, candidates, our_floor=0.0, their_floor=0.0, order=SIZE_ORDER):
    """(ratio, how): our size over the source's. `ours` is {our bone: position}
    at our rest on `our_floor`, `candidates` {rest name: {our bone: position}}
    the source's, whose floor is `their_floor` (its parent's origin).

    The first candidate (in `order`) that STANDS gives our standing height over
    its (the pelvis over the floor: a ratio that puts our feet on the floor when
    the source's are); none standing - a crouched or jumping first frame with no
    bind, a lying clip - the leg lengths (`leg_length`, pose-free: thigh +
    calf). (1.0, "") when neither can be read. Pure."""
    names = list(order) + sorted(set(candidates) - set(order))
    mine = standing_height(ours, our_floor)
    if mine:
        for name in names:
            if name in candidates:
                theirs = standing_height(candidates[name], their_floor)
                if theirs:
                    return mine / theirs, "standing (%s)" % name
    mine = leg_length(ours)
    for name in names:
        if name in candidates:
            theirs = leg_length(candidates[name])
            if mine and theirs:
                return mine / theirs, "legs (%s)" % name
    return 1.0, ""


def scale_pivot(first_root, origin):
    """The point a source is scaled about: under its root's FIRST frame, on its
    parent's floor (`origin`'s height). A floor drop and a kept place are both
    computed from the unscaled first frame, so scaling about any other point
    moved the clip (s - 1) * p0 off it (the review: a CMU clip starting 20 cm out
    landed 25 cm off the cursor). Pure."""
    return (first_root[0], origin[1], first_root[2])


def scaled_track(track, scale):
    """A root track scaled about its first point (`scale_pivot`'s rule): the
    travel the bake will carry, for a layout computed before it. Pure."""
    if not track or scale == 1.0:
        return list(track)
    first = track[0]
    return [tuple(f + scale * (c - f) for c, f in zip(p, first)) for p in track]


# ---------------------------------------------------------------- a root that never moves

STILL = 1e-3           # of the body's size: a root moving less than this stands still
TRAVEL = 0.05          # ... while the hips travel more than this


def static_root(root_track, hips_track, size, still=STILL, travel=TRAVEL):
    """Pure: is a floor-standing root bone a placeholder - its world matrix the
    same on every sampled frame (`root_track`, 16 floats each) while the hips
    travel on the ground (`hips_track`, positions) more than `travel` of `size`?
    MotionBuilder's Reference and Character Creator's BoneRoot usually are: the
    travel lives in the hips, and driving Main from the root lost it. An in-place
    clip (the hips only sway) keeps its root."""
    if not root_track or not hips_track or not size:
        return False
    first = root_track[0]
    for m in root_track[1:]:
        for i, (a, b) in enumerate(zip(m, first)):
            tol = still * size if i in (12, 13, 14) else 1e-5
            if abs(a - b) > tol:
                return False
    h0 = hips_track[0]
    ground = max(math.hypot(p[0] - h0[0], p[2] - h0[2]) for p in hips_track)
    return ground > travel * size


def sample_frames(first, last, most=120):
    """Whole frames from `first` to `last`, at most `most` of them, both ends
    kept. Pure."""
    if first is None or last is None:
        return []
    first, last = int(math.floor(first)), int(math.ceil(last))
    count = last - first + 1
    if count <= most:
        return list(range(first, last + 1))
    return sorted(set(int(round(first + (last - first) * i / float(most - 1)))
                      for i in range(most)))


def drop_static_root(mapping, sample, frames, size, notes):
    """`mapping` without its root when `static_root` says it is a placeholder
    (a note says so: Main then takes the hips' horizontal travel, as it does for
    a source with no root at all); else `mapping` itself. `sample(path, frame)`
    answers a world matrix. Pure but for `sample`."""
    if "root" not in mapping or "pelvis" not in mapping or not frames:
        return mapping
    root, hips = mapping["root"], mapping["pelvis"]
    roots = [list(sample(root, f)) for f in frames]
    hips_track = [tuple(sample(hips, f))[12:15] for f in frames]
    if not static_root(roots, hips_track, size):
        return mapping
    notes.append("%s never moves while the hips travel - no root bone, Main takes the "
                 "hips' travel" % leaf(root))
    return dict((k, v) for k, v in mapping.items() if k != "root")
