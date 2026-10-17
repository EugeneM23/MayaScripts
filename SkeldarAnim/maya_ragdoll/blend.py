"""Blend: the take and the ragdoll mixed (2026-10-17).

Spec `docs/superpowers/specs/2026-10-17-ragdoll-blend-design.md`. Over the span (the highlight, else
the current frame for Length) the rig's take is read on every frame and Fall's 16 capsules run over it,
every one dynamic. Each frame each body is KICKED (an impulse and a torque impulse, `plan.servo`)
toward where the take has it next frame - the zone's strength the share of the way (Anim 1, Follow its
strength, Free 0), easing in from the take over Blend in and back over Blend out; a limb rolls with its
bend plane (`plan.blend_bodies`), the joints hold the human range grown to the take's own and the
clavicle's linear reach (`plan.widened`, `plan.joint_travel`), bodies the take brings together never
collide. Every bone then plays the take turned by its body's SWING (`plan.swung`: the take's roll kept)
and laid down the skeleton by the take's offsets; an Anim zone's bones play the take exactly. Pasted
onto `RagdollBlend_<a>` (an override layer easing out over Blend out) or the base layer. One undo;
nothing of the simulation is left.
"""

import json

import maya.cmds as cmds
import numpy as np

from maya_ragdoll import fall as rd
from maya_ragdoll import impulse, plan, sim

__all__ = ["blend", "LAYER_PREFIX"]

LAYER_PREFIX = "RagdollBlend_"
UNDO_CHUNK = "skeldarRagdollBlend"
ALL_ANIM = "every zone plays the animation - nothing to simulate; set a zone to Follow or Free"
#  the last press's run and card (a verify reads it)
LAST = {}
#  how much of the last frame's drift off its aim the next aim leans against
DRIFT_GAIN = 0.5


def _states(s, keys):
    return plan.body_states(s.get("zones"), keys)


