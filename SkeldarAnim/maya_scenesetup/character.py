"""Put the working character into the scene: skeleton, geometry, camera bone.

The animator opened the Manny rig scene by hand at the start of every
session; the Add Character button imports the same content into the CURRENT
scene instead. Import, never open -- whatever is already in the scene
survives -- and no namespace, deliberately: the UE bridge merges clips onto
this skeleton by plain bone names, and a namespace is exactly what stops the
names matching.

Two defences, both earned. The button REFUSES when the scene already holds a
skeleton: importing over an existing `root` makes Maya rename the incoming
one (`root1`, `pelvis1`, ...), a second character the picker and the UE
bridge then refuse to guess between -- nothing happening is the safe
direction, and the status line says why. And imported script nodes named
like the studio's "vaccine" malware are deleted on arrival: the shipped copy
in assets/ is sanitized, but the legacy fallback IS the user's original
infected file, and some day a re-export lands in assets/ unsanitized. The
sweep only ever looks at nodes this import created.

Import never executes script nodes, so the sweep runs before the malware
ever could; it fires on the next scene OPEN, which is exactly the copy this
button is retiring.
"""

import os

import maya.cmds as cmds

from maya_scenesetup import catalog

LABEL = "Manny"

NO_FILE = "file not found: {0}"
ALREADY = "{0} is already in the scene - the character was not imported"

# Leaf-name markers of the vaccine script nodes (vaccine_gene, breed_gene,
# and whatever numeric suffix Maya hangs on a clash).
_MALWARE = ("vaccine", "breed")


# ------------------------------------------------------------------ policy

def scene_type(path):
    """Maya's file type for a scene path. Explicit, never sniffed."""
    return "mayaBinary" if path.lower().endswith(".mb") else "mayaAscii"


def refusal(existing_roots):
    """Why the import must not run, or "".

    Any skeleton already in the scene -- the character itself, or a
    namespaced reference skeleton from the UE bridge -- refuses the press.
    """
    roots = [root for root in existing_roots or [] if root]
    if not roots:
        return ""
    return ALREADY.format(roots[0].split("|")[-1])


def malware_nodes(names):
    """The names among `names` that read as vaccine malware."""
    found = []
    for name in names or []:
        leaf = name.split("|")[-1].split(":")[-1].lower()
        if any(marker in leaf for marker in _MALWARE):
            found.append(name)
    return found


def added_message(joints, meshes, removed):
    message = "{0} added - {1} joints, {2} meshes".format(
        LABEL, joints, meshes)
    if removed:
        message += (" - removed malware script node(s): "
                    + ", ".join(removed))
    return message


# ------------------------------------------------------------------ action

def add_character():
    """Import the character scene, sweep it, and say what arrived."""
    from maya_overrig import builder  # drags maya.mel in; keep import lazy

    path = catalog.character_path()
    if not os.path.isfile(path):
        return NO_FILE.format(path)

    problem = refusal(builder.character_roots())
    if problem:
        return problem

    new = cmds.file(path, i=True, type=scene_type(path),
                    returnNewNodes=True, ignoreVersion=True) or []

    suspect = malware_nodes(cmds.ls(new, type="script") or [])
    removed = [node for node in suspect if cmds.objExists(node)]
    if removed:
        cmds.delete(removed)

    joints = len(cmds.ls(new, type="joint") or [])
    meshes = len(cmds.ls(new, type="mesh") or [])
    return added_message(joints, meshes, removed)
