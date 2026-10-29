"""Standalone gates for Connections' pick-then-apply (2026-10-29).

    mayapy verify_connections_apply.py [out.txt]

mayapy STANDALONE, the plugin's Manny_Rig, a fresh scene per case (spec
docs/superpowers/specs/2026-10-29-connections-pick-then-apply-design.md). A press is the card's
own command object, called as the button calls it; the card itself is not built (cmds.window
answers False in batch), so every painter and every status write is the no-op it is with no
panel - what is gated here is the picks, the bake and the settle.

A  Body: IK picked on Arm R and FK on Leg L - the scene unmoved, both in `picks`; the tab's
   Apply all bakes both in ONE undo chunk (one Ctrl+Z puts both blends back), the picks gone;
   a limb picked at what it already shows records nothing; Apply all with nothing picked says so.
B  Body, a row's own check: the W of the right arm applied by its check alone (a Double knot
   World, the leg untouched), one Ctrl+Z; and a REFUSAL - a limb whose blend is driven - leaves
   its pick standing with the scene unmoved.
C  Weapon, the aim row: Aim Mode picked, the weapon not aimed yet; the row's check aims it and
   the pick drops, one Ctrl+Z; and the tab's Apply all with only an aim pick never reads the
   three parent collections (there is no panel to read).
D  Camera: Root + Position only picked, the row's check moves the control, one Ctrl+Z; the aim
   row the same; the tab's Apply all takes a parent pick and an aim pick in ONE chunk.
E  The picks are ONE set per character: reading a second rig's drops the first's.

The weapon's three parent rows are not here: their apply goes through OverRig's
apply_Parent_in/_out, which read the time slider and die in mayapy (verify_connections.py, a GUI
Maya, is their proof).
"""
import io
import sys
import traceback

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

REPO = "C:/!!!Work/MayaScripts"
sys.path.insert(0, REPO + "/SkeldarAnim")
for p in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:                                        # noqa: BLE001
        pass

from maya_scenesetup import (bonedrive, camera, cameraaim, catalog,  # noqa: E402
                             character, connections as cx, equip, fkik, ikworld,
                             pending, weaponaim)
import maya_rigs  # noqa: E402

OUT = io.open(sys.argv[1], "w", encoding="utf-8") if len(sys.argv) > 1 else None
RESULTS = []
CASE = ["-"]


def say(*parts):
    line = " ".join(str(p) for p in parts)
    print(line)
    sys.stdout.flush()
    if OUT is not None:
        OUT.write(line + "\n")
        OUT.flush()


def gate(name, ok, value=""):
    RESULTS.append(bool(ok))
    say("%s %02d %s: %s %s" % ("PASS" if ok else "FAIL", len(RESULTS), CASE[0], name, value))
    return bool(ok)


def wm(node):
    return om.MMatrix(cmds.getAttr(node + ".worldMatrix[0]"))


def moved(a, b):
    return max(abs(a[12 + i] - b[12 + i]) for i in range(3))


def node(rig, leaf):
    return cmds.ls(maya_rigs.node(rig, leaf), long=True)[0]


def blend(rig, kind, side):
    """FKIKArm_R.FKIKBlend (0 FK, 10 IK) - what the limb shows."""
    return cmds.getAttr(node(rig, fkik.FKIK_NODE.format(kind, side))
                        + "." + fkik.BLEND_ATTR)


def bone(root, name):
    for j in [root] + (cmds.listRelatives(root, allDescendents=True, type="joint",
                                          fullPath=True) or []):
        if j.split("|")[-1].split(":")[-1] == name:
            return j
    return None


def fresh(end=24):
    cmds.file(new=True, force=True)
    cmds.undoInfo(state=True, infinity=True)
    cmds.currentUnit(time="ntsc")
    cmds.playbackOptions(min=0, max=end, animationStartTime=0, animationEndTime=end)
    cmds.currentTime(0)
    character.add_character(catalog.character_by_key("Manny_Rig"))
    rig = maya_rigs.rigs()[0]
    cmds.select(clear=True)
    pending.clear()
    return rig


def arm_key(side):
    return pending.limb_key(fkik.ARM, side)


def leg_key(side):
    return pending.limb_key(fkik.LEG, side)


# ------------------------------------------------------------------ A: the body tab

