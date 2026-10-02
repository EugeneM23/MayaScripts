"""Retarget onto the PlayerMale AdvancedSkeleton rig: ROTATIONS, from three kinds of skeleton.

The sibling of `maya_asretarget.py` (which drives the UE5 Manny's AS rig) for the rig
built on 2026-09-05 over the PlayerMale game skeleton -- a copy with a different target
and one different rule, both the animator's (2026-09-05): «сделаем копию скрипта
ретаргета на разные скелеты: unreal engine, mixamo и собственный скелет ... не учитывать
изменения позиций в костях, только вращения».

    import sys; sys.path.append(r"C:/!!!Work/MayaScripts/SkeldarAnim")
    import maya_pmretarget
    print(maya_pmretarget.report())      # read-only: what would be driven, from what
    print(maya_pmretarget.connect())     # build it, from the SELECTED source skeleton
    print(maya_pmretarget.bake())        # the vendor's Bake over the clip's range, then Disconnect
    print(maya_pmretarget.disconnect())  # Disconnect alone -- the rig keeps NO animation

`bake()` is AdvancedSkeleton's own MoCap Matcher > Bake and Disconnect MoCap Skeleton,
pressed in that order with the playback range set to the clip's keys for the length of the
bake.  Every constraint built here registers its nodeState on
`MoCapConstraints.disableConstraints` and every helper is parented under
`MoCapConstraints`, the contract the vendor's Bake and Disconnect rely on (measured
2026-09-04).  A Disconnect WITHOUT the Bake leaves the rig frozen in the pose of the frame
it stood on and nothing else -- which is what «сработал только на 1 кадре» looks like
(2026-09-06, the Mixamo clip: connected, disconnected, never baked).

What is driven, and how:

- **FK controls take the source bone's ROTATION only**, through an orientConstraint whose
  offset is our rest frame against the source's rest frame, the two rest poses aligned
  bone by bone where the skeletons differ (our bone then points where the source's bone
  points, at every frame, with the roll our own axis work established).  Never position:
  the animator's rule, and a foreign skeleton's positions would hand the rig its
  proportions.
- **The IK end controls and the poles follow OUR OWN FK joints** (`FKXWrist_R`,
  `FKXAnkle_R`, `FKXToes_R`; a pole is placed from its whole FK limb so the IK plane is the
  FK plane, see POLE_CHAIN), so the IK pose is the FK pose in our proportions and the
  animator can bake and then switch either way.  A rotation-only retarget has no source
  positions to give an IK control; the vendor's own connect puts the source's hand there,
  which lands wrong by the proportion difference.
- **Main and RootX_M carry the travel, SCALED**: the source is 10x our size (UE and Mixamo
  clips stand ~170 cm, this character 17.5 units), so translations are multiplied by
  `our pelvis height / the source's pelvis height` at rest.  Main follows the source's
  root bone (rotation, scaled translation); with no root bone (Mixamo) it takes the hips'
  horizontal travel.  RootX_M follows the pelvis (rotation, scaled position).
- Nothing else moves: no twist joints, no neck in-between on this rig, no metacarpals.

Three source schemas, detected from the bones the source has:

- `OWN`   -- the PlayerMale skeleton itself, animated (an imported clip).  Same names, so
             the rest is OUR bones' rest and no alignment is needed.
- `UE5`   -- Unreal's Manny (`pelvis`, `spine_05`, metacarpals).  Rest from the shipped
             `SkeldarAnim/assets/manny_skeleton_template.json` (the bind pose's world
             matrices), aligned bone by bone.  Our four spine joints take spine_01/02/03
             and Chest takes spine_05; the neck takes neck_01, the head the head.
- `UE4`   -- the UE4 mannequin (`spine_03` is the chest, no `spine_05`).  Rest from
             `SkeldarAnim/assets/ue4_mannequin_template.json`, extracted 2026-09-05 from
             the shipped `UE4_Mannequin.fbx`.
- `MIXAMO`-- Mixamo (`Hips`, `Spine2`, side as a prefix), rest = the pose with every
             rotate at 0 (its bind lives in jointOrient; measured an exact T-pose).

Design record: docs/superpowers/specs/2026-09-05-pmretarget-design.md
"""

import collections
import json
import math
import os

import maya.api.OpenMaya as om
import maya.cmds as cmds

import maya_rigs
import maya_skeletonmap as skelmap

# ------------------------------------------------------------------ our rig

# AdvancedSkeleton control base -> PlayerMale game bone (without the side prefix).
OUR_ROWS = [
    ("Spine1", "Spine1"), ("Spine2", "Spine2"), ("Spine3", "Spine3"), ("Chest", "Spine4"),
    ("Neck", "Neck"), ("Head", "Head"), ("Jaw", "Jaw"), ("Eye", "Eye"),
    ("Scapula", "Shoulder"), ("Shoulder", "Arm"), ("Elbow", "ForeArm"), ("Wrist", "Hand"),
    ("IndexFinger1", "Finger1"), ("IndexFinger2", "Finger2"), ("IndexFinger3", "Finger3"),
    ("MiddleFinger1", "Middle1"), ("MiddleFinger2", "Middle2"), ("MiddleFinger3", "Middle3"),
    ("RingFinger1", "Ring1"), ("RingFinger2", "Ring2"), ("RingFinger3", "Ring3"),
    ("PinkyFinger1", "Pinky1"), ("PinkyFinger2", "Pinky2"), ("PinkyFinger3", "Pinky3"),
    ("ThumbFinger1", "Thumb1"), ("ThumbFinger2", "Thumb2"), ("ThumbFinger3", "Thumb3"),
    ("Hip", "Thigh"), ("Knee", "Knee"), ("Ankle", "Ankle"), ("Toes", "Toes"),
]
OUR_SIDES = [("_M", ""), ("_L", "Left_"), ("_R", "Right_")]      # the side is a PREFIX
OUR_ROOT, OUR_PELVIS = "Root", "Hip"
# The IK end controls and the poles follow OUR OWN FK joints, whatever the source.
IK_FOLLOW = [("IKArm", "FKXWrist", True), ("IKLeg", "FKXAnkle", True), ("IKToes", "FKXToes", False)]
# A pole is placed from the whole FK limb so that the IK plane IS the FK plane: a base on
# the upper-lower line at the mid joint's share, nudged a little off the line AWAY from the
# pole's rest side in the MID joint's own frame, aimed at the mid joint, the pole a limb's
# length out along that aim.  Bent, the aim is the line-to-knee direction (the FK plane,
# whatever axis the bend was about -- a UE take bends our knee off its hinge); straight,
# the nudge alone decides and it turns with the FK knee, so the roll survives.  Measured on
# the way here: a pole riding the upper bone at a fixed standoff was 0.11 deg off on our
# own take and 5 deg on a UE one, one riding the knee's frame the same, and the vendor's
# nudge in WORLD z went 19.7 deg wrong on a straight leg under a yaw.
POLE_FOLLOW = [("PoleArm", "FKXElbow"), ("PoleLeg", "FKXKnee")]
POLE_CHAIN = {"PoleArm": ("FKXShoulder", "FKXElbow", "FKXWrist"), "PoleLeg": ("FKXHip", "FKXKnee", "FKXAnkle")}
NUDGE = 0.002    # of the limb's length: small, so a bent knee's own offset from the line decides the
                 # plane (a 2% nudge left 0.3 deg of it out of plane) and the nudge only speaks on a
                 # straight limb, where it carries the FK knee's roll
# The bone an IK control / pole stands on, for the proportion note and the pole standoff.
IK_BONE = {"IKArm": "Hand", "IKLeg": "Ankle", "IKToes": "Toes", "PoleArm": "Arm", "PoleLeg": "Thigh"}

