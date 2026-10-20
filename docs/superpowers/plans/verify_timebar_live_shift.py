"""verify_timebar_live_shift.py - the Time Bar's live key drag moved as ONE shift a step
(2026-10-20, «ключи сильно задерживаются за курсором»), mayapy standalone.

Every scenario is dragged twice from the same saved scene: through the shift
(`keyframe -relative -option over`, one command a step) and through the per-key
writes the drag used before (`_shift_of` answering None), and every key of every
curve is compared - time, value, breakdown, both tangent types, angles, weights,
lock. The per-key road is the reference: it shipped and was verified live.
Also: given up = the curves as they were; one undo after a release = as they were;
the cost of a step on both roads.

    mayapy docs/superpowers/plans/verify_timebar_live_shift.py
"""
import os
import random
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.environ.get("TIMEBAR_PLUGIN") or os.path.normpath(
    os.path.join(HERE, "..", "..", "..", "SkeldarAnim"))
sys.path.insert(0, PLUGIN)

import maya.standalone                                       # noqa: E402
maya.standalone.initialize()
import maya.cmds as cmds                                     # noqa: E402

from maya_timebar import scene                               # noqa: E402

FAILED = []


def gate(ok, text):
    print("%s %s" % ("PASS" if ok else "FAIL", text))
    if not ok:
        FAILED.append(text)


def build(path):
    cmds.file(new=True, force=True)
    cmds.playbackOptions(edit=True, animationStartTime=0, animationEndTime=90,
                         minTime=0, maxTime=90)
    rnd = random.Random(11)
    dense = cmds.createNode("transform", name="dense")
    for attr in ("tx", "ty", "rz"):
        for t in range(0, 81):
            cmds.setKeyframe(dense, attribute=attr, time=t, value=rnd.uniform(-5, 5))
    curve = cmds.listConnections(dense + ".tx", source=True)[0]
    for t, itt, ott in ((21, "linear", "step"), (24, "flat", "flat"), (28, "spline", "linear"),
                        (40, "clamped", "stepnext"), (5, "linear", "linear")):
        cmds.keyTangent(curve, edit=True, time=(t, t), inTangentType=itt, outTangentType=ott)
    cmds.keyTangent(curve, edit=True, time=(30, 30), lock=False)
    cmds.keyTangent(curve, edit=True, time=(30, 30), inTangentType="fixed", outTangentType="fixed",
                    inAngle=33.0, outAngle=-12.0)
    cmds.keyframe(curve, edit=True, time=(26, 26), breakdown=True)
    cmds.keyframe(curve, edit=True, time=(45, 45), breakdown=True)
    sparse = cmds.createNode("transform", name="sparse")
    for t in (0, 7, 15, 22, 30, 41, 55, 70):
        cmds.setKeyframe(sparse, attribute="tx", time=t, value=rnd.uniform(-5, 5))
        cmds.setKeyframe(sparse, attribute="ry", time=t, value=rnd.uniform(-90, 90))
    weighted = cmds.listConnections(sparse + ".ry", source=True)[0]
    cmds.keyTangent(weighted, edit=True, weightedTangents=True)
    cmds.keyTangent(weighted, edit=True, time=(22, 22), lock=False)
    cmds.keyTangent(weighted, edit=True, time=(22, 22), inTangentType="fixed",
                    outTangentType="fixed", inAngle=20.0, outAngle=40.0, inWeight=3.0, outWeight=7.5)
    frac = cmds.createNode("transform", name="frac")
    for t in (3, 10.5, 21.25, 27, 33.75, 50):
        cmds.setKeyframe(frac, attribute="tz", time=t, value=rnd.uniform(-5, 5))
    lone = cmds.createNode("transform", name="lone")
    cmds.setKeyframe(lone, attribute="sx", time=25, value=2.0)
    outside = cmds.createNode("transform", name="outside")
    for t in (0, 60, 80):
        cmds.setKeyframe(outside, attribute="tx", time=t, value=float(t))
    cmds.currentTime(12)
    cmds.file(rename=path)
    cmds.file(save=True, type="mayaAscii", force=True)


