"""Proof for root_offset_batch_tool (C:/!!!Work/Perforce/Atone/Scripts/Maya).

NOT a bridge script. This one runs in its own mayapy session:

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/verify_root_offset_batch.py

and it must stay that way, because the tool starts every file with
`cmds.file(new=True, force=True)` -- sending it down the command port would
discard whatever the animator has open.

Two halves. First a SYNTHETIC root with a deliberately curved translateZ, a
UE-style custom-attribute curve and a rotation, where the splice can be
measured against values worked out by hand. Then a REAL clip from
//Atone/Animations/Export, imported and re-exported through the tool's own
import/export, because the bug that started this ("клип обрезается") only
shows up in the file that lands on disk.

What is claimed, per the animator's rule -- act inside the window, keep
everything else as it is:

  * frames before the window keep their exact shape,
  * the window is the straight offset,
  * frames after the window keep their shape and continue from where the
    offset stopped, no jump at the seam,
  * every other channel on the root -- rotate, scale, Pose_0..9,
    MoveData_Speed, the pose drivers -- is left alone,
  * the exported FBX covers the whole clip, not just the window.
"""

import os
import sys
import tempfile

import maya.standalone
maya.standalone.initialize(name="python")

import maya.cmds as cmds
import maya.mel as mel

TOOL_DIR = r"C:/!!!Work/Perforce/Atone/Scripts/Maya"
sys.path.append(TOOL_DIR)
import root_offset_batch_tool as T  # noqa: E402

SOURCE_DIR = r"C:/!!!Work/Animations/Export"
WALK = os.path.join(SOURCE_DIR, "ShortSword_Walk_1P.fbx").replace("\\", "/")
ATTACK = os.path.join(SOURCE_DIR, "ShortSword_Attack_Right_3P.FBX").replace("\\", "/")
OUT_DIR = tempfile.mkdtemp(prefix="root_offset_proof_")

RESULTS = []
TOL = 1e-6


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print("{0} {1}{2}".format("PASS" if ok else "FAIL", name,
                              "  " + detail if detail else ""))


def close(name, got, want, tol=TOL):
    check(name, abs(got - want) <= tol, "got {0:.6f} want {1:.6f}".format(got, want))


def sample(node, attr, frames):
    return [cmds.getAttr("{0}.{1}".format(node, attr), time=f) for f in frames]


def worst(left, right):
    return max(abs(a - b) for a, b in zip(left, right)) if left else 0.0


def key_times(node, attr):
    return sorted(cmds.keyframe(node, attribute=attr, query=True, timeChange=True) or [])


def read_back(path):
    """Import a file to look at it. The mode has to be set here too: the tool
    restores whatever it found, so a raw FBXImport after gate 21 would still
    run under exmerge and create nothing -- trap 33 from the other side."""
    cmds.file(new=True, force=True)
    mel.eval('FBXImportMode -v add')
    mel.eval('FBXImportSetMayaFrameRate -v true')
    mel.eval('FBXImport -f "{0}"'.format(path))


def all_key_times():
    curves = cmds.ls(type=T.TIME_CURVES) or []
    return sorted(cmds.keyframe(curves, query=True, timeChange=True) or []) if curves else []


# ---------------------------------------------------------------------------
# a synthetic root whose curve has a real shape, so "the shape survived" is
# not something a straight line can pass by accident
# ---------------------------------------------------------------------------

def build_synthetic():
    cmds.file(new=True, force=True)
    cmds.select(clear=True)
    root = cmds.joint(name="root")
    cmds.addAttr(root, longName="Pose_0", attributeType="double", keyable=True)
    cmds.addAttr(root, longName="MoveData_Speed", attributeType="double", keyable=True)

    for frame, value in ((0, 0.0), (5, -30.0), (20, 50.0), (40, 100.0)):
        cmds.setKeyframe(root, attribute="translateZ", time=frame, value=value)
    for frame, value in ((0, 0.0), (40, 40.0)):
        cmds.setKeyframe(root, attribute="translateX", time=frame, value=value)
    for frame, value in ((0, 0.0), (40, 90.0)):
        cmds.setKeyframe(root, attribute="rotateY", time=frame, value=value)
    for frame, value in ((0, 0.0), (13, 1.0), (40, 0.0)):
        cmds.setKeyframe(root, attribute="Pose_0", time=frame, value=value)
    for frame, value in ((0, 0.0), (40, 600.0)):
        cmds.setKeyframe(root, attribute="MoveData_Speed", time=frame, value=value)
    return cmds.ls(root, long=True)[0]


