"""verify_walk_weapon_overlap.py - Weapon overlap, in mayapy standalone (never the animator's scene).

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/walkparam/verify_walk_weapon_overlap.py

Three phases, on a COPY of the animator's walks folder (their own cycle and the Pose Library card
LongSword_Idle_3P, a two-handed grip - the scene on port 7004 on 2026-10-30):

  reading  a Manny UE5 skeleton with a Long Sword equipped in its right hand: what scene.weapons_in_hands
           hands the model - the grip the weapon's own origin in that hand, the tip the blade's own tip,
           both against the scene's own matrices and the mesh's farthest vertex; a weapon taken off the
           hand is no longer in a hand.
  keys     the whole press (scene.apply) at 0 ms and at a lag, the keys read back off the scene frame by
           frame: the blade points at its own tip that many frames earlier, the grip is held, the blade
           keeps its length, the cycle is still a loop, the hand turned with it, weapon_r stands on the
           weapon's socket (so the exported bone carries the lag), the status line says it, and 0 ms is
           the walk with no weapon at all.
  model    the same weapon on the model under the animator's own cycle and their two-handed card: the aim
           exact, the grip held, both hands carried with their hold kept, a lead the other way, Whip on
           top of it, and Balance seeing it.

Phases can be named on the command line (`reading`, `keys`, `model`); the default runs all three.
"""
import math
import os
import shutil
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
MINE = os.environ.get("WALKS_HOME", "C:/Users/MY PC/Documents/maya/SkeldarWalks")
LIBRARY = os.environ.get("POSE_LIBRARY", "C:/Users/MY PC/Documents/maya/scripts/SkeldarAnim/poses")
WALK = os.environ.get("WEAPON_WALK", "own:8e4ef9f3703a44a3")
CARD = os.environ.get("WEAPON_CARD", "LongSword_Idle_3P.pose")
MS = float(os.environ.get("WEAPON_MS", "150"))      # the lag the gates measure at
BASE = {"changes": {"tempo": ["ratio", 0.8709677419354839]}, "pins": ["tempo"], "in_place": 1.0,
        "physics": True}
PHASES = tuple(a for a in sys.argv[1:] if not a.startswith("-")) or ("reading", "keys", "model")

import maya.standalone                                       # noqa: E402
maya.standalone.initialize()
import maya.cmds as cmds                                     # noqa: E402

sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))         # the repository's plugin, never the installed copy
from maya_walk import scene as sw                             # noqa: E402
from maya_walk import cards as wcards                         # noqa: E402
from maya_walk import pose as wp                              # noqa: E402
from maya_scenesetup import catalog, character, equip, bonedrive, weaponspace   # noqa: E402
from maya_scenesetup import aim as weaponaim                   # noqa: E402

wm, wt, gait = sw.wm, sw.wt, sw.gait
FAILED, COUNT = [], [0]


def gate(ok, text):
    COUNT[0] += 1
    print("gate %2d %s  %s" % (COUNT[0], "ok  " if ok else "FAIL", text))
    sys.stdout.flush()
    if not ok:
        FAILED.append(COUNT[0])


TEMP = tempfile.mkdtemp(prefix="weapon_overlap_")
COPY = os.path.join(TEMP, "SkeldarWalks")
shutil.copytree(MINE, COPY)
sw.WALKS = COPY
HAS_CARD = bool(CARD) and os.path.isdir(os.path.join(LIBRARY, CARD))
if HAS_CARD:                     # the press reads the card through the library's own root
    cmds.optionVar(stringValue=("skeldarPoseLibraryRoot", LIBRARY))
else:
    print("note: %s is not in %s - the gates run with no pose (straight arms)" % (CARD, LIBRARY))
if not sw.walk_exists(WALK):
    names = sw.walk_names()
    if not names:
        print("no walk to read in %s - nothing to verify" % MINE)
        raise SystemExit(1)
    WALK = names[0]
    print("note: %s is not in the folder - using %s" % (os.environ.get("WEAPON_WALK", WALK), WALK))


# ------------------------------------------------------------------ the scene

def world(node, frame=None):
    """A node's world matrix (4, 4), Maya's own row-vector order, at `frame` (a real time change: the
    weapon's space is parent-constrained, trap 69)."""
    if frame is not None:
        cmds.currentTime(frame, update=True)
    return np.array(cmds.xform(node, query=True, worldSpace=True, matrix=True), float).reshape(4, 4)


