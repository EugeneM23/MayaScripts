"""Live checks: an animation from UE lands on the skeleton already in the scene.

Run inside Maya through the bridge runner, with the Unreal editor open.

The real question is not "did curves appear" but "is it the right animation".
So the clip is imported twice - once merged onto the scene skeleton, once as
its own reference skeleton - and the two are compared frame by frame. The
reference is deleted afterwards; the merged animation stays, which is the
point of the feature.

Driven through the window's own callbacks, so what is proved is the button the
animator presses, not an API underneath it.
"""

import sys

REPO = r"C:/!!!Work/MayaScripts/SkeldarAnim"
if REPO not in sys.path:
    sys.path.append(REPO)

for name in [m for m in list(sys.modules) if m.startswith("maya_uebridge")]:
    del sys.modules[name]

import maya.cmds as cmds

from maya_uebridge import animimport, window

SEARCH = "AS_Longsword_Attack_Back_Combo_2_Hold_1_3P"
SAMPLE_BONES = ["pelvis", "spine_03", "upperarm_l", "lowerarm_r", "hand_r",
                "thigh_l", "foot_l", "head"]
CHANNELS = ["rotateX", "rotateY", "rotateZ"]

failures = []
checks = [0]


def check(label, condition, detail=""):
    checks[0] += 1
    print("%-56s %s %s" % (label, "OK" if condition else "FAIL", detail))
    if not condition:
        failures.append(label)


def joints_now():
    return set(cmds.ls(type="joint", long=True) or [])


def namespaces_now():
    cmds.namespace(setNamespace=":")
    return set(cmds.namespaceInfo(listOnlyNamespaces=True) or [])


def sample(node, attr, frame):
    return cmds.getAttr("{0}.{1}".format(node, attr), time=frame)


def keyed_count(joints):
    return len([j for j in joints
                if (cmds.listConnections(j, type="animCurve", source=True,
                                         destination=False) or [])])


def key_range(joints):
    curves = list(set(cmds.listConnections(joints, type="animCurve",
                                           source=True, destination=False) or []))
    times = cmds.keyframe(curves, query=True, timeChange=True) or []
    return (min(times), max(times)) if times else (None, None)


def press_import():
    window._run(window.import_selected, busy="exporting...")
    return cmds.text(window._STATUS, query=True, label=True)


# ---------------------------------------------------------------- setup

scene_root = (cmds.ls("root", long=True) or [None])[0]
check("the scene has a root joint", bool(scene_root), scene_root or "")
if not scene_root:
    raise SystemExit

scene_joints = animimport.joints_under(scene_root)
print("scene skeleton: {0} joints\n".format(len(scene_joints)))

window.show_window()
window._run(window.refresh, busy="asking the editor...")
check("the editor answered", bool(window._STATE["records"]),
      "{0} assets".format(len(window._STATE["records"])))
if not window._STATE["records"]:
    raise SystemExit

cmds.textField(window._SEARCH, edit=True, text=SEARCH)
window._run(window._repopulate)
rows = cmds.textScrollList(window._LIST, query=True, numberOfItems=True) or 0
check("the test animation is in the list", rows >= 1, "{0} rows".format(rows))
if not rows:
    raise SystemExit
cmds.textScrollList(window._LIST, edit=True, selectIndexedItem=1)
target = window._selected_record()
print("clip: {0}  ({1} frames per UE)\n".format(target.name, target.frames))


# ---------------------------------------------------------------- the merge

joints_before = joints_now()
namespaces_before = namespaces_now()

cmds.select(clear=True)
cmds.radioButtonGrp(window._MODE, edit=True, select=1)
check("the window defaults to merging onto the scene", window.merge_selected())

status = press_import()
print("status: {0}\n".format(status))

check("the status names the skeleton it used", "root" in status, status[:60])
check("the status does not claim zero bones", "0 bones animated" not in status)
check("no 'nothing matched' warning", "no bone names matched" not in status)

check("no new joints were created", joints_now() == joints_before,
      "{0} added".format(len(joints_now() - joints_before)))
check("no namespace was created", namespaces_now() == namespaces_before,
      "{0} added".format(sorted(namespaces_now() - namespaces_before)))

keyed = keyed_count(scene_joints)
check("the scene skeleton is animated", keyed > 50,
      "{0}/{1} bones keyed".format(keyed, len(scene_joints)))

start, end = key_range(scene_joints)
check("it has a key range", start is not None, "{0} - {1}".format(start, end))
if target.frames:
    check("the range matches what UE reported",
          abs((end - start) - target.frames) <= 2,
          "maya {0:g} vs ue {1}".format(end - start, target.frames))

