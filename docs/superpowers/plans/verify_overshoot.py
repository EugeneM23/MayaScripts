"""Live proof of the overshoot tool. Send through the command port.

Everything happens in a SANDBOX: locators this script creates, animates,
measures and deletes. It never touches the animator's character, and it never
calls cmds.undo() -- the whole bridge script is one command, so an undo there
reverts a chunk of somebody else's work.

Design: docs/superpowers/specs/2026-08-20-overshoot-redesign-design.md

The two claims everything else hangs off:
  * the pose key does not move -- the tool only builds the stop after it;
  * the curve leaves the pose at the speed of the move that arrived.
"""

import sys

if r"C:/!!!Work/MayaScripts/SkeldarAnim" not in sys.path:
    sys.path.append(r"C:/!!!Work/MayaScripts/SkeldarAnim")

import maya.cmds as cmds

import maya_overshoot as mo

RESULTS = []
NOTES = []


def gate(name, ok, detail=""):
    RESULTS.append((bool(ok), name, detail))


def note(text):
    NOTES.append(text)


def quietly(fn, *args, **kw):
    """Teardown must not lose its remaining steps to one failing call."""
    try:
        return fn(*args, **kw)
    except Exception as exc:                                  # noqa: BLE001
        NOTES.append("teardown: %s: %s" % (getattr(fn, "__name__", fn), exc))


def deselect_keys():
    # selectKey(clear=True) needs something selected to work from (trap 42)
    quietly(cmds.selectKey, clear=True)


def sample(plug, first, last, step=1.0):
    out = []
    t = float(first)
    while t <= last + 1e-9:
        out.append((t, cmds.getAttr(plug, time=t)))
        t += step
    return out


def worst(a, b):
    return max(abs(x[1] - y[1]) for x, y in zip(a, b)) if a else 0.0


def slope_after(plug, t, step=0.1):
    return (cmds.getAttr(plug, time=t + step) - cmds.getAttr(plug, time=t)) / step


def turning_points(plug, first, last, step=0.25):
    pts = sample(plug, first, last, step)
    out = []
    for i in range(1, len(pts) - 1):
        before = pts[i][1] - pts[i - 1][1]
        after = pts[i + 1][1] - pts[i][1]
        if before == 0.0 and after == 0.0:
            continue
        if (before > 0) != (after > 0):
            out.append(pts[i])
    return out


# ---------------------------------------------------------------------------
#  sandbox
# ---------------------------------------------------------------------------

created = []
sel = cmds.ls(selection=True, long=True) or []
now = cmds.currentTime(query=True)
auto = cmds.autoKeyframe(query=True, state=True)
layers_before = set(cmds.ls(type="animLayer") or [])
picked = [l for l in layers_before if cmds.animLayer(l, query=True, selected=True)]

cmds.autoKeyframe(state=False)

