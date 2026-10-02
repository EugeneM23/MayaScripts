"""verify_delete_character.py - Characters > Delete (2026-10-01), in mayapy STANDALONE.

It adds characters and deletes them, so never in the animator's scene:

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/verify_delete_character.py

Phase A: every catalog row added alone, a part of it selected, deleted: the scene back to the
UUIDs it had (but Maya's singleton copies an import makes, trap 121/122), Ctrl+Z bringing every
node back, redo taking them again.
Phase B: a full kit - a rig with a weapon in hand, armor, a camera, a CoM, a palette recolour,
keys and a layer of the animator's; a Manny skeleton with a weapon in hand and one on the floor, a
camera and a CoM; a clip skeleton a third rig is retargeted from - and the animator's cubes: one
constrained to the rig's hand, one riding a rig control through BakeAcross. Three characters in one
press: each part names its character, the confirm says what goes, everything of theirs goes,
nothing of anybody else's, the retargeted rig is disconnected, the rider released, Ctrl+Z.
Phase C: the refusals and Cancel.
"""

import collections
import os
import sys
import time
import traceback

import maya.standalone

maya.standalone.initialize(name="python")
import maya.cmds as cmds  # noqa: E402

for _plugin in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(_plugin, quiet=True)
    except RuntimeError:
        pass

REPO = "C:/!!!Work/MayaScripts/SkeldarAnim"
sys.path.insert(0, REPO)
cmds.undoInfo(state=True, infinity=True)

import maya_rigs  # noqa: E402
import maya_rig_retarget  # noqa: E402
from maya_overrig import builder  # noqa: E402
from maya_scenesetup import armor  # noqa: E402
from maya_scenesetup import camera  # noqa: E402
from maya_scenesetup import catalog  # noqa: E402
from maya_scenesetup import character  # noqa: E402
from maya_scenesetup import colour  # noqa: E402
from maya_scenesetup import connections  # noqa: E402
from maya_scenesetup import deletion  # noqa: E402
from maya_scenesetup import equip  # noqa: E402
from maya_scenesetup import skeleton  # noqa: E402

CLIP = "C:/!!!Work/Animations/Export/LongSword_Attack_Right_Heavy_3P.FBX"
EXCUSED = {"shapeEditorManager", "poseInterpolatorManager", "UsdDefaultSettings"}
FAILED, PASSED = [], []


def gate(name, ok, detail=""):
    (PASSED if ok else FAILED).append(name)
    print("%s  %s%s" % ("PASS" if ok else "FAIL", name, ("  | " + str(detail)) if detail else ""))


def uuids():
    return set(cmds.ls(cmds.ls() or [], uuid=True) or [])


def path(uuid):
    found = cmds.ls(uuid, long=True)
    return found[0] if found else None


def kinds(us):
    c = collections.Counter()
    for u in us:
        p = path(u)
        if p:
            c[cmds.nodeType(p)] += 1
    return dict(c.most_common(12))


def unexcused(us):
    return set(u for u in us if path(u) and cmds.nodeType(path(u)) not in EXCUSED)


def names(us, limit=12):
    return sorted(p for p in (path(u) for u in us) if p)[:limit]


def press(selection, answer=True):
    asked = []
    line = deletion.delete_selected(selection, confirm=lambda text: asked.append(text) or answer)
    return line, (asked[0] if asked else "")


def new_rig(before):
    for rig in maya_rigs.rigs():
        if rig.namespace not in before:
            return rig
    return None


def new_root(before):
    fresh = [r for r in builder.character_roots() if r not in before]
    fresh = [r for r in fresh if not any(maya_rigs.under(r, g.group) for g in maya_rigs.rigs())]
    return sorted(fresh, key=lambda p: p.count("|"))[0] if fresh else None


def mesh_of(root):
    shapes = colour.skinned_shapes(root)
    return cmds.listRelatives(shapes[0], parent=True, fullPath=True)[0] if shapes else None


def _at(root, leaf):
    """A top of the character `root` belongs to, by leaf: `|leaf` at world level (before
    2026-10-02), `<its group>|leaf` in its character group since."""
    group = maya_rigs.group_of(root)
    return (group or "") + "|" + leaf


