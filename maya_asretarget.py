"""Retarget: drive the AdvancedSkeleton rig from a second, animated skeleton.

The animator imports a clip on another skeleton, this makes the rig follow it,
and the baking stays their own button in AdvancedSkeleton: every constraint
built here registers its `nodeState` on `MoCapConstraints.disableConstraints`
and every helper node is parented under `MoCapConstraints`, which is the whole
contract the vendor's `Bake` and `Disconnect MoCap Skeleton` rely on.

Two source schemas are known (`SCHEMAS`, detected from the bones the source
actually has): a UE5 twin of the rig's own skeleton, and Mixamo -- different
names, a Y-down-the-bone convention against our X, and a T-pose rest against
our A-pose. The rest-pose difference is what the alignment below is for.  A
twin's FK controls follow their bones in POSITION as well as rotation, because a
clip can animate a bone's translation and only a twin's positions are ours to
reproduce (measured 2026-09-05: the Longsword clip slides its clavicles 3.65 cm).

Design: docs/superpowers/specs/2026-09-04-as-retarget-design.md
        docs/superpowers/specs/2026-09-05-asretarget-mixamo-design.md

Run in Maya (Script Editor, Python tab):
    import sys; sys.path.append(r"C:/!!!Work/MayaScripts")
    import maya_asretarget
    print(maya_asretarget.report())      # read-only: what would be driven
    print(maya_asretarget.connect())     # build it, from the selected skeleton
    print(maya_asretarget.disconnect())  # the same as AdvancedSkeleton's button

Then, in AdvancedSkeleton: MoCap Matcher > Bake, then Disconnect MoCap Skeleton.
"""

import collections
import math

import maya.api.OpenMaya as om
import maya.cmds as cmds

# AdvancedSkeleton deform-joint base -> UE bone base.  The rig's own map
# (2026-09-04), minus the twist Part joints: they have no FK controls and the
# rig's twist network recomputes them from the bones we drive.
ROWS = [
    ("Spine1", "spine_01"), ("Spine2", "spine_02"), ("Spine3", "spine_03"),
    ("Spine4", "spine_04"), ("Spine5", "spine_05"),
    ("Neck", "neck_01"), ("NeckPart1", "neck_02"), ("Head", "head"),
    ("Scapula", "clavicle"), ("Shoulder", "upperarm"), ("Elbow", "lowerarm"),
    ("Wrist", "hand"),
    ("IndexFinger0", "index_metacarpal"), ("IndexFinger1", "index_01"),
    ("IndexFinger2", "index_02"), ("IndexFinger3", "index_03"),
    ("MiddleFinger0", "middle_metacarpal"), ("MiddleFinger1", "middle_01"),
    ("MiddleFinger2", "middle_02"), ("MiddleFinger3", "middle_03"),
    ("RingFinger0", "ring_metacarpal"), ("RingFinger1", "ring_01"),
    ("RingFinger2", "ring_02"), ("RingFinger3", "ring_03"),
    ("PinkyFinger0", "pinky_metacarpal"), ("PinkyFinger1", "pinky_01"),
    ("PinkyFinger2", "pinky_02"), ("PinkyFinger3", "pinky_03"),
    ("ThumbFinger1", "thumb_01"), ("ThumbFinger2", "thumb_02"),
    ("ThumbFinger3", "thumb_03"),
    ("Hip", "thigh"), ("Knee", "calf"), ("Ankle", "foot"), ("Toes", "ball"),
]
SIDES = [("_M", ""), ("_L", "_l"), ("_R", "_r")]

# AdvancedSkeleton deform-joint base -> Mixamo bone base.  Measured on the
# animator's own clip 2026-09-05: 65 joints under `mixamorig:Hips`, the side is
# a PREFIX (`LeftUpLeg`), there are no metacarpals, the spine is three joints
# against our five, and the neck is one against our two.
MIXAMO_ROWS = [
    ("Spine1", "Spine"), ("Spine3", "Spine1"), ("Spine5", "Spine2"),
    ("Neck", "Neck"), ("Head", "Head"),
    ("Scapula", "Shoulder"), ("Shoulder", "Arm"), ("Elbow", "ForeArm"),
    ("Wrist", "Hand"),
    ("IndexFinger1", "HandIndex1"), ("IndexFinger2", "HandIndex2"),
    ("IndexFinger3", "HandIndex3"),
    ("MiddleFinger1", "HandMiddle1"), ("MiddleFinger2", "HandMiddle2"),
    ("MiddleFinger3", "HandMiddle3"),
    ("RingFinger1", "HandRing1"), ("RingFinger2", "HandRing2"),
    ("RingFinger3", "HandRing3"),
    ("PinkyFinger1", "HandPinky1"), ("PinkyFinger2", "HandPinky2"),
    ("PinkyFinger3", "HandPinky3"),
    ("ThumbFinger1", "HandThumb1"), ("ThumbFinger2", "HandThumb2"),
    ("ThumbFinger3", "HandThumb3"),
    ("Hip", "UpLeg"), ("Knee", "Leg"), ("Ankle", "Foot"), ("Toes", "ToeBase"),
]
MIXAMO_SIDES = [("_M", ""), ("_L", "Left"), ("_R", "Right")]

# The two controls whose own rest frame is NOT the bone's frame: AdvancedSkeleton
# keeps them world-oriented on purpose (see the rig spec), so their rest offset
# is far from the identity and rides their constraint's target offsets.  Root
# motion reaches `Main`, which is what the UE `root` bone follows -- put it in
# the pelvis instead and an export loses it.
ROOT_ROWS = [("Main", "root"), ("RootX_M", "pelvis")]
# The IK end controls sit exactly on their bones with matching frames (measured
# 0.0000-0.0095 cm, 0.00000 deg), so they need no offset.  Toes take rotation
# only, as the vendor's own connect does.
IK_ROWS = [("IKArm", "hand", True), ("IKLeg", "foot", True), ("IKToes", "ball", False)]
# The pole rides the UPPER bone's frame: the limb plane is fixed by its roll, and
# a pole point-constrained to the mid joint is degenerate on a straight limb.
POLE_ROWS = [("PoleArm", "upperarm"), ("PoleLeg", "thigh")]
MIXAMO_IK_ROWS = [("IKArm", "Hand", True), ("IKLeg", "Foot", True),
                  ("IKToes", "ToeBase", False)]
