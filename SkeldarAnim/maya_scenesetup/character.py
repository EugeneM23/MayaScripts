"""Put the working character into the scene: skeleton, geometry, camera bone.

The animator opened the Manny rig scene by hand at the start of every
session; the Add Character button imports the same content into the CURRENT
scene instead. Import, never open -- whatever is already in the scene
survives -- and no namespace, deliberately: the UE bridge merges clips onto
this skeleton by plain bone names, and a namespace is exactly what stops the
names matching.

**Press it as many times as you like** (2026-09-01, the user's ask: "я
должен иметь возможность добавить в сцену сколько угодно персонажей").
It used to refuse whenever the scene held any skeleton, and the stated
reason was that the picker and the UE bridge "refuse to guess between"
two characters. That premise is gone: every rig operation is scoped to the
character the picker is CONNECTED to, and the bridge takes the selection
first. So the refusal is gone with it, and two things take its place --
the message names the rename, and the new character is connected
immediately, so "add it" and "work on it" are one press.

Only the TOP node collides. Maya renames `root` to `root1`, but `pelvis`
is a child of a different parent and keeps its plain name, which is what
makes a second character usable at all: the UE bridge merges clips by
plain bone names.

The defence that stays: imported script nodes named like the studio's
"vaccine" malware are deleted on arrival. The shipped copy in assets/ is
sanitized, but the legacy fallback IS the user's original infected file,
and some day a re-export lands in assets/ unsanitized. The sweep only
ever looks at nodes this import created.

Import never executes script nodes, so the sweep runs before the malware
ever could; it fires on the next scene OPEN, which is exactly the copy this
button is retiring.
"""

import os
import re

import maya.cmds as cmds

from maya_scenesetup import catalog
from maya_scenesetup import colour

LABEL = "Manny"

NO_FILE = "file not found: {0}"

# Kept as the wording for the RENAME note, which is what the animator now
# needs to know: the top node is the only one that collides.
RENAMED = "imported as {0} ({1} already in the scene)"

# Leaf-name markers of the vaccine script nodes (vaccine_gene, breed_gene,
# and whatever numeric suffix Maya hangs on a clash).
_MALWARE = ("vaccine", "breed")

# A rig arrives in its OWN NAMESPACE (2026-09-08, «я должен иметь возможность
# добавить в сцену много ригов»): both retarget modules address a rig by
# name -- `Main`, `ControlSet`, `FKWrist_R` -- and a namespace is what keeps
# `Manny_Rig1:Main` one node when `Main` would be two. Measured 2026-09-08:
# every one of the file's 2713 nodes lands under the namespace, none stray.
# The one-rig-per-scene refusal of 2026-09-07 is gone with its premise.
RIG_NAMESPACE_BASE = "Manny_Rig"

_ILLEGAL_NAMESPACE = re.compile(r"[^A-Za-z0-9_]")


def free_namespace(base, taken):
    """A Maya-legal namespace from `base`, unique against `taken`. Pure.

    The clip importer's own rule (`records.namespace_for`), spelled here so
    Scene Setup does not import the bridge for one function.
    """
    name = _ILLEGAL_NAMESPACE.sub("_", base or "") or "rig"
    if name[0].isdigit():
        name = "_" + name
    if name not in taken:
        return name
    index = 1
    while "{0}{1}".format(name, index) in taken:
        index += 1
    return "{0}{1}".format(name, index)


def existing_namespaces():
    """Every namespace in the scene, nested ones as `a:b`."""
    return cmds.namespaceInfo(":", listOnlyNamespaces=True, recurse=True) or []


# ------------------------------------------------------------------ policy

def scene_type(path):
    """Maya's file type for a character asset. Explicit, never sniffed.

    The `FBX` row arrived with the UE4 mannequin (2026-09-01): the editor
    exports FBX, so that is what the plugin ships. It decides which import
    path runs, and the FBX one has to force the plugin's global import MODE
    (trap 33) -- see `fbximport`.
    """
    lowered = (path or "").lower()
    if lowered.endswith(".fbx"):
        return "FBX"
    return "mayaBinary" if lowered.endswith(".mb") else "mayaAscii"


def is_fbx(path):
    return scene_type(path) == "FBX"


