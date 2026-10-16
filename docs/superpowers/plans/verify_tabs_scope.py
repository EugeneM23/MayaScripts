"""Scene tabs, stage 2: the plugin sees only the active tab - the proof in
mayapy standalone (2026-10-15).

A DECOY tab holds a Manny rig (keyed), a bare Manny UE5 skeleton and a bare
UE4 Mannequin (plain `root`s, the mannequin red from the palette); the work
happens in another tab: the plugin's scene questions, Add Character, a
retarget, an export with nothing selected, a weapon, Delete, a clip's
namespace, a save, Shared's copy. Every section is gated on its own (a
section that raises fails its "ran" gate and the next one still runs), and
the decoy is checked untouched; last, a weapon's file is opened by Open
scene (a tab of its own).

Run from the repo root (PowerShell), after verify_scene_tabs.py has built its
fixtures once:
  $env:MAYA_APP_DIR = "$env:TEMP\\skeldar_tabs_appdir"
  & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/verify_tabs_scope.py
Spec: docs/superpowers/specs/2026-10-15-scene-tabs-plugin-scope-design.md
"""
import os
import shutil
import sys
import tempfile
import traceback

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402

for _plug in ("matrixNodes", "quatNodes", "fbxmaya"):
    try:
        cmds.loadPlugin(_plug, quiet=True)
    except RuntimeError:
        pass

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(REPO, "SkeldarAnim").replace("\\", "/"))

from maya_scenetabs import opening, records, saving, scope, session, switching  # noqa: E402

WORK = os.path.join(tempfile.gettempdir(), "skeldar_tabs_verify").replace("\\", "/")
RUN = WORK + "/scope_run"
RESULTS = []
DECOY = "tab_rig"
ACTIVE = "tab_plain"


def gate(name, ok, detail=""):
    RESULTS.append(bool(ok))
    print("%s  %s  %s" % ("PASS" if ok else "FAIL", name, detail))


def section(name, run, ctx):
    try:
        run(ctx)
    except Exception:                                            # noqa: BLE001
        gate("%s: ran to the end" % name, False, traceback.format_exc()[-600:])
    finally:
        try:
            scope.enter_active(cmds)                             # whatever a failure left current
        except Exception:                                        # noqa: BLE001
            pass


def copy(name, as_name=None):
    os.makedirs(RUN, exist_ok=True)
    target = RUN + "/" + (as_name or name)
    shutil.copyfile(WORK + "/" + name, target)
    return target


def decoy_snapshot():
    """The decoy's nodes and what they hold: names, the rig's keys, the bare skeletons' joints'
    world matrices, its materials' colours."""
    nodes = sorted(cmds.namespaceInfo(":" + DECOY, listOnlyDependencyNodes=True, recurse=True) or [])
    keys = cmds.keyframe(DECOY + ":Manny_Rig:FKShoulder_R.rotateZ", q=True, timeChange=True,
                         valueChange=True)
    joints = sorted(j for root in cmds.ls(DECOY + ":root", long=True) or []
                    for j in [root] + (cmds.listRelatives(root, allDescendents=True, type="joint",
                                                          fullPath=True) or []))
    worlds = [[round(v, 6) for v in cmds.xform(j, q=True, matrix=True, worldSpace=True)] for j in joints]
    colours = sorted((m, tuple(round(c, 4) for c in cmds.getAttr(m + ".color")[0]))
                     for m in cmds.ls(DECOY + ":*", materials=True, recursive=True) or []
                     if cmds.attributeQuery("color", node=m, exists=True))
    return {"nodes": nodes, "keys": keys, "worlds": worlds, "colours": colours}