MIXAMO_POLE_ROWS = [("PoleArm", "Arm"), ("PoleLeg", "UpLeg")]

# A schema is everything that differs between one source skeleton and another.
#
# rest        -- where the source's REST pose comes from.  "live" means the
#                source stands in the same bind pose as our rig (a twin), so its
#                current matrices ARE the rest; "jointOrient" means the bind is
#                in the joints' jointOrient and the rest is the pose with every
#                rotate at 0, which is what a Mixamo FBX carries (measured
#                2026-09-05: that pose is an exact T-pose, arms along +X to
#                0.000, 47.23 cm out and 0.00 cm up).
# align       -- whether to align the rest poses bone by bone.  A twin needs no
#                alignment; Mixamo's T-pose sits 54.83 deg off our A-pose arm
#                and a retarget without the alignment droops by exactly that.
# twin        -- the source IS this skeleton: the same bones with the same
#                proportions (a second UE5 Manny).  Two things follow from that
#                one fact.  Its bone POSITIONS are ours to reproduce, so the FK
#                controls are driven in position as well as rotation -- a clip
#                can animate a bone's translation (measured 2026-09-05 on the
#                animator's Longsword clip: the clavicles slide 3.65 cm, the neck
#                base 3.67, spine_05 2.52, the thighs 0.81 over the take), and a
#                rotation-only drive lost every centimetre of it, 6.35 cm at the
#                hands.  And a position drive keeps our own sub-millimetre rest
#                offset from the source bone (0.0003-0.0095 cm) rather than going
#                straight to it.  A foreign skeleton gets neither: placing our
#                controls on Mixamo's joints would hand the rig Mixamo's
#                proportions, and its rest hand is 40 cm from where ours rests.
# root_bone    -- the source's root-motion bone, or None: Mixamo has none and
#                the travel lives in the hips.
Schema = collections.namedtuple(
    "Schema", "name rows sides side_before ik_rows pole_rows pelvis root_bone rest align "
              "twin hints")

UE5 = Schema(name="ue5", rows=ROWS, sides=SIDES, side_before=False, ik_rows=IK_ROWS,
             pole_rows=POLE_ROWS, pelvis="pelvis", root_bone="root",
             rest="live", align=False, twin=True,
             hints=("pelvis", "spine_05", "upperarm_l", "hand_r", "ball_l"))
MIXAMO = Schema(name="mixamo", rows=MIXAMO_ROWS, sides=MIXAMO_SIDES, side_before=True,
                ik_rows=MIXAMO_IK_ROWS, pole_rows=MIXAMO_POLE_ROWS,
                pelvis="Hips", root_bone=None,
                rest="jointOrient", align=True, twin=False,
                hints=("Hips", "Spine2", "LeftArm", "RightHand", "LeftToeBase"))
SCHEMAS = (UE5, MIXAMO)

# Pose-independent proportions: a joint's local translation does not change with
# the pose, so these lengths compare two skeletons without posing either.
SEGMENTS = [("thigh_l", "calf_l"), ("calf_l", "foot_l"), ("thigh_r", "calf_r"),
            ("calf_r", "foot_r"), ("upperarm_l", "lowerarm_l"),
            ("lowerarm_l", "hand_l"), ("upperarm_r", "lowerarm_r"),
            ("lowerarm_r", "hand_r"), ("pelvis", "spine_01"), ("neck_01", "head")]

# How far a rest offset may sit from the identity before it is carried at all
# (on the constraint itself, or in a pole's helper pair): the aligned controls
# measure ~1e-7 against their bones, the IK end controls stand 0.0003-0.0095 cm
# off theirs, the FK controls 0.00004 cm (median) with FKNeckPart1_M at 0.129,
# and a pole is nowhere near its bone.
OFFSET_TOL = 1e-5
# A control is at its build pose when these read their defaults.  A pole's offset
# is pose-dependent (a pole is not rigidly linked to its bone), so the rest
# matrices have to be read with the rig at rest.
DEFAULTS = (("tx", 0.0), ("ty", 0.0), ("tz", 0.0), ("rx", 0.0), ("ry", 0.0), ("rz", 0.0))

HOLDER = "MoCapConstraints"      # AdvancedSkeleton's own node name
SWITCH = "disableConstraints"    # ... and its own attribute
DRIVER_PREFIX = "asrtDriver_"
TARGET_PREFIX = "asrtTarget_"

Drive = collections.namedtuple("Drive", "control bone translate rotate")


# ---------------------------------------------------------------- pure policy

def leaf(path):
    """The short name without its namespace: `|clip:root|clip:pelvis` -> `pelvis`."""
    return path.split("|")[-1].split(":")[-1]


def bone_name(base, side, schema):
    """Pure: the source's name for a bone. Mixamo puts the side FIRST."""
    return (side + base) if schema.side_before else (base + side)


def candidates(schema=UE5):
    """Every control name the schema's tables can drive, in build order."""
    out = ["Main", "RootX_M"]
    for base, _ in schema.rows:
        for side, _ in schema.sides:
            out.append("FK" + base + side)
    for base, _, _ in schema.ik_rows:
        for side, _ in schema.sides[1:]:
            out.append(base + side)
    for base, _ in schema.pole_rows:
        for side, _ in schema.sides[1:]:
            out.append(base + side)
    return out


