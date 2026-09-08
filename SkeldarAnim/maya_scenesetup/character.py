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
    return RENAMED.format(leaf, others[0])


def malware_nodes(names):
    """The names among `names` that read as vaccine malware."""
    found = []
    for name in names or []:
        leaf = name.split("|")[-1].split(":")[-1].lower()
        if any(marker in leaf for marker in _MALWARE):
            found.append(name)
    return found


def added_message(joints, meshes, removed, note="", connected=False,
                  label=None, colour_name="", namespace="", selected=False):
    """What the press says. `label` names WHICH skeleton arrived, now that
    the dropdown offers more than one, `colour_name` which colour it is
    wearing -- the animator picked the press by colour from then on -- and
    `namespace` which namespace a RIG landed in, since 2026-09-08 the name
    every message about it uses."""
    message = "{0} added{1} - {2} joints, {3} meshes".format(
        label or LABEL, (" as " + namespace) if namespace else "", joints,
        meshes)
    if colour_name:
        message += " - " + colour_name
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


def add_character(entry=None, rgb=None):
    """Import a character, colour it, sweep it, connect it, and say so.

    `entry` is a `catalog.Character`; None means the dropdown's default,
    Manny, so every existing caller keeps its behaviour. Repeatable: every
    press adds another character. The one refusal left is the file not
    being there.

    `rgb` is the colour the character arrives wearing; None means the next
    free palette colour, which is what the button passes -- two characters
    can then never arrive identical even when nobody touches the swatch.
    The meshes are taken from the import's OWN nodes, which is exact and
    needs no searching (and `import_asset` has already re-resolved them
    from their UUIDs, because the flatten invalidates every long path below
    the wrapper -- trap 16).
    """
    entry = entry or catalog.default_character()

    from maya_overrig import builder  # drags maya.mel in; keep import lazy

    path = catalog.character_file(entry)
    if not os.path.isfile(path):
        return NO_FILE.format(path)

    if rgb is None:
        rgb = colour.free_colour().rgb

    # A rig gets a namespace of its own; a bare skeleton keeps plain names.
    namespace = ""
    if catalog.is_rig(entry):
        namespace = free_namespace(RIG_NAMESPACE_BASE, existing_namespaces())

    before_roots = builder.character_roots()
    new = import_asset(path, namespace or None)

    # Its own undo chunk: creating the material and assigning it are two
    # commands, and half of that undone is a mesh with no shader.
    cmds.undoInfo(openChunk=True)
    try:
        painted = colour.paint_nodes(new, rgb, entry.key)
    finally:
        cmds.undoInfo(closeChunk=True)

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
    connected = connect(root)
    selected = select_rig(namespace) if namespace else False

    joints = len(cmds.ls(new, type="joint") or [])
    meshes = len(cmds.ls(new, type="mesh") or [])
    return added_message(joints, meshes, removed, note, connected,
                         label=entry.label,
                         colour_name=colour.colour_name(rgb) if painted
                         else "", namespace=namespace, selected=selected)
