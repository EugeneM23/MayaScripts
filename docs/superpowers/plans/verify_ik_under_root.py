"""Live checks: IK rigs ride the root control, fingers stay visible.

Run inside Maya through the bridge runner (see the plan; the runner's
explicit globals dict is what lets these helpers see module-level names).
Binds explicitly to `root`, resets the scene from ANY state, then walks the
flow with assertions at every step. No cmds.undo -- the whole script is one
command, and undoing reverts a prior chunk. Values are read before they are
written back; autoKey is off throughout.
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


def is_under(child, parent):
    if not (child and parent and cmds.objExists(child)
            and cmds.objExists(parent)):
        return False
    return cmds.ls(child, long=True)[0].startswith(
        cmds.ls(parent, long=True)[0] + "|")


def visible(node):
    """Effective visibility: the node's flag and every ancestor's."""
    if not cmds.objExists(node):
        return False
    path = cmds.ls(node, long=True)[0]
    while path:
        if not cmds.getAttr(path + ".visibility"):
            return False
        path = path.rsplit("|", 1)[0]
    return True


def wiggle():
    """Settle the DAG -- reads straight after a setAttr return stale mixtures."""
    now = cmds.currentTime(query=True)
    cmds.currentTime(now + 1, edit=True)
    cmds.currentTime(now, edit=True)


def stray_ik_roots():
    return [n.split("|")[-1] for n in
            (cmds.ls("|*_IK_feet", "|*_IK_knee", "|*_IK_strech_gr",
                     long=True) or [])]


def node_count():
    return len([n for n in cmds.ls(long=True)
                if not cmds.objectType(n).startswith("animCurve")])


FINGER_CTRLS = [fkcontrols.controller_name(j) for j in
                ("index_metacarpal_l", "index_01_l", "thumb_01_l",
                 "pinky_metacarpal_r", "middle_02_r")]

auto_key = cmds.autoKeyframe(query=True, state=True)
cmds.autoKeyframe(state=False)

window = maya_overrig.show_picker()
cmds.select("root", replace=True)
window.connect_to_selection()
smap = window._scene_map

# --- reset from ANY state ---------------------------------------------------
if builder.has_build():
    builder.bake_limbs(smap, builder.built_limbs())
if fkcontrols.has_fk():
    fkcontrols.bake_fk(smap)
bones = [smap[b.joint] for b in bodymap.BUTTONS if b.joint in smap
         and cmds.objExists(smap[b.joint])]
constrained = [b for b in bones
               if cmds.listRelatives(b, children=True, type="constraint")]
if constrained:
    print("reset: sweeping %d constrained bones" % len(constrained))
    overrig.fast_bake(constrained)
    overrig.delete_constraint_attributes(constrained)
    for b in constrained:
        for con in cmds.listRelatives(b, children=True, type="constraint",
                                      fullPath=True) or []:
            if cmds.objExists(con):
                cmds.delete(con)
for s in cmds.ls("RigPicker_*", type="objectSet") or []:
    if not overrig.set_members(s):
        cmds.delete(s)
for n in cmds.ls("|*_IK_feet", "|*_IK_knee", "|*_IK_strech_gr",
                 long=True) or []:
    print("reset: deleting stray", n)
    cmds.delete(n)

baseline = node_count()
print("baseline non-anim nodes: %d\n" % baseline)

# --- hybrid build -----------------------------------------------------------
print(fkcontrols.rebuild(smap, fk_limbs=False), "\n")

# --- section 1: fingers are visible on the IK hands -------------------------
for ctrl in FINGER_CTRLS:
    check("finger control exists: " + ctrl, cmds.objExists(ctrl))
    check("FINGER CONTROL IS VISIBLE: " + ctrl, visible(ctrl))

for limb in ("arm_l", "arm_r"):
    anchor = fkcontrols._limb_anchor(smap, limb)
    check("anchor transform is visible: " + limb,
          bool(anchor) and cmds.getAttr(anchor + ".visibility") == 1,
          str(anchor))
    shapes = cmds.listRelatives(anchor, shapes=True, fullPath=True) or []
    check("anchor shape is hidden: " + limb,
          bool(shapes) and all(cmds.getAttr(s + ".visibility") == 0
                               for s in shapes),
          str(shapes))
    check("fingers hang on the anchor: " + limb,
          is_under(fkcontrols.controller_name(
              "index_metacarpal_" + limb[-1]), anchor))

print("\n%s" % ("SECTIONS SO FAR PASS" if not failures
                else "FAILURES: %s" % failures))
cmds.autoKeyframe(state=auto_key)