def drive_plan(controls, bones, schema=UE5):
    """Pure: what to constrain to what.

    controls -- control names that exist in this rig
    bones    -- leaf names that exist in the source skeleton
    Returns (drives, missing), missing being [(control, bone)] rows skipped
    because the source has no such bone.  A schema's own gaps -- Mixamo has no
    metacarpals, no second neck joint and three spine joints against our five --
    are not "missing": those rows simply are not in its table.
    """
    controls = set(controls)
    bones = set(bones)
    drives, missing = [], []

    def add(control, bone, translate, rotate):
        if control not in controls or bone is None:
            return
        if bone not in bones:
            missing.append((control, bone))
            return
        drives.append(Drive(control, bone, translate, rotate))

    add("Main", schema.root_bone, True, True)
    add("RootX_M", schema.pelvis, True, True)
    # An FK control of a twin takes the bone's POSITION too: the clip may animate
    # the bone's translation (the Longsword clip slides its clavicles 3.65 cm),
    # and only a twin's positions are ours to reproduce -- see Schema.twin.
    for as_base, src_base in schema.rows:
        for as_side, src_side in schema.sides:
            add("FK" + as_base + as_side, bone_name(src_base, src_side, schema),
                schema.twin, True)
    for as_base, src_base, translate in schema.ik_rows:
        for as_side, src_side in schema.sides[1:]:
            add(as_base + as_side, bone_name(src_base, src_side, schema),
                translate, True)
    for as_base, src_base in schema.pole_rows:
        for as_side, src_side in schema.sides[1:]:
            add(as_base + as_side, bone_name(src_base, src_side, schema),
                True, False)
    return drives, missing


def detect_schema(bones, schemas=SCHEMAS):
    """Pure: which schema this source is, by the bones it actually has.

    Scored on the schema's own hint bones, which are chosen to be unambiguous
    (`pelvis`/`spine_05` against `Hips`/`Spine2`), so a source that is neither
    scores zero everywhere and is refused rather than guessed at.
    """
    bones = set(bones)
    scored = [(sum(1 for hint in s.hints if hint in bones), s) for s in schemas]
    scored.sort(key=lambda pair: -pair[0])
    best, schema = scored[0]
    if not best:
        return None, 0
    return schema, best


def keeps_position(control, schema):
    """Pure: does this control's POSITION keep our own rest offset?

    A pole always does -- it stands 85 cm out from its bone and that standoff IS
    the control.  Everything else follows the schema: a twin keeps its
    sub-millimetre offset, a foreign skeleton goes straight to the source's bone
    because our rest hand is 40 cm from where its rest hand is.
    """
    if control.startswith("Pole"):
        return True
    return schema.twin


def top_joint(path, joint_paths):
    """Pure: the shallowest joint on `path`, or None.

    A group above the skeleton is not a joint, so `|grp|root|pelvis` answers
    `|grp|root` -- which is what lets the animator select the enclosing group's
    contents, a namespaced import or a plain bone and mean the same skeleton.
    """
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
        return "", ("the selection holds no joint - select a bone of the "
                    "imported skeleton")
    if len(roots) > 1:
        return "", ("two skeletons selected (%s) - select bones of one only"
                    % ", ".join(leaf(r) for r in roots))
    root = roots[0]
    for path in rig_paths_:
        if path == root or path.startswith(root + "|"):
            return "", ("%s is the rig's own skeleton - select the imported "
                        "clip's skeleton instead" % root)
    return root, ""


def rigid(matrix):
    """Pure: the same transform with its scale and shear thrown away.

    Both matrices going into an offset have to be rigid, or the offset carries a
    scale that the helper's driver -- a plain transform following the bone by
    point+orient, scale 1 -- cannot reproduce: measured, the rig's own scale
    chain leaves ~4e-7 on a bone, and 85 cm out at the pole that came back as
    33 microns of error.
    """
    tm = om.MTransformationMatrix(om.MMatrix(matrix))
    out = om.MTransformationMatrix()
    out.setRotation(tm.rotation(asQuaternion=True))
    out.setTranslation(tm.translation(om.MSpace.kWorld), om.MSpace.kWorld)
    return list(out.asMatrix())


def offset_local(control_world, bone_world):
    """Pure: the rest offset as a LOCAL matrix, C_rest * B_rest^-1.

    Maya is row-vector (world = local * parent), so a helper carrying this as its
    local matrix, under a parent holding the source bone's world matrix, stands
    exactly where the control stands at rest -- whatever pose the clip is in.
    A parentConstraint's target offsets carry the same matrix (`parent_offsets`).
    """
    return list(om.MMatrix(rigid(control_world))
                * om.MMatrix(rigid(bone_world)).inverse())


def is_identity(matrix, tol=1e-6):
    """Pure: is this 16-float matrix the identity within tol?"""
    return all(abs(a - b) <= tol
               for a, b in zip(list(om.MMatrix(matrix)), list(om.MMatrix())))


def rotation_only(matrix):
    """Pure: the same matrix with its translation row zeroed."""
    m = list(matrix)
    m[12] = m[13] = m[14] = 0.0
    return m


def needs_offset(local, translate, tol=OFFSET_TOL):
    """Pure: must this drive carry a rest offset at all?

    Measured, never tabulated: whether a control stands on its bone is a fact
    about the rig, and a rotation-only drive does not care where the bone is.
    """
    return not is_identity(local if translate else rotation_only(local), tol)


def segment_lengths(positions):
    """Pure: {first bone of the pair: distance} for every SEGMENTS pair present."""
    out = {}
    for a, b in SEGMENTS:
        if a in positions and b in positions:
            pa, pb = positions[a], positions[b]
            out[a] = math.sqrt(sum((x - y) ** 2 for x, y in zip(pa, pb)))
    return out


def our_bone_map():
    """Pure: {control: the UE bone it drives on OUR rig}.

    Our rig is always the UE5 Manny, whatever the source is, so this comes from
    the UE5 tables and never from the schema.
    """
    out = {"Main": "root", "RootX_M": "pelvis"}
    for base, ue in ROWS:
        for side, ue_side in SIDES:
            out["FK" + base + side] = ue + ue_side
    for base, ue, _ in IK_ROWS:
        for side, ue_side in SIDES[1:]:
            out[base + side] = ue + ue_side
    for base, ue in POLE_ROWS:
        for side, ue_side in SIDES[1:]:
            out[base + side] = ue + ue_side
    return out