def questions(ctx):
    import maya_rigs
    from maya_overrig import builder
    from maya_scenesetup import skeleton
    from maya_uebridge import animimport
    gate("scope: the active namespace", scope.active_namespace(cmds) == ACTIVE, scope.active_namespace(cmds))
    gate("scope: the decoy is not the active tab's", not scope.in_active(DECOY + ":root", cmds))
    gate("scope: the current namespace is the active tab's",
         cmds.namespaceInfo(currentNamespace=True).lstrip(":") == ACTIVE)
    gate("rigs: none in the active tab (the decoy's is not seen)", maya_rigs.rigs() == [],
         [r.namespace for r in maya_rigs.rigs()])
    rig, refusal = maya_rigs.current_rig([])
    gate("rigs: current_rig says there is none, not two", rig is None and refusal == maya_rigs.NO_RIG, refusal)
    gate("roots: no skeleton in the active tab", builder.character_roots() == [], builder.character_roots())
    gate("roots: the bridge sees none", animimport.skeleton_roots() == [], animimport.skeleton_roots())
    gate("roots: current_root answers nothing", skeleton.current_root() is None)


def add(ctx):
    import maya_rigs
    from maya_scenesetup import catalog, character, colour
    cmds.select(clear=True)
    message = character.add_character(catalog.default_rig())
    rigs = maya_rigs.rigs()
    gate("add: the rig is the active tab's", [r.namespace for r in rigs] == [ACTIVE + ":Manny_Rig"],
         ([r.namespace for r in rigs], message))
    gate("add: the line names it as the tab shows it", "as Manny_Rig" in message, message)
    gate("add: its character group and layer are in the tab, named as the tab shows them",
         cmds.objExists(ACTIVE + ":Manny_Rig_Character") and cmds.objExists(ACTIVE + ":Manny_Rig_Layer"))
    gate("add: Main selected", cmds.ls(selection=True) == [ACTIVE + ":Manny_Rig:Main"], cmds.ls(selection=True))
    free = colour.free_colour()
    gate("add: the tab's free colour is the palette's first (the decoy wears it)",
         free is not None and getattr(free, "rgb", free) == colour.PALETTE[0].rgb,
         (free, colour.our_materials()))
    message = character.add_character(catalog.default_character())
    gate("add: a bare skeleton in the tab", cmds.objExists(ACTIVE + ":root")
         and cmds.objExists(ACTIVE + ":Manny_Skeleton_Character"), message)
    gate("scope: the current namespace is still the tab's after two imports",
         cmds.namespaceInfo(currentNamespace=True).lstrip(":") == ACTIVE)
    ctx["rig"] = maya_rigs.rigs()[0]


def retarget(ctx):
    import maya_rig_retarget
    pelvis = cmds.ls(ACTIVE + ":pelvis", long=True)[0]
    for frame, value in ((0, 0.0), (10, 20.0)):
        cmds.setKeyframe(pelvis, attribute="translateX", time=frame, value=value)
    cmds.playbackOptions(minTime=0, maxTime=10)
    ok, text = maya_rig_retarget.run_retarget(source_root=cmds.ls(ACTIVE + ":root", long=True)[0],
                                              rig=ctx["rig"], bones="rotation")
    gate("retarget: in the tab, onto the tab's rig", ok and "rigs in the scene" not in text, text[:200])
    gate("retarget: the rig took the clip",
         (cmds.keyframe(ACTIVE + ":Manny_Rig:RootX_M", q=True, keyframeCount=True) or 0) > 0)
    gate("retarget: its camera in the rig's namespace",
         cmds.objExists(ACTIVE + ":Manny_Rig:SceneSetup_camera"),
         cmds.ls("*SceneSetup_camera*", recursive=True))


def export(ctx):
    from maya_uebridge import animexport
    cmds.select(clear=True)
    root = animexport.resolve_root()
    first = root[0] if isinstance(root, tuple) else root
    gate("export: nothing selected names the tab's character", bool(first) and scope.in_active(first, cmds), root)
    cmds.select(ACTIVE + ":root")
    fbx = RUN + "/scoped_export.fbx"
    animexport.export_hierarchy(fbx, layout="plain")
    with scope.at_root(cmds):                                    # read back beside everything, then gone
        mel.eval("FBXImportMode -v add")
        cmds.file(fbx, i=True, type="FBX", namespace="chk", ignoreVersion=True)
    names = [n.split("|")[-1] for n in cmds.ls("chk:*", type="joint", long=True) or []]
    nested = [n for n in names if n.count(":") != 1]
    gate("export: the file's bones plain (read back as chk:root, chk:pelvis)",
         "chk:root" in names and "chk:pelvis" in names and not nested, (len(names), nested[:4]))
    cmds.namespace(removeNamespace=":chk", deleteNamespaceContent=True)
    gate("export: the tab's skeleton keeps its names", cmds.objExists(ACTIVE + ":root")
         and cmds.objExists(ACTIVE + ":pelvis"))


