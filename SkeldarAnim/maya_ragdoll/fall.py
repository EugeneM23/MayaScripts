"""Fall: a rig dropped by physics from a frame of its take, baked into its controls (2026-10-16).

One press (spec `docs/superpowers/specs/2026-10-16-ragdoll-fall-design.md`):
1. the rig (one, any part of it selected) and the span (the highlight, else the current frame for
   `length` frames); refusals before anything changes;
2. its game skeleton read at the frame before the fall and at the fall (`scene.skeleton`, the Pose
   Library's reader: the unrolled limb bones in their drive), the skin's points at the fall;
3. the Bullet ragdoll built there (`sim.Scene`), the time stepped to the end, every body read each
   frame, then every node of it deleted - all of it UNRECORDED (nothing of it survives an undo);
4. every game bone's world each frame - each riding its body as it did at the fall - as a Pose
   Library animation card in memory (the rig's own skeleton is its source: a twin, exact), pasted
   onto the rig (`animapply`, Replace, every frame, In place) on `Ragdoll_<a>` - an override layer
   weighted 0 before the fall and 1 from it - or on the base layer; one undo chunk;
5. Drop weapon: a weapon held in a hand is let go as a body of its own and baked onto the floor's
   road (`maya_scenesetup.floor`): out of the hand, its bone following it.
"""

import json
import math
from collections import OrderedDict

import maya.cmds as cmds
import numpy as np

from maya_ragdoll import plan, sim
from maya_ragdoll import impulse
from maya_ragdoll import weapon as wp

__all__ = ["fall", "Refused", "DEFAULTS", "LAYER_PREFIX"]

LAYER_PREFIX = "Ragdoll_"
#  the last press's run and card (a verify reads it)
LAST = {}
LAYER_MARKER = "skeldarRagdoll"
UNDO_CHUNK = "skeldarRagdollFall"
DEFAULTS = OrderedDict((
    ("length", 60.0),
    ("fade", 8.0),
    ("strength", 1.0),
    ("mass", 75.0),
    ("friction", 0.8),
    ("bounce", 0.1),
    ("drop_weapon", True),
    ("layer", "new"),          # "new" | "base"
))

NOTHING = "Select any part of a rig - Fall drops it from the current frame"
TWO = "Fall drops one rig at a time - %s are selected"
NOT_RIG = "%s is not a rig of ours - Fall bakes into a rig's controls"
RETARGETING = "%s is in the middle of a retarget (MoCapConstraints) - press Retarget to finish it"
SHORT = "the span %d-%d is too short - highlight more frames or raise Length"
MISSING = "%s has no %s - the ragdoll needs the UE bones"


class Refused(Exception):
    pass


# ------------------------------------------------------------------ settings

def settings(given=None):
    out = OrderedDict(DEFAULTS)
    for key, value in (given or {}).items():
        if key in out:
            out[key] = value
    out["layer"] = "base" if out["layer"] == "base" else "new"
    return out


# ------------------------------------------------------------------ what the press acts on

def _ref(selection):
    from maya_poselib import apply as ap
    refs, refusal = ap._targets(selection)
    if refusal or not refs:
        raise Refused(refusal or NOTHING)
    if len(refs) > 1:
        raise Refused(TWO % len(refs))
    ref = refs[0]
    if ref.kind != "rig" or ref.rig is None:
        raise Refused(NOT_RIG % ref.label)
    import maya_rigs
    if cmds.objExists(maya_rigs.node(ref.rig, "MoCapConstraints")):
        raise Refused(RETARGETING % ref.label)
    return ref


def _highlight():
    if cmds.about(batch=True):
        return None
    try:
        from maya_overrig import overrig
        return overrig.slider_selection()
    except Exception:                                    # noqa: BLE001 - no UI (mayapy)
        return None


def _colliders(selection, ref):
    """The selected meshes that are not the character's: their transforms."""
    from maya_poselib import scene
    out = []
    for item in selection or []:
        path = (cmds.ls(item, long=True) or [None])[0]
        if not path or cmds.nodeType(path) != "transform":
            continue
        if scene.split([path])[0]:
            continue                                       # part of a character
        meshes = cmds.listRelatives(path, shapes=True, type="mesh", fullPath=True) or []
        if any(not cmds.getAttr(m + ".intermediateObject") for m in meshes):
            out.append(path)
    return out


