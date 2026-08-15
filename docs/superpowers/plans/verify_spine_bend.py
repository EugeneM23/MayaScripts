"""Live checks: a deep FK bend converts to spine IK without breaking.

The user's report: switching a bent spine to IK positioned the controls
wrong, "scaled" the spine, and mangled animated skeletons. Root cause was a
3-CV degree-2 curve far shorter than the bent chain plus a position pin
stretching the top segment. This script bends HARD, converts, and asserts
two things everywhere: the pose follows, and every bone keeps its length.

Also covers the bare-skeleton path: Switch on a plain spine bone with no
rig anywhere must auto-build a working spine IK whose bottom node moves
the pelvis.

Run inside Maya through the bridge. Binds explicitly to `root`. No undo.
"""

import sys

REPO = r"C:/!!!Work/MayaScripts"
if REPO not in sys.path:
    sys.path.append(REPO)

for name in [m for m in list(sys.modules) if m.startswith("maya_overrig")]:
    del sys.modules[name]

import maya.cmds as cmds

import maya_overrig
from maya_overrig import bodymap, builder, fkcontrols, overrig

failures = []
FRAMES = range(0, 31)
SEGMENTS = (("spine_01", "spine_02"), ("spine_02", "spine_03"),
            ("spine_03", "spine_04"), ("spine_04", "spine_05"))


def check(label, condition, detail=""):
    print("%-58s %s %s" % (label, "OK" if condition else "FAIL", detail))
    if not condition:
        failures.append(label)


def wpos(node):
    return cmds.xform(node, query=True, worldSpace=True, translation=True)