def snap():
    out = {}
    for curve in sorted(cmds.ls(type=("animCurveTL", "animCurveTA", "animCurveTU"))):
        times = cmds.keyframe(curve, q=True, timeChange=True) or []
        keys = []
        for t in times:
            span = (t, t)
            one = lambda **f: (cmds.keyTangent(curve, q=True, time=span, **f) or [None])[0]
            keys.append((round(t, 4),
                         round((cmds.keyframe(curve, q=True, time=span, valueChange=True) or [0])[0], 6),
                         bool(cmds.keyframe(curve, q=True, time=span, breakdown=True)),
                         one(inTangentType=True), one(outTangentType=True),
                         round(one(inAngle=True), 4), round(one(outAngle=True), 4),
                         round(one(inWeight=True), 4), round(one(outWeight=True), 4),
                         bool(one(lock=True))))
        out[curve] = keys
    return out


STEPPED = ("step", "stepnext")


def meaningful(key):
    """A key without the numbers Maya does not use: the angle and weight of a
    stepped side (a step's out angle reads whatever it was last computed as)."""
    t, v, bd, itt, ott, ia, oa, iw, ow, lock = key
    if itt in STEPPED:
        ia = iw = None
    if ott in STEPPED:
        oa = ow = None
    return (t, v, bd, itt, ott, ia, oa, iw, ow, lock)


def evaluated():
    """Every curve's value at quarter frames - what the animator sees."""
    out = {}
    for curve in sorted(cmds.ls(type=("animCurveTL", "animCurveTA", "animCurveTU"))):
        out[curve] = [round((cmds.keyframe(curve, q=True, eval=True, time=(f / 4.0, f / 4.0),
                                           valueChange=True) or [0])[0], 5)
                      for f in range(-20, 381)]
    return out


def differ(a, b):
    """The first few differences between two snaps (keys, then evaluation), as text."""
    out = []
    keys_a, eval_a = a
    keys_b, eval_b = b
    for curve in sorted(set(keys_a) | set(keys_b)):
        ka, kb = keys_a.get(curve), keys_b.get(curve)
        if ka is None or kb is None:
            out.append("%s only in one" % curve)
            continue
        ka, kb = [meaningful(k) for k in ka], [meaningful(k) for k in kb]
        if ka == kb:
            continue
        ta, tb = [k[0] for k in ka], [k[0] for k in kb]
        if ta != tb:
            out.append("%s times %s / %s" % (curve, sorted(set(ta) ^ set(tb))[:6], len(ta) - len(tb)))
            continue
        for x, y in zip(ka, kb):
            if x != y:
                out.append("%s %s / %s" % (curve, x, y))
                break
    for curve in sorted(set(eval_a) & set(eval_b)):
        worst = max(abs(x - y) for x, y in zip(eval_a[curve], eval_b[curve]))
        if worst > 1e-4:
            out.append("%s evaluates %.5f apart" % (curve, worst))
    return out[:6]


def state():
    return snap(), evaluated()


def maya_move(path, selection, target, select=("dense", "sparse", "frac", "lone", "outside")):
    """Maya's own move of the block, once, from the scene as it was: the keys standing
    where the block lands cut, breakdowns plain for the move, one keyframe -relative."""
    cmds.file(path, open=True, force=True)
    a, b = selection
    d = target[0] - a
    span = (a, b + 1 - 1e-3)
    for curve in cmds.keyframe(list(select), q=True, name=True) or []:
        times = cmds.keyframe(curve, q=True, timeChange=True) or []
        moved = [t for t in times if a - 1e-6 <= t < b + 1 - 1e-6]
        if not moved:
            continue
        landing = set(round(t + d, 4) for t in moved)
        cut = [t for t in times if t not in moved and round(t, 4) in landing]
        if cut:
            cmds.cutKey(curve, time=[(t, t) for t in cut], clear=True)
        bds = cmds.keyframe(curve, q=True, breakdown=True) or []
        if bds:
            cmds.keyframe(curve, edit=True, time=[(t, t) for t in bds], breakdown=False)
        cmds.keyframe(curve, edit=True, time=span, relative=True, timeChange=d, option="over")
        if bds:
            back = [t + d if a - 1e-6 <= t < b + 1 - 1e-6 else t for t in bds]
            cmds.keyframe(curve, edit=True, time=[(t, t) for t in back], breakdown=True)
    return state()


