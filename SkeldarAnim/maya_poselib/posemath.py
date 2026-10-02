"""The Pose Library's bone transfer (2026-10-02): which bone plays which, how their rests differ,
where every target bone stands for a card's pose, mirror and blend - pure, on skeletons as data.

The animator: «если анимация относится к ригу то мы должны сохранять анимацию не контроллов а
костей, таким образом мы сможем потом переносить эту анимацию на скелеты и на риги ... если мы
сохранили анимацию костей рук и потом переносим ее на кости рук другого скелета то скрипт должен
определить что это похожая иерархия костей и перенести анимацию подобно тому как у нас работает
сейчас с элементами ретаргета».

A card holds the BONES of one character, and a target skeleton is read the same way:
`{leaf: {"parent", "canonical", "rest", "world", ["drive"]}}`, matrices as 16-float lists in
Maya's row-vector convention (`world = local · parent`). `canonical` is our UE5 name from
`maya_skeletonmap.recognize` (None for a bone it does not map); `rest` the skinCluster's bind;
`world` the bone as it stands; `drive` (rig sources only) the bone as the rig's drive chain
holds it, with the roll AdvancedSkeleton moves into the twist joints put back (trap 126).

- `pairs` answers which source bone plays each target bone - by leaf name when both carry the
  UE limbs, else through the canonical names, the spine and neck chain onto chain;
- `alignments` the minimal rotation taking each target bone's rest direction onto its
  partner's (identity for a twin) - `skeletonimport._alignments`' rule, trap 171 included;
- `targets` the world matrix of EVERY target bone: each member takes its partner's rotation
  RELATIVE TO ITS NEAREST PAIRED ANCESTOR, carried through the two rests, so a hand pose lands
  on the arm as it stands and a full pose on a character standing elsewhere keeps its place and
  facing; lengths are the target's, only the pelvis takes the pose's offset from the root;
- `mirror` reflects a pose across the source's sagittal plane, `blend` mixes two matrices.

The solvers (`skelsolve`, `rigsolve`) turn the targets into channel values; nothing here
touches a scene. The retarget's pure pieces are reused, never copied
(`maya_skeletonmap.covers_ue_core`, `distribute`, `canonical_parents`, `direction_children`);
the UE4 spine map is `skeletonimport.pair_bones`', the blend `fkik.blended`'s - both modules
import `maya.cmds`, so their few lines are restated here.

The stdlib, maya.api.OpenMaya and maya_skeletonmap only (a subprocess test pins it).
Spec: docs/superpowers/specs/2026-10-02-pose-library-design.md
"""

import math
import re

import maya.api.OpenMaya as om

import maya_skeletonmap as skelmap

# never members on their own, and paired only by leaf (on the UE road)
HELPERS = ("ik_", "weapon_", "camera_", "interaction", "center_of_mass")
# a UE4 target under a UE5 source: the same bones, fewer of them (maya_retarget's map,
# skeletonimport.pair_bones') - {target: source}
UE4_SPINE = {"spine_01": "spine_02", "spine_02": "spine_04", "spine_03": "spine_05"}
# the card's text, in this order
REGIONS = ("Head", "Spine", "Pelvis", "Arm L", "Hand L", "Arm R", "Hand R", "Leg L", "Leg R")
SCALE_TOLERANCE = 0.02     # two bodies within 2 % of each other's size are one size
SHORTEST_HEIGHT = 1.0      # cm: a pelvis lower than this over its root says nothing of size
# world Y where a skeleton with no root of its own stands at its bind: its top joint's parent is
# the world (or a group at the origin), so its floor is that origin's height - the retarget's
# `their_floor` for such a source (maya_skeletonmap.size_ratio)
FLOOR = 0.0
EPS = 1e-9

_ARM = ("clavicle", "upperarm", "lowerarm")
_HAND = ("hand",) + skelmap.FINGERS
_LEG = ("thigh", "calf", "foot", "ball")


# ---------------------------------------------------------------- matrices

def matrix(values):
    """An om.MMatrix from 16 floats (row-major, how a card stores it) or from a matrix."""
    return om.MMatrix(values)


def flat(m):
    """16 floats, row-major: how a matrix crosses a module boundary or lands in pose.json."""
    return [float(v) for v in matrix(m)]


