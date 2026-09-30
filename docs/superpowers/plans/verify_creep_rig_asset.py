"""Standalone gates for the shipped Creep rig (assets/Creep_Rig.ma) going through Add Character.

    mayapy verify_creep_rig_asset.py <UE5 clip .fbx> [<the Creep_Sword.fbx it replaces>]

mayapy STANDALONE, an empty scene: Add Character twice with "Creep [rig]" and once with
"Manny [rig]" (the many-rigs rule, 2026-09-08), then a clip retargeted onto the FIRST Creep
through the Retarget button's own function.  Gates: each Creep lands in its own
`Creep_Rig` namespace, is found by `maya_rigs` with its rotation-only mark, arrives at its
bind (every skin BPM * WM = I) with its controls at default, painted, carrying no script
node; the retarget keeps the Creep's bone lengths and copies the source's orientations;
the second Creep and the Manny do not move.  And the weapon, as on every rig: the catalog's
"Creep Sword" added at zero grip sits on weapon_r and drives it; the retarget carries the
clip's weapon_r RELATIVE TO THE HAND (the Creep's arm is longer) with the sword riding it;
Remove Weapon gives the bone its track back.

Since 2026-09-24's frame (catalog `Weapon.frame`, bonedrive.FRAME_ROTATE: «чтобы оси
соответствовали направлению геометрии, но при этом меч сохранил свою позу в руке») the sword's
NODE stands turned by its frame on weapon_r at zero grip, its guard along its own X, the fields
reading 0 0 0 (gates 11, 14); given the asset it replaced (the one with the 45 in its points),
every blade vertex is checked where that one stood.  And a bone that takes the sword over
(Connections' `_drive_bone`, weapon_l) sits on the sword's SOCKET, not on the turned node (15).
"""
import math
import sys

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds
import maya.mel as mel
import maya.api.OpenMaya as om

sys.path.insert(0, "C:/!!!Work/MayaScripts/SkeldarAnim")
for p in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(p, quiet=True)
    except Exception:
        pass
CLIP = sys.argv[1]
OLD_SWORD = sys.argv[2].replace("\\", "/") if len(sys.argv) > 2 else ""
FAILS = []


def gate(n, ok, msg):
    print("%s gate %02d: %s" % ("PASS" if ok else "FAIL", n, msg))
    if not ok:
        FAILS.append(n)


def wm(n):
    return om.MMatrix(cmds.getAttr(n + ".worldMatrix[0]"))


def rot(m):
    return om.MTransformationMatrix(m).rotation(asQuaternion=True)


def ang(a, b):
    q = a.inverse() * b
    return math.degrees(2 * math.acos(max(-1.0, min(1.0, abs(q.w)))))


def pos(n):
    return om.MVector(cmds.xform(n, q=True, ws=True, t=True))


cmds.file(new=True, force=True)
from maya_scenesetup import catalog, character
import maya_rigs, maya_asretarget as ar, maya_rig_retarget as rr

creep = catalog.character_by_key("Creep_Rig")
gate(1, creep is not None and creep.label in catalog.character_labels() and catalog.is_rig(creep),
     "the dropdown offers %s" % catalog.character_labels())
texts = [character.add_character(creep), character.add_character(creep), character.add_character(catalog.character_by_key("Manny_Rig"))]
for t in texts:
    print("   ", t.splitlines()[0])
rigs = dict((r.namespace, r) for r in maya_rigs.rigs())
gate(2, set(rigs) == {"Creep_Rig", "Creep_Rig1", "Manny_Rig"}, "three rigs, each in its own namespace: %s" % sorted(rigs))
h, h2, manny = rigs.get("Creep_Rig"), rigs.get("Creep_Rig1"), rigs.get("Manny_Rig")
gate(3, ar.rotation_mode(h) and ar.rotation_mode(h2) and not ar.rotation_mode(manny),
     "rotation-only mark: Creep %s, Creep1 %s, Manny %s" % (ar.rotation_mode(h), ar.rotation_mode(h2), ar.rotation_mode(manny)))
#  since 2026-09-28 in the layout of the Creep's own FBX: `root` under the Null `Armature`
gate(4, h.skeleton_root == "|Creep_Rig:Armature|Creep_Rig:root" and len(cmds.listRelatives(h.skeleton_root, ad=True, type="joint")) == 90 and cmds.objExists("Creep_Rig:weapon_r") and cmds.objExists("Creep_Rig:weapon_l"),
     "the Creep's skeleton under its Armature: %s, %d joints below it" % (h.skeleton_root, len(cmds.listRelatives(h.skeleton_root, ad=True, type="joint") or [])))