# ------------------------------------------------------------ source schemas

UE_SIDES = [("_M", ""), ("_L", "_l"), ("_R", "_r")]
UE5_ROWS = [
    ("Spine1", "spine_01"), ("Spine2", "spine_02"), ("Spine3", "spine_03"), ("Chest", "spine_05"),
    ("Neck", "neck_01"), ("Head", "head"),
    ("Scapula", "clavicle"), ("Shoulder", "upperarm"), ("Elbow", "lowerarm"), ("Wrist", "hand"),
    ("IndexFinger1", "index_01"), ("IndexFinger2", "index_02"), ("IndexFinger3", "index_03"),
    ("MiddleFinger1", "middle_01"), ("MiddleFinger2", "middle_02"), ("MiddleFinger3", "middle_03"),
    ("RingFinger1", "ring_01"), ("RingFinger2", "ring_02"), ("RingFinger3", "ring_03"),
    ("PinkyFinger1", "pinky_01"), ("PinkyFinger2", "pinky_02"), ("PinkyFinger3", "pinky_03"),
    ("ThumbFinger1", "thumb_01"), ("ThumbFinger2", "thumb_02"), ("ThumbFinger3", "thumb_03"),
    ("Hip", "thigh"), ("Knee", "calf"), ("Ankle", "foot"), ("Toes", "ball"),
]
# The UE4 mannequin's spine is three joints and spine_03 carries the clavicles: our Chest.
UE4_ROWS = [(a, b) for a, b in UE5_ROWS if a not in ("Spine3", "Chest")] + [("Chest", "spine_03")]
MIXAMO_SIDES = [("_M", ""), ("_L", "Left"), ("_R", "Right")]
MIXAMO_ROWS = [
    ("Spine1", "Spine"), ("Spine2", "Spine1"), ("Chest", "Spine2"),
    ("Neck", "Neck"), ("Head", "Head"), ("Eye", "Eye"),
    ("Scapula", "Shoulder"), ("Shoulder", "Arm"), ("Elbow", "ForeArm"), ("Wrist", "Hand"),
    ("IndexFinger1", "HandIndex1"), ("IndexFinger2", "HandIndex2"), ("IndexFinger3", "HandIndex3"),
    ("MiddleFinger1", "HandMiddle1"), ("MiddleFinger2", "HandMiddle2"), ("MiddleFinger3", "HandMiddle3"),
    ("RingFinger1", "HandRing1"), ("RingFinger2", "HandRing2"), ("RingFinger3", "HandRing3"),
    ("PinkyFinger1", "HandPinky1"), ("PinkyFinger2", "HandPinky2"), ("PinkyFinger3", "HandPinky3"),
    ("ThumbFinger1", "HandThumb1"), ("ThumbFinger2", "HandThumb2"), ("ThumbFinger3", "HandThumb3"),
    ("Hip", "UpLeg"), ("Knee", "Leg"), ("Ankle", "Foot"), ("Toes", "ToeBase"),
]

# rest      -- where the source's REST pose comes from: "ours" (the source IS this
#              skeleton, so its rest is our bones' rest, by name), "jointOrient" (the bind
#              lives in jointOrient; the rest is the pose with every rotate at 0), or
#              "template" (a shipped JSON of bind-pose world matrices, `template`).
# align     -- align the rest poses bone by bone (a foreign skeleton); the twin needs none.
# required  -- bones the source must have to be this schema; absent -- bones it must NOT
#              have (UE4 is UE5 without spine_05).  Checked in SCHEMAS order.
Schema = collections.namedtuple(
    "Schema", "name rows sides side_before pelvis root_bone rest template align required absent")

OWN = Schema("own", OUR_ROWS, OUR_SIDES, True, OUR_PELVIS, OUR_ROOT, "ours", None, False,
             ("Hip", "Spine4", "Right_Arm", "Left_Hand", "Right_Toes"), ())
UE5 = Schema("ue5", UE5_ROWS, UE_SIDES, False, "pelvis", "root", "template",
             "manny_skeleton_template.json", True,
             ("pelvis", "spine_05", "upperarm_l", "hand_r", "ball_l"), ())
UE4 = Schema("ue4", UE4_ROWS, UE_SIDES, False, "pelvis", "root", "template",
             "ue4_mannequin_template.json", True,
             ("pelvis", "spine_03", "upperarm_l", "hand_r", "ball_l"), ("spine_05",))
MIXAMO = Schema("mixamo", MIXAMO_ROWS, MIXAMO_SIDES, True, "Hips", None, "jointOrient", None, True,
                ("Hips", "Spine2", "LeftArm", "RightHand", "LeftToeBase"), ())
SCHEMAS = (OWN, UE5, UE4, MIXAMO)

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

OFFSET_TOL = 1e-5
DEFAULTS = (("tx", 0.0), ("ty", 0.0), ("tz", 0.0), ("rx", 0.0), ("ry", 0.0), ("rz", 0.0))

HOLDER = "MoCapConstraints"      # AdvancedSkeleton's own node name (leaf; one per rig)
SWITCH = "disableConstraints"    # ... and its own attribute
SCALE_GROUP = "pmrtScale"


def _n(rig, leaf_name):
    """The scene name of one of the rig's nodes: `ns:leaf`, or the plain name
    for a rig in the root namespace. Every rig node this module touches goes
    through here -- controls, FKX joints, ControlSet, the holder, the helpers."""
    return maya_rigs.node(rig, leaf_name)


def _rig(rig):
    """The rig to act on: the one given, else the selection's, else the sole
    rig. Returns (rig, refusal)."""
    if rig is not None:
        return rig, ""
    return maya_rigs.current_rig()


def holder_of(rig):
    return _n(rig, HOLDER)
FOLLOW_PREFIX = "pmrtFollow_"
SCALED_PREFIX = "pmrtScaled_"
OFFSET_PREFIX = "pmrtOffset_"
POLE_BASE_PREFIX = "pmrtPoleBase_"
POLE_FRAME_PREFIX = "pmrtPoleFrame_"
POLE_NUDGE_PREFIX = "pmrtPoleNudge_"
POLE_PREFIX = "pmrtPole_"

# kind: fk (rotation from a source bone) | main (root motion, scaled) | ground (hips'
# horizontal travel, scaled; no root bone) | pelvis (rotation + scaled position) |
# ik / iktoes / pole (our own FKX joint; `source` is that joint's name)
Drive = collections.namedtuple("Drive", "control source kind")


# ---------------------------------------------------------------- pure policy

def leaf(path):
    """The short name without its namespace: `|clip:Root|clip:Hip` -> `Hip`."""
    return path.split("|")[-1].split(":")[-1]


def bone_name(base, side, schema):
    """Pure: the source's name for a bone; a prefix side goes first."""
    return (side + base) if schema.side_before else (base + side)


def our_bone(control):
    """Pure: the PlayerMale bone a control stands on, or None."""
    if control == "Main":
        return OUR_ROOT
    if control == "RootX_M":
        return OUR_PELVIS
    rows = dict(OUR_ROWS)
    sides = dict(OUR_SIDES)
    for suffix in ("_M", "_L", "_R"):
        if not control.endswith(suffix):
            continue
        base = control[:-len(suffix)]
        if base.startswith("FK") and base[2:] in rows:
            return sides[suffix] + rows[base[2:]]
        if base in IK_BONE:
            return sides[suffix] + IK_BONE[base]
    return None