def world(node):
    return [round(v, 6) for v in cmds.xform(node, query=True, matrix=True, worldSpace=True)]


# ------------------------------------------------------------------ phase A

def phase_a():
    cmds.file(new=True, force=True)
    for entry in catalog.CHARACTERS:
        before = uuids()
        rigs_before = set(r.namespace for r in maya_rigs.rigs())
        roots_before = set(builder.character_roots())
        character.add_character(entry)
        added = uuids() - before
        if catalog.is_rig(entry):
            rig = new_rig(rigs_before)
            part = maya_rigs.node(rig, "FKWrist_R")
            part = (cmds.ls(part, long=True) or [rig.main])[0]
        else:
            root = new_root(roots_before)
            part = mesh_of(root) or root
        start = time.time()
        line, asked = press([part])
        took = time.time() - start
        left = unexcused(uuids() - before)
        gate("A %s: everything its Add brought is gone (selected %s)"
             % (entry.label, part.split("|")[-1]), not left,
             "%s %s" % (kinds(left), names(left)))
        gate("A %s: nothing that stood before is touched" % entry.label,
             before <= uuids(), names(before - uuids()))
        gate("A %s: the confirm names it" % entry.label, "Delete 1 character" in asked, asked[:80])
        if catalog.is_rig(entry):
            gate("A %s: its namespace is gone" % entry.label,
                 not cmds.namespace(exists=":" + rig.namespace), line)
        print("     %s  (%.2f s)" % (line, took))
        cmds.undo()
        gate("A %s: Ctrl+Z brings every node back" % entry.label, added <= uuids(),
             "%d missing" % len(added - uuids()))
        cmds.redo()
        gate("A %s: redo takes them again" % entry.label, not unexcused(uuids() - before))


# ------------------------------------------------------------------ phase B