def place(local, m):
    return np.asarray(local, float) @ m[:3, :3] + m[3, :3]


def path_of(node, start, frames):
    """A node's world matrices over the take: (frames + 1, 4, 4)."""
    return np.array([world(node, start + f) for f in range(frames + 1)])


def farthest_vertex(mesh):
    """The mesh's vertex farthest from its own origin, in its own frame - the blade's tip, measured rather
    than read off the extents (what the reading's tip is checked against)."""
    import maya.api.OpenMaya as om
    sel = om.MSelectionList()
    sel.add(mesh)
    dag = sel.getDagPath(0)
    inverse = dag.inclusiveMatrix().inverse()
    best, far = None, -1.0
    for point in om.MFnMesh(dag.extendToShape()).getPoints(om.MSpace.kWorld):
        local = point * inverse
        d = math.sqrt(local[0] ** 2 + local[1] ** 2 + local[2] ** 2)
        if d > far:
            best, far = np.array([local[0], local[1], local[2]]), d
    return best


def add_walker():
    """A Manny UE5 skeleton with a Long Sword in its right hand: (root, the weapon's path)."""
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    entry = catalog.character_for("Manny", "skeleton")
    character.add_character(entry)
    root = [p for p in cmds.ls(type="joint", long=True) if p.rsplit("|", 1)[-1] == "root"][0]
    said = equip.to_hand(root, "R", catalog.by_key("LongSword_02"))
    marked = [n for n in cmds.ls(transforms=True, long=True)
              if cmds.attributeQuery(bonedrive.MARKER, node=n, exists=True)]
    if not marked:
        raise RuntimeError("no weapon in the hand: %s" % said)
    return root, marked[0]


def hand_of(root, side):
    leaf = sw.WEAPON_HANDS[side]
    return [p for p in (cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True) or [])
            if p.rsplit("|", 1)[-1].split(":")[-1] == leaf][0]


# ------------------------------------------------------------------ the phases

def params(ms, exact=True):
    """The animator's own parameters with the lag `ms` on top. `exact`: Whip and In place off as well - the
    springs move the hands after the swing (Arm overlap's gates do the same), and In place takes the root's
    own per-frame shift out AFTER the arms pass, so the aim is right in the travelling world it was computed
    in and a gate against the in-place path reads ~1.5 cm at the tip."""
    out = sw.normal_params(dict(BASE, pose=1.0 if HAS_CARD else 0.0))
    changes = dict(out["changes"])
    pins = set(out["pins"])
    if ms:
        changes["weapon_overlap"] = ["offset", ms]
        pins.add("weapon_overlap")
    if exact:
        changes["whip"] = ["offset", -gait.P["whip"].default]
        pins.add("whip")
        out["in_place"] = 0.0
    out["changes"], out["pins"] = changes, sorted(pins)
    return out


def phase_reading():
    print("\n-- reading: what the scene hands the model")
    root, weapon = add_walker()
    hand = hand_of(root, "r")
    held = sw.weapons_in_hands(root)
    gate(sorted(held) == ["r"], "the weapon in the right hand is the one read: %s" % sorted(held))
    rel = world(weapon) @ np.linalg.inv(world(hand))
    grip_err = float(np.abs(np.array(held["r"]["grip"]) - rel[3, :3]).max())
    gate(grip_err < 1e-9, "the grip is the weapon's own origin in the hand: %.2e cm" % grip_err)
    tip_err = float(np.abs(np.array(held["r"]["tip"]) - place(farthest_vertex(weapon), rel)).max())
    gate(tip_err < 1e-6, "the tip is the mesh's farthest vertex: %.2e cm" % tip_err)
    blade = float(np.linalg.norm(np.array(held["r"]["tip"]) - np.array(held["r"]["grip"])))
    gate(abs(blade - 115.925) < 0.01, "the blade is the Long Sword's own 115.9 cm: %.3f" % blade)
    equip.take_off(root, "R")
    gate(sw.weapons_in_hands(root) == {}, "a weapon taken off the hand is in no hand")
    return held


