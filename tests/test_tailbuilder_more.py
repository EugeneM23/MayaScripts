"""maya_tailbuilder - the scene half on a fake scene (tests/test_tailbuilder.py proves the model and
the card): which keys a tail runs through, what refuses, the plan, the keys Apply writes and the
marker, re-applying from the marker, Restore keys, the locked and driven channels, the box, the
selection. A small keyed scene in a fake cmds (linear between keys); OpenMaya does the matrices.
The live half is docs/superpowers/plans/physstop/verify_physstop.py."""

import bisect
import contextlib
import io
import json
import unittest

import maya_tailbuilder as ps

IDENTITY = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]


class Scene(object):
    """Keyed channels (linear between keys, held outside them), string attributes, locks, drivers,
    shapes with boxes, the selection, undo chunks."""

    def __init__(self):
        self.keys = {}
        self.attrs = {}
        self.locked = set()
        self.drivers = {}
        self.curves = set()
        self.referenced = set()
        self.shapes = {}             # transform: [(shape, box min, box max, intermediate)]
        self.transforms = set()
        self.selection = []
        self.chunks = []
        self.tangents = []
        self.parent_matrix = {}      # node: flat 16
        self.time = 0.0

    # --- building it
    def node(self, name, keys=None, box=((-5.0, 0.0, -5.0), (5.0, 10.0, 5.0))):
        self.transforms.add(name)
        for ch, pairs in (keys or {}).items():
            self.keys[name + "." + ch] = dict(pairs)
        if box:
            self.shapes[name] = [(name + "|" + name.strip("|") + "Shape", box[0], box[1], False)]
        return name

    def value(self, plug, t):
        keys = self.keys.get(plug)
        if not keys:
            return 0.0
        times = sorted(keys)
        if t <= times[0]:
            return keys[times[0]]
        if t >= times[-1]:
            return keys[times[-1]]
        i = bisect.bisect_right(times, t)
        a, b = times[i - 1], times[i]
        return keys[a] + (keys[b] - keys[a]) * (t - a) / (b - a)

    # --- cmds
    def keyframe(self, plug, query=False, timeChange=False, time=None, **_kw):
        times = sorted(self.keys.get(plug, {}))
        if time is not None:
            return [t for t in times if time[0] - 1e-9 <= t <= time[1] + 1e-9]
        return times

    def setKeyframe(self, node, attribute=None, time=None, value=None, **_kw):  # noqa: N802
        self.keys.setdefault(node + "." + attribute, {})[round(float(time), 6)] = float(value)

    def keyTangent(self, node, attribute=None, time=None, **kw):  # noqa: N802
        self.tangents.append((node, attribute, time, kw))

    def cutKey(self, node, attribute=None, time=None, clear=False):  # noqa: N802
        keys = self.keys.get(node + "." + attribute, {})
        for t in [t for t in keys if time[0] <= t <= time[1]]:
            del keys[t]

    def getAttr(self, plug, time=None, lock=False, **_kw):     # noqa: N802
        if lock:
            return plug in self.locked
        node, attr = plug.rsplit(".", 1)
        if attr in ps.CHANNELS:
            return self.value(plug, self.time if time is None else time)
        if attr in ps.IDENTITY_FIXED:
            return [tuple(ps.IDENTITY_FIXED[attr])]
        if attr == "rotateOrder":
            return 0
        if attr == "parentMatrix[0]":
            return list(self.parent_matrix.get(node, IDENTITY))
        if attr in ("worldInverseMatrix[0]", "worldMatrix[0]"):
            return list(IDENTITY)
        for shapes in self.shapes.values():
            for shape, low, high, intermediate in shapes:
                if shape == node:
                    return {"intermediateObject": intermediate, "boundingBoxMin": [low],
                            "boundingBoxMax": [high]}[attr]
        return self.attrs[plug]

    def attributeQuery(self, name, node=None, exists=False):  # noqa: N802
        return (node + "." + name) in self.attrs

    def addAttr(self, node, longName=None, dataType=None):    # noqa: N802
        self.attrs[node + "." + longName] = ""

    def setAttr(self, plug, value, type=None):                # noqa: N802,A002
        self.attrs[plug] = value

    def deleteAttr(self, plug):                               # noqa: N802
        del self.attrs[plug]

    def listConnections(self, plug, **_kw):                   # noqa: N802
        source = self.drivers.get(plug)
        return [source] if source else []

    def ls(self, *args, **kw):
        if kw.get("selection"):
            return list(self.selection)
        if kw.get("type") == "animCurve":
            return [a for a in args if a in self.curves]
        return list(args)

    def referenceQuery(self, node, isNodeReferenced=False):   # noqa: N802
        return node in self.referenced

    def listRelatives(self, node, allDescendents=False, parent=False, **_kw):  # noqa: N802
        if parent:
            for owner, shapes in self.shapes.items():
                if node in [s[0] for s in shapes]:
                    return [owner]
            return [node.rsplit("|", 1)[0]]
        return [s[0] for s in self.shapes.get(node, [])]

    def objectType(self, node, isAType=None):                 # noqa: N802
        shapes = [s[0] for group in self.shapes.values() for s in group]
        if isAType == "shape":
            return node in shapes
        if isAType == "transform":
            return node in self.transforms
        return False

    def undoInfo(self, openChunk=False, closeChunk=False, chunkName=None):  # noqa: N802
        self.chunks.append("open %s" % chunkName if openChunk else "close")

    #  the card is closed: a press reads the memory and answers its line
    def text(self, name, exists=False, **_kw):
        return False

    def floatSliderGrp(self, name, exists=False, **_kw):     # noqa: N802
        return False

    def optionVar(self, exists=None, **_kw):                  # noqa: N802
        return False