PRE = [0, 2, 4, 5, 7, 9, 10]          # before and up to the window start
TAIL = [20, 22, 25, 30, 35, 40]       # the window end and everything after
INSIDE = [11, 13, 15, 17, 19]

root = build_synthetic()
before_pre_z = sample(root, "translateZ", PRE)
before_tail_z = sample(root, "translateZ", TAIL)
before_x = sample(root, "translateX", PRE + INSIDE + TAIL)
before_ry = sample(root, "rotateY", PRE + INSIDE + TAIL)
before_pose = sample(root, "Pose_0", PRE + INSIDE + TAIL)
before_speed_keys = key_times(root, "MoveData_Speed")
base_z = cmds.getAttr(root + ".translateZ", time=10)
old_end_z = cmds.getAttr(root + ".translateZ", time=20)

# ============================ the splice ===================================
try:
    T.apply_root_offset(root, "Z", 200.0, 10, 10, "linear", "linear", False)
    spliced = True
except Exception as exc:                                     # noqa: BLE001
    check("1. apply_root_offset runs", False, repr(exc))
    spliced = False

if spliced:
    check("1. apply_root_offset runs", True)

    # ---- the window itself
    close("2. window start holds the original value",
          cmds.getAttr(root + ".translateZ", time=10), base_z)
    close("3. window end is start + distance",
          cmds.getAttr(root + ".translateZ", time=20), base_z + 200.0)
    close("4. the window is a straight ramp (midpoint)",
          cmds.getAttr(root + ".translateZ", time=15), base_z + 100.0)

    # ---- everything before the window is untouched, shape included
    after_pre_z = sample(root, "translateZ", PRE)
    check("5. frames before the window keep their exact shape",
          worst(after_pre_z, before_pre_z) <= TOL,
          "worst {0:.9f}".format(worst(after_pre_z, before_pre_z)))

    # ---- the tail is kept and continues from where the offset stopped
    delta = (base_z + 200.0) - old_end_z
    after_tail_z = sample(root, "translateZ", TAIL)
    want_tail = [v + delta for v in before_tail_z]
    check("6. the tail keeps its shape, shifted to continue (delta {0:.3f})".format(delta),
          worst(after_tail_z, want_tail) <= TOL,
          "worst {0:.9f}".format(worst(after_tail_z, want_tail)))
    close("7. no jump at the seam", cmds.getAttr(root + ".translateZ", time=20),
          before_tail_z[0] + delta)

    # ---- nothing else on the root was touched
    check("8. translateX untouched when 'key all axes' is off",
          worst(sample(root, "translateX", PRE + INSIDE + TAIL), before_x) <= TOL)
    check("9. rotateY untouched",
          worst(sample(root, "rotateY", PRE + INSIDE + TAIL), before_ry) <= TOL)
    check("10. the UE curve Pose_0 survives untouched",
          worst(sample(root, "Pose_0", PRE + INSIDE + TAIL), before_pose) <= TOL)
    check("11. MoveData_Speed keeps its keys",
          key_times(root, "MoveData_Speed") == before_speed_keys)

    # ---- the export range must cover the clip, not just the window
    rng = (cmds.playbackOptions(query=True, animationStartTime=True),
           cmds.playbackOptions(query=True, animationEndTime=True))
    check("12. the animation range covers the whole clip", rng[0] <= 0 and rng[1] >= 40,
          "range {0}..{1}".format(*rng))

