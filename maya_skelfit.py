"""A UE5 Manny-schema skeleton fitted to a humanoid mesh, and the skin.

The template is measured, never assumed: assets/manny_skeleton_template.json
is extracted from the shipped Manny_Skeleton.ma by
assets/make_skeleton_template.py (93 joints, bind orientation in the ROTATE
channels, jointOrient zero everywhere but root, rotateOrder xyz on all,
segmentScaleCompensate off). Binding uses the influences that carry real
weight in Manny's own skin -- 74 of 93; `thigh_*`, `upperarm_*` and
`spine_05` are deliberately absent because those segments' skin rides their
twist bones, which is the convention the twist rig and every UE clip assume.

Workflow (the manny-skeleton skill drives it over the bridge):

    import sys; sys.path.append(r"C:/!!!Work/MayaScripts")
    import maya_skelfit
    maya_skelfit.build()      # fit + create the skeleton, refuse over one
    # ... the user drags joints that landed badly ...
    maya_skelfit.finalize()   # mirror the edited side, re-solve orientation
    maya_skelfit.bind()       # geodesic voxel skin
    maya_skelfit.pose_test("elbows"); maya_skelfit.restore_pose()

Design: docs/superpowers/specs/2026-08-27-skeleton-skin-skill-design.md.
Live proof: docs/superpowers/plans/verify_skelfit.py.
"""

import json
import math
import os

import maya.api.OpenMaya as om
import maya.cmds as cmds

TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "assets", "manny_skeleton_template.json")

# the slice of the side reach that counts as "the arm tip" when measuring a
# mesh: vertices within 2% of the full x-span of the extreme point
_TIP_BAND = 0.02

# UE's export helpers ride the limb ends (measured: 6e-6 off their targets in
# the template), so the fit snaps them onto the fitted target instead of
# scaling them independently -- ik_hand_gun has no side suffix and sits on
# the RIGHT hand, which is exactly the case a midline rule gets wrong
IK_FOLLOWS = {
    "ik_hand_gun": "hand_r",
    "ik_hand_l": "hand_l",
    "ik_hand_r": "hand_r",
    "ik_foot_l": "foot_l",
    "ik_foot_r": "foot_r",
}

# deliberately asymmetric in the template (attachment points, not anatomy --
# the right one sits for the grip); symmetrizing them would break both
ASYMMETRIC = {"weapon_l", "weapon_r"}

_JOINT_KEYS = ("name", "parent", "translate", "rotate", "jointOrient",
               "rotateAxis", "rotateOrder", "preferredAngle", "radius",
               "segmentScaleCompensate", "side", "type", "world_position",
               "world_matrix")


# ------------------------------------------------- pure: orientation solver

def _rotation_of(matrix16):
    """The orthonormal rotation part of a flat 16-float matrix."""
    return om.MTransformationMatrix(om.MMatrix(matrix16)).rotation(
        asQuaternion=True).asMatrix()


def hierarchy_order(template):
    """Joint names, every parent before any of its children."""
    kids = children_map(template)
    order = [j["name"] for j in template["joints"] if j["parent"] is None]
    index = 0
    while index < len(order):
        order.extend(kids[order[index]])
        index += 1
    return order