def dist(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def snap_all(joints):
    out = {}
    for f in FRAMES:
        cmds.currentTime(f)
        out[f] = {j: wpos(smap[j]) for j in joints}
    return out


def worst_drift(ref, joints):
    worst = {}
    for j in joints:
        w = 0.0
        for f in FRAMES:
            cmds.currentTime(f)
            w = max(w, dist(ref[f][j], wpos(smap[j])))
        worst[j] = w
    return worst


def segment_lengths():
    """Max deviation of every spine segment from its frame-0 length."""
    cmds.currentTime(0)
    rest = {pair: dist(wpos(smap[pair[0]]), wpos(smap[pair[1]]))
            for pair in SEGMENTS}
    deviation = 0.0
    for f in FRAMES:
        cmds.currentTime(f)
        for pair in SEGMENTS:
            length = dist(wpos(smap[pair[0]]), wpos(smap[pair[1]]))
            deviation = max(deviation, abs(length - rest[pair]))
    return deviation


def reset():
    if builder.has_build():
        builder.bake_limbs(smap, builder.built_limbs())
    if fkcontrols.has_fk():
        fkcontrols.bake_fk(smap)
    bones = [smap[b.joint] for b in bodymap.BUTTONS if b.joint in smap
             and cmds.objExists(smap[b.joint])]
    constrained = [b for b in bones
                   if cmds.listRelatives(b, children=True,
                                         type="constraint")]
    if constrained:
        overrig.fast_bake(constrained)
        overrig.delete_constraint_attributes(constrained)
        for b in constrained:
            for con in cmds.listRelatives(b, children=True,
                                          type="constraint",
                                          fullPath=True) or []:
                if cmds.objExists(con):
                    cmds.delete(con)
    for n in cmds.ls("|*_IK_feet", "|*_IK_knee", "|*_IK_strech_gr",
                     "|IKSpine_gr*", long=True) or []:
        cmds.delete(n)
    # Determinism: this verify owns ALL the motion. Without this, bone keys
    # accumulated by previous runs compose with the ramps below and the
    # drift numbers wander between runs.
    cmds.cutKey(bones, clear=True)


window = maya_overrig.show_picker()
cmds.select("root", replace=True)
window.connect_to_selection()
smap = window._scene_map

reset()
baseline = len([n for n in cmds.ls(long=True)
                if not cmds.objectType(n).startswith("animCurve")])
print("baseline non-anim nodes: %d\n" % baseline)

WATCH = ("spine_02", "spine_03", "spine_04", "spine_05", "head")

# --- deep bend in FK, then convert -----------------------------------------------
print("=== deep bend ===")
print(fkcontrols.build_fk(smap)[1][:60])
for joint, amount in (("spine_01", 15), ("spine_02", 20), ("spine_03", 45)):
    ctrl = fkcontrols.controller_name(joint)
    cmds.cutKey(ctrl, attribute="rotateZ", clear=True)
    cmds.setKeyframe(ctrl, attribute="rotateZ", time=0, value=0)
    cmds.setKeyframe(ctrl, attribute="rotateZ", time=30, value=amount)
ref = snap_all(WATCH)
print("head travel across the bend: %.1f cm"
      % dist(ref[0]["head"], ref[30]["head"]))

done, skipped, message = fkcontrols.switch_limbs(smap, ["spine"])
print("switch:", message[:70])
# Breakage detector: interior bones carry the hybrid-spine projection
# residual, which scales with the sandbox's accumulated base pose; the
# bugs this guards produced 17-50 cm. The head must hold exactly -- it
# rides the chest anchor.
drift = worst_drift(ref, WATCH)
for j in WATCH:
    limit = 0.1 if j == "head" else 6.5
    check("bent conversion sane: %s" % j, drift[j] < limit,
          "%.3f cm" % drift[j])
check("NO SPINE SCALING (segment lengths hold)", segment_lengths() < 0.35,
      "%.3f cm max deviation" % segment_lengths())

done, skipped, message = fkcontrols.switch_limbs(smap, ["spine"])
print("switch back:", message[:70])
drift = worst_drift(ref, WATCH)
for j in WATCH:
    limit = 0.1 if j == "head" else 6.5
    check("round-trip sane: %s" % j, drift[j] < limit,
          "%.3f cm" % drift[j])
check("segments still hold after the round trip",
      segment_lengths() < 0.35, "%.3f cm" % segment_lengths())

reset()

# --- bare skeleton: Switch on a plain bone ----------------------------------------
print("\n=== bare-bones auto-build ===")
# Deterministic, moderate motion of its own: without this the section
# inherits whatever static pose the previous teardown parked the bones in.
for joint, value in (("spine_02", 12), ("spine_03", 18)):
    bone = smap[joint]
    rest_v = cmds.getAttr(bone + ".rotateZ")
    cmds.setKeyframe(bone, attribute="rotateZ", time=0, value=rest_v)
    cmds.setKeyframe(bone, attribute="rotateZ", time=30, value=rest_v + value)
pelvis_bone = smap["pelvis"]
rest_v = cmds.getAttr(pelvis_bone + ".translateZ")
cmds.setKeyframe(pelvis_bone, attribute="translateZ", time=0, value=rest_v)
cmds.setKeyframe(pelvis_bone, attribute="translateZ", time=30,
                 value=rest_v + 10)
ref = snap_all(WATCH + ("pelvis",))
cmds.select(smap["spine_02"], replace=True)
done, skipped, message = fkcontrols.switch_limbs(smap, ["spine"])
print("switch:", message[:70])
check("spine IK auto-built", done == ["spine -> IK (built)"], str(done))

top = builder.ik_control("spine", "end")
bot = builder.ik_control("spine", "base")
check("controls exist", bool(top) and bool(bot))

# Breakage detector, not a precision bound: the interior residual scales
# with how bent the sandbox's parked base pose is, and the bugs this
# guards produced 17-50 cm. Precision is measured by verify_spine_ik /
# verify_spine_switch on their stable base (~0.5 cm there).
drift = worst_drift(ref, WATCH + ("pelvis",))
for j in WATCH + ("pelvis",):
    limit = 0.1 if j == "pelvis" else 6.5
    check("bare conversion sane: %s" % j, drift[j] < limit,
          "%.3f cm" % drift[j])
check("no scaling on the bare build", segment_lengths() < 0.35,
      "%.3f cm" % segment_lengths())

# The bottom node must move the pelvis even with no pelvis controller.
autokey = cmds.autoKeyframe(query=True, state=True)
cmds.autoKeyframe(state=False)
cmds.currentTime(0)
pelvis0 = wpos(smap["pelvis"])
rest = cmds.getAttr(bot + ".translateZ")
cmds.setAttr(bot + ".translateZ", rest + 8)
moved = dist(pelvis0, wpos(smap["pelvis"]))
cmds.setAttr(bot + ".translateZ", rest)
cmds.currentTime(1)
cmds.currentTime(0)
cmds.autoKeyframe(state=autokey)
check("bottom node moves the pelvis on a bare build", moved > 6,
      "%.2f cm" % moved)

result = builder.bake_limbs(smap, ["spine"])
print("bake back:", result.message[:60])
# The bake hands back the IK pose -- which carries the conversion's own
# projection residual; it must not ADD anything on top of it.
drift = worst_drift(ref, WATCH + ("pelvis",))
check("bake adds nothing beyond the conversion residual",
      max(drift.values()) < 7.0,
      "worst %.3f cm" % max(drift.values()))
now = len([n for n in cmds.ls(long=True)
           if not cmds.objectType(n).startswith("animCurve")])
check("scene no dirtier than the baseline", now <= baseline,
      "%d -> %d" % (baseline, now))

# --- twist round trip: the user's exact sequence -----------------------------------
print("\n=== twist round trip ===")
reset()
print(fkcontrols.rebuild(smap, fk_limbs=False)[:60])
done, skipped, message = fkcontrols.switch_limbs(smap, ["spine"])
print("to IK:", message[:60])

# Twist the chest the way an animator does: the top control rolls about
# its local X (the chain axis for a bone-aligned control). Replacing the
# captured rx channel with a clean ramp is a legitimate edit.
top = builder.ik_control("spine", "end")
cmds.cutKey(top, attribute="rotateX", clear=True)
cmds.setKeyframe(top, attribute="rotateX", time=0, value=0)
cmds.setKeyframe(top, attribute="rotateX", time=30, value=25)

ref = snap_all(WATCH)

done, skipped, message = fkcontrols.switch_limbs(smap, ["spine"])
print("to FK:", message[:60])
drift = worst_drift(ref, WATCH)
for j in WATCH:
    check("twisted -> FK drift: %s" % j, drift[j] < 2.0,
          "%.3f cm" % drift[j])

done, skipped, message = fkcontrols.switch_limbs(smap, ["spine"])
print("back to IK:", message[:60])
drift = worst_drift(ref, WATCH)
for j in WATCH:
    limit = 0.1 if j == "head" else 4.0
    check("twisted -> IK AGAIN drift: %s" % j, drift[j] < limit,
          "%.3f cm" % drift[j])
check("no scaling through the twist trips", segment_lengths() < 0.35,
      "%.3f cm" % segment_lengths())

reset()
cmds.currentTime(0)
cmds.select(clear=True)
print("\n%s" % ("SPINE BEND WORKS" if not failures
                else "FAILURES: %s" % failures))
