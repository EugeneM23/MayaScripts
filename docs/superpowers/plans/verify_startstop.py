"""verify_startstop - mayapy STANDALONE proof of Start/Stop Builder (docs/superpowers/specs/2026-11-17-start-stop-builder-design.md).

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/verify_startstop.py

Unreal's clips as the bridge exports them (not in the repository), from %TEMP%/maya_uebridge:
M_Neutral_Sprint_Stop_F_Lfoot (a stop), AS_am_LongS_OxGuardL_Walk_Fwd_Start (a start) and
AS_am_LongS_OxGuardL_Walk_Fwd (its loop), AS_Creep_Jog_B_Start / _Stop (never still). The poses: the animator's goblin and two_handed_sword .wpose files
(SKELDAR_WALKS, default Documents/maya/SkeldarWalks), made into Pose Library cards in a temp library by
maya_walk.cards.migrate - the road the card's wells take. Each clip is keyed onto the plugin's Manny UE5 skeleton
(Add Character) joint by joint by its world matrix, then pressed through maya_startstop.scene.apply.
"""
import os
import shutil
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.normpath(os.path.join(HERE, "..", "..", "..", "SkeldarAnim"))
CLIPS = os.path.join(os.environ.get("TEMP", ""), "maya_uebridge")
STOP = os.path.join(CLIPS, "M_Neutral_Sprint_Stop_F_Lfoot.fbx")
START = os.path.join(CLIPS, "AS_am_LongS_OxGuardL_Walk_Fwd_Start.fbx")
LOOP = os.path.join(CLIPS, "AS_am_LongS_OxGuardL_Walk_Fwd.fbx")
CREEP_START = os.path.join(CLIPS, "AS_Creep_Jog_B_Start.fbx")
CREEP_STOP = os.path.join(CLIPS, "AS_Creep_Jog_B_Stop.fbx")
WALKS = os.environ.get("SKELDAR_WALKS") or os.path.join(os.environ["USERPROFILE"], "Documents", "maya", "SkeldarWalks")

import maya.standalone  # noqa: E402
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402

sys.path.insert(0, PLUGIN)
for name in ("fbxmaya", "matrixNodes", "quatNodes"):
    cmds.loadPlugin(name, quiet=True)

from maya_startstop import model, scene, weapon  # noqa: E402

GATES = []


def gate(name, ok, detail):
    GATES.append((name, bool(ok)))
    print("%s  %-66s %s" % ("PASS" if ok else "FAIL", name, detail))


def add_skeleton():
    from maya_scenesetup import catalog, character
    before = set(cmds.ls(type="joint", long=True))
    character.add_character(catalog.character_for("Manny", "skeleton"))
    new = [j for j in cmds.ls(type="joint", long=True) if j not in before]
    return [j for j in new if not cmds.listRelatives(j, parent=True, type="joint")][0]


def key_clip(root, fbx, ns):
    """The FBX imported into `ns`, every joint of `root` constrained to its namesake with no offset and baked,
    the clip gone. Returns (start, end)."""
    cmds.namespace(add=ns)
    cmds.namespace(set=ns)
    mel.eval("FBXResetImport")
    mel.eval("FBXImportMode -v add")
    mel.eval("FBXImportSetMayaFrameRate -v false")
    mel.eval('FBXImport -f "%s"' % fbx.replace("\\", "/"))
    cmds.namespace(set=":")
    cmds.currentUnit(time="ntsc")
    src = dict((j.split("|")[-1].split(":")[-1], j) for j in cmds.ls(ns + ":*", type="joint", long=True))
    times = cmds.keyframe(list(src.values()), query=True, timeChange=True) or [0.0]
    start, end = int(round(min(times))), int(round(max(times)))
    temps, driven = [], []
    for joint in scene._joints(root):
        leaf = scene._leaf(joint)
        if leaf in src:
            temps += cmds.parentConstraint(src[leaf], joint, maintainOffset=False)
            driven.append(joint)
    cmds.bakeResults(driven, time=(start, end), simulation=True, attribute=["tx", "ty", "tz", "rx", "ry", "rz"])
    cmds.delete(temps)
    cmds.namespace(removeNamespace=ns, deleteNamespaceContent=True)
    cmds.playbackOptions(minTime=start, maxTime=end, animationStartTime=start, animationEndTime=end)
    cmds.currentTime(start)
    return start, end