def _meshes(ref):
    from maya_scenesetup import colour
    shapes = colour.character_meshes(ref.root) or []
    return [s for s in cmds.ls(shapes, long=True) or []
            if cmds.nodeType(s) == "mesh" and not cmds.getAttr(s + ".intermediateObject")]


# ------------------------------------------------------------------ the simulation

def _worlds(bones):
    return dict((leaf, plan.mat(bone["world"])) for leaf, bone in bones.items())


def _bodies(worlds, keys):
    return dict((key, plan.body_frame(key, worlds)) for key in keys)


def simulate(ref, a, b, s, colliders=(), progress=None, weapons=(), impulses=True):
    """{"bones", "parents", "before", "first", "bodies": {frame: {body: 4x4}}, "radius", ...} -
    the ragdoll run from `a` to `b`, nothing of it left in the scene."""
    from maya_poselib import scene, timewalk
    bones, _convention = scene.skeleton(ref)
    missing = plan.missing_bodies(bones)
    if missing:
        raise Refused(MISSING % (ref.label, ", ".join(missing)))
    keys = [row[0] for row in plan.BODIES]
    parents = dict((leaf, bone["parent"]) for leaf, bone in bones.items())
    rider_of = plan.riders(parents)
    fps = _fps()
    with _unrecorded(), timewalk.Walk(fresh=False) as walk:
        walk.go(a - 1)
        prev = scene.refresh_world(ref, bones)
        weapon_prev = dict((w[1], wp.mat_of(w[1])) for w in weapons)
        walk.go(a)
        first = scene.refresh_world(ref, bones)
        weapon_first = dict((w[1], wp.mat_of(w[1])) for w in weapons)
        w_prev, w_first = _worlds(prev), _worlds(first)
        body_prev, body_first = _bodies(w_prev, keys), _bodies(w_first, keys)
        points = sim.skinned_points(_meshes(ref), rider_of)
        mass = plan.masses(float(s["mass"]), keys)
        kids = plan.children(keys)
        centres = dict((k, plan.pos(m)) for k, m in body_first.items())
        left, up, forward = plan.facing(w_first)
        radius, axis = {}, {}
        for key in keys:
            p, q = plan.axis_points(key, w_first)
            axis[key] = (p, q)
            radius[key] = plan.radius(points.get(key), p, q, float(np.linalg.norm(q - p)))
        hits, hit_notes = (impulse.hits(ref.rig, body_first, a, b) if impulses else ([], []))
        floor = plan.floor_height([points.get(k) for k in ("foot_l", "foot_r")],
                                  [axis[k] + (radius[k],) for k in ("foot_l", "foot_r")])
        world = sim.Scene(a, float(s["friction"]), float(s["bounce"]))
        try:
            world.build_floor(floor, centres["pelvis"])
            for path in colliders:
                world.build_collider(path)
            for key in keys:
                p, q = axis[key]
                length = float(np.linalg.norm(q - p))
                v, w = plan.velocities(body_prev[key], body_first[key], fps)
                world.build_capsule(key, body_first[key], plan.capsule_length(length, radius[key]),
                                    radius[key], mass[key], v, w)
            boxes = {}
            for index, (_side, path, _bone) in enumerate(weapons):
                centre, size = wp.local_box(path)
                now, before = weapon_first[path], weapon_prev[path]
                body_now, body_before = wp.body_frame(now, centre), wp.body_frame(before, centre)
                v, w = plan.velocities(body_before, body_now, fps)
                name = "weapon%d" % index
                world.build_box(name, body_now, size, wp.MASS, v, w)
                boxes[path] = (name, plan.rigid(now) @ np.linalg.inv(body_now))
            for key, _bones, parent, kind, _share, _start, _end in plan.BODIES:
                if parent is None:
                    continue
                anchor = axis[key][0]
                parent_dir = axis[parent][1] - axis[parent][0]
                child_dir = axis[key][1] - axis[key][0]
                frame, lo, hi = plan.joint_frame(kind, anchor, parent_dir, child_dir, forward,
                                                 plan.rot(body_first[key])[1])
                carried, lever = plan.carried(anchor, key, kids, mass, centres)
                k = plan.stiffness(float(s["strength"]), carried, lever)
                world.build_joint(key, parent, frame, lo, hi, k,
                                  plan.fade_keys(a, float(s["fade"]), k))
            # In a GUI Maya Bullet does not step while the viewport is suspended (the walk's
            # `refresh -suspend`): every body stood still (measured 2026-10-16; mayapy has no
            # viewport and fell). The steps run with the refresh on, suspended again after.
            cmds.refresh(suspend=False)
            try:
                cmds.currentTime(a)          # the solver initialises on a time change at its start
                bodies = {a: world.read()}
                done = []
                for t in range(a + 1, b + 1):
                    for hit in hits:
                        if hit["at"] == t:   # set for the one step into t, cleared after it
                            j, point = plan.impulse(mass[hit["key"]], hit["speed"], hit["tip"],
                                                    hit["direction"], bodies[t - 1][hit["key"]])
                            world.impulse(hit["key"], j, point)
                            done.append(hit)
                    cmds.currentTime(t)      # Bullet steps on a real time change, not MAnimControl
                    world.clear_impulses()
                    bodies[t] = world.read()
                    if progress is not None and not progress(t):
                        raise Refused("cancelled - nothing changed")
            finally:
                cmds.refresh(suspend=True)
        finally:
            world.delete()
    tracks = dict((path, dict((t, m @ bodies[t][name]) for t in bodies))
                  for path, (name, m) in boxes.items())
    return {"bones": bones, "parents": parents, "rider_of": rider_of, "first": first,
            "weapons": tracks, "impulses": done, "impulse_notes": hit_notes,
            "body_first": body_first, "bodies": bodies, "radius": radius, "floor": floor,
            "mass": mass}


