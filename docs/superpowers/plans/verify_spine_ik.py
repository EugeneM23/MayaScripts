"""Live checks for the spline-IK spine: three controls, 50/50 middle, no aim.

Run inside Maya through the bridge. Binds explicitly to `root`.
Never uses cmds.undo() -- attribute writes are restored explicitly, with the
values read back first (constrained channels do not rest at zero).
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


class pushed(object):
    """Temporarily add to an attribute; always restores the read value."""

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

# --- reset -------------------------------------------------------------------
if fkcontrols.has_fk():
    fkcontrols.bake_fk(smap)
if builder.has_build():
    builder.bake_limbs(smap, builder.built_limbs())

baseline = len([n for n in cmds.ls(long=True)
                if not cmds.objectType(n).startswith("animCurve")])
print("baseline non-anim nodes: %d\n" % baseline)

chest_ref = snap("spine_05")
mid_ref = snap("spine_03")
head_ref = snap("head")
pelvis_ref = snap("pelvis")

# --- build --------------------------------------------------------------------
result = builder.build(smap, only=["spine"])
print("build spine IK:", result.message, "\n")
check("spine reported built", result.built == ["spine"], str(result.built))

top = builder.ik_control("spine", "end")
mid = builder.ik_control("spine", "pole")
bot = builder.ik_control("spine", "base")
def is_ctrl(path, mark):
    leaf = (path or "").split("|")[-1]
    return leaf == mark or (leaf.startswith(mark)
                            and leaf[len(mark):].isdigit())


check("top control is the control itself",
      is_ctrl(top, "IKSpine_top"), str(top))
check("mid control is the control itself (not blend/zero)",
      is_ctrl(mid, "IKSpine_mid"), str(mid))
check("bottom control is the control itself",
      is_ctrl(bot, "IKSpine_bot"), str(bot))

check("pelvis stays out of the spine rig",
      "pelvis" not in [j.split("|")[-1] for j in
                       (cmds.listConnections(top) or [])], "")
check("no drift: chest", drift_of("spine_05", chest_ref) < 0.5,
      "%.3f cm" % drift_of("spine_05", chest_ref))
check("small drift: middle (projection bound)",
      drift_of("spine_03", mid_ref) < 2.0,
      "%.3f cm" % drift_of("spine_03", mid_ref))
check("no drift: pelvis untouched", drift_of("pelvis", pelvis_ref) < 0.01,
      "%.3f cm" % drift_of("pelvis", pelvis_ref))

# --- behaviour ---------------------------------------------------------------
cmds.currentTime(0)

chest0 = wpos(smap["spine_05"])
with pushed(top + ".translateZ", 10):
    moved = dist(chest0, wpos(smap["spine_05"]))
check("top moves the chest", moved > 5, "%.2f cm" % moved)

mid_w0 = cmds.xform(mid, query=True, worldSpace=True, translation=True)
with pushed(top + ".translateZ", 10):
    mid_moved = dist(mid_w0, cmds.xform(mid, query=True, worldSpace=True,
                                        translation=True))
check("middle follows the top at ~50%", 3.5 < mid_moved < 6.5,
      "%.2f cm (want ~5)" % mid_moved)

with pushed(bot + ".translateZ", 10):
    mid_moved = dist(mid_w0, cmds.xform(mid, query=True, worldSpace=True,
                                        translation=True))
check("middle follows the bottom at ~50%", 3.5 < mid_moved < 6.5,
      "%.2f cm (want ~5)" % mid_moved)

waist0 = wpos(smap["spine_03"])
with pushed(mid + ".translateZ", 8):
    moved = dist(waist0, wpos(smap["spine_03"]))
# The degree-2 curve smooths a CV push, so the waist takes roughly half of
# it -- that is the curve doing its job, not slack in the rig.
check("middle is animatable and bends the waist", moved > 3,
      "%.2f cm" % moved)

lower0 = wpos(smap["spine_01"])
chest0 = wpos(smap["spine_05"])
with pushed(bot + ".translateZ", 8):
    lower_moved = dist(lower0, wpos(smap["spine_01"]))
    chest_moved = dist(chest0, wpos(smap["spine_05"]))
check("bottom sways the lower spine", lower_moved > 4,
      "%.2f cm" % lower_moved)
check("chest stays planted meanwhile", chest_moved < 1.5,
      "%.2f cm" % chest_moved)

chest0 = wpos(smap["spine_05"])
with pushed(smap["pelvis"] + ".translateZ", 10):
    follow = dist(chest0, wpos(smap["spine_05"]))
check("whole spine follows the pelvis bone", follow > 8, "%.2f cm" % follow)

# Twist distributes: roll the chest, the waist takes roughly half the roll,
# and nothing on the solver aims (no flip when the top translates far).
with pushed(top + ".rotateY", 40):
    waist_roll = cmds.xform(smap["spine_03"], query=True, worldSpace=True,
                            rotation=True)
print("  waist world rotation under chest roll 40:",
      ["%.1f" % v for v in waist_roll])
with pushed(top + ".translateX", 25):
    flipped = dist(wpos(smap["spine_03"]),
                   cmds.xform(mid, query=True, worldSpace=True,
                              translation=True))
check("no flip under a large chest translate", flipped < 30,
      "%.1f" % flipped)

# --- picker resolution ---------------------------------------------------------
resolution = window._resolution()
check("picker: spine_ik_top resolves", "spine_ik_top" in resolution)
check("picker: spine_ik_mid resolves to the control",
      resolution.get("spine_ik_mid", "") == mid)
check("picker: spine_ik_bot resolves", "spine_ik_bot" in resolution)
check("picker: FK spine buttons dimmed", "spine_03" not in resolution)

# --- bake back -----------------------------------------------------------------
result = builder.bake_limbs(smap, ["spine"])
print("\nbake back:", result.message)
now = len([n for n in cmds.ls(long=True)
           if not cmds.objectType(n).startswith("animCurve")])
check("scene back to baseline", now == baseline, "%d -> %d" % (baseline, now))
check("chest animation on the bones at the end",
      drift_of("spine_05", chest_ref) < 0.6,
      "%.3f cm" % drift_of("spine_05", chest_ref))
check("head follows again", drift_of("head", head_ref) < 1.0,
      "%.3f cm" % drift_of("head", head_ref))

cmds.currentTime(0)
cmds.select(clear=True)
print("\n%s" % ("SPINE IK WORKS" if not failures
                else "FAILURES: %s" % failures))
