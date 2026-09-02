"""Live check: the second character's ROOT gets the clip too.

The bug (2026-09-02, the animator): «анимация root кости переносится только
на первый скелет тоесть на тот у которого нету префикса на последующие
скелеты мы ее не переносим».

Maya will not let two nodes at world level share a short name, so a second
character has exactly ONE joint renamed - its root. `FBXImport -v exmerge`
matches by name, so the clip's `root` reached nothing and the character
played the clip on the spot while the first one walked. Measured before
this change: 67 of 68 bones.

WHAT THIS RUNS AGAINST. Two throwaway skeletons of its own, built at world
level - which is the only place the collision happens, so they cannot live
inside a group. Their bones are named `rpv_*` on purpose: nothing of the
animator's can collide with them, and the only name they DO share with the
scene is the root, which is the whole subject. Everything created is
registered by UUID as it is created and deleted from that registry (trap
47: a `finally` that deletes a group cannot clean up a failure that
happened before the group existed).

It calls the REAL `import_clip`, so `other_skeletons_held` renames the
animator's own characters aside for the length of each merge and restores
them in its `finally` - exactly what pressing Import does in any
multi-character scene. The gates below assert the scene came back.

House rules: no `cmds.undo` (the whole script is one command), no
SystemExit (it escapes into the command-port handler and has killed the
bridge for a session), autoKey off throughout, every value read before it
is written back, every teardown step guarded on its own.
"""

import os
import contextlib
import sys
import traceback

REPO = r"C:/!!!Work/MayaScripts/SkeldarAnim"
if REPO not in sys.path:
    sys.path.insert(0, REPO)

# The session imports the INSTALLED SkeldarAnim copy, and a stale package
# root keeps its submodules bound as attributes, so `from pkg import mod`
# hands back yesterday's object.
for _name in [m for m in list(sys.modules)
              if m.split(".")[0] in ("maya_overrig", "maya_uebridge",
                                     "maya_scenesetup")]:
    del sys.modules[_name]

import maya.cmds as cmds

from maya_uebridge import animexport, animimport

# Only the ROOT is a name the scene may already own - that is the subject.
# Everything else is `rpv_` so no merge of ours can reach the animator's
# character even if a hold were to fail.
CHAIN = (("root", (0.0, 0.0, 0.0)),
         ("rpv_pelvis", (0.0, 95.0, 0.0)),
         ("rpv_spine", (0.0, 20.0, 0.0)),
         ("rpv_head", (0.0, 25.0, 0.0)))

TRAVEL = 100.0                 # cm the root walks over the clip
LAST = 10.0                    # last frame of the clip
NAMESPACE = "rpvCheck"

failures = []
notes = []
gates = []


def check(label, condition, detail=""):
    gates.append(label)
    print("%-64s %s %s" % (label, "OK" if condition else "FAIL", detail))
    if not condition:
        failures.append(label)


def leaf(path):
    return (path or "").split("|")[-1]


def uuid_of(path):
    return (cmds.ls(path, uuid=True) or [None])[0]


def path_of(uuid):
    return (cmds.ls(uuid, long=True) or [None])[0]


def wmatrix(node, frame):
    cmds.currentTime(frame, edit=True)
    return cmds.xform(node, query=True, worldSpace=True, matrix=True)


def travel(node, first=0.0, last=LAST):
    """How far the node's world matrix moves between two frames."""
    a = wmatrix(node, first)
    b = wmatrix(node, last)
    return max(abs(x - y) for x, y in zip(a, b))


def build_skeleton(registry):
    """A four-joint chain at WORLD level, so Maya decorates the second
    one's root exactly as it decorates a second character's."""
    parent = None
    made = []
    for name, offset in CHAIN:
        if parent is None:
            cmds.select(clear=True)
        else:
            cmds.select(parent, replace=True)
        cmds.joint(name=name, position=offset, relative=True)
        # From the SELECTION, never from what `joint` returned: the second
        # skeleton repeats every bone name, so a short name is ambiguous.
        path = (cmds.ls(selection=True, long=True) or [None])[0]
        registry.append(uuid_of(path))
        made.append(path)
        parent = path
    cmds.select(clear=True)
    return made


