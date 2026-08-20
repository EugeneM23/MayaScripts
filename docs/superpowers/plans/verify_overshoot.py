"""Live proof of the redesigned overshoot. Send through the command port.

Everything happens in a SANDBOX: locators this script creates, animates,
measures and deletes. It never touches the animator's character, and it never
calls cmds.undo() -- the whole bridge script is one command, so an undo there
reverts a chunk of somebody else's work.

Twelve gates, in the order the design spec lists them:
docs/superpowers/specs/2026-08-20-overshoot-redesign-design.md
"""

import sys

if r"C:/!!!Work/MayaScripts" not in sys.path:
    sys.path.append(r"C:/!!!Work/MayaScripts")

import maya.cmds as cmds

import maya_overshoot as mo

RESULTS = []
NOTES = []


def gate(name, ok, detail=""):
    RESULTS.append((bool(ok), name, detail))


def note(text):
    NOTES.append(text)


def sample(plug, first, last, step=1.0):
    out = []
    t = float(first)
    while t <= last + 1e-9:
        out.append((t, cmds.getAttr(plug, time=t)))
        t += step
    return out


def quietly(fn, *args, **kw):
    """Teardown must not lose its remaining steps to one failing call."""
    try:
        return fn(*args, **kw)
    except Exception as exc:                                  # noqa: BLE001
        NOTES.append("teardown: %s: %s" % (getattr(fn, "__name__", fn), exc))


def deselect_keys():
    # selectKey(clear=True) needs something selected to work from
    quietly(cmds.selectKey, clear=True)


def worst(a, b):
    """Largest absolute difference between two equal-length sample lists."""
    return max(abs(x[1] - y[1]) for x, y in zip(a, b)) if a else 0.0


