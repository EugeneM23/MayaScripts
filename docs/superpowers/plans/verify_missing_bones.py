"""Live checks: the rig builds on a skeleton that is missing bones.

Run in an EMPTY scene through the bridge runner. Builds its own UE4-schema
skeleton -- no `root`, no metacarpals, a spine that stops at `spine_03` and a
neck without `neck_02` -- which is what a suit or an older mannequin actually
gives us, and what broke two things at once:

  * Build did nothing at all on the first press of a session. `build_fk` ran
    OverRig's MEL procs without ever sourcing the toolset, so it raised into
    the Script Editor where nobody was looking. Pressing Switch first went
    through `builder.build`, which does source it, and Build worked ever after.
  * The finger chains stayed behind in world space. Everything that hangs a
    chain asked for `<finger>_metacarpal_<side>_FK_ctrl`, a controller such a
    skeleton never has, so the four fingers of each hand were never attached
    to the hand at all. Only the thumbs, which start at `thumb_01`, followed.
    Finger controllers are no longer built (2026-08-18), so that half is now
    checked as "the resolution still skips the missing bone, and nothing was
    built on it" -- the fix, `chain_root`, is what the spine and neck of this
    skeleton exercise anyway.

No cmds.undo -- the whole script is one command. autoKey is off throughout,
values are read before they are written back, and the test skeleton is
deleted at the end.
"""

import sys

REPO = r"C:/!!!Work/MayaScripts"
if REPO not in sys.path:
    sys.path.append(REPO)

for name in [m for m in list(sys.modules) if m.startswith("maya_overrig")]:
    del sys.modules[name]

import maya.cmds as cmds

import maya_overrig
from maya_overrig import builder, fkcontrols, naming, overrig

KEEP = False          # leave the test skeleton and rig standing afterwards
GROUP = "RigPickerTest_missing_bones"

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


def wiggle():
    """Settle the DAG -- reads straight after a setAttr return stale mixtures."""
    now = cmds.currentTime(query=True)
    cmds.currentTime(now + 1, edit=True)
    cmds.currentTime(now, edit=True)


# ---------------------------------------------------------------------------
# the skeleton: UE4 schema, and deliberately incomplete
# ---------------------------------------------------------------------------

def side_sign(side):
    return 1.0 if side == "l" else -1.0


def build_skeleton():
    """A skeleton with real gaps: no root, no metacarpals, short spine.

    Elbows and knees carry a bend, or OverRig's IK has no plane to solve in.
    """
    spec = [("pelvis", None, (0, 95, 0)),
            ("spine_01", "pelvis", (0, 105, 0)),
            ("spine_02", "spine_01", (0, 117, 0)),
            ("spine_03", "spine_02", (0, 129, 0)),
            ("neck_01", "spine_03", (0, 143, 0)),
            ("head", "neck_01", (0, 152, 0))]

    for side in ("l", "r"):
        s = side_sign(side)
        spec += [
            ("clavicle_" + side, "spine_03", (3 * s, 140, 0)),
            ("upperarm_" + side, "clavicle_" + side, (16 * s, 140, 0)),
            ("lowerarm_" + side, "upperarm_" + side, (43 * s, 140, -2)),
            ("hand_" + side, "lowerarm_" + side, (70 * s, 140, 0)),
            ("thigh_" + side, "pelvis", (9 * s, 92, 0)),
            ("calf_" + side, "thigh_" + side, (9 * s, 52, 3)),
            ("foot_" + side, "calf_" + side, (9 * s, 12, 0)),
            ("ball_" + side, "foot_" + side, (9 * s, 4, 10)),
        ]
        # Four fingers straight off the hand: no metacarpals anywhere.
        for finger, z in (("index", 3), ("middle", 1),
                          ("ring", -1), ("pinky", -3)):
            parent = "hand_" + side
            for index in (1, 2, 3):
                name = "%s_%02d_%s" % (finger, index, side)
                spec.append((name, parent, ((70 + 6 * index) * s, 140, z)))
                parent = name
        parent = "hand_" + side
        for index in (1, 2, 3):
            name = "thumb_%02d_%s" % (index, side)
            spec.append((name, parent,
                         ((70 + 3 * index) * s, 140 - index, 2 + 2 * index)))
            parent = name

    created = []
    for name, parent, position in spec:
        if parent:
            cmds.select(parent, replace=True)
        else:
            cmds.select(clear=True)
        created.append(cmds.joint(name=name, position=position))
    cmds.joint("pelvis", edit=True, orientJoint="xyz",
               secondaryAxisOrient="yup", children=True, zeroScaleOrient=True)
    cmds.group("pelvis", name=GROUP)
    cmds.select(clear=True)
    return created


