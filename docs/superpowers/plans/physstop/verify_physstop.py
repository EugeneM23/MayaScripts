"""verify_physstop.py - the physical stop in mayapy standalone (never the animator's scene).

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/physstop/verify_physstop.py

The animator's cube rebuilt from two keys and run with the defaults, against the cube frame by frame;
re-apply, an edited pose B, one undo, Restore keys; a parented, pivoted, zxy prop; a spin past 360;
the refusals.
"""
import importlib.util
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds
import maya.api.OpenMaya as om

tests = load("physstop_tests", os.path.join(REPO, "tests", "test_physstop.py"))
ps = load("skeldar_physstop", os.path.join(HERE, "skeldar_physstop.py"))
with open(os.path.join(HERE, "cube_reference.json")) as f:
    REF = json.load(f)
FAILED = []
COUNT = [0]


def gate(ok, text):
    COUNT[0] += 1
    print("gate %2d %s  %s" % (COUNT[0], "ok  " if ok else "FAIL", text))
    if not ok:
        FAILED.append(COUNT[0])


def ends(node, frames):
    """The bottom and top centre of a unit cube's mesh in world, on each frame."""
    out = []
    for f in frames:
        m = om.MMatrix(cmds.getAttr(node + ".worldMatrix[0]", time=f))
        out.append((om.MPoint(0, -0.5, 0) * m, om.MPoint(0, 0.5, 0) * m))
    return out


cmds.currentUnit(time="film")
cmds.undoInfo(state=True, infinity=True)

# --- The animator's cube: A at f0, B keyed at f9 (it passed its target at f9.1), the cube's own rest pose.
cube = cmds.polyCube(width=1, height=1, depth=1, name="cube")[0]
cmds.setAttr(cube + ".scale", 4.131199784, 11.644606338, 3.883901969, type="double3")
A = (0.0, 5.837090, 0.0, 0.0, 0.0, 0.0)
B = (0.0, 5.829040, -32.065960, 2.906870, 0.0, 0.0)
for ch, a, b in zip(ps.CHANNELS, A, B):
    cmds.setKeyframe(cube, attribute=ch, time=0, value=a)
    cmds.setKeyframe(cube, attribute=ch, time=9, value=b)

lines = ps.apply([cube])
print(lines[0])
times = ps.key_times(cube)
end = times[-1]
gate(times == [float(i) for i in range(int(end) + 1)], "a key on every frame 0..%g" % end)
first, last = ps.pose_at(cube, 0), ps.pose_at(cube, end)
gate(max(abs(x - y) for x, y in zip(first[0] + first[1], A)) < 1e-6, "frame 0 is pose A")
gate(max(abs(x - y) for x, y in zip(last[0] + last[1], B)) < 1e-6, "the last key is pose B")
pts = ends(cube, range(int(end) + 1))
fixed, _ = ps.fixed_parts(cube)
at_b = om.MPoint(0, -0.5, 0) * ps.local_matrix(B[:3], B[3:], 0, fixed)
gate(abs(pts[9][0].z - at_b.z) < 1e-4,
     "the bottom passes B's place on the path at f9: z %.5f / %.5f" % (pts[9][0].z, at_b.z))

mats = [[m[i * 4:(i + 1) * 4] for i in range(4)] for m in REF["wm"]]
ref_bottom = [tests._mul((0, -0.5, 0, 1), m) for m in mats]
ref_top = [tests._mul((0, 0.5, 0, 1), m) for m in mats]


def point(f, which):
    return pts[min(f, len(pts) - 1)][which]


def spread(ref, which):
    return math.sqrt(sum((point(f, which).x - ref[f][0]) ** 2 + (point(f, which).y - ref[f][1]) ** 2
                         + (point(f, which).z - ref[f][2]) ** 2 for f in range(31)) / 31)


eb, et = spread(ref_bottom, 0), spread(ref_top, 1)
gate(eb < 1.0, "the bottom against the cube: rms %.3f cm over frames 0-30 (32 cm of travel)" % eb)
gate(et < 1.5, "the top against the cube: rms %.3f cm" % et)
tilts = [math.degrees(math.atan2(point(f, 1).z - point(f, 0).z, point(f, 1).y - point(f, 0).y)) for f in range(31)]
peak = max(range(31), key=lambda f: tilts[f])
gate(6 <= peak <= 10, "the tilt peaks at frame %d, %.1f deg (the cube: frame 8, 24.1 deg)" % (peak, tilts[peak]))
sink = min(point(f, 0).y for f in range(31))
gate(-3.8 < sink < -2.4, "the bottom sinks to %.2f cm (the cube: -3.10)" % sink)
print("   model tilt by frame:", " ".join("%.1f" % t for t in tilts))
print("   cube  tilt by frame:", " ".join("%.1f" % math.degrees(math.atan2(t[2] - b[2], t[1] - b[1]))
                                         for b, t in zip(ref_bottom, ref_top)))

# --- Re-apply with other numbers: the same two keys, a longer settle.
end1 = ps.key_times(cube)[-1]
ps.apply([cube], {"weight": 2.0})
end2 = ps.key_times(cube)[-1]
memo = ps.remembered(cube)
gate(memo["tA"] == 0 and memo["tB"] == 9 and end2 > end1,
     "re-applied from the same keys; heavier settles later: %g -> %g" % (end1, end2))
cmds.setKeyframe(cube, attribute="translateX", time=end2, value=10.0)
ps.apply([cube])
end3 = ps.key_times(cube)[-1]
gate(abs(cmds.getAttr(cube + ".translateX", time=end3) - 10.0) < 1e-6 and ps.remembered(cube)["tB"] == 9,
     "an edited last key became pose B")