def case_a():
    CASE[0] = "A"
    say("--- A: the Body tab's picks and its Apply all")
    rig = fresh()
    shown = (blend(rig, fkik.ARM, "R"), blend(rig, fkik.LEG, "L"))
    #  the shipped rig stands every limb in FK: both picks below are a real change
    gate("the rig stands arm R and leg L in FK", shown == (0, 0), "blends %s" % (shown,))

    cx._press_limb("R", fkik.IK, fkik.ARM)()
    cx._press_limb("L", fkik.IK, fkik.LEG)()
    chosen = cx.picks(rig)
    gate("two picks, nothing baked",
         chosen == {arm_key("R"): fkik.IK, leg_key("L"): fkik.IK}
         and (blend(rig, fkik.ARM, "R"), blend(rig, fkik.LEG, "L")) == shown,
         "%s, blends %s" % (sorted(chosen), (blend(rig, fkik.ARM, "R"),
                                             blend(rig, fkik.LEG, "L"))))

    #  a pick at what the scene already shows records nothing (pending.record drops it)
    cx._press_limb("R", fkik.FK, fkik.LEG)()
    gate("a pick at what it already shows records nothing",
         cx.picks(rig) == {arm_key("R"): fkik.IK, leg_key("L"): fkik.IK},
         sorted(cx.picks(rig)))

    text = cx._press_apply_body()
    after = (blend(rig, fkik.ARM, "R"), blend(rig, fkik.LEG, "L"))
    gate("Apply all baked both limbs", after == (10, 10), "blends %s - %s" % (after, text))
    gate("the picks are gone", cx.picks(rig) == {}, cx.picks(rig))

    cmds.undo()
    back = (blend(rig, fkik.ARM, "R"), blend(rig, fkik.LEG, "L"))
    gate("ONE Ctrl+Z puts both limbs back", back == shown, "blends %s" % (back,))

    pending.clear()
    gate("Apply all with nothing picked says so", cx._press_apply_body() == cx.NOTHING_PICKED)


# ------------------------------------------------------------------ B: a row's own check

def case_b():
    CASE[0] = "B"
    say("--- B: a row's own check, and a refusal that leaves its pick")
    rig = fresh()
    leg_shown = blend(rig, fkik.LEG, "R")

    #  the W chip and the camera's Position only chip are read off the panel
    #  (cmds.checkBox), so the pick they record is recorded here directly
    cx.remember(rig, {arm_key("R"): fkik.IK, pending.world_key(fkik.ARM, "R"): True})
    text = cx._press_limb_apply("R", fkik.ARM)()
    control = node(rig, "IKArm_R")
    knot = ikworld.knot_of(control)
    gate("the row's check put the right arm in world", bool(knot), "%s - %s" % (knot, text))
    gate("the leg it did not name is untouched", blend(rig, fkik.LEG, "R") == leg_shown)
    gate("its picks are gone", cx.picks(rig) == {}, cx.picks(rig))

    cmds.undo()
    gate("ONE Ctrl+Z takes the row's press back",
         not ikworld.knot_of(control) and blend(rig, fkik.ARM, "R") == 0,
         "knot %s, blend %s" % (ikworld.knot_of(control), blend(rig, fkik.ARM, "R")))

    #  a refusal: the left arm's blend driven by a node of the animator's
    driver = cmds.createNode("multDoubleLinear")
    cmds.connectAttr(driver + ".output",
                     node(rig, fkik.FKIK_NODE.format(fkik.ARM, "L"))
                     + "." + fkik.BLEND_ATTR)
    before = blend(rig, fkik.ARM, "L")
    cx.remember(rig, {arm_key("L"): fkik.IK})
    text = cx._press_limb_apply("L", fkik.ARM)()
    gate("a refused press leaves its pick standing",
         cx.picks(rig) == {arm_key("L"): fkik.IK}, "%s - %s" % (cx.picks(rig), text))
    gate("and the scene unmoved", blend(rig, fkik.ARM, "L") == before,
         "blend %s" % blend(rig, fkik.ARM, "L"))
    gate("the refusal names itself", bool(text) and text != cx.NOTHING_PICKED, text)


# ------------------------------------------------------------------ C: the weapon's aim row

def case_c():
    CASE[0] = "C"
    say("--- C: the Weapon tab's aim row")
    rig = fresh(20)
    root = rig.skeleton_root
    say("   ", equip.to_hand(root, "R", catalog.by_key("LongSword_02")))
    sword = bonedrive.driving_weapon(bone(root, "weapon_r"))
    gate("a sword in the right hand", bool(sword), sword)

    cx._press_aim_pick(cx.AIM_ON)()
    gate("Aim Mode picked, the weapon not aimed yet",
         cx.picks(rig) == {pending.AIM: True} and not weaponaim.is_aimed(sword),
         cx.picks(rig))

    text = cx._press_aim_apply()
    gate("the row's check aims it", weaponaim.is_aimed(sword), text)
    gate("the pick drops once it came true", cx.picks(rig) == {}, cx.picks(rig))

    cmds.undo()
    gate("ONE Ctrl+Z takes Aim Mode back", not weaponaim.is_aimed(sword))

    #  Apply all over an aim pick alone must not reach the three parent collections:
    #  there is no panel, so cx.menus() would raise
    cx.remember(rig, {pending.AIM: True})
    text = cx._press_apply_all()
    gate("the tab's Apply all takes the aim alone, reading no parent row",
         weaponaim.is_aimed(sword) and cx.picks(rig) == {}, text)
    cmds.undo()