def weapon(ctx):
    import maya_rigs
    from maya_scenesetup import catalog, equip
    line = equip.to_hand(maya_rigs.rigs()[0].skeleton_root, "R", catalog.WEAPONS[0])
    weapons = cmds.ls("*.mayaWeapon", objectsOnly=True, recursive=True) or []
    gate("weapon: in the tab", weapons and all(n.split("|")[-1].startswith(ACTIVE + ":") for n in weapons),
         (weapons, line))
    gate("weapon: the line names the character as the tab shows it", "Manny_Rig's" in line, line)


def delete(ctx):
    from maya_scenesetup import deletion
    line = deletion.delete_selected([cmds.ls(ACTIVE + ":root", long=True)[0]], confirm=lambda *a, **k: True)
    gate("delete: the tab's skeleton went", not cmds.objExists(ACTIVE + ":root"), line)
    gate("delete: the decoy's plain skeletons stayed", len(cmds.ls(DECOY + ":root") or []) == 2)


def clip(ctx):
    from maya_uebridge import formats, nativeimport
    joints = [{"name": "clipHips", "parent": None, "t": (0, 90, 0)},
              {"name": "clipSpine", "parent": 0, "t": (0, 10, 0)}]
    formats.build("clipX", joints, [None, None], [], set_timeline=False)
    gate("clip: built at the root", cmds.objExists(":clipX:clipHips"))
    gate("clip: the current namespace is the tab's again",
         cmds.namespaceInfo(currentNamespace=True).lstrip(":") == ACTIVE)
    note = nativeimport.merge_into_root("clipX")
    gate("clip: kept, it merges into the tab", cmds.objExists(ACTIVE + ":clipHips")
         and not cmds.namespace(exists=":clipX"), note)


def bridge(ctx):
    """2026-10-16, found live: every Animation Setup import left its clip skeleton at the
    ROOT, in every tab - its namespace was deleted by a name relative to the tab's (trap 254)."""
    clip_file = "C:/!!!Work/Animations/Export/ShortSword_Walk_1P.fbx"
    if not os.path.isfile(clip_file):
        gate("bridge: SKIPPED - no clip on this disk", True)
        return
    import maya_retargetmode
    from maya_uebridge import lineimport, records as bridge_records, rigimport
    maya_retargetmode.set_asker(lambda *a, **k: "stretch")
    tabs = [t["ns"] for t in session.state()["tabs"]]

    def outside():
        tops = [t for t in cmds.ls(assemblies=True) or []
                if not any(t.startswith(ns + ":") for ns in tabs) and t not in ("persp", "top", "front", "side")]
        spaces = [n for n in cmds.namespaceInfo(":", listOnlyNamespaces=True) or []
                  if n not in ("UI", "shared") and n not in tabs]
        return tops + spaces

    line = rigimport.import_and_retarget(clip_file, "ShortSword_Walk_1P", clip_fps=30.0, target="new_rig")
    gate("bridge: onto a new rig, nothing left outside the tabs", not outside(), (outside(), line[:160]))
    gate("bridge: the line names the rig as the tab shows it", "tab_" not in line, line[:200])
    record = bridge_records.AnimRecord(*(["ShortSword_Walk_1P"] + [""] * (len(bridge_records.AnimRecord._fields) - 1)))
    line = lineimport.run([record._replace(fps=30.0)], lambda r: (clip_file, 30.0), "skeleton")
    gate("bridge: onto a new skeleton, nothing left outside the tabs", not outside(), (outside(), line[:160]))
    gate("bridge: the scope still the active tab's",
         cmds.namespaceInfo(currentNamespace=True).lstrip(":") == ACTIVE)


