"""Live proof for the Add Character button (2026-08-25 design).

Run through the command-port bridge in the user's Maya. Adaptive on purpose:

- In a scene that already holds a skeleton, the only thing this proves LIVE
  is the refusal (the scene must come through untouched); the import gates
  are skipped and say so.
- In a scene with no skeleton, the real thing runs: import, counts, the
  malware sweep finding nothing, the second-press refusal -- and then every
  imported node is deleted, so the scene is left as it was found.

Bridge hygiene (CLAUDE.md): no cmds.file(new), no undo, no literal writes to
animated channels -- this script only imports and deletes what it imported.
"""

import sys

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

roots_before = builder.character_roots()

if roots_before:
    before = scene_uuids()
    message = character.add_character()
    gate("4 refuses over an existing skeleton", "already" in message, message)
    gate("5 refusal touches nothing", scene_uuids() == before,
         "{0} roots".format(len(roots_before)))
    print("SKIPPED import gates - scene already holds a skeleton: "
          + ", ".join(roots_before))
else:
    before = scene_uuids()
    message = character.add_character()
    gate("4 add reports the character", message.startswith("Manny added"),
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
    gate("12 second press refuses", "already" in second, second)

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

print("RESULT: {0} failures".format(len(FAILURES)))
if FAILURES:
    for name in FAILURES:
        print("  FAILED: " + name)
