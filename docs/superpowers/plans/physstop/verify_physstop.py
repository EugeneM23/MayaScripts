"""verify_physstop.py - the physical stop in mayapy standalone (never the animator's scene).

& 'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe' docs/superpowers/plans/physstop/verify_physstop.py

The animator's cube rebuilt from three of its own poses (frames 0 and 5, its rest at 9) and run with the
defaults, against the cube frame by frame; the breakdown hit exactly; an arc bent aside with the overshoot
leaving along its tangent; a breakdown tilted aside; re-apply, an edited pose B, one undo, Restore keys; a
parented, pivoted, zxy prop; a spin past 360; an old two-pose transition; the refusals.
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


def world_point(node, point, t):
    return om.MPoint(point) * om.MMatrix(cmds.getAttr(node + ".worldMatrix[0]", time=t))


def key(node, t, values):
    for ch, v in zip(ps.CHANNELS, values):
        cmds.setKeyframe(node, attribute=ch, time=t, value=v)


def channels(node, t):
    tr, ro = ps.pose_at(node, t)
    return tr + ro


def worst(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


cmds.currentUnit(time="film")
cmds.undoInfo(state=True, infinity=True)

# --- The animator's cube from three of its own poses: frame 0, frame 5, its rest keyed at 9.
cube = cmds.polyCube(width=1, height=1, depth=1, name="cube")[0]
cmds.setAttr(cube + ".scale", 4.131199784, 11.644606338, 3.883901969, type="double3")
CH = REF["ch"]
A = tuple(CH[c][0] for c in ps.CHANNELS)
M = tuple(CH[c][5] for c in ps.CHANNELS)
B = (0.0, 5.829040, -32.065960, 2.906870, 0.0, 0.0)
key(cube, 0, A)
key(cube, 5, M)
key(cube, 9, B)
line = ps.apply([cube])[0]
print(line)
times = ps.key_times(cube)
end = times[-1]
gate(times == [float(i) for i in range(int(end) + 1)], "a key on every frame 0..%g" % end)
gate(worst(channels(cube, 0), A) < 1e-6, "frame 0 is pose A")
gate(worst(channels(cube, 5), M) < 1e-6, "frame 5 is pose M exactly (%.1e)" % worst(channels(cube, 5), M))
gate(worst(channels(cube, end), B) < 1e-6, "the last key is pose B")
gate("breakdown at 5: lag" in line and "back" in line, "the breakdown's lag read back: " + line.split("|")[1])

mats = [[m[i * 4:(i + 1) * 4] for i in range(4)] for m in REF["wm"]]
ref_bottom = [tests._mul((0, -0.5, 0, 1), m) for m in mats]
ref_top = [tests._mul((0, 0.5, 0, 1), m) for m in mats]
bottom = [world_point(cube, (0, -0.5, 0), min(f, end)) for f in range(31)]
top = [world_point(cube, (0, 0.5, 0), min(f, end)) for f in range(31)]


def spread(ours, ref):
    return math.sqrt(sum((p.x - r[0]) ** 2 + (p.y - r[1]) ** 2 + (p.z - r[2]) ** 2
                         for p, r in zip(ours, ref)) / len(ref))


eb, et = spread(bottom, ref_bottom), spread(top, ref_top)
gate(eb < 0.8, "the bottom against the cube: rms %.3f cm over frames 0-30 (32 cm of travel)" % eb)
gate(et < 1.2, "the top against the cube: rms %.3f cm" % et)
tilts = [math.degrees(math.atan2(t.z - b.z, t.y - b.y)) for b, t in zip(bottom, top)]
peak = max(range(31), key=lambda f: tilts[f])
gate(6 <= peak <= 10, "the tilt peaks at frame %d, %.1f deg (the cube: frame 8, 24.1 deg)" % (peak, tilts[peak]))
sink = min(p.y for p in bottom)
gate(-3.8 < sink < -2.4, "the bottom sinks to %.2f cm (the cube: -3.10)" % sink)
print("   model tilt:", " ".join("%.1f" % t for t in tilts))
print("   cube  tilt:", " ".join("%.1f" % math.degrees(math.atan2(t[2] - b[2], t[1] - b[1]))
                               for b, t in zip(ref_bottom, ref_top)))

# --- Re-apply with other numbers: the same three keys, a longer settle; an edited B; one undo; Restore.
end1 = ps.key_times(cube)[-1]
ps.apply([cube], {"weight": 2.0})
end2 = ps.key_times(cube)[-1]
memo = ps.remembered(cube)
gate((memo["tA"], memo["tM"], memo["tB"]) == (0, 5, 9) and end2 > end1,
     "re-applied from the same keys; heavier settles later: %g -> %g" % (end1, end2))
gate(worst(channels(cube, 5), M) < 1e-6, "  ... and still stands in M at 5")
cmds.setKeyframe(cube, attribute="translateX", time=end2, value=10.0)
ps.apply([cube])
end3 = ps.key_times(cube)[-1]
gate(abs(cmds.getAttr(cube + ".translateX", time=end3) - 10.0) < 1e-6, "an edited last key became pose B")
cmds.undo()
gate(ps.key_times(cube)[-1] == end2 and ps.remembered(cube)["params"]["weight"] == 2.0, "one undo = one press")
cmds.redo()
ps.restore([cube])
gate(ps.key_times(cube) == [0.0, 5.0, 9.0] and not cmds.attributeQuery(ps.MARKER, node=cube, exists=True),
     "Restore keys: the three keys back, the marker gone")
gate(worst(channels(cube, 5), M) < 1e-6 and abs(cmds.getAttr(cube + ".translateX", time=9) - 10.0) < 1e-6,
     "  ... M as keyed, B as it was last")

# --- An arc bent aside: through M, the overshoot leaving along its tangent at B.
box = cmds.polyCube(width=2, height=10, depth=2, name="arcBox")[0]
key(box, 0, (0, 5, 0, 0, 0, 0))
key(box, 6, (15, 5, -20, 0, 0, 0))
key(box, 12, (0, 5, -40, 0, 0, 0))
print(ps.apply([box], {"sway": 0.0, "weight": 0.2})[0])
p_box = ps.plan(box, {"sway": 0.0, "weight": 0.2})
bm = world_point(box, (0, -5, 0), 6)
gate(abs(bm.x - 15) < 1e-6 and abs(bm.z + 20) < 1e-6, "the bottom passes the breakdown's place at 6: (%.4f, %.4f)"
     % (bm.x, bm.z))
b3 = world_point(box, (0, -5, 0), 3)
arc_t = p_box.transition
the_arc = ps.Arc((0, 0, 0), (15, 0, -20), (0, 0, -40))
off_arc = 0.0
for row in arc_t.rows:
    if row.t <= 12:
        here, there = world_point(box, (0, -5, 0), row.t), the_arc.at(row.p)
        off_arc = max(off_arc, math.hypot(here.x - there[0], here.z - there[2]))
gate(off_arc < 1e-6 and b3.x > 1.0, "  ... on the arc every frame to %.1e cm (only the sink is vertical); at 3 it "
     "already stands %.2f cm aside" % (off_arc, b3.x))
crest = max((r for r in arc_t.rows if r.t > 12), key=lambda r: r.p)
bc = world_point(box, (0, -5, 0), crest.t)
away = om.MVector(bc.x - 0.0, 0.0, bc.z + 40.0)
tan = om.MVector(*ps.Arc((0, 0, 0), (15, 0, -20), (0, 0, -40)).tangent)
tan.y = 0.0
angle = math.degrees(away.angle(tan))
gate(angle < 3.0 and away.length() > 0.2, "the overshoot (%.2f cm at %g) leaves along the arc's tangent at B: "
     "%.2f deg off" % (away.length(), crest.t, angle))

# --- A breakdown tilted aside: the top lags to that side.
side = cmds.polyCube(width=2, height=10, depth=2, name="sideBox")[0]
key(side, 0, (0, 5, 0, 0, 0, 0))
key(side, 5, (0, 5, -15, 0, 0, 15))
key(side, 10, (0, 5, -30, 0, 0, 0))
line = ps.apply([side], {"sway": 0.0})[0]
low, high = world_point(side, (0, -5, 0), 4), world_point(side, (0, 5, 0), 4)
gate("left" in line.split("|")[1] and high.x - low.x < -1.0,
     "a breakdown tilted left lags left: top %.2f cm left of the bottom at 4 (%s)" % (low.x - high.x,
                                                                                   line.split("|")[1].strip()))

# --- A parented, pivoted, zxy prop: Maya's world matrix is the one the script composed, every frame.
holder = cmds.group(empty=True, name="holder")
cmds.setAttr(holder + ".translate", 5, 2, -3, type="double3")
cmds.setAttr(holder + ".rotate", 0, 35, 0, type="double3")
cmds.setAttr(holder + ".scale", 1.5, 1.5, 1.5, type="double3")
prop = cmds.polyCube(width=2, height=6, depth=1, name="prop")[0]
prop = cmds.ls(cmds.parent(prop, holder, relative=True)[0], long=True)[0]
cmds.setAttr(prop + ".rotateOrder", 2)
cmds.setAttr(prop + ".rotatePivot", 0.3, -3.0, 0.1, type="double3")
cmds.setAttr(prop + ".scalePivot", 0.3, -3.0, 0.1, type="double3")
cmds.setAttr(prop + ".rotateAxis", 0, 15, 0, type="double3")
key(prop, 10, (0, 3, 0, 0, 10, 0))
key(prop, 15, (6, 3, 4, 20, 25, 0))
key(prop, 20, (12, 3, 8, 0, 40, 5))
pb = ps.plan(prop)
print(ps.apply([prop])[0])
fixed, order = ps.fixed_parts(prop)
largest = 0.0
for t, tr, ro in pb.frames:
    want = ps.local_matrix(tr, ro, order, fixed) * om.MMatrix(cmds.getAttr(prop + ".parentMatrix[0]", time=t))
    have = om.MMatrix(cmds.getAttr(prop + ".worldMatrix[0]", time=t))
    largest = max(largest, max(abs(want.getElement(i, j) - have.getElement(i, j))
                               for i in range(4) for j in range(4)))
gate(largest < 1e-6, "pivots, rotate axis, zxy, a turned scaled parent: Maya's world = the script's to %.1e" % largest)
gate(worst(channels(prop, 15), (6, 3, 4, 20, 25, 0)) < 1e-6, "  ... and the prop stands in its breakdown at 15")

# --- A spin past 360: the eulers stay on the winding the keys asked for.
spin = cmds.polyCube(name="spin")[0]
key(spin, 0, (0, 0.5, 0, 0, 350, 0))
key(spin, 4, (0, 0.5, -5, 0, 360, 0))
key(spin, 8, (0, 0.5, -10, 0, 370, 0))
ps.apply([spin])
ys = [cmds.getAttr(spin + ".rotateY", time=t) for t in ps.key_times(spin)]
gate(max(abs(b - a) for a, b in zip(ys, ys[1:])) < 30 and abs(ys[-1] - 370) < 1e-6
     and abs(cmds.getAttr(spin + ".rotateY", time=4) - 360) < 1e-6,
     "no euler jumps on a 350 -> 360 -> 370 spin (rotateY %.1f..%.1f)" % (min(ys), max(ys)))

# --- An old two-pose transition: refused until Restore, which puts its two keys back.
old = cmds.polyCube(name="old")[0]
for f in range(0, 21):
    key(old, f, (0, 0.5, -f, 0, 0, 0))
cmds.addAttr(old, longName=ps.MARKER, dataType="string")
cmds.setAttr(old + "." + ps.MARKER, json.dumps({"tA": 0, "tB": 9, "tE": 20, "params": {}}), type="string")
line = ps.apply([old])[0]
gate("Restore keys first" in line, "an old two-pose transition is refused: " + line)
ps.restore([old])
gate(ps.key_times(old) == [0.0, 9.0], "  ... and Restore puts its two keys back")

# --- Refusals and notes.
two = cmds.polyCube(name="two")[0]
key(two, 0, (0, 0, 0, 0, 0, 0))
key(two, 8, (0, 0, -10, 0, 0, 0))
line = ps.apply([two])[0]
gate(line.endswith("needs three keys on translate/rotate - from, breakdown, to - has 2"), "two keys: " + line)
locked = cmds.polyCube(name="locked")[0]
for t, v in ((0, 0), (4, -10), (8, -20)):
    cmds.setKeyframe(locked, attribute="translateZ", time=t, value=v)
cmds.setAttr(locked + ".rotateX", lock=True)
line = ps.apply([locked])[0]
gate("not written (locked or driven): rotateX" in line, "a locked channel is named")
bare = cmds.group(empty=True, name="bare")
for t, v in ((0, 0), (4, -10), (8, -20)):
    cmds.setKeyframe(bare, attribute="translateZ", time=t, value=v)
line = ps.apply([bare])[0]
gate("no geometry" in line and ps.key_times(bare)[-1] > 8, "an empty transform works and says so")
small = cmds.polyCube(name="small")[0]
for t, v in ((0, 0), (4, -20), (8, -40)):
    cmds.setKeyframe(small, attribute="translateZ", time=t, value=v)
cmds.setKeyframe(small, attribute="rotateX", time=4, value=20)
ps.apply([small])
largest = max(abs(cmds.getAttr(small + ".rotateX", time=t)) for t in ps.key_times(small))
gate(largest < 90.0, "a 1 cm cube flying 40 cm with a 20 deg breakdown lag stays sane: at most %.1f deg" % largest)

print("%d gates, %s" % (COUNT[0], "all passed" if not FAILED else "FAILED: %s" % FAILED))
maya.standalone.uninitialize()
