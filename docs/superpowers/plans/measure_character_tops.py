"""measure_character_tops.py - what one character leaves at the scene's TOP LEVEL (2026-10-02).

mayapy standalone, read-and-throw-away (it adds characters into empty scenes):

    $env:SKELDAR_PLUGIN = '<a SkeldarAnim folder>'   # the build to measure; default: this worktree
    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/measure_character_tops.py

Per catalog row, alone in a new scene: every new world-level DAG node, every new display layer, every
new objectSet the default outliner lists (not a shading group, not a default set). Then the extras on
a Manny rig and on a Manny skeleton: a weapon in the right hand, one on the floor, the Tech Limb,
Camera Setup, a centre of mass, and (the rig) a UE clip retargeted onto it. Run once on the build
before the character groups and once after: the spec quotes both.
"""

import os
import sys
import traceback

import maya.standalone

maya.standalone.initialize(name="python")
import maya.cmds as cmds  # noqa: E402

for _plugin in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(_plugin, quiet=True)
    except RuntimeError:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.environ.get("SKELDAR_PLUGIN") or os.path.join(HERE, "..", "..", "..", "SkeldarAnim")
sys.path.insert(0, os.path.abspath(PLUGIN))
CLIP = "C:/!!!Work/Animations/Export/LongSword_Attack_Right_Heavy_3P.FBX"

import maya_rigs  # noqa: E402
from maya_overrig import builder  # noqa: E402
from maya_scenesetup import armor, camera, catalog, character, equip, skeleton  # noqa: E402

print("PLUGIN", os.path.abspath(PLUGIN))


def tops():
    return set(cmds.ls(assemblies=True, long=True) or [])


def layers():
    return set(cmds.ls(type="displayLayer") or [])


def outliner_sets():
    out = set()
    for s in cmds.ls(type="objectSet") or []:
        if cmds.nodeType(s) != "objectSet":
            continue                       # shadingEngine, ...
        if s in ("defaultLightSet", "defaultObjectSet") or cmds.ls(s, defaultNodes=True):
            continue
        out.add(s)
    return out


def snapshot():
    return tops(), layers(), outliner_sets()


def report(title, before):
    after = snapshot()
    new_tops = sorted(after[0] - before[0])
    print("== %s" % title)
    print("   top level (%d): %s" % (len(new_tops), ", ".join(t.lstrip("|") for t in new_tops)))
    print("   layers (%d): %s" % (len(after[1] - before[1]), ", ".join(sorted(after[1] - before[1]))))
    print("   sets (%d): %s" % (len(after[2] - before[2]), ", ".join(sorted(after[2] - before[2]))))
    return after


def new_root(before):
    fresh = [r for r in builder.character_roots() if r not in before]
    fresh = [r for r in fresh if not any(maya_rigs.under(r, g.group) for g in maya_rigs.rigs())]
    return sorted(fresh, key=lambda p: p.count("|"))[0] if fresh else None


def com(root):
    from maya_com import network
    char = network._character_for(root)
    model, info = network.build_model(char)
    network.create(char, model, info)


def extras(root, label, retarget_rig=None):
    before = snapshot()
    sword, spear = catalog.by_key("LongSword_02"), catalog.by_key("Spear_01")
    print("   ", equip.to_hand(root, "R", sword))
    before = report(label + " + a sword in the right hand", before)
    print("   ", equip.to_floor(root, spear, (120.0, 0.0, 30.0), (1.0, 0.0, 0.0)))
    before = report(label + " + a spear on the floor", before)
    print("   ", armor.equip(root, catalog.armor_by_key("Tech_Limb")))
    before = report(label + " + the Tech Limb", before)
    print("   ", camera.setup(skeleton.resolve_bone(root, camera.BONE), 0, 10))
    before = report(label + " + Camera Setup", before)
    com(root)
    before = report(label + " + a centre of mass", before)
    if retarget_rig is not None and os.path.isfile(CLIP):
        from maya_uebridge import rigimport
        print("   ", rigimport.import_and_retarget(CLIP, "LongSword_Attack_Right_Heavy_3P",
                                                   target="rig", rig=retarget_rig))
        report(label + " + a UE clip retargeted onto it", before)


def main():
    for entry in catalog.CHARACTERS:
        cmds.file(new=True, force=True)
        before = snapshot()
        print("   ", character.add_character(entry))
        report(entry.label + " alone", before)
    cmds.file(new=True, force=True)
    character.add_character(catalog.character_by_key("Manny_Rig"))
    rig = maya_rigs.rigs()[0]
    extras(rig.skeleton_root, "Manny [rig]", retarget_rig=rig)
    cmds.file(new=True, force=True)
    roots = set(builder.character_roots())
    character.add_character(catalog.character_by_key("Manny"))
    extras(new_root(roots), "Manny UE5 [skeleton]")


if __name__ == "__main__":
    try:
        main()
    except Exception:                                              # noqa: BLE001
        traceback.print_exc()
    print("DONE")
    os._exit(0)