SCENARIOS = {
    # a block's body dragged right step by step, back, released
    "A block right": (((20, 35),), [(20 + i, 35 + i) for i in range(1, 13)] + [(25, 40)], (25, 40)),
    # dragged far left over the standing keys
    "B block left": (((20, 35),), [(20 - i, 35 - i) for i in range(1, 19)], (2, 17)),
    # stamped twice, then back over the copies
    "C stamps": (((20, 35),), [(23, 38), "S", (28, 43), "S", (18, 33), (22, 37)], (24, 39)),
    # a lone frame's keys dragged across thirty frames
    "E one frame": (((25, 25),), [(25 + i, 25 + i) for i in range(1, 31)], (55, 55)),
    # edge drags (a scale, key by key) mixed with moves
    "F scale and move": (((20, 35),), [(20, 40), (21, 36), (22, 37), (22, 45), (24, 39)], (24, 39)),
    # the block over a fractional key
    "G fractions": (((10, 22),), [(10 + i, 22 + i) for i in range(1, 9)], (18, 30)),
}


def drag(path, steps, release, per_key, select=("dense", "sparse", "frac", "lone", "outside")):
    cmds.file(path, open=True, force=True)
    cmds.select(list(select))
    real = getattr(scene, "_shift_of", None)
    if per_key:
        scene._shift_of = lambda *a: None
    try:
        selection = steps[0][0]
        began = scene.live_begin(selection)
        costs = []
        for step in steps[1]:
            if step == "S":
                scene.live_stamp()
                continue
            t0 = time.perf_counter()
            scene.live_to(step)
            costs.append((time.perf_counter() - t0) * 1000.0)
        scene.live_end(release)
    finally:
        if real is not None:
            scene._shift_of = real
    return began, state(), costs


# the scenarios a single move of the block reaches: Maya's own move is the truth
PURE = ("A block right", "B block left", "E one frame", "G fractions")