# ============================ key all axes =================================
root = build_synthetic()
before_x_pre = sample(root, "translateX", PRE)
before_x_tail = sample(root, "translateX", TAIL)
base_x = cmds.getAttr(root + ".translateX", time=10)
old_end_x = cmds.getAttr(root + ".translateX", time=20)
try:
    T.apply_root_offset(root, "Z", 200.0, 10, 10, "linear", "linear", True)
    close("13. an idle axis is held flat inside the window",
          cmds.getAttr(root + ".translateX", time=15), base_x)
    check("14. an idle axis keeps the frames before the window",
          worst(sample(root, "translateX", PRE), before_x_pre) <= TOL)
    dx = base_x - old_end_x
    check("15. an idle axis's tail continues from the hold",
          worst(sample(root, "translateX", TAIL), [v + dx for v in before_x_tail]) <= TOL,
          "delta {0:.3f}".format(dx))
except Exception as exc:                                     # noqa: BLE001
    for name in ("13. an idle axis is held flat inside the window",
                 "14. an idle axis keeps the frames before the window",
                 "15. an idle axis's tail continues from the hold"):
        check(name, False, repr(exc))

# ==================== a root with no animation at all ======================
cmds.file(new=True, force=True)
cmds.select(clear=True)
bare = cmds.ls(cmds.joint(name="root"), long=True)[0]
try:
    T.apply_root_offset(bare, "Z", 100.0, 0, 30, "linear", "linear", True)
    close("16. an unanimated root starts at its own value",
          cmds.getAttr(bare + ".translateZ", time=0), 0.0)
    close("17. an unanimated root lands on the distance",
          cmds.getAttr(bare + ".translateZ", time=30), 100.0)
    check("18. exactly two keys on the offset axis",
          key_times(bare, "translateZ") == [0.0, 30.0],
          str(key_times(bare, "translateZ")))
except Exception as exc:                                     # noqa: BLE001
    for name in ("16. an unanimated root starts at its own value",
                 "17. an unanimated root lands on the distance",
                 "18. exactly two keys on the offset axis"):
        check(name, False, repr(exc))

# ==================== which joint is the root ==============================
cmds.file(new=True, force=True)
cmds.select(clear=True)
cmds.joint(name="pelvis", position=(0, 100, 0))
cmds.joint(name="spine_01", position=(0, 110, 0))
cmds.select(clear=True)
cmds.joint(name="ik_hand_root", position=(50, 0, 0))
picked = T.find_root_joint()
check("19. a stray ik_hand_root does not win over the real skeleton root",
      picked is not None and picked.split("|")[-1] == "pelvis", str(picked))

cmds.file(new=True, force=True)
cmds.select(clear=True)
cmds.joint(name="root")
cmds.joint(name="pelvis", position=(0, 100, 0))
cmds.select(clear=True)
cmds.joint(name="ik_foot_root", position=(0, 0, 50))
check("20. the real root still wins when it exists",
      (T.find_root_joint() or "").split("|")[-1] == "root", str(T.find_root_joint()))

# ==================== the FBX round trip ===================================
cmds.loadPlugin("fbxmaya", quiet=True)

if not os.path.isfile(ATTACK):
    check("21. source clip available", False, ATTACK)