def turning_points(plug, first, last, step=0.25):
    """(time, value) where the sampled curve changes direction."""
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

    #  tx  a move that stops on the last key      0 -> 100 over 20 frames
    #  ty  a move into a hold                     0 -> 50 at 20, held at 30
    #  tz  a move that carries on                  0 -> 50 at 20 -> 120 at 40
    #  ry  the same as tx, in degrees
    for attr, keys in (
            ("translateX", ((0, 0.0), (20, 100.0))),
            ("translateY", ((0, 0.0), (20, 50.0), (30, 50.0))),
            ("translateZ", ((0, 0.0), (20, 50.0), (40, 120.0))),
            ("rotateY", ((0, 0.0), (20, 60.0))),
    ):
        for t, v in keys:
            cmds.setKeyframe(loc, attribute=attr, time=t, value=v)

    tx = "%s.translateX" % loc
    ty = "%s.translateY" % loc
    tz = "%s.translateZ" % loc
    ry = "%s.rotateY" % loc

    before_tx = sample(tx, -5, 60)
    before_ty = sample(ty, -5, 60)
    before_tz = sample(tz, -5, 60)
    before_ry = sample(ry, -5, 60)

    note("fps %s   base tx at 20: %.4f" % (
        cmds.currentUnit(query=True, time=True), cmds.getAttr(tx, time=20)))

    # ---------------------------------------------------------------- apply
    deselect_keys()
    cmds.selectKey(loc, attribute="translateX", time=(20, 20))
    cmds.selectKey(loc, attribute="translateY", time=(20, 20), add=True)
    cmds.selectKey(loc, attribute="translateZ", time=(20, 20), add=True)

    report = mo.overshoot_objects([loc], shape="Spring", do_pos=True,
                                  do_rot=False, amount_pos=0.20, frames_pos=12)
    note("report: " + report)

    layer = "%s_overshoot_pos" % loc.split("|")[-1]
    gate("1a the additive layer exists",
         cmds.animLayer(layer, query=True, exists=True), layer)
    gate("1b it is additive, not override",
         cmds.animLayer(layer, query=True, exists=True) and
         not cmds.animLayer(layer, query=True, override=True))

    # ------------------------------------------------- 1  the extreme lands
    peak = cmds.getAttr(tx, time=20)
    gate("1c the extreme is on the selected key at the requested size",
         abs(peak - 120.0) < 1e-4, "tx at 20 = %.6f, wanted 120" % peak)
    if abs(peak - 20.0) < 1e-4:
        note("setKeyframe(animLayer=) wrote the value ABSOLUTELY, not as an "
             "offset -- write through animLayer -findCurveForPlug instead")

    # -------------------------------------- 2  nothing outside the window
    after_tx = sample(tx, -5, 60)
    outside = [(a, b) for a, b in zip(before_tx, after_tx)
               if a[0] < 0.0 or a[0] > 32.0]
    gate("2 the base animation outside the window is untouched",
         worst([a for a, _ in outside], [b for _, b in outside]) < 1e-9,
         "worst %.3e" % worst([a for a, _ in outside], [b for _, b in outside]))

    # --------------------------------------------- 3  the turning points
    #  Spring: 3 swings over 12 frames -> 20, 24, 28 and the landing at 32
    want = [(20.0, 120.0), (24.0, 100.0 - 6.0), (28.0, 100.0 + 1.8)]
    turns = turning_points(tx, 18, 34)
    matched = []
    for wt, wv in want:
        near = [p for p in turns if abs(p[0] - wt) <= 0.5]
        matched.append(bool(near) and abs(near[0][1] - wv) < 0.75)
    gate("3a the turning points sit where the geometric series says",
         all(matched), "found %s" % [(round(t, 2), round(v, 3)) for t, v in turns])
    gate("3b and there are no others",
         len(turns) == len(want),
         "%d turning points in 18..34" % len(turns))
    gate("3c the settle lands exactly on the pose",
         abs(cmds.getAttr(tx, time=32) - 100.0) < 1e-6,
         "tx at 32 = %.9f" % cmds.getAttr(tx, time=32))

    # ------------------------------------- 4  the extreme is not a corner
    out_slope = cmds.getAttr(tx, time=20.25) - cmds.getAttr(tx, time=20.0)
    in_slope = cmds.getAttr(tx, time=20.0) - cmds.getAttr(tx, time=19.75)
    gate("4 the extreme is a turning point, not a kick",
         abs(out_slope) < 0.05 and abs(in_slope) < 0.6,
         "in %.5f out %.5f per quarter frame" % (in_slope, out_slope))

    # -------------------------------------------------- 7  the next key
    gate("7 the key after the pose is untouched",
         abs(cmds.getAttr(ty, time=30) - 50.0) < 1e-9,
         "ty at 30 = %.9f" % cmds.getAttr(ty, time=30))
    gate("7b the hold shortened the settle instead of running over it",
         abs(cmds.getAttr(ty, time=29) - 50.0) < 1e-6,
         "ty at 29 = %.9f" % cmds.getAttr(ty, time=29))

    # ------------------------------------------- 10  refusals, 11  sparsity
    gate("10a a pass-through key is refused",
         worst(before_tz, sample(tz, -5, 60)) < 1e-9,
         "tz worst %.3e" % worst(before_tz, sample(tz, -5, 60)))
    gate("10b and the report says why", "not a stop" in report, report[-90:])

    curve = (cmds.animLayer(layer, query=True, findCurveForPlug=tx) or [None])[0]
    count = len(cmds.keyframe(curve, query=True, timeChange=True) or [])
    gate("11 the plan is sparse", count <= 6, "%d keys on the layer curve" % count)

    # ------------------------------------------------- 6  idempotence
    keys_once = list(zip(cmds.keyframe(curve, query=True, timeChange=True) or [],
                         cmds.keyframe(curve, query=True, valueChange=True) or []))
    deselect_keys()
    cmds.selectKey(loc, attribute="translateX", time=(20, 20))
    mo.overshoot_objects([loc], shape="Spring", do_pos=True, do_rot=False,
                         amount_pos=0.20, frames_pos=12)
    keys_twice = list(zip(cmds.keyframe(curve, query=True, timeChange=True) or [],
                          cmds.keyframe(curve, query=True, valueChange=True) or []))
    gate("6 applying twice changes nothing", keys_once == keys_twice,
         "%d -> %d keys" % (len(keys_once), len(keys_twice)))

    # ------------------------------------------------- 8  amount, weight
    cmds.animLayer(layer, edit=True, weight=0.5)
    half = cmds.getAttr(tx, time=20)
    cmds.animLayer(layer, edit=True, weight=1.0)
    gate("8a the layer weight is the strength dial",
         abs(half - 110.0) < 1e-3, "tx at 20 with weight 0.5 = %.6f" % half)

    deselect_keys()
    cmds.selectKey(loc, attribute="translateX", time=(20, 20))
    mo.overshoot_objects([loc], shape="Spring", do_pos=True, do_rot=False,
                         amount_pos=0.40, frames_pos=12)
    gate("8b amplitude is linear in the amount",
         abs(cmds.getAttr(tx, time=20) - 140.0) < 1e-4,
         "40%% gave %.6f, wanted 140" % cmds.getAttr(tx, time=20))

    # ------------------------------------------------------- 5  removal
    cmds.delete(layer)
    gate("5 deleting the layer restores the animation exactly",
         worst(before_tx, sample(tx, -5, 60)) < 1e-9,
         "worst %.3e" % worst(before_tx, sample(tx, -5, 60)))
    gate("5b and the hold channel with it",
         worst(before_ty, sample(ty, -5, 60)) < 1e-9,
         "worst %.3e" % worst(before_ty, sample(ty, -5, 60)))

    # -------------------------------------------------------- 9  bounce
    deselect_keys()
    cmds.selectKey(loc, attribute="translateX", time=(20, 20))
    mo.overshoot_objects([loc], shape="Bounce", do_pos=True, do_rot=False,
                         amount_pos=0.20, frames_pos=12)
    walk = sample(tx, 20, 32, 0.25)
    gate("9a the bounce never crosses to the far side of the pose",
         min(v for _, v in walk) >= 100.0 - 1e-4,
         "lowest %.6f" % min(v for _, v in walk))
    contacts = [t for t, v in walk if abs(v - 100.0) < 0.35]
    islands = []
    for t in contacts:
        if not islands or t - islands[-1][-1] > 0.5:
            islands.append([t])
        else:
            islands[-1].append(t)
    mids = [sum(g) / len(g) for g in islands]
    gaps = [b - a for a, b in zip(mids, mids[1:])]
    gate("9b its contacts close in geometrically", len(gaps) >= 2 and
         all(b < a for a, b in zip(gaps, gaps[1:])),
         "contacts at %s, gaps %s" % ([round(m, 2) for m in mids],
                                      [round(g, 2) for g in gaps]))

    bounce_layer = "%s_overshoot_pos" % loc.split("|")[-1]
    if cmds.animLayer(bounce_layer, query=True, exists=True):
        cmds.delete(bounce_layer)

    # ---------------------------------------------- 12  rotation, additivity
    deselect_keys()
    cmds.selectKey(loc, attribute="rotateY", time=(20, 20))
    mo.overshoot_objects([loc], shape="Snap", do_pos=False, do_rot=True,
                         amount_rot=0.25, frames_rot=10)
    rot_layer = "%s_overshoot_rot" % loc.split("|")[-1]
    gate("12a rotation goes into its own layer",
         cmds.animLayer(rot_layer, query=True, exists=True), rot_layer)
    got = cmds.getAttr(ry, time=20)
    gate("12b a euler offset adds per channel",
         abs(got - 75.0) < 1e-3, "ry at 20 = %.6f, wanted 75" % got)
    # Maya 2027 has no -rotationAccumulationMode flag at all, so 12b above is
    # the whole answer on how euler offsets accumulate: measured, not assumed.
    if cmds.animLayer(rot_layer, query=True, exists=True):
        cmds.delete(rot_layer)
    gate("12c and comes off cleanly",
         worst(before_ry, sample(ry, -5, 60)) < 1e-9,
         "worst %.3e" % worst(before_ry, sample(ry, -5, 60)))

    # ------------------------------- the curve path needs no layer at all
    deselect_keys()
    cmds.selectKey(loc, attribute="translateX", time=(20, 20))
    mo.overshoot_objects([loc], shape="Spring", do_pos=True, do_rot=False,
                         amount_pos=0.20, frames_pos=12, use_layer=False)
    baked = cmds.getAttr(tx, time=20)
    gate("13 baking into the curves gives the same extreme",
         abs(baked - 120.0) < 1e-4, "tx at 20 = %.6f" % baked)
    gate("13b with no anim layer in sight",
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
print("=" * 72)
for ok, name, detail in RESULTS:
    print("%s  %-58s %s" % ("PASS" if ok else "FAIL", name, detail))
print("-" * 72)
for line in NOTES:
    print("note: " + line)
print("=" * 72)
print("%d/%d gates" % (passed, len(RESULTS)))