def candidates(schema):
    """Every control name the schema's tables can drive, in build order."""
    out = ["Main", "RootX_M"]
    for base, _ in schema.rows:
        for side, _ in schema.sides:
            out.append("FK" + base + side)
    for base, _, _ in IK_FOLLOW:
        for side in ("_L", "_R"):
            out.append(base + side)
    for base, _ in POLE_FOLLOW:
        for side in ("_L", "_R"):
            out.append(base + side)
    return out


def drive_plan(controls, bones, schema):
    """Pure: what to constrain to what.

    controls -- control names that exist in this rig
    bones    -- leaf names that exist in the source skeleton
    Returns (drives, missing); missing = [(control, bone)] rows skipped because the source
    lacks the bone.  Rows a schema does not have (UE has no jaw, no eyes; Mixamo has no
    jaw) are not "missing", they are simply not driven.
    """
    controls, bones = set(controls), set(bones)
    drives, missing = [], []

    def add(control, bone, kind):
        if control not in controls or bone is None:
            return
        if bone not in bones:
            missing.append((control, bone))
            return
        drives.append(Drive(control, bone, kind))

    if schema.root_bone:
        add("Main", schema.root_bone, "main")
    else:
        add("Main", schema.pelvis, "ground")
    add("RootX_M", schema.pelvis, "pelvis")
    for as_base, src_base in schema.rows:
        for as_side, src_side in schema.sides:
            add("FK" + as_base + as_side, bone_name(src_base, src_side, schema), "fk")
    for as_base, fkx, full in IK_FOLLOW:
        for side in ("_L", "_R"):
            if as_base + side in controls:
                drives.append(Drive(as_base + side, fkx + side, "ik" if full else "iktoes"))
    for as_base, fkx in POLE_FOLLOW:
        for side in ("_L", "_R"):
            if as_base + side in controls:
                drives.append(Drive(as_base + side, fkx + side, "pole"))
    return drives, missing


def detect_schema(bones, schemas=SCHEMAS):
    """Pure: which schema this source is, by the bones it has -- the first whose
    required bones are all present and whose absent bones are all absent.  A skeleton
    that is none of them is refused rather than guessed at."""
    bones = set(bones)
    for schema in schemas:
        if all(b in bones for b in schema.required) and not any(b in bones for b in schema.absent):
            return schema
    return None


def top_joint(path, joint_paths):
    """Pure: the shallowest joint on `path`, or None."""
    joint_paths = set(joint_paths)
    parts = [p for p in path.split("|") if p]
    for i in range(1, len(parts) + 1):
        candidate = "|" + "|".join(parts[:i])
        if candidate in joint_paths:
            return candidate
    return None


def source_root_of(selection, joint_paths, rig_paths_):
    """Pure: which skeleton the animator means.  Returns (root, refusal)."""
    if not selection:
        return "", "nothing selected - select any joint of the imported skeleton"
    roots = []
    for path in selection:
        root = top_joint(path, joint_paths)
        if root and root not in roots:
            roots.append(root)
    if not roots:
        return "", "the selection holds no joint - select a bone of the imported skeleton"
    if len(roots) > 1:
        return "", ("two skeletons selected (%s) - select bones of one only"
                    % ", ".join(leaf(r) for r in roots))
    root = roots[0]
    for path in rig_paths_:
        if path == root or path.startswith(root + "|"):
            return "", ("%s is the rig's own skeleton - select the imported clip's "
                        "skeleton instead" % root)
    return root, ""


def rigid(matrix):
    """Pure: the same transform with its scale and shear thrown away."""
    tm = om.MTransformationMatrix(om.MMatrix(matrix))
    out = om.MTransformationMatrix()
    out.setRotation(tm.rotation(asQuaternion=True))
    out.setTranslation(tm.translation(om.MSpace.kWorld), om.MSpace.kWorld)
    return list(out.asMatrix())


def offset_local(control_world, bone_world):
    """Pure: the rest offset as a LOCAL matrix, C_rest * B_rest^-1 (row vectors)."""
    return list(om.MMatrix(rigid(control_world)) * om.MMatrix(rigid(bone_world)).inverse())


def is_identity(matrix, tol=1e-6):
    return all(abs(a - b) <= tol for a, b in zip(list(om.MMatrix(matrix)), list(om.MMatrix())))


def rotation_only(matrix):
    """Pure: the same matrix with its translation row zeroed."""
    m = list(matrix)
    m[12] = m[13] = m[14] = 0.0
    return m


def position(matrix):
    return (matrix[12], matrix[13], matrix[14])


def direction(rest, first, second):
    """Pure: the unit vector from one rest bone to another, or None."""
    if first not in rest or second not in rest:
        return None
    a, b = position(rest[first]), position(rest[second])
    v = om.MVector(b[0] - a[0], b[1] - a[1], b[2] - a[2])
    if v.length() < 1e-6:
        return None
    return v.normal()


def rotation_angle(matrix):
    q = om.MTransformationMatrix(om.MMatrix(matrix)).rotation(asQuaternion=True)
    return math.degrees(2 * math.acos(max(-1.0, min(1.0, abs(q.w)))))


def align_rotation(ours, theirs):
    """Pure: the minimal rotation taking our rest bone direction onto the source's."""
    if ours is None or theirs is None:
        return list(om.MMatrix())
    return list(om.MQuaternion(ours, theirs).asMatrix())


def depth_of(leaf_name, parents):
    depth, node = 0, parents.get(leaf_name)
    while node:
        depth += 1
        node = parents.get(node)
    return depth


def descends(child, ancestor, parents):
    steps, node = 1, parents.get(child)
    while node:
        if node == ancestor:
            return steps
        steps += 1
        node = parents.get(node)
    return 0


# A hand's nearest mapped descendant is the THUMB, the one finger that does not continue
# the hand (a measured 30.77 deg of wrist roll on the Manny rig); a hand points along the
# middle finger.
DIRECTION_CHILD = {"Right_Hand": "Right_Middle1", "Left_Hand": "Left_Middle1"}


def alignments(triples, rig_rest, src_rest, rig_parents, src_parents):
    """Pure: {control: the rest-alignment rotation for its bone}.

    A bone's direction needs a child BOTH skeletons map, so the head, the toes, the jaw
    and the finger tips inherit their parent's alignment.  Root down, so a parent's
    answer is ready when its children ask.
    """
    ordered = sorted(triples, key=lambda t: depth_of(t[1], rig_parents))
    preferred = dict((t[1], t[2]) for t in triples)
    out, by_bone = {}, {}
    for control, our, src in ordered:
        best = None
        want = DIRECTION_CHILD.get(our)
        if want is not None and want in preferred:
            best = (0, want, preferred[want])
        for other, other_our, other_src in triples:
            if other == control or best is not None and best[0] == 0:
                continue
            ours = descends(other_our, our, rig_parents)
            theirs = descends(other_src, src, src_parents)
            if ours and theirs and (best is None or ours + theirs < best[0]):
                best = (ours + theirs, other_our, other_src)
        rotation = None
        if best is not None:
            rotation = align_rotation(direction(rig_rest, our, best[1]),
                                      direction(src_rest, src, best[2]))
        if rotation is None:
            node = rig_parents.get(our)
            while node and node not in by_bone:
                node = rig_parents.get(node)
            rotation = by_bone.get(node, list(om.MMatrix()))
        out[control] = rotation
        by_bone[our] = rotation
    return out


def reference_rotation(control_rest, align):
    """Pure: our control's rest frame turned by the alignment (a WORLD rotation, so it
    post-multiplies), rotation only."""
    return rotation_only(list(om.MMatrix(rigid(control_rest)) * om.MMatrix(align)))