def save(ctx):
    saved = saving.save_tab()
    saving.save_tab(path=RUN + "/plain_tab.ma", adopt=False)
    with open(RUN + "/plain_tab.ma") as handle:
        text = handle.read()
    named = [line for line in text.splitlines()
             if line.startswith(("createNode", "connectAttr", "parent ", "rename ")) and "tab_" in line]
    gate("save: the tab's file holds its rig, every node named without the tab",
         '"Manny_Rig:Main"' in text and not named, (saved, named[:3]))
    gate("save: the rig's clip label names no tab", '"tab_plain"' not in text)


def shared(ctx):
    opening.open_tab(ctx["film"])
    target = RUN + "/shared_copy.ma"
    scope.export_scene(target, "mayaAscii", cmds)
    with open(target) as handle:
        text = handle.read()
    gate("shared: the active tab alone, no prefix", "tab_" not in text and '"hero"' in text)
    gate("shared: its reference written in", '"ref:box"' in text and "file -r " not in text)
    gate("shared: the tab keeps its own path", records.tab(session.state(), "tab_film")["path"] == ctx["film"])


def decoy(ctx):
    switching.switch(DECOY)
    after = decoy_snapshot()
    for key in ("nodes", "keys", "worlds", "colours"):
        same = after[key] == ctx["before"][key]
        detail = "" if same else (sorted(set(map(str, after[key])) ^ set(map(str, ctx["before"][key])))[:8])
        gate("decoy: %s untouched" % key, same, detail)
    tabs = set(t["ns"] for t in session.state()["tabs"])
    every = [n.lstrip(":") for n in cmds.namespaceInfo(":", listOnlyNamespaces=True, recurse=True) or []]
    stray = [n for n in every if n.split(":")[0] not in tabs | {"UI", "shared"} or ":tab_" in n]
    gate("scene: no stray or doubled namespace", not stray, stray)


def open_scene(ctx):
    """Open scene on a weapon's right-button menu: its FBX opens in a tab of its own, the session stays."""
    from maya_scenesetup import catalog, opener
    before = [t["ns"] for t in session.state()["tabs"]]
    entry = catalog.WEAPONS[0]
    text = opener.open_asset(entry.path, entry.label)
    after = [t["ns"] for t in session.state()["tabs"]]
    new = [ns for ns in after if ns not in before]
    gate("open scene: a weapon's FBX opens in a tab of its own",
         len(new) == 1 and scope.active_namespace(cmds) == new[0], (new, text))
    meshes = cmds.ls(new[0] + ":*", type="mesh", recursive=True) or [] if new else []
    gate("open scene: its model is in that tab", bool(meshes), meshes[:2])
    gate("open scene: every other tab stays open", all(ns in after for ns in before), after)


def main():
    from maya_scenesetup import catalog, character
    rig_file, plain_file, film_file = copy("rig.ma"), copy("plain.mb"), copy("film.ma")
    cmds.file(new=True, force=True)
    cmds.file(rig_file, open=True, force=True)
    character.add_character(catalog.default_character())                         # plain `root`
    character.add_character(catalog.character_for("UE4_Mannequin", "skeleton"))   # untextured: red
    opening.open_tab(plain_file)
    gate("setup: the decoy tab holds a rig and two plain skeletons",
         cmds.objExists(DECOY + ":Manny_Rig:Main") and len(cmds.ls(DECOY + ":root") or []) == 2)
    switching.switch(DECOY)
    ctx = {"before": decoy_snapshot(), "film": film_file}
    switching.switch(ACTIVE)
    for name, run in (("questions", questions), ("add", add), ("retarget", retarget), ("export", export),
                      ("weapon", weapon), ("delete", delete), ("clip", clip), ("bridge", bridge), ("save", save),
                      ("shared", shared), ("decoy", decoy), ("open_scene", open_scene)):
        section(name, run, ctx)


if __name__ == "__main__":
    try:
        main()
    except Exception:                                            # noqa: BLE001
        gate("ran to the end", False, traceback.format_exc())
    failed = RESULTS.count(False)
    print("%d of %d gates failed" % (failed, len(RESULTS)))
    maya.standalone.uninitialize()
    sys.exit(1 if failed else 0)