def new_root(before_roots, after_roots):
    """The root this import added, or None. Pure.

    A path diff, not a name diff: the incoming top node is the one Maya
    renamed, so its name is not knowable in advance -- and everything
    below it kept its plain name, so a name diff would report nothing.
    """
    before = set(before_roots or [])
    fresh = [root for root in (after_roots or [])
             if root and root not in before]
    if not fresh:
        return None
    # Shallowest first, then by path: deterministic, and a character root
    # is always shallower than anything the import brought under it.
    return min(fresh, key=lambda path: (path.count("|"), path))


def rename_note(root, existing_roots):
    """"imported as root1 (root already in the scene)", or "".

    Said out loud because the animator will see `root1` in the outliner and
    wonder what went wrong. Nothing did: only the TOP node collides, every
    bone under it keeps its plain name, and that is what lets the UE bridge
    merge clips onto it by name.
    """
    roots = [r for r in existing_roots or [] if r]
    if not roots or not root:
        return ""
    leaf = root.split("|")[-1]
    others = [r.split("|")[-1] for r in roots if r != root]
    if not others or leaf in others:
        return ""
    # What collided is a PLAIN top node -- `root` when there is one. A rig's
    # namespaced joints are never it, and an AdvancedSkeleton rig has dozens
    # of top joints (2026-09-24: the note named `Creep_Rig:FKXAnkle_L`).
    plain = [o for o in others if ":" not in o]
    if not plain:
        # Beside rigs alone nothing collided (2026-09-30): their top joints
        # are namespaced, so a plain `root` keeps its name.
        return ""
    named = [o for o in plain if o == "root"]
    return RENAMED.format(leaf, (named or plain)[0])


def malware_nodes(names):
    """The names among `names` that read as vaccine malware."""
    found = []
    for name in names or []:
        leaf = name.split("|")[-1].split(":")[-1].lower()
        if any(marker in leaf for marker in _MALWARE):
            found.append(name)
    return found


def added_message(joints, meshes, removed, note="", connected=False,
                  label=None, colour_name="", namespace="", selected=False,
                  placed=None):
    """What the press says. `label` names WHICH skeleton arrived, now that
    the dropdown offers more than one, `colour_name` which colour it is
    wearing -- the animator picked the press by colour from then on -- and
    `namespace` which namespace a RIG landed in, since 2026-09-08 the name
    every message about it uses. `placed` is the floor point a dropped
    portrait stood it on (2026-09-30)."""
    message = "{0} added{1} - {2} joints, {3} meshes".format(
        label or LABEL, (" as " + namespace) if namespace else "", joints,
        meshes)
    if colour_name:
        message += " - " + colour_name
    if placed is not None:
        message += " - at ({0}, {1})".format(int(round(placed[0])),
                                             int(round(placed[2])))
    if note:
        message += " - " + note
    if connected:
        message += " - connected"
    if selected:
        message += " - selected"
    if removed:
        message += (" - removed malware script node(s): "
                    + ", ".join(removed))
    return message


def appearance(textured, rgb, switched, missing):
    """Pure: what an Add says the character arrived wearing -- its colour's
    name, or «textured» for a row that arrives in its own images (2026-09-28,
    the Orc D), with the viewport's Textures named when this press turned
    them on and any image the installed copy lacks named by its file.
    Weapons > Add's wording for Spear 03 (`window.appearance`)."""
    if not textured:
        return colour.colour_name(rgb)
    text = "textured (viewport textures on)" if switched else "textured"
    if missing:
        text += " - missing image(s): " + ", ".join(
            os.path.basename(path) for path in missing)
    return text


# ------------------------------------------------------------------ action

def rig_present():
    """True when at least one AdvancedSkeleton rig stands in the scene."""
    import maya_rigs
    return bool(maya_rigs.rigs())


def select_rig(namespace):
    """Select the new rig's `Main`, so the rig just added is the one the next
    press acts on -- "add it" and "work on it" stay one press without the
    picker's Connect. True when it was selected."""
    import maya_rigs
    main = cmds.ls(maya_rigs.node(namespace, maya_rigs.MAIN), long=True) or []
    if len(main) != 1:
        return False
    cmds.select(main[0], replace=True)
    return True


def connect(root):
    """Hand the new character to the picker. True when one took it.

    Guarded and lazy: `picker_window` imports PySide6, and Scene Setup is
    plain `cmds` and has to keep working in a session where the picker
    cannot even be imported (Maya 2024 and older ship PySide2). And off
    entirely while `skeldar_features.PICKER` is off (2026-09-07): the
    picker is not on the shelf, so opening it from here would surprise.
    """
    import skeldar_features
    if not root or not skeldar_features.PICKER:
        return False
    try:
        from maya_overrig import picker_window
    except Exception:
        return False
    return picker_window.connect_root(root)