def solve_channels(template, positions):
    """translate/rotate per joint for the fitted world positions.

    Each joint's world frame is the TEMPLATE frame swung so its bone aims
    at the fitted child -- and the swing is HIERARCHICAL: a joint first
    inherits its parent's full swing, then adds only the minimal aim
    correction on top. A subtree swung rigidly WITHOUT roll about its root
    bone -- which is exactly the motion the fit's own arm re-aim and a
    user dragging joints produce, and the only rigid motion positions can
    witness -- therefore keeps its template LOCAL channels exactly, and
    identical positions reproduce the template channels exactly; the roll
    conventions the twist rig and UE retarget
    rely on survive the fit either way. Leaves and zero-length bones
    inherit the parent's swing whole. `root` keeps its channels verbatim
    (jointOrient lives there; it is never re-aimed). Row-vector convention
    throughout: frame axes are rows, so a world swing right-multiplies,
    and local = world * parent_world^-1."""
    jm = joint_map(template)
    kids = children_map(template)
    swings, worlds, channels = {}, {}, {}
    for name in hierarchy_order(template):
        entry = jm[name]
        parent = entry["parent"]
        primary = kids[name][0] if kids[name] else None
        inherited = swings.get(parent) or om.MMatrix()
        if name == "root":
            total = om.MMatrix()
        elif primary is None:
            total = inherited
        else:
            u = [a - b for a, b in zip(jm[primary]["world_position"],
                                       entry["world_position"])]
            v = [a - b for a, b in zip(positions[primary], positions[name])]
            if math.hypot(*u) < 1e-4 or math.hypot(*v) < 1e-4:
                total = inherited
            else:
                carried = om.MVector(*u) * inherited
                total = inherited * swing_quat(carried, v).asMatrix()
        swings[name] = total

        tm = om.MTransformationMatrix(
            _rotation_of(entry["world_matrix"]) * total)
        tm.setTranslation(om.MVector(*positions[name]), om.MSpace.kTransform)
        worlds[name] = tm.asMatrix()

        if name == "root":
            channels[name] = {"translate": list(positions[name]),
                              "rotate": list(entry["rotate"]),
                              "world": worlds[name]}
            continue
        local = om.MTransformationMatrix(
            worlds[name] * worlds[parent].inverse())
        translate = local.translation(om.MSpace.kTransform)
        euler = local.rotation(asQuaternion=False)
        channels[name] = {
            "translate": [translate.x, translate.y, translate.z],
            "rotate": [math.degrees(euler.x), math.degrees(euler.y),
                       math.degrees(euler.z)],
            "world": worlds[name],
        }
    return channels


# ------------------------------------------------------------- pure: template

def validate_template(data):
    """Raise ValueError on anything the builder would trip over later."""
    joints = data.get("joints") or []
    if not joints:
        raise ValueError("template holds no joints")
    names = [j.get("name") for j in joints]
    dupes = sorted({n for n in names if names.count(n) > 1})
    if dupes:
        raise ValueError("duplicate joint names: %s" % ", ".join(dupes))
    known = set(names)
    for j in joints:
        missing = [k for k in _JOINT_KEYS if k not in j]
        if missing:
            raise ValueError("joint %s misses keys: %s"
                             % (j.get("name"), ", ".join(missing)))
        if j["parent"] is not None and j["parent"] not in known:
            raise ValueError("joint %s has unknown parent %s"
                             % (j["name"], j["parent"]))
    roots = [j["name"] for j in joints if j["parent"] is None]
    if len(roots) != 1:
        raise ValueError("expected exactly one root joint, found: %s" % roots)
    if not data.get("meshes"):
        raise ValueError("template holds no mesh records")
    landmarks = data.get("landmarks") or {}
    missing = [k for k in ("ground_y", "height", "tip_l", "tip_r")
               if k not in landmarks]
    if missing:
        raise ValueError("template landmarks miss: %s (regenerate with "
                         "assets/make_skeleton_template.py)" % ", ".join(missing))
    return data


def load_template(path=None):
    with open(path or TEMPLATE_PATH, encoding="utf-8") as f:
        return validate_template(json.load(f))


def joint_map(template):
    return {j["name"]: j for j in template["joints"]}


def children_map(template):
    """name -> child names, in the template's file order (stable, so the
    primary child -- the bone-axis child -- is deterministic)."""
    kids = {j["name"]: [] for j in template["joints"]}
    for j in template["joints"]:
        if j["parent"] is not None:
            kids[j["parent"]].append(j["name"])
    return kids


def side_of(name):
    if name.endswith("_l"):
        return "l"
    if name.endswith("_r"):
        return "r"
    return None


def pair_name(name):
    side = side_of(name)
    if side is None:
        return None
    return name[:-2] + ("_r" if side == "l" else "_l")


