"""Live proof for the Add Character button (2026-08-25, revised 2026-09-01).

Run through the command-port bridge in the user's Maya. The 2026-09-01
change is what this had to be rewritten for: the button used to REFUSE
whenever the scene held a skeleton, and now it adds another character every
press ("я должен иметь возможность добавить в сцену сколько угодно
персонажей"). So the branch that used to prove a refusal now proves the
second character instead: it arrives, Maya renames only its TOP node, every
bone under it keeps its plain name, and it becomes the connected one.

Either way every node this script imports is deleted afterwards, so the
scene is left exactly as it was found.

Bridge hygiene (CLAUDE.md): no cmds.file(new), no undo, no literal writes to
animated channels -- this script only imports and deletes what it imported.
"""

import os
import sys
import traceback

REPO = "C:/!!!Work/MayaScripts/SkeldarAnim"

# Note 9: the session imports the INSTALLED SkeldarAnim copy. Prove the
# repo's code, not yesterday's build.
if REPO not in sys.path:
    sys.path.insert(0, REPO)
for name in list(sys.modules):
    if name.split(".")[0] in ("maya_overrig", "maya_uebridge",
                              "maya_scenesetup"):
        del sys.modules[name]

import maya.cmds as cmds  # noqa: E402

from maya_overrig import builder  # noqa: E402
from maya_scenesetup import catalog, character, skeleton  # noqa: E402

FAILURES = []


def gate(label, ok, detail=""):
    print("{0} {1}{2}".format("PASS" if ok else "FAIL", label,
                              " - " + str(detail) if detail else ""))
    if not ok:
        FAILURES.append(label)


def scene_uuids():
    return set(cmds.ls(cmds.ls(), uuid=True))  # trap 8: bulk uuid form


def malware_in_scene():
    return character.malware_nodes(cmds.ls(type="script") or [])


# ---------------------------------------------------------------- gates 1-2

# The label comes from the table, never spelled out here: the dropdown
# renamed the row to "Manny (UE5)" on 2026-09-01 and a hardcoded "Manny
# added" then failed on correct code.
MANNY = catalog.default_character()

path = catalog.character_path()
gate("1 shipped path resolves", path.endswith("assets/Manny_Skeleton.ma"),
     path)
gate("2 shipped file on disk", bool(cmds.file(path, query=True,
                                              exists=True)), path)

with open(path, "rb") as handle:
    content = handle.read()
gate("3 shipped file sanitized",
     b"vaccine" not in content and b"breed_gene" not in content,
     "{0} bytes".format(len(content)))

# ------------------------------------------------------------- adaptive run

# The animator's working state. Importing a `.ma` MOVES THE CURRENT FRAME
# (measured 2026-09-01: 47 -> 17 on the shipped Manny) and every branch here
# clears the selection, so both are put back at the end. The frame is not
# cosmetic -- with autoKey on, the animator's next drag would key the wrong
# one.
FRAME = cmds.currentTime(query=True)
SELECTION = cmds.ls(selection=True, long=True) or []

roots_before = builder.character_roots()

if roots_before:
    before = scene_uuids()
    message = character.add_character()
    new_uuids = scene_uuids() - before
    roots_after = builder.character_roots()
    fresh = [r for r in roots_after if r not in roots_before]

    gate("4 a second character is ADDED, not refused",
         message.startswith(MANNY.label + " added") and len(fresh) == 1,
         message)
    gate("5 the rename is reported", "imported as" in message, message)

    root = fresh[0] if fresh else None
    hierarchy = skeleton.scene_map(root) if root else {}
    gate("6 only the TOP node was renamed",
         bool(root) and root.split("|")[-1] != "root"
         and "pelvis" in hierarchy and "weapon_r" in hierarchy,
         "{0}, {1} bones".format(root.split("|")[-1] if root else "-",
                                 len(hierarchy)))
    gate("7 the first character is untouched",
         all(r in roots_after for r in roots_before),
         "{0} -> {1} roots".format(len(roots_before), len(roots_after)))
    gate("8 no malware in the scene", not malware_in_scene(),
         malware_in_scene())
    gate("9 the new one is the active character",
         skeleton.current_root() == root, skeleton.current_root())

    for uuid in sorted(new_uuids):
        for node in cmds.ls(uuid, long=True) or []:
            if cmds.objExists(node):
                try:
                    cmds.delete(node)
                except Exception:
                    pass  # died with a parent already
    gate("10 the scene comes back to what it was",
         builder.character_roots() == roots_before,
         str(builder.character_roots()))
    print("SKIPPED the empty-scene gates - the scene already held: "
          + ", ".join(r.split("|")[-1] for r in roots_before))