def rigid(m):
    """The matrix's rotation and translation, scale and shear removed."""
    tm = om.MTransformationMatrix(matrix(m))
    out = om.MTransformationMatrix()
    out.setRotation(tm.rotation(asQuaternion=True))
    out.setTranslation(tm.translation(om.MSpace.kWorld), om.MSpace.kWorld)
    return out.asMatrix()


def rotation(m):
    """The matrix's rotation alone (no translation, no scale)."""
    return _quaternion(m).asMatrix()


def position(m):
    """The matrix's translation row as an om.MVector."""
    m = matrix(m)
    return om.MVector(m[12], m[13], m[14])


def angle(a, b):
    """Degrees between two matrices' rotations (positions and scale ignored).

    2·atan2(|v|, |w|) of the delta quaternion rather than 2·acos(|w|): acos loses up to
    ~2e-6 deg to rounding at an exact match, which a 1e-9 gate would read as a miss."""
    q = _quaternion(a).inverse() * _quaternion(b)
    vector = math.sqrt(q.x * q.x + q.y * q.y + q.z * q.z)
    return math.degrees(2.0 * math.atan2(vector, abs(q.w)))


def direction_angle(a, b):
    """Degrees between two directions (0 when either is zero); atan2 of the cross product over
    the dot, exact near 0 and near 180."""
    a, b = om.MVector(a), om.MVector(b)
    if a.length() < EPS or b.length() < EPS:
        return 0.0
    return math.degrees(math.atan2((a ^ b).length(), a * b))


def blend(a, b, alpha):
    """Between two matrices: the translation lerped, the rotation slerped the short way
    (`fkik.blended`, the rig's own blend); 0 is `a`, 1 is `b`, exactly."""
    a, b = matrix(a), matrix(b)
    if alpha <= 0.0:
        return om.MMatrix(a)
    if alpha >= 1.0:
        return om.MMatrix(b)
    qa, qb = _quaternion(a), _quaternion(b)
    if qa.x * qb.x + qa.y * qb.y + qa.z * qb.z + qa.w * qb.w < 0:
        qb = om.MQuaternion(-qb.x, -qb.y, -qb.z, -qb.w)
    tm = om.MTransformationMatrix(om.MQuaternion.slerp(qa, qb, alpha).asMatrix())
    tm.setTranslation(position(a) * (1.0 - alpha) + position(b) * alpha, om.MSpace.kTransform)
    return tm.asMatrix()


def _quaternion(m):
    return om.MTransformationMatrix(matrix(m)).rotation(asQuaternion=True)


def _placed(turn, point):
    """A rotation matrix standing at `point` (an MVector or an MPoint)."""
    values = flat(turn)
    values[12:15] = [point.x, point.y, point.z]
    return om.MMatrix(values)


# ---------------------------------------------------------------- names

def is_helper(leaf):
    """An export helper (`ik_*`, `weapon_*`, `camera_*`, `interaction`, `center_of_mass`):
    never a member on its own, paired only by leaf on the UE road. A namespace is ignored."""
    return leaf.split(":")[-1].startswith(HELPERS)


def is_twist(leaf):
    """A twist bone (`upperarm_twist_01_l` ...): it rides with its limb and is never a member,
    nor a direction child, on its own."""
    return "_twist_" in leaf


_SWAP = {"l": "r", "r": "l", "L": "R", "R": "L", "left": "right", "right": "left",
         "Left": "Right", "Right": "Left", "LEFT": "RIGHT", "RIGHT": "LEFT"}
# the side tokens a game studio meets (maya_skeletonmap's conventions), tried in order
_SIDE_RULES = (
    re.compile(r"(?<=[_.])([lLrR])$"),                 # hand_l, hand.L, DEF-hand.L, Shoulder_L
    re.compile(r"(?<=_)([lLrR])(?=_)"),                # upperarm_L_, CC_Base_L_Upperarm
    re.compile(r"(?<=\s)([LR])(?=\s)"),                # Bip001 L Hand
    re.compile(r"(Left|Right)(?![a-z])"),              # LeftHand, Left_Arm, Character1_LeftHand
    re.compile(r"(?<![A-Za-z])(left|right)(?![a-z])"),  # left_hand, hand_left
    re.compile(r"(?<![A-Za-z])(LEFT|RIGHT)(?![A-Z])"),  # LEFT_HAND
    re.compile(r"^([lrLR])(?=[A-Z])"),                 # lShldrBend (Daz), LHipJoint (CMU)
)