#  A ball that travels 100 cm along X through a breakdown raised 10 cm at frame 5 (an arc coming in
#  from above), every channel keyed at 0, 5, 10.
BALL = {"translateX": {0.0: 0.0, 5.0: 50.0, 10.0: 100.0},
        "translateY": {0.0: 0.0, 5.0: 10.0, 10.0: 0.0},
        "translateZ": {0.0: 0.0, 5.0: 0.0, 10.0: 0.0},
        "rotateX": {0.0: 0.0, 5.0: 0.0, 10.0: 0.0},
        "rotateY": {0.0: 0.0, 5.0: 0.0, 10.0: 0.0},
        "rotateZ": {0.0: 0.0, 5.0: 0.0, 10.0: 0.0}}


class Base(unittest.TestCase):

    def setUp(self):
        self.scene = Scene()
        self.ball = self.scene.node("|ball", BALL)
        saved = ps._cmds
        ps._cmds = lambda: self.scene
        self.addCleanup(setattr, ps, "_cmds", saved)

    def pose(self, t):
        return ps.pose_at(self.ball, t)

    def assertNear(self, a, b, tol=1e-6):                     # noqa: N802
        for x, y in zip(a, b):
            self.assertAlmostEqual(x, y, delta=tol)


class Source(Base):

    def test_key_times_merge_every_channel(self):
        self.scene.keys["|ball.rotateY"][7.0] = 3.0
        self.assertEqual(ps.key_times(self.ball), [0.0, 5.0, 7.0, 10.0])

    def test_the_last_three_keys(self):
        self.assertEqual(ps.source(self.ball), (0.0, 5.0, 10.0, 10.0))
        self.scene.keys["|ball.translateX"][-10.0] = 5.0
        self.assertEqual(ps.source(self.ball), (0.0, 5.0, 10.0, 10.0))

    def test_two_keys_are_refused_by_name(self):
        for plug in list(self.scene.keys):
            self.scene.keys[plug].pop(5.0)
        with self.assertRaises(ps.Refusal) as caught:
            ps.source(self.ball)
        self.assertEqual(str(caught.exception), "ball: needs three keys on translate/rotate - "
                                                "from, breakdown, to - has 2")

    def test_keys_closer_than_a_frame_are_refused(self):
        self.scene.keys["|ball.translateX"][9.5] = 99.0
        with self.assertRaises(ps.Refusal) as caught:
            ps.source(self.ball)
        self.assertIn("less than a frame apart", str(caught.exception))

    def test_the_marker_is_read_and_a_broken_one_is_none(self):
        self.assertIsNone(ps.remembered(self.ball))
        self.scene.attrs["|ball." + ps.MARKER] = json.dumps({"tA": 0, "tE": 10})
        self.assertEqual(ps.remembered(self.ball), {"tA": 0, "tE": 10})
        self.scene.attrs["|ball." + ps.MARKER] = "{broken"
        self.assertIsNone(ps.remembered(self.ball))

    def test_a_marker_whose_last_key_moved_is_not_ours(self):
        self.assertTrue(ps._ours({"tE": 10.0}, [0.0, 10.0]))
        self.assertFalse(ps._ours({"tE": 12.0}, [0.0, 10.0]))
        self.assertFalse(ps._ours(None, [0.0, 10.0]))
        self.assertFalse(ps._ours({"tE": 10.0}, []))

    def test_a_two_pose_marker_asks_for_restore_first(self):
        self.scene.attrs["|ball." + ps.MARKER] = json.dumps({"tA": 0, "tB": 5, "tE": 10})
        with self.assertRaises(ps.Refusal) as caught:
            ps.source(self.ball)
        self.assertIn("two-pose transition", str(caught.exception))

    def test_poses_are_read_off_the_curves(self):
        self.assertEqual(self.pose(5.0), ((50.0, 10.0, 0.0), (0.0, 0.0, 0.0)))
        self.assertEqual(self.pose(2.5), ((25.0, 5.0, 0.0), (0.0, 0.0, 0.0)))