def position(matrix):
    """Pure: the translation row of a 16-float matrix."""
    return (matrix[12], matrix[13], matrix[14])


def direction(rest, first, second):
    """Pure: the unit vector from one rest bone to another, or None if they sit
    on top of each other (a zero-length bone says nothing about a direction)."""
    if first not in rest or second not in rest:
        return None
    a, b = position(rest[first]), position(rest[second])
    v = om.MVector(b[0] - a[0], b[1] - a[1], b[2] - a[2])
    if v.length() < 1e-6:
        return None
    return v.normal()


def rotation_angle(matrix):
    """Pure: how far a rotation matrix turns, in degrees."""
    q = om.MTransformationMatrix(om.MMatrix(matrix)).rotation(asQuaternion=True)
    return math.degrees(2 * math.acos(max(-1.0, min(1.0, abs(q.w)))))


def align_rotation(ours, theirs):
    """Pure: the minimal rotation taking our rest bone direction onto the
    source's, as a 16-float matrix.

    Minimal because nothing else is known: the two skeletons agree on where a
    bone POINTS at rest and say nothing about the roll around it, and the roll
    our rig already has is the one its own axis work established.
    """
    if ours is None or theirs is None:
        return list(om.MMatrix())
    return list(om.MQuaternion(ours, theirs).asMatrix())


def depth_of(leaf_name, parents):
    """Pure: how many steps up to the top of the skeleton."""
    depth, node = 0, parents.get(leaf_name)
    while node:
        depth += 1
        node = parents.get(node)
    return depth


def descends(child, ancestor, parents):
    """Pure: how many steps from child up to ancestor, or 0 if unrelated."""
    steps, node = 1, parents.get(child)
    while node:
        if node == ancestor:
            return steps
        steps += 1
        node = parents.get(node)
    return 0


# Which child gives a bone its direction, where the nearest one is the wrong
# one.  A hand's nearest mapped descendant is the THUMB -- the one finger that
# does not continue the hand -- and taking it rolled the wrist by a measured
# 30.77 deg.  The middle finger is what a hand points along.
DIRECTION_CHILD = {"hand_l": "middle_01_l", "hand_r": "middle_01_r"}


def alignments(triples, rig_rest, src_rest, rig_parents, src_parents):
    """Pure: {control: the rest-alignment rotation for its bone}.

    A bone's direction needs a child to point at, and it has to be a child BOTH
    skeletons map -- so the hand aims at the middle finger (Mixamo has no
    metacarpal) and the head, the toes and the finger tips, which have no mapped
    child at all, inherit their parent's alignment.  Processed from the root
    down, so a parent's answer is ready when its children ask for it.
    """
    ordered = sorted(triples, key=lambda t: depth_of(t[1], rig_parents))
    preferred = dict((t[1], t[2]) for t in triples)
    out, by_bone = {}, {}
    for control, our_bone, src_bone in ordered:
        best = None
        want = DIRECTION_CHILD.get(our_bone)
        if want is not None and want in preferred:
            best = (0, want, preferred[want])
        for other, other_our, other_src in triples:
            if other == control or best is not None and best[0] == 0:
                continue
            ours = descends(other_our, our_bone, rig_parents)
            theirs = descends(other_src, src_bone, src_parents)
            if ours and theirs and (best is None or ours + theirs < best[0]):
                best = (ours + theirs, other_our, other_src)
        rotation = None
        if best is not None:
            rotation = align_rotation(direction(rig_rest, our_bone, best[1]),
                                      direction(src_rest, src_bone, best[2]))
        if rotation is None:                      # no mapped child: inherit
            node = rig_parents.get(our_bone)
            while node and node not in by_bone:
                node = rig_parents.get(node)
            rotation = by_bone.get(node, list(om.MMatrix()))
        out[control] = rotation
        by_bone[our_bone] = rotation
    return out


def reference_matrix(control_rest, align, source_rest, keep_position):
    """Pure: where the control should stand when the source stands at ITS rest.

    Rotation: our own rest frame, turned by the alignment (a WORLD rotation, so
    it post-multiplies).  Position: ours when the offset is worth keeping, the
    source's bone when it is not.
    """
    tm = om.MTransformationMatrix(om.MMatrix(rigid(control_rest))
                                  * om.MMatrix(align))
    out = om.MTransformationMatrix()
    out.setRotation(tm.rotation(asQuaternion=True))
    where = position(control_rest) if keep_position else position(source_rest)
    out.setTranslation(om.MVector(where[0], where[1], where[2]), om.MSpace.kWorld)
    return list(out.asMatrix())


def euler_offset(matrix, rotate_order):
    """Pure: a rotation matrix as the euler triple a constraint's `offset` takes.

    Measured 2026-09-05: an orientConstraint's offset holds
    `W_target = O * W_source` (trap 19's convention, worst element 0.000000000),
    which is exactly the shape of our rest offset -- so a rotation-only drive
    needs no helper node at all.
    """
    tm = om.MTransformationMatrix(om.MMatrix(matrix))
    tm.reorderRotation(rotate_order + 1)
    e = tm.rotation(asQuaternion=False)
    return (math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))


def parent_offsets(matrix, rotate_order):
    """Pure: a rigid rest offset as a parentConstraint's two target offsets.

    Measured 2026-09-05 on sandbox transforms over all six rotate orders:
    `targetOffsetTranslate` = the offset's translation row and
    `targetOffsetRotate` = its euler in the CONSTRAINED node's rotate order make
    the constraint hold exactly W_control = O * W_source (worst element 4.6e-14),
    and `-mo` stores those very numbers.  So a position+rotation drive with a
    rest offset is ONE constraint and no helper node.  The order matters: read
    in xyz for a zyx control the follow is wrong by up to 1.47.
    """
    m = list(matrix)
    return (m[12], m[13], m[14]), euler_offset(rotation_only(matrix), rotate_order)


LIMB_SPANS = [("arm", "Shoulder", "Elbow", "Wrist"),
              ("leg", "Hip", "Knee", "Ankle")]