def center_names(template):
    return {j["name"] for j in template["joints"] if side_of(j["name"]) is None}


def bind_influences(template):
    """The joints the voxel bind may weight: the influences carrying real
    weight on the template's biggest mesh (the body). Handing it all 93
    would let ik_foot_l -- standing exactly on the foot -- steal the foot's
    weights, and would put the arm on `upperarm` instead of its twists."""
    body = max(template["meshes"].values(), key=lambda m: m["vertices"])
    return list(body["weighted_influences"])


# ------------------------------------------------------------------ scene side

REFERENCE_ATTR = "skelfitReference"


def scene_mesh_transforms():
    """Transforms holding a real (non-intermediate) mesh, long names."""
    shapes = cmds.ls(type="mesh", long=True, noIntermediate=True) or []
    seen, transforms = set(), []
    for shape in shapes:
        transform = cmds.listRelatives(shape, parent=True, fullPath=True)[0]
        if transform not in seen:
            seen.add(transform)
            transforms.append(transform)
    return transforms


def selected_mesh_transforms():
    """Selected transforms that hold a mesh (a selected shape counts as its
    transform), long names, selection order kept."""
    picked = []
    for node in cmds.ls(selection=True, long=True) or []:
        if cmds.nodeType(node) == "mesh":
            node = cmds.listRelatives(node, parent=True, fullPath=True)[0]
        shapes = cmds.listRelatives(node, shapes=True, fullPath=True,
                                    noIntermediate=True) or []
        if any(cmds.nodeType(s) == "mesh" for s in shapes):
            if node not in picked:
                picked.append(node)
    return picked


def target_mesh():
    """The mesh to fit/bind, or (None, reason)."""
    return choose_mesh(selected_mesh_transforms(), scene_mesh_transforms())


def mesh_points(transform):
    """World position of every vertex, one API call."""
    sel = om.MSelectionList()
    sel.add(transform)
    fn = om.MFnMesh(sel.getDagPath(0))
    return [[p.x, p.y, p.z] for p in fn.getPoints(om.MSpace.kWorld)]


def _write_channels(name, entry, channel):
    cmds.setAttr(name + ".translate", *channel["translate"], type="double3")
    cmds.setAttr(name + ".rotate", *channel["rotate"], type="double3")
    cmds.setAttr(name + ".jointOrient", *entry["jointOrient"], type="double3")


def _store_reference(positions):
    if not cmds.attributeQuery(REFERENCE_ATTR, node="root", exists=True):
        cmds.addAttr("root", longName=REFERENCE_ATTR, dataType="string")
    cmds.setAttr("root." + REFERENCE_ATTR, json.dumps(positions),
                 type="string")


def build(mesh=None):
    """Fit the template onto the mesh and create the skeleton.

    Refuses over an existing skeleton (same policy as Add Character:
    nothing happening is the safe direction) and over name clashes -- a
    stray transform named like a bone would silently rename the joint."""
    if cmds.ls(type="joint"):
        return ("refused: the scene already has joints - this builds a "
                "FRESH skeleton (delete the old one, or start a new scene)")
    template = load_template()
    taken = cmds.ls([j["name"] for j in template["joints"]]) or []
    if taken:
        return ("refused: node names the skeleton needs are taken: %s"
                % ", ".join(sorted(taken)[:6]))
    if mesh is None:
        mesh, reason = target_mesh()
        if mesh is None:
            return "refused: " + reason

    positions, notes, scale = fit_positions(template, mesh_points(mesh))
    channels = solve_channels(template, positions)
    jm = joint_map(template)
    for name in hierarchy_order(template):
        entry = jm[name]
        if entry["parent"]:
            joint = cmds.createNode("joint", name=name,
                                    parent=entry["parent"], skipSelect=True)
        else:
            joint = cmds.createNode("joint", name=name, skipSelect=True)
        cmds.setAttr(joint + ".rotateOrder", entry["rotateOrder"])
        cmds.setAttr(joint + ".segmentScaleCompensate",
                     entry["segmentScaleCompensate"])
        cmds.setAttr(joint + ".radius", entry["radius"])
        cmds.setAttr(joint + ".side", entry["side"])
        cmds.setAttr(joint + ".type", entry["type"])
        cmds.setAttr(joint + ".preferredAngle", *entry["preferredAngle"],
                     type="double3")
        _write_channels(name, entry, channels[name])
    _store_reference(positions)
    cmds.select(clear=True)
    return ("%d joints on %s - %s. Drag any joints that landed badly, then "
            "finalize()" % (len(template["joints"]),
                            mesh.rsplit("|", 1)[-1], "; ".join(notes)))