def opposite(name):
    """The other side's spelling of a bone name - `hand_l`↔`hand_r`, `LeftHand`↔`RightHand`,
    `Left_Arm`↔`Right_Arm`, `hand.L`↔`hand.R`, `DEF-hand.L`, `upperarm_L_`↔`upperarm_R_`,
    `Bip001 L Hand`↔`Bip001 R Hand`, `lShldrBend`↔`rShldrBend` - or None for a centre bone. The
    first side token found wins; a namespace is kept."""
    if not name:
        return None
    head, sep, leaf = name.rpartition(":")
    for rule in _SIDE_RULES:
        found = rule.search(leaf)
        if found:
            side = found.group(1)
            return head + sep + leaf[:found.start(1)] + _SWAP[side] + leaf[found.end(1):]
    return None


def _region(name):
    base, side = name, ""
    if name.endswith(("_l", "_r")):
        base, side = name[:-2], " " + name[-1].upper()
    if base == "head" or base.startswith("neck_"):
        return "Head"
    if base.startswith("spine_"):
        return "Spine"
    if base == "pelvis":
        return "Pelvis"
    if not side:
        return None
    word = base.split("_")[0]
    if word in _ARM:
        return "Arm" + side
    if word in _HAND:
        return "Hand" + side
    if word in _LEG:
        return "Leg" + side
    return None


def regions(names):
    """The body regions a set of canonical UE5 names touches, in `REGIONS` order: `Head` =
    neck_*, head; `Spine` = spine_*; `Pelvis` = pelvis; `Arm <S>` = clavicle, upperarm,
    lowerarm and their twists; `Hand <S>` = the hand and every finger and metacarpal;
    `Leg <S>` = thigh, calf, foot, ball and their twists. Helpers and the root touch none."""
    found = set(filter(None, (_region(n) for n in names or ())))
    return [r for r in REGIONS if r in found]


# ---------------------------------------------------------------- hierarchy

def _depth(bones, leaf):
    """How many of the bone's ancestors are in `bones` (a cycle stops the walk)."""
    depth, node, seen = 0, bones[leaf].get("parent"), set()
    while node in bones and node not in seen:
        seen.add(node)
        depth += 1
        node = bones[node].get("parent")
    return depth


def _ordered(bones):
    """Parents first: by depth, ties by name."""
    return sorted(bones, key=lambda b: (_depth(bones, b), b))


def root_of(bones):
    """The skeleton's root: the shallowest bone - its parent None or not in the dict - ties
    sorted by name. None for no bones."""
    if not bones:
        return None
    return _ordered(bones)[0]


def ue_named(bones):
    """Does the skeleton carry every UE limb bone by NAME (`covers_ue_core` of its leaves)?"""
    return skelmap.covers_ue_core(bones)


def _find(bones, name):
    """The leaf playing our bone `name`: the one whose canonical name it is, else the leaf
    spelled so; None when neither."""
    for leaf in sorted(bones):
        if bones[leaf].get("canonical") == name:
            return leaf
    return name if name in bones else None


def _canonical_index(bones, helpers=False):
    """{canonical name: leaf} of the bones that carry one (helpers left out unless asked)."""
    out = {}
    for leaf in sorted(bones):
        name = bones[leaf].get("canonical")
        if not name or name in out:
            continue
        if not helpers and (is_helper(leaf) or is_helper(name)):
            continue
        out[name] = leaf
    return out


# ---------------------------------------------------------------- pairing

def pairs(source, target):
    """{target leaf: source leaf}: which source bone plays each target bone.

    Both skeletons `ue_named` -> by leaf: every target leaf the source carries (twist bones and
    helpers included); a UE4 target under a UE5 source (`spine_05` in the source, neither
    `spine_04` nor `spine_05` in the target) takes `{"spine_01": "spine_02", "spine_02":
    "spine_04", "spine_03": "spine_05"}`. Otherwise by canonical name: a target bone whose
    canonical name a source bone carries, helpers never; the spine (`spine_*`) and the neck
    (`neck_*`) paired chain onto chain with `distribute(source_chain, target_chain)`, each chain
    that side's canonical spine/neck bones bottom-up by canonical name. The two roots
    (`root_of`) are always paired, last, so the target root's partner is the source root."""
    if ue_named(source) and ue_named(target):
        out = _by_leaf(source, target)
    else:
        out = _by_canonical(source, target)
    target_root, source_root = root_of(target), root_of(source)
    if target_root is not None and source_root is not None:
        out[target_root] = source_root
    return out