def wrapper_nodes(nodes, is_joint, has_shape, depth):
    """The FBX axis-conversion wrappers among `nodes`. Pure.

    One transform at world level, holding no shape of its own and not a
    joint: that is what the FBX importer wraps a file's contents in. The
    scene arrives as three lookups so the decision is testable without
    Maya.
    """
    found = []
    for node in nodes or []:
        if depth(node) != 1 or is_joint(node) or has_shape(node):
            continue
        if node not in found:
            found.append(node)
    return found


# A reference figure should read as a figure. The UE4 mannequin's FBX
# brings `M_UE4Man_Body` and `M_UE4Man_ChestLogo` with color (0, 0, 0) --
# UE does not put the textures in the file, so the character arrives pure
# black («сильно темный»). Maya's own default lambert grey is the obvious
# value to land on, and it is one constant so a second asset with the same
# problem needs no second decision.
GREY = (0.5, 0.5, 0.5)

# What counts as "black enough to be a mistake". A material an artist
# genuinely made black sits at 0.0 too, which is why the texture test below
# matters more than this threshold.
_BLACK = 0.02

TRANSFORM_CHANNELS = ("translate", "rotate", "scale", "shear")


def needs_grey(colour, textured):
    """Whether a material arrived unusably dark. Pure.

    Two conditions, and the second is the important one: a TEXTURED colour
    is never overridden, whatever it reads as, because the texture is what
    decides the look and the plug's value is meaningless then. Only a flat,
    near-black, untextured colour is the "the textures did not come along"
    case this exists for.
    """
    if textured or colour is None:
        return False
    return all(abs(channel) <= _BLACK for channel in colour)


def grey_black_materials(nodes):
    """Give this import's pure-black materials a grey colour.

    Scoped to the nodes the import created, so nothing already in the
    animator's scene is touched -- and to the FBX path, because Manny's
    `.ma` brings its own shading and a black material there would be
    somebody's choice.
    """
    changed = []
    for material in (cmds.ls(nodes, materials=True) or []):
        plug = material + ".color"
        if not cmds.objExists(plug):
            continue
        textured = bool(cmds.listConnections(plug, source=True,
                                             destination=False))
        try:
            colour = cmds.getAttr(plug)[0]
        except Exception:
            continue
        if not needs_grey(colour, textured):
            continue
        try:
            cmds.setAttr(plug, GREY[0], GREY[1], GREY[2], type="double3")
        except RuntimeError:
            continue  # locked or referenced; the look is not worth a raise
        changed.append(material)
    return changed


def transform_plugs(node):
    """The twelve t/r/s/shear plugs of a node, in a fixed order. Pure."""
    return ["{0}.{1}{2}".format(node, channel, axis)
            for channel in TRANSFORM_CHANNELS for axis in "XYZ"]


def _locked_plugs(node):
    """Which of those plugs are locked right now.

    The FBX importer LOCKS a skinned mesh's transform -- t, r and s, all
    nine (measured) -- to stop anyone double-transforming the deformation.
    A locked plug makes `cmds.xform` a silent no-op, which is exactly how
    the first version of the flatten left the skeleton right and the
    geometry lying on its side: the joints took their world matrix back
    and the mesh could not.
    """
    found = []
    for plug in transform_plugs(node):
        if cmds.objExists(plug) and cmds.getAttr(plug, lock=True):
            found.append(plug)
    return found


def _set_locked(plugs, state):
    for plug in plugs:
        try:
            cmds.setAttr(plug, lock=state)
        except Exception:
            pass  # referenced or otherwise unwritable; nothing to do