def euler_offset(matrix, rotate_order):
    """Pure: a rotation matrix as the euler triple a constraint's `offset` takes, in the
    constrained node's rotate order (an orientConstraint holds W = O * W_source)."""
    tm = om.MTransformationMatrix(om.MMatrix(matrix))
    tm.reorderRotation(rotate_order + 1)
    e = tm.rotation(asQuaternion=False)
    return (math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))


def parent_offsets(matrix, rotate_order):
    """Pure: a rigid rest offset as a parentConstraint's two target offsets (measured
    2026-09-05 over all six rotate orders, 4.6e-14)."""
    m = list(matrix)
    return (m[12], m[13], m[14]), euler_offset(rotation_only(matrix), rotate_order)


def scale_factor(rig_rest, src_rest, schema):
    """Pure: our pelvis height over the source's, both above their own root.

    Rotations are scale-free; the travel is not.  A UE or Mixamo clip stands ~170 cm and
    this character 17.5 units, so Main's and RootX_M's translations are multiplied by
    this.  With no root bone the source's pelvis height is taken from the ground.
    """
    if OUR_PELVIS not in rig_rest or schema.pelvis not in src_rest:
        return 1.0
    ours = position(rig_rest[OUR_PELVIS])[1] - (position(rig_rest[OUR_ROOT])[1] if OUR_ROOT in rig_rest else 0.0)
    base = position(src_rest[schema.root_bone])[1] if schema.root_bone in src_rest else 0.0
    theirs = position(src_rest[schema.pelvis])[1] - base
    if abs(theirs) < 1e-6:
        return 1.0
    return ours / theirs


LIMB_SPANS = [("arm", "Shoulder", "Elbow", "Wrist"), ("leg", "Hip", "Knee", "Ankle")]


def limb_ratios(rig_rest, src_rest, schema, side="_L"):
    """Pure: {limb: (rig length / source length) / scale} through the schema's map --
    the proportion difference that remains once the overall size is taken out."""
    s = scale_factor(rig_rest, src_rest, schema)
    ours = dict(OUR_SIDES)[side]
    theirs = dict(schema.sides)[side]
    rows, our_rows = dict(schema.rows), dict(OUR_ROWS)
    out = {}
    for limb, first, middle, last in LIMB_SPANS:
        rig_names = [ours + our_rows[b] for b in (first, middle, last)]
        src_names = [bone_name(rows[b], theirs, schema) if b in rows else None for b in (first, middle, last)]
        if None in src_names or not all(n in rig_rest for n in rig_names) or not all(n in src_rest for n in src_names):
            continue

        def span(rest, names):
            total = 0.0
            for a, b in zip(names, names[1:]):
                pa, pb = position(rest[a]), position(rest[b])
                total += math.sqrt(sum((x - y) ** 2 for x, y in zip(pa, pb)))
            return total
        source = span(src_rest, src_names) * s
        if source > 1e-6:
            out[limb] = span(rig_rest, rig_names) / source
    return out


def proportion_note(ratios, tol=0.02):
    """What a proportion difference means here: nothing is scaled and nothing lands on
    the source's positions -- FK copies the angles, IK follows our own FK."""
    off = dict((limb, r) for limb, r in ratios.items() if abs(r - 1.0) > tol)
    if not off:
        return ""
    return (", ".join("the rig's %s is %+.1f%% of the source's (size taken out)" % (limb, (r - 1.0) * 100.0)
                      for limb, r in sorted(off.items()))
            + " - rotations are copied, so hands and feet land where OUR limbs put them")


# ------------------------------------------------------------- scene wrappers

def source_bones(root):
    """{leaf name without namespace: long path} for the source subtree."""
    paths = [root] + (cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True) or [])
    return dict((leaf(p), p) for p in paths)


def parents_of(bones):
    """{leaf: parent leaf} inside one skeleton, from the DAG paths themselves."""
    out = {}
    for name, path in bones.items():
        parts = [leaf("|" + p) for p in path.split("|") if p]
        out[name] = parts[-2] if len(parts) > 1 else None
    return out


def _local_rest(joint):
    """The joint's own LOCAL matrix with rotate at 0 (bind in jointOrient)."""
    def euler(values):
        return om.MEulerRotation([math.radians(v) for v in values], 0).asMatrix()
    m = euler(cmds.getAttr(joint + ".rotateAxis")[0]) * euler(cmds.getAttr(joint + ".jointOrient")[0])
    scale = om.MMatrix()
    for i, v in enumerate(cmds.getAttr(joint + ".scale")[0]):
        scale.setElement(i, i, v)
    m = scale * m
    for i, v in enumerate(cmds.getAttr(joint + ".translate")[0]):
        m.setElement(3, i, v)
    return m


def template_rest(filename, assets=None):
    """{bone name: bind-pose world matrix} from a shipped skeleton template."""
    path = os.path.join(assets or ASSETS, filename)
    with open(path) as fh:
        data = json.load(fh)
    return dict((j["name"], list(j["world_matrix"])) for j in data["joints"])


def rest_matrices(bones, schema, rig_rest=None):
    """{leaf: rest world matrix} for the source skeleton.

    "ours"        -- the source is this very skeleton: its rest is our bones' rest by name
                     (the imported copy stands in the clip's pose, not in the bind pose).
    "jointOrient" -- the pose with every rotate at 0, walked down the hierarchy (Mixamo).
    "template"    -- the shipped bind pose (UE5 Manny, UE4 mannequin); a source bone the
                     template does not know is left out and reported as missing.
    """
    if schema.rest == "given":
        return dict(schema.rest_given)
    if schema.rest == "ours":
        return dict((name, list(rig_rest[name])) for name in bones if name in (rig_rest or {}))
    if schema.rest == "template":
        template = template_rest(schema.template)
        return dict((name, template[name]) for name in bones if name in template)
    parents = parents_of(bones)
    out = {}
    for name in sorted(bones, key=lambda n: depth_of(n, parents)):
        parent = parents.get(name)
        if parent in out:
            base = om.MMatrix(out[parent])
        else:
            above = cmds.listRelatives(bones[name], parent=True, fullPath=True)
            base = om.MMatrix(cmds.getAttr(above[0] + ".worldMatrix[0]")) if above else om.MMatrix()
        out[name] = list(_local_rest(bones[name]) * base)
    return out


# ------------------------------------------------- any other convention (2026-10-02)
#
# A source none of SCHEMAS knows (a Biped, Rigify, a CC or Daz character, a CMU BVH,
# Unity, VRM ...) is read by maya_skeletonmap and re-keyed into UE names, so it runs
# through the UE5 rows above as if it were Manny - rest aligned, rotations only, the
# travel scaled as for every source here. A copy of the sibling module's idea, not of
# its code: this module still takes nothing of the Manny rig's (a test pins that).

MIXAMO_CONVENTIONS = ("mixamo", "motionbuilder_hik")
GENERIC_SPINE = ("spine_01", "spine_02", "spine_03", "spine_05")     # UE5_ROWS' spine
GENERIC_NECK = ("neck_01",)


class GenericSchema(Schema):
    """A Schema read by maya_skeletonmap; carries `bones`, `rest_given`,
    `parents`, `convention`, `rest_choice` and `notes` beside the tuple."""


def ue_names_of_ours():
    """Pure: {our PlayerMale bone: the UE bone the same AS control drives}."""
    ue = dict(UE5_ROWS)
    out = {OUR_PELVIS: "pelvis", OUR_ROOT: "root"}
    for base, ours in OUR_ROWS:
        if base not in ue:
            continue
        for (side, our_side), (_s, ue_side) in zip(OUR_SIDES, UE_SIDES):
            out[our_side + ours] = ue[base] + ue_side
    return out


def _joint_paths(root):
    return [root] + (cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True) or [])