def limb_ratios(rig_rest, src_rest, schema, side="_L"):
    """Pure: {limb: rig length / source length} through the schema's own map.

    Measured through the map rather than by name, because a foreign schema
    shares no bone name with us -- which is why the plain segment comparison
    stays silent on a Mixamo source and this exists.
    """
    ours = our_bone_map()
    src_side = dict(schema.sides)[side]
    out = {}
    for limb, first, middle, last in LIMB_SPANS:
        rig_names = [ours.get("FK" + b + side) for b in (first, middle, last)]
        rows = dict(schema.rows)
        src_names = [bone_name(rows[b], src_side, schema) if b in rows else None
                     for b in (first, middle, last)]
        if None in rig_names or None in src_names:
            continue
        if not all(n in rig_rest for n in rig_names) or \
                not all(n in src_rest for n in src_names):
            continue

        def span(rest, names):
            total = 0.0
            for a, b in zip(names, names[1:]):
                pa, pb = position(rest[a]), position(rest[b])
                total += math.sqrt(sum((x - y) ** 2 for x, y in zip(pa, pb)))
            return total
        source = span(src_rest, src_names)
        if source > 1e-6:
            out[limb] = span(rig_rest, rig_names) / source
    return out


def proportion_note(ratios, tol=0.02):
    """What a length difference means for the animator, per FK/IK mode.

    Nothing is scaled and nothing is refused: a rotation copy keeps the rig's
    own proportions (FK) and an end-effector copy lands the hand where the
    source's is (IK).  Both are right, they just differ, and by how much is
    what this says.
    """
    off = dict((limb, r) for limb, r in ratios.items() if abs(r - 1.0) > tol)
    if not off:
        return ""
    parts = ", ".join("the rig's %s is %+.1f%% of the source's" % (limb, (r - 1.0) * 100.0)
                      for limb, r in sorted(off.items()))
    return (parts + " - in FK the rig copies the source's ANGLES (its own "
            "proportions kept), in IK the hand and foot land on the source's own "
            "positions; both are driven, the FKIKBlend chooses")


def scale_warning(source_lengths, rig_lengths, tol=0.02):
    """Pure: name the segments whose length differs by more than tol, or ""."""
    bad = []
    for name in sorted(rig_lengths):
        if name not in source_lengths:
            continue
        rig, src = rig_lengths[name], source_lengths[name]
        if rig > 1e-6 and abs(src - rig) / rig > tol:
            bad.append("%s %.1f vs %.1f" % (name, src, rig))
    if not bad:
        return ""
    return ("the source's proportions differ (source vs rig): " + ", ".join(bad)
            + " - a rotation copy will not land the feet; scale the source first")


# ------------------------------------------------------------- scene wrappers

def source_bones(root):
    """{leaf name without namespace: long path} for the source subtree."""
    paths = [root] + (cmds.listRelatives(root, allDescendents=True, type="joint",
                                        fullPath=True) or [])
    return dict((leaf(p), p) for p in paths)


def parents_of(bones):
    """{leaf: parent leaf} inside one skeleton, from the DAG paths themselves."""
    out = {}
    for name, path in bones.items():
        parts = [leaf("|" + p) for p in path.split("|") if p]
        out[name] = parts[-2] if len(parts) > 1 else None
    return out


def _local_rest(joint):
    """The joint's own LOCAL matrix with rotate at 0: what its bind pose is when
    the bind lives in jointOrient rather than in the rotate channels."""
    def euler(values):
        return om.MEulerRotation([math.radians(v) for v in values], 0).asMatrix()
    m = euler(cmds.getAttr(joint + ".rotateAxis")[0]) * euler(
        cmds.getAttr(joint + ".jointOrient")[0])
    scale = om.MMatrix()
    for i, v in enumerate(cmds.getAttr(joint + ".scale")[0]):
        scale.setElement(i, i, v)
    m = scale * m
    for i, v in enumerate(cmds.getAttr(joint + ".translate")[0]):
        m.setElement(3, i, v)
    return m


def rest_matrices(bones, mode):
    """{leaf: rest world matrix} for a skeleton.

    "live" -- the source stands in the same bind pose as our rig, so what the
    scene shows IS the rest (and our own rig, at its build pose, always answers
    this way).
    "jointOrient" -- the bind is in the joints' jointOrient, so the rest is the
    pose with every rotate at 0, walked down the hierarchy.  Measured on the
    animator's Mixamo clip: that pose is an exact T-pose.  Our own rig must
    NEVER be read this way -- its bind lives in the rotate channels, and
    zeroing them straightens the skeleton by 76 cm.
    """
    if mode == "live":
        return dict((name, cmds.getAttr(path + ".worldMatrix[0]"))
                    for name, path in bones.items())
    parents = parents_of(bones)
    order = sorted(bones, key=lambda name: depth_of(name, parents))
    out = {}
    for name in order:
        parent = parents.get(name)
        base = om.MMatrix(out[parent]) if parent in out else om.MMatrix(
            cmds.getAttr((cmds.listRelatives(bones[name], parent=True, fullPath=True)
                          or [None])[0] + ".worldMatrix[0]")
            if cmds.listRelatives(bones[name], parent=True) else om.MMatrix())
        out[name] = list(_local_rest(bones[name]) * base)
    return out


def tpose_note(rest, schema):
    """What the computed rest pose looks like, so a wrong guess is visible.

    A retarget rests entirely on the source's rest pose being the pose the
    clip's rotations are measured from; if that came out wrong, every number
    below it is wrong too, quietly.  So the arm spread and the height are
    reported rather than assumed.
    """
    if schema.rest == "live":
        return ""
    pairs = [("LeftArm", "LeftHand"), ("upperarm_l", "hand_l")]
    for shoulder, hand in pairs:
        if shoulder in rest and hand in rest:
            a, b = position(rest[shoulder]), position(rest[hand])
            top = max(position(m)[1] for m in rest.values())
            return ("source rest pose: arm reaches %.2f cm sideways and %.2f cm "
                    "vertically (a T-pose is sideways only), height %.2f cm"
                    % (abs(b[0] - a[0]), abs(b[1] - a[1]), top))
    return ""


