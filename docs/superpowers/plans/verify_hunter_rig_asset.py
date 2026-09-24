"""Standalone gates for the shipped Hunter rig (assets/Hunter_Rig.ma) going through Add Character.

    mayapy verify_hunter_rig_asset.py <UE5 clip .fbx>

mayapy STANDALONE, an empty scene: Add Character twice with "Hunter [rig]" and once with
"Manny [rig]" (the many-rigs rule, 2026-09-08), then a clip retargeted onto the FIRST Hunter
through the Retarget button's own function.  Gates: each Hunter lands in its own
`Hunter_Rig` namespace, is found by `maya_rigs` with its rotation-only mark, arrives at its
bind (every skin BPM * WM = I) with its controls at default, painted, carrying no script
node; the retarget keeps the Hunter's bone lengths and copies the source's orientations;
the second Hunter and the Manny do not move.  And the weapon, as on every rig: the catalog's
"Hunter Sword" added at zero grip sits on weapon_r and drives it; the retarget carries the
clip's weapon_r RELATIVE TO THE HAND (the Hunter's arm is longer) with the sword riding it;
Remove Weapon gives the bone its track back.
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

hunter = catalog.character_by_key("Hunter_Rig")
gate(1, hunter is not None and hunter.label in catalog.character_labels() and catalog.is_rig(hunter),
     "the dropdown offers %s" % catalog.character_labels())
texts = [character.add_character(hunter), character.add_character(hunter), character.add_character(catalog.character_by_key("Manny_Rig"))]
for t in texts:
    print("   ", t.splitlines()[0])
rigs = dict((r.namespace, r) for r in maya_rigs.rigs())
gate(2, set(rigs) == {"Hunter_Rig", "Hunter_Rig1", "Manny_Rig"}, "three rigs, each in its own namespace: %s" % sorted(rigs))
h, h2, manny = rigs.get("Hunter_Rig"), rigs.get("Hunter_Rig1"), rigs.get("Manny_Rig")
gate(3, ar.rotation_mode(h) and ar.rotation_mode(h2) and not ar.rotation_mode(manny),
     "rotation-only mark: Hunter %s, Hunter1 %s, Manny %s" % (ar.rotation_mode(h), ar.rotation_mode(h2), ar.rotation_mode(manny)))
gate(4, h.skeleton_root == "|Hunter_Rig:root" and len(cmds.listRelatives(h.skeleton_root, ad=True, type="joint")) == 90 and cmds.objExists("Hunter_Rig:weapon_r") and cmds.objExists("Hunter_Rig:weapon_l"),
     "the Hunter's skeleton at world level: %s, %d joints below it" % (h.skeleton_root, len(cmds.listRelatives(h.skeleton_root, ad=True, type="joint") or [])))
scripts = [s for s in cmds.ls(type="script") if s.startswith(("Hunter_Rig", "Manny_Rig"))]
gate(5, not [s for s in scripts if s.startswith("Hunter_Rig")], "script nodes the Hunter asset brought: %s" % [s for s in scripts if s.startswith("Hunter_Rig")])
worst, skins = 0.0, []
for sc in cmds.ls(type="skinCluster"):
    if not sc.startswith("Hunter_Rig:"):
        continue
    skins.append(sc)
    for idx in cmds.getAttr(sc + ".matrix", multiIndices=True) or []:
        src = cmds.listConnections("%s.matrix[%d]" % (sc, idx), s=True, d=False)
        if src:
            p = om.MMatrix(cmds.getAttr("%s.bindPreMatrix[%d]" % (sc, idx))) * wm(src[0])
            worst = max(worst, max(abs(p.getElement(r, c) - (r == c)) for r in range(4) for c in range(4)))
off = ar.posed_controls(rig=h)
gate(6, len(skins) == 5 and worst < 1e-4 and not off, "%d Hunter skins at their bind (|BPM*WM - I| %.2e), controls at default %s" % (len(skins), worst, off[:4]))
geo = cmds.listRelatives("|Hunter_Rig:Group|Hunter_Rig:Geometry", children=True) or []
painted = [m for m in cmds.ls("Hunter_Rig:Hunter_*", type="mesh") if not cmds.getAttr(m + ".intermediateObject")]
colours = set()
for m in painted:
    for sg in cmds.listConnections(m, type="shadingEngine") or []:
        colours.update(x for x in cmds.ls(cmds.listConnections(sg + ".surfaceShader", s=True, d=False) or [], materials=True)
                       if cmds.attributeQuery("skeldarColour", node=x, exists=True))
gate(7, {"Hunter_Rig:Hunter_Body", "Hunter_Rig:Hunter_Face"} <= set(geo) and "Hunter_Rig:Hunter_Props" not in geo and len(painted) == 5 and colours,
     "Geometry %s; %d meshes painted with %s" % ([g.split(":")[-1] for g in geo], len(painted), sorted(colours)))

# the retarget, onto the FIRST Hunter
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

# the Hunter's sword from the catalog, as on any rig: Add at zero grip, before the take
from maya_scenesetup import attach, bonedrive, weaponspace
sword_entry = catalog.by_key("Hunter_Sword")
cmds.currentTime(first)
weapon, wnote = attach.attach(sword_entry, H["hand_r"], H["weapon_r"], (0, 0, 0), (0, 0, 0))
weapon = cmds.ls(weapon, long=True)[0]
off = max(abs(a - b) for a, b in zip(list(wm(weapon)), list(wm(H["weapon_r"]))))
#  since 2026-09-24 a weapon lives in its hand's SPACE, outside the skeleton (weaponspace)
gate(11, weaponspace.holding_hand(weapon) == H["hand_r"] and not weapon.startswith(H["root"] + "|")
     and bonedrive.driving_weapon(H["weapon_r"]) and off < 1e-4,
     "Add 'Hunter Sword': %s in hand_r's space (%s) drives weapon_r, sitting on the bone to %.2e at zero grip %s"
     % (weapon.split("|")[-1], weapon.rsplit("|", 2)[-2], off, wnote))

cmds.select(cmds.ls("Hunter_Rig:Main")[0], src)
ok, text = rr.run_retarget()
print(text.splitlines()[0][:220])
gate(8, ok and "ROTATIONS ONLY" in text and not cmds.objExists(ar.holder_of(h)), "the button, with a Hunter control and the clip selected: ok=%s" % ok)
worst_rot, worst_len, moved = 0.0, 0.0, 0.0
for t in range(int(first), int(last) + 1, max(1, int((last - first) / 10))):
    cmds.currentTime(t)
    for b in ("pelvis", "spine_03", "neck_01", "head", "clavicle_l", "hand_l", "hand_r", "foot_l", "ball_r", "middle_02_r"):
        worst_rot = max(worst_rot, ang(rot(wm(S[b])), rot(wm(H[b]))))
    for n, p in H.items():
        if n not in ("root", "pelvis", "weapon_r", "weapon_l") and not n.startswith("ik_"):   # the weapon bones carry the clip's weapon motion in the hand
            worst_len = max(worst_len, (om.MVector(cmds.getAttr(p + ".translate")[0]) - om.MVector(rest_t[n])).length())
    moved = max(moved, max(max(abs(a - c) for a, c in zip(list(m), list(wm(p)))) for p, m in still.items()))
gate(9, worst_rot < 0.05 and worst_len < 1e-3, "the Hunter on the clip's orientations to %.5f deg, its bone lengths kept to %.6f cm" % (worst_rot, worst_len))
gate(10, moved < 1e-6, "the second Hunter and the Manny did not move: %.9f" % moved)

# weapon_r took the clip's grip RELATIVE TO THE HAND (a world copy would float off the Hunter's
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
    worst_grip = max(worst_grip, mdiff(wm(weapon), wm(H["weapon_r"])))
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
print("RESULT: %d of 13 gates failed %s" % (len(FAILS), FAILS))
