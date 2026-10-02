"""verify_clip_labels.py - the animation's name under each character (2026-10-02), in mayapy
STANDALONE. It adds rigs and skeletons and deletes them, so never in the animator's scene:

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/verify_clip_labels.py

No Unreal editor: the editor's export is replaced by UE clips on disk, as verify_uebridge_many.py
does. REPO may be set in the environment (SKELDAR_REPO) to prove a worktree's plugin.

Gates:
 1  a batch onto New rig (`lineimport.run`, three clips): one label per rig, reading its clip,
    linked to its game skeleton's root, under the rig's group, in its namespace, dressed
    (transform reference, shape normal + our colour), never under the skeleton
 2  the labels follow their rigs over the take: at the first, middle and last frame (a real time
    change) each stands on the floor (y 0) at its root's x/z + FRONT, while the thrust's root
    travels ~2.5 m (the positive control: a label that did not follow would read that far off)
 3  a single import onto rig 1 (Import Animation, Rig mode): its label's text replaced, the same
    node, still one; the same clip again keeps it
 4  a batch in the Skeleton mode (Characters on Manny UE5 [skeleton]): one label per skeleton at
    world level, linked by message, following its root
 5  Skeleton x Onto selected onto skeleton 1: its label's text replaced, one label
 6  the export: a rig's and a skeleton's FBX read back hold no label (the positive control: the
    label exported on purpose reads back by name)
 7  Delete: a rig and a skeleton deleted through a control / a mesh take their labels; Ctrl+Z
    brings them back linked; the other characters keep theirs
 8  nothing stray: every label in the scene belongs to a character standing
 9  a Creep rig, its root under its Armature Null: labelled, following its root
"""

import math
import os
import sys
import tempfile
import time
import traceback
import types

SCRATCH = tempfile.mkdtemp(prefix="cliplabels_")
os.environ.setdefault("MAYA_APP_DIR", os.path.join(SCRATCH, "prefs"))

import maya.standalone  # noqa: E402

maya.standalone.initialize(name="python")
import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402

for _plugin in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(_plugin, quiet=True)
    except RuntimeError:
        pass

REPO = os.environ.get("SKELDAR_REPO", "C:/!!!Work/MayaScripts/SkeldarAnim").replace("\\", "/")
sys.path.insert(0, REPO)
cmds.undoInfo(state=True, infinity=True)

import maya_rigs  # noqa: E402
from maya_scenesetup import cliplabel  # noqa: E402
from maya_scenesetup import deletion  # noqa: E402
from maya_uebridge import animexport  # noqa: E402
from maya_uebridge import lineimport  # noqa: E402
from maya_uebridge import rigimport  # noqa: E402
from maya_uebridge import skeletonimport  # noqa: E402

print("plugin from", os.path.dirname(cliplabel.__file__))
EXPORT = "C:/!!!Work/Animations/Export/"
CLIPS = {"LongSword_Attack_Right_Heavy_1P": EXPORT + "LongSword_Attack_Right_Heavy_1P.FBX",
         "ShortSword_Attack_Thrust_3P": EXPORT + "ShortSword_Attack_Thrust_3P.FBX",
         "ShortSword_Walk_1P": EXPORT + "ShortSword_Walk_1P.fbx",
         "Sword_Idle": EXPORT + "Sword_Idle.fbx"}
ORDER = ["LongSword_Attack_Right_Heavy_1P", "ShortSword_Attack_Thrust_3P", "ShortSword_Walk_1P"]
FAILED, PASSED = [], []


def gate(name, ok, detail=""):
    (PASSED if ok else FAILED).append(name)
    print("%s  %s%s" % ("PASS" if ok else "FAIL", name, ("  | " + str(detail)) if detail else ""))


def record(name):
    return types.SimpleNamespace(name=name)


def export(rec):
    return CLIPS[rec.name], 30


def choose(model, kind):
    cmds.optionVar(stringValue=("mayaSceneSetup_characterModel", model))
    cmds.optionVar(stringValue=("mayaSceneSetup_characterKind", kind))


def wt(node):
    return cmds.xform(node, query=True, worldSpace=True, translation=True)


def labels_by_root():
    out = {}
    for label in cliplabel.all_labels():
        roots = cmds.listConnections(label + "." + cliplabel.ROOT_LINK, source=True,
                                     destination=False) or []
        root = (cmds.ls(roots[0], long=True) or [None])[0] if roots else None
        out.setdefault(root, []).append(label)
    return out