def rig_paths():
    """Long paths that belong to the rig: everything under `Group` (the rig's own
    internals) plus the UE skeleton our DeformationSystem drives -- those joints
    carry our constraints, which is what tells them apart from an imported clip."""
    out = []
    for j in cmds.ls(type="joint", long=True) or []:
        if j == "|Group" or j.startswith("|Group|"):
            out.append(j)
        elif cmds.listRelatives(j, children=True, type="constraint"):
            out.append(j)
    return out


def rig_skeleton_root(paths):
    """The rig's UE skeleton root: the shallowest path outside `Group`."""
    outside = [p for p in paths if not (p == "|Group" or p.startswith("|Group|"))]
    if not outside:
        return ""
    return sorted(outside, key=lambda p: (p.count("|"), p))[0]


def _set_local(node, matrix):
    """Write a local matrix onto a transform as translate + rotate.

    Only those two are needed: a point constraint reads the target's world
    position and an orient constraint its world rotation, and the offset between
    two rigid frames carries no shear.
    """
    tm = om.MTransformationMatrix(om.MMatrix(matrix))
    tm.reorderRotation(cmds.getAttr(node + ".rotateOrder") + 1)
    e = tm.rotation(asQuaternion=False)
    t = tm.translation(om.MSpace.kTransform)
    cmds.setAttr(node + ".translate", t.x, t.y, t.z)
    cmds.setAttr(node + ".rotate", math.degrees(e.x), math.degrees(e.y),
                 math.degrees(e.z))


def _holder():
    """AdvancedSkeleton's own holder node, created the way its connect does."""
    if not cmds.objExists(HOLDER):
        cmds.createNode("transform", name=HOLDER, skipSelect=True)
        for attr in ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz"):
            cmds.setAttr(HOLDER + "." + attr, lock=True)
    if not cmds.attributeQuery(SWITCH, node=HOLDER, exists=True):
        cmds.addAttr(HOLDER, longName=SWITCH, attributeType="bool", keyable=True)
    return HOLDER


def _register(constraints):
    """The contract: the vendor's Bake walks these, its Disconnect deletes them."""
    for c in constraints:
        cmds.connectAttr(HOLDER + "." + SWITCH, c + ".nodeState", force=True)


def _helper(control, source_path, local):
    """Driver (follows the source bone 1:1) + target (holds the rest offset)."""
    driver = cmds.createNode("transform", name=DRIVER_PREFIX + control,
                             parent=HOLDER, skipSelect=True)
    made = [cmds.pointConstraint(source_path, driver)[0],
            cmds.orientConstraint(source_path, driver)[0]]
    target = cmds.createNode("transform", name=TARGET_PREFIX + control,
                             parent=driver, skipSelect=True)
    _set_local(target, local)
    return target, made


NECK_BIAS = ("FKNeck_M", "bias", 10.0)   # measured: 0 -> neck_01 takes half, 10 -> all
# The in-between's OTHER share, found 2026-09-05: NeckPart1_M's orientConstraint
# has its offsetX DRIVEN -- the head's twist about the neck axis (HeadQTETwist_M)
# times this multiplier -- so neck_02 rolls by half of whatever the head rolls
# (24.24 deg at a 52.8 deg head twist on the Longsword clip) while a UE source
# keeps neck_02 at its rest roll.  The same design as the limb twist joints.
# At 0 neck_02 lands exactly on every frame.  Read it under the pose, never at
# rest: at build pose the offset reads (0, 0, 0) and hides all of this.
NECK_TWIST = ("twistAmountDivideNeckPart1_M", "input2", 0.0)


def has_neck_inbetween():
    """Does this rig's neck distribute its control's bend across two joints?"""
    control, attr, _ = NECK_BIAS
    return bool(cmds.objExists("NeckInbetweenMM_M")
                and cmds.attributeQuery(attr, node=control, exists=True))


def neck_note():
    """What the neck's in-between costs a retarget, and the knob that removes it.

    Measured 2026-09-04: `FKNeck_M.bias` (keyable, soft range 0..10, default 0)
    feeds the in-between's blend weight linearly -- 0 gives 0.5 and 10 gives
    1.0, where 30 deg on the control turns neck_01 by exactly 30.0000.  So at
    the default the retargeted neck lands half as bent as the source's.
    """
    if not has_neck_inbetween():
        return ""
    control, attr, full = NECK_BIAS
    tnode, tattr, tfull = NECK_TWIST
    return ("note: the neck's in-between hands neck_01 HALF of its control's "
            "bend and rolls neck_02 by half of the head's twist, so the neck lands "
            "softer and twists differently from the source (the head's orientation "
            "is exact, its position a few mm off at a 15 deg bend). For an exact "
            "neck set %s.%s to %g and %s.%s to %g -- by hand, or "
            "connect(exact_neck=True), the default."
            % (control, attr, full, tnode, tattr, tfull))


def set_exact_neck():
    """Turn the neck's in-between off by its own two knobs.  Writes.

    The bias (bend share, measured 2026-09-04) and the twist multiplier (roll
    share, measured 2026-09-05); a rig without an in-between has neither and
    gets an empty string.
    """
    if not has_neck_inbetween():
        return ""
    done = []
    for node, attr, full in (NECK_BIAS, NECK_TWIST):
        if not cmds.objExists(node) or not cmds.attributeQuery(attr, node=node,
                                                                exists=True):
            continue
        was = cmds.getAttr(node + "." + attr)
        cmds.setAttr(node + "." + attr, full)
        done.append("%s.%s %g -> %g" % (node, attr, was, full))
    if not done:
        return ""
    return ("neck: %s -- so neck_01 takes its control's bend 1:1 and neck_02 "
            "stops taking half of the head's roll. LEAVE THEM THERE: they decide "
            "how the baked neck keys distribute, and putting them back afterwards "
            "would halve the neck and re-roll neck_02." % ", ".join(done))