def animate(chain):
    """A clip with real root motion, on EVERY bone.

    Every bone, so "nothing is left unanimated" is a statement the clip can
    actually support - a bone the clip never carried is reported stale for
    a good reason, and a gate that confused the two would be measuring the
    test rather than the tool. Keyed off the values the joints hold, never
    off a literal (trap 30).
    """
    root = chain[0]
    base = cmds.getAttr(root + ".translateX")
    cmds.setKeyframe(root, attribute="translateX", time=0.0, value=base)
    cmds.setKeyframe(root, attribute="translateX", time=LAST,
                     value=base + TRAVEL)
    for path in chain[1:]:
        turn = cmds.getAttr(path + ".rotateZ")
        cmds.setKeyframe(path, attribute="rotateZ", time=0.0, value=turn)
        cmds.setKeyframe(path, attribute="rotateZ", time=LAST,
                         value=turn + 30.0)


@contextlib.contextmanager
def lever_disabled():
    """The control: the same merge with the root rename suppressed.

    A gate that cannot fail proves nothing, and this is the one place the
    change lives - so the run measures both sides of it.
    """
    @contextlib.contextmanager
    def nothing(_target, _joints):
        yield ""
    real = animimport.target_root_plain
    animimport.target_root_plain = nothing
    try:
        yield
    finally:
        animimport.target_root_plain = real