def simulate(ref, a, b, s, colliders=(), progress=None, impulses=True):
    """{"bones", "takes" {frame: bones}, "target" {frame: {body: 4x4}}, "bodies" {frame: {body:
    4x4}}, ...}: the take read on every frame `a - 1`..`b`, the ragdoll run over it."""
    from maya_poselib import scene, timewalk
    bones, _convention = scene.skeleton(ref)
    missing = plan.missing_bodies(bones)
    if missing:
        raise rd.Refused(rd.MISSING % (ref.label, ", ".join(missing)))
    keys = [row[0] for row in plan.BODIES]
    state, strength = _states(s, keys)
    if all(state[k] == "anim" for k in keys):
        raise rd.Refused(ALL_ANIM)
    parents = dict((leaf, bone["parent"]) for leaf, bone in bones.items())
    rider_of = plan.riders(parents)
    fps = rd._fps()
    blend_in, blend_out = float(s["blend_in"]), float(s["blend_out"])
    with rd._unrecorded(), timewalk.Walk(fresh=False) as walk:
        takes, worlds, target = {}, {}, {}
        for t in range(a - 1, b + 1):
            walk.go(t)
            takes[t] = scene.refresh_world(ref, bones)
            worlds[t] = rd._worlds(takes[t])
        span_all = range(a - 1, b + 1)
        target = dict(zip(span_all, plan.blend_bodies([worlds[t] for t in span_all], keys)))
        walk.go(a)
        first = takes[a]
        w_first, body_first = worlds[a], target[a]
        points = sim.skinned_points(rd._meshes(ref), rider_of)
        mass = plan.masses(float(s["mass"]), keys)
        radius, axis, length = {}, {}, {}
        for key in keys:
            p, q = plan.axis_points(key, w_first)
            axis[key] = (p, q)
            length[key] = float(np.linalg.norm(q - p))
            radius[key] = plan.radius(points.get(key), p, q, length[key])
        hits, notes = (impulse.hits(ref.rig, body_first, a, b) if impulses else ([], []))
        for hit in [h for h in hits if state[h["key"]] == "anim"]:
            hits.remove(hit)
            notes.append("%s hits the %s, which plays the animation" % (hit["name"], hit["key"]))
        anatomy = rd._anatomy(first, keys)
        _left, _up, forward = plan.facing(w_first)
        # bodies the take itself brings together (an arm across the chest) never collide
        filters, _apart = plan.collision_filters(axis, radius, keys, [
            dict((k, plan.axis_points(k, worlds[t])) for k in keys) for t in range(a, b + 1)])
        floor = plan.floor_height([points.get(k) for k in ("foot_l", "foot_r")],
                                  [axis[k] + (radius[k],) for k in ("foot_l", "foot_r")])
        # the take's soles over the whole span: a foot in the air at the first frame put the
        # floor under the other foot there, and a later step went through it
        floor = min([floor] + [y for k in ("foot_l", "foot_r")
                               for y in plan.sole_heights(points.get(k), body_first[k],
                                                          [target[t][k] for t in range(a, b + 1)])])
        inertia = dict((k, plan.capsule_inertia(mass[k], plan.capsule_length(length[k], radius[k]),
                                                radius[k])) for k in keys)
        world = sim.Scene(a, float(s["friction"]), float(s["bounce"]))
        try:
            world.build_floor(floor, plan.pos(body_first["pelvis"]))
            for path in colliders:
                world.build_collider(path)
            for key in keys:
                v, w = plan.velocities(target[a - 1][key], body_first[key], fps)
                world.build_capsule(key, body_first[key],
                                    plan.capsule_length(length[key], radius[key]), radius[key],
                                    mass[key], v, w, filters.get(key))
            span = range(a, b + 1)
            for key, _bones, parent, kind, _share, _start, _end in plan.BODIES:
                if parent is None:
                    continue
                anchor = axis[key][0]
                parent_dir = axis[parent][1] - axis[parent][0]
                child_dir = axis[key][1] - axis[key][0]
                if kind in plan.HINGES or anatomy is None:
                    frame, lo, hi = plan.joint_frame(kind, anchor, parent_dir, child_dir, forward,
                                                     plan.rot(body_first[key])[1])
                else:
                    rest_b, now_b, facing_rest = anatomy
                    frame, lo, hi, _off = plan.anatomical_joint(
                        kind, key, anchor,
                        (rest_b[parent][0], rest_b[key][0], rest_b[parent][1], rest_b[key][1]),
                        (now_b[parent][0], now_b[key][0]), facing_rest)
                # the human range grown to what the take itself does, and the linear room a
                # shrugging clavicle gives the shoulder: the joints hold the chain, never fight it
                parents_now = [target[t][parent] for t in span]
                children_now = [target[t][key] for t in span]
                lo, hi = plan.widened(lo, hi, plan.joint_angles(frame, parents_now, children_now))
                linear = plan.joint_travel(frame, anchor, parents_now, children_now)
                world.build_joint(key, parent, frame, lo, hi, 0.0, [(a, 0.0)], linear)

            def pull(key, t):
                if state[key] == "anim":
                    return 1.0
                return plan.blend_strength(t, a, b, blend_in, blend_out, (
                    0.0 if state[key] == "free" else strength[key]))
            # Bullet steps only with the viewport's refresh on (trap 266) and Cached Playback off
            # (`sim.Scene` switches it off while it stands)
            cmds.refresh(suspend=False)
            try:
                cmds.currentTime(a)          # the solver initialises on a time change at its start
                bodies = {a: world.read(), a - 1: target[a - 1]}
                done, drift, aims = [], {}, {}
                for t in range(a + 1, b + 1):
                    kicks = {}
                    for key in keys:         # each body pulled toward where the take has it at t
                        # its axis only: a capsule is round about it, the bake keeps the take's
                        # roll, and spinning it up to the take's roll (80 deg a frame) let Bullet's
                        # gyroscopic term swing the axis 28 deg off
                        want = target[t][key]
                        p_k = pull(key, t)
                        if p_k < 1.0:        # a spring with weight: it lags, swings and sags
                            aims.pop(key, None)
                            kicks[key] = plan.follow(
                                bodies[t - 2][key], bodies[t - 1][key], target[t - 2][key],
                                target[t - 1][key], want, fps, p_k, mass[key], inertia[key])
                            continue
                        if key in drift:
                            want = plan.aimed(want, drift[key], DRIFT_GAIN)
                        aims[key] = want
                        kicks[key] = plan.servo(bodies[t - 2][key], bodies[t - 1][key], want,
                                                fps, 1.0, mass[key], inertia[key])
                    for hit in hits:
                        if hit["at"] == t:
                            j, point = plan.impulse(mass[hit["key"]], hit["speed"], hit["tip"],
                                                    hit["direction"], bodies[t - 1][hit["key"]])
                            sj, st = kicks[hit["key"]]
                            kicks[hit["key"]] = (sj + j, st + plan.hit_torque(point, j))
                            done.append(hit)
                    for key, (j, torque) in kicks.items():
                        if np.any(j) or np.any(torque):
                            world.kick(key, j, torque)
                    cmds.currentTime(t)
                    world.clear_impulses()
                    bodies[t] = world.read()
                    struck = set(h["key"] for h in hits if h["at"] == t)
                    for key in keys:         # how far a held body's step landed off its aim
                        drift.pop(key, None)
                        if key in aims and key not in struck:
                            drift[key] = plan.world_turn(aims[key], bodies[t][key])
                    if progress is not None and not progress(t):
                        raise rd.Refused("cancelled - nothing changed")
            finally:
                cmds.refresh(suspend=True)
        finally:
            world.delete()
    del bodies[a - 1]
    return {"bones": bones, "parents": parents, "rider_of": rider_of, "takes": takes,
            "worlds": worlds, "target": target, "bodies": bodies, "state": state,
            "strength": strength, "floor": floor, "impulses": done, "impulse_notes": notes,
            "radius": radius, "axis": axis, "mass": mass}