def posed_controls(tol=1e-3):
    """Controls off their default translate/rotate: the rig is not at build pose."""
    out = []
    for control in cmds.sets("ControlSet", query=True) or []:
        for attr, default in DEFAULTS:
            plug = control + "." + attr
            if not cmds.objExists(plug) or not cmds.getAttr(plug, settable=True):
                continue
            if abs(cmds.getAttr(plug) - default) > tol:
                out.append(control)
                break
    return out


def _key_range(paths):
    """The source's own key range, as text -- the animator has to match the
    playback range to it before the vendor's Bake, which reads only that."""
    if not paths:
        return "no keys"
    count = cmds.keyframe(paths, query=True, keyframeCount=True) or 0
    if not count:
        return "no keys"
    return "%g..%g" % (cmds.findKeyframe(paths, which="first"),
                       cmds.findKeyframe(paths, which="last"))


Plan = collections.namedtuple(
    "Plan", "root drives missing warn bones rig_bones refusal schema "
            "src_rest rig_rest align notes")


def _drive_offset(drive, plan):
    """The constant rest offset for one drive: reference * source_rest^-1."""
    ours = our_bone_map()[drive.control]
    reference = reference_matrix(
        cmds.getAttr(drive.control + ".worldMatrix[0]"),
        plan.align.get(drive.control, list(om.MMatrix())),
        plan.src_rest[drive.bone],
        keeps_position(drive.control, plan.schema))
    if plan.schema.rest == "live" and plan.schema.twin:
        # a twin: the source's rest IS our own bone's, and reading it from our
        # own rig is what the 2026-09-04 gates measured
        return offset_local(reference, plan.rig_rest[ours])
    return offset_local(reference, plan.src_rest[drive.bone])


def _plan(source_root=None):
    """Everything connect() needs, computed without touching the scene."""
    empty = Plan("", [], [], "", {}, {}, "", UE5, {}, {}, {}, [])
    if not cmds.objExists("ControlSet") or not cmds.objExists("Main"):
        return empty._replace(
            refusal="no AdvancedSkeleton rig in this scene (ControlSet/Main missing)")
    joints = cmds.ls(type="joint", long=True) or []
    rig = rig_paths()
    if source_root is None:
        source_root, refusal = source_root_of(
            cmds.ls(selection=True, long=True) or [], joints, rig)
        if refusal:
            return empty._replace(refusal=refusal)
    elif not cmds.objExists(source_root):
        return empty._replace(refusal="%s not found" % source_root)
    ue_root = rig_skeleton_root(rig)
    if not ue_root:
        return empty._replace(
            refusal="the rig drives no skeleton - is this rig constrained to UE bones?")
    rig_bones = dict((leaf(p), p) for p in [ue_root] + (
        cmds.listRelatives(ue_root, allDescendents=True, type="joint",
                           fullPath=True) or []))
    bones = source_bones(source_root)
    schema, score = detect_schema(list(bones))
    if schema is None:
        return empty._replace(
            refusal="%s is neither a UE5 skeleton nor a Mixamo one (none of %s "
                    "found) - a third schema needs a row in SCHEMAS"
                    % (leaf(source_root),
                       ", ".join(sorted(set(h for s in SCHEMAS for h in s.hints)))))
    controls = [c for c in candidates(schema) if cmds.objExists(c)]
    drives, missing = drive_plan(controls, list(bones), schema)
    ours = our_bone_map()
    drives = [d for d in drives if ours.get(d.control) in rig_bones]
    if not drives:
        return empty._replace(
            refusal="no bone of %s matches this rig" % leaf(source_root))

    src_rest = rest_matrices(bones, schema.rest)
    rig_rest = rest_matrices(rig_bones, "live")
    triples = [(d.control, ours[d.control], d.bone) for d in drives]
    align = (alignments(triples, rig_rest, src_rest,
                        parents_of(rig_bones), parents_of(bones))
             if schema.align else
             dict((d.control, list(om.MMatrix())) for d in drives))
    warn = scale_warning(
        segment_lengths(dict((n, position(m)) for n, m in src_rest.items())),
        segment_lengths(dict((n, position(m)) for n, m in rig_rest.items())))
    notes = []
    if schema.align:
        worst = max([(rotation_angle(a), c) for c, a in align.items()] or [(0.0, "")])
        notes.append("rest poses aligned bone by bone, worst %.2f deg (%s)"
                     % (worst[0], worst[1]))
    tp = tpose_note(src_rest, schema)
    if tp:
        notes.append(tp)
    ratios = limb_ratios(rig_rest, src_rest, schema)
    note = proportion_note(ratios)
    if note:
        notes.append(note)
    return Plan(source_root, drives, missing, warn, bones, rig_bones, "",
                schema, src_rest, rig_rest, align, notes)


def report(source_root=None):
    """Read-only: what connect() would build, and from what."""
    plan = _plan(source_root)
    if plan.refusal:
        return plan.refusal
    lines = ["source: %s (%d bones, schema %s, keys %s)"
             % (plan.root, len(plan.bones), plan.schema.name,
                _key_range(list(plan.bones.values())))]
    offsets = [d.control for d in plan.drives
               if needs_offset(_drive_offset(d, plan), d.translate)]
    lines.append("would drive %d controls: %d rotation only, %d with position; "
                 "%d need a rest offset (%s)"
                 % (len(plan.drives),
                    len([d for d in plan.drives if not d.translate]),
                    len([d for d in plan.drives if d.translate]),
                    len(offsets), ", ".join(offsets[:8])))
    for note in plan.notes:
        lines.append(note)
    posed = posed_controls()
    if posed:
        lines.append("the rig is posed (%s%s) - connect() will refuse until it is "
                     "at its build pose" % (", ".join(posed[:4]),
                                            " ..." if len(posed) > 4 else ""))
    if plan.missing:
        lines.append("no source bone for: "
                     + ", ".join("%s (%s)" % (c, b) for c, b in plan.missing))
    if plan.warn:
        lines.append(plan.warn)
    lines.append(neck_note())
    if cmds.objExists(HOLDER):
        lines.append("%s already exists - disconnect first" % HOLDER)
    return "\n".join(line for line in lines if line)