def under(path, top):
    return path == top or path.startswith(top + "|")


def dressed(label):
    shape = cliplabel.shape_of(label)
    want = cliplabel.colour_of(cliplabel.COLOUR)
    rgb = cmds.getAttr(shape + ".overrideColorRGB")[0]
    return (cmds.getAttr(label + ".overrideDisplayType") == 2
            and cmds.getAttr(shape + ".overrideEnabled")
            and cmds.getAttr(shape + ".overrideDisplayType") == 0
            and cmds.getAttr(shape + ".overrideRGBColors")
            and not cmds.getAttr(shape + ".displayArrow")
            and max(abs(a - b) for a, b in zip(rgb, want)) < 1e-6)


def follow_error(label, root, frames):
    """Worst distance over `frames` between the label and the root's floor point + FRONT, and
    how far the root travelled on the floor (a real time change for each)."""
    worst, start = 0.0, None
    travel = 0.0
    for frame in frames:
        cmds.currentTime(frame - 1)
        cmds.currentTime(frame)
        r = wt(root)
        p = wt(label)
        want = (r[0], cliplabel.FLOOR, r[2] + cliplabel.FRONT)
        worst = max(worst, max(abs(p[i] - want[i]) for i in range(3)))
        if start is None:
            start = r
        travel = max(travel, math.hypot(r[0] - start[0], r[2] - start[2]))
    return worst, travel


def frames_of(root):
    curves = cmds.listConnections(root, type="animCurve", source=True, destination=False) or []
    rigs = [r for r in maya_rigs.rigs() if r.skeleton_root == root]
    if rigs:
        curves = cmds.listConnections(rigs[0].main, type="animCurve", source=True,
                                      destination=False) or []
    times = cmds.keyframe(curves, query=True, timeChange=True) if curves else []
    if not times:
        a = cmds.playbackOptions(query=True, minTime=True)
        b = cmds.playbackOptions(query=True, maxTime=True)
        return [a, (a + b) / 2.0, b]
    a, b = min(times), max(times)
    return [a, round((a + b) / 2.0), b]


def read_back(fbx):
    """(joints, nodes) an FBX holds, imported into a namespace of its own and deleted."""
    ns = "chk%d" % int(time.time() * 1000 % 100000)
    cmds.namespace(add=ns)
    cmds.namespace(set=ns)
    try:
        mel.eval("FBXResetImport")
        mel.eval("FBXImportMode -v add")
        mel.eval('FBXImport -f "%s"' % fbx.replace("\\", "/"))
    finally:
        cmds.namespace(set=":")
    nodes = cmds.namespaceInfo(":" + ns, listOnlyDependencyNodes=True, recurse=True,
                               dagPath=True) or []
    joints = [n for n in nodes if cmds.objectType(n) == "joint"]
    names = [n.split("|")[-1].split(":")[-1] for n in nodes]
    marked = [n for n in nodes if cmds.attributeQuery(cliplabel.MARKER, node=n, exists=True)]
    annotations = [n for n in nodes if cmds.objectType(n) == "annotationShape"]
    cmds.namespace(removeNamespace=ns, deleteNamespaceContent=True)
    return joints, names, marked, annotations