def _down(parents):
    """The bones parents first."""
    out, seen = [], set()

    def visit(leaf):
        if leaf in seen:
            return
        seen.add(leaf)
        parent = parents.get(leaf)
        if parent in parents:
            visit(parent)
        out.append(leaf)
    for leaf in parents:
        visit(leaf)
    return out


def frame_worlds(run, t):
    """{bone: 4x4} at frame `t`, and {bone: drive 4x4}: each bone turned by its body's change
    (`plan.carried_by`), laid down the skeleton from the bone above it by the take's own offset - so the
    bones keep the take's lengths and stay joined where a body's joint cannot follow the take (a
    clavicle riding the chest). A bone whose parent rides no body (the pelvis) takes its carried
    place; a bone riding none, or riding an Anim body, plays the take."""
    parents, rider_of = run["parents"], run["rider_of"]
    take, target, now = run["worlds"][t], run["target"][t], run["bodies"][t]
    out = {}
    for leaf in _down(parents):
        m = plan.rigid(take[leaf])
        body = rider_of.get(leaf)
        parent = parents.get(leaf)
        if body is None or run["state"].get(body) == "anim":
            out[leaf] = m
            continue
        turned = plan.carried_by(m, target[body], plan.swung(target[body], now[body]))
        if parent in out and rider_of.get(parent) is not None:
            p_take = plan.rigid(take[parent])
            offset = (plan.pos(m) - plan.pos(p_take)) @ plan.rot(p_take).T
            place = plan.pos(out[parent]) + offset @ plan.rot(out[parent])
            turned = plan.frame(plan.rot(turned), place)
        out[leaf] = turned
    drives = {}
    for leaf, bone in run["takes"][t].items():
        body = rider_of.get(leaf)
        if "drive" not in bone or body is None or leaf not in out:
            continue
        if run["state"].get(body) == "anim":
            drives[leaf] = plan.rigid(plan.mat(bone["drive"]))
        else:
            d = plan.carried_by(plan.rigid(plan.mat(bone["drive"])), target[body],
                                plan.swung(target[body], now[body]))
            drives[leaf] = plan.frame(plan.rot(d), plan.pos(out[leaf]))
    return out, drives


