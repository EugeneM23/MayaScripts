"""Live checks for the spline-IK spine v3.

The bottom node carries the pelvis (its controller re-hung inside), the top
control drives spine_04 -- one bone below the chest tip -- and spine_05
rides with its own keys. Built on top of FK root+pelvis chains, the way
every real flow reaches it.

Run inside Maya through the bridge. Binds explicitly to `root`. No undo;
attribute writes restore the read value (constrained channels rest != 0).
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
    """Temporarily add to an attribute, with clean measurement hygiene.

    autoKeyframe goes off for the duration -- the user runs with it ON,
    and a scripted poke at a keyed channel writes real keys otherwise.
    A time wiggle after unkeyed writes forces a full evaluation: reads
    without a time change return stale mixtures over the port.
    """

    def __init__(self, plug, delta):
        self.plug = plug
        self.delta = delta

    def _settle(self):
        now = cmds.currentTime(query=True)
        cmds.currentTime(now + 1)
        cmds.currentTime(now)

    def __enter__(self):
        self.autokey = cmds.autoKeyframe(query=True, state=True)
        cmds.autoKeyframe(state=False)
        self.rest = cmds.getAttr(self.plug)
        self.keyed = bool(cmds.keyframe(self.plug, query=True,
                                        timeChange=True))
        cmds.setAttr(self.plug, self.rest + self.delta)
        if not self.keyed:
            self._settle()

    def __exit__(self, *_exc):
        cmds.setAttr(self.plug, self.rest)
        self._settle()
        cmds.autoKeyframe(state=self.autokey)


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
spine04_ref = snap("spine_04")
mid_ref = snap("spine_03")
head_ref = snap("head")
pelvis_ref = snap("pelvis")

# --- FK root+pelvis first (the real precondition), then spine IK ---------------
count, message = fkcontrols.build_fk(smap, only=["root", "pelvis"])
print("build root+pelvis FK:", message)
pelvis_ctrl = fkcontrols.controller_name("pelvis")
root_ctrl = fkcontrols.controller_name("root")
check("pelvis controller exists", cmds.objExists(pelvis_ctrl))

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


check("top control resolves exactly", is_ctrl(top, "IKSpine_top"), str(top))
check("mid control resolves exactly", is_ctrl(mid, "IKSpine_mid"), str(mid))
check("bottom control resolves exactly", is_ctrl(bot, "IKSpine_bot"),
      str(bot))
hipdrive = fkcontrols._spine_anchor("IKSpine_hipdrive")
check("PELVIS CONTROLLER RIDES THE BOTTOM NODE'S DRIVE GROUP",
      bool(hipdrive) and is_under(pelvis_ctrl, hipdrive), str(hipdrive))

check("no drift: spine_04 (the driven chest)",
      drift_of("spine_04", spine04_ref) < 1.0,
      "%.3f cm" % drift_of("spine_04", spine04_ref))
check("no drift: spine_05 rides with its keys",
      drift_of("spine_05", chest_ref) < 0.6,
      "%.3f cm" % drift_of("spine_05", chest_ref))
check("small drift: middle (projection bound)",
      drift_of("spine_03", mid_ref) < 2.0,
      "%.3f cm" % drift_of("spine_03", mid_ref))
check("no drift: pelvis (re-baked into the bottom node)",
      drift_of("pelvis", pelvis_ref) < 0.5,
      "%.3f cm" % drift_of("pelvis", pelvis_ref))

# --- behaviour ---------------------------------------------------------------
cmds.currentTime(0)

s4_0 = wpos(smap["spine_04"])
s5_0 = wpos(smap["spine_05"])
with pushed(top + ".translateZ", 10):
    s4_moved = dist(s4_0, wpos(smap["spine_04"]))
    s5_moved = dist(s5_0, wpos(smap["spine_05"]))
check("top drives spine_04", s4_moved > 5, "%.2f cm" % s4_moved)
check("spine_05 rides along", s5_moved > 5, "%.2f cm" % s5_moved)

pelvis0 = wpos(smap["pelvis"])
s4_0 = wpos(smap["spine_04"])
with pushed(bot + ".translateZ", 8):
    pelvis_moved = dist(pelvis0, wpos(smap["pelvis"]))
    s4_moved = dist(s4_0, wpos(smap["spine_04"]))
check("BOTTOM MOVES THE PELVIS", pelvis_moved > 6,
      "%.2f cm" % pelvis_moved)
check("chest mostly stays during the hip sway", s4_moved < 2.5,
      "%.2f cm" % s4_moved)

mid_w0 = cmds.xform(mid, query=True, worldSpace=True, translation=True)
with pushed(top + ".translateZ", 10):
    mid_moved = dist(mid_w0, cmds.xform(mid, query=True, worldSpace=True,
                                        translation=True))
check("middle follows the top at ~50%", 3.5 < mid_moved < 6.5,
      "%.2f cm (want ~5)" % mid_moved)

with pushed(bot + ".translateZ", 10):
    mid_moved = dist(mid_w0, cmds.xform(mid, query=True, worldSpace=True,
                                        translation=True))
check("middle follows the hips at ~50%", 3.5 < mid_moved < 6.5,
      "%.2f cm (want ~5)" % mid_moved)

# The mid-bends-the-curve mechanics are already exercised by the 50/50
# checks (blend -> control -> cluster -> curve -> waist). Poking the keyed
# channels here would rewrite curve tangents and damage the animation the
# later drift checks measure, so animatability is checked structurally.
free = all(not cmds.getAttr(mid + "." + a, lock=True)
           and cmds.getAttr(mid + "." + a, keyable=True)
           for a in ("translateX", "translateY", "translateZ",
                     "rotateX", "rotateY", "rotateZ"))
check("middle control is animatable (channels free)", free)

# The general pelvis control keeps working, and reads as a hip control:
# hips (and the spine base) move, the chest stays.
pelvis0 = wpos(smap["pelvis"])
s4_0 = wpos(smap["spine_04"])
with pushed(pelvis_ctrl + ".translateX", 8):
    pelvis_moved = dist(pelvis0, wpos(smap["pelvis"]))
    s4_moved = dist(s4_0, wpos(smap["spine_04"]))
check("pelvis control still moves the pelvis", pelvis_moved > 6,
      "%.2f cm" % pelvis_moved)
check("chest planted under the pelvis control too", s4_moved < 2.5,
      "%.2f cm" % s4_moved)

# Root motion carries the whole rig.
s4_0 = wpos(smap["spine_04"])
pelvis0 = wpos(smap["pelvis"])
with pushed(root_ctrl + ".translateX", 10):
    s4_moved = dist(s4_0, wpos(smap["spine_04"]))
    pelvis_moved = dist(pelvis0, wpos(smap["pelvis"]))
check("root control carries the chest", s4_moved > 8,
      "%.2f cm" % s4_moved)
check("root control carries the pelvis", pelvis_moved > 8,
      "%.2f cm" % pelvis_moved)

# --- picker resolution ----------------------------------------------------------
resolution = window._resolution()
check("picker: spine IK circles live",
      all(k in resolution for k in ("spine_ik_top", "spine_ik_mid",
                                    "spine_ik_bot")))
check("picker: FK spine buttons dimmed", "spine_03" not in resolution)
check("picker: pelvis FK button live (controller survived)",
      "pelvis" in resolution)

# --- teardown: FK first (frees the pelvis controller), then the spine ----------
removed, message = fkcontrols.bake_fk(smap)
print("\nbake FK back:", message)
result = builder.bake_limbs(smap, ["spine"])
print("bake spine back:", result.message)

now = len([n for n in cmds.ls(long=True)
           if not cmds.objectType(n).startswith("animCurve")])
check("scene back to baseline", now == baseline, "%d -> %d" % (baseline, now))
check("chest animation on the bones at the end",
      drift_of("spine_05", chest_ref) < 0.7,
      "%.3f cm" % drift_of("spine_05", chest_ref))
check("pelvis animation on the bones at the end",
      drift_of("pelvis", pelvis_ref) < 0.5,
      "%.3f cm" % drift_of("pelvis", pelvis_ref))
check("head follows again", drift_of("head", head_ref) < 1.2,
      "%.3f cm" % drift_of("head", head_ref))

cmds.currentTime(0)
cmds.select(clear=True)
print("\n%s" % ("SPINE IK WORKS" if not failures
                else "FAILURES: %s" % failures))