def cards():
    from maya_walk import cards as wcards
    folder, library = tempfile.mkdtemp(), tempfile.mkdtemp()
    for name in ("goblin", "two_handed_sword"):
        shutil.copy(os.path.join(WALKS, name + ".wpose.gz"), folder)
    wcards.migrate(folder, library)
    return dict((n, os.path.join(library, wcards.MIGRATED_FOLDER, n + ".pose")) for n in ("goblin", "two_handed_sword"))


def slide_over(clip, a, w):
    worst = 0.0
    for s in model.SIDES:
        for joint in ("foot_" + s, "ball_" + s):
            j = clip.index[joint]
            for c0, c1 in a.feet[s]["contacts"]:
                for f in range(c0 + 1, c1 + 1):
                    moved = float(np.linalg.norm(w[j, f, 3, :3] - w[j, f - 1, 3, :3]))
                    own = float(np.linalg.norm(clip.worlds[j, f, 3, :3] - clip.worlds[j, f - 1, 3, :3]))
                    worst = max(worst, moved - own)
    return worst


def lengths_off(clip, a, w):
    worst = 0.0
    for j in range(clip.J):
        p = clip.parents[j]
        if p < 0 or a.kind[j] in ("helper", "pelvis"):
            continue
        new = np.linalg.norm(w[j, :, 3, :3] - w[p, :, 3, :3], axis=1)
        old = np.linalg.norm(clip.worlds[j, :w.shape[1], 3, :3] - clip.worlds[p, :w.shape[1], 3, :3], axis=1)
        worst = max(worst, float(np.abs(new - old).max()))
    return worst


def rel(a, b):
    return np.einsum("fij,fjk->fik", a, np.linalg.inv(b))