else:
    before = scene_uuids()
    message = character.add_character()
    gate("4 add reports the character",
         message.startswith(MANNY.label + " added"),
         message)

    new_uuids = scene_uuids() - before
    roots = builder.character_roots()
    gate("5 exactly one skeleton now", len(roots) == 1, roots)

    root = roots[0] if roots else None
    subtree = ((cmds.listRelatives(root, allDescendents=True,
                                   fullPath=True) or []) + [root]
               if root else [])
    joints = cmds.ls(subtree, type="joint") if subtree else []
    gate("6 the skeleton is whole", bool(root) and len(joints) >= 93,
         "{0} joints under {1}".format(len(joints), root))

    arrived = []
    for uuid in new_uuids:
        named = cmds.ls(uuid, long=True) or []
        arrived.extend(named)
    mesh_count = len(cmds.ls(arrived, type="mesh") or [])
    gate("7 the geometry arrived", mesh_count >= 6,
         "{0} meshes".format(mesh_count))

    gate("8 no malware in the scene", not malware_in_scene(),
         malware_in_scene())

    hierarchy = skeleton.scene_map(root) if root else {}
    gate("9 weapon_r resolves in the map", "weapon_r" in hierarchy,
         hierarchy.get("weapon_r"))
    gate("10 camera_bone rides along", "camera_bone" in hierarchy,
         hierarchy.get("camera_bone"))
    gate("11 the header would bind", skeleton.current_root() == root,
         skeleton.current_root())

    second = character.add_character()
    second_roots = builder.character_roots()
    gate("12 a second press adds a second character",
         second.startswith(MANNY.label + " added") and len(second_roots) == 2,
         "{0} | {1} roots".format(second, len(second_roots)))
    new_uuids = scene_uuids() - before

    # -------------------------------------------------------------- cleanup
    for uuid in sorted(new_uuids):
        for node in cmds.ls(uuid, long=True) or []:
            if cmds.objExists(node):
                try:
                    cmds.delete(node)
                except Exception:
                    pass  # died with a parent already
    # Locked plugin-settings nodes (UsdDefaultRenderSettings) and Maya's
    # singleton managers (shapeEditorManager, poseInterpolatorManager)
    # survive any delete -- every .ma import leaves them, by Maya's design.
    # The gate is about CONTENT: nothing the animator can see or select may
    # survive, and no script node may (that is where malware lives).
    leftover = scene_uuids() - before
    stray, excused = [], []
    for uuid in sorted(leftover):
        for node in cmds.ls(uuid, long=True) or []:
            kind = cmds.objectType(node)
            inherited = cmds.nodeType(node, inherited=True) or []
            if "dagNode" in inherited or kind == "script":
                stray.append("{0} ({1})".format(node, kind))
            else:
                excused.append("{0} ({1})".format(node, kind))
    gate("13 scene left as found", not stray,
         "stray: {0}; singletons excused: {1}".format(stray or "none",
                                                      excused or "none"))

# --------------------------------------------------- the UE4 mannequin pass
# The 2026-09-01 dropdown. Runs whatever the scene held, because the press
# is repeatable now, and cleans up after itself either way.

UE4 = catalog.character_by_key("UE4_Mannequin")
if UE4 is None:
    gate("20 the UE4 mannequin is in the table", False, "no such entry")
else:
    ue4_path = catalog.character_file(UE4)
    gate("20 the UE4 mannequin ships as FBX",
         ue4_path.endswith("UE4_Mannequin.fbx")
         and cmds.file(ue4_path, query=True, exists=True)
         and character.scene_type(ue4_path) == "FBX", ue4_path)

    before = scene_uuids()
    roots_before = builder.character_roots()
    # The mode the bridge leaves behind is exactly what trap 33 is about, so
    # put it there on purpose and prove the import survives it.
    import maya.mel as _mel
    try:
        _mel.eval("FBXImportMode -v exmerge")
        hostile = _mel.eval("FBXImportMode -q")
    except Exception:
        hostile = ""
    message = character.add_character(UE4)
    print("   " + message)

    new_uuids = scene_uuids() - before
    roots_after = builder.character_roots()
    fresh = [r for r in roots_after if r not in roots_before]
    root = fresh[0] if fresh else None
    hierarchy = skeleton.scene_map(root) if root else {}

    gate("21 it arrives even from the bridge's exmerge mode",
         message.startswith("UE4 Mannequin added") and len(fresh) == 1,
         "mode was {0!r} | {1}".format(hostile, message))
    gate("22 68 joints with plain UE4 names",
         len(hierarchy) == 68 and "root" in hierarchy
         and "spine_03" in hierarchy and "ik_hand_gun" in hierarchy,
         "{0} bones".format(len(hierarchy)))
    gate("23 the UE5-only bones are absent",
         not any(name in hierarchy for name in
                 ("spine_04", "spine_05", "neck_02", "index_metacarpal_l")),
         "spine_04={0} metacarpal={1}".format(
             "spine_04" in hierarchy, "index_metacarpal_l" in hierarchy))
    gate("24 no weapon_r and no camera_bone, as documented",
         "weapon_r" not in hierarchy and "camera_bone" not in hierarchy)
    gate("25 the first character is untouched",
         all(r in roots_after for r in roots_before),
         "{0} -> {1} roots".format(len(roots_before), len(roots_after)))
    gate("26 the new one is the active character",
         skeleton.current_root() == root, skeleton.current_root())
    gate("27 no malware in the scene", not malware_in_scene(),
         malware_in_scene())
    gate("28 the plugin's import mode was put back",
         (_mel.eval("FBXImportMode -q") or "") == hostile,
         _mel.eval("FBXImportMode -q"))

    for uuid in sorted(new_uuids):
        for node in cmds.ls(uuid, long=True) or []:
            if cmds.objExists(node):
                try:
                    cmds.delete(node)
                except Exception:
                    pass  # died with a parent already
    gate("29 the scene comes back to what it was",
         builder.character_roots() == roots_before,
         str(builder.character_roots()))