def run():
    registry = []
    auto_key = cmds.autoKeyframe(query=True, state=True)
    frame = cmds.currentTime(query=True)
    selection = cmds.ls(selection=True, long=True) or []
    playback = (cmds.playbackOptions(query=True, animationStartTime=True),
                cmds.playbackOptions(query=True, animationEndTime=True),
                cmds.playbackOptions(query=True, minTime=True),
                cmds.playbackOptions(query=True, maxTime=True))
    scene_names_before = sorted(
        leaf(p) for p in (cmds.ls(type="joint", long=True) or []))

    folder = os.path.join(os.environ.get("TEMP", "."), "maya_uebridge_verify")
    fbx = os.path.join(folder, "rpv_root_name.fbx")

    cmds.autoKeyframe(state=False)
    try:
        cmds.playbackOptions(animationStartTime=0, animationEndTime=LAST,
                             minTime=0, maxTime=LAST)

        # ----------------------------------------------------- the setup
        chain_a = build_skeleton(registry)
        chain_b = build_skeleton(registry)
        root_a, root_b = chain_a[0], chain_b[0]
        uuid_a, uuid_b = uuid_of(root_a), uuid_of(root_b)
        print("A: %s     B: %s" % (root_a, root_b))

        check("Maya decorated the second root, as it does a second character",
              leaf(root_b) != "root", leaf(root_b))
        check("...and only the root: every other bone kept its plain name",
              all(leaf(p) == name for p, (name, _) in
                  zip(chain_b[1:], CHAIN[1:])),
              ", ".join(leaf(p) for p in chain_b[1:]))
        check("the rule reads that name as a decoration of `root`",
              animimport.plain_root_name(
                  leaf(root_b), [leaf(p) for p in chain_b[1:]]) == "root",
              leaf(root_b))

        animate(chain_b)
        reference = travel(root_b, 0.0, LAST)
        check("B's root really carries root motion to measure",
              abs(reference - TRAVEL) < 1e-4, "%.7f" % reference)

        # --------------------------------------------- the export direction
        written = animexport.export_hierarchy(fbx, root=root_b,
                                              start=0.0, end=LAST)
        check("the export wrote a file", os.path.isfile(fbx)
              and os.path.getsize(fbx) > 0, fbx)
        check("the export reports the root it actually wrote",
              written.get("root") == "root", str(written.get("root")))
        check("...and says so in the status line",
              "root motion" in (written.get("warning") or ""),
              (written.get("warning") or "")[:70])
        check("B's own name is back after the export",
              leaf(path_of(uuid_b)) == leaf(root_b), leaf(path_of(uuid_b)))

        # Read the file back as its own skeleton: the names in it ARE the
        # names of the nodes it creates, which is the only honest proof of
        # what the exporter wrote.
        before = set(cmds.ls(long=True))
        animimport.import_clip(fbx, namespace=NAMESPACE, set_timeline=False)
        fresh = [n for n in (set(cmds.ls(long=True)) - before)
                 if cmds.objExists(n)]
        for node in fresh:
            registry.append(uuid_of(node))
        imported = [n for n in fresh
                    if cmds.objectType(n) == "joint"
                    and not cmds.listRelatives(n, parent=True, type="joint")]
        check("the clip in the file names its root `root`",
              len(imported) == 1
              and leaf(imported[0]).split(":")[-1] == "root",
              ", ".join(leaf(n) for n in imported) or "nothing imported")

        # ------------------------------------- the import, lever suppressed
        cmds.select(chain_b[1], replace=True)
        with lever_disabled():
            control = animimport.import_clip(fbx, merge=True,
                                             set_timeline=False)
        moved = travel(path_of(uuid_b), 0.0, LAST)
        check("CONTROL: without the rename the root does not move at all",
              moved < 1e-6, "%.9f" % moved)
        check("CONTROL: every OTHER bone did take the clip",
              control.get("joints", 0) == len(CHAIN) - 1,
              str(control.get("joints")))
        check("CONTROL: and the root is named as unanimated",
              leaf(root_b) in (control.get("stale") or []),
              str(control.get("stale")))

        # ---------------------------------------------- the import, for real
        cmds.select(chain_b[1], replace=True)
        result = animimport.import_clip(fbx, merge=True, set_timeline=False)
        moved = travel(path_of(uuid_b), 0.0, LAST)
        check("THE GATE: the second character's root takes the root motion",
              abs(moved - reference) < 1e-4,
              "%.7f against %.7f" % (moved, reference))
        check("every bone of B is animated, root included",
              result.get("joints", 0) == len(CHAIN)
              and not (result.get("stale") or []),
              "%s joints, stale %s" % (result.get("joints"),
                                       result.get("stale")))
        check("the status names the rename",
              "root motion" in (result.get("warning") or ""),
              (result.get("warning") or "")[:70])
        check("B wears its own name again afterwards",
              leaf(path_of(uuid_b)) == leaf(root_b), leaf(path_of(uuid_b)))

        # --------------------------------------------- the other character
        a_moved = travel(path_of(uuid_a), 0.0, LAST)
        check("character A never moved", a_moved < 1e-9, "%.9f" % a_moved)
        check("A wears its own name", leaf(path_of(uuid_a)) == leaf(root_a),
              leaf(path_of(uuid_a)))
        check("no joint anywhere is left holding a hold name",
              not [p for p in (cmds.ls(type="joint", long=True) or [])
                   if leaf(p).startswith(animimport.HOLD_PREFIX)])

    finally:
        for step in (
                lambda: cmds.select(clear=True),
                lambda: _delete(registry),
                lambda: cmds.namespace(removeNamespace=NAMESPACE)
                if cmds.namespace(exists=NAMESPACE) else None,
                lambda: cmds.autoKeyframe(state=auto_key),
                lambda: cmds.playbackOptions(
                    animationStartTime=playback[0],
                    animationEndTime=playback[1],
                    minTime=playback[2], maxTime=playback[3]),
                lambda: cmds.currentTime(frame, edit=True),
                lambda: cmds.select(
                    [n for n in selection if cmds.objExists(n)], replace=True)
                if selection else cmds.select(clear=True),
        ):
            try:
                step()
            except Exception:
                traceback.print_exc()
        try:
            if os.path.isfile(fbx):
                os.remove(fbx)
        except OSError:
            notes.append("could not remove " + fbx)

    after = sorted(leaf(p) for p in (cmds.ls(type="joint", long=True) or []))
    check("the animator's scene is exactly as it was found",
          after == scene_names_before,
          "%d joints before, %d after" % (len(scene_names_before), len(after)))


def _delete(registry):
    """By UUID, never by name: a failure may have left the nodes renamed,
    and a name diff would not find them (trap 47)."""
    doomed = []
    for uuid in registry:
        path = path_of(uuid)
        if path and cmds.objExists(path):
            doomed.append(path)
    if doomed:
        cmds.delete(doomed)


try:
    run()
except Exception:
    traceback.print_exc()
    failures.append("the run raised")

print("\n%d of %d gates failed" % (len(failures), len(gates)))
for note in notes:
    print("note: " + note)
for name in failures:
    print("FAILED: " + name)