# ------------------------------------------------------------------ the card

def card(ref, run, a, b):
    """(header, frames): the fall as a Pose Library animation card of the rig's own skeleton."""
    from maya_poselib import animcapture, animdata, scene
    bones, first = run["bones"], run["first"]
    worlds = _worlds(first)
    rider_of = run["rider_of"]
    local = plan.offsets(worlds, run["body_first"], rider_of)
    fixed = dict((leaf, plan.rigid(m)) for leaf, m in worlds.items() if leaf not in local)
    drives = {}
    for leaf, bone in first.items():
        if "drive" in bone and leaf in rider_of:
            body = rider_of[leaf]
            drives[leaf] = (body, plan.rigid(plan.mat(bone["drive"]))
                            @ np.linalg.inv(run["body_first"][body]))
    order = list(bones)
    world_rows, drive_rows = [], dict((leaf, []) for leaf in drives)
    for t in range(a, b + 1):
        now = plan.bone_worlds(local, run["bodies"][t], fixed)
        row = []
        for leaf in order:
            row.extend(animdata.encode(plan.flat(now[leaf])))
        world_rows.append(row)
        for leaf, (body, m) in drives.items():
            drive_rows[leaf].append(animdata.encode(plan.flat(m @ run["bodies"][t][body])))
    frames = {"bones": order, "world": world_rows, "drive": drive_rows}
    members = [leaf for leaf in order if leaf in rider_of]
    header = animcapture._common("character")
    header.update(animcapture._span(a, b))
    header.update({
        "name": "Ragdoll",
        "key_times": [],
        "character": scene.identity(ref),
        "bones": dict((name, animcapture._static(bone)) for name, bone in bones.items()),
        "members": members,
        "regions": scene.regions_of(bones, members),
        "rig_source": True,
        "objects": [],
    })
    return header, frames


# ------------------------------------------------------------------ the layer

def layer_name(a):
    return LAYER_PREFIX + ("%d" % a).replace("-", "m")


def ours(layer):
    return bool(cmds.objExists(layer)) and cmds.attributeQuery(LAYER_MARKER, node=layer,
                                                                exists=True)


def layers():
    """Every layer of ours in the scene."""
    return [l for l in cmds.ls(type="animLayer") or [] if ours(l)]


def _layer_selection():
    out = {}
    for layer in cmds.ls(type="animLayer") or []:
        out[layer] = bool(cmds.animLayer(layer, query=True, selected=True))
    return out


def _select_layers(chosen):
    for layer in cmds.ls(type="animLayer") or []:
        try:
            cmds.animLayer(layer, edit=True, selected=layer in chosen)
        except Exception:                                  # noqa: BLE001
            pass


def _restore_layers(state):
    for layer, on in state.items():
        if cmds.objExists(layer):
            try:
                cmds.animLayer(layer, edit=True, selected=on)
            except Exception:                              # noqa: BLE001
                pass