# ------------------------------- the point of it: a clip lands on the UE4 man
# «просто сделаем так чтобы можно было добавить его в сцену импортировать на
# него анимацию» -- so the last gates are that second half. Skips itself
# with a reason when no editor answers; the rest of this script does not
# need one.

if UE4 is not None:
    try:
        from maya_uebridge import animimport, uelink, uescripts, window
        cached, _project, choice, _content = window.load_cache()
        uelink.discover_nodes(timeout=6)
        pool = [rec for rec in cached
                if "UE4_Mannequin" in (rec.skeleton or "")]
        if not pool:
            raise RuntimeError("no cached clip on UE4_Mannequin - Refresh")
    except Exception as error:
        print("SKIPPED 30-32 (a clip onto the UE4 mannequin): "
              + str(error).splitlines()[0])
    else:
        clip = pool[0]
        roots_before = builder.character_roots()
        before = scene_uuids()
        try:
            character.add_character(UE4)
            fresh = [r for r in builder.character_roots()
                     if r not in roots_before]
            target = fresh[0] if fresh else None
            hierarchy = skeleton.scene_map(target) if target else {}
            gate("30 the bridge resolves it as the import target",
                 animimport.resolve_target() == target,
                 animimport.resolve_target())

            out = os.path.join(window.temp_folder(), "vac_ue4.json")
            fbx = os.path.join(window.temp_folder(), "vac_ue4.fbx")
            payload = uelink.run_script(
                uescripts.export_script(out, clip.package, fbx), out,
                project=choice)
            info = animimport.import_clip(
                payload.get("path") or fbx, "", set_timeline=False,
                clip_fps=payload.get("fps") or clip.fps, merge=True)
            gate("31 every bone of the pack clip landed on it",
                 info.get("joints") == len(hierarchy) and not info.get("stale"),
                 "{0}/{1} animated, {2} without keys".format(
                     info.get("joints"), len(hierarchy),
                     len(info.get("stale") or [])))
            sampled = [name for name in ("pelvis", "spine_01", "upperarm_l",
                                         "hand_r", "thigh_l")
                       if hierarchy.get(name)
                       and cmds.listConnections(hierarchy[name],
                                                type="animCurve")]
            gate("32 the sampled bones really carry curves",
                 len(sampled) == 5, ", ".join(sampled))
        except Exception:
            FAILURES.append("gates 30-32 raised")
            traceback.print_exc()
        finally:
            for uuid in sorted(scene_uuids() - before):
                for node in cmds.ls(uuid, long=True) or []:
                    if cmds.objExists(node):
                        try:
                            cmds.delete(node)
                        except Exception:
                            pass


# ------------------------------------------------------- the working state

for step in (
        lambda: cmds.currentTime(FRAME, edit=True),
        lambda: (cmds.select([n for n in SELECTION if cmds.objExists(n)],
                             replace=True)
                 if any(cmds.objExists(n) for n in SELECTION)
                 else cmds.select(clear=True)),
):
    try:
        step()
    except Exception as exc:
        print("could not restore: {0}".format(exc))

gate("14 frame and selection put back",
     cmds.currentTime(query=True) == FRAME
     and (cmds.ls(selection=True, long=True) or []) ==
     [n for n in SELECTION if cmds.objExists(n)],
     "frame {0:g}, {1} selected".format(
         cmds.currentTime(query=True),
         len(cmds.ls(selection=True, long=True) or [])))

print("RESULT: {0} failures".format(len(FAILURES)))
if FAILURES:
    for name in FAILURES:
        print("  FAILED: " + name)