def bind(mesh=None, resolution=256):
    """Geodesic voxel skin of the mesh to the weighted-influence joints.

    Two steps, the way Maya's own bind UI does it: `skinCluster` with
    bindMethod 3 creates the deformer, `geomBind` computes the voxel
    weights. geomBind needs a GPU context (measured: it fails in batch
    with 'Unable to create an offscreen OpenGL buffer') and a failure
    leaves closest-distance fallback weights -- so it is reported loudly,
    never swallowed."""
    template = load_template()
    missing = [j["name"] for j in template["joints"]
               if not cmds.objExists(j["name"])]
    if missing:
        return "refused: no built skeleton (%s missing)" % ", ".join(missing[:4])
    if mesh is None:
        mesh, reason = target_mesh()
        if mesh is None:
            return "refused: " + reason
    shape_history = cmds.listHistory(mesh) or []
    existing = cmds.ls(shape_history, type="skinCluster") or []
    if existing:
        return ("refused: %s is already skinned (%s) - detach it first "
                "(Skin > Unbind, or skinCluster -e -ub)"
                % (mesh.rsplit("|", 1)[-1], existing[0]))
    influences = bind_influences(template)
    skin = cmds.skinCluster(
        influences + [mesh], toSelectedBones=True, bindMethod=3,
        maximumInfluences=8, obeyMaxInfluences=True, normalizeWeights=1,
        name=mesh.rsplit("|", 1)[-1].lstrip("|") + "_skin")[0]
    try:
        cmds.geomBind(skin, bindMethod=3,
                      geodesicVoxelParams=(resolution, True),
                      falloff=0.2, maxInfluences=8)
    except RuntimeError as exc:
        return ("skin %s created but voxel weighting FAILED (%s) - the "
                "weights on it now are closest-distance fallback"
                % (skin, str(exc).strip()))
    return ("%s: %s voxel-bound to %d joints (resolution %d, max 8 "
            "influences)" % (mesh.rsplit("|", 1)[-1], skin,
                             len(influences), resolution))


# canned deltas ADDED to the current rotate channels -- a visual smoke of
# the skin, not anatomy; restore_pose puts the exact prior values back
POSES = {
    "elbows": {"lowerarm_l": (0.0, 0.0, -60.0), "lowerarm_r": (0.0, 0.0, -60.0)},
    "knees": {"calf_l": (0.0, 0.0, 45.0), "calf_r": (0.0, 0.0, 45.0)},
    "shoulders": {"upperarm_l": (0.0, 0.0, -40.0),
                  "upperarm_r": (0.0, 0.0, -40.0)},
    "head": {"neck_01": (0.0, 25.0, 0.0), "head": (0.0, 20.0, 0.0)},
    "spine": {"spine_01": (15.0, 0.0, 0.0), "spine_03": (15.0, 0.0, 0.0)},
}

_POSE_STORE = {}