else:
    # trap 33: the import mode is a global session setting, and maya_uebridge
    # leaves it on exmerge, where the importer creates nothing at all.
    mel.eval('FBXImportMode -v exmerge')
    T.import_fbx(ATTACK)
    joints = cmds.ls(type="joint") or []
    check("21. the import works even after something left the mode on exmerge",
          len(joints) > 50, "{0} joint(s)".format(len(joints)))

    if joints:
        root = T.find_root_joint()
        src_keys = all_key_times()
        src_range = (min(src_keys), max(src_keys))
        ue_curves = [c for c in (cmds.listConnections(root, type="animCurve",
                                                     source=True, destination=False) or [])
                     if not c.split("_")[-1] in ("translateX", "translateY", "translateZ")]
        src_ue = len(set(ue_curves))
        check("22. the scene fps follows the file, so keys land on whole frames",
              all(abs(t - round(t)) < 1e-6 for t in src_keys),
              "fps {0}, range {1}..{2}".format(cmds.currentUnit(query=True, time=True),
                                               src_range[0], src_range[1]))

        base = cmds.getAttr(root + ".translateZ", time=0)
        REAL_TAIL = [21, 25, 30, 40, 46]
        orig_tail = sample(root, "translateZ", REAL_TAIL)
        old_end = cmds.getAttr(root + ".translateZ", time=20)
        T.apply_root_offset(root, "Z", 300.0, 0, 20, "linear", "linear", True)
        out = os.path.join(OUT_DIR, "attack_offset.fbx").replace("\\", "/")
        T.export_fbx(out)
        check("23. the file was written", os.path.isfile(out), out)

        read_back(out)
        got_keys = all_key_times()
        got_range = (min(got_keys), max(got_keys)) if got_keys else (None, None)
        check("24. the exported clip is not cut down to the offset window",
              got_keys and got_range[0] <= src_range[0] + TOL
              and got_range[1] >= src_range[1] - TOL,
              "source {0}..{1} -> export {2}..{3}".format(
                  src_range[0], src_range[1], got_range[0], got_range[1]))

        rr = T.find_root_joint()
        got_ue = len(set(c for c in (cmds.listConnections(rr, type="animCurve", source=True,
                                                          destination=False) or [])
                        if not c.split("_")[-1] in ("translateX", "translateY", "translateZ")))
        check("25. the UE curves on the root survive the round trip",
              got_ue >= src_ue, "{0} before, {1} after".format(src_ue, got_ue))
        close("26. the offset is in the exported file",
              cmds.getAttr(rr + ".translateZ", time=20), base + 300.0, tol=1e-3)

        # the real-clip version of gate 6: this root actually travels, so a
        # tail that merely "exists" is not the claim -- it has to be the
        # original motion, carried
        real_shift = (base + 300.0) - old_end
        got_tail = sample(rr, "translateZ", REAL_TAIL)
        want_tail = [v + real_shift for v in orig_tail]
        check("27. the real clip's root motion after the window is carried, not redone",
              worst(got_tail, want_tail) <= 1e-3,
              "worst {0:.6f} over frames {1}".format(worst(got_tail, want_tail), REAL_TAIL))

# ============ a second clip, and the body animation around the window ======
# Measured on the SKELETON's curves, not on every curve in the scene: the
# earliest keys in ShortSword_Walk_1P (-25..4) belong to Manny_rig:camera1,
# and the tool deliberately leaves cameras out of the export. An early
# version of this gate compared against those and read the tool as lossy.
def joint_curves():
    found = set()
    for joint in cmds.ls(type="joint", long=True) or []:
        found.update(cmds.listConnections(joint, type="animCurve",
                                         source=True, destination=False) or [])
    return [c for c in found if cmds.nodeType(c) in T.TIME_CURVES]


def skeleton_key_times():
    curves = joint_curves()
    return sorted(cmds.keyframe(curves, query=True, timeChange=True) or []) if curves else []


def liveliest_plug(skip_node):
    """The channel with the widest travel, so 'unchanged' is a real claim.
    A 1P clip animates arms and weapon only -- thigh_l sits perfectly still
    through the whole thing and would pass anything."""
    best = (0.0, None)
    for curve in joint_curves():
        plug = (cmds.listConnections(curve + ".output", destination=True,
                                     plugs=True) or [None])[0]
        if not plug or plug.split(".")[0] == skip_node.split("|")[-1]:
            continue
        values = cmds.keyframe(curve, query=True, valueChange=True) or []
        if values and max(values) - min(values) > best[0]:
            best = (max(values) - min(values), plug)
    return best


if not os.path.isfile(WALK):
    check("28. second clip available", False, WALK)
else:
    T.import_fbx(WALK)
    src_range = (min(skeleton_key_times()), max(skeleton_key_times()))
    root = T.find_root_joint()
    spread, plug = liveliest_plug(root)
    body_frames = [int(src_range[0]), 3, 9, 14, int(src_range[1])]
    orig_body = [cmds.getAttr(plug, time=f) for f in body_frames] if plug else []

    T.apply_root_offset(root, "Z", 150.0, 0, 30, "linear", "linear", True)
    out = os.path.join(OUT_DIR, "walk_offset.fbx").replace("\\", "/")
    T.export_fbx(out)

    read_back(out)
    got_range = (min(skeleton_key_times()), max(skeleton_key_times()))
    check("28. the skeleton's whole key range survives the export",
          got_range[0] <= src_range[0] + TOL and got_range[1] >= src_range[1] - TOL,
          "source {0:g}..{1:g} -> export {2:g}..{3:g}".format(*(src_range + got_range)))
    got_body = [cmds.getAttr(plug, time=f) for f in body_frames] if plug else []
    check("29. the body animation across the window is untouched",
          bool(got_body) and worst(got_body, orig_body) <= 1e-3,
          "{0} travels {1:.1f}, worst {2:.6f}".format(plug, spread,
                                                      worst(got_body, orig_body)))