# ------------------------------------------------------------------ D: the camera tab

def case_d():
    CASE[0] = "D"
    say("--- D: the Camera tab")
    rig = fresh(20)
    cmds.select(node(rig, "Main"))
    camera_bone = node(rig, "camera_root")
    say("   setup:", camera.setup(camera_bone, 0, 20))

    #  a move re-parents the control, so its path is read again every time (trap 16)
    def ctl():
        return camera.control_for(camera_bone)

    gate("a camera control under Main", camera.parent_choice(ctl()) == "Main",
         "%s - %s" % (ctl(), camera.parent_choice(ctl())))
    stood = wm(ctl())

    cx._press_camera_pick("Root")()
    cx.remember(rig, dict(cx.picks(rig), **{pending.CAMERA_POSITION: True}))
    gate("the parent and Position only picked, the control unmoved",
         cx.picks(rig) == {pending.CAMERA: "Root", pending.CAMERA_POSITION: True}
         and moved(wm(ctl()), stood) < 1e-9, cx.picks(rig))

    text = cx._press_camera_parent()
    gate("the row's check moved it onto Root, position only",
         camera.parent_choice(ctl()) == "Root" and camera.is_position_only(ctl())
         and moved(wm(ctl()), stood) < 1e-6,
         "%s, position only %s, %.2e cm - %s" % (camera.parent_choice(ctl()),
                                                 camera.is_position_only(ctl()),
                                                 moved(wm(ctl()), stood), text))
    gate("its picks are gone", cx.picks(rig) == {}, cx.picks(rig))

    cmds.undo()
    gate("ONE Ctrl+Z puts the camera back under Main",
         camera.parent_choice(ctl()) == "Main" and not camera.is_position_only(ctl()),
         camera.parent_choice(ctl()))

    cx._press_camera_aim_pick(cx.AIM_ON)()
    gate("the camera's Aim Mode picked, not aimed yet",
         cx.picks(rig) == {pending.CAMERA_AIM: True} and not cameraaim.is_aimed(ctl()),
         cx.picks(rig))
    text = cx._press_camera_aim_apply()
    gate("the aim row's check aims the camera",
         cameraaim.is_aimed(ctl()) and cx.picks(rig) == {}, text)
    cmds.undo()
    gate("ONE Ctrl+Z takes it back", not cameraaim.is_aimed(ctl()))

    #  the tab's Apply all: a parent pick and an aim pick in one chunk
    cx.remember(rig, {pending.CAMERA: "Head", pending.CAMERA_AIM: True})
    text = cx._press_apply_camera()
    gate("Apply all took the parent and the aim",
         camera.parent_choice(ctl()) == "Head" and cameraaim.is_aimed(ctl())
         and cx.picks(rig) == {},
         "%s, aimed %s - %s" % (camera.parent_choice(ctl()),
                                cameraaim.is_aimed(ctl()), text))
    cmds.undo()
    gate("ONE Ctrl+Z takes both back",
         camera.parent_choice(ctl()) == "Main" and not cameraaim.is_aimed(ctl()),
         "%s, aimed %s" % (camera.parent_choice(ctl()), cameraaim.is_aimed(ctl())))


# ------------------------------------------------------------------ E: one set per character

def case_e():
    CASE[0] = "E"
    say("--- E: the picks are one set, the character's own")
    rig = fresh()
    character.add_character(catalog.character_by_key("Manny_Rig"))
    cmds.select(clear=True)
    second = [r for r in maya_rigs.rigs() if r.namespace != rig.namespace][0]
    gate("two rigs", bool(second.namespace) and second.namespace != rig.namespace,
         "%s, %s" % (rig.namespace, second.namespace))

    cx.remember(rig, {arm_key("R"): fkik.IK})
    gate("the first rig's pick", cx.picks(rig) == {arm_key("R"): fkik.IK})
    gate("the second rig has none of it", cx.picks(second) == {}, cx.picks(second))
    gate("and reading the second dropped the first's", cx.picks(rig) == {}, cx.picks(rig))


for case in (case_a, case_b, case_c, case_d, case_e):
    try:
        case()
    except Exception:                                        # noqa: BLE001
        say(traceback.format_exc())
        RESULTS.append(False)

say("%d of %d gates failed" % (RESULTS.count(False), len(RESULTS)))
if OUT is not None:
    OUT.close()