def pose_test(name="elbows"):
    """Apply one canned pose (delta on top of the current values)."""
    if name not in POSES:
        return "refused: unknown pose '%s' (have: %s)" % (
            name, ", ".join(sorted(POSES)))
    if _POSE_STORE:
        return "refused: a pose is already applied - restore_pose() first"
    for joint in POSES[name]:
        if not cmds.objExists(joint):
            return "refused: joint %s not in the scene" % joint
        if cmds.listConnections(joint + ".rotate", type="animCurve"):
            return ("refused: %s.rotate is keyed - pose_test is for the "
                    "unkeyed bind check" % joint)
    was_auto = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)
    try:
        for joint, delta in POSES[name].items():
            prior = cmds.getAttr(joint + ".rotate")[0]
            _POSE_STORE[joint] = prior
            cmds.setAttr(joint + ".rotate",
                         prior[0] + delta[0], prior[1] + delta[1],
                         prior[2] + delta[2], type="double3")
    finally:
        cmds.autoKeyframe(state=was_auto)
    return "pose '%s' applied to %d joints" % (name, len(POSES[name]))


def restore_pose():
    """Exact prior rotate values back (trap 14: read first, write back)."""
    if not _POSE_STORE:
        return "nothing to restore"
    was_auto = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)
    try:
        for joint, prior in list(_POSE_STORE.items()):
            if cmds.objExists(joint):
                cmds.setAttr(joint + ".rotate", *prior, type="double3")
            del _POSE_STORE[joint]
    finally:
        cmds.autoKeyframe(state=was_auto)
    return "pose restored"


def screenshot(path, view="front"):
    """One viewport frame to `path`, joints drawn through the mesh; every
    panel/camera setting put back afterwards (the user works in this
    scene)."""
    panels = cmds.getPanel(type="modelPanel") or []
    if not panels:
        return "refused: no model panel (batch session?)"
    visible = cmds.getPanel(visiblePanels=True) or []
    panel = next((p for p in panels if p in visible), panels[-1])
    camera = {"front": "front", "side": "side", "persp": "persp"}.get(view)
    if camera is None:
        return "refused: view must be front/side/persp"

    old_camera = cmds.modelEditor(panel, q=True, camera=True)
    old_xray = cmds.modelEditor(panel, q=True, jointXray=True)
    old_joints = cmds.modelEditor(panel, q=True, joints=True)
    camera_xform = cmds.xform(camera, q=True, matrix=True, worldSpace=True)
    old_coi = None
    if cmds.objExists(camera + ".centerOfInterest"):
        old_coi = cmds.getAttr(camera + ".centerOfInterest")
    try:
        cmds.modelEditor(panel, e=True, camera=camera, jointXray=True,
                         joints=True, activeView=True)
        fit = cmds.ls(type="mesh", noIntermediate=True, long=True) or None
        if fit:
            transforms = list({cmds.listRelatives(s, parent=True,
                                                  fullPath=True)[0]
                               for s in fit})
            cmds.viewFit(camera, *transforms)
        cmds.playblast(frame=[cmds.currentTime(query=True)],
                       format="image", compression="png",
                       completeFilename=path, viewer=False,
                       showOrnaments=False, percent=100,
                       widthHeight=(1280, 960), forceOverwrite=True)
    finally:
        cmds.xform(camera, matrix=camera_xform, worldSpace=True)
        if old_coi is not None:
            cmds.setAttr(camera + ".centerOfInterest", old_coi)
        cmds.modelEditor(panel, e=True, camera=old_camera,
                         jointXray=old_xray, joints=old_joints)
    return path


def _skeleton_positions(template):
    return {j["name"]: cmds.xform(j["name"], q=True, ws=True, translation=True)
            for j in template["joints"]}