def connect(source_root=None, require_build_pose=True, exact_neck=True):
    """Make the rig follow the source skeleton, in AdvancedSkeleton's own shape.

    exact_neck -- set FKNeck_M.bias so neck_01 takes its control's bend 1:1
    (default since 2026-09-05, the animator's ask being an exact neck); False
    leaves the rig's neck in-between as it is and only reports the cost.
    """
    if cmds.objExists(HOLDER):
        return ("%s already exists - press \"Disconnect MoCap Skeleton\" in "
                "AdvancedSkeleton first, or run disconnect()" % HOLDER)
    plan = _plan(source_root)
    if plan.refusal:
        return plan.refusal
    posed = posed_controls()
    if posed and require_build_pose:
        return ("the rig is posed (%s%s) - press \"Go To BuildPose\" in "
                "AdvancedSkeleton first, or connect(require_build_pose=False). "
                "The rest offsets are read from the pose the rig stands in, and "
                "a pole's offset is pose-dependent."
                % (", ".join(posed[:4]), " ..." if len(posed) > 4 else ""))

    # Read every rest offset BEFORE building anything: the first constraints move
    # controls that later ones measure against (a pole follows the IK control it
    # rides, so its offset came out 0.022 cm wrong when read mid-build).
    offsets = dict((d.control, _drive_offset(d, plan)) for d in plan.drives)

    auto = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)
    cmds.undoInfo(openChunk=True, chunkName="AS retarget connect")
    made = []
    helped, turned, ground = 0, 0, ""
    try:
        _holder()
        for drive in plan.drives:
            target = plan.bones[drive.bone]
            local = offsets[drive.control]
            order = cmds.getAttr(drive.control + ".rotateOrder")
            shifted = needs_offset(local, drive.translate)
            if drive.translate and drive.rotate:
                # a rigid follow is ONE parentConstraint, its two target offsets
                # holding the rest offset exactly (measured 2026-09-05, 4.6e-14;
                # see parent_offsets).  No helper: 66 of the 74 twin drives are
                # of this kind, and a helper pair each would have doubled the
                # nodes the vendor's Bake walks.
                con = cmds.parentConstraint(target, drive.control)[0]
                if shifted:
                    move, turn = parent_offsets(local, order)
                    cmds.setAttr(con + ".target[0].targetOffsetTranslate", *move)
                    cmds.setAttr(con + ".target[0].targetOffsetRotate", *turn)
                    turned += 1
                made.append(con)
            elif drive.translate:
                # a pole: a point constraint cannot turn its offset with the
                # bone, so the offset lives in a helper pair under the holder
                if shifted:
                    target, helpers = _helper(drive.control, target, local)
                    made += helpers
                    helped += 1
                made.append(cmds.pointConstraint(target, drive.control)[0])
            elif shifted:
                # a rotation-only drive needs no node: the constraint's own
                # offset holds exactly O * W_source (measured 2026-09-05)
                made.append(cmds.orientConstraint(target, drive.control,
                                                  offset=euler_offset(local, order))[0])
                turned += 1
            else:
                made.append(cmds.orientConstraint(target, drive.control)[0])
        if plan.schema.root_bone is None and cmds.objExists("Main") \
                and plan.schema.pelvis in plan.bones:
            # no root bone in the source: give `Main` the horizontal travel, which
            # is what root motion MEANS for translation, and leave the facing in
            # the pelvis rather than inventing a yaw.  The pelvis is constrained
            # absolutely, so it absorbs whatever Main does - the pose is untouched.
            made.append(cmds.pointConstraint(plan.bones[plan.schema.pelvis], "Main",
                                             skip=["y"])[0])
            ground = ("Main takes the source's horizontal travel (%s has no root "
                      "bone); the facing stays in the pelvis" % plan.schema.name)
        _register(made)
    finally:
        cmds.undoInfo(closeChunk=True)
        cmds.autoKeyframe(state=auto)

    lines = ["retarget connected: %d controls driven from %s, schema %s "
             "(%d rest offsets on constraints, %d through a helper)"
             % (len(plan.drives), leaf(plan.root), plan.schema.name, turned, helped)]
    for note in plan.notes:
        lines.append(note)
    if ground:
        lines.append(ground)
    if plan.missing:
        lines.append("no source bone for: "
                     + ", ".join(c for c, _ in plan.missing))
    if plan.warn:
        lines.append(plan.warn)
    lines.append("playback range %g..%g, the source's keys run %s - the vendor's"
                 " Bake reads the RANGE, so match it to the clip first"
                 % (cmds.playbackOptions(query=True, min=True),
                    cmds.playbackOptions(query=True, max=True),
                    _key_range(list(plan.bones.values()))))
    lines.append(set_exact_neck() if exact_neck else neck_note())
    lines.append("now in AdvancedSkeleton: MoCap Matcher > Bake, then "
                 "Disconnect MoCap Skeleton")
    return "\n".join(line for line in lines if line)


def disconnect():
    """What AdvancedSkeleton's own \"Disconnect MoCap Skeleton\" button does."""
    if not cmds.objExists(HOLDER):
        return "nothing connected (%s not found)" % HOLDER
    doomed = []
    if cmds.attributeQuery(SWITCH, node=HOLDER, exists=True):
        doomed = cmds.listConnections(HOLDER + "." + SWITCH, source=False,
                                      destination=True) or []
    cmds.undoInfo(openChunk=True, chunkName="AS retarget disconnect")
    try:
        for node in sorted(set(doomed)):
            if cmds.objExists(node):
                cmds.delete(node)
        if cmds.objExists(HOLDER):     # its children, our helpers, go with it
            cmds.delete(HOLDER)
    finally:
        cmds.undoInfo(closeChunk=True)
    return "retarget disconnected (%d constraints)" % len(set(doomed))
