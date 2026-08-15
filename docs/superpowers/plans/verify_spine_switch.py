"""Live checks for Switch FK/IK on the spine, spline-IK edition.

The pelvis controller must survive the switch; thigh chains never move;
neck and clavicle chains re-hang on the top node; fingers ride their arm --
the original bug was fingers detaching because they were lifted with the
chest chains.

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
from maya_overrig import bodymap, builder, fkcontrols

failures = []


def check(label, condition, detail=""):
    print("%-58s %s %s" % (label, "OK" if condition else "FAIL", detail))
    if not condition:
        failures.append(label)


def wpos(node):
    return cmds.xform(node, query=True, worldSpace=True, translation=True)


def dist(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def snap(joint):
    out = {}
    for frame in (0, 15, 30):
        cmds.currentTime(frame)
        out[frame] = wpos(smap[joint])
    return out


def drift_of(joint, ref):
    worst = 0.0
    for frame, pos in ref.items():
        cmds.currentTime(frame)
        worst = max(worst, dist(pos, wpos(smap[joint])))
    return worst


def is_under(child, parent):
    if not (child and parent and cmds.objExists(child)
            and cmds.objExists(parent)):
        return False
    return cmds.ls(child, long=True)[0].startswith(
        cmds.ls(parent, long=True)[0] + "|")


class pushed(object):
    def __init__(self, plug, delta):
        self.plug = plug
        self.delta = delta

    def __enter__(self):
        self.rest = cmds.getAttr(self.plug)
        cmds.setAttr(self.plug, self.rest + self.delta)

    def __exit__(self, *_exc):
        cmds.setAttr(self.plug, self.rest)


window = maya_overrig.show_picker()
cmds.select("root", replace=True)
window.connect_to_selection()
smap = window._scene_map

# --- reset ------------------------------------------------------------------
if fkcontrols.has_fk():
    fkcontrols.bake_fk(smap)
if builder.has_build():
    builder.bake_limbs(smap, builder.built_limbs())

baseline = len([n for n in cmds.ls(long=True)
                if not cmds.objectType(n).startswith("animCurve")])
print("baseline non-anim nodes: %d\n" % baseline)

hand_ref = snap("hand_l")
head_ref = snap("head")
thigh_ref = snap("thigh_l")
chest_ref = snap("spine_05")
finger_ref = snap("index_03_l")

# --- full FK, then switch the spine to IK ------------------------------------
count, message = fkcontrols.build_fk(smap)
print("build FK:", message, "\n")
check("full FK built", count == 64, str(count))
pelvis_ctrl = fkcontrols.controller_name("pelvis")
check("pelvis has its own controller", cmds.objExists(pelvis_ctrl))
check("pelvis is its own chain",
      bool(fkcontrols.chain_members("pelvis")))

cmds.select(fkcontrols.controller_name("spine_03"), replace=True)
done, skipped, message = fkcontrols.switch_limbs(smap, ["spine"])
print("switch spine:", message, "\n")
check("spine reported switched to IK", done == ["spine -> IK"], str(done))
check("spine is IK now", builder.built_limbs() == ["spine"],
      str(builder.built_limbs()))
check("spine FK chain gone", not fkcontrols.chain_members("spine"))

check("PELVIS CONTROLLER SURVIVED", cmds.objExists(pelvis_ctrl))
check("pelvis chain manifest intact",
      bool(fkcontrols.chain_members("pelvis")))

top = builder.ik_control("spine", "end")
mid = builder.ik_control("spine", "pole")
bot = builder.ik_control("spine", "base")
check("three spine controls exist", all([top, mid, bot]))

neck_ctrl = fkcontrols.controller_name("neck_01")
clav_l = fkcontrols.controller_name("clavicle_l")
clav_r = fkcontrols.controller_name("clavicle_r")
thigh_l = fkcontrols.controller_name("thigh_l")
index_ctrl = fkcontrols.controller_name("index_metacarpal_l")
hand_ctrl = fkcontrols.controller_name("hand_l")

check("neck hangs on the top control", is_under(neck_ctrl, top))
check("clavicles hang on the top control",
      is_under(clav_l, top) and is_under(clav_r, top))
check("thighs still hang on the pelvis controller",
      is_under(thigh_l, pelvis_ctrl))
check("fingers still hang on the hand (never lifted)",
      is_under(index_ctrl, hand_ctrl))

check("head animation survived the switch",
      drift_of("head", head_ref) < 1.0,
      "%.3f cm" % drift_of("head", head_ref))
check("hand animation survived the switch",
      drift_of("hand_l", hand_ref) < 1.0,
      "%.3f cm" % drift_of("hand_l", hand_ref))
check("finger animation survived the switch",
      drift_of("index_03_l", finger_ref) < 1.2,
      "%.3f cm" % drift_of("index_03_l", finger_ref))
check("thigh animation survived the switch",
      drift_of("thigh_l", thigh_ref) < 0.5,
      "%.3f cm" % drift_of("thigh_l", thigh_ref))

# THE BUG: moving the spine IK must carry the fingers with everything else.
cmds.currentTime(0)
tip0 = wpos(smap["index_03_l"])
head0 = wpos(smap["head"])
with pushed(top + ".translateZ", 10):
    tip_moved = dist(tip0, wpos(smap["index_03_l"]))
    head_moved = dist(head0, wpos(smap["head"]))
check("head follows the top control", head_moved > 5,
      "%.2f cm" % head_moved)
check("FINGERS FOLLOW THE TOP CONTROL (the bug)", tip_moved > 5,
      "%.2f cm" % tip_moved)

# --- switch back to FK ---------------------------------------------------------
done, skipped, message = fkcontrols.switch_limbs(smap, ["spine"])
print("\nswitch spine back:", message, "\n")
check("spine reported switched to FK", done == ["spine -> FK"], str(done))
check("no IK left", builder.built_limbs() == [], str(builder.built_limbs()))
check("spine FK chain recorded again",
      bool(fkcontrols.chain_members("spine")))
check("pelvis controller still standing", cmds.objExists(pelvis_ctrl))

spine05_ctrl = fkcontrols.controller_name("spine_05")
check("neck back on the spine_05 control", is_under(neck_ctrl, spine05_ctrl))
check("clavicles back on the spine_05 control",
      is_under(clav_l, spine05_ctrl) and is_under(clav_r, spine05_ctrl))
check("thighs never moved", is_under(thigh_l, pelvis_ctrl))
check("fingers never moved", is_under(index_ctrl, hand_ctrl))
check("chest animation survived the round trip",
      drift_of("spine_05", chest_ref) < 1.0,
      "%.3f cm" % drift_of("spine_05", chest_ref))

# --- bake everything back --------------------------------------------------------
removed, message = fkcontrols.bake_fk(smap)
print("\nfinal bake:", message)
check("nothing recorded",
      not fkcontrols.has_fk() and not builder.has_build())
now = len([n for n in cmds.ls(long=True)
           if not cmds.objectType(n).startswith("animCurve")])
check("scene back to baseline", now == baseline, "%d -> %d" % (baseline, now))
check("head animation on the bones at the end",
      drift_of("head", head_ref) < 1.2,
      "%.3f cm" % drift_of("head", head_ref))

cmds.currentTime(0)
cmds.select(clear=True)
print("\n%s" % ("SPINE SWITCH WORKS" if not failures
                else "FAILURES: %s" % failures))