def flatten_wrappers(nodes):
    """Unparent the FBX importer's wrapper and delete it. Returns its name(s).

    The importer wraps a file's contents in one transform carrying the
    Z-up -> Y-up conversion (measured: `rotateX -90`). Manny's `.ma` has no
    such node, so Add Character used to leave two different shapes in the
    outliner -- «ue5 скелет вставляется кости отдельно меш отдельно, UE4
    вставляется в одной группе с мешем, нужно сделать однородно».

    And the wrapper is worse than untidy. A UE clip carries that SAME -90
    on `root`'s jointOrient, so merging one onto a WRAPPED skeleton applies
    the rotation twice and the character lies down: measured in a
    standalone Maya, head at Y=2.96 wrapped against Y=147.84 flat, from the
    same clip. Flattening is what makes an animation import land upright.

    World matrices are recorded and put back BY HAND. A plain
    `cmds.parent(..., world=True)` moved the skeleton 90 degrees (measured:
    worst world-matrix element 1.0) -- Maya distributes a joint's new
    parentage into `jointOrient`, and the arithmetic it picks is not the
    one that preserves the pose. Re-asserting the world matrix afterwards
    is; the rest pose comes out identical to the wrapped import.
    """
    wrappers = wrapper_nodes(
        cmds.ls(nodes, long=True, type="transform") or [],
        is_joint=lambda n: cmds.objectType(n) == "joint",
        has_shape=lambda n: bool(cmds.listRelatives(n, shapes=True)),
        depth=lambda n: n.count("|"))

    removed = []
    for wrapper in wrappers:
        if not cmds.objExists(wrapper):
            continue
        children = cmds.listRelatives(wrapper, children=True,
                                      fullPath=True) or []
        if children:
            # By UUID: every path below changes as soon as one is moved.
            worlds = {}
            for child in children:
                uuid = (cmds.ls(child, uuid=True) or [None])[0]
                if uuid:
                    worlds[uuid] = cmds.xform(child, query=True,
                                              worldSpace=True, matrix=True)
            cmds.parent(children, world=True)
            for uuid, matrix in worlds.items():
                paths = cmds.ls(uuid, long=True) or []
                if not paths:
                    continue
                # Unlocked around the write and locked back exactly as
                # found: the importer's protection is right, it just has
                # to let this one write through. Without it the mesh
                # silently keeps identity and lies on its side while the
                # skeleton stands up (measured: bbox Y and Z swapped).
                locks = _locked_plugs(paths[0])
                _set_locked(locks, False)
                try:
                    cmds.xform(paths[0], worldSpace=True, matrix=matrix)
                finally:
                    _set_locked(locks, True)
        if cmds.objExists(wrapper):
            cmds.delete(wrapper)
        removed.append(wrapper.split("|")[-1])
    return removed


def import_asset(path, namespace=None):
    """Import a character asset and return every node that arrived.

    `namespace` is where a RIG lands (2026-09-08); a bare skeleton passes
    None and keeps its plain bone names, which the merge-by-name import
    still needs.

    Two formats since 2026-09-01. `.ma` is Manny; `.fbx` is the UE4
    mannequin, and it MUST go through `fbximport`, which forces the FBX
    plugin's global import MODE -- `maya_uebridge` leaves it on `exmerge`,
    where the importer matches names against the scene and creates nothing
    at all, so without that guard Add Character would silently stop working
    after any animation import from Unreal (trap 33).

    Import, never open: whatever is already in the scene survives. And no
    namespace, deliberately -- the UE bridge merges clips onto this skeleton
    by plain bone names, which is the whole point of adding it.
    """
    if is_fbx(path):
        from maya_scenesetup import fbximport
        new = fbximport.import_nodes(path)
        # UUIDs BEFORE the flatten. Re-parenting invalidates the long path
        # of every node under the wrapper (trap 16), and the caller counts
        # these and sweeps them for malware -- against stale paths it
        # counted zero joints and swept nothing.
        uuids = cmds.ls(new, uuid=True) or []
        # FBX only: the wrapper is that importer's artifact, and Manny's
        # `.ma` brings its skeleton, meshes and camera at world level
        # already. Running this over a `.ma` would flatten the mesh GROUP
        # the animator's file legitimately has.
        flatten_wrappers(new)
        live = []
        for uuid in uuids:
            live.extend(cmds.ls(uuid, long=True) or [])
        grey_black_materials(live)
        return live
    options = {}
    if namespace:
        options["namespace"] = namespace
    return cmds.file(path, i=True, type=scene_type(path),
                     returnNewNodes=True, ignoreVersion=True, **options) or []


def rig_namespace(entry):
    """Pure: the namespace a rig row lands in -- its own key (`Manny_Rig`,
    `Creep_Rig`), uniquified by `free_namespace`. A second rig row must not
    arrive as `Manny_Rig1` (2026-09-24, the Creep)."""
    return entry.key or RIG_NAMESPACE_BASE


def placement(at):
    """The world offset a drop at floor point `at` asks for: (x, 0, z). The
    move is relative, so the feet keep the height the file gives them. Pure."""
    return (float(at[0]), 0.0, float(at[2]))


