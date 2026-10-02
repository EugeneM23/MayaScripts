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

2026-10-01, an animation dragged out of the list (`listdrag`): `rig=` names
the rig the clip was dropped on; a rig ADDED is the one active in the
Characters card (`new_rig_entry`: its picked row when that is a rig, else
Manny - «на тот который активен во вкладке characters но если в персонажах
нет активного рига то тогда берем базовый маникен»); and `at=` - the floor
point a drop beside every rig aimed at - leaves the new rig standing there
after every bake («риг с анимацией оставался в том месте куда мы указали
после всех перезапеканий»): the clip is wrapped in a group of its namespace
before the connect, which measures it unmoved, and the group is moved after
the connect, so the bake carries the move into the controls, the helper
bones and the camera. The exported root bone carries it too.

The same evening, «если я перетащил анимацию в риг который на сцене сейчас ...
позиция меняется на позицию из анимационного файла ... я хочу чтобы риг
остался на своем месте»: a rig ALREADY in the scene keeps its place - where
its Main stands on the current frame, read before the reset zeroes it, and
its heading - by the same wrapper, turned about Main's start and moved onto
that place. A drop on a rig and the Import button (Rig mode) alike.

2026-10-01, several animations at once (`lineimport`): the press is four
pieces a batch reuses in its own order - `plan_press` (which rig, the
refusals), `ready_rig` (a rig added, or the standing one reset),
`import_source` (the clip as its own skeleton), `retarget_imported`
(connect, place, bake, delete) - and `stand_skeleton` stands a skeleton of
several on its slot. `import_and_retarget` composes them as before.