def phase_b():
    cmds.file(new=True, force=True)
    sword = catalog.by_key("LongSword_02")
    # The others: a Creep skeleton holding a sword, a rig the clip will drive, the animator's cubes.
    roots = set(builder.character_roots())
    character.add_character(catalog.character_by_key("Creep"))
    creep = new_root(roots)
    print("   ", equip.to_hand(creep, "R", sword))
    rigs = set(r.namespace for r in maya_rigs.rigs())
    character.add_character(catalog.character_by_key("Manny_Rig"))
    rig_b = new_rig(rigs)
    held = cmds.polyCube(name="heldCube")[0]
    rider = cmds.polyCube(name="riderCube")[0]
    cmds.setKeyframe(rider, attribute="translateX", time=0, value=0)
    cmds.setKeyframe(rider, attribute="translateX", time=10, value=50)
    s0 = uuids()
    creep_root_at = world(creep)
    creep_space = cmds.listRelatives(equip.occupant(creep, "R")[0], parent=True, fullPath=True)[0]

    # The ones to delete: rig A with its kit.
    rigs = set(r.namespace for r in maya_rigs.rigs())
    character.add_character(catalog.character_by_key("Manny_Rig"))
    rig_a = new_rig(rigs)
    root_a = rig_a.skeleton_root
    print("   ", equip.to_hand(root_a, "R", sword))
    print("   ", armor.equip(root_a, catalog.armor_by_key("Tech_Limb")))
    print("   ", camera.setup(skeleton.resolve_bone(root_a, camera.BONE), 0, 10))
    wrist = cmds.ls(maya_rigs.node(rig_a, "FKWrist_R"), long=True)[0]
    cmds.setKeyframe(wrist, attribute="rotateX", time=0, value=0)
    cmds.setKeyframe(wrist, attribute="rotateX", time=10, value=40)
    colour.paint(colour.character_meshes(root_a), (0.2, 0.8, 0.3), "mine")
    controls = [cmds.ls(maya_rigs.node(rig_a, n), long=True)[0] for n in ("FKWrist_R", "FKElbow_R")]
    cmds.select(controls, replace=True)
    layer = cmds.createDisplayLayer(name="myRigLayer", noRecurse=True)
    hand_a = skeleton.resolve_bone(root_a, "hand_r")
    cmds.parentConstraint(hand_a, held, maintainOffset=True)
    print("   ", connections.bake_across([cmds.ls(rider, long=True)[0], wrist]))

    # The Manny skeleton: a dagger in hand, a spear on the floor, a camera.
    roots = set(builder.character_roots())
    character.add_character(catalog.character_by_key("Manny"))
    manny = new_root(roots)
    print("   ", equip.to_hand(manny, "R", catalog.by_key("Dagger_01")))
    print("   ", equip.to_floor(manny, catalog.by_key("Spear_01"), (120.0, 0.0, 30.0),
                                (1.0, 0.0, 0.0)))
    print("   ", camera.setup(skeleton.resolve_bone(manny, camera.BONE), 0, 10))

    # The centres of mass.
    from maya_com import network
    for root in (root_a, manny):
        char = network._character_for(root)
        model, info = network.build_model(char)
        network.create(char, model, info)

    # A clip the rig B is retargeted from.
    from maya_uebridge import animimport
    animimport.import_clip(CLIP, namespace="clipdel", merge=False)
    clip_joints = [n for n in cmds.namespaceInfo(":clipdel", listOnlyDependencyNodes=True,
                                                 recurse=True, dagPath=True) or []
                   if cmds.objectType(n) == "joint"]
    clip_root = sorted(cmds.ls(clip_joints, long=True), key=lambda p: p.count("|"))[0]
    print("   ", maya_rig_retarget.connect(source_root=clip_root, rig=rig_b))
    holder_b = maya_rigs.node(rig_b, deletion.HOLDER)
    gate("B setup: rig B stands connected to the clip", cmds.objExists(holder_b))
    s1 = uuids()
    held_at = world(held)
    clip_pelvis = [j for j in cmds.ls(clip_joints, long=True) if j.endswith(":pelvis")][0]

    # Which character each part names (read-only).
    chars = deletion.characters()
    label = dict((c.root, c.label) for c in chars)

    def names_of(part):
        picked, _unowned = deletion.choose([cmds.ls(part, long=True)[0]], chars)
        return [c.label for c in picked]

    weapon_a = equip.occupant(root_a, "R")[0]
    piece_a = list(armor.worn(root_a).values())[0][0]
    cam_a = camera.camera_for(skeleton.resolve_bone(root_a, camera.BONE))
    com_a = [g for g in network.find_all() if network.root_of(g) == root_a][0]
    handle_a = network.part(com_a, "handle")
    floor_spear = equip.occupant(manny, "L")[0]
    dagger = equip.occupant(manny, "R")[0]
    cam_m = camera.camera_for(skeleton.resolve_bone(manny, camera.BONE))
    handle_m = network.part([g for g in network.find_all() if network.root_of(g) == manny][0],
                            "handle")
    rig_a_label = label[root_a]
    for part, who in ((wrist, rig_a_label), (mesh_of(root_a), rig_a_label),
                      (hand_a, rig_a_label), (weapon_a, rig_a_label), (piece_a, rig_a_label),
                      (cam_a, rig_a_label), (handle_a, rig_a_label),
                      (mesh_of(manny), label[manny]), (manny + "|pelvis", label[manny]),
                      (dagger, label[manny]), (floor_spear, label[manny]), (cam_m, label[manny]),
                      (handle_m, label[manny]), (_at(manny, "SKM_Manny_Simple"), label[manny]),
                      (_at(manny, "camera1"), label[manny]), (_at(creep, "Armature"), label[creep]),
                      (creep_space, label[creep]), (clip_root, label[clip_root])):
        got = names_of(part)
        gate("B names: %s -> %s" % (part.split("|")[-1], who), got == [who], got)
    gate("B names: the cubes name nobody",
         not deletion.choose([cmds.ls(held, long=True)[0]], chars)[0])

    # The press: a part of each of the three.
    start = time.time()
    line, asked = press([wrist, mesh_of(manny), clip_pelvis])
    took = time.time() - start
    print("     ASKED:\n" + asked)
    print("     LINE: %s  (%.2f s)" % (line, took))
    for text in ("Delete 3 characters", "1 weapon", "1 armor piece", "camera", "centre of mass",
                 "2 weapons", maya_rigs.label(rig_b) + " is retargeted from them", "heldCube"):
        gate("B confirm: says %r" % text, text in asked)

    after = uuids()
    gate("B: everything that stood before the three were added still stands",
         (s0 & s1) <= after, names((s0 & s1) - after))
    left = unexcused(after - s0)
    explained = set()
    for u in left:
        p = path(u)
        if any(maya_rigs.under(p, cmds.ls(c, long=True)[0]) for c in (held, rider)):
            explained.add(u)
            continue
        near = cmds.listConnections(p) or []
        if any(cmds.ls(n, long=True) and any(
                maya_rigs.under(cmds.ls(n, long=True)[0], cmds.ls(c, long=True)[0])
                for c in (held, rider)) for n in near):
            explained.add(u)
    gate("B: nothing of the three is left (only the cubes' own new nodes)",
         not (left - explained), "%s %s" % (kinds(left - explained), names(left - explained)))
    gate("B: their namespaces are gone",
         not any(cmds.namespace(exists=":" + ns) for ns in (rig_a.namespace, "clipdel")))
    gate("B: rig B is disconnected (its holder gone)", not cmds.objExists(holder_b))
    gate("B: rig B itself stands", maya_rigs.find(rig_b.namespace) is not None)
    gate("B: the Creep did not move", world(creep) == creep_root_at)
    gate("B: the Creep keeps its sword and the shared WeaponSpaces group",
         cmds.objExists(creep_space) and bool(equip.occupant(creep, "R")[0]))
    gate("B: the rider is released, shown and keyed",
         not connections.our_constraints(cmds.ls(rider, long=True)[0])
         and cmds.getAttr(rider + ".visibility")
         and bool(cmds.keyframe(rider, query=True, timeChange=True)))
    gate("B: the constrained cube keeps its pose, its constraint gone with its target",
         world(held) == held_at
         and not cmds.listRelatives(held, children=True, type="parentConstraint"),
         (world(held)[12:15], held_at[12:15]))
    gate("B: the animator's layer of the rig's controls is gone", not cmds.objExists(layer))
    gate("B: no proxy is left", not connections.proxies())
    gate("B: the line names the three and the undo", "Ctrl+Z" in line and "disconnected" in line,
         line)

    cmds.undo()
    back = uuids()
    gate("B: Ctrl+Z brings all of it back", s1 <= back, "%d missing %s"
         % (len(s1 - back), kinds(s1 - back)))
    gate("B: Ctrl+Z puts rig B's connection back", cmds.objExists(holder_b))
    cmds.redo()
    gate("B: redo takes them again", not cmds.objExists(holder_b)
         and not cmds.namespace(exists=":" + rig_a.namespace))


