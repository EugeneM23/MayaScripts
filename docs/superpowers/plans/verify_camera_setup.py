"""Live proof for Camera Setup, run through the command port.

Two halves. First a SANDBOX: a throwaway joint with real animation and a
throwaway camera, driven through the same functions, where the camera can be
moved and the joint measured following it. That is the only honest place to
measure the follow -- after the bake the real camera's channels are keyed, and
rewriting the animator's curves to prove a point is not on the table.

Then the real scene, where the claim is that the bone's motion is unchanged and
now comes from the camera.

Never cmds.undo() from a bridge script: the whole script is one command.
"""

import maya.cmds as cmds

from maya_scenesetup import camera as camerarig
from maya_scenesetup import skeleton

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print("{0} {1}{2}".format("PASS" if ok else "FAIL", name,
                              "  " + detail if detail else ""))


def worst(left, right):
    return max(abs(a - b) for a, b in zip(left, right))


def sample(node, frames):
    restore = cmds.currentTime(query=True)
    found = []
    for frame in frames:
        cmds.currentTime(frame)
        found.append(camerarig.world_matrix(node))
    cmds.currentTime(restore)
    return found


start = cmds.playbackOptions(query=True, minTime=True)
end = cmds.playbackOptions(query=True, maxTime=True)
frames = [start, (start + end) // 2, end]

# ======================= the sandbox =====================================
# A joint that really moves, so "the bone did not move" cannot pass by being
# a still scene, and the follow can be measured by hand.
autokey = cmds.autoKeyframe(query=True, state=True)
cmds.autoKeyframe(state=False)

sandbox_root = cmds.group(empty=True, world=True, name="verify_camera_sandbox")
cmds.select(clear=True)
sandbox_bone = cmds.joint(name="verify_camera_bone")
sandbox_bone = cmds.parent(sandbox_bone, sandbox_root)[0]
sandbox_bone = cmds.ls(sandbox_bone, long=True)[0]

for frame, values in ((start, (0.0, 100.0, 0.0, 0.0, 0.0, 0.0)),
                      (end, (50.0, 130.0, -20.0, 25.0, 40.0, -15.0))):
    for channel, value in zip(camerarig.CHANNELS, values):
        cmds.setKeyframe(sandbox_bone, attribute=channel, time=frame,
                         value=value)

wanted = sample(sandbox_bone, frames)
check("the sandbox bone actually moves",
      worst(wanted[0], wanted[-1]) > 1.0,
      "travel {0:.3f}".format(worst(wanted[0], wanted[-1])))

cmds.currentTime(start)
message = camerarig.setup(sandbox_bone, start, end)
print("sandbox setup said:", message)

sandbox_camera = camerarig.existing_camera()
check("a camera was made", sandbox_camera is not None, str(sandbox_camera))

got = sample(sandbox_bone, frames)
check("the sandbox animation survived the setup",
      worst([v for m in wanted for v in m], [v for m in got for v in m]) < 1e-4,
      "worst world-matrix element {0:.9f}".format(
          worst([v for m in wanted for v in m], [v for m in got for v in m])))

check("the bone holds no curves of its own now",
      not (cmds.listConnections(sandbox_bone, type="animCurve") or []))
check("the camera holds the keys",
      bool(cmds.listConnections(sandbox_camera, type="animCurve")))

# The follow: move the camera at a frame and watch the joint go with it. The
# camera IS keyed after the bake, so the channel is read, poked and put back --
# never a literal rest value, and autoKey is off.
cmds.currentTime(start)
plug = sandbox_camera + ".translateX"
rest = cmds.getAttr(plug)
before = camerarig.world_matrix(sandbox_bone)
connections = cmds.listConnections(plug, source=True, destination=False) or []
if connections:
    cmds.disconnectAttr(connections[0] + ".output", plug)
cmds.setAttr(plug, rest + 40.0)
after = camerarig.world_matrix(sandbox_bone)
cmds.setAttr(plug, rest)
restored = camerarig.world_matrix(sandbox_bone)
if connections:
    cmds.connectAttr(connections[0] + ".output", plug)

check("moving the camera moves the bone", worst(before, after) > 1.0,
      "bone travelled {0:.3f} for 40 on the camera".format(
          worst(before, after)))
check("and putting the camera back puts the bone back",
      worst(before, restored) < 1e-6,
      "worst {0:.12f}".format(worst(before, restored)))

cmds.currentTime(start)
offset_now = camerarig.offset_between(camerarig.world_matrix(sandbox_bone),
                                     camerarig.world_matrix(sandbox_camera))
check("the camera stands at the measured axis offset",
      worst(offset_now, camerarig.AXIS_OFFSET) < 1e-4,
      "worst {0:.9f}".format(worst(offset_now, camerarig.AXIS_OFFSET)))

# The correction the user asked for: the camera lands IN the bone's transform,
# not merely somewhere rigidly attached to it.
check("the camera sits exactly on the bone",
      worst(camerarig.world_matrix(sandbox_camera)[12:],
            camerarig.world_matrix(sandbox_bone)[12:]) < 1e-6,
      "position gap {0:.9f}".format(
          worst(camerarig.world_matrix(sandbox_camera)[12:],
                camerarig.world_matrix(sandbox_bone)[12:])))

# The rigid ride is the real invariant: whatever the offset is, it must not
# change from frame to frame once the bone hangs off the camera.
spread = []
for frame in frames:
    cmds.currentTime(frame)
    spread.append(camerarig.offset_between(
        camerarig.world_matrix(sandbox_bone),
        camerarig.world_matrix(sandbox_camera)))
cmds.currentTime(start)
check("and holds it at every frame",
      max(worst(spread[0], other) for other in spread) < 1e-4,
      "worst {0:.9f}".format(max(worst(spread[0], other) for other in spread)))

cmds.delete(sandbox_camera)
cmds.delete(sandbox_root)
cmds.autoKeyframe(state=autokey)
check("the sandbox cleaned itself up",
      not cmds.objExists("verify_camera_sandbox")
      and camerarig.existing_camera() is None)

# ======================= the real scene ==================================
root = skeleton.current_root()
bone, problem = camerarig.resolve_bone(skeleton.scene_map(root))
check("camera_bone resolved", bone is not None, problem or str(bone))

before = sample(bone, frames)

message = camerarig.setup(bone, start, end)
print("setup said:", message)

made = camerarig.existing_camera()
check("the camera exists and is marked", made is not None, str(made))
check("it jumped into the bone's transform",
      worst(camerarig.world_matrix(made)[12:],
            camerarig.world_matrix(bone)[12:]) < 1e-6,
      "position gap {0:.9f}".format(
          worst(camerarig.world_matrix(made)[12:],
                camerarig.world_matrix(bone)[12:])))
check("with the measured axes",
      worst(camerarig.offset_between(camerarig.world_matrix(bone),
                                     camerarig.world_matrix(made)),
            camerarig.AXIS_OFFSET) < 1e-4,
      "worst {0:.9f}".format(
          worst(camerarig.offset_between(camerarig.world_matrix(bone),
                                         camerarig.world_matrix(made)),
                camerarig.AXIS_OFFSET)))

after = sample(bone, frames)
drift = worst([v for m in before for v in m], [v for m in after for v in m])
check("the bone's motion is unchanged", drift < 1e-4,
      "worst world-matrix element {0:.9f} over frames {1}".format(drift, frames))

check("the bone is driven by our camera",
      len(camerarig.our_constraints(bone)) == 1,
      str(camerarig.our_constraints(bone)))
check("the bone kept no curves",
      not (cmds.listConnections(bone, type="animCurve") or []))

wanted_offset = camerarig.offset_between(camerarig.world_matrix(bone),
                                        camerarig.world_matrix(made))
for frame in frames:
    cmds.currentTime(frame)
    here = camerarig.offset_between(camerarig.world_matrix(bone),
                                   camerarig.world_matrix(made))
    check("the offset holds at frame {0:g}".format(frame),
          worst(here, wanted_offset) < 1e-4,
          "worst {0:.9f}".format(worst(here, wanted_offset)))
cmds.currentTime(start)

# --- pressing it twice ---------------------------------------------------
again = camerarig.setup(bone, start, end)
print("second press said:", again)
marked = camerarig.our_cameras()
check("a second press leaves exactly one of our cameras", len(marked) == 1,
      "{0} marked: {1}".format(len(marked), marked))
check("and exactly one constraint",
      len(camerarig.our_constraints(bone)) == 1,
      str(len(camerarig.our_constraints(bone))))

after_twice = sample(bone, frames)
drift = worst([v for m in before for v in m],
              [v for m in after_twice for v in m])
check("and the motion still did not move", drift < 1e-3,
      "worst world-matrix element {0:.9f}".format(drift))

passed = sum(1 for _name, ok, _detail in RESULTS if ok)
print("\n{0}/{1} checks passed".format(passed, len(RESULTS)))