def main():
    poses = cards()
    knobs = model.knobs()

    # 1. a stop, nothing posed: the clip itself
    root = add_skeleton()
    key_clip(root, STOP, "stopsrc")
    source, _s, _j = scene.read_worlds(root)
    still = model.knobs(torso_drag=0.0, head_drag=0.0, arm_drag=0.0)      # (the springs are their own gate)
    text = scene.apply(root, still, None)
    played, _s, _j = scene.read_worlds(root)
    off = float(np.abs(played.worlds[:, :, 3, :3] - source.worlds[:, :, 3, :3]).max())
    gate("no pose, no springs: the skeleton plays its clip", off < 1e-3, "%.2e cm" % off)
    entry = scene.entry_of(root)
    a = entry.analysis
    gate("the stop reads as a stop", a.transition == "stop", a.transition)
    gate("the clip kept on the top joint", scene.has_source(root), scene.SOURCE_ATTR)

    # 2. the goblin: planted feet, lengths
    scene.apply(root, knobs, poses["goblin"])
    w, _s, _j = scene.read_worlds(root)
    gate("goblin: no planted foot moves more than the clip's", slide_over(source, a, w.worlds) < 0.05,
         "%.4f cm a frame" % slide_over(source, a, w.worlds))
    gate("goblin: every bone the clip's length", lengths_off(source, a, w.worlds) < 1e-3,
         "%.2e cm" % lengths_off(source, a, w.worlds))

    # 3. the sword: the grip, the Weapon tab
    text = scene.apply(root, knobs, poses["two_handed_sword"])
    w, _s, _j = scene.read_worlds(root)
    ix = source.index
    grip = rel(w.worlds[ix["hand_l"]], w.worlds[ix["hand_r"]])
    spread = float(np.abs(grip - grip[0]).max())
    gate("sword: the two-handed grip held", spread < 1e-3, "%.2e" % spread)
    _name, pose = entry.pose(poses["two_handed_sword"])
    result = model.evaluate(a, pose, k=knobs)
    keyed = float(np.abs(w.worlds[:, :, 3, :3] - result.worlds[:, :, 3, :3]).max())
    gate("sword: the keys are the model's", keyed < 1e-3, "%.2e cm" % keyed)
    gate("sword: Hold holds both hands", result.info["weapon"]["hold"] == ["l", "r"], result.info["weapon"]["hold"])
    gate("sword: the line names the hold", "ride the chest" in text, text.split("|")[-1].strip())
    chest = weapon._chest(source)
    free = model.evaluate(a, pose, k=model.knobs(weapon_hold=0.0))
    held_swing = float(np.ptp(rel(result.worlds[ix["hand_r"]], result.worlds[chest])[:, 3, :3], axis=0).max())
    free_swing = float(np.ptp(rel(free.worlds[ix["hand_r"]], free.worlds[chest])[:, 3, :3], axis=0).max())
    gate("sword: a held hand moves less against the chest", held_swing < free_swing,
         "%.2f cm against %.2f" % (held_swing, free_swing))
    late = model.evaluate(a, pose, k=model.knobs(weapon_overlap=100.0))
    lag = late.info["weapon"]["lag"]
    gate("sword: Overlap 100 ms is 100 ms of frames", abs(lag - 0.1 * source.fps) < 1e-6,
         "%.2f fr at %g fps" % (lag, source.fps))
    still = model.evaluate(a, pose, k=model.knobs(weapon_inherit=0.0))
    moved = float(np.abs(still.worlds[ix["hand_r"]] - result.worlds[ix["hand_r"]]).max())
    gate("sword: Inherit 0 changes the held hand", moved > 0.1, "%.2f cm" % moved)

    # 4. undo and Restore
    before = scene.read_worlds(root)[0].worlds
    cmds.undoInfo(state=True)
    scene.apply(root, knobs, poses["goblin"])
    cmds.undo()
    back = float(np.abs(scene.read_worlds(root)[0].worlds - before).max())
    gate("one undo takes a press back", back < 1e-6, "%.2e" % back)
    scene.restore(root)
    own = float(np.abs(scene.read_worlds(root)[0].worlds[:, :, 3, :3] - source.worlds[:, :, 3, :3]).max())
    gate("Restore: the clip's own keys back", own < 1e-3 and not scene.has_source(root), "%.2e cm" % own)

    # 5. a start ending on its loop
    cycle_root = add_skeleton()
    key_clip(cycle_root, LOOP, "loopsrc")
    start_root = add_skeleton()
    key_clip(start_root, START, "startsrc")
    start_clip = scene.read_worlds(start_root)[0]
    scene.use_cycle(cycle_root)
    text = scene.apply(start_root, knobs, poses["goblin"])
    entry = scene.entry_of(start_root)
    a = entry.analysis
    gate("the start reads as a start", a.transition == "start", a.transition)
    _name, pose = entry.pose(poses["goblin"])
    current = scene.cycle()
    result = model.evaluate(a, pose, k=knobs, start=None, cycle=current["cycle"])
    info = result.info["cycle"]
    played = scene.read_worlds(start_root)[0].worlds
    keyed = float(np.abs(played[:, :, 3, :3] - result.worlds[:, :, 3, :3]).max())
    gate("start: the keys are the model's", keyed < 1e-3, "%.2e cm" % keyed)
    cyc = current["cycle"]
    aligned = cyc.sample(info["phase"]) @ info["place"]
    pairs = [(j, cyc.clip.index[n]) for j, n in enumerate(start_clip.names) if n in cyc.clip.index]
    last = max(float(np.abs(played[j, -1] - aligned[jc]).max()) for j, jc in pairs)
    gate("start: its last frame is the loop's frame (placed)", info.get("end") and last < 1e-3,
         "%.2e at the loop's frame %.2f" % (last, info["phase"]))
    B = int(info["frames"])                  # the last B frames go from the start to the loop
    before = lengths_off(start_clip, a, played[:, :start_clip.F - B])
    gate("start: every bone the clip's length before it goes to the loop", before < 1e-3, "%.2e cm" % before)
    # the loop's own bone lengths differ from the start's (UE clips key translations): the window between them
    # stays between the two
    loop = cyc.frames
    own = 0.0
    for j, jc in pairs:
        p, pc_ = start_clip.parents[j], cyc.clip.parents[jc]
        if p < 0 or pc_ < 0 or a.kind[j] in ("helper", "pelvis"):
            continue
        mine = np.linalg.norm(start_clip.worlds[j, -1, 3, :3] - start_clip.worlds[p, -1, 3, :3])
        theirs = np.linalg.norm(loop[jc, :, 3, :3] - loop[pc_, :, 3, :3], axis=1)
        own = max(own, float(np.abs(theirs - mine).max()))
    window = lengths_off(start_clip, a, played)
    gate("start: into the loop no bone strays past the two clips' own lengths", window <= own + 1e-3,
         "%.3f cm against the clips' own %.3f" % (window, own))

    # 6. starts and stops that never stand still read by their slow end
    for path, want in ((CREEP_START, "start"), (CREEP_STOP, "stop")):
        other = add_skeleton()
        key_clip(other, path, "creep" + want)
        found = model.Analysis(scene.read_worlds(other)[0])
        gate("%s reads as a %s" % (os.path.basename(path), want), found.transition == want,
             "%s, reference %s" % (found.transition, found.reference))

    failed = [n for n, ok in GATES if not ok]
    print("\n%d of %d gates failed" % (len(failed), len(GATES)))
    for n in failed:
        print("  FAILED: " + n)


if __name__ == "__main__":
    try:
        main()
    finally:
        os._exit(0)