def finalize(side=None):
    """Mirror the user-edited side onto the other and re-solve every
    orientation. Accidental keys (autoKey during joint drags) are cut --
    before the bind the skeleton's pose IS the data, keys on it are noise."""
    template = load_template()
    missing = [j["name"] for j in template["joints"]
               if not cmds.objExists(j["name"])]
    if missing:
        return ("refused: no built skeleton (%s missing)"
                % ", ".join(missing[:4]))
    current = _skeleton_positions(template)
    if side is None:
        if not cmds.attributeQuery(REFERENCE_ATTR, node="root", exists=True):
            return ("refused: no fit reference on root - pass side='l' or "
                    "side='r' explicitly")
        reference = json.loads(cmds.getAttr("root." + REFERENCE_ATTR))
        side, moved = edited_side(reference, current)

    result = finalize_positions(template, current, side)
    channels = solve_channels(template, result)
    jm = joint_map(template)
    was_auto = cmds.autoKeyframe(query=True, state=True)
    cmds.autoKeyframe(state=False)
    try:
        cut = 0
        for name in hierarchy_order(template):
            for channel in ("translate", "rotate"):
                curves = cmds.listConnections(name + "." + channel,
                                              type="animCurve") or []
                if curves:
                    cmds.cutKey(name, attribute=channel, clear=True)
                    cut += 1
            _write_channels(name, jm[name], channels[name])
    finally:
        cmds.autoKeyframe(state=was_auto)
    _store_reference(result)
    moved_now = sum(1 for name in current
                    if math.dist(current[name], result[name]) > 1e-4)
    note = " (%d accidental keyed channels cut)" % cut if cut else ""
    return ("side '%s' mirrored onto '%s', %d joints moved, orientations "
            "re-solved%s" % (side, "r" if side == "l" else "l",
                             moved_now, note))


# ------------------------------------------------------------------ pure: fit

def _centroid(points):
    n = float(len(points))
    return [sum(p[axis] for p in points) / n for axis in range(3)]


def mesh_landmarks(points):
    """Ground, height and the two arm tips of a humanoid point cloud.

    The template's landmarks are computed from Manny's own mesh by THIS
    function (the generator imports it), so fitting a mesh onto itself is
    exact by construction rather than by luck. The arm tip is the centroid
    of the vertices within 2% of the x-span of the side's extreme point --
    the fingertips on an A/T-pose humanoid. A character whose widest point
    is not the arm (a shield, a pauldron) gets its arms fitted to that
    instead; the adjustment pass is the corrective, and the build note
    names the assumption."""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    ground = min(ys)
    band = _TIP_BAND * (max(xs) - min(xs))
    return {
        "ground_y": ground,
        "height": max(ys) - ground,
        "tip_l": _centroid([p for p in points if p[0] >= max(xs) - band]),
        "tip_r": _centroid([p for p in points if p[0] <= min(xs) + band]),
    }


def swing_quat(u, v):
    """The minimal rotation taking direction u onto direction v."""
    a = om.MVector(u[0], u[1], u[2]).normal()
    b = om.MVector(v[0], v[1], v[2]).normal()
    if a * b < -0.999999:  # antiparallel: 180 degrees about any perpendicular
        axis = a ^ om.MVector(0.0, 1.0, 0.0)
        if axis.length() < 1e-6:
            axis = a ^ om.MVector(1.0, 0.0, 0.0)
        return om.MQuaternion(math.pi, axis.normal())
    return om.MQuaternion(a, b)


def rotate_about(point, pivot, quat):
    """`point` swung about `pivot` by `quat`."""
    v = om.MVector(point[0] - pivot[0], point[1] - pivot[1],
                   point[2] - pivot[2]).rotateBy(quat)
    return [pivot[0] + v.x, pivot[1] + v.y, pivot[2] + v.z]


def arm_chain(template, side):
    """upperarm_<side> and everything riding it, template file order."""
    kids = children_map(template)
    chain, queue = [], ["upperarm_" + side]
    while queue:
        name = queue.pop(0)
        chain.append(name)
        queue.extend(kids[name])
    return chain