class Channels(Base):

    def test_locked_and_driven_channels_are_blocked_a_curve_is_not(self):
        self.scene.locked.add("|ball.rotateY")
        self.scene.drivers["|ball.rotateZ"] = "pairBlend1"
        self.scene.drivers["|ball.translateZ"] = "ball_translateZ"
        self.scene.curves.add("ball_translateZ")
        self.assertEqual(ps.blocked(self.ball), ["rotateY", "rotateZ"])

    def test_the_fixed_parts_and_the_order(self):
        fixed, order = ps.fixed_parts(self.ball)
        self.assertEqual(fixed, ps.IDENTITY_FIXED)
        self.assertEqual(order, 0)

    def test_the_box_of_the_visible_shapes(self):
        self.scene.shapes["|ball"].append(("|ball|orig", (-50.0, -50.0, -50.0),
                                           (50.0, 50.0, 50.0), True))
        low, high = ps.object_box(self.ball)
        self.assertNear(low, (-5.0, 0.0, -5.0))
        self.assertNear(high, (5.0, 10.0, 5.0))

    def test_no_shape_no_box(self):
        self.scene.shapes["|ball"] = []
        self.assertIsNone(ps.object_box(self.ball))

    def test_the_selection_s_transforms_once_a_shape_naming_its_own(self):
        self.scene.node("|cube", BALL)
        self.scene.selection = ["|ball|ballShape", "|ball", "time1", "|cube"]
        self.assertEqual(ps.selected(), ["|ball", "|cube"])