def _by_leaf(source, target):
    ue4 = "spine_05" in source and "spine_05" not in target and "spine_04" not in target
    out = {}
    for leaf in target:
        wanted = UE4_SPINE.get(leaf, leaf) if ue4 else leaf
        if wanted in source:
            out[leaf] = wanted
    return out


def _by_canonical(source, target):
    s_index, t_index = _canonical_index(source), _canonical_index(target)
    out = {}
    for name, leaf in t_index.items():
        if not name.startswith(("spine_", "neck_")) and name in s_index:
            out[leaf] = s_index[name]
    for prefix in ("spine_", "neck_"):
        out.update(skelmap.distribute(_chain(s_index, prefix), _chain(t_index, prefix)))
    return out


def _chain(index, prefix):
    return [index[name] for name in sorted(index) if name.startswith(prefix)]


def _own_root(pairs, source, target_root):
    """Does the source have a root of its own? Not when the bone partnering the target root
    also plays another target bone - Mixamo's Hips is both its root and its pelvis. A source
    with no root of its own takes its GROUND frame (`_ground`) as its root's."""
    partner = pairs.get(target_root)
    if partner is None or partner not in source:
        return False
    return all(s != partner for t, s in pairs.items() if t != target_root)


def _paired_ancestor(target, leaf, pairs, source, target_root):
    """The bone's nearest ancestor that has a partner (the target root always counts)."""
    node, seen = target[leaf].get("parent"), set()
    while node in target and node not in seen:
        seen.add(node)
        if node == target_root or (node in pairs and pairs[node] in source):
            return node
        node = target[node].get("parent")
    return None


# ---------------------------------------------------------------- a source with no root

def _heading(turn):
    """The yaw about world +Y of a world-space turn: its twist about +Y in the swing-twist split
    `turn = swing · yaw`, the swing's axis lying in the floor (the quaternion's vector part
    projected onto Y). Identity for a half turn about a floor axis (the bone upside down), which
    has no heading."""
    q = _quaternion(turn)
    size = math.hypot(q.y, q.w)
    if size < EPS:
        return om.MMatrix()
    return om.MQuaternion(0.0, q.y / size, 0.0, q.w / size).asMatrix()


def _ground(rest, pose):
    """(pose frame, rest frame) standing in for the root of a skeleton that has none, read off
    its top bone (Mixamo's Hips). Both stand on the rest floor (`FLOOR`) under the bone - its x
    and z; the rest frame unturned (world axes: a bind stands facing the way the target's root
    rest does), the pose frame turned by the bone's HEADING, the yaw about world +Y of its
    rest-to-pose turn `rot(rest)⁻¹ · rot(pose)`.

    So a card made on such a skeleton standing elsewhere, turned elsewhere, transfers and
    mirrors as it would from a twin with a root at that ground frame: the character stays
    where it stands and faces. The cost, stated: the hips' own yaw against the body's facing
    cannot be told apart from the facing on a skeleton with no root - it is read as the facing."""
    rest, pose = matrix(rest), matrix(pose)
    turn = rotation(rest).inverse() * rotation(pose)
    at_rest, at_pose = position(rest), position(pose)
    return (_placed(_heading(turn), om.MVector(at_pose.x, FLOOR, at_pose.z)),
            _placed(om.MMatrix(), om.MVector(at_rest.x, FLOOR, at_rest.z)))


def _root_frames(bones, root, pose, rootless):
    """(pose frame, rest frame) of a skeleton's root for `pose` (the root bone's world or
    drive): the root bone's own, else - a skeleton with no root of its own - its ground frame
    (`_ground`). The one place `targets`, `mirror` and `scale_between` read a root from."""
    rest = matrix(bones[root]["rest"])
    if rootless:
        return _ground(rest, pose)
    return matrix(pose), rest


# ---------------------------------------------------------------- rest alignment