def make_layer(a, ref):
    """`Ragdoll_<a>` made afresh (one of ours by that name deleted first): override, weight 0
    before the fall and 1 from it (stepped), marked with the rig and the frame."""
    name = layer_name(a)
    if ours(name):
        cmds.delete(name)
    layer = cmds.animLayer(name, override=True)
    cmds.addAttr(layer, longName=LAYER_MARKER, dataType="string")
    cmds.setAttr(layer + "." + LAYER_MARKER, json.dumps({"rig": ref.namespace, "frame": a}),
                 type="string")
    cmds.setKeyframe(layer, attribute="weight", time=a - 1, value=0.0)
    cmds.setKeyframe(layer, attribute="weight", time=a, value=1.0)
    cmds.keyTangent(layer, attribute="weight", outTangentType="step")
    return layer


# ------------------------------------------------------------------ the press

def _fps():
    import maya.api.OpenMaya as om
    return float(om.MTime(1.0, om.MTime.kSeconds).asUnits(om.MTime.uiUnit()))


class _unrecorded(object):
    def __enter__(self):
        self.was = cmds.undoInfo(query=True, state=True)
        if self.was:
            cmds.undoInfo(stateWithoutFlush=False)
        return self

    def __exit__(self, *exc):
        if self.was:
            cmds.undoInfo(stateWithoutFlush=True)
        return False


def _widen(b):
    if cmds.playbackOptions(query=True, maxTime=True) < b:
        cmds.playbackOptions(maxTime=b)
    if cmds.playbackOptions(query=True, animationEndTime=True) < b:
        cmds.playbackOptions(animationEndTime=b)


def _take_range(a, b):
    """The frames a weapon's hand track is sampled over: the playback and animation ranges and the
    fall."""
    lo = min(cmds.playbackOptions(query=True, minTime=True),
             cmds.playbackOptions(query=True, animationStartTime=True), a)
    hi = max(cmds.playbackOptions(query=True, maxTime=True),
             cmds.playbackOptions(query=True, animationEndTime=True), b)
    return int(math.floor(lo)), int(math.ceil(hi))


def _cut_after(ref, members, b):
    """Base layer: the pasted controls' keys after the fall's end cut, or the take would stand the
    character back up there."""
    from maya_poselib import rigsolve
    controls = rigsolve.controls_for(ref.rig, members)
    if controls:
        cmds.cutKey(controls, time=(b + 0.5, 10 ** 7), clear=True)


def fall(selection=None, given=None, progress=None):
    """(ok, line): the press."""
    s = settings(given)
    if selection is None:
        selection = cmds.ls(selection=True, long=True) or []
    ref = _ref(selection)
    a, b = plan.span(_highlight(), cmds.currentTime(query=True), s["length"])
    if b - a < 2:
        raise Refused(SHORT % (a, b))
    colliders = _colliders(selection, ref)
    held = wp.held(ref) if s["drop_weapon"] else []
    run = simulate(ref, a, b, s, colliders, progress, held)
    hand_tracks = {}
    if held:
        lo, hi = _take_range(a, b)
        with _unrecorded():
            here = cmds.currentTime(query=True)
            hand_tracks = wp.sample([w[1] for w in held], lo, hi)
            cmds.currentTime(here)
    header, frames = card(ref, run, a, b)
    LAST.update(run=run, header=header, frames=frames, a=a, b=b)
    from maya_poselib import animapply, animdata
    options = animdata.Options(mode="replace", at_current=False, keys="every", in_place=False)
    state = _layer_selection()
    cmds.undoInfo(openChunk=True, chunkName=UNDO_CHUNK)
    try:
        _widen(b)
        if s["layer"] == "new":
            layer = make_layer(a, ref)
            _select_layers([layer])
        else:
            layer = None
            _select_layers([])
        ok, text = animapply._press_refs(header, frames, [ref], options=options)
        if ok and layer is None:
            _cut_after(ref, header["members"], b)
        dropped = ""
        if ok and held:
            dropped = wp.drop(ref, held, hand_tracks, run["weapons"], layer)
    finally:
        _restore_layers(state)
        cmds.undoInfo(closeChunk=True)
    if not ok:
        return False, text
    where = ("on %s" % layer) if layer else "on the base layer"
    line = "%s falls from frame %d to %d, %s - floor at %.1f cm" % (ref.label, a, b, where,
                                                                     run["floor"])
    if colliders:
        line += " | %d collider%s" % (len(colliders), "" if len(colliders) == 1 else "s")
    if dropped:
        line += " | " + dropped
    hit_line = impulse.summary(run.get("impulses"))
    if hit_line:
        line += " | " + hit_line
    if run.get("impulse_notes"):
        line += " | " + "; ".join(run["impulse_notes"])
    return True, line
