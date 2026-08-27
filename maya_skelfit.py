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

TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "assets", "manny_skeleton_template.json")

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