# ------------------------------------------------------------------ phase C

def phase_c():
    cmds.file(new=True, force=True)
    roots = set(builder.character_roots())
    character.add_character(catalog.character_by_key("Creep"))
    creep = new_root(roots)
    armature = cmds.listRelatives(creep, parent=True, fullPath=True)[0]
    cube = cmds.ls(cmds.polyCube(name="lonelyCube")[0], long=True)[0]
    before = uuids()
    line, asked = press([])
    gate("C: nothing selected is refused", line == deletion.NOTHING_SELECTED and not asked, line)
    line, asked = press([cube])
    gate("C: a cube alone is refused", line == deletion.NOT_A_CHARACTER and not asked, line)
    line, asked = press([creep + "|pelvis"], answer=False)
    gate("C: Cancel changes nothing", line == deletion.CANCELLED and uuids() == before, line)
    line, asked = press([mesh_of(creep), cube])
    gate("C: a mixed selection deletes the character and keeps the cube",
         cmds.objExists(cube) and not cmds.objExists(creep), line)
    gate("C: the line says the cube stays", "1 selected node belongs to no character" in line, line)
    gate("C: the Creep's Armature went with it", not cmds.objExists(armature), armature)


if __name__ == "__main__":
    for name, phase in (("A", phase_a), ("B", phase_b), ("C", phase_c)):
        print("=== phase", name)
        try:
            phase()
        except Exception:                                          # noqa: BLE001
            traceback.print_exc()
            gate("phase %s ran to the end" % name, False)
    print("\n%d gates, %d failed" % (len(PASSED) + len(FAILED), len(FAILED)))
    for name in FAILED:
        print("FAILED:", name)
    os._exit(0)