def main():
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    choose("Manny", "rig")

    # ------------------------------------------------------------- 1, 2: a batch onto new rigs
    t = time.time()
    line = lineimport.run([record(n) for n in ORDER], export, "new_rig")
    print("batch new_rig (%.1f s): %s" % (time.time() - t, line))
    rigs = sorted(maya_rigs.rigs(), key=lambda r: r.namespace)
    by_root = labels_by_root()
    ok, notes = len(rigs) == 3, []
    clip_of_rig = {}
    for rig in rigs:
        found = by_root.get(rig.skeleton_root, [])
        if len(found) != 1:
            ok = False
            notes.append("%s: %d labels" % (rig.namespace, len(found)))
            continue
        label = found[0]
        clip_of_rig[rig.namespace] = cliplabel.clip_of(label)
        checks = dict(
            text=cliplabel.text_of(label) in ORDER,
            group=under(label, rig.group),
            namespace=label.split("|")[-1].startswith(rig.namespace + ":"),
            dressed=dressed(label),
            not_in_skeleton=not under(label, rig.skeleton_root))
        if not all(checks.values()):
            ok = False
            notes.append("%s %s" % (rig.namespace, checks))
    ok = ok and sorted(clip_of_rig.values()) == sorted(ORDER)
    gate("1 batch New rig: one dressed label per rig, its clip, under its group, in its "
         "namespace, outside the skeleton", ok, notes or clip_of_rig)

    worst, travels = 0.0, {}
    for rig in rigs:
        label = by_root[rig.skeleton_root][0]
        error, travel = follow_error(label, rig.skeleton_root, frames_of(rig.skeleton_root))
        worst = max(worst, error)
        travels[cliplabel.clip_of(label)] = round(travel, 3)
    thrust = travels.get("ShortSword_Attack_Thrust_3P", 0.0)
    gate("2 the labels follow their rigs on the floor (first / middle / last frame)",
         worst < 0.01 and thrust > 100.0, "worst %.6f cm; root travel %s" % (worst, travels))

    # ------------------------------------------------------------- 3: a re-import onto rig 1
    rig1 = rigs[0]
    before = by_root[rig1.skeleton_root][0]
    before_uuid = cmds.ls(before, uuid=True)[0]
    old_clip = cliplabel.clip_of(before)
    new_clip = "Sword_Idle"
    line = rigimport.import_and_retarget(CLIPS[new_clip], new_clip, clip_fps=30,
                                         target="rig", rig=rig1)
    print("re-import:", line)
    after = labels_by_root().get(rig1.skeleton_root, [])
    same = len(after) == 1 and cmds.ls(after[0], uuid=True)[0] == before_uuid
    gate("3 a single import onto rig 1 replaces its label's text on the same node",
         same and cliplabel.text_of(after[0]) == new_clip,
         "%s -> %s, %d label(s)" % (old_clip, cliplabel.text_of(after[0]) if after else None,
                                    len(after)))
    keep = cliplabel.label_rig(rig1, new_clip)
    gate("3b the same clip again keeps it", keep == after[0]
         and len(labels_by_root().get(rig1.skeleton_root, [])) == 1)
    error, _travel = follow_error(after[0], rig1.skeleton_root, frames_of(rig1.skeleton_root))
    gate("3c the replaced label still follows", error < 0.01, "%.6f" % error)

    # ------------------------------------------------------------- 4: a batch of skeletons
    choose("Manny", "skeleton")
    rig_roots = set(r.skeleton_root for r in maya_rigs.rigs())
    t = time.time()
    line = lineimport.run([record(n) for n in ORDER], export, "skeleton",
                          centre=(0.0, 0.0, 800.0))
    print("batch skeleton (%.1f s): %s" % (time.time() - t, line))
    bare = [r for r in skeletonimport.bare_roots() if r not in rig_roots]
    by_root = labels_by_root()
    ok, notes, worst = len(bare) == 3, [], 0.0
    for root in bare:
        found = by_root.get(root, [])
        if len(found) != 1:
            ok = False
            notes.append("%s: %d labels" % (root, len(found)))
            continue
        label = found[0]
        if label.count("|") != 1 or not dressed(label) or cliplabel.text_of(label) not in ORDER:
            ok = False
            notes.append("%s: %s" % (root, label))
        error, _travel = follow_error(label, root, frames_of(root))
        worst = max(worst, error)
    gate("4 batch Skeleton: one dressed label per skeleton at world level, following its root",
         ok and worst < 0.01, notes or "worst %.6f cm" % worst)

    # ------------------------------------------------------------- 5: onto a skeleton standing
    skel1 = sorted(bare)[0]
    before = by_root[skel1][0]
    line = skeletonimport.import_onto_existing(CLIPS["Sword_Idle"], "Sword_Idle", skel1,
                                               clip_fps=30)
    print("onto existing:", line)
    after = labels_by_root().get(skel1, [])
    gate("5 Skeleton x Onto selected replaces the skeleton's label's text",
         len(after) == 1 and after[0] == before and cliplabel.text_of(after[0]) == "Sword_Idle",
         [cliplabel.text_of(a) for a in after])

    # ------------------------------------------------------------- 6: never in an export
    out = os.path.join(SCRATCH, "rig_export.fbx")
    report = animexport.export_hierarchy(out, root=rigs[1].skeleton_root)
    joints, names, marked, annotations = read_back(out)
    rig_clean = joints and not marked and not annotations and not any(
        cliplabel.LEAF in n for n in names)
    out2 = os.path.join(SCRATCH, "skeleton_export.fbx")
    animexport.export_hierarchy(out2, root=sorted(bare)[1])
    joints2, names2, marked2, ann2 = read_back(out2)
    skel_clean = joints2 and not marked2 and not ann2 and not any(
        cliplabel.LEAF in n for n in names2)
    # The positive control: the label itself exported reads back by its name.
    control = os.path.join(SCRATCH, "label_control.fbx")
    label = labels_by_root()[rigs[1].skeleton_root][0]
    cmds.select(label, replace=True)
    mel.eval("FBXResetExport")
    mel.eval('FBXExport -f "%s" -s' % control.replace("\\", "/"))
    _j, cnames, _m, _a = read_back(control)
    seen = any(cliplabel.LEAF in n for n in cnames)
    gate("6 a rig's and a skeleton's export hold no label; the label exported on purpose does",
         bool(rig_clean and skel_clean and seen),
         "rig %d joints, skeleton %d joints, control names %s" % (
             len(joints), len(joints2), [n for n in cnames if cliplabel.LEAF in n]))

    # ------------------------------------------------------------- 7: Delete takes them
    rig2 = rigs[2]
    rig2_label = labels_by_root()[rig2.skeleton_root][0]
    rig2_label_uuid = cmds.ls(rig2_label, uuid=True)[0]
    skel2 = sorted(bare)[2]
    skel2_label = labels_by_root()[skel2][0]
    skel2_label_uuid = cmds.ls(skel2_label, uuid=True)[0]
    mesh = None
    for skin in cmds.ls(type="skinCluster") or []:
        infl = cmds.skinCluster(skin, query=True, influence=True) or []
        if infl and any(under((cmds.ls(j, long=True) or [""])[0], skel2) for j in infl[:3]):
            geo = cmds.skinCluster(skin, query=True, geometry=True) or []
            if geo:
                mesh = (cmds.ls(geo[0], long=True) or [None])[0]
                break
    control_node = (cmds.ls(rig2.main, long=True) or [rig2.main])[0]
    kept = [l for l in cliplabel.all_labels() if l not in (rig2_label, skel2_label)]
    asked = []
    line = deletion.delete_selected(selection=[control_node, mesh],
                                    confirm=lambda text: asked.append(text) or True)
    print("delete:", line)
    gone = not cmds.ls(rig2_label_uuid) and not cmds.ls(skel2_label_uuid)
    others = all(cmds.objExists(l) for l in kept)
    gate("7 Delete through a control and a mesh takes the two characters' labels, the others "
         "keep theirs", gone and others and mesh is not None, line)
    cmds.undo()
    back = cmds.ls(rig2_label_uuid, long=True) and cmds.ls(skel2_label_uuid, long=True)
    relinked = back and labels_by_root().get(skel2) == cmds.ls(skel2_label_uuid, long=True)
    gate("7b Ctrl+Z brings them back, linked to their roots", bool(relinked),
         cmds.ls(skel2_label_uuid, long=True))
    cmds.redo()

    # ------------------------------------------------------------- 8: nothing stray
    roots = set(r.skeleton_root for r in maya_rigs.rigs()) | set(skeletonimport.bare_roots())
    stray = [l for root, ls in labels_by_root().items() for l in ls if root not in roots]
    counts = dict((root.split("|")[-1], len(ls)) for root, ls in labels_by_root().items())
    gate("8 every label belongs to a character standing, one each", not stray
         and all(n == 1 for n in counts.values()), counts)

    # ------------------------------------------------------------- 9: a Creep rig
    choose("Creep", "rig")
    before = set(r.namespace for r in maya_rigs.rigs())
    line = rigimport.import_and_retarget(CLIPS["ShortSword_Attack_Thrust_3P"],
                                         "ShortSword_Attack_Thrust_3P", clip_fps=30,
                                         target="new_rig", at=(-400.0, 0.0, 0.0))
    print("creep:", line)
    creep = [r for r in maya_rigs.rigs() if r.namespace not in before]
    found = labels_by_root().get(creep[0].skeleton_root, []) if creep else []
    error, travel = (follow_error(found[0], creep[0].skeleton_root,
                                  frames_of(creep[0].skeleton_root)) if found else (1e9, 0.0))
    gate("9 a Creep rig (its root under its Armature): labelled, following the root",
         len(found) == 1 and travel > 100.0 and error < 0.01 and under(found[0], creep[0].group),
         "%s %s, worst %.6f cm over %.1f cm" % (creep[0].namespace if creep else None,
                                                [cliplabel.text_of(f) for f in found],
                                                error, travel))


try:
    main()
except Exception:
    traceback.print_exc()
    FAILED.append("crashed")
print("%d passed, %d failed: %s" % (len(PASSED), len(FAILED), FAILED))
print("VERIFY DONE")