scripts = [s for s in cmds.ls(type="script") if s.startswith(("Creep_Rig", "Manny_Rig"))]
gate(5, not [s for s in scripts if s.startswith("Creep_Rig")], "script nodes the Creep asset brought: %s" % [s for s in scripts if s.startswith("Creep_Rig")])
worst, skins = 0.0, []
for sc in cmds.ls(type="skinCluster"):
    if not sc.startswith("Creep_Rig:"):
        continue
    skins.append(sc)
    for idx in cmds.getAttr(sc + ".matrix", multiIndices=True) or []:
        src = cmds.listConnections("%s.matrix[%d]" % (sc, idx), s=True, d=False)
        if src:
            p = om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (sc, idx))) * wm(src[0])
            worst = max(worst, max(abs(p.getElement(r, c) - (r == c)) for r in range(4) for c in range(4)))
off = ar.posed_controls(rig=h)
gate(6, len(skins) == 5 and worst < 1e-4 and not off, "%d Creep skins at their bind (|BPM*WM - I| %.2e), controls at default %s" % (len(skins), worst, off[:4]))
geo = cmds.listRelatives("|Creep_Rig:Group|Creep_Rig:Geometry", children=True) or []
painted = [m for m in cmds.ls("Creep_Rig:Creep_*", type="mesh") if not cmds.getAttr(m + ".intermediateObject")]
colours = set()
for m in painted:
    for sg in cmds.listConnections(m, type="shadingEngine") or []:
        colours.update(x for x in cmds.ls(cmds.listConnections(sg + ".surfaceShader", s=True, d=False) or [], materials=True)
                       if cmds.attributeQuery("skeldarColour", node=x, exists=True))
gate(7, {"Creep_Rig:Creep_Body", "Creep_Rig:Creep_Face"} <= set(geo) and "Creep_Rig:Creep_Props" not in geo and len(painted) == 5 and colours,
     "Geometry %s; %d meshes painted with %s" % ([g.split(":")[-1] for g in geo], len(painted), sorted(colours)))

# the retarget, onto the FIRST Creep
before = set(cmds.ls(type="joint", long=True))
cmds.namespace(add="clip"); cmds.namespace(set=":clip")
mel.eval('FBXResetImport; FBXImportMode -v add; FBXImportSetMayaFrameRate -v false;')
mel.eval('FBXImport -f "%s";' % CLIP.replace("\\", "/"))
cmds.namespace(set=":")
new = [j for j in cmds.ls(type="joint", long=True) if j not in before]
src = min((j for j in new if not cmds.listRelatives(j, parent=True, type="joint")), key=lambda j: j.count("|"))
S = dict((p.split("|")[-1].split(":")[-1], p) for p in [src] + cmds.listRelatives(src, ad=True, type="joint", fullPath=True))
first, last = cmds.findKeyframe(list(S.values()), which="first"), cmds.findKeyframe(list(S.values()), which="last")
cmds.playbackOptions(min=first, max=last, animationStartTime=first, animationEndTime=last)
def bones(rig):
    return dict((p.split("|")[-1].split(":")[-1], p) for p in [rig.skeleton_root] + cmds.listRelatives(rig.skeleton_root, ad=True, type="joint", fullPath=True))
H, H2, M = bones(h), bones(h2), bones(manny)
rest_t = dict((n, cmds.getAttr(p + ".translate")[0]) for n, p in H.items())
still = dict((p, wm(p)) for p in list(H2.values()) + list(M.values()))