# ---------------------------------------------------------------------------
# guard: this needs a scene of its own
# ---------------------------------------------------------------------------

existing = [r for r in naming.find_skeleton_roots()
            if not cmds.ls(r, long=True)[0].startswith("|" + GROUP)]
if existing or cmds.ls("RigPicker_*", type="objectSet"):
    print("Run this in an EMPTY scene: found skeletons %s and sets %s" % (
        [r.split("|")[-1] for r in existing],
        cmds.ls("RigPicker_*", type="objectSet") or []))
    raise SystemExit

auto_key = cmds.autoKeyframe(query=True, state=True)
cmds.autoKeyframe(state=False)
cmds.playbackOptions(animationStartTime=0, animationEndTime=10,
                     minTime=0, maxTime=10)
cmds.currentTime(0)

if cmds.objExists(GROUP):
    cmds.delete(GROUP)
build_skeleton()
print("test skeleton: %d joints, no root, no metacarpals\n"
      % len(cmds.ls(type="joint")))

# ---------------------------------------------------------------------------
# section 1: Build works on the first press of a session
# ---------------------------------------------------------------------------

loaded_before = overrig.is_loaded()

window = maya_overrig.show_picker()
cmds.select("pelvis", replace=True)
window.connect_to_selection()
smap = window._scene_map

check("bound without a root bone", "root" not in smap and "pelvis" in smap)
check("skeleton really has no metacarpals",
      not any(j.endswith("metacarpal_l") for j in smap))

# Through the panel's own button path, not the module underneath it: the
# silent failure lived in the gap between the two.
window.fk_limbs_button.setChecked(False)
window.build_rig()
message = window.status.currentMessage()
print(message, "\n")

check("BUILD DID NOT FAIL", "failed" not in message
      and "not loaded" not in message and "Aborted" not in message)
check("OverRig was sourced by Build itself",
      overrig.is_loaded(), "loaded before Build: %s" % loaded_before)
check("all four IK limbs built",
      set(builder.built_limbs()) == set(builder.DEFAULT_IK),
      str(builder.built_limbs()))
check("the torso is FK",
      set(fkcontrols.built_fk_chains()) >= {"pelvis", "spine", "neck"},
      str(fkcontrols.built_fk_chains()))
check("no root controller was invented", not cmds.objExists("root_FK_ctrl"))

# ---------------------------------------------------------------------------
# section 2: the fingers are bones, and they follow the hand as bones
# ---------------------------------------------------------------------------
#
# Trap 21 was found through the fingers, and its FIX is `chain_root` -- which
# is still what every step asks, on this skeleton's spine (no `spine_04`) and
# neck (no `neck_02`) as much as on its hands. The pure resolution is checked
# here as it always was; only the "and therefore it hangs on the hand" half is
# gone, because finger controllers are no longer built (2026-08-18).

table = dict(fkcontrols.CHAINS)
for limb in ("arm_l", "arm_r"):
    side = limb[-1]
    check("no IK hand anchor built for nothing: " + limb,
          not fkcontrols._anchor_in(builder.limb_set(limb),
                                    limb + "_IK_anchor"))
    for finger in ("index", "middle", "ring", "pinky", "thumb"):
        chain = "%s_%s" % (finger, side)
        ctrl = fkcontrols.chain_root_control(table[chain], smap)
        expected = ("%s_01_%s_FK_ctrl" % (finger, side))
        check("chain root skips the missing metacarpal: " + chain,
              ctrl == expected, "%s" % ctrl)
        check("and no such controller was built: " + chain,
              not cmds.objExists(ctrl))
        check("the chain is not recorded: " + chain,
              not fkcontrols.chain_members(chain))

# The measurement the user made by eye: move the hand, the fingers come.
# The bones now, rather than their rings -- same claim, one indirection less.
cmds.currentTime(0)
probes = {"hand_l bone": smap["hand_l"],
          "index_l bone": smap["index_01_l"],
          "pinky_l bone": smap["pinky_01_l"],
          "thumb_l bone": smap["thumb_01_l"]}