check("the timeline was set to the clip",
      abs(cmds.playbackOptions(query=True, maxTime=True) - end) < 0.001,
      "timeline max {0}".format(cmds.playbackOptions(query=True, maxTime=True)))

moved = 0
for bone in SAMPLE_BONES:
    node = (cmds.ls(bone, long=True) or [None])[0]
    if not node:
        continue
    spread = max(abs(sample(node, "rotateX", start + (end - start) * f)
                     - sample(node, "rotateX", start))
                 for f in (0.25, 0.5, 0.75, 1.0))
    if spread > 0.5:
        moved += 1
check("the bones actually move over time", moved >= 5,
      "{0}/{1} sampled bones change".format(moved, len(SAMPLE_BONES)))

# Animated plus untouched must account for the skeleton exactly. Without this
# the status happily said "92 animated" and "93 not in the clip" at once.
animated = keyed_count(scene_joints)
reported_missing = status.count("not in the clip") and status
missing_count = 0
if "bone(s) not in the clip" in status:
    missing_count = int(status.split("|")[-1].strip().split(" ")[0])
check("animated plus untouched accounts for the skeleton",
      animated + missing_count == len(scene_joints),
      "{0} + {1} vs {2}".format(animated, missing_count, len(scene_joints)))


# ---------------------------------------------------------------- twice over

status_again = press_import()
check("importing the same clip twice reports the same thing",
      status_again == status, status_again[:60])
check("and leaves the same number of bones keyed",
      keyed_count(scene_joints) == keyed)
check("and the same range", key_range(scene_joints) == (start, end))


# ---------------------------------------------------------------- ground truth

cmds.radioButtonGrp(window._MODE, edit=True, select=2)
check("the second mode is a separate skeleton", not window.merge_selected())
press_import()

reference_namespaces = sorted(namespaces_now() - namespaces_before)
check("the reference skeleton arrived in its own namespace",
      len(reference_namespaces) == 1, str(reference_namespaces))

if reference_namespaces:
    prefix = reference_namespaces[0]
    worst, worst_where, compared = 0.0, "", 0
    for bone in SAMPLE_BONES:
        mine = (cmds.ls(bone, long=True) or [None])[0]
        theirs = (cmds.ls("{0}:{1}".format(prefix, bone), long=True) or [None])[0]
        if not (mine and theirs):
            continue
        for channel in CHANNELS:
            for fraction in (0.0, 0.25, 0.5, 0.75, 1.0):
                frame = start + (end - start) * fraction
                gap = abs(sample(mine, channel, frame)
                          - sample(theirs, channel, frame))
                compared += 1
                if gap > worst:
                    worst, worst_where = gap, "{0}.{1}@{2:g}".format(
                        bone, channel, frame)
    check("merged animation equals the reference, frame for frame",
          worst < 0.001,
          "{0} samples, worst {1:.6f} deg at {2}".format(
              compared, worst, worst_where or "-"))

    mine = (cmds.ls("root", long=True) or [None])[0]
    theirs = (cmds.ls("{0}:root".format(prefix), long=True) or [None])[0]
    if mine and theirs:
        worst_t = max(
            abs(sample(mine, channel, start + (end - start) * fraction)
                - sample(theirs, channel, start + (end - start) * fraction))
            for channel in ("translateX", "translateY", "translateZ")
            for fraction in (0.0, 0.5, 1.0))
        check("root motion matches the reference", worst_t < 0.001,
              "worst {0:.6f} cm".format(worst_t))

    # A reference skeleton in the scene must not confuse the target choice.
    cmds.select(clear=True)
    chosen = animimport.choose_target_root(animimport.skeleton_roots(),
                                           animimport.selected_roots())
    check("the namespaced reference is not mistaken for the target",
          chosen == scene_root, str(chosen))

    cmds.namespace(setNamespace=":")
    if cmds.namespace(exists=prefix):
        cmds.namespace(removeNamespace=prefix, deleteNamespaceContent=True)
    check("the reference skeleton was removed again",
          not cmds.namespace(exists=prefix))

check("the scene skeleton kept its animation after the cleanup",
      keyed_count(scene_joints) > 50)

cmds.radioButtonGrp(window._MODE, edit=True, select=1)

print("\n{0}/{1} checks passed".format(checks[0] - len(failures), checks[0]))
if failures:
    print("FAILED: " + ", ".join(failures))
else:
    print("ALL GREEN")