cmds.undo()
gate(ps.key_times(cube)[-1] == end2 and abs(cmds.getAttr(cube + ".translateX", time=end2) - 10.0) < 1e-6
     and ps.remembered(cube)["params"]["weight"] == 2.0, "one undo = one press")
cmds.redo()
ps.restore([cube])
gate(ps.key_times(cube) == [0.0, 9.0] and not cmds.attributeQuery(ps.MARKER, node=cube, exists=True),
     "Restore keys: the two keys back, the marker gone")
gate(abs(cmds.getAttr(cube + ".translateX", time=9) - 10.0) < 1e-6
     and abs(cmds.getAttr(cube + ".translateZ", time=9) - B[2]) < 1e-6, "  ... pose B as it was last")

# --- A parented, pivoted, zxy prop: Maya's world matrix is the one the script composed, every frame.
holder = cmds.group(empty=True, name="holder")
cmds.setAttr(holder + ".translate", 5, 2, -3, type="double3")
cmds.setAttr(holder + ".rotate", 0, 35, 0, type="double3")
cmds.setAttr(holder + ".scale", 1.5, 1.5, 1.5, type="double3")
prop = cmds.polyCube(width=2, height=6, depth=1, name="prop")[0]
prop = cmds.parent(prop, holder, relative=True)[0]
prop = cmds.ls(prop, long=True)[0]
cmds.setAttr(prop + ".rotateOrder", 2)
cmds.setAttr(prop + ".rotatePivot", 0.3, -3.0, 0.1, type="double3")
cmds.setAttr(prop + ".scalePivot", 0.3, -3.0, 0.1, type="double3")
cmds.setAttr(prop + ".rotateAxis", 0, 15, 0, type="double3")
for ch, a, b in zip(ps.CHANNELS, (0, 3, 0, 0, 10, 0), (12, 3, 8, 0, 40, 5)):
    cmds.setKeyframe(prop, attribute=ch, time=10, value=a)
    cmds.setKeyframe(prop, attribute=ch, time=20, value=b)
pb = ps.plan(prop)
print(ps.apply([prop])[0])
fixed, order = ps.fixed_parts(prop)
worst = 0.0
for t, tr, ro in pb.frames:
    want = ps.local_matrix(tr, ro, order, fixed) * om.MMatrix(cmds.getAttr(prop + ".parentMatrix[0]", time=t))
    have = om.MMatrix(cmds.getAttr(prop + ".worldMatrix[0]", time=t))
    worst = max(worst, max(abs(want.getElement(i, j) - have.getElement(i, j)) for i in range(4) for j in range(4)))
gate(worst < 1e-6, "pivots, rotate axis, zxy, a turned scaled parent: Maya's world = the script's to %.1e" % worst)
low = om.MPoint(0, -3, 0)
top = om.MPoint(0, 3, 0)
m15 = om.MMatrix(cmds.getAttr(prop + ".worldMatrix[0]", time=15))
m10 = om.MMatrix(cmds.getAttr(prop + ".worldMatrix[0]", time=10))
m20 = om.MMatrix(cmds.getAttr(prop + ".worldMatrix[0]", time=pb.transition.end))
motion = (low * m20) - (low * m10)
motion.y = 0.0
lean = (top * m15) - (low * m15)
gate(lean * motion.normal() < 0, "mid-way the prop's top leans back against its motion (%.2f)" % (lean * motion.normal()))

# --- A spin past 360: the eulers stay on the winding the keys asked for.
spin = cmds.polyCube(name="spin")[0]
for ch, a, b in zip(ps.CHANNELS, (0, 0.5, 0, 0, 350, 0), (0, 0.5, -10, 0, 370, 0)):
    cmds.setKeyframe(spin, attribute=ch, time=0, value=a)
    cmds.setKeyframe(spin, attribute=ch, time=8, value=b)
ps.apply([spin])
ys = [cmds.getAttr(spin + ".rotateY", time=t) for t in ps.key_times(spin)]
gate(max(abs(b - a) for a, b in zip(ys, ys[1:])) < 30 and abs(ys[-1] - 370) < 1e-6,
     "no euler jumps on a 350 -> 370 spin (rotateY %.1f..%.1f)" % (min(ys), max(ys)))

# --- Refusals and notes.
lone = cmds.polyCube(name="lone")[0]
cmds.setKeyframe(lone, attribute="translateX", time=0, value=0)
line = ps.apply([lone])[0]
gate(line.endswith("needs two keys on translate/rotate - has 1"), "one key: " + line)
locked = cmds.polyCube(name="locked")[0]
for t, v in ((0, 0), (8, -20)):
    cmds.setKeyframe(locked, attribute="translateZ", time=t, value=v)
cmds.setAttr(locked + ".rotateX", lock=True)
line = ps.apply([locked])[0]
gate("not written (locked or driven): rotateX" in line, "a locked channel is named: " + line)
bare = cmds.group(empty=True, name="bare")
for t, v in ((0, 0), (8, -20)):
    cmds.setKeyframe(bare, attribute="translateZ", time=t, value=v)
line = ps.apply([bare])[0]
gate("no geometry" in line and ps.key_times(bare)[-1] > 8, "an empty transform works and says so: " + line)
small = cmds.polyCube(name="small")[0]
for t, v in ((0, 0), (8, -40)):
    cmds.setKeyframe(small, attribute="translateZ", time=t, value=v)
ps.apply([small])
worst = max(abs(cmds.getAttr(small + ".rotateX", time=t)) for t in ps.key_times(small))
gate(worst < 60.0, "a 1 cm cube flying 40 cm in 8 frames tilts at most %.1f deg, not over" % worst)

print("%d gates, %s" % (COUNT[0], "all passed" if not FAILED else "FAILED: %s" % FAILED))
maya.standalone.uninitialize()