before = {k: wpos(v) for k, v in probes.items()}
ik_end = builder.ik_control("arm_l", "end")
rest = cmds.getAttr(ik_end + ".translate")[0]
cmds.setAttr(ik_end + ".translateY", rest[1] - 20.0)
wiggle()
after = {k: wpos(v) for k, v in probes.items()}
cmds.setAttr(ik_end + ".translate", *rest)
wiggle()
travelled = {k: dist(after[k], before[k]) for k in probes}
for name in sorted(probes):
    check("TRAVELS WITH THE IK HAND: " + name,
          abs(travelled[name] - travelled["hand_l bone"]) < 0.5,
          "%.3f cm (hand %.3f)" % (travelled[name], travelled["hand_l bone"]))
for name in sorted(probes):
    check("returns to rest: " + name,
          dist(wpos(probes[name]), before[name]) < 0.01)

# ---------------------------------------------------------------------------
# section 3: the fingers survive a switch in both directions
# ---------------------------------------------------------------------------

print("\n" + fkcontrols.switch_limbs(smap, ["arm_l"])[2] + "\n")
check("arm_l is FK now", bool(fkcontrols.chain_members("arm_l"))
      and "arm_l" not in builder.built_limbs())
for finger in ("index", "middle", "ring", "pinky", "thumb"):
    bone = smap[finger + "_01_l"]
    check("finger bone rides the hand bone (FK arm): " + finger,
          is_under(bone, smap["hand_l"]))
    check("no controller appeared for it: " + finger,
          not cmds.objExists(
              fkcontrols.chain_root_control(table[finger + "_l"], smap)))

print("\n" + fkcontrols.switch_limbs(smap, ["arm_l"])[2] + "\n")
check("arm_l is IK again", "arm_l" in builder.built_limbs())
check("no anchor built by the switches either",
      not fkcontrols._anchor_in(builder.limb_set("arm_l"),
                                "arm_l_IK_anchor"))
for finger in ("index", "middle", "ring", "pinky", "thumb"):
    check("finger bone rides the hand bone (IK arm): " + finger,
          is_under(smap[finger + "_01_l"], smap["hand_l"]))

# ---------------------------------------------------------------------------
# section 4: it all comes apart again
# ---------------------------------------------------------------------------

cmds.select([smap[j] for j in smap], replace=True)
ik_hit, fk_hit = fkcontrols.bake_targets(smap)
print("\n" + fkcontrols.bake_selection(smap, ik_hit, fk_hit) + "\n")

check("no IK limbs left", not builder.built_limbs(),
      str(builder.built_limbs()))
check("no FK chains left", not fkcontrols.built_fk_chains(),
      str(fkcontrols.built_fk_chains()))
check("no controllers left", not cmds.ls("*_FK_ctrl"),
      str(cmds.ls("*_FK_ctrl") or [])[:80])
still_constrained = [j for j in cmds.ls(type="joint")
                     if cmds.listRelatives(j, children=True,
                                           type="constraint")]
check("no bone is still constrained", not still_constrained,
      str(still_constrained[:4]))

# ---------------------------------------------------------------------------
# section 5: a failure is never silent again
# ---------------------------------------------------------------------------

def boom():
    raise RuntimeError("deliberate")


window._run("Probe", window.build_button, boom)
check("A FAILING ACTION REACHES THE STATUS BAR",
      "Probe failed" in window.status.currentMessage()
      and "deliberate" in window.status.currentMessage(),
      window.status.currentMessage())
check("the button is usable again after a failure",
      window.build_button.isEnabled())

# ---------------------------------------------------------------------------

if not KEEP:
    window.close()
    for node in (cmds.ls("|" + GROUP, long=True)
                 + (cmds.ls("|*_IK_feet", "|*_IK_knee", "|*_IK_strech_gr",
                            long=True) or [])):
        if cmds.objExists(node):
            cmds.delete(node)
    for s in cmds.ls("RigPicker_*", type="objectSet") or []:
        cmds.delete(s)

cmds.autoKeyframe(state=auto_key)
print("\n%d check(s) failed%s" % (len(failures),
                                  ": " + ", ".join(failures) if failures
                                  else " - all green"))