class Plan(Base):

    def test_a_and_m_and_b_are_hit_exactly(self):
        p = ps.plan(self.ball)
        self.assertEqual((p.t_a, p.t_m, p.t_b), (0.0, 5.0, 10.0))
        self.assertEqual(p.frames[0][0], 0.0)
        self.assertNear(p.frames[0][1], (0.0, 0.0, 0.0))
        at_m = [f for f in p.frames if abs(f[0] - 5.0) < 1e-9][0]
        self.assertNear(at_m[1], (50.0, 10.0, 0.0), 1e-5)
        self.assertNear(at_m[2], (0.0, 0.0, 0.0), 1e-5)
        last = p.frames[-1]
        self.assertEqual(last[0], p.transition.end)
        self.assertNear(last[1], (100.0, 0.0, 0.0), 1e-5)
        self.assertGreater(p.transition.end, 10.0)
        self.assertAlmostEqual(p.height, 10.0)
        self.assertEqual(p.notes, [])

    def test_it_overshoots_b_along_the_travel(self):
        p = ps.plan(self.ball, {"overshoot": 10.0})
        past = max(f[1][0] for f in p.frames)
        self.assertGreater(past, 100.0)
        self.assertEqual(p.info["entry"].split()[-1], "up")

    def test_a_referenced_node_is_refused(self):
        self.scene.referenced.add(self.ball)
        with self.assertRaises(ps.Refusal) as caught:
            ps.plan(self.ball)
        self.assertEqual(str(caught.exception), "ball: referenced - not touched")

    def test_no_geometry_takes_the_pivot_and_says_so(self):
        self.scene.shapes["|ball"] = []
        p = ps.plan(self.ball)
        self.assertEqual(p.height, ps.FALLBACK_HEIGHT)
        self.assertIn("no geometry", p.notes[0])

    def test_a_parent_carries_the_world(self):
        """A parent moved 20 cm along Z: the channels the plan writes are the same local ones."""
        alone = ps.plan(self.ball).frames
        self.scene.parent_matrix["|ball"] = IDENTITY[:14] + [20.0, 1.0]
        moved = ps.plan(self.ball).frames
        self.assertEqual(len(alone), len(moved))
        for a, b in zip(alone, moved):
            self.assertNear(a[1], b[1], 1e-5)


class Write(Base):

    def apply(self, **given):
        return ps.apply([self.ball], given or None)

    def test_apply_keys_every_frame_keeps_a_and_leaves_the_marker(self):
        line = self.apply()[0]
        memo = json.loads(self.scene.attrs["|ball." + ps.MARKER])
        self.assertEqual((memo["tA"], memo["tM"], memo["tB"]), (0.0, 5.0, 10.0))
        self.assertEqual(memo["params"], ps.params())
        times = ps.key_times(self.ball)
        self.assertEqual(times[0], 0.0)
        self.assertEqual(times[-1], memo["tE"])
        self.assertEqual(times[:12], [float(t) for t in range(12)])
        self.assertNear(self.pose(5.0)[0], (50.0, 10.0, 0.0), 1e-5)
        self.assertNear(self.pose(memo["tE"])[0], (100.0, 0.0, 0.0), 1e-5)
        self.assertEqual(self.scene.chunks, ["open skeldarPhysStop", "close"])
        self.assertTrue(line.startswith("ball: frames 0-%g | breakdown at 5: " % memo["tE"]))
        self.assertIn("settles %g frames after B" % (memo["tE"] - 10.0), line)
        outs = [t for t in self.scene.tangents if t[2] == (0.0, 0.0)]
        self.assertEqual(len(outs), 6)
        self.assertTrue(all(t[3] == {"outTangentType": "auto"} for t in outs))

    def test_a_tail_is_read_again_from_its_marker(self):
        first = self.apply()
        frames = dict((t, self.pose(t)) for t in ps.key_times(self.ball))
        self.assertEqual(ps.source(self.ball)[:3], (0.0, 5.0, 10.0))
        self.assertEqual(ps.selection_line([self.ball]),
                         "ball: a tail 0-%g, M at 5, B at 10" % ps.key_times(self.ball)[-1])
        again = self.apply()
        self.assertEqual(first, again)
        for t, pose in frames.items():
            self.assertNear(self.pose(t)[0], pose[0], 1e-6)

    def test_a_locked_channel_is_left_and_named(self):
        self.scene.locked.add("|ball.rotateY")
        before = dict(self.scene.keys["|ball.rotateY"])
        line = self.apply()[0]
        self.assertEqual(self.scene.keys["|ball.rotateY"], before)
        self.assertIn("not written (locked or driven): rotateY", line)

    def test_every_channel_blocked_is_refused(self):
        self.scene.locked.update("|ball." + ch for ch in ps.CHANNELS)
        lines = self.apply()
        self.assertEqual(lines, ["ball: every translate/rotate channel is locked or driven"])
        self.assertNotIn("|ball." + ps.MARKER, self.scene.attrs)
        self.assertEqual(self.scene.chunks, ["open skeldarPhysStop", "close"])

    def test_one_refusal_does_not_stop_the_others(self):
        self.scene.node("|stub", {"translateX": {0.0: 0.0, 4.0: 1.0}})
        lines = ps.apply(["|stub", self.ball])
        self.assertIn("needs three keys", lines[0])
        self.assertTrue(lines[1].startswith("ball: frames"))

    def test_a_key_at_a_is_set_when_a_channel_has_none_there(self):
        del self.scene.keys["|ball.rotateX"][0.0]
        self.apply()
        self.assertIn(0.0, self.scene.keys["|ball.rotateX"])

    def test_the_chunk_closes_when_the_press_fails(self):
        saved = ps.plan
        ps.plan = lambda node, given=None: 1 / 0
        try:
            with self.assertRaises(ZeroDivisionError):
                self.apply()
        finally:
            ps.plan = saved
        self.assertEqual(self.scene.chunks, ["open skeldarPhysStop", "close"])