def main():
    path = os.path.join(tempfile.mkdtemp(prefix="skeldar_live_shift_"), "live_shift.ma")
    build(path)
    cmds.file(path, open=True, force=True)
    original = state()
    gate(len(original[0]) == 8, "the scene's curves: %d" % len(original[0]))
    for name, (sel, moves, release) in sorted(SCENARIOS.items()):
        steps = (sel, moves)
        ok1, shifted, cost_s = drag(path, steps, release, per_key=False)
        ok2, perkey, cost_k = drag(path, steps, release, per_key=True)
        gate(ok1 and ok2, "%s: a drag begins on both roads" % name)
        if name in PURE:
            truth = maya_move(path, sel[0], release)
            diff = differ(shifted, truth)
            gate(not diff, "%s: every key as Maya's own move puts it %s" % (name, diff))
            diff = differ(perkey, truth)
            print("INFO %s: the per-key road against Maya's move %s" % (name, diff or "the same"))
        diff = differ(shifted, perkey)
        gate(not diff, "%s: every key the same as the per-key road %s" % (name, diff))
        gate(shifted[0] != original[0], "%s: the keys did move" % name)
    # the release with no live step (move_keys) and a lane's move (lane_move): the same rule
    for name, (sel, release) in (("move_keys right over keys", ((20, 35), (27, 42))),
                                 ("move_keys left over keys", ((20, 35), (4, 19))),
                                 ("move_keys one frame", ((25, 25), (44, 44)))):
        cmds.file(path, open=True, force=True)
        cmds.select(["dense", "sparse", "frac", "lone", "outside"])
        scene.move_keys(sel, release)
        got = state()
        diff = differ(got, maya_move(path, sel, release))
        gate(not diff, "%s: every key as Maya's own move puts it %s" % (name, diff))
        cmds.file(path, open=True, force=True)
        cmds.select(["dense", "sparse", "frac", "lone", "outside"])
        scene.move_keys(sel, release)
        cmds.undo()
        diff = differ(state(), original)
        gate(not diff, "%s: one undo, the curves as they were %s" % (name, diff))
    _ok, scaled_live, _c = drag(path, (((20, 35),), [(20, 44)]), (20, 44), per_key=True)
    cmds.file(path, open=True, force=True)
    cmds.select(["dense", "sparse", "frac", "lone", "outside"])
    scene.move_keys((20, 35), (20, 44))
    diff = differ(state(), scaled_live)
    gate(not diff, "move_keys scaled: as the live drag scales %s" % diff)
    from maya_timebar import layerscene
    cmds.file(path, open=True, force=True)
    cmds.select(["dense", "sparse", "frac", "lone", "outside"])
    cmds.animLayer("Probe")                  # an empty layer: BaseAnimation is a lane now
    cmds.select(["dense", "sparse", "frac", "lone", "outside"])
    names = [layerscene.anim_layers()[-1]["name"]]
    ok, why = layerscene.lane_move(names, (20, 35), (27, 42))
    diff = differ(state(), maya_move(path, (20, 35), (27, 42)))
    gate(ok and not diff, "lane_move on %s: every key as Maya's own move puts it %s %s" % (names, why, diff))
    # given up = as it was, both roads
    for per_key in (False, True):
        cmds.file(path, open=True, force=True)
        cmds.select(["dense", "sparse", "frac", "lone", "outside"])
        real = getattr(scene, "_shift_of", None)
        if per_key:
            scene._shift_of = lambda *a: None
        scene.live_begin((20, 35))
        for i in range(1, 9):
            scene.live_to((20 + i, 35 + i))
        scene.live_stamp()
        scene.live_to((10, 25))
        scene.live_end(None)
        if real is not None:
            scene._shift_of = real
        diff = differ(state(), original)
        gate(not diff, "given up (%s): the curves as they were %s" % (
            "per key" if per_key else "shift", diff))
    # one undo after a release = as it was; redo = the move
    cmds.file(path, open=True, force=True)
    cmds.select(["dense", "sparse", "frac", "lone", "outside"])
    scene.live_begin((20, 35))
    for i in range(1, 7):
        scene.live_to((20 + i, 35 + i))
    scene.live_end((26, 41))
    moved = state()
    cmds.undo()
    diff = differ(state(), original)
    gate(not diff, "one undo after the release: the curves as they were %s" % diff)
    cmds.redo()
    diff = differ(state(), moved)
    gate(not diff, "redo: the move again %s" % diff)
    # the cost of a step on a dense block, both roads
    cmds.file(new=True, force=True)
    nodes = []
    for i in range(8):
        n = cmds.createNode("transform", name="c%d" % i)
        for attr in ("tx", "ty", "tz", "rx", "ry", "rz"):
            for t in range(0, 121):
                cmds.setKeyframe(n, attribute=attr, time=t, value=(t * (i + 1)) % 17)
        nodes.append(n)
    heavy = os.path.join(os.path.dirname(path), "heavy.ma")
    cmds.file(rename=heavy)
    cmds.file(save=True, type="mayaAscii", force=True)
    res = {}
    for per_key in (False, True):
        _ok, _s, costs = drag(heavy, (((20, 59),), [(20 + i, 59 + i) for i in range(1, 11)]),
                              (30, 69), per_key, select=nodes)
        res[per_key] = sorted(costs)[len(costs) // 2]
    print("COST a step, 48 curves x 40 keys: shift %.1f ms, per key %.1f ms" % (res[False], res[True]))
    gate(res[False] * 5 < res[True], "the shift costs a fifth of the per-key writes or less")
    print("")
    print("%d gate(s) failed" % len(FAILED))


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    print("CRASHED")
maya.standalone.uninitialize()
os._exit(0)