def phase_keys(held):
    print("\n-- keys: the press, read back off the scene")
    root, weapon = add_walker()
    hand = hand_of(root, "r")
    bone = [p for p in (cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True) or [])
            if p.rsplit("|", 1)[-1].split(":")[-1] == "weapon_r"][0]
    grip_p = np.array(sw.weapons_in_hands(root)["r"]["grip"])
    tip_p = np.array(sw.weapons_in_hands(root)["r"]["tip"])

    quiet, info, line = sw.apply(root, WALK, params=params(0.0), pose_card=CARD if HAS_CARD else None)
    start, frames = sw.memo_of(root)["start"], quiet.frames
    was_weapon = path_of(weapon, start, frames)
    was_hand = path_of(hand, start, frames)
    socket_was = world(weapon, start) @ np.linalg.inv(world(bone, start))

    got, info, line = sw.apply(root, WALK, params=params(MS), pose_card=CARD if HAS_CARD else None)
    lag = float(got.info["knobs"]["weapon_overlap_r"])
    fps = sw.output_fps()
    gate(abs(lag - MS * fps / 1000.0) < 1e-6,
         "%.0f ms is %.3f frames at %.0f fps: %.3f" % (MS, MS * fps / 1000.0, fps, lag))
    now_weapon = path_of(weapon, start, frames)
    now_hand = path_of(hand, start, frames)

    #  the weapon rides the hand, so the blade's aim is read off the hand's own path
    o_was = np.array([place(grip_p, m) for m in was_hand])
    t_was = np.array([place(tip_p, m) for m in was_hand])
    o_now = np.array([place(grip_p, m) for m in now_hand])
    t_now = np.array([place(tip_p, m) for m in now_hand])
    want = wm.shifted_points(t_was, lag)
    worst_aim, worst_grip, worst_len, moved = 0.0, 0.0, 0.0, 0.0
    for f in range(frames + 1):
        d = wm._unit(t_now[f] - o_now[f])
        asked = wm._unit(want[f] - o_was[f])
        worst_aim = max(worst_aim, math.degrees(math.acos(min(1.0, abs(float(np.dot(d, asked)))))))
        worst_grip = max(worst_grip, float(np.linalg.norm(o_now[f] - o_was[f])))
        worst_len = max(worst_len, abs(float(np.linalg.norm(t_now[f] - o_now[f]))
                                       - float(np.linalg.norm(t_was[f] - o_was[f]))))
        moved = max(moved, float(np.linalg.norm(t_now[f] - t_was[f])))
    gate(worst_aim < 0.05, "the blade points at its own tip %.2f frames earlier: %.4f deg" % (lag, worst_aim))
    gate(worst_grip < 0.05, "the grip is held: %.4f cm" % worst_grip)
    gate(worst_len < 0.05, "the blade keeps its length: %.4f cm" % worst_len)
    gate(moved > 2.0, "the tip really trails: %.2f cm" % moved)
    #  the sword the animator SEES is what swings: its own mesh's tip, and it is the tip the gates measure
    mesh_tip = weaponaim.tip_offset(*weaponaim.local_extents(weapon))
    was_mesh = np.array([place(mesh_tip, m) for m in was_weapon])
    now_mesh = np.array([place(mesh_tip, m) for m in now_weapon])
    swept = float(np.abs(now_mesh - was_mesh).max())
    same = float(np.abs(now_mesh - t_now).max())
    gate(swept > 1.0 and same < 0.01,
         "the sword mesh's own tip swings %.2f cm and is the tip measured (%.4f cm apart)" % (swept, same))
    turned = max(float(np.linalg.norm(wm.log_rot(was_hand[f][:3, :3].T @ now_hand[f][:3, :3])))
                 for f in range(frames + 1))
    gate(math.degrees(turned) > 0.5, "the hand turned with the weapon: %.2f deg" % math.degrees(turned))
    travel = was_weapon[frames, 3, :3] - was_weapon[0, 3, :3]
    loop = float(np.abs((now_weapon[frames, 3, :3] - now_weapon[0, 3, :3]) - travel).max())
    gate(loop < 0.01, "the cycle is still a loop: %.4f cm" % loop)
    socket_now = world(weapon, start) @ np.linalg.inv(world(bone, start))
    gate(float(np.abs(socket_now - socket_was).max()) < 1e-4,
         "weapon_r still stands on the weapon's socket: %.2e" % float(np.abs(socket_now - socket_was).max()))
    said = [p for p in line.split(" | ") if "weapon trails" in p]
    gate(bool(said) and "cm behind" in said[0], "the line says it: %s" % (said[0] if said else line))

    #  the animator's own parameters, Whip and In place as they have them: the trail is still there and the
    #  grip still held, and the aim is measured in the travelling world the swing was computed in (In place
    #  takes the root's own shift out afterwards: ~1.5 cm at the tip of a 116 cm blade)
    sw.apply(root, WALK, params=params(0.0, exact=False), pose_card=CARD if HAS_CARD else None)
    real_was = path_of(hand, start, frames)
    sw.apply(root, WALK, params=params(MS, exact=False), pose_card=CARD if HAS_CARD else None)
    real_now = path_of(hand, start, frames)
    r_o_was = np.array([place(grip_p, m) for m in real_was])
    r_t_was = np.array([place(tip_p, m) for m in real_was])
    r_o_now = np.array([place(grip_p, m) for m in real_now])
    r_t_now = np.array([place(tip_p, m) for m in real_now])
    r_want = wm.shifted_points(r_t_was, lag)
    r_aim = max(math.degrees(math.acos(min(1.0, abs(float(np.dot(wm._unit(r_t_now[f] - r_o_now[f]),
                                                                 wm._unit(r_want[f] - r_o_was[f])))))))
                for f in range(frames + 1))
    r_grip = max(float(np.linalg.norm(r_o_now[f] - r_o_was[f])) for f in range(frames + 1))
    r_moved = max(float(np.linalg.norm(r_t_now[f] - r_t_was[f])) for f in range(frames + 1))
    gate(r_moved > 2.0 and r_aim < 2.0 and r_grip < 2.0,
         "with their own Whip and In place: the tip trails %.1f cm, the aim %.2f deg, the grip %.2f cm"
         % (r_moved, r_aim, r_grip))

    #  0 ms is the walk with no weapon at all
    sw.apply(root, WALK, params=params(0.0), pose_card=CARD if HAS_CARD else None)
    again = path_of(weapon, start, frames)
    gate(float(np.abs(again - was_weapon).max()) < 1e-6,
         "0 ms is the walk it was: %.2e" % float(np.abs(again - was_weapon).max()))
    #  ...and a lag with nothing in the hands changes nothing and says so
    equip.take_off(root, "R")
    bare = sw.apply(root, WALK, params=params(0.0), pose_card=CARD if HAS_CARD else None)[0]
    bare_hand = path_of(hand, start, frames)
    said = sw.apply(root, WALK, params=params(MS), pose_card=CARD if HAS_CARD else None)[2]
    gate(float(np.abs(path_of(hand, start, frames) - bare_hand).max()) < 1e-6,
         "with no weapon in the hands the lag changes nothing")
    gate("no weapon in the hands" in said, "and the line says so: %s" % said.split(" | ")[-1])