try:
    loc = cmds.spaceLocator(name="overshootProof#")[0]
    created.append(loc)

    #  tx  a move that stops on the last key   0 -> 100 over 10 frames
    #  ty  a move into a hold                  0 -> 50 at 20, held at 30
    #  tz  a move that carries on              0 -> 50 at 20 -> 120 at 40
    #  ry  60 degrees over the same 10 frames
    for attr, keys in (
            ("translateX", ((10, 0.0), (20, 100.0))),
            ("translateY", ((10, 0.0), (20, 50.0), (30, 50.0))),
            ("translateZ", ((10, 0.0), (20, 50.0), (40, 120.0))),
            ("rotateY", ((10, 0.0), (20, 60.0))),
    ):
        for t, v in keys:
            cmds.setKeyframe(loc, attribute=attr, time=t, value=v)

    tx = "%s.translateX" % loc
    ty = "%s.translateY" % loc
    tz = "%s.translateZ" % loc
    ry = "%s.rotateY" % loc

    before_tx = sample(tx, 0, 60, 0.5)
    before_ty = sample(ty, 0, 60, 0.5)
    before_tz = sample(tz, 0, 60, 0.5)
    before_ry = sample(ry, 0, 60, 0.5)

    #  100 units over 10 frames is 10 a frame; Spring's entry constant turns
    #  that into the excursion the plan asks for
    speed = 10.0
    entry = mo.sine_entry_slope(3, 0.30)
    want_peak = speed * 12 / entry
    note("fps %s   move speed %.3f/frame   expected peak %+.4f"
         % (cmds.currentUnit(query=True, time=True), speed, want_peak))

    # ---------------------------------------------------------------- apply
    deselect_keys()
    cmds.selectKey(loc, attribute="translateX", time=(20, 20))
    cmds.selectKey(loc, attribute="translateY", time=(20, 20), add=True)
    cmds.selectKey(loc, attribute="translateZ", time=(20, 20), add=True)

    report = mo.overshoot_objects([loc], shape="Spring", do_pos=True,
                                  do_rot=False, strength_pos=1.0,
                                  frames_pos=12)
    note("report: " + report)

    layer = "%s_overshoot_pos" % loc.split("|")[-1]
    gate("0a the additive layer exists",
         cmds.animLayer(layer, query=True, exists=True), layer)
    gate("0b it is additive, not override",
         cmds.animLayer(layer, query=True, exists=True) and
         not cmds.animLayer(layer, query=True, override=True))

    # ------------------------------------------- 1  THE POSE DOES NOT MOVE
    at_pose = cmds.getAttr(tx, time=20)
    gate("1 the pose key keeps its value",
         abs(at_pose - 100.0) < 1e-6, "tx at 20 = %.9f" % at_pose)
    if abs(at_pose - 100.0) > 1.0:
        note("setKeyframe(animLayer=) is NOT writing offsets -- it landed the "
             "value absolutely; write through animLayer -findCurveForPlug")

    # ------------------------------- 2  it leaves at the speed of the move
    got = slope_after(tx, 20.0)
    gate("2 the curve leaves the pose at the speed of the move",
         abs(got - speed) < 0.25 * speed,
         "%.4f per frame, move was %.4f" % (got, speed))
    if abs(got) < 0.2 * speed:
        note("the pose key's out tangent came out flat -- the calibration in "
             "set_out_slope did not take")
    elif abs(got - 0.49 * speed) < 0.1 * speed:
        note("the out tangent fell back to linear (aimed at the crest), so "
             "the exact-slope path failed")

    # ------------------------------------------------- 3  the excursion
    peak = max(sample(tx, 20, 32, 0.25), key=lambda p: abs(p[1] - 100.0))
    gate("3a the peak is the speed times the window over the entry constant",
         abs(abs(peak[1] - 100.0) - want_peak) < 0.05 * want_peak,
         "peak %+.4f at frame %g, wanted %+.4f" % (peak[1] - 100.0, peak[0],
                                                   want_peak))
    gate("3b and it lands where the shape says (u0 = %.4f)"
         % mo.sine_first_extreme(3, 0.30),
         abs(peak[0] - 22.0) <= 0.75, "at frame %g" % peak[0])
    gate("3c the settle comes back to the pose exactly",
         abs(cmds.getAttr(tx, time=32) - 100.0) < 1e-6,
         "tx at 32 = %.9f" % cmds.getAttr(tx, time=32))

    turns = turning_points(tx, 20.5, 33)
    gate("3d there are as many turning points as swings",
         len(turns) == 3, "%s" % [(round(t, 2), round(v - 100.0, 3))
                                  for t, v in turns])

    # -------------------------------------- 4  nothing outside the window
    after_tx = sample(tx, 0, 60, 0.5)
    outside = [(a, b) for a, b in zip(before_tx, after_tx)
               if a[0] <= 20.0 or a[0] > 32.0]
    gate("4 the animation outside the window is untouched",
         worst([a for a, _ in outside], [b for _, b in outside]) < 1e-9,
         "worst %.3e" % worst([a for a, _ in outside], [b for _, b in outside]))

    # -------------------------------------------------- 5  the next key
    gate("5a the key after the pose is untouched",
         abs(cmds.getAttr(ty, time=30) - 50.0) < 1e-9,
         "ty at 30 = %.9f" % cmds.getAttr(ty, time=30))
    gate("5b the hold shortened the settle instead of running over it",
         abs(cmds.getAttr(ty, time=29) - 50.0) < 1e-6,
         "ty at 29 = %.9f" % cmds.getAttr(ty, time=29))

    # ------------------------------------------ 6  refusals, 7  sparsity
    gate("6a a pass-through key is refused",
         worst(before_tz, sample(tz, 0, 60, 0.5)) < 1e-9,
         "tz worst %.3e" % worst(before_tz, sample(tz, 0, 60, 0.5)))
    gate("6b and the report says why", "not a stop" in report, report[-90:])

    curve = (cmds.animLayer(layer, query=True, findCurveForPlug=tx) or [None])[0]
    count = len(cmds.keyframe(curve, query=True, timeChange=True) or [])
    gate("7 the plan is sparse", count <= 6, "%d keys on the layer curve" % count)

    # ------------------------------------------------- 8  idempotence
    keys_once = list(zip(cmds.keyframe(curve, query=True, timeChange=True) or [],
                         cmds.keyframe(curve, query=True, valueChange=True) or []))
    deselect_keys()
    cmds.selectKey(loc, attribute="translateX", time=(20, 20))
    mo.overshoot_objects([loc], shape="Spring", do_pos=True, do_rot=False,
                         strength_pos=1.0, frames_pos=12)
    keys_twice = list(zip(cmds.keyframe(curve, query=True, timeChange=True) or [],
                          cmds.keyframe(curve, query=True, valueChange=True) or []))
    gate("8 applying twice changes nothing", keys_once == keys_twice,
         "%d -> %d keys" % (len(keys_once), len(keys_twice)))

    # ------------------------------------------------ 9  strength, weight
    cmds.animLayer(layer, edit=True, weight=0.5)
    half = max(sample(tx, 20, 32, 0.25), key=lambda p: abs(p[1] - 100.0))[1]
    cmds.animLayer(layer, edit=True, weight=1.0)
    gate("9a the layer weight is the strength dial",
         abs((half - 100.0) - want_peak * 0.5) < 0.05 * want_peak,
         "peak %+.4f at weight 0.5, wanted %+.4f" % (half - 100.0,
                                                     want_peak * 0.5))

    deselect_keys()
    cmds.selectKey(loc, attribute="translateX", time=(20, 20))
    mo.overshoot_objects([loc], shape="Spring", do_pos=True, do_rot=False,
                         strength_pos=2.0, frames_pos=12)
    doubled = max(sample(tx, 20, 32, 0.25), key=lambda p: abs(p[1] - 100.0))[1]
    gate("9b strength 2 doubles the excursion",
         abs((doubled - 100.0) - want_peak * 2.0) < 0.05 * want_peak,
         "peak %+.4f, wanted %+.4f" % (doubled - 100.0, want_peak * 2.0))
    gate("9c and it still leaves at twice the speed",
         abs(slope_after(tx, 20.0) - 2 * speed) < 0.25 * speed,
         "%.4f per frame" % slope_after(tx, 20.0))

    # ---------------------------------------------------- 10  removal
    cmds.delete(layer)
    gate("10a deleting the layer restores the animation exactly",
         worst(before_tx, sample(tx, 0, 60, 0.5)) < 1e-9,
         "worst %.3e" % worst(before_tx, sample(tx, 0, 60, 0.5)))
    gate("10b and the hold channel with it",
         worst(before_ty, sample(ty, 0, 60, 0.5)) < 1e-9,
         "worst %.3e" % worst(before_ty, sample(ty, 0, 60, 0.5)))

    # -------------------------------------------------------- 11  bounce
    deselect_keys()
    cmds.selectKey(loc, attribute="translateX", time=(20, 20))
    mo.overshoot_objects([loc], shape="Bounce", do_pos=True, do_rot=False,
                         strength_pos=1.0, frames_pos=7)
    walk = sample(tx, 20, 27, 0.25)
    gate("11a the bounce never crosses to the far side of the pose",
         min(v for _, v in walk) >= 100.0 - 1e-4,
         "lowest %.6f" % min(v for _, v in walk))
    contacts = [t for t, v in walk if abs(v - 100.0) < 0.25]
    islands = []
    for t in contacts:
        if not islands or t - islands[-1][-1] > 0.5:
            islands.append([t])
        else:
            islands[-1].append(t)
    mids = [sum(g) / len(g) for g in islands]
    gaps = [b - a for a, b in zip(mids, mids[1:])]
    gate("11b its arcs shorten instead of ticking like a metronome",
         len(gaps) >= 2 and all(b <= a + 1e-9 for a, b in zip(gaps, gaps[1:])),
         "contacts %s gaps %s" % ([round(m, 2) for m in mids],
                                  [round(g, 2) for g in gaps]))
    gate("11c and it launches at the speed of the move too",
         abs(slope_after(tx, 20.0) - speed) < 0.3 * speed,
         "%.4f per frame" % slope_after(tx, 20.0))
    if cmds.animLayer(layer, query=True, exists=True):
        cmds.delete(layer)

    # ------------------------------------------------------ 12  rotation
    deselect_keys()
    cmds.selectKey(loc, attribute="rotateY", time=(20, 20))
    mo.overshoot_objects([loc], shape="Snap", do_pos=False, do_rot=True,
                         strength_rot=1.0, frames_rot=5)
    rot_layer = "%s_overshoot_rot" % loc.split("|")[-1]
    gate("12a rotation goes into its own layer",
         cmds.animLayer(rot_layer, query=True, exists=True), rot_layer)
    gate("12b the pose angle is untouched",
         abs(cmds.getAttr(ry, time=20) - 60.0) < 1e-6,
         "ry at 20 = %.9f" % cmds.getAttr(ry, time=20))
    want_rot = 6.0 * 5 / mo.sine_entry_slope(1, 0.30)
    rot_peak = max(sample(ry, 20, 25, 0.25), key=lambda p: abs(p[1] - 60.0))
    gate("12c a euler offset adds per channel, at the planned size",
         abs(abs(rot_peak[1] - 60.0) - want_rot) < 0.08 * want_rot,
         "peak %+.4f at %g, wanted %+.4f" % (rot_peak[1] - 60.0, rot_peak[0],
                                             want_rot))
    # Maya 2027 has no -rotationAccumulationMode flag at all (trap 41), so the
    # measurement above is the whole answer on how euler offsets accumulate.
    if cmds.animLayer(rot_layer, query=True, exists=True):
        cmds.delete(rot_layer)
    gate("12d and comes off cleanly",
         worst(before_ry, sample(ry, 0, 60, 0.5)) < 1e-9,
         "worst %.3e" % worst(before_ry, sample(ry, 0, 60, 0.5)))

    # ------------------------------- 13  the curve path needs no layer
    deselect_keys()
    cmds.selectKey(loc, attribute="translateX", time=(20, 20))
    mo.overshoot_objects([loc], shape="Spring", do_pos=True, do_rot=False,
                         strength_pos=1.0, frames_pos=12, use_layer=False)
    gate("13a baking into the curves leaves the pose alone as well",
         abs(cmds.getAttr(tx, time=20) - 100.0) < 1e-6,
         "tx at 20 = %.9f" % cmds.getAttr(tx, time=20))
    baked = max(sample(tx, 20, 32, 0.25), key=lambda p: abs(p[1] - 100.0))
    gate("13b with the same excursion",
         abs(abs(baked[1] - 100.0) - want_peak) < 0.05 * want_peak,
         "peak %+.4f, wanted %+.4f" % (baked[1] - 100.0, want_peak))
    gate("13c and no anim layer in sight",
         not [l for l in (cmds.ls(type="animLayer") or [])
              if l not in layers_before])

finally:
    for node in created:
        if cmds.objExists(node):
            quietly(cmds.delete, node)
    for l in (cmds.ls(type="animLayer") or []):
        if l not in layers_before and cmds.objExists(l):
            quietly(cmds.delete, l)
    for l in picked:
        if cmds.objExists(l):
            quietly(cmds.animLayer, l, edit=True, selected=True)
    deselect_keys()
    quietly(cmds.autoKeyframe, state=auto)
    quietly(cmds.currentTime, now)
    if sel:
        quietly(cmds.select, [s for s in sel if cmds.objExists(s)], replace=True)
    else:
        quietly(cmds.select, clear=True)

passed = sum(1 for ok, _, _ in RESULTS if ok)
print("=" * 74)
for ok, name, detail in RESULTS:
    print("%s  %-56s %s" % ("PASS" if ok else "FAIL", name, detail))
print("-" * 74)
for line in NOTES:
    print("note: " + line)
print("=" * 74)
print("%d/%d gates" % (passed, len(RESULTS)))