Design: docs/superpowers/specs/2026-09-07-advancedskeleton-pipeline-design.md,
docs/superpowers/specs/2026-09-08-many-rigs-design.md,
docs/superpowers/specs/2026-10-01-uebridge-many-animations-design.md
"""

import math
import os

import maya.cmds as cmds

from maya_uebridge import animimport
from maya_uebridge import records

NO_RIG_FILE = "no rig file - {0} is missing from assets/"
SHIFT_NODE = "skeldarDropShift"   # the clip's wrapper, moved onto the rig's place
CONNECTED = ("the rig is still connected to a source (MoCapConstraints "
             "stands) - press Retarget, or disconnect, first")
POSED = ("the rig is posed - AdvancedSkeleton: Go To BuildPose, then import "
         "again")
TARGETS = ("rig", "new_rig")


# ------------------------------------------------------------------ policy

def precheck(rig_present, holder_present, posed, rig_file_ok,
             rig_file="Manny_Rig.ma"):
    """The refusal, or "" when the press may go ahead. Pure.

    A missing rig FILE matters only when there is no rig to use; a posed
    rig matters only when there is one (a freshly added rig stands in its
    build pose by construction). The press itself asks the pose question
    AFTER `reset_build_pose`, so `posed` there means a channel the reset
    could not touch.
    """
    if not rig_present and not rig_file_ok:
        return NO_RIG_FILE.format(rig_file)
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


def rig_entry_for(chosen, default):
    """The rig a press adds: `chosen` (the Characters card's active row) when
    it is a rig, else `default` (Manny). Pure."""
    if chosen is not None and getattr(chosen, "kind", "") == "rig":
        return chosen
    return default


def shift_for(at, root_at_start):
    """(dx, 0, dz) that stands the clip's root, at its first frame, on the
    floor point `at`: horizontal only, the clip keeps its own height. Pure."""
    return (at[0] - root_at_start[0], 0.0, at[2] - root_at_start[2])


def heading(matrix):
    """The yaw in degrees of a node's +Z axis on the floor, from its flat
    row-major world matrix (Maya's xform -q -ws -m). Pure."""
    return math.degrees(math.atan2(matrix[8], matrix[10]))


def facing(matrix):
    """The yaw in degrees a node or a skeleton's root faces on the floor, from
    its flat row-major world matrix. Pure.

    Main faces its +Z; a UE root stands under the -90 X turn (its own
    jointOrient, or the Creep's Armature), so its +Z points up and the way it
    faces is its -Y. Whichever of the two lies flatter on the floor is the
    one read, so both answer 0 standing as their files have them."""
    z = (matrix[8], matrix[9], matrix[10])
    if math.hypot(z[0], z[2]) >= abs(z[1]):
        return math.degrees(math.atan2(z[0], z[2]))
    return math.degrees(math.atan2(-matrix[4], -matrix[6]))


def place_moves(point, yaw, start_matrix, facing_of=heading):
    """(pivot, turn, move) that stand a node - at the clip's first frame at
    `start_matrix` - on the floor `point` facing `yaw` (None: keep its own
    facing): turn the clip `turn` degrees about world Y around `pivot` (the
    node's start), then move it horizontally by `move`. `facing_of` reads
    the yaw of `start_matrix` (`heading` for a rig's Main, `facing` for a
    skeleton's root). Pure."""
    pivot = (start_matrix[12], start_matrix[13], start_matrix[14])
    turn = 0.0
    if yaw is not None:
        turn = (yaw - facing_of(start_matrix) + 180.0) % 360.0 - 180.0
    return pivot, turn, shift_for(point, pivot)


def fresh_rig(before, after):
    """The one rig `after` holds that `before` did not, by namespace, or None. Pure."""
    taken = set(rig.namespace for rig in before or [])
    new = [rig for rig in after or [] if rig.namespace not in taken]
    return new[0] if len(new) == 1 else None


# ------------------------------------------------------------------ action

def new_rig_entry():
    """The catalog row of the rig a press adds: the Characters card's active
    row when it is a rig (read from its memory, so the card need not be
    open), else Manny."""
    from maya_scenesetup import catalog
    try:
        from maya_scenesetup import window as scene_window
        chosen = scene_window.chosen_character()
    except Exception:                                        # noqa: BLE001
        chosen = None
    return rig_entry_for(chosen, catalog.default_rig())


def _rig_file_ok(entry=None):
    from maya_scenesetup import catalog
    path = catalog.character_file(entry or catalog.default_rig())
    return bool(path) and os.path.isfile(path)


def _rig_file_name(entry):
    from maya_scenesetup import catalog
    path = catalog.character_file(entry or catalog.default_rig()) or ""
    return os.path.basename(path) or "the rig file"


def _wrap(source, namespace):
    """The clip's root inside a group of its namespace (it dies with the
    namespace), standing where it stood: (group, the root's new path)."""
    uuid = cmds.ls(source, uuid=True)[0]
    group = cmds.group(source, name="{0}:{1}".format(namespace, SHIFT_NODE))
    return group, cmds.ls(uuid, long=True)[0]


def rig_place(rig):
    """Where the rig stands now: its Main on the current frame, as
    {"point", "yaw"}. Read BEFORE `reset_build_pose` zeroes it."""
    matrix = cmds.xform(rig.main, query=True, worldSpace=True, matrix=True)
    return {"point": (matrix[12], matrix[13], matrix[14]),
            "yaw": heading(matrix), "kept": True}


def _place(group, rig, place, start):
    """Turn and move the clip's wrapper so the rig's Main, at the clip's first
    frame, stands on `place` (and faces its yaw, when it has one). Measured on
    Main after the connect - with a real time change, a constraint chain does
    not answer getAttr(time=) (trap 69). The clip's keys are never touched."""
    if start is not None:
        cmds.currentTime(start, update=True)
    matrix = cmds.xform(rig.main, query=True, worldSpace=True, matrix=True)
    return move_wrapper(group, place, matrix)


def move_wrapper(group, place, start_matrix, facing_of=heading):
    """Turn the clip's wrapper about the node standing at `start_matrix` (at
    the clip's first frame) onto `place`'s yaw, move it onto its point, and
    say where it stands."""
    pivot, turn, (dx, dy, dz) = place_moves(place["point"], place.get("yaw"),
                                            start_matrix, facing_of)
    if abs(turn) > 1e-6:
        cmds.xform(group, worldSpace=True, pivots=pivot)
        cmds.setAttr(group + ".rotateY", turn)
    cmds.move(dx, dy, dz, group, relative=True, worldSpace=True)
    x, z = int(round(place["point"][0])), int(round(place["point"][2]))
    if place.get("kept"):
        return "kept in place at ({0}, {1})".format(x, z)
    return "standing at floor ({0}, {1})".format(x, z)


def root_at(source, frame=None):
    """Where the clip's root stands at `frame` (now, with None): a bare
    skeleton driven by its own curves, read in a time context - no
    constraint, so trap 69 does not apply, and no rig is evaluated."""
    if frame is None:
        return tuple(cmds.xform(source, query=True, worldSpace=True,
                                translation=True))
    matrix = cmds.getAttr(source + ".worldMatrix[0]", time=frame)
    return (matrix[12], matrix[13], matrix[14])


def stand_skeleton(namespace, source, point, start=None):
    """A clip's skeleton, its root at its first frame, onto the floor `point`
    (horizontally): the root wrapped in a group of its namespace and the
    group moved - its keys are never touched. Returns (dx, dz)."""
    at_start = root_at(source, start)
    shift, _root = _wrap(source, namespace)
    dx, dy, dz = shift_for(point, at_start)
    cmds.move(dx, dy, dz, shift, relative=True, worldSpace=True)
    return (dx, dz)


NO_JOINT = "{0} imported into {1} but holds no joint - nothing to retarget"


def plan_press(target, rig=None):
    """(plan, refusal): which rig a press acts on, before anything is touched.

    The plan is a dict - `rig` (None when one is to be added), `mod` (its
    retarget module), `add`, `entry` (the catalog row a rig is added from).
    `rig` names the rig for target "rig" (a drop on it); None asks the
    selection, else the only rig, else adds one. "new_rig" always adds."""
    import maya_rig_retarget
    import maya_rigs

    if target not in TARGETS:
        return None, "unknown import target {0!r}".format(target)
    all_rigs = maya_rigs.rigs()
    if target == "new_rig":
        rig = None
    if target == "rig" and rig is None and all_rigs:
        rig, refusal = maya_rigs.current_rig()
        if rig is None:
            return None, refusal
    add_rig = rig is None
    mod, module_refusal = (maya_rig_retarget.rig_module(rig) if rig
                           else (None, ""))
    if rig is not None and mod is None:
        return None, module_refusal
    holder = bool(mod is not None and cmds.objExists(mod.holder_of(rig)))
    entry = new_rig_entry() if add_rig else None
    file_ok = _rig_file_ok(entry)
    refusal = precheck(not add_rig, holder, False, file_ok,
                       "" if file_ok else _rig_file_name(entry))
    if refusal:
        return None, refusal
    return dict(rig=rig, mod=mod, add=add_rig, entry=entry), ""


def ready_rig(plan):
    """(rig, mod, notes, failure): the rig the clip goes onto, ready for the
    connect - a rig ADDED from `plan["entry"]` (every call adds one), or the
    planned rig with its previous take cleared."""
    import maya_rig_retarget
    import maya_rigs
    from maya_scenesetup import character

    notes = []
    if plan["add"]:
        before = maya_rigs.rigs()
        notes.append(character.add_character(plan["entry"]))
        rig = fresh_rig(before, maya_rigs.rigs())
        if rig is None:
            return None, None, notes, "the added rig was not found in the scene"
        mod, module_refusal = maya_rig_retarget.rig_module(rig)
        if mod is None:
            return None, None, notes, module_refusal
        return rig, mod, notes, ""
    rig, mod = plan["rig"], plan["mod"]
    # A clip import REPLACES the take, as the old merge did (trap 27: the
    # target's animation is cleared first): the previous bake's keys go and
    # the controls return to the build pose. A baked rig passes
    # `posed_controls` -- a keyed channel is not settable and is skipped --
    # while standing in the take's pose, and a connect made there would
    # measure the pole offsets against that pose. What is still posed
    # afterwards is a channel nothing here may touch, and that IS a refusal.
    curves, zeroed = mod.reset_build_pose(rig)
    if curves or zeroed:
        notes.append("previous take cleared ({0} curves), rig at "
                     "build pose".format(curves))
    posed = mod.posed_controls(rig=rig)
    if posed:
        return rig, mod, notes, "{0}: {1}".format(
            POSED, ", ".join(sorted(posed)[:6]))
    return rig, mod, notes, ""


def import_source(fbx_path, name, clip_fps=None, set_timeline=True):
    """(namespace, info, source): the clip as its own namespaced skeleton and
    its topmost joint (None when it brought none)."""
    namespace = records.namespace_for(name, animimport.existing_namespaces())
    info = animimport.import_clip(fbx_path, namespace,
                                  set_timeline=set_timeline,
                                  clip_fps=clip_fps, merge=False)
    nodes = cmds.namespaceInfo(namespace, listOnlyDependencyNodes=True,
                               recurse=True, dagPath=True) or []
    source = source_root_in(nodes, lambda path: cmds.objectType(path) == "joint")
    return namespace, info, source


CANCELLED = "cancelled - nothing changed"


def decide_bones(rig, mod, source):
    """The retarget version for this clip onto `rig` (2026-10-02,
    `maya_retargetmode`): the Retarget card's setting and the measured clip,
    asked when the stretch would break the rig's proportions. Returns the
    Decision; raises `maya_retargetmode.Cancelled` on Cancel. A module that
    cannot measure answers the legacy retarget (mode None)."""
    import maya_rig_retarget
    import maya_retargetmode
    decide = getattr(maya_rig_retarget, "decide_for", None)
    if decide is None:
        return maya_retargetmode.Decision(None, False, "")
    return decide(mod, rig, source)


def discard_added(rig):
    """A rig this press added, deleted whole (a Cancel leaves the scene as it
    was): Characters' own Delete, unasked."""
    from maya_scenesetup import deletion
    return deletion.delete_selected([rig.main], confirm=lambda _text: True)


def retarget_imported(rig, mod, namespace, info, source, name, place=None,
                      bones=None):
    """(line, failure): the imported clip connected onto `rig`, moved onto
    `place` (a dict with "point" and "yaw"; None leaves it where it is),
    baked, and its skeleton deleted. A connect refusal leaves the skeleton
    as it arrived and is the failure. `bones` is the retarget version
    ("rotation" / "stretch"; None the legacy rule)."""
    import maya_rig_retarget
    import maya_rigs

    # The wrapper goes on BEFORE the connect: the holder remembers the
    # clip's root by PATH (trap 16), so the root must not be re-parented
    # after it. The connect measures the clip unmoved; the wrapper moves
    # after it, and the bake carries the move.
    shift = None
    if place is not None:
        shift, source = _wrap(source, namespace)
    connect_text = maya_rig_retarget.connect(
        source_root=source, rig=rig, **({"bones": bones} if bones else {}))
    if not cmds.objExists(mod.holder_of(rig)):
        if shift:
            cmds.ungroup(shift)
        return "", "{0} imported as {1}; retarget refused: {2}".format(
            name, namespace, _first_line(connect_text))
    placed = _place(shift, rig, place, info.get("start")) if shift else ""

    bake_text = maya_rig_retarget.bake(rig=rig)
    cmds.namespace(removeNamespace=namespace, deleteNamespaceContent=True)
    line = result_line(name, info, connect_text, bake_text, namespace,
                       maya_rigs.label(rig))
    if placed:
        line = "{0}  |  {1}".format(line, placed)
    return line, ""


def import_and_retarget(fbx_path, name, clip_fps=None, set_timeline=True,
                        target="rig", rig=None, at=None):
    """The press. Returns the status line.

    `rig` (2026-10-01, an animation dragged onto a rig in the viewport) is
    the rig that takes the clip with `target="rig"`, whatever is selected;
    None asks the selection as the Import button does. "new_rig" ignores it.
    A rig ADDED is `new_rig_entry()`'s; `at` (a floor point) stands an added
    rig there. A rig already in the scene keeps its place and heading, and
    `at` is ignored for it.

    Refusals happen first and touch nothing. After the import, a connect
    refusal leaves the imported skeleton in the scene and says so -- the
    animator can fix what it names and press Retarget by hand.
    """
    plan, refusal = plan_press(target, rig)
    if refusal:
        return refusal

    place = None
    if not plan["add"]:
        place = rig_place(plan["rig"])
    elif at is not None:
        place = {"point": tuple(at), "yaw": None}
    cmds.undoInfo(openChunk=True, chunkName="UE anim import + retarget")
    try:
        # Which retarget version is asked once the clip is in and BEFORE
        # anything of the rig changes (2026-10-02): a rig in the scene is
        # measured at its bind (`maya_retargetmode.rest_world`), so its take
        # is reset only after the answer - a Cancel leaves it as it was. An
        # added rig is added first (it is what the clip is measured against)
        # and deleted again on Cancel.
        import maya_retargetmode
        notes = []
        if plan["add"]:
            rig, mod, notes, failure = ready_rig(plan)
            if failure:
                return "  |  ".join(notes + [failure])
        else:
            rig, mod = plan["rig"], plan["mod"]
        namespace, info, source = import_source(fbx_path, name, clip_fps,
                                                set_timeline)
        if source is None:
            return "  |  ".join(notes + [NO_JOINT.format(name, namespace)])
        try:
            decision = decide_bones(rig, mod, source)
        except maya_retargetmode.Cancelled:
            cmds.namespace(removeNamespace=namespace, deleteNamespaceContent=True)
            if plan["add"]:
                discard_added(rig)
            return CANCELLED
        if not plan["add"]:
            rig, mod, notes, failure = ready_rig(plan)
            if failure:
                cmds.namespace(removeNamespace=namespace, deleteNamespaceContent=True)
                return "  |  ".join(notes + [failure])
        if decision.reason:
            notes.append(decision.reason)
        line, failure = retarget_imported(rig, mod, namespace, info, source,
                                          name, place, bones=decision.mode)
    finally:
        cmds.undoInfo(closeChunk=True)
    if failure:
        return "  |  ".join(notes + [failure])
    return "  |  ".join(notes + [line]) if notes else line