def _zero_rest(paths):
    parents = skelmap.parent_map(paths)
    out = {}
    for path in sorted(paths, key=lambda p: (p.count("|"), p)):
        parent = parents.get(path)
        if parent in out:
            base = om.MMatrix(out[parent])
        else:
            above = cmds.listRelatives(path, parent=True, fullPath=True)
            base = om.MMatrix(cmds.getAttr(above[0] + ".worldMatrix[0]")) if above else om.MMatrix()
        out[path] = list(_local_rest(path) * base)
    return out


def _rest_candidates(paths):
    out = {"jointOrient": _zero_rest(paths)}
    if cmds.keyframe(paths, query=True, keyframeCount=True) or 0:
        first = cmds.findKeyframe(paths, which="first")
        out["firstFrame"] = dict((p, cmds.getAttr(p + ".worldMatrix[0]", time=first)) for p in paths)
    return out


def generic_schema(source_root, rig_rest):
    """(GenericSchema, refusal) for a source no row of SCHEMAS knows."""
    paths = _joint_paths(source_root)
    live = dict((p, tuple(cmds.xform(p, query=True, worldSpace=True, translation=True))) for p in paths)
    result = skelmap.recognize(paths, live, spine_targets=GENERIC_SPINE, neck_targets=GENERIC_NECK)
    if result.refusal:
        return None, "%s: %s" % (leaf(source_root), result.refusal)
    wanted = set(ue for base, ue in UE5_ROWS)
    mapping = dict((k, v) for k, v in result.mapping.items()
                   if k in ("pelvis", "root") or k[:-2] in wanted or k in wanted)
    rig_pos = dict((ue, position(rig_rest[ours])) for ours, ue in ue_names_of_ours().items()
                   if ours in rig_rest)
    candidates = _rest_candidates(paths)
    choice, scores = skelmap.choose_rest(
        dict((name, dict((o, position(m[s])) for o, s in mapping.items() if s in m))
             for name, m in candidates.items()), rig_pos)
    rest = candidates[choice or "jointOrient"]
    named = set(mapping)
    rows = [(a, u) for a, u in UE5_ROWS if u in named or u + "_l" in named or u + "_r" in named]
    schema = GenericSchema("generic:" + result.convention, rows, UE_SIDES, False, "pelvis",
                           "root" if "root" in mapping else None, "given", None, True, (), ())
    schema.bones = mapping
    schema.rest_given = dict((o, list(rest[s])) for o, s in mapping.items())
    schema.parents = skelmap.canonical_parents(mapping, skelmap.parent_map(paths))
    schema.convention, schema.rest_choice = result.convention, choice
    schema.notes = ["source read as %s (%d bones mapped, confidence %.2f); rest pose: %s"
                    % (result.convention, len(mapping), result.confidence, choice)] + list(result.notes)
    del scores
    return schema, ""


def rig_paths(rig=None):
    """Long paths of every joint that belongs to the rig: its own deformation joints
    under its group plus the game skeleton it drives (`maya_rigs`)."""
    rig, _ = _rig(rig)
    return maya_rigs.rig_paths(rig) if rig else []


def rig_skeleton_root(paths_or_rig=None):
    """The game skeleton's root. Takes a Rig; the old `rig_paths()` list is still
    accepted and answered the old way (the shallowest path outside the rigs' own
    groups) for the verify scripts that pass one."""
    if isinstance(paths_or_rig, maya_rigs.Rig):
        return paths_or_rig.skeleton_root
    if paths_or_rig is None:
        rig, _ = _rig(None)
        return rig.skeleton_root if rig else ""
    groups = set(maya_rigs.top_of(r.group) for r in maya_rigs.rigs())
    outside = [p for p in paths_or_rig if not any(maya_rigs.under(p, g) for g in groups)]
    return maya_rigs.shallowest(outside)


def _set_local(node, matrix):
    tm = om.MTransformationMatrix(om.MMatrix(matrix))
    tm.reorderRotation(cmds.getAttr(node + ".rotateOrder") + 1)
    e = tm.rotation(asQuaternion=False)
    t = tm.translation(om.MSpace.kTransform)
    cmds.setAttr(node + ".translate", t.x, t.y, t.z)
    cmds.setAttr(node + ".rotate", math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))


def _holder(rig):
    """AdvancedSkeleton's own holder node, created the way its connect does -- in the
    rig's namespace, so two connected rigs each have their own."""
    holder = holder_of(rig)
    if not cmds.objExists(holder):
        cmds.createNode("transform", name=holder, skipSelect=True)
        for attr in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"):
            cmds.setAttr(holder + "." + attr, lock=True)
    if not cmds.attributeQuery(SWITCH, node=holder, exists=True):
        cmds.addAttr(holder, longName=SWITCH, attributeType="bool", keyable=True)
    return holder


def _register(constraints, holder):
    """The contract: the vendor's Bake walks these, its Disconnect deletes them."""
    for c in constraints:
        cmds.connectAttr(holder + "." + SWITCH, c + ".nodeState", force=True)


SOURCE_ATTR = "pmrtSourceRoot"     # on the holder: where the clip came from, for bake()


def _remember_source(root, holder):
    if not cmds.attributeQuery(SOURCE_ATTR, node=holder, exists=True):
        cmds.addAttr(holder, longName=SOURCE_ATTR, dataType="string")
    cmds.setAttr(holder + "." + SOURCE_ATTR, root, type="string")


def source_key_range(rig=None):
    """(first, last) key of the connected source's bones, or None."""
    root = connected_source(rig)
    if root is None:
        return None
    paths = list(source_bones(root).values())
    if not (cmds.keyframe(paths, query=True, keyframeCount=True) or 0):
        return None
    return cmds.findKeyframe(paths, which="first"), cmds.findKeyframe(paths, which="last")


def _scale_group(factor, rig):
    """A group under the holder scaled by the size ratio; whatever sits under it at the
    source's world position stands at OUR scale.  Dies with the holder.  In the rig's
    namespace: a plain `pmrtScale` would find the OTHER rig's on the second connect."""
    group = _n(rig, SCALE_GROUP)
    if not cmds.objExists(group):
        grp = cmds.createNode("transform", name=group, parent=holder_of(rig), skipSelect=True)
        cmds.setAttr(grp + ".scale", factor, factor, factor)
    return group


def _scaled_follower(source_path, name, factor, offset, rig):
    """A node standing at `factor` times the source bone's world position, plus a WORLD offset.

    Three transforms and one plain connection, no DG node: `pmrtFollow_` is point-constrained
    to the bone (world position, unscaled); `pmrtScaled_` sits under the scaled group with its
    translate CONNECTED to the follower's, so its world position is the follower's times the
    group's scale; `pmrtOffset_` under it carries the rest offset, divided by the scale so
    it comes out in world units.  The offset lives HERE and not on the control's
    pointConstraint because a pointConstraint's `offset` is in the constrained node's PARENT
    space -- RootX_M's parent follows Main, so a yaw of Main turned the offset with it
    (measured: 0.115 off after a 25 deg root turn).  All three die with the holder.
    """
    follower = cmds.createNode("transform", name=_n(rig, FOLLOW_PREFIX + name), parent=holder_of(rig),
                               skipSelect=True)
    con = cmds.pointConstraint(source_path, follower)[0]
    scaled = cmds.createNode("transform", name=_n(rig, SCALED_PREFIX + name), parent=_scale_group(factor, rig),
                             skipSelect=True)
    cmds.connectAttr(follower + ".translate", scaled + ".translate")
    shifted = cmds.createNode("transform", name=_n(rig, OFFSET_PREFIX + name), parent=scaled, skipSelect=True)
    cmds.setAttr(shifted + ".translate", *[o / factor for o in offset])
    return shifted, [con]