def card(ref, run, a, b):
    """(header, frames): the blended take as a Pose Library animation card of the rig's own
    skeleton (`frame_worlds` on every frame)."""
    from maya_poselib import animdata
    bones, rider_of = run["bones"], run["rider_of"]
    order = list(bones)
    world_rows, drive_rows = [], {}
    for t in range(a, b + 1):
        worlds, drives = frame_worlds(run, t)
        row = []
        for leaf in order:
            row.extend(animdata.encode(plan.flat(worlds[leaf])))
        world_rows.append(row)
        for leaf, m in drives.items():
            drive_rows.setdefault(leaf, []).append(animdata.encode(plan.flat(m)))
    drive_rows = dict((leaf, rows) for leaf, rows in drive_rows.items() if len(rows) == b - a + 1)
    frames = {"bones": order, "world": world_rows, "drive": drive_rows}
    return rd.card_header(ref, bones, rider_of, a, b, "Ragdoll Blend"), frames


def layer_name(a):
    return LAYER_PREFIX + ("%d" % a).replace("-", "m")


def make_layer(a, b, ref, blend_out):
    """`RagdollBlend_<a>` made afresh: override, 0 before the span, 1 over it, easing to 0 over the
    last `blend_out` frames."""
    name = layer_name(a)
    if rd.ours(name):
        cmds.delete(name)
    layer = cmds.animLayer(name, override=True)
    cmds.addAttr(layer, longName=rd.LAYER_MARKER, dataType="string")
    cmds.setAttr(layer + "." + rd.LAYER_MARKER,
                 json.dumps({"rig": ref.namespace, "frame": a, "mode": "blend"}), type="string")
    for t, w in plan.layer_weight_keys(a, b, blend_out):
        cmds.setKeyframe(layer, attribute="weight", time=t, value=w,
                         inTangentType="linear", outTangentType="linear")
    cmds.keyTangent(layer, attribute="weight", time=(a - 1, a - 1), outTangentType="step")
    return layer


def _zones_line(state):
    parts = []
    for name in plan.STATES:
        zones = [plan.ZONE_LABEL[z] for z in plan.ZONES
                 if any(state[k] == name for k in state if plan.zone_of(k) == z)]
        if zones:
            parts.append("%s: %s" % (plan.STATE_LABEL[name], ", ".join(zones)))
    return "; ".join(parts)


def blend(selection=None, given=None, progress=None):
    """(ok, line): the press."""
    s = rd.settings(given)
    if selection is None:
        selection = cmds.ls(selection=True, long=True) or []
    ref = rd._ref(selection)
    a, b = plan.span(rd._highlight(), cmds.currentTime(query=True), s["length"])
    if b - a < 2:
        raise rd.Refused(rd.SHORT % (a, b))
    colliders = rd._colliders(selection, ref)
    run = simulate(ref, a, b, s, colliders, progress)
    header, frames = card(ref, run, a, b)
    LAST.update(run=run, header=header, frames=frames, a=a, b=b)
    from maya_poselib import animapply, animdata
    options = animdata.Options(mode="replace", at_current=False, keys="every", in_place=False)
    state = rd._layer_selection()
    cmds.undoInfo(openChunk=True, chunkName=UNDO_CHUNK)
    try:
        rd._widen(b)
        if s["layer"] == "new":
            layer = make_layer(a, b, ref, float(s["blend_out"]))
            rd._select_layers([layer])
        else:
            layer = None
            rd._select_layers([])
        ok, text = animapply._press_refs(header, frames, [ref], options=options)
    finally:
        rd._restore_layers(state)
        cmds.undoInfo(closeChunk=True)
    if not ok:
        return False, text
    where = ("on %s" % layer) if layer else "on the base layer"
    line = "%s blends with physics from %d to %d, %s - %s" % (ref.label, a, b, where,
                                                              _zones_line(run["state"]))
    if colliders:
        line += " | %d collider%s" % (len(colliders), "" if len(colliders) == 1 else "s")
    hit_line = impulse.summary(run.get("impulses"))
    if hit_line:
        line += " | " + hit_line
    if run.get("impulse_notes"):
        line += " | " + "; ".join(run["impulse_notes"])
    if not run.get("impulses") and "free" not in set(run["state"].values()):
        line += (" | no impulse and no Free zone: Follow only adds weight and lag - "
                 "+ Impulse for a hit, Free for a limp part, a lower strength for more")
    return True, line
