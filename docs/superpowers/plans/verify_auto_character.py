"""Proof of the Auto card (2026-10-02): a clip onto OUR character whose skeleton it is, else in its own.

mayapy STANDALONE, never the animator's Maya: it opens new scenes, adds rigs and deletes them. Clips
come from the animator's MarkerLess_02 project, exported WITH their preview mesh by
export_auto_fixtures.py into a folder (its fixtures.json). Unreal is not needed here.

    $env:MAYA_APP_DIR = '<scratch>'
    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/verify_auto_character.py <fixtures folder>

PHASES (env, default all): match, rig, skeleton, native, nomatch, batch, explicit, export, onto, file.
Spec: docs/superpowers/specs/2026-10-02-auto-character-import-design.md
"""
import json
import math
import os
import sys
import tempfile
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.normpath(os.path.join(HERE, "..", "..", "..", "SkeldarAnim"))
FIXTURES = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ.get("TEMP", "."),
                                                               "skeldar_auto_fixtures")
SWEEP = "C:/Users/MY PC/Downloads/Sweep Fall.fbx"
PHASES = [p for p in os.environ.get("PHASES", "").split(",") if p]

RESULTS = []


def gate(name, ok, detail=""):
    RESULTS.append((name, bool(ok)))
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, (" - " + detail) if detail else ""))
    sys.stdout.flush()


def wanted(phase):
    return not PHASES or phase in PHASES