def pole_joints(control):
    """Pure: the FKX upper, mid and lower joint of a pole control's limb."""
    base, side = control[:-2], control[-2:]
    return tuple(j + side for j in POLE_CHAIN[base])


def _pole_rig(control, upper, mid, lower, rig):
    """Four transforms and three constraints under the holder that put a pole in the FK plane.

    `pmrtPoleBase_`  -- on the upper-lower line at the mid joint's share (point constraint to
                        both, each weighted by the OTHER bone's length);
    `pmrtPoleFrame_` -- under it, orient-constrained to the mid joint;
    `pmrtPoleNudge_` -- under that, NUDGE of the limb off the line, opposite the side the pole
                        rests on (in the mid joint's rest frame, so it turns with the knee),
                        aimed at the mid joint;
    `pmrtPole_`      -- a limb's length out along the aim.
    Read at the rig's build pose; every number is measured, none assumed.
    """
    upper, mid, lower = (_n(rig, j) for j in (upper, mid, lower))
    a, b, c = (om.MVector(cmds.xform(j, q=True, ws=True, t=True)) for j in (upper, mid, lower))
    d_upper, d_lower = (a - b).length(), (b - c).length()
    length = d_upper + d_lower
    on_line = (a * d_lower + c * d_upper) / length
    side = om.MVector(cmds.xform(_n(rig, control), q=True, ws=True, t=True)) - on_line
    if side.length() < 1e-6:
        side = b - on_line
    if side.length() < 1e-6:
        raise RuntimeError("%s rests on the limb's line and the limb is straight: no pole side" % control)
    mid_rot = om.MTransformationMatrix(om.MMatrix(cmds.getAttr(mid + ".worldMatrix[0]"))).rotation(asQuaternion=True).asMatrix()
    local = (side.normal() * -NUDGE * length) * mid_rot.inverse()        # row vectors: local = world * R^-1
    base = cmds.createNode("transform", name=_n(rig, POLE_BASE_PREFIX + control), parent=holder_of(rig),
                           skipSelect=True)
    con = cmds.pointConstraint(upper, lower, base)[0]
    w = cmds.pointConstraint(con, query=True, weightAliasList=True)
    cmds.setAttr("%s.%s" % (con, w[0]), d_lower)
    cmds.setAttr("%s.%s" % (con, w[1]), d_upper)
    frame = cmds.createNode("transform", name=_n(rig, POLE_FRAME_PREFIX + control), parent=base, skipSelect=True)
    made = [con, cmds.orientConstraint(mid, frame)[0]]
    nudge = cmds.createNode("transform", name=_n(rig, POLE_NUDGE_PREFIX + control), parent=frame, skipSelect=True)
    cmds.setAttr(nudge + ".translate", local.x, local.y, local.z)
    made.append(cmds.aimConstraint(mid, nudge, aimVector=(1, 0, 0), upVector=(0, 1, 0),
                                   worldUpType="vector", worldUpVector=(0, 1, 0))[0])
    pole = cmds.createNode("transform", name=_n(rig, POLE_PREFIX + control), parent=nudge, skipSelect=True)
    cmds.setAttr(pole + ".translateX", length)
    return pole, made


TIME_CURVES = ("animCurveTL", "animCurveTA", "animCurveTT", "animCurveTU")


def reset_build_pose(rig=None):
    """The controls back to the build pose: the previous take's keys deleted,
    translate/rotate zeroed where the channel is free. Returns (curves deleted,
    controls zeroed).

    What AdvancedSkeleton's Go To BuildPose does for the channels this module
    checks (`posed_controls`, `DEFAULTS`), in cmds -- so the bridge's IMPORT
    can replace one take with the next without the vendor's button.  A copy of
    the sibling module's, deliberately (this module imports nothing from it).
    Time curves only: a driven key (animCurveUA/UU) is part of the rig.
    """
    rig, _ = _rig(rig)
    controls = (cmds.sets(rig.control_set, query=True) or []) if rig else []
    curves = set()
    for control in controls:
        for curve in cmds.listConnections(control, type="animCurve", source=True,
                                          destination=False) or []:
            if cmds.objectType(curve) in TIME_CURVES:
                curves.add(curve)
    if curves:
        cmds.delete(list(curves))
    zeroed = 0
    for control in controls:
        touched = False
        for attr, default in DEFAULTS:
            plug = control + "." + attr
            if not cmds.objExists(plug) or not cmds.getAttr(plug, settable=True):
                continue
            if abs(cmds.getAttr(plug) - default) > 1e-9:
                cmds.setAttr(plug, default)
                touched = True
        zeroed += 1 if touched else 0
    return len(curves), zeroed


def posed_controls(tol=1e-3, rig=None):
    """Controls off their default translate/rotate: the rig is not at build pose."""
    out = []
    rig, _ = _rig(rig)
    for control in (cmds.sets(rig.control_set, query=True) or []) if rig else []:
        for attr, default in DEFAULTS:
            plug = control + "." + attr
            if not cmds.objExists(plug) or not cmds.getAttr(plug, settable=True):
                continue
            if abs(cmds.getAttr(plug) - default) > tol:
                out.append(control)
                break
    return out


def _key_range(paths):
    if not paths:
        return "no keys"
    count = cmds.keyframe(paths, query=True, keyframeCount=True) or 0
    if not count:
        return "no keys"
    return "%g..%g" % (cmds.findKeyframe(paths, which="first"), cmds.findKeyframe(paths, which="last"))


def foreign_constraints(control, rig):
    """Constraints already on a control whose targets lie outside the rig -- the animator's
    own work (measured 2026-09-05: the left arm's FK controls parent-constrained to
    locators beside an OverRig setup).  A second constraint on a driven channel would
    fail or fight, so such a control is left alone and named."""
    kinds = {"parentConstraint": cmds.parentConstraint, "orientConstraint": cmds.orientConstraint,
             "pointConstraint": cmds.pointConstraint, "scaleConstraint": cmds.scaleConstraint}
    out = []
    for con in cmds.listRelatives(_n(rig, control), children=True, type="constraint", fullPath=True) or []:
        if holder_of(rig) in (cmds.listConnections(con + ".nodeState", source=True, destination=False) or []):
            continue                                  # one of ours, registered on the holder
        fn = kinds.get(cmds.nodeType(con))
        targets = fn(con, query=True, targetList=True) if fn else []
        if any(not maya_rigs.under(cmds.ls(t, long=True)[0], rig.group) for t in targets):
            out.extend(targets)
    return out


Plan = collections.namedtuple(
    "Plan", "root drives missing bones rig_bones refusal schema src_rest rig_rest align scale notes busy rig")