def fit_positions(template, points):
    """name -> world position of the template fitted onto the mesh points.

    Uniform scale by height about the ground plane, then each arm chain is
    rigidly swung about its shoulder so the template shoulder-to-tip
    direction matches the measured one (this absorbs the A-pose/T-pose
    difference), then the result is symmetrized exactly: sided pairs are
    averaged across the midline, center joints are pinned to x=0."""
    lm_t = template["landmarks"]
    lm_m = mesh_landmarks(points)
    scale = lm_m["height"] / lm_t["height"]
    notes = ["scale %.3f" % scale]
    if abs(lm_m["ground_y"]) > 1.0:
        notes.append("mesh stands %.1f off the ground plane; fitted where it "
                     "stands" % lm_m["ground_y"])

    def base(p):
        return [p[0] * scale,
                (p[1] - lm_t["ground_y"]) * scale + lm_m["ground_y"],
                p[2] * scale]

    positions = {j["name"]: base(j["world_position"])
                 for j in template["joints"]}

    for side in ("l", "r"):
        shoulder = positions["upperarm_" + side]
        u = [a - b for a, b in zip(base(lm_t["tip_" + side]), shoulder)]
        v = [a - b for a, b in zip(lm_m["tip_" + side], shoulder)]
        quat = swing_quat(u, v)
        angle = math.degrees(quat.asAxisAngle()[1])
        if angle > 0.5:
            notes.append("arm_%s re-aimed %.1f deg" % (side, angle))
        for name in arm_chain(template, side):
            positions[name] = rotate_about(positions[name], shoulder, quat)

    symmetrize(template, positions)
    return positions, notes, scale


def symmetrize(template, positions):
    """Exact symmetry in place: sided pairs averaged across the midline,
    midline joints pinned to x=0, the ik followers snapped onto their
    targets. Midline means the TEMPLATE stands on x=0 there -- an unsided
    name alone is not enough (ik_hand_gun sits on the right hand)."""
    jm = joint_map(template)
    for name, position in positions.items():
        if name in IK_FOLLOWS or name in ASYMMETRIC:
            continue
        side = side_of(name)
        if side is None:
            if abs(jm[name]["world_position"][0]) < 0.1:
                position[0] = 0.0
        elif side == "l":
            mirrored = positions[pair_name(name)]
            avg = [(position[0] - mirrored[0]) / 2.0,
                   (position[1] + mirrored[1]) / 2.0,
                   (position[2] + mirrored[2]) / 2.0]
            positions[name] = avg
            positions[pair_name(name)] = [-avg[0], avg[1], avg[2]]
    for follower, target in IK_FOLLOWS.items():
        positions[follower] = list(positions[target])
    return positions


# --------------------------------------------------- pure: finalize decisions

def choose_mesh(selected, scene):
    """The target mesh, or (None, why not): the selection wins, else the
    lone mesh; two candidates with no hint are refused, because skinning
    the wrong character in silence is worse than asking."""
    if len(selected) == 1:
        return selected[0], ""
    if len(selected) > 1:
        return None, "select ONE mesh to fit, not %d" % len(selected)
    if len(scene) == 1:
        return scene[0], ""
    if not scene:
        return None, "no mesh in the scene to fit"
    return None, ("several meshes in the scene (%s) - select the one to fit"
                  % ", ".join(n.rsplit("|", 1)[-1] for n in scene[:6]))


def edited_side(reference, current):
    """Which side the user edited: the one that diverged further from the
    snapshot `build` stored, and by how much."""
    moved = {"l": 0.0, "r": 0.0}
    for name, position in current.items():
        side = side_of(name)
        if side and name in reference:
            moved[side] = max(moved[side],
                              math.dist(position, reference[name]))
    side = "l" if moved["l"] >= moved["r"] else "r"
    return side, moved[side]


def finalize_positions(template, current, side):
    """The edited side copied onto the other across the midline, midline
    joints pinned back to x=0 (their y/z edits kept), ik followers snapped
    onto their targets, weapons left exactly where they are."""
    jm = joint_map(template)
    result = {name: list(position) for name, position in current.items()}
    for name, position in list(result.items()):
        if name in IK_FOLLOWS or name in ASYMMETRIC:
            continue
        this_side = side_of(name)
        if this_side is None:
            if abs(jm[name]["world_position"][0]) < 0.1:
                result[name][0] = 0.0
        elif this_side == side:
            result[pair_name(name)] = [-position[0], position[1], position[2]]
    for follower, target in IK_FOLLOWS.items():
        result[follower] = list(result[target])
    return result