# the Creep's sword from the catalog, as on any rig: Add at zero grip, before the take
from maya_scenesetup import attach, bonedrive, weaponspace
sword_entry = catalog.by_key("Creep_Sword")
cmds.currentTime(first)
weapon, wnote = attach.attach(sword_entry, H["hand_r"], H["weapon_r"], (0, 0, 0), (0, 0, 0))
weapon = cmds.ls(weapon, long=True)[0]
# the frame the node carries: the row's own, then the socket turn (2026-09-30)
FRAME = om.MMatrix(bonedrive.matrix_of(bonedrive.socket_frame(sword_entry.frame), (0, 0, 0)))
off = max(abs(a - b) for a, b in zip(list(wm(weapon)), list(FRAME * wm(H["weapon_r"]))))
#  since 2026-09-24 a weapon lives in its hand's SPACE, outside the skeleton (weaponspace)
gate(11, weaponspace.holding_hand(weapon) == H["hand_r"] and not weapon.startswith(H["root"] + "|")
     and bonedrive.driving_weapon(H["weapon_r"]) and off < 1e-4 and sword_entry.frame == (0.0, 45.0, 0.0),
     "Add 'Creep Sword': %s in hand_r's space (%s) drives weapon_r, standing in its frame %s "
     "(with the socket turn %s) on the bone to %.2e at zero grip %s"
     % (weapon.split("|")[-1], weapon.rsplit("|", 2)[-2], sword_entry.frame,
        bonedrive.socket_frame(sword_entry.frame), off, wnote))


def mesh_points(node, space):
    shape = cmds.listRelatives(node, shapes=True, fullPath=True, noIntermediate=True)[0]
    sel = om.MSelectionList(); sel.add(shape)
    return om.MFnMesh(sel.getDagPath(0)).getPoints(space)


# the axes on the geometry: in the node's own space the guard lies along X, the thickness on Z;
# the fields read the grip, not the model's turn; and, given the asset this one replaced (the 45 in
# its POINTS, the node on the bone), every vertex stands where that one stood at zero grip
local = mesh_points(weapon, om.MSpace.kObject)
guard_x, thick_z = max(abs(p.x) for p in local), max(abs(p.z) for p in local)
fields = bonedrive.measured_grip(weapon, H["weapon_r"])
kept = "not checked (no old asset given)"
kept_ok = True
if OLD_SWORD:
    from maya_scenesetup import attach as _a
    before = set(cmds.ls(assemblies=True))
    old_roots = _a.import_model(OLD_SWORD)
    old_mesh = _a.mesh_transforms(old_roots)[0]
    old_local = mesh_points(old_mesh, om.MSpace.kObject)
    world = mesh_points(weapon, om.MSpace.kWorld)
    bone = wm(H["weapon_r"])
    worst_v = max(world[i].distanceTo(om.MPoint(old_local[i]) * bone) for i in range(len(world)))
    kept_ok = len(old_local) == len(world) and worst_v < 1e-3
    kept = "every vertex where the old asset stood on weapon_r: %.2e cm over %d" % (worst_v, len(world))
    cmds.delete([n for n in cmds.ls(assemblies=True, long=True) if n.lstrip("|") not in before])
gate(14, guard_x > 2 * thick_z and max(abs(v) for v in fields[0] + fields[1]) < 1e-6 and kept_ok,
     "the node's axes on the geometry: guard %.2f along its own X, thickness %.2f on Z; the fields read %s; %s"
     % (guard_x, thick_z, tuple(round(v, 6) for v in fields[0] + fields[1]), kept))

# the size the creature holds it at (2026-09-25, «меч крипа стал меньше чем был изначально»): in the
# creature's own file lowerarm_r scales the hand 1.32 and the sword with it -- 124.017 cm pommel to tip
# (measured in creep_T-pose_draft (1).fbx and the animator's scene before our work); the shrunk asset
# stood 93.952.  Measured in the hand, in world, along the node's own blade axis.
CREATURE_SWORD = 124.017
node_m = wm(weapon)
blade_axis = om.MVector(node_m.getElement(1, 0), node_m.getElement(1, 1), node_m.getElement(1, 2)).normal()
along = [om.MVector(p) * blade_axis for p in mesh_points(weapon, om.MSpace.kWorld)]
length = max(along) - min(along)
gate(16, abs(length - CREATURE_SWORD) < 0.01,
     "the sword in the Creep's hand %.3f cm from pommel to tip (the creature's own %.3f)" % (length, CREATURE_SWORD))