class Restore(Base):

    def test_back_to_the_three_keys_and_no_marker(self):
        ps.apply([self.ball])
        lines = ps.restore([self.ball])
        self.assertEqual(lines, ["ball: back to its keys at 0, 5, 10"])
        self.assertEqual(ps.key_times(self.ball), [0.0, 5.0, 10.0])
        self.assertNear(self.pose(5.0)[0], (50.0, 10.0, 0.0), 1e-5)
        self.assertNear(self.pose(10.0)[0], (100.0, 0.0, 0.0), 1e-5)
        self.assertNotIn("|ball." + ps.MARKER, self.scene.attrs)
        self.assertEqual(self.scene.chunks[-2:], ["open skeldarPhysStopRestore", "close"])

    def test_an_object_with_no_tail(self):
        self.assertEqual(ps.restore([self.ball]),
                         ["ball: no transition of this script to restore"])

    def test_a_two_pose_tail_puts_back_its_two_keys(self):
        self.scene.keys = {"|ball.translateX": {0.0: 0.0, 3.0: 60.0, 8.0: 100.0}}
        self.scene.attrs["|ball." + ps.MARKER] = json.dumps({"tA": 0.0, "tB": 3.0, "tE": 8.0})
        self.assertEqual(ps.restore([self.ball]), ["ball: back to its keys at 0, 3"])
        self.assertEqual(self.scene.keys["|ball.translateX"], {0.0: 0.0, 3.0: 100.0})

    def test_a_locked_channel_is_not_cut(self):
        ps.apply([self.ball])
        self.scene.locked.add("|ball.translateZ")
        dense = len(self.scene.keys["|ball.translateZ"])
        ps.restore([self.ball])
        self.assertEqual(len(self.scene.keys["|ball.translateZ"]), dense)


class Edges(Base):

    def test_a_slow_last_stretch_holds_the_overshoot_and_says_so(self):
        self.scene.keys = {"|ball.translateX": {0.0: 0.0, 5.0: 50.0, 40.0: 100.0}}
        p = ps.plan(self.ball, {"overshoot": 20.0})
        self.assertTrue(p.transition.clamped)
        self.assertTrue(p.notes[0].startswith("overshoot held to "), p.notes)
        self.assertIn("overshoot held to", ps.describe(p, []))

    def test_a_refresh_that_cannot_read_the_selection_leaves_the_subtitle(self):
        written = []

        class Card(object):
            def text(self, name, exists=False, edit=False, label=None, **_kw):
                if exists:
                    return True
                written.append(label)

        saved = (ps._cmds, ps.selected)
        ps._cmds = lambda: Card()

        def broken():
            raise RuntimeError("no scene")
        ps.selected = broken
        try:
            ps.refresh()
            self.assertEqual(written, [])
            ps.selected = lambda: []
            ps.refresh()
            self.assertEqual(written, [ps.NOTHING])
        finally:
            ps._cmds, ps.selected = saved

    def test_a_job_maya_will_not_kill_does_not_stop_the_start(self):
        made = []

        class Card(object):
            def scriptJob(self, exists=None, kill=None, force=False, event=None,  # noqa: N802
                          parent=None):
                if exists is not None:
                    raise RuntimeError("no such job")
                made.append((event[0], parent))
                return 5

        saved = (ps._cmds, dict(ps.JOB))
        ps._cmds = lambda: Card()
        ps.JOB.clear()
        ps.JOB[""] = 4
        try:
            ps.start()
            self.assertEqual(ps.JOB[""], 5)
        finally:
            ps._cmds = saved[0]
            ps.JOB.clear()
            ps.JOB.update(saved[1])
        self.assertEqual(made, [("SelectionChanged", ps.STATUS)])


