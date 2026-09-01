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

import maya.cmds as cmds

from maya_scenesetup import catalog

LABEL = "Manny"

NO_FILE = "file not found: {0}"

# Kept as the wording for the RENAME note, which is what the animator now
# needs to know: the top node is the only one that collides.
RENAMED = "imported as {0} ({1} already in the scene)"

# Leaf-name markers of the vaccine script nodes (vaccine_gene, breed_gene,
# and whatever numeric suffix Maya hangs on a clash).
_MALWARE = ("vaccine", "breed")


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
                  label=None):
    """What the press says. `label` names WHICH skeleton arrived, now that
    the dropdown offers more than one."""
    message = "{0} added - {1} joints, {2} meshes".format(
        label or LABEL, joints, meshes)
    if note:
        message += " - " + note
    if connected:
        message += " - connected"
    if removed:
        message += (" - removed malware script node(s): "
                    + ", ".join(removed))
    return message


# ------------------------------------------------------------------ action

def connect(root):
    """Hand the new character to the picker. True when one took it.

    Guarded and lazy: `picker_window` imports PySide6, and Scene Setup is
    plain `cmds` and has to keep working in a session where the picker
    cannot even be imported (Maya 2024 and older ship PySide2).
    """
    if not root:
        return False
    try:
        from maya_overrig import picker_window
    except Exception:
        return False
    return picker_window.connect_root(root)


def import_asset(path):
    """Import a character asset and return every node that arrived.

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
        return fbximport.import_nodes(path)
    return cmds.file(path, i=True, type=scene_type(path),
                     returnNewNodes=True, ignoreVersion=True) or []


def add_character(entry=None):
    """Import a character, sweep it, connect it, and say so.

    `entry` is a `catalog.Character`; None means the dropdown's default,
    Manny, so every existing caller keeps its behaviour. Repeatable: every
    press adds another character. The one refusal left is the file not
    being there.
    """
    from maya_overrig import builder  # drags maya.mel in; keep import lazy

    entry = entry or catalog.default_character()
    path = catalog.character_file(entry)
    if not os.path.isfile(path):
        return NO_FILE.format(path)

    before_roots = builder.character_roots()
    new = import_asset(path)

    # Format-blind on purpose: an FBX cannot carry a script node, but the
    # sweep costs nothing and the `.ma` path genuinely needs it.
    suspect = malware_nodes(cmds.ls(new, type="script") or [])
    removed = [node for node in suspect if cmds.objExists(node)]
    if removed:
        cmds.delete(removed)

    # After the sweep, so a deleted node cannot be reported as a root.
    root = new_root(before_roots, builder.character_roots())
    note = rename_note(root, before_roots + ([root] if root else []))
    connected = connect(root)

    joints = len(cmds.ls(new, type="joint") or [])
    meshes = len(cmds.ls(new, type="mesh") or [])
    return added_message(joints, meshes, removed, note, connected,
                         label=entry.label)
