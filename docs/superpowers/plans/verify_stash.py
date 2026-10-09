"""verify_stash - the Stash section against real Maya, standalone.

Run with mayapy, never in the animator's Maya:

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' verify_stash.py

It points MAYA_APP_DIR at a scratch folder first, so the stash folder and
every preference it writes live there, and nothing of the animator's is
touched. The list's selection is a plain function here (a standalone run has
no window to pick a row in), everything else is the real code path: the
copies, the opens, the imports, the save-to, the delete and the open-scene
refusal.

Gates (each prints PASS or FAIL; the exit code is the number of failures):
  1  a stash of the open scene writes a copy under its stem and time
  2  the open scene keeps its name and its modified flag (unsaved edits too)
  3  the copy holds the unsaved edit (exportAll writes what is in the scene)
  4  a second stash of the same scene makes " (2)" and overwrites nothing
  5  Open of a stashed scene: it is the scene, unmodified, and its cube is in
  6  Import of a stashed scene brings its nodes in, script nodes out
  7  a stashed FBX Imports as its own skeleton in a namespace
  8  Save to... copies the file out
  9  Delete removes the file from disk (the batch run has no confirm)
 10  Delete refuses the scene open in this Maya and keeps its file
"""

import os
import shutil
import sys
import tempfile
import time

SCRATCH = tempfile.mkdtemp(prefix="stash_verify_")
os.environ["MAYA_APP_DIR"] = SCRATCH

PLUGIN = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
    "SkeldarAnim"))
sys.path.insert(0, PLUGIN)

import maya.standalone  # noqa: E402
maya.standalone.initialize(name="python")

import maya.cmds as cmds  # noqa: E402

import maya_stash as stash  # noqa: E402
import maya_stashstore as store  # noqa: E402
from maya_scenesetup import colour  # noqa: E402

FAILS = []
WORK = os.path.join(SCRATCH, "work")
os.makedirs(WORK)


def gate(number, label, ok, detail=""):
    print("{0:>2} {1} {2}{3}".format(number, "PASS" if ok else "FAIL", label,
                                     (" - " + detail) if detail else ""))
    if not ok:
        FAILS.append(number)


def pick(name):
    """The list's selection, for a run with no window."""
    stash.selected_names = lambda: [name] if isinstance(name, str) else name


def folder():
    return os.path.join(SCRATCH, store.FOLDER)


def stashed():
    return sorted(os.listdir(folder())) if os.path.isdir(folder()) else []


# -- a scene with a cube, saved, then an unsaved edit on top
cmds.file(new=True, force=True)
cmds.polyCube(name="savedcube")
saved_path = os.path.join(WORK, "shot.ma").replace("\\", "/")
cmds.file(rename=saved_path)
cmds.file(save=True, type="mayaAscii")
cmds.polyCube(name="unsavededit")
scene_before = cmds.file(query=True, sceneName=True)
modified_before = cmds.file(query=True, modified=True)

# -- 1, 2, 3: stash the scene
message = stash.stash_scene()
names = stashed()
gate(1, "a stash of the open scene writes a copy",
     len(names) == 1 and names[0].startswith("shot_") and
     names[0].endswith(".ma"), ", ".join(names) + " | " + message[:60])
scene_after = cmds.file(query=True, sceneName=True)
modified_after = cmds.file(query=True, modified=True)
gate(2, "the open scene keeps its name and its modified flag",
     scene_after == scene_before and modified_after == modified_before
     and bool(modified_after),
     "%s modified=%s" % (scene_after, modified_after))
copy_text = open(os.path.join(folder(), names[0]), encoding="utf-8",
                 errors="replace").read()
gate(3, "the copy holds the unsaved edit too",
     "unsavededit" in copy_text and "savedcube" in copy_text)

# -- 4: a second press
stash.stash_scene()
names = stashed()
gate(4, "a second stash makes ' (2)' and overwrites nothing",
     len(names) == 2 and any(n.endswith(" (2).ma") for n in names), str(names))
first = [n for n in names if not n.endswith(" (2).ma")][0]
pick(first)

# -- 5: Open
cmds.file(new=True, force=True)
message = stash.open_selected()
opened = cmds.file(query=True, sceneName=True) or ""
gate(5, "Open of a stashed scene: it is the scene, unmodified",
     os.path.basename(opened) == first and not cmds.file(query=True,
                                                         modified=True)
     and bool(cmds.ls("savedcube")), message[:80])

# -- 6: Import into a fresh scene
cmds.file(new=True, force=True)
message = stash.import_selected()
gate(6, "Import of a stashed scene brings its nodes in",
     bool(cmds.ls("savedcube")) and "Imported" in message, message[:80])

# -- 7: an FBX, stashed then imported as its own skeleton
spear = os.path.join(PLUGIN, "assets", "Spear_01.fbx")
stash.stash_file(spear)
pick("Spear_01.fbx")
cmds.file(new=True, force=True)
message = stash.import_selected()
gate(7, "a stashed FBX imports as its own skeleton in a namespace",
     "Imported Spear_01.fbx as" in message, message[:100])

# -- 8: Save to... (the picker answered by a path)
dest = os.path.join(WORK, "out_copy.ma")
pick(first)
cmds.fileDialog2 = lambda **kwargs: [dest]
message = stash.save_selected()
same = False
if os.path.isfile(dest):
    with open(dest, "rb") as copied, open(os.path.join(folder(), first),
                                          "rb") as original:
        same = copied.read() == original.read()
gate(8, "Save to... copies the stashed file out", same, message[:80])

# -- 9: Delete a stashed file (batch: no confirm)
second = [n for n in stashed() if n.endswith(" (2).ma")][0]
stash.delete_names([second])
gate(9, "Delete removes the file from disk", second not in stashed(),
     ", ".join(stashed()))

# -- 10: Delete refuses the scene open in this Maya
cmds.file(new=True, force=True)
open_one = os.path.join(folder(), first).replace("\\", "/")
cmds.file(open_one, open=True, force=True, executeScriptNodes=False,
          ignoreVersion=True, prompt=False)
message = stash.delete_names([first])
gate(10, "Delete refuses the open scene and keeps its file",
     first in stashed() and "scene open in this Maya" in message,
     message[:100])

shutil.rmtree(SCRATCH, ignore_errors=True)
print("failures: %d" % len(FAILS))
sys.exit(len(FAILS))