def _plan(source_root=None, rig=None):
    """Everything connect() needs, computed without touching the scene."""
    empty = Plan("", [], [], {}, {}, "", OWN, {}, {}, {}, 1.0, [], [], None)
    rig, refusal = _rig(rig)
    if rig is None:
        return empty._replace(refusal=refusal)
    empty = empty._replace(rig=rig)
    joints = cmds.ls(type="joint", long=True) or []
    if source_root is None:
        # the selection names the SOURCE; a rig control in it named the rig already
        source_root, refusal = source_root_of(
            [p for p in (cmds.ls(selection=True, long=True) or [])
             if maya_rigs.rig_of(p, [rig]) is None or cmds.objectType(p) == "joint"],
            joints, maya_rigs.rig_paths(rig))
        if refusal:
            return empty._replace(refusal=refusal)
    elif not cmds.objExists(source_root):
        return empty._replace(refusal="%s not found" % source_root)
    game_root = rig.skeleton_root
    if not game_root:
        return empty._replace(refusal="the rig drives no skeleton - is this rig constrained to the game bones?")
    rig_bones = dict((leaf(p), p) for p in [game_root] + (
        cmds.listRelatives(game_root, allDescendents=True, type="joint", fullPath=True) or []))
    bones = source_bones(source_root)
    schema = detect_schema(list(bones))
    if schema is None or (schema is MIXAMO and skelmap.convention_of(list(bones.values()))
                          not in MIXAMO_CONVENTIONS):
        # none of SCHEMAS: any other convention, read by maya_skeletonmap
        schema, refusal = generic_schema(source_root, dict(
            (name, cmds.getAttr(path + ".worldMatrix[0]")) for name, path in rig_bones.items()))
        if schema is None:
            return empty._replace(refusal=refusal)
        bones = dict(schema.bones)
    controls = [c for c in candidates(schema) if cmds.objExists(_n(rig, c))]
    drives, missing = drive_plan(controls, list(bones), schema)
    drives = [d for d in drives
              if d.kind in ("fk", "main", "ground", "pelvis") or cmds.objExists(_n(rig, d.source))]
    drives = [d for d in drives
              if d.kind != "pole" or all(cmds.objExists(_n(rig, j)) for j in pole_joints(d.control))]
    drives = [d for d in drives if our_bone(d.control) in rig_bones]
    busy = [(d.control, foreign_constraints(d.control, rig)) for d in drives]
    busy = [(c, t) for c, t in busy if t]
    drives = [d for d in drives if d.control not in dict(busy)]
    rig_rest = dict((name, cmds.getAttr(path + ".worldMatrix[0]")) for name, path in rig_bones.items())
    src_rest = rest_matrices(bones, schema, rig_rest)
    # a bone the rest pose cannot describe cannot be driven either
    lacking = [d for d in drives if d.kind in ("fk", "main", "ground", "pelvis") and d.source not in src_rest]
    missing += [(d.control, d.source) for d in lacking]
    drives = [d for d in drives if d not in lacking]
    if not drives:
        return empty._replace(refusal="no bone of %s matches this rig" % leaf(source_root))
    fk = [d for d in drives if d.kind == "fk"]
    triples = [(d.control, our_bone(d.control), d.source) for d in fk]
    align = (alignments(triples, rig_rest, src_rest, parents_of(rig_bones),
                        getattr(schema, "parents", None) or parents_of(bones))
             if schema.align else dict((d.control, list(om.MMatrix())) for d in fk))
    scale = scale_factor(rig_rest, src_rest, schema)
    notes = ["schema %s%s; the source stands %.4g times our size, so its travel is scaled by %.4f"
             % (schema.name, (", rest from %s" % schema.template) if schema.template else "",
                1.0 / scale if scale else 0.0, scale)] + list(getattr(schema, "notes", []))
    if schema.align:
        worst = max([(rotation_angle(a), c) for c, a in align.items()] or [(0.0, "")])
        notes.append("rest poses aligned bone by bone, worst %.2f deg (%s)" % (worst[0], worst[1]))
    note = proportion_note(limb_ratios(rig_rest, src_rest, schema))
    if note:
        notes.append(note)
    if busy:
        notes.append("left alone, already constrained by something that is not the rig: "
                     + ", ".join("%s (%s)" % (c, ", ".join(t)) for c, t in busy))
    return Plan(source_root, drives, missing, bones, rig_bones, "", schema, src_rest, rig_rest, align, scale,
                notes, busy, rig)


def _rotation_offset(drive, plan):
    """The constant rotation offset for an FK / main / pelvis drive: reference * source_rest^-1."""
    reference = reference_rotation(cmds.getAttr(_n(plan.rig, drive.control) + ".worldMatrix[0]"),
                                   plan.align.get(drive.control, list(om.MMatrix())))
    return rotation_only(offset_local(reference, rotation_only(plan.src_rest[drive.source])))


def _position_offset(drive, plan):
    """Where the control's rest position sits against the source's rest position, scaled:
    our rest minus scale times theirs -- a pointConstraint's world offset."""
    ours = position(cmds.getAttr(_n(plan.rig, drive.control) + ".worldMatrix[0]"))
    theirs = position(plan.src_rest[drive.source])
    return tuple(o - plan.scale * t for o, t in zip(ours, theirs))


def report(source_root=None, rig=None):
    """Read-only: what connect() would build, and from what."""
    plan = _plan(source_root, rig)
    if plan.refusal:
        return plan.refusal
    rig = plan.rig
    kinds = collections.Counter(d.kind for d in plan.drives)
    lines = ["source: %s (%d bones, keys %s)" % (plan.root, len(plan.bones), _key_range(list(plan.bones.values())))]
    lines.append("would drive %d controls: %d FK by rotation only, %d IK ends and %d poles following our own FK "
                 "joints, Main %s, RootX_M %s"
                 % (len(plan.drives), kinds["fk"], kinds["ik"] + kinds["iktoes"], kinds["pole"],
                    "from the root bone (rotation + scaled travel)" if kinds["main"] else
                    ("from the hips' horizontal travel" if kinds["ground"] else "not driven"),
                    "from the pelvis (rotation + scaled position)" if kinds["pelvis"] else "not driven"))
    lines += plan.notes
    posed = posed_controls(rig=rig)
    if posed:
        lines.append("the rig is posed (%s%s) - connect() will refuse until it is at its build pose"
                     % (", ".join(posed[:4]), " ..." if len(posed) > 4 else ""))
    if plan.missing:
        lines.append("no source bone for: " + ", ".join("%s (%s)" % (c, b) for c, b in plan.missing))
    if cmds.objExists(holder_of(rig)):
        lines.append("%s already exists - disconnect first" % holder_of(rig))
    return "\n".join(line for line in lines if line)