def alignments(pairs, source, target):
    """{target leaf: om.MMatrix} for every paired target bone: the minimal rotation
    `om.MQuaternion(t_dir, s_dir)` taking the target's rest direction onto the source's.

    The direction child is `direction_children(canonical_parents(...))` of the TARGET's paired
    bones in our names (leaves on the UE road, canonical names on the other), mapped back to
    leaves; twist bones and helpers are never direction children. The target direction is the
    child's offset in the bone's CURRENT frame re-expressed in its rest frame (trap 171: `local
    = (pos(child_now) - pos(bone_now)) · rigid(bone_now)⁻¹`, `t_dir = local · rigid(bone_rest)`
    as a vector); the source direction the partner child's rest position minus the partner's.
    A bone with no paired direction child inherits its nearest paired ancestor's; the root's is
    identity. For a twin every one is ≈ identity."""
    ue = ue_named(source) and ue_named(target)
    target_root = root_of(target)
    usable = [t for t in _ordered(target) if t in pairs and t != target_root
              and pairs[t] in source and not is_helper(t) and not is_twist(t)]
    mapping, names = {}, {}
    for leaf in usable:
        name = leaf if ue else (target[leaf].get("canonical") or leaf)
        if name not in mapping:
            mapping[name], names[leaf] = leaf, name
    parents = dict((leaf, bone.get("parent")) for leaf, bone in target.items())
    children = skelmap.direction_children(skelmap.canonical_parents(mapping, parents))
    out = {}
    for leaf in _ordered(target):
        if leaf not in pairs:
            continue
        turn = None
        if leaf != target_root and leaf in names:
            child = mapping.get(children.get(names[leaf]))
            if child is not None:
                turn = _alignment(source, target, pairs, leaf, child)
        if turn is None:
            above = None if leaf == target_root else \
                _paired_ancestor(target, leaf, pairs, source, target_root)
            turn = om.MMatrix(out[above]) if above in out else om.MMatrix()
        out[leaf] = turn
    return out


def _alignment(source, target, pairs, leaf, child):
    """The minimal rotation for one bone, or None when a direction is zero."""
    bone_now, child_now = matrix(target[leaf]["world"]), matrix(target[child]["world"])
    local = (position(child_now) - position(bone_now)) * rigid(bone_now).inverse()
    t_dir = local * rigid(target[leaf]["rest"])
    s_dir = position(source[pairs[child]]["rest"]) - position(source[pairs[leaf]]["rest"])
    if t_dir.length() < EPS or s_dir.length() < EPS:
        return None
    return om.MQuaternion(t_dir.normal(), s_dir.normal()).asMatrix()


# ---------------------------------------------------------------- size

def scale_between(source, target, pairs):
    """How much bigger the target's body is: the pelvis's rest height above the root's rest
    along world Y, target over source. 1.0 when either pelvis is missing or a height is below
    1 cm; a ratio within 2 % of 1 is 1.0. A skeleton whose root IS its pelvis (Mixamo's Hips)
    measures it above its ground frame's rest (`_ground`: the rest floor, `FLOOR`)."""
    target_root, target_pelvis = root_of(target), _find(target, "pelvis")
    source_root = pairs.get(target_root) or root_of(source)
    source_pelvis = pairs.get(target_pelvis) if target_pelvis else None
    if target_pelvis is None or source_pelvis not in source or source_root not in source:
        return 1.0
    t_height = _height(target, target_pelvis, target_root)
    s_height = _height(source, source_pelvis, source_root)
    if t_height < SHORTEST_HEIGHT or s_height < SHORTEST_HEIGHT:
        return 1.0
    ratio = t_height / s_height
    return 1.0 if abs(ratio - 1.0) <= SCALE_TOLERANCE else ratio


def _height(bones, pelvis, root):
    """The pelvis's rest height over its root's rest frame (the ground's, for a skeleton whose
    root is its pelvis)."""
    rest = bones[root]["rest"]
    floor = position(_root_frames(bones, root, rest, root == pelvis)[1]).y
    return position(bones[pelvis]["rest"]).y - floor


# ---------------------------------------------------------------- the transfer