cmds.select(cmds.ls("Creep_Rig:Main")[0], src)
ok, text = rr.run_retarget()
print(text.splitlines()[0][:220])
gate(8, ok and "ROTATIONS ONLY" in text and not cmds.objExists(ar.holder_of(h)), "the button, with a Creep control and the clip selected: ok=%s" % ok)
worst_rot, worst_len, moved = 0.0, 0.0, 0.0
for t in range(int(first), int(last) + 1, max(1, int((last - first) / 10))):
    cmds.currentTime(t)
    for b in ("pelvis", "spine_03", "neck_01", "head", "clavicle_l", "hand_l", "hand_r", "foot_l", "ball_r", "middle_02_r"):
        if b in S:                     # a 3P clip may carry fewer bones (LongSword_Attack_Right_Heavy_3P: no neck_01)
            worst_rot = max(worst_rot, ang(rot(wm(S[b])), rot(wm(H[b]))))
    for n, p in H.items():
        if n not in ("root", "pelvis", "weapon_r", "weapon_l") and not n.startswith("ik_"):   # the weapon bones carry the clip's weapon motion in the hand
            worst_len = max(worst_len, (om.MVector(cmds.getAttr(p + ".translate")[0]) - om.MVector(rest_t[n])).length())
    moved = max(moved, max(max(abs(a - c) for a, c in zip(list(m), list(wm(p)))) for p, m in still.items()))
gate(9, worst_rot < 0.05 and worst_len < 1e-3, "the Creep on the clip's orientations to %.5f deg, its bone lengths kept to %.6f cm" % (worst_rot, worst_len))
gate(10, moved < 1e-6, "the second Creep and the Manny did not move: %.9f" % moved)

# weapon_r took the clip's grip RELATIVE TO THE HAND (a world copy would float off the Creep's
# longer arm), and the sword still rides it at its grip
def rel(bone, hand):
    return wm(bone) * wm(hand).inverse()
def mdiff(a, b):
    return max(abs(x - y) for x, y in zip(list(a), list(b)))
frames = list(range(int(first), int(last) + 1, max(1, int((last - first) / 10))))
worst_rel, worst_grip, track = 0.0, 0.0, {}
has_src = "weapon_r" in S
for t in frames:
    cmds.currentTime(t)
    if has_src:
        worst_rel = max(worst_rel, mdiff(rel(H["weapon_r"], H["hand_r"]), rel(S["weapon_r"], S["hand_r"])))
    worst_grip = max(worst_grip, mdiff(wm(weapon), FRAME * wm(H["weapon_r"])))
    track[t] = rel(H["weapon_r"], H["hand_r"])
moving = max(mdiff(track[frames[0]], m) for m in track.values())
gate(12, has_src and worst_rel < 1e-3 and worst_grip < 1e-3 and bonedrive.driving_weapon(H["weapon_r"]),
     "weapon_r on the clip's weapon_r relative to the hand to %.2e (it moves %.2f in the hand over the take); the sword on it to %.2e"
     % (worst_rel, moving, worst_grip))

# Remove Weapon: the bone takes its animation back and the sword goes
removed = attach.detach(H["hand_r"], H["weapon_r"])
back = 0.0
for t in frames:
    cmds.currentTime(t)
    back = max(back, mdiff(rel(H["weapon_r"], H["hand_r"]), track[t]))
gate(13, not cmds.objExists(weapon) and not bonedrive.driving_weapon(H["weapon_r"]) and not cmds.listRelatives(H["weapon_r"], c=True, type="constraint") and back < 1e-3,
     "Remove Weapon %s: the sword gone, weapon_r free and keyed on its own track to %.2e" % (removed, back))
# a bone that takes the sword over (Connections moves the drive to weapon_l when the left hand holds)
# sits on the sword's SOCKET -- the frame undone -- never on the turned node; on the SECOND Creep, which
# holds nothing yet
from maya_scenesetup import connections
weapon2, _ = attach.attach(sword_entry, H2["hand_r"], H2["weapon_r"], (0, 0, 0), (0, 0, 0))
weapon2 = cmds.ls(weapon2, long=True)[0]
socket = FRAME.inverse() * wm(weapon2)
connections._drive_bone(weapon2, H2["weapon_l"])
cmds.currentTime(first + 1)
cmds.currentTime(first)
on_socket = mdiff(wm(H2["weapon_l"]), FRAME.inverse() * wm(weapon2))
on_weapon_r = mdiff(socket, wm(H2["weapon_r"]))
gate(15, on_socket < 1e-4 and on_weapon_r < 1e-4,
     "weapon_l taking the sword over sits on its socket to %.2e (the socket is weapon_r's own place to %.2e)"
     % (on_socket, on_weapon_r))
print("RESULT: %d of 16 gates failed %s" % (len(FAILS), FAILS))