def phase_model(held):
    print("\n-- model: the animator's own cycle under their two-handed card")
    cmds.file(new=True, force=True)
    walk, statics = sw.load_walk(WALK, sw.normal_params(BASE)["clean"])[:2]
    pose = None
    if CARD and os.path.isdir(os.path.join(LIBRARY, CARD)):
        bones = wcards.read_card(os.path.join(LIBRARY, CARD))[1]
        pose = wp.filtered(wp.prepare(walk, statics, bones, wm, wt), sw.ALL_PARTS)
    base_knobs = sw.params_knobs(walk, sw.normal_params(dict(BASE, pose=1.0 if pose else 0.0)))[0]
    #  the geometry is measured in the travelling cycle the swing is computed in: In place takes the root's
    #  own per-frame shift out after the arms pass (and the springs move the hands after it - Whip's own gate
    #  below puts it back)
    base_knobs = dict(base_knobs, in_place=0.0)

    def run(**over):
        ks = dict(base_knobs)
        for name, value in over.items():          # a sided knob on both sides too (trap 317)
            ks[name] = value
            if name in wm.SIDED:
                ks[name + "_l"] = ks[name + "_r"] = value
        return walk.evaluate(ks, pose, weapons=held)

    lag = MS * walk.fps / 1000.0
    chains = walk._arm_chains()
    hand_r, hand_l = chains["r"][-1], chains["l"][-1]
    quiet = run(weapon_overlap=0.0, arm_drag=0.0)
    swung = run(weapon_overlap=lag, arm_drag=0.0)
    n = quiet.frames
    grip_p, tip_p = np.array(held["r"]["grip"]), np.array(held["r"]["tip"])
    was, now = np.array(quiet.worlds[hand_r]), np.array(swung.worlds[hand_r])
    o_was = np.array([place(grip_p, m) for m in was])
    t_was = np.array([place(tip_p, m) for m in was])
    o_now = np.array([place(grip_p, m) for m in now])
    t_now = np.array([place(tip_p, m) for m in now])
    want = wm.shifted_points(t_was, lag)
    worst_aim = worst_grip = worst_len = moved = 0.0
    for f in range(n + 1):
        d, asked = wm._unit(t_now[f] - o_now[f]), wm._unit(want[f] - o_was[f])
        worst_aim = max(worst_aim, math.degrees(math.acos(min(1.0, abs(float(np.dot(d, asked)))))))
        worst_grip = max(worst_grip, float(np.linalg.norm(o_now[f] - o_was[f])))
        worst_len = max(worst_len, abs(float(np.linalg.norm(t_now[f] - o_now[f]))
                                       - float(np.linalg.norm(t_was[f] - o_was[f]))))
        moved = max(moved, float(np.linalg.norm(t_now[f] - t_was[f])))
    gate(worst_aim < 0.05, "the blade aims at its own tip %.2f frames earlier: %.5f deg" % (lag, worst_aim))
    gate(worst_grip < 0.05, "the grip is held: %.4f cm" % worst_grip)
    gate(worst_len < 0.05, "the blade keeps its length: %.4f cm" % worst_len)
    gate(moved > 2.0, "the tip really trails: %.2f cm" % moved)
    said = swung.info["arms"]["overlap"]
    gate(abs(said["weapon"] - lag) < 1e-9 and said["weapon_sides"] == ["r"],
         "the info names the lag and the side: %.3f fr, %s" % (said["weapon"], said["weapon_sides"]))

    if pose is not None and said["grip"]:
        weapon_at = lambda r, f: wm.matrix(np.array(r.worlds[hand_r, f])[:3, :3],
                                           place(grip_p, np.array(r.worlds[hand_r, f])))
        worst_hold, carried = 0.0, 0.0
        for f in range(n + 1):
            a = np.array(quiet.worlds[hand_l, f]) @ np.linalg.inv(weapon_at(quiet, f))
            b = np.array(swung.worlds[hand_l, f]) @ np.linalg.inv(weapon_at(swung, f))
            worst_hold = max(worst_hold, float(np.abs(a - b).max()))
            carried = max(carried, float(np.linalg.norm(swung.worlds[hand_l, f, 3, :3]
                                                        - quiet.worlds[hand_l, f, 3, :3])))
        gate(worst_hold < 1e-4, "the two-handed hold is kept: %.2e" % worst_hold)
        gate(carried > 0.5, "the other hand is carried with the weapon: %.2f cm" % carried)
    else:
        print("note: the card holds no two-handed grip - the hold gates are skipped")

    zero = run(weapon_overlap=0.0, arm_drag=0.0)
    gate(np.array_equal(zero.worlds, quiet.worlds), "0 frames is the cycle matrix for matrix")
    lead = run(weapon_overlap=-lag, arm_drag=0.0)
    apart = float(np.abs(np.array([place(tip_p, m) for m in np.array(lead.worlds[hand_r])]) - t_now).max())
    gate(apart > 2.0, "a lead swings it the other way: %.2f cm apart" % apart)
    whip_quiet = run(weapon_overlap=0.0, arm_drag=2.0)
    whip_swung = run(weapon_overlap=lag, arm_drag=2.0)
    whipped = float(np.abs(np.array(whip_swung.worlds[hand_r]) - np.array(whip_quiet.worlds[hand_r])).max())
    gate(whipped > 0.1, "Whip takes the swung arm as its target: %.3f" % whipped)
    bal_quiet = run(weapon_overlap=0.0, arm_drag=0.0, balance=1.0)
    bal_swung = run(weapon_overlap=lag, arm_drag=0.0, balance=1.0)
    gate(float(bal_quiet.info["balance"]["carry"]) != float(bal_swung.info["balance"]["carry"]),
         "Balance sees it: carry %.4f against %.4f" % (float(bal_swung.info["balance"]["carry"]),
                                                       float(bal_quiet.info["balance"]["carry"])))


held = None
try:
    if "reading" in PHASES or "keys" in PHASES or "model" in PHASES:
        held = phase_reading() if "reading" in PHASES else None
    if held is None and ("keys" in PHASES or "model" in PHASES):
        held = phase_reading()          # the model and the keys both want a real reading
    if "keys" in PHASES:
        phase_keys(held)
    if "model" in PHASES:
        phase_model(held)
finally:
    print("\n%d of %d gates failed%s" % (len(FAILED), COUNT[0], (": " + ", ".join(map(str, FAILED))) if FAILED else ""))
    shutil.rmtree(TEMP, ignore_errors=True)