def targets(source, target, pairs, members, use_drive=False, scale=1.0, pelvis="pelvis"):
    """{target leaf: om.MMatrix}: where EVERY target bone stands for the source's pose
    (unchanged bones at their current world).

    `P[s]` is `source[s]["drive"]` when `use_drive` and the bone has one, else its `world`.
    Parents first, a target bone `t` that is a member's partner (`pairs[t] in members`), with
    `tp` its nearest paired ancestor, `s = pairs[t]`, `sp = pairs[tp]`, takes the rotation

        O_t  = rigid(T_rest[t]) · A[t] · rigid(S_rest[s])⁻¹
        O_tp = rigid(T_rest[tp]) · A[tp] · rigid(S_rest[sp])⁻¹
        R_t  = rotation(O_t · rotation(P[s]) · rotation(P[sp])⁻¹ · O_tp⁻¹ · rotation(W[tp]))

    `W[tp]` being `tp`'s RESULT (its target when solved, else where it followed to). Every other
    bone follows its parent rigidly, `W[x] = (T_now[x] · T_now[parent]⁻¹) · W[parent]`, so a
    non-member between two members, and every descendant, moves with what moved. Positions:
    every bone keeps its own local translation, `local_translation(t) · W[parent]`. The root
    keeps its current world. The PELVIS (the target bone playing `pelvis`, paired with a
    member) takes the pose's offset from the root, in the source root's frame, into the target
    root's, scaled:

        d_local = (pos(P[s_pelvis]) - pos(P[s_root])) · rotation(P[s_root])⁻¹
        d_t     = d_local · rotation(O_root)⁻¹ · scale
        pos     = pos(T_now[t_root]) + d_t · rotation(T_now[t_root])

    A source with no root of its own (its root also plays another target bone, Mixamo's Hips)
    reads `P[s_root]` and `S_rest[s_root]` off its GROUND frame (`_ground`): the rest floor
    under the hips, turned by their heading. Read literally the rule would hold the pelvis
    relative to ITSELF - its offset zero, on the target's root, its turn lost - and the world
    origin in its place would carry the card's world placement and facing into the target."""
    members = set(members or ())
    align = alignments(pairs, source, target)
    target_root = root_of(target)
    own_root = _own_root(pairs, source, target_root)
    target_pelvis = _find(target, pelvis)
    now = dict((leaf, matrix(bone["world"])) for leaf, bone in target.items())

    def pose(s):
        bone = source[s]
        return matrix(bone["drive"] if use_drive and bone.get("drive") else bone["world"])

    def frame(leaf):
        """(P, S_rest) of a target bone's partner - for the target root, the source root's
        frames (`_root_frames`: the ground's for a source with no root of its own)."""
        if leaf is None:
            return om.MMatrix(), om.MMatrix()
        s = pairs.get(leaf)
        if s not in source:                 # an unpaired target root: nothing to stand on
            return om.MMatrix(), om.MMatrix()
        if leaf == target_root:
            return _root_frames(source, s, pose(s), not own_root)
        return pose(s), matrix(source[s]["rest"])

    def offset(leaf):
        """O: the target's rest against its partner's, through the alignment."""
        if leaf is None:
            return om.MMatrix()
        rest = frame(leaf)[1]
        return rigid(target[leaf]["rest"]) * align.get(leaf, om.MMatrix()) * rigid(rest).inverse()

    out = {}
    for leaf in _ordered(target):
        parent = target[leaf].get("parent")
        if leaf == target_root or parent not in target:
            out[leaf] = om.MMatrix(now[leaf])
            continue
        local = now[leaf] * now[parent].inverse()
        s = pairs.get(leaf)
        if s not in members or s not in source:
            out[leaf] = local * out[parent]
            continue
        above = _paired_ancestor(target, leaf, pairs, source, target_root)
        above_world = out[above] if above is not None else om.MMatrix()
        turn = rotation(offset(leaf) * rotation(pose(s)) * rotation(frame(above)[0]).inverse()
                        * offset(above).inverse() * rotation(above_world))
        if leaf == target_pelvis:
            root_pose = frame(target_root)[0]
            d_local = (position(pose(s)) - position(root_pose)) * rotation(root_pose).inverse()
            d_t = d_local * rotation(offset(target_root)).inverse() * scale
            point = position(now[target_root]) + d_t * rotation(now[target_root])
        else:
            t = position(local)
            point = om.MPoint(t.x, t.y, t.z) * out[parent]
        out[leaf] = _placed(turn, point)
    return out


# ---------------------------------------------------------------- mirror