class MovingParent(Base):
    """Fixed 2026-10-27 (`_pose_b`), the bug as it was: under a parent that MOVES, a tail's last key holds pose B's WORLD
    place in the parent's space at the END frame, and a re-run reads it back as pose B in the
    parent's space at B's frame (`plan`: `pose_at(node, b_time)` placed with `parent_at(t_b)`;
    `restore`: B's key from `pose_at(node, memo["tE"])`). Every slider release re-applies, so B
    walks by the parent's travel between B and the end on every release (46 cm a press here), and
    Restore keys gives B back moved. Should: a re-run reproduces the tail; Restore gives B's own
    key back."""

    def setUp(self):
        Base.setUp(self)
        scene = self.scene
        real = Scene.getAttr

        def getAttr(plug, time=None, lock=False, **kw):                 # noqa: N802
            if plug.endswith(".parentMatrix[0]"):
                t = scene.time if time is None else time
                return IDENTITY[:12] + [0.0, 0.0, 2.0 * t, 1.0]        # 2 cm a frame along Z
            return real(scene, plug, time=time, lock=lock, **kw)
        scene.getAttr = getAttr

    def test_a_re_run_under_a_moving_parent_reproduces_the_tail(self):
        ps.apply([self.ball])
        end = ps.key_times(self.ball)[-1]
        before = self.pose(end)
        ps.apply([self.ball])
        self.assertNear(self.pose(ps.key_times(self.ball)[-1])[0], before[0], 1e-4)

    def test_restore_under_a_moving_parent_gives_b_s_own_key_back(self):
        ps.apply([self.ball])
        ps.restore([self.ball])
        self.assertNear(self.pose(10.0)[0], (100.0, 0.0, 0.0), 1e-4)


class CardPresses(Base):

    def test_the_buttons_press_their_functions(self):
        made = {}

        class Card(object):
            def button(self, name, command=None, **kw):
                made[name] = command
                return name

        saved = ps._cmds
        ps._cmds = lambda: Card()
        pressed = []
        try:
            for name, press in ((ps.APPLY_BTN, "apply"), (ps.RESTORE_BTN, "restore")):
                ps._button(name, name, "primary", "wave-sine", "tip",
                           lambda p=press: pressed.append(p))
                made[name]()
        finally:
            ps._cmds = saved
            import maya_hubstyle
            maya_hubstyle.take_marks()
        self.assertEqual(pressed, ["apply", "restore"])

    def test_a_press_on_a_real_tail_and_restore(self):
        self.scene.selection = [self.ball]

        with contextlib.redirect_stdout(io.StringIO()):
            line = ps.press_apply()
        self.assertTrue(line.startswith("ball: frames 0-"), line)
        self.assertEqual(ps.press_restore(), "ball: back to its keys at 0, 5, 10")

    def test_show_window_opens_the_hub_on_its_section(self):
        import maya_hub
        asked = []
        saved = maya_hub.show
        maya_hub.show = lambda key=None: asked.append(key) or "hub"
        try:
            self.assertEqual(ps.show_window(), "hub")
        finally:
            maya_hub.show = saved
        self.assertEqual(asked, ["tailbuilder"])


if __name__ == "__main__":
    unittest.main()
