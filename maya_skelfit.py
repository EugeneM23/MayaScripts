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