def place(entry, namespace, root, at):
    """Stand the new character at floor point `at` (2026-09-30, a portrait
    dragged into a viewport): a rig's `Main` -- the whole rig's control, root
    motion; its skeleton's root rides it by constraint -- else the skeleton's
    `root`, moved by `placement(at)` in world space. Never a Null above the
    root: the Creep skeleton's `Armature` must stay at the origin, or the
    export no longer reads Cascadeur's layout (fbxlayout.in_layout). No turn:
    a character faces +Z as its file does (the animator's pick). The node
    moved, or None."""
    if at is None:
        return None
    node = None
    if catalog.is_rig(entry):
        import maya_rigs
        found = cmds.ls(maya_rigs.node(namespace, maya_rigs.MAIN),
                        long=True) or []
        node = found[0] if len(found) == 1 else None
    else:
        node = root
    if not node:
        return None
    x, y, z = placement(at)
    cmds.move(x, y, z, node, relative=True, worldSpace=True)
    return node


def group_base(entry, namespace):
    """Pure: what a character's group and layer are named for -- a rig's namespace (`Manny_Rig1`:
    the name every message uses), a skeleton's asset file stem (`Manny_Skeleton`, `Creep_Skeleton`,
    `UE4_Mannequin`)."""
    if namespace:
        return namespace
    return os.path.splitext(os.path.basename(getattr(entry, "file", "") or ""))[0] \
        or getattr(entry, "key", "") or "Character"


def world_tops(paths):
    """Pure: the world-level DAG paths among `paths` (`|root`, `|Armature`, `|camera1`), in order,
    without repeats."""
    return [p for p in dict.fromkeys(paths or []) if p and p.count("|") == 1]


def group_failed_note(exc):
    """Pure: the Add line's word when the character could not be grouped (it stands as before)."""
    return "no character group ({0}) - its parts stand at world level".format(
        str(exc).strip().splitlines()[0] if str(exc).strip() else type(exc).__name__)


def group_character(entry, new, namespace, root):
    """The character just added, in ONE outliner group with its own display layer (2026-10-02,
    `chargroup`). A rig's group holds every world-level node of its namespace, a skeleton's every
    world-level node its import brought. Returns (group, layer) or (None, None)."""
    from maya_scenesetup import chargroup
    if namespace:
        import maya_rigs
        rig = maya_rigs.find(namespace)
        root = rig.skeleton_root if rig is not None else root
        tops = [t for t in cmds.ls(assemblies=True, long=True) or []
                if maya_rigs.namespace_of(t) == namespace
                or maya_rigs.namespace_of(t).startswith(namespace + ":")]
    else:
        tops = world_tops(cmds.ls(cmds.ls(new or [], type="transform", long=True) or [],
                                  long=True) or [])
    if not tops:
        return None, None
    return chargroup.make(group_base(entry, namespace), getattr(entry, "label", ""), root, tops)


def character_group(root_or_rig):
    """THE public question (2026-10-02): the character group of a root, any node of a character,
    or a `maya_rigs.Rig` -- a long path, or None for a character added before the groups (and for
    anything of nobody's). Park a new part of a character with `chargroup.park(node, owner)`."""
    from maya_scenesetup import chargroup
    return chargroup.group_of(root_or_rig)


def add_character(entry=None, rgb=None, at=None):
    """Import a character, colour it, sweep it, connect it, and say so.

    `entry` is a `catalog.Character`; None means the dropdown's default,
    Manny, so every existing caller keeps its behaviour. Repeatable: every
    press adds another character. The one refusal left is the file not
    being there.

    `rgb` is the colour the character arrives wearing; None means the next
    free palette colour, which is what the Characters card passes since the
    colour left it (2026-09-30) -- two characters never arrive identical, and
    the Colour section repaints the selection.
    A `textured` row ignores it and arrives in its own images.
    The meshes are taken from the import's OWN nodes, which is exact and
    needs no searching (and `import_asset` has already re-resolved them
    from their UUIDs, because the flatten invalidates every long path below
    the wrapper -- trap 16).

    `at` is a floor point (2026-09-30, a portrait dropped into a viewport):
    the character stands there (`place`).

    Nothing of the press can be undone, and on purpose. Measured live
    2026-09-30: `file -import` FLUSHES Maya's undo queue (a cube made before
    it in the same call could not be undone after it), exactly as Maya's own
    File > Import. What followed the import - the colour, the sweep, the
    move, the selection - used to be recorded, so a Ctrl+Z left the new
    character unpainted at the origin. It runs with undo recording off now
    (`_unrecorded`): the character arrives whole or not at all.
    """
    entry = entry or catalog.default_character()

    from maya_overrig import builder  # drags maya.mel in; keep import lazy

    path = catalog.character_file(entry)
    if not os.path.isfile(path):
        return NO_FILE.format(path)

    return _add(entry, path, rgb, at, builder)


