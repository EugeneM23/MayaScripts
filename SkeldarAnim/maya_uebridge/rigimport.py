"""IMPORT in one press: the rig if it is missing (or a NEW one, asked for),
the clip as its own skeleton, the retarget, the bake, and the source
skeleton gone.

2026-09-07, the animator: «import onto the skeleton давай поменяем на
автоматический импорт нашего рига + импорт выбранной анимации, потом
ретаргет, бейк анимаций на ретаргет и удаление скелета с которого взяли
анимацию, такая вот автоматизация процесса». Every piece already existed --
`character.add_character`, `animimport.import_clip`, `maya_rig_retarget`'s
connect and bake -- and this module is the order they run in, plus the
refusals that stop the press BEFORE anything is imported.

2026-09-08, «я должен иметь возможность добавить в сцену много ригов как
через add так и через import»: the press takes a `target` --

    "rig"      the SELECTED rig, else the only one; a rig is ADDED when the
               scene has none (the 2026-09-07 behaviour);
    "new_rig"  always adds a rig and retargets onto it -- many rigs through
               import.

Two rigs and nothing selected is a refusal that names them, before anything
is exported or imported.

Design: docs/superpowers/specs/2026-09-07-advancedskeleton-pipeline-design.md,
docs/superpowers/specs/2026-09-08-many-rigs-design.md
"""

import os

import maya.cmds as cmds

from maya_uebridge import animimport
from maya_uebridge import records

NO_RIG_FILE = ("no rig file - Manny_Rig.ma is missing from assets/ and the "
               "legacy path")
CONNECTED = ("the rig is still connected to a source (MoCapConstraints "
             "stands) - press Retarget, or disconnect, first")
POSED = ("the rig is posed - AdvancedSkeleton: Go To BuildPose, then import "
         "again")
TARGETS = ("rig", "new_rig")


# ------------------------------------------------------------------ policy

def precheck(rig_present, holder_present, posed, rig_file_ok):
    """The refusal, or "" when the press may go ahead. Pure.

    A missing rig FILE matters only when there is no rig to use; a posed
    rig matters only when there is one (a freshly added rig stands in its
    build pose by construction). The press itself asks the pose question
    AFTER `reset_build_pose`, so `posed` there means a channel the reset
    could not touch.
    """
    if not rig_present and not rig_file_ok:
        return NO_RIG_FILE
    if holder_present:
        return CONNECTED
    if rig_present and posed:
        return POSED
    return ""


def source_root_in(namespace_nodes, is_joint):
    """The topmost joint among a namespace's DAG nodes, or None. Pure.

    Asked of `namespaceInfo(..., dagPath=True, recurse=True)` rather than
    `ls("ns:*")`: a Mixamo clip nests its own namespace (`ns:mixamorig:Hips`)
    and the flat glob does not reach it (the lesson `maya_pmretarget` paid
    for). Shallowest path first, then by name, so the answer is stable.
    """
    joints = [path for path in namespace_nodes or []
              if path.startswith("|") and is_joint(path)]
    if not joints:
        return None
    return sorted(joints, key=lambda path: (path.count("|"), path))[0]


def result_line(name, info, connect_text, bake_text, deleted_namespace,
                rig_label="the rig"):
    """What the status says after the whole press. Pure."""
    span = ""
    if info.get("start") is not None:
        span = ", frames {0:g}-{1:g}".format(info["start"], info["end"])
    head = "{0} retargeted onto {1}{2}".format(name, rig_label, span)
    tail = ("source skeleton {0} deleted".format(deleted_namespace)
            if deleted_namespace else "source skeleton kept")
    parts = [head, _first_line(connect_text), _first_line(bake_text), tail]
    return "  |  ".join(part for part in parts if part)


def _first_line(text):
    lines = [line for line in (text or "").splitlines() if line.strip()]
    return lines[0] if lines else ""


def fresh_rig(before, after):
    """The one rig `after` holds that `before` did not, by namespace, or None. Pure."""
    taken = set(rig.namespace for rig in before or [])
    new = [rig for rig in after or [] if rig.namespace not in taken]
    return new[0] if len(new) == 1 else None


# ------------------------------------------------------------------ action