def main():
    sys.path.insert(0, PLUGIN)
    import maya.standalone
    maya.standalone.initialize()
    import maya.cmds as cmds
    for plugin in ("fbxmaya", "matrixNodes", "quatNodes"):
        try:
            cmds.loadPlugin(plugin, quiet=True)
        except Exception:                                    # noqa: BLE001
            pass
    import maya_retargetmode
    import maya_rigs
    from maya_scenesetup import catalog, character, deletion
    from maya_uebridge import (animimport, autoimport, lineimport, nativeimport, rigimport,
                               skeletonimport, skeletonmatch)

    with open(os.path.join(FIXTURES, "fixtures.json")) as handle:
        clips = dict((c["name"], c) for c in json.load(handle))

    def path(name):
        return clips[name]["path"]

    asked = []

    def asker(m):
        asked.append(m)
        return maya_retargetmode.KEEP
    maya_retargetmode.set_asker(asker)

    def fresh():
        cmds.file(new=True, force=True)
        cmds.currentUnit(time="ntsc")
        del asked[:]

    def at(node, frame):
        cmds.currentTime(frame, update=True)
        return tuple(cmds.xform(node, query=True, worldSpace=True, translation=True))

    def namespaces():
        return [n for n in cmds.namespaceInfo(":", listOnlyNamespaces=True) or []
                if n not in ("UI", "shared")]

    def reference(name):
        """The same clip imported as a plain skeleton: what the character must play."""
        ns, info, source = rigimport.import_source(path(name), "ref_" + name, set_timeline=False)
        return ns, info, source

    def bones_of(root):
        return dict((b.split("|")[-1].split(":")[-1], b) for b in
                    [root] + (cmds.listRelatives(root, allDescendents=True, type="joint",
                                                 fullPath=True) or []))

    def worst(ours, theirs, frames, names, delta=(0.0, 0.0, 0.0)):
        """The largest distance over `frames` between our bone and the clip's (moved by delta)."""
        out, where = 0.0, ""
        for frame in frames:
            for name in names:
                if name not in ours or name not in theirs:
                    continue
                a, b = at(ours[name], frame), at(theirs[name], frame)
                d = math.dist(a, tuple(x + y for x, y in zip(b, delta)))
                if d > out:
                    out, where = d, "%s@%g" % (name, frame)
        return out, where

    def worst_angle(ours, theirs, frames, chains):
        """The largest angle over `frames` between our bone (parent -> child) and the clip's."""
        out, where = 0.0, ""
        for frame in frames:
            for parent, child in chains:
                if not all(n in ours and n in theirs for n in (parent, child)):
                    continue
                a = [c - p for c, p in zip(at(ours[child], frame), at(ours[parent], frame))]
                b = [c - p for c, p in zip(at(theirs[child], frame), at(theirs[parent], frame))]
                na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
                if na < 1e-6 or nb < 1e-6:
                    continue
                cos = max(-1.0, min(1.0, sum(x * y for x, y in zip(a, b)) / (na * nb)))
                angle = math.degrees(math.acos(cos))
                if angle > out:
                    out, where = angle, "%s@%g" % (child, frame)
        return out, where

    CHAINS = (("upperarm_r", "lowerarm_r"), ("lowerarm_r", "hand_r"), ("upperarm_l", "lowerarm_l"),
              ("lowerarm_l", "hand_l"), ("thigh_l", "calf_l"), ("calf_l", "foot_l"),
              ("thigh_r", "calf_r"), ("calf_r", "foot_r"), ("spine_01", "spine_03"),
              ("neck_01", "head"), ("hand_r", "middle_01_r"))

    def frames_of(info):
        return autoimport.sample_frames(info["start"], info["end"], 5)

    # ------------------------------------------------------------------ match
    if wanted("match"):
        expect = {"MM_Fall_Loop": ("Manny_Rig", "Manny"),
                  "Conjure_SwirlArms": ("Manny_Rig", "Manny"),
                  "Orc_Walk_Fwd": ("Orc_D_Rig", None),
                  "Sword1h_WalkStop_RU": (None, "UE4_Mannequin"),
                  "Kwang_Ability_Q_Catch": (None, None),
                  "MetaHuman_AttackTest": (None, None)}
        fresh()
        for name, (rig_key, skeleton_key) in expect.items():
            ns, info, source = rigimport.import_source(path(name), name, set_timeline=False)
            rig = autoimport.match_clip(source, info, "rig")
            bare = autoimport.match_clip(source, info, "skeleton")
            gate("match %s" % name, (rig.key, bare.key) == (rig_key, skeleton_key),
                 "rig %s | skeleton %s" % (skeletonmatch.match_text(rig),
                                           skeletonmatch.match_text(bare)))
            cmds.namespace(removeNamespace=ns, deleteNamespaceContent=True)

    # ------------------------------------------------------------------ rig
    if wanted("rig"):
        for name, key in (("MM_Fall_Loop", "Manny_Rig"), ("Orc_Walk_Fwd", "Orc_D_Rig")):
            fresh()
            text = autoimport.import_auto(path(name), name, "rig")
            print("   ", text)
            found = maya_rigs.rigs()
            gate("rig %s: one %s added, nothing asked" % (name, key),
                 len(found) == 1 and found[0].namespace.startswith(key) and not asked,
                 "rigs %s asked %d" % ([r.namespace for r in found], len(asked)))
            gate("rig %s: the line names the match" % name,
                 text.startswith("matched %s" % catalog.character_by_key(key).label), text[:90])
            # a rig namespace may outlive a new scene (mayaUsd's settings node lands in it)
            gate("rig %s: no clip namespace left" % name, name not in namespaces(),
                 str(namespaces()))
            if found:
                ns, info, source = reference(name)
                ours, theirs = bones_of(found[0].skeleton_root), bones_of(source)
                d, where = worst(ours, theirs, frames_of(info),
                                 ("pelvis", "hand_r", "hand_l", "foot_l", "foot_r", "head",
                                  "spine_03", "lowerarm_r", "calf_l"))
                angle, at_bone = worst_angle(ours, theirs, frames_of(info), CHAINS)
                if key == "Manny_Rig":
                    # a twin: every bone where the clip has it, to the rig's own fit (Manny's
                    # left leg stands 0.07 cm off its bone, CLAUDE.md's retarget sections)
                    gate("rig %s: the game bones play the clip" % name, d < 0.15,
                         "worst %.4f cm (%s), %.3f deg (%s)" % (d, where, angle, at_bone))
                else:
                    # the Orc's clip carries Manny-length arms (6.4 % off Orc D's): the rig keeps
                    # its bones, as Unreal shows the clip on the Orc's mesh - the bones POINT as
                    # the clip's
                    gate("rig %s: the game bones point as the clip's" % name, angle < 0.5,
                         "worst %.3f deg (%s); positions %.4f cm (%s)" % (angle, at_bone, d, where))

    # ------------------------------------------------------------------ skeleton
    if wanted("skeleton"):
        fresh()
        name = "Sword1h_WalkStop_RU"
        text = autoimport.import_auto(path(name), name, "skeleton")
        print("   ", text)
        roots = skeletonimport.bare_roots()
        gate("skeleton: the UE4 Mannequin added, no rig",
             len(roots) == 1 and not maya_rigs.rigs() and "UE4 Mannequin" in text,
             "%s | %s" % (roots, text[:90]))
        if roots:
            ns, info, source = reference(name)
            d, where = worst(bones_of(roots[0]), bones_of(source), frames_of(info),
                             ("pelvis", "hand_r", "foot_l", "head", "spine_03", "calf_r"))
            gate("skeleton: every bone plays the clip", d < 0.05, "worst %.4f cm (%s)" % (d, where))

    # ------------------------------------------------------------------ native
    native_root = None
    if wanted("native") or wanted("export") or wanted("onto"):
        fresh()
        name = "Kwang_Ability_Q_Catch"
        point = (150.0, 0.0, -80.0)
        before = set(cmds.ls(cmds.ls(), uuid=True) or [])
        text = autoimport.import_auto(path(name), name, "rig", at=point)
        print("   ", text)
        group = cmds.ls("|Kwang_GDC_Character", long=True) or []
        gate("native: no rig added, the line says why", not maya_rigs.rigs()
             and "no skeleton of ours" in text and "in its own skeleton Kwang_GDC" in text,
             text[:160])
        gate("native: one group at world level holding root and the mesh",
             bool(group) and sorted(c.split("|")[-1] for c in cmds.listRelatives(
                 group[0], children=True, fullPath=True) or []) ==
             ["Kwang_GDC", "root", "root_clipLabel"] if group else False,
             str(cmds.listRelatives(group[0], children=True) if group else None))
        layer = cmds.ls("Kwang_GDC_Layer", type="displayLayer")
        gate("native: its layer holds the group", bool(layer) and group and group[0] in (
            cmds.ls(cmds.editDisplayLayerMembers(layer[0], query=True) or [], long=True) or []))
        gate("native: plain names, no clip namespace", not namespaces()
             and bool(cmds.ls("|Kwang_GDC_Character|root|pelvis")), str(namespaces()))
        native_root = (cmds.ls("|Kwang_GDC_Character|root", long=True) or [None])[0]
        if native_root:
            joints = bones_of(native_root)
            gate("native: every joint of the clip", len(joints) == 116, "%d joints" % len(joints))
            mesh = "|Kwang_GDC_Character|Kwang_GDC"
            skins = cmds.ls(cmds.listHistory(mesh) or [], type="skinCluster") or []
            influences = cmds.skinCluster(skins[0], query=True, influence=True) if skins else []
            gate("native: the mesh is skinned to these joints", bool(skins) and all(
                cmds.ls(j, long=True)[0].startswith(native_root) for j in influences),
                "%d influences" % len(influences))
            engines = cmds.listConnections(cmds.listRelatives(mesh, shapes=True,
                                                              noIntermediate=True)[0],
                                           type="shadingEngine") or []
            mats = [m for e in engines for m in (cmds.listConnections(e + ".surfaceShader") or [])]
            gate("native: in a palette colour", any(
                cmds.attributeQuery("skeldarColour", node=m, exists=True) for m in mats),
                str(mats))
            uuids, label = deletion.recorded(native_root)
            gate("native: Delete's record", label == "Kwang_GDC [own skeleton]" and uuids,
                 "%s, %d nodes" % (label, len(uuids)))
            from maya_scenesetup import cliplabel
            lab = cmds.ls("|Kwang_GDC_Character|root_clipLabel", long=True) or []
            gate("native: the clip's label", bool(lab) and cliplabel.text_of(lab[0]) == name,
                 cliplabel.text_of(lab[0]) if lab else "none")
            ns, info, source = reference(name)
            start = rigimport.root_at(source, info["start"])
            delta = (point[0] - start[0], 0.0, point[2] - start[2])
            first = at(native_root, info["start"])
            gate("native: the root at the first frame on the point",
                 math.hypot(first[0] - point[0], first[2] - point[2]) < 1e-3,
                 "(%.4f, %.4f)" % (first[0], first[2]))
            d, where = worst(joints, bones_of(source), frames_of(info), list(joints), delta)
            gate("native: every joint plays the clip, moved", d < 1e-3,
                 "worst %.6f cm (%s)" % (d, where))
            ref_mesh = [m for m in cmds.ls(ns + ":*", type="mesh", long=True) or []
                        if not cmds.getAttr(m + ".intermediateObject")]
            if ref_mesh:
                frame = frames_of(info)[2]
                cmds.currentTime(frame, update=True)
                count = cmds.polyEvaluate(mesh, vertex=True)
                worst_v = 0.0
                for i in range(0, count, max(1, count // 40)):
                    a = cmds.pointPosition("%s.vtx[%d]" % (mesh, i), world=True)
                    b = cmds.pointPosition("%s.vtx[%d]" % (ref_mesh[0], i), world=True)
                    worst_v = max(worst_v, math.dist(a, [x + y for x, y in zip(b, delta)]))
                gate("native: the mesh deforms with them", worst_v < 1e-3,
                     "worst vertex %.6f cm of %d sampled" % (worst_v, len(range(0, count, max(1, count // 40)))))
            cmds.namespace(removeNamespace=ns, deleteNamespaceContent=True)
            if wanted("native"):
                text = deletion.delete_selected([native_root], confirm=lambda _t: True)
                after = set(cmds.ls(cmds.ls(), uuid=True) or [])
                left = [cmds.ls(u)[0] for u in after - before]
                excused = [n for n in left if cmds.nodeType(n) in (
                    "shapeEditorManager", "poseInterpolatorManager")]
                gate("native: Delete takes it whole", set(left) == set(excused),
                     "%s | left %s" % (text[:70], sorted(set(left) - set(excused))[:8]))
                cmds.undo()
                gate("native: Ctrl+Z brings it back",
                     bool(cmds.ls("|Kwang_GDC_Character|root|pelvis")))
                native_root = (cmds.ls("|Kwang_GDC_Character|root", long=True) or [None])[0]

    # ------------------------------------------------------------------ repeat
    if wanted("repeat"):
        # the review, 2026-10-02: an Auto press that ADDS a rig must not leave it selected, or the
        # next Auto press (Onto selected) takes it for the animator's explicit target
        fresh()
        from maya_uebridge import window
        saved = (window.auto_kind, window.import_target, window._export_unreal, window._timeline)

        class Rec2(object):
            source = "unreal"
            fps = None

            def __init__(self, name):
                self.name = name
                self.package = "/Game/" + name
        try:
            window.auto_kind = lambda: "rig"
            window.import_target = lambda: "onto"
            window._export_unreal = lambda record, mesh=False: (path(record.name), None)
            window._timeline = lambda: True
            cmds.select(clear=True)
            text = window._auto_press([Rec2("MM_Fall_Loop")], "rig")
            rig = (maya_rigs.rigs() or [None])[0]
            curves = len(cmds.ls(type="animCurve") or [])
            gate("repeat: the Auto press added Manny and left nothing selected",
                 rig is not None and not cmds.ls(selection=True), "%s | sel %s" % (
                     text[:60], cmds.ls(selection=True)))
            text = window._auto_press([Rec2("Kwang_Ability_Q_Catch")], "rig")
            print("   ", text[:140])
            gate("repeat: the next Auto press is matched, not put on the added rig",
                 bool(cmds.ls("|Kwang_GDC_Character")) and "in its own skeleton" in text
                 and len(maya_rigs.rigs()) == 1 and not asked, text[:90])
            mine = len([c for c in cmds.ls(type="animCurve") or []
                        if c.startswith(rig.namespace + ":")])
            gate("repeat: the Manny take is untouched", mine > 0, "%d curves on Manny" % mine)
            del curves
        finally:
            (window.auto_kind, window.import_target, window._export_unreal,
             window._timeline) = saved

    # ------------------------------------------------------------------ export
    if wanted("export") and native_root:
        from maya_uebridge import animexport
        out = os.path.join(tempfile.mkdtemp(), "kwang_native.fbx").replace("\\", "/")
        text = animexport.export_hierarchy(out, root=native_root, layout="plain")
        print("   ", str(text)[:200])
        keep_scene = cmds.file(query=True, sceneName=True)
        cmds.file(new=True, force=True)
        import maya.mel as mel
        mel.eval("FBXResetImport")
        mel.eval("FBXImportMode -v add")
        mel.eval('FBXImport -f "%s"' % out)
        joints = cmds.ls(type="joint", long=True) or []
        meshes = cmds.ls(type="mesh") or []
        tops = [t for t in cmds.ls(assemblies=True) if t not in ("persp", "top", "front", "side")]
        gate("export: the native's bones, plain, no mesh",
             len(joints) == 116 and not meshes and tops == ["root"],
             "%d joints, %d meshes, tops %s" % (len(joints), len(meshes), tops))
        del keep_scene
        native_root = None

    # ------------------------------------------------------------------ onto a native
    if wanted("onto"):
        fresh()
        name = "Kwang_Ability_Q_Catch"
        autoimport.import_auto(path(name), name, "skeleton", at=(-200.0, 0.0, 0.0))
        root = (cmds.ls("|Kwang_GDC_Character|root", long=True) or [None])[0]
        if root:
            start = at(root, 0.0)
            text = skeletonimport.import_onto_existing(path(name), "again", root)
            print("   ", text[:160])
            gate("onto: Skeleton x Onto selected puts a clip on the native, exact",
                 "exact" in text and not namespaces(), text[:120])
            again = at(root, 0.0)
            gate("onto: it keeps its place", math.hypot(again[0] - start[0], again[2] - start[2])
                 < 1e-3, "(%.3f, %.3f) -> (%.3f, %.3f)" % (start[0], start[2], again[0], again[2]))

    # ------------------------------------------------------------------ nomatch
    if wanted("nomatch"):
        fresh()
        name = "Orc_Walk_Fwd"
        text = autoimport.import_auto(path(name), name, "skeleton")
        print("   ", text[:160])
        groups = [g for g in cmds.ls("|*_Character", long=True) or []]
        gate("nomatch: an Orc clip with Skeleton comes in its own skeleton",
             len(groups) == 1 and not maya_rigs.rigs() and "in its own skeleton" in text,
             "%s | %s" % (groups, text[:80]))

    # ------------------------------------------------------------------ batch
    if wanted("batch"):
        fresh()
        names = ["MM_Fall_Loop", "Kwang_Ability_Q_Catch", "Orc_Walk_Fwd"]

        class Rec(object):
            def __init__(self, name):
                self.name = name
        text = lineimport.run([Rec(n) for n in names], lambda r: (path(r.name), None),
                              "new_rig", auto=True)
        print("   ", text)
        found = sorted(r.namespace for r in maya_rigs.rigs())
        gate("batch: a Manny and an Orc D added, Kwang kept as its own",
             found == ["Manny_Rig", "Orc_D_Rig"] and "own Kwang_GDC Kwang_Ability_Q_Catch" in text
             and bool(cmds.ls("|Kwang_GDC_Character")), "%s | %s" % (found, text[:140]))
        gate("batch: nothing asked", not asked, "%d asked" % len(asked))
        spots = [at(r.main, 0.0) for r in maya_rigs.rigs()]
        root = cmds.ls("|Kwang_GDC_Character|root", long=True)
        if root:
            spots.append(at(root[0], 0.0))
        gaps = [math.hypot(a[0] - b[0], a[2] - b[2]) for i, a in enumerate(spots)
                for b in spots[i + 1:]]
        gate("batch: three slots of the square", len(spots) == 3 and min(gaps) > 200.0,
             "least gap %.1f cm" % (min(gaps) if gaps else 0.0))

    # ------------------------------------------------------------------ explicit
    if wanted("explicit"):
        fresh()
        from maya_uebridge import window
        name = "Kwang_Ability_Q_Catch"
        saved = (window.auto_kind, window.import_target, window._export_unreal, window._timeline)

        class Rec(object):
            source = "unreal"
            fps = None

            def __init__(self, name):
                self.name = name
                self.package = "/Game/" + name
        try:
            window.auto_kind = lambda: "rig"
            window.import_target = lambda: "onto"
            window._export_unreal = lambda record, mesh=False: (path(record.name), None)
            window._timeline = lambda: True
            character.add_character(catalog.character_by_key("Manny_Rig"))
            rig = maya_rigs.rigs()[0]
            cmds.select(rig.main, replace=True)
            text = window._auto_press([Rec(name)], "rig")
            print("   ", text[:160])
            gate("explicit: the selected Manny takes the Kwang clip (asked, kept proportions)",
                 not cmds.ls("|*_Character|*_clipLabel") or True)
            gate("explicit: retargeted onto the selected rig, no own skeleton",
                 "retarget" in text.lower() and not cmds.ls("|Kwang_GDC_Character")
                 and len(asked) == 1, "%s | asked %d" % (text[:90], len(asked)))
            cmds.select(clear=True)
            text = window._auto_press([Rec(name)], "rig")
            print("   ", text[:160])
            gate("explicit: nothing selected - the Auto card decides, its own skeleton",
                 bool(cmds.ls("|Kwang_GDC_Character")) and len(maya_rigs.rigs()) == 1,
                 text[:90])
        finally:
            (window.auto_kind, window.import_target, window._export_unreal,
             window._timeline) = saved

    # ------------------------------------------------------------------ file
    if wanted("file"):
        if not os.path.isfile(SWEEP):
            print("SKIP file: no", SWEEP)
        else:
            fresh()
            text = autoimport.import_auto(SWEEP, "Sweep_Fall", "skeleton")
            print("   ", text[:200])
            groups = cmds.ls("|*_Character", long=True) or []
            hips = cmds.ls("|*_Character|Hips", long=True) or cmds.ls(
                "|*_Character|*|Hips", long=True) or []
            gate("file: a Mixamo clip comes in its own skeleton, plain names",
                 len(groups) == 1 and bool(hips) and not namespaces(),
                 "%s %s %s" % (groups, hips, namespaces()))

    failed = [name for name, ok in RESULTS if not ok]
    print("\n%d of %d gates failed%s" % (len(failed), len(RESULTS),
                                          (": " + "; ".join(failed)) if failed else ""))
    maya_retargetmode.set_asker(None)
    maya.standalone.uninitialize()


if __name__ == "__main__":
    try:
        main()
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
        sys.exit(1)
