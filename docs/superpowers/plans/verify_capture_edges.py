"""Live check: a pose keyed at the range edges survives a rebuild.

The user's bug: raise the FK arms (a pose lands on the current frame, over
dense baked keys -- so it exists ONLY at the keyed frames), bake all, Build
again -> the fingers fell to the interior pose. Cause: OverRig's capture
bakes clip a frame at each end of the playback range; the fix pads the
range by one frame around every capture (overrig.padded_range).

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


def check(label, condition, detail=""):
    print("%-58s %s %s" % (label, "OK" if condition else "FAIL", detail))
    if not condition:
        failures.append(label)


def wpos(node):
    return cmds.xform(node, query=True, worldSpace=True, translation=True)


def dist(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


window = maya_overrig.show_picker()
cmds.select("root", replace=True)
window.connect_to_selection()
smap = window._scene_map

# --- reset from any state -------------------------------------------------------
if builder.has_build():
    builder.bake_limbs(smap, builder.built_limbs())
if fkcontrols.has_fk():
    fkcontrols.bake_fk(smap)
bones = [smap[b.joint] for b in bodymap.BUTTONS if b.joint in smap
         and cmds.objExists(smap[b.joint])]
constrained = [b for b in bones
               if cmds.listRelatives(b, children=True, type="constraint")]
if constrained:
    overrig.fast_bake(constrained)
    overrig.delete_constraint_attributes(constrained)
    for b in constrained:
        for con in cmds.listRelatives(b, children=True, type="constraint",
                                      fullPath=True) or []:
            if cmds.objExists(con):
                cmds.delete(con)

baseline = len([n for n in cmds.ls(long=True)
                if not cmds.objectType(n).startswith("animCurve")])
print("baseline non-anim nodes: %d\n" % baseline)

rest_gap = None
cmds.currentTime(0)
rest_gap = dist(wpos(smap["hand_l"]), wpos(smap["index_metacarpal_l"]))
print("rest hand->metacarpal: %.2f cm" % rest_gap)

# --- the user's flow --------------------------------------------------------------
print(fkcontrols.rebuild(smap, fk_limbs=False)[:70])
print(fkcontrols.switch_limbs(smap, ["arm_l", "arm_r"])[2][:70])

# The raise, exactly as an animator makes it: keys at the frames they touch,
# over the dense baked keys underneath -- the pose exists ONLY at 0 and 30.
for side in ("l", "r"):
    ctrl = fkcontrols.controller_name("upperarm_" + side)
    for frame in (0, 30):
        cmds.setKeyframe(ctrl, attribute="rotateZ", time=frame, value=-60)

cmds.currentTime(0)
raised_hand = wpos(smap["hand_l"])
raised_tip = wpos(smap["index_03_l"])

print(fkcontrols.bake_fk(smap)[1][:70])
if builder.has_build():
    builder.bake_limbs(smap, builder.built_limbs())

cmds.currentTime(0)
check("bake kept the frame-0 raise",
      dist(raised_hand, wpos(smap["hand_l"])) < 1.0,
      "%.2f cm" % dist(raised_hand, wpos(smap["hand_l"])))
check("bake kept the fingers on the hand",
      abs(dist(wpos(smap["hand_l"]), wpos(smap["index_metacarpal_l"]))
          - rest_gap) < 1.0)

# --- rebuild: this is where the fingers used to fall -------------------------------
# Every finger reading below is a BONE distance, and since 2026-08-18 the
# fingers have no controllers at all -- so what these gates now watch is the
# arm's capture carrying the hand, with the finger bones rigidly along for the
# ride. The edge-clipping bug this script was written for lived in the CHAIN
# capture, which the arm still goes through.
print("\nrebuild:", fkcontrols.rebuild(smap, fk_limbs=False)[:70])

for frame in (0, 15, 30):
    cmds.currentTime(frame)
    gap = dist(wpos(smap["hand_l"]), wpos(smap["index_metacarpal_l"]))
    check("fingers on the hand at frame %d" % frame,
          abs(gap - rest_gap) < 2.0, "%.2f cm (rest %.2f)" % (gap, rest_gap))
cmds.currentTime(0)
check("frame-0 raise survived the rebuild",
      dist(raised_hand, wpos(smap["hand_l"])) < 2.0,
      "%.2f cm" % dist(raised_hand, wpos(smap["hand_l"])))
check("frame-0 fingertip survived the rebuild",
      dist(raised_tip, wpos(smap["index_03_l"])) < 2.5,
      "%.2f cm" % dist(raised_tip, wpos(smap["index_03_l"])))

# --- teardown -----------------------------------------------------------------------
fkcontrols.bake_fk(smap)
if builder.has_build():
    builder.bake_limbs(smap, builder.built_limbs())
now = len([n for n in cmds.ls(long=True)
           if not cmds.objectType(n).startswith("animCurve")])
check("scene no dirtier than the baseline", now <= baseline,
      "%d -> %d" % (baseline, now))

cmds.currentTime(0)
cmds.select(clear=True)
print("\n%s" % ("EDGE CAPTURE WORKS" if not failures
                else "FAILURES: %s" % failures))