def _rig_file_ok():
    from maya_scenesetup import catalog
    path = catalog.character_file(catalog.default_rig())
    return bool(path) and os.path.isfile(path)


def import_and_retarget(fbx_path, name, clip_fps=None, set_timeline=True,
                        target="rig", rig=None):
    """The press. Returns the status line.

    `rig` (2026-10-01, an animation dragged onto a rig in the viewport) is
    the rig that takes the clip with `target="rig"`, whatever is selected;
    None asks the selection as the Import button does. "new_rig" ignores it.

    Refusals happen first and touch nothing. After the import, a connect
    refusal leaves the imported skeleton in the scene and says so -- the
    animator can fix what it names and press Retarget by hand.
    """
    import maya_rig_retarget
    import maya_rigs
    from maya_scenesetup import catalog, character

    if target not in TARGETS:
        return "unknown import target {0!r}".format(target)
    all_rigs = maya_rigs.rigs()
    if target == "new_rig":
        rig = None
    if target == "rig" and rig is None and all_rigs:
        rig, refusal = maya_rigs.current_rig()
        if rig is None:
            return refusal
    add_rig = rig is None
    mod, module_refusal = (maya_rig_retarget.rig_module(rig) if rig
                           else (None, ""))
    if rig is not None and mod is None:
        return module_refusal
    holder = bool(mod is not None and cmds.objExists(mod.holder_of(rig)))
    refusal = precheck(not add_rig, holder, False, _rig_file_ok())
    if refusal:
        return refusal

    notes = []
    deleted = ""
    cmds.undoInfo(openChunk=True, chunkName="UE anim import + retarget")
    try:
        if add_rig:
            notes.append(character.add_character(catalog.default_rig()))
            rig = fresh_rig(all_rigs, maya_rigs.rigs())
            if rig is None:
                return "  |  ".join(notes + [
                    "the added rig was not found in the scene"])
            mod, module_refusal = maya_rig_retarget.rig_module(rig)
            if mod is None:
                return "  |  ".join(notes + [module_refusal])
        else:
            # A clip import REPLACES the take, as the old merge did (trap
            # 27: the target's animation is cleared first): the previous
            # bake's keys go and the controls return to the build pose. A
            # baked rig passes `posed_controls` -- a keyed channel is not
            # settable and is skipped -- while standing in the take's pose,
            # and a connect made there would measure the pole offsets
            # against that pose. What is still posed afterwards is a
            # channel nothing here may touch, and that IS a refusal.
            curves, zeroed = mod.reset_build_pose(rig)
            if curves or zeroed:
                notes.append("previous take cleared ({0} curves), rig at "
                             "build pose".format(curves))
            posed = mod.posed_controls(rig=rig)
            if posed:
                return "  |  ".join(notes + [
                    "{0}: {1}".format(POSED, ", ".join(sorted(posed)[:6]))])

        namespace = records.namespace_for(name,
                                          animimport.existing_namespaces())
        info = animimport.import_clip(fbx_path, namespace,
                                      set_timeline=set_timeline,
                                      clip_fps=clip_fps, merge=False)
        nodes = cmds.namespaceInfo(namespace, listOnlyDependencyNodes=True,
                                   recurse=True, dagPath=True) or []
        source = source_root_in(
            nodes, lambda path: cmds.objectType(path) == "joint")
        if source is None:
            return "  |  ".join(notes + [
                "{0} imported into {1} but holds no joint - nothing to "
                "retarget".format(name, namespace)])

        connect_text = maya_rig_retarget.connect(source_root=source, rig=rig)
        if not cmds.objExists(mod.holder_of(rig)):
            return "  |  ".join(notes + [
                "{0} imported as {1}; retarget refused: {2}".format(
                    name, namespace, _first_line(connect_text))])

        bake_text = maya_rig_retarget.bake(rig=rig)
        cmds.namespace(removeNamespace=namespace,
                       deleteNamespaceContent=True)
        deleted = namespace
    finally:
        cmds.undoInfo(closeChunk=True)

    line = result_line(name, info, connect_text, bake_text, deleted,
                       maya_rigs.label(rig))
    return "  |  ".join(notes + [line]) if notes else line