def mirror(source, members):
    """(new_source, new_members): the pose reflected left ↔ right, in the source root's frame.

    `l` = normalised (the left upper arm's, else the left thigh's, rest position − its
    opposite's) in root-local coordinates (root-local +X when neither pair is there), `F = I −
    2·l·lᵀ`. For every bone, `r = rot(S_rest[x]) · rot(S_rest[root])⁻¹`, `p = rot(P[x]) ·
    rot(P[root])⁻¹`, `D = r⁻¹ · p` (the root-space delta); a bone with an opposite present takes
    `p' = r[s] · F · D[ō] · F`, a centre bone `p' = r[s] · F · D[s] · F`; back to world `P'[s] =
    p' · rot(P[root])` at `P[s]`'s position. The pelvis's position reflects too: `d = (pos(P[pel])
    − pos(P[root])) · rot(P[root])⁻¹`, `d' = d · F`. Both `world` and `drive` are mirrored (a
    drive reads its opposite's world where the opposite has none). Members swap to their
    opposites; centre members stay. The opposite comes from the canonical name's side, else the
    leaf's side token (`opposite`). A skeleton whose root IS its pelvis (Mixamo's Hips) has no
    root frame of its own: it mirrors in its ground frame (`_ground`, as `targets` reads it) -
    the floor under the hips, turned by their heading - so it keeps its place and facing and
    swaps left and right as a twin with a root there would; the hips mirror as a centre bone.
    (The world's frame instead would reflect the card's world place and facing: a body facing
    +X would come back facing -X.)"""
    root = root_of(source)
    pelvis = _find(source, "pelvis")
    rootless = pelvis == root
    sides = _opposites(source)
    rest_root = rotation(_root_frames(source, root, source[root]["rest"], rootless)[1])
    flip = _reflection(source, rest_root)
    rest = dict((x, rotation(b["rest"]) * rest_root.inverse()) for x, b in source.items())
    out = dict((leaf, dict(bone)) for leaf, bone in source.items())
    for key in ("world", "drive"):
        if not any(key in bone for bone in source.values()):
            continue
        pose = dict((x, matrix(b.get(key) or b["world"])) for x, b in source.items())
        root_frame = _root_frames(source, root, pose[root], rootless)[0]
        root_turn, root_place = rotation(root_frame), position(root_frame)
        delta = dict((x, rest[x].inverse() * (rotation(pose[x]) * root_turn.inverse()))
                     for x in source)
        for leaf, bone in source.items():
            if key not in bone or (leaf == root and not rootless):
                continue
            reflected = flip * delta[sides.get(leaf, leaf)] * flip
            turn = rotation(rest[leaf] * reflected * root_turn)
            point = position(pose[leaf])
            if leaf == pelvis:
                d = (point - root_place) * root_turn.inverse()
                point = root_place + (d * flip) * root_turn
            out[leaf][key] = flat(_placed(turn, point))
    return out, [sides.get(m, m) for m in members or ()]


def _opposites(bones):
    """{leaf: its opposite's leaf} for the bones whose other side is in the skeleton."""
    index = _canonical_index(bones, helpers=True)
    out = {}
    for leaf, bone in bones.items():
        other = None
        name = bone.get("canonical")
        if name and opposite(name) in index:
            other = index[opposite(name)]
        if other is None and opposite(leaf) in bones:
            other = opposite(leaf)
        if other is not None and other != leaf:
            out[leaf] = other
    return out


def _reflection(bones, root_turn):
    """F = I − 2·l·lᵀ: the reflection across the skeleton's sagittal plane, in its root's rest
    frame (`root_turn`), `l` its rest right-to-left direction (the upper arms, else the
    thighs)."""
    side = om.MVector(1.0, 0.0, 0.0)
    for name in ("upperarm_l", "thigh_l"):
        left, right = _find(bones, name), _find(bones, name[:-1] + "r")
        if left is None or right is None or left == right:
            continue
        across = (position(bones[left]["rest"]) - position(bones[right]["rest"])) * \
            root_turn.inverse()
        if across.length() > EPS:
            side = across.normal()
            break
    axis = (side.x, side.y, side.z)
    values = [1.0 if row == col else 0.0 for row in range(4) for col in range(4)]
    for row in range(3):
        for col in range(3):
            values[row * 4 + col] -= 2.0 * axis[row] * axis[col]
    return om.MMatrix(values)