def connect(source_root=None, require_build_pose=True, rig=None):
    """Make the rig follow the source skeleton, in AdvancedSkeleton's own shape."""
    rig, refusal = _rig(rig)
    if rig is None:
        return refusal
    holder = holder_of(rig)
    if cmds.objExists(holder):
        return ("%s already exists - press \"Disconnect MoCap Skeleton\" in AdvancedSkeleton first, "
                "or run disconnect()" % holder)
    plan = _plan(source_root, rig)
    if plan.refusal:
        return plan.refusal
    posed = posed_controls(rig=rig)
    if posed and require_build_pose:
        return ("the rig is posed (%s%s) - press \"Go To BuildPose\" in AdvancedSkeleton first, or "
                "connect(require_build_pose=False). Every rest offset is read from the pose the rig "
                "stands in." % (", ".join(posed[:4]), " ..." if len(posed) > 4 else ""))

    # every rest quantity is read BEFORE the first constraint moves anything
    rot, pos, local = {}, {}, {}
    for d in plan.drives:
        if d.kind in ("fk", "main", "pelvis"):
            rot[d.control] = _rotation_offset(d, plan)
        if d.kind in ("main", "ground", "pelvis"):
            pos[d.control] = _position_offset(d, plan)
        if d.kind in ("ik", "iktoes"):
            local[d.control] = offset_local(cmds.getAttr(_n(rig, d.control) + ".worldMatrix[0]"),
                                            cmds.getAttr(_n(rig, d.source) + ".worldMatrix[0]"))

    auto = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)
    cmds.undoInfo(openChunk=True, chunkName="PlayerMale retarget connect")
    made = []
    try:
        _holder(rig)
        _remember_source(plan.root, holder)
        for d in plan.drives:
            control = _n(rig, d.control)
            order = cmds.getAttr(control + ".rotateOrder")
            if d.kind == "fk":
                target = plan.bones[d.source]
                if is_identity(rot[d.control], OFFSET_TOL):
                    made.append(cmds.orientConstraint(target, control)[0])
                else:
                    made.append(cmds.orientConstraint(target, control,
                                                      offset=euler_offset(rot[d.control], order))[0])
            elif d.kind in ("main", "pelvis"):
                target = plan.bones[d.source]
                made.append(cmds.orientConstraint(target, control, offset=euler_offset(rot[d.control], order))[0])
                shifted, cons = _scaled_follower(target, d.control, plan.scale, pos[d.control], rig)
                made += cons
                made.append(cmds.pointConstraint(shifted, control)[0])
            elif d.kind == "ground":
                shifted, cons = _scaled_follower(plan.bones[d.source], d.control, plan.scale, pos[d.control], rig)
                made += cons
                made.append(cmds.pointConstraint(shifted, control, skip=["y"])[0])
            elif d.kind == "ik":
                con = cmds.parentConstraint(_n(rig, d.source), control)[0]
                move, turn = parent_offsets(local[d.control], order)
                cmds.setAttr(con + ".target[0].targetOffsetTranslate", *move)
                cmds.setAttr(con + ".target[0].targetOffsetRotate", *turn)
                made.append(con)
            elif d.kind == "iktoes":
                made.append(cmds.orientConstraint(_n(rig, d.source), control,
                                                  offset=euler_offset(rotation_only(local[d.control]), order))[0])
            elif d.kind == "pole":
                pole, helpers = _pole_rig(d.control, *pole_joints(d.control), rig=rig)
                made += helpers
                made.append(cmds.pointConstraint(pole, control)[0])
        _register(made, holder)
    finally:
        cmds.undoInfo(closeChunk=True)
        cmds.autoKeyframe(state=auto)

    kinds = collections.Counter(d.kind for d in plan.drives)
    lines = ["retarget connected: %d controls of %s driven from %s -- %d FK by rotation, %d IK ends and %d poles "
             "following our own FK joints, %d constraints"
             % (len(plan.drives), maya_rigs.label(rig), leaf(plan.root), kinds["fk"], kinds["ik"] + kinds["iktoes"],
                kinds["pole"], len(made))]
    lines += plan.notes
    if plan.missing:
        lines.append("no source bone for: " + ", ".join(c for c, _ in plan.missing))
    lines.append("the source's keys run %s (playback range %g..%g)" % (
        _key_range(list(plan.bones.values())), cmds.playbackOptions(query=True, min=True),
        cmds.playbackOptions(query=True, max=True)))
    lines.append("the rig FOLLOWS the clip now and keeps nothing of it yet: run maya_pmretarget.bake() -- the "
                 "vendor's Bake over the clip's keys, then its Disconnect. Disconnecting without the bake "
                 "leaves one frozen pose.")
    return "\n".join(line for line in lines if line)


def vendor_bake(start, end, rig=None):
    """What AdvancedSkeleton's `asMoCapMatcherBake` does, in cmds, flag for flag.

    Read whole from the vendor's MEL (2026-09-07): every constraint on the holder's
    switch, resolved through `constraintParentInverseMatrix` to the object it drives,
    baked with -simulation over the range, static channels deleted afterwards.  Ours so
    the bake needs nothing of AdvancedSkeleton sourced in the session.  A copy of the
    sibling module's, deliberately: this module imports nothing from it (a test pins that).
    Returns the objects baked, in the order the constraints were registered.
    """
    rig, _ = _rig(rig)
    holder = holder_of(rig) if rig else HOLDER
    constraints = cmds.listConnections(holder + "." + SWITCH, source=False, destination=True) or []
    controls = []
    for constraint in constraints:
        driven = cmds.listConnections(constraint + ".constraintParentInverseMatrix") or []
        if driven and driven[0] not in controls:
            controls.append(driven[0])
    if not controls:
        return []
    cmds.bakeResults(*controls, simulation=True, time=(start, end), sampleBy=1,
                     disableImplicitControl=True, preserveOutsideKeys=False,
                     sparseAnimCurveBake=False, removeBakedAttributeFromLayer=False,
                     bakeOnOverrideLayer=False, controlPoints=False, shape=False)
    cmds.delete(*controls, staticChannels=True, unitlessAnimationCurves=False,
                hierarchy="none", controlPoints=False, shape=True)
    return controls


def connected_source(rig=None):
    """The source root connect() remembered on the rig's holder, or None."""
    rig, _ = _rig(rig)
    if rig is None:
        return None
    holder = holder_of(rig)
    if not cmds.objExists(holder) or not cmds.attributeQuery(SOURCE_ATTR, node=holder, exists=True):
        return None
    root = cmds.getAttr(holder + "." + SOURCE_ATTR)
    return root if root and cmds.objExists(root) else None


def bake(disconnect=True, rig=None):
    """AdvancedSkeleton's own MoCap Matcher > Bake, over the CLIP's key range, then (by default)
    its Disconnect MoCap Skeleton.

    Since 2026-09-07 the bake itself is `vendor_bake` -- the vendor's proc in cmds, flag
    for flag -- over the connected source's key range (a range left at 0..100 over a 0..75
    clip does not bake 25 frames of nothing), so nothing of AdvancedSkeleton has to be
    sourced in the session.  Returns what was keyed.
    """
    rig, refusal = _rig(rig)
    if rig is None:
        return refusal
    if not cmds.objExists(holder_of(rig)):
        return "nothing connected (%s not found) - connect() first" % holder_of(rig)
    controls = set(cmds.sets(rig.control_set, query=True) or [])
    before = set(c for c in controls if cmds.listConnections(c, type="animCurve", source=True, destination=False))
    span = source_key_range(rig) or (cmds.playbackOptions(query=True, min=True),
                                     cmds.playbackOptions(query=True, max=True))
    vendor_bake(span[0], span[1], rig)
    keyed = [c for c in controls if c not in before and cmds.listConnections(c, type="animCurve", source=True, destination=False)]
    curves = list(set(cmds.listConnections(keyed, type="animCurve", source=True, destination=False) or [])) if keyed else []
    baked = ("%g..%g" % (cmds.findKeyframe(curves, which="first"), cmds.findKeyframe(curves, which="last"))) if curves else "nothing"
    note = "baked %d controls over %s (%d curves; static channels dropped, as the vendor's Bake does)" % (len(keyed), baked, len(curves))
    if disconnect:
        note += "; " + disconnect_(rig)
    else:
        note += "; still connected - disconnect() when done"
    return note


def disconnect(rig=None):
    """What AdvancedSkeleton's own \"Disconnect MoCap Skeleton\" button does -- and, like it, it
    keeps NOTHING of the clip: bake() first, or the rig is left frozen in one pose."""
    return disconnect_(rig)


def disconnect_(rig=None):
    rig, refusal = _rig(rig)
    if rig is None:
        return refusal
    holder = holder_of(rig)
    if not cmds.objExists(holder):
        return "nothing connected (%s not found)" % holder
    doomed = []
    if cmds.attributeQuery(SWITCH, node=holder, exists=True):
        doomed = cmds.listConnections(holder + "." + SWITCH, source=False, destination=True) or []
    cmds.undoInfo(openChunk=True, chunkName="PlayerMale retarget disconnect")
    try:
        for node in sorted(set(doomed)):
            if cmds.objExists(node):
                cmds.delete(node)
        if cmds.objExists(holder):     # its children, our helpers, go with it
            cmds.delete(holder)
    finally:
        cmds.undoInfo(closeChunk=True)
    return "retarget disconnected (%d constraints)" % len(set(doomed))