class _unrecorded(object):
    """Undo recording off for the block - without the flush that
    `undoInfo(state=False)` does - and back as it was after."""

    def __enter__(self):
        self.was = bool(cmds.undoInfo(query=True, state=True))
        if self.was:
            cmds.undoInfo(stateWithoutFlush=False)
        return self

    def __exit__(self, *_exc):
        if self.was:
            cmds.undoInfo(stateWithoutFlush=True)
        return False


def _add(entry, path, rgb, at, builder):
    """The body of `add_character`: the import, then the rest unrecorded."""
    textured = getattr(entry, "textured", False)
    if rgb is None and not textured:
        rgb = colour.free_colour().rgb

    # A rig gets a namespace of its own; a bare skeleton keeps plain names.
    namespace = ""
    if catalog.is_rig(entry):
        namespace = free_namespace(rig_namespace(entry), existing_namespaces())

    before_roots = builder.character_roots()
    new = import_asset(path, namespace or None)
    with _unrecorded():
        return _after_import(entry, new, namespace, before_roots, rgb, at,
                             textured, builder)


def _after_import(entry, new, namespace, before_roots, rgb, at, textured,
                  builder):
    """Dress, sweep, place and select what the import brought (unrecorded)."""
    # A textured row (2026-09-28, the Orc D) keeps the materials it ships
    # with: its images pointed at the installed copy, the viewport's Textures
    # on. Everything else gets a fresh palette colour.
    switched, missing = [], []
    if textured:
        _count, missing = colour.relink_images(new, catalog.asset_path)
        switched = colour.show_textures()
        painted = None
    else:
        painted = colour.paint_nodes(new, rgb, entry.key)

    # Format-blind on purpose: an FBX cannot carry a script node, but the
    # sweep costs nothing and the `.ma` path genuinely needs it.
    suspect = malware_nodes(cmds.ls(new, type="script") or [])
    removed = [node for node in suspect if cmds.objExists(node)]
    if removed:
        cmds.delete(removed)

    # After the sweep, so a deleted node cannot be reported as a root.
    root = new_root(before_roots, builder.character_roots())
    note = "" if namespace else rename_note(
        root, before_roots + ([root] if root else []))
    placed = at if place(entry, namespace, root, at) else None
    # Every part in ONE outliner group with its own display layer (2026-10-02). Best effort, like
    # the record below: the character is what the press is for, and it has arrived.
    # By UUID across it: the re-parent invalidates every path below (trap 16) -- against stale
    # paths the line counted 0 joints and 0 meshes, and the record would hold nothing.
    root_uuid = (cmds.ls(root, uuid=True) or [None])[0] if root else None
    new_uuids = cmds.ls(new or [], uuid=True) or []
    try:
        group_character(entry, new, namespace, root)
    except Exception as exc:                                     # noqa: BLE001
        # `chargroup.make` is all or nothing: the character stands as before the groups, and
        # the line says so (it used to go to the Script Editor only).
        print("Add Character: no character group ({0})".format(exc))
        note = ((note + " - ") if note else "") + group_failed_note(exc)
    if root_uuid:
        root = (cmds.ls(root_uuid, long=True) or [root])[0]
    if new_uuids:
        new = [path for uuid in new_uuids for path in (cmds.ls(uuid, long=True) or [])]
    if root and not namespace:
        # What this import brought, for Characters > Delete (2026-10-01): a skeleton's asset can
        # carry nodes connected to nothing of it (Manny's: the dead half of a rig, a camera1),
        # and only this list knows them. A rig has its namespace.
        # Best effort: the character is what the press is for, and it has arrived.
        try:
            from maya_scenesetup import deletion
            deletion.record_import(root, new, entry.label)
        except Exception as exc:                                 # noqa: BLE001
            print("Add Character: no record for Delete ({0})".format(exc))
    connected = connect(root)
    selected = select_rig(namespace) if namespace else False

    joints = len(cmds.ls(new, type="joint") or [])
    meshes = len(cmds.ls(new, type="mesh") or [])
    wearing = (appearance(textured, rgb, switched, missing)
               if textured or painted else "")
    return added_message(joints, meshes, removed, note, connected,
                         label=entry.label, colour_name=wearing,
                         namespace=namespace, selected=selected,
                         placed=placed)