# ============ frames before zero, on the skeleton itself ===================
# The general form of the animator's complaint. FBX carries negative time
# fine; this is the gate that would catch it if a future change started
# clamping the export at frame zero.
cmds.file(new=True, force=True)
cmds.select(clear=True)
neg = cmds.joint(name="root")
for frame, value in ((-10, 5.0), (-5, 7.0), (0, 11.0), (5, 13.0), (10, 17.0)):
    cmds.setKeyframe(neg, attribute="translateY", time=frame, value=value)
T.apply_root_offset(cmds.ls(neg, long=True)[0], "Z", 60.0, 0, 5,
                    "linear", "linear", False)
neg_out = os.path.join(OUT_DIR, "negative.fbx").replace("\\", "/")
T.export_fbx(neg_out)
read_back(neg_out)
back = cmds.ls("root", long=True)[0]
check("30. keys before frame zero survive the export",
      key_times(back, "translateY") == [-10.0, -5.0, 0.0, 5.0, 10.0],
      str(key_times(back, "translateY")))
check("31. and they keep their values",
      worst(sample(back, "translateY", [-10, -5, 0, 5, 10]),
            [5.0, 7.0, 11.0, 13.0, 17.0]) <= 1e-4)

# ==================== the source must not be overwritten ===================
# On a copy, and measured by hash: an exception on its own proves nothing --
# the first version of this gate "passed" because the import had failed for an
# unrelated reason, long before the export could have overwritten anything.
import hashlib                                              # noqa: E402
import shutil                                               # noqa: E402


def digest(path):
    with open(path, "rb") as handle:
        return hashlib.md5(handle.read()).hexdigest()


if os.path.isfile(WALK):
    sandbox = os.path.join(OUT_DIR, "in_place")
    os.makedirs(sandbox)
    victim = os.path.join(sandbox, "ShortSword_Walk_1P.fbx")
    shutil.copy2(WALK, victim)
    before = digest(victim)

    tool = T.RootOffsetBatchTool()
    tool.source_dir = sandbox
    tool.output_dir = sandbox
    tool.log = lambda message: None
    reason = ""
    try:
        tool._process_one("ShortSword_Walk_1P.fbx", {
            "axis": "Z", "distance": 100.0, "start_frame": 0, "frame_count": 30,
            "start_tangent": "linear", "end_tangent": "linear",
            "key_all_axes": True, "suffix": ""})
    except Exception as exc:                                 # noqa: BLE001
        reason = str(exc)
    check("32. writing on top of the source file is refused, and says why",
          "overwrite the source" in reason, reason or "no error raised")
    check("33. the source file is untouched", digest(victim) == before)

    # ...and the same run with a suffix must go through
    tool.log = lambda message: None
    tool._process_one("ShortSword_Walk_1P.fbx", {
        "axis": "Z", "distance": 100.0, "start_frame": 0, "frame_count": 30,
        "start_tangent": "linear", "end_tangent": "linear",
        "key_all_axes": True, "suffix": "_offset"})
    check("34. the same file exports fine with a suffix",
          os.path.isfile(os.path.join(sandbox, "ShortSword_Walk_1P_offset.fbx")))
    check("35. and the source is still untouched", digest(victim) == before)

# ---------------------------------------------------------------------------
passed = sum(1 for _n, ok, _d in RESULTS if ok)
print("\n{0}/{1} gates passed".format(passed, len(RESULTS)))
for name, ok, detail in RESULTS:
    if not ok:
        print("  FAILED: {0}  {1}".format(name, detail))
print("output in " + OUT_DIR)
