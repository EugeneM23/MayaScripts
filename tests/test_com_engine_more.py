"""The trail engine's scene half and its callbacks, on fakes (no Maya).

test_com_engine.py proves the slice's decisions on a FakeScene; this proves
what the engine asks Maya (`Scene`), which frames a key edit or an attribute
set marks dirty, how a curve edit is traced to its character, and how the
callbacks and jobs come and go."""

import sys
import types
import unittest
from unittest import mock

try:                         # the real package, so its attributes can be swapped
    import maya.cmds         # noqa: F401
    import maya.api.OpenMaya         # noqa: F401
    import maya.api.OpenMayaAnim     # noqa: F401
except ImportError:          # pragma: no cover - plain Python: fakes below
    pass

import maya_hubcopy as hubcopy
import maya_rigs
from maya_com import engine, network

_MISSING = object()


# ------------------------------------------------------------------ fakes

def _put_back(name, old):
    if old is _MISSING:
        sys.modules.pop(name, None)
    else:
        sys.modules[name] = old


def use_fakes(test, cmds=None, om=None, oma=None):
    """`import maya.cmds` / `maya.api.OpenMaya(Anim)` answer the fakes until
    the test ends: the sys.modules entries AND the parent packages' attributes
    (an `import a.b.c as x` reads the attributes first)."""
    def put(name, module):
        test.addCleanup(_put_back, name, sys.modules.get(name, _MISSING))
        sys.modules[name] = module
    pkg = sys.modules.get("maya")
    if pkg is None:
        pkg = types.ModuleType("maya")
        pkg.__path__ = []
        put("maya", pkg)
    api = types.ModuleType("maya.api")
    api.__path__ = []
    for leaf, module in (("OpenMaya", om), ("OpenMayaAnim", oma)):
        if module is not None:
            setattr(api, leaf, module)
            put("maya.api." + leaf, module)
    put("maya.api", api)
    patches = [mock.patch.object(pkg, "api", api, create=True)]
    if cmds is not None:
        put("maya.cmds", cmds)
        patches.append(mock.patch.object(pkg, "cmds", cmds, create=True))
    for p in patches:
        p.start()
        test.addCleanup(p.stop)


class Time(object):
    def __init__(self, value, unit=None):
        self.value = float(value)

    @staticmethod
    def uiUnit():
        return "film"


class Node(object):
    """A dependency node: plugs by name, an optional time curve."""

    def __init__(self, name, curve_type=None, curve=None, uuid=None, valid=True):
        self.name = name
        self.uuid = uuid or ("U-" + name)
        self.curve_type = curve_type
        self.curve = curve                 # frame -> value
        self.valid = valid
        self.plugs = {}
        self.evaluations = 0

    def plug(self, attr, value=0.0):
        p = self.plugs.get(attr)
        if p is None:
            p = self.plugs[attr] = Plug(self, attr, value)
        return p

    def hasFn(self, kind):
        return kind == "kAnimCurve" and self.curve_type is not None


class Plug(object):
    def __init__(self, node, attr, value=0.0):
        self._node = node
        self.attr = attr
        self.value = value
        self.dests = []
        self.src = None
        self.children = []
        self.isNull = False
        self.set_data = []

    def node(self):
        return self._node

    def name(self):
        return self._node.name + "." + self.attr

    def connectedTo(self, as_dst, as_src):
        return list(self.dests) if as_src else ([self.src] if self.src else [])

    @property
    def isDestination(self):
        return self.src is not None

    def source(self):
        return self.src or NULL

    def asDouble(self):
        if isinstance(self.value, Exception):
            raise self.value
        return self.value

    def child(self, i):
        return self.children[i]

    def setMObject(self, data):
        self.set_data.append(data)

    def setMTime(self, t):
        self.set_data.append(("time", t.value))


class _Null(object):
    isNull = True


NULL = _Null()


def connect(src, dst):
    src.dests.append(dst)
    dst.src = src


class World(object):
    """What the fake OpenMaya modules read and record."""

    def __init__(self):
        self.by_name = {}          # node or plug name -> Node / Plug
        self.time = 12.0
        self.visits = []
        self.removed = []
        self.attr_callbacks = []
        self.curve_callbacks = []
        self.modifiers = []
        self.next_id = [1000]

    def add(self, thing, name=None):
        self.by_name[name or (thing.name() if isinstance(thing, Plug) else thing.name)] = thing
        return thing

    def new_id(self):
        self.next_id[0] += 1
        return self.next_id[0]


def make_om(world):
    om = types.ModuleType("fake OpenMaya")
    om.MTime = Time
    om.MFn = types.SimpleNamespace(kAnimCurve="kAnimCurve")

    class MSelectionList(object):
        def __init__(self):
            self.items = []

        def add(self, name):
            if name not in world.by_name:
                raise RuntimeError("(kInvalidParameter): No object matches name")
            self.items.append(world.by_name[name])

        def getPlug(self, i):
            return self.items[i]

        def getDependNode(self, i):
            return self.items[i]

    class MObjectHandle(object):
        def __init__(self, obj):
            self.obj = obj

        def hashCode(self):
            return id(self.obj)

        def isValid(self):
            return self.obj.valid

        def object(self):
            return self.obj

    class MFnDependencyNode(object):
        def __init__(self, node):
            self.node = node

        def uuid(self):
            return types.SimpleNamespace(asString=lambda: self.node.uuid)

        def findPlug(self, name, networked):
            if name not in self.node.plugs:
                raise RuntimeError("no plug " + name)
            return self.node.plugs[name]

        def getConnections(self):
            return list(self.node.plugs.values())

    class MMessage(object):
        @staticmethod
        def removeCallback(cb):
            if cb == "boom":
                raise RuntimeError("gone")
            world.removed.append(cb)

    class MNodeMessage(object):
        kAttributeSet = 0x2000
        kConnectionMade = 0x0001

        @staticmethod
        def addAttributeChangedCallback(obj, fn, data):
            cb = world.new_id()
            world.attr_callbacks.append((cb, obj, fn, data))
            return cb

    class MDGModifier(object):
        def __init__(self):
            self.values = []
            self.done = 0
            world.modifiers.append(self)

        def newPlugValueDouble(self, plug, value):
            self.values.append((plug, value))

        def doIt(self):
            self.done += 1

    class MPointArray(list):
        pass

    class MFnPointArrayData(object):
        def create(self, arr):
            return ("points", list(arr))

    om.MSelectionList = MSelectionList
    om.MObjectHandle = MObjectHandle
    om.MFnDependencyNode = MFnDependencyNode
    om.MMessage = MMessage
    om.MNodeMessage = MNodeMessage
    om.MDGModifier = MDGModifier
    om.MPointArray = MPointArray
    om.MPoint = lambda x, y, z: (x, y, z)
    om.MFnPointArrayData = MFnPointArrayData
    return om


def make_oma(world):
    oma = types.ModuleType("fake OpenMayaAnim")

    class MAnimControl(object):
        @staticmethod
        def currentTime():
            return Time(world.time)

        @staticmethod
        def setCurrentTime(t):
            world.time = t.value
            world.visits.append(t.value)

    class MFnAnimCurve(object):
        def __init__(self, node):
            if node.curve_type is None:
                raise RuntimeError("(kInvalidParameter): not an anim curve")
            self.node = node
            self.animCurveType = node.curve_type

        def evaluate(self, t):
            self.node.evaluations += 1
            value = self.node.curve(t.value)
            if isinstance(value, Exception):
                raise value
            return value

        def findPlug(self, name, networked):
            if name not in self.node.plugs:
                raise RuntimeError("no plug " + name)
            return self.node.plugs[name]

        def object(self):
            return self.node

    class MAnimMessage(object):
        @staticmethod
        def addAnimCurveEditedCallback(fn):
            cb = world.new_id()
            world.curve_callbacks.append((cb, fn))
            return cb

    oma.MAnimControl = MAnimControl
    oma.MFnAnimCurve = MFnAnimCurve
    oma.MAnimMessage = MAnimMessage
    return oma


class FakeScene(object):
    """The engine's seam, as in test_com_engine."""

    def __init__(self, groups, span=(0, 10), current=5):
        self.groups = dict(groups)
        self.span = span
        self.now = current
        self.walked = []
        self.writes = []
        self.settings_by = {u: {"trail": 1, "range": 0, "around": 5} for u in groups}

    def current(self):
        return self.now

    def playback(self):
        return self.span

    def animation(self):
        return (self.span[0] - 100, self.span[1] + 100)

    def playing(self):
        return False

    def mouse_down(self):
        return False

    def group(self, uuid):
        return self.groups.get(uuid)

    def settings(self, group):
        uuid = [u for u, g in self.groups.items() if g == group][0]
        return self.settings_by[uuid]

    def reader(self, group):
        return lambda: (float(self.now), 0.0, 0.0, 0.0)

    def walk(self, frame_list, readers):
        self.walked.append(list(frame_list))
        out = {}
        here = self.now
        for f in frame_list:
            self.now = f
            out[f] = {u: r() for u, r in readers.items()}
        self.now = here
        return out

    def tweaks(self, plugs):
        return []

    def put_back(self, tweaks):
        pass

    def write(self, group, span, points):
        self.writes.append((group, span, dict(points)))


class EngineCase(unittest.TestCase):
    """A fresh `sys._skeldar_com` per test (the old one put back after), and
    `arm` recorded instead of a Qt timer."""

    def setUp(self):
        old = getattr(sys, "_skeldar_com", _MISSING)
        sys._skeldar_com = {}
        self.addCleanup(self._restore_state, old)
        self.st = engine.state()
        self.st["per_frame_ms"] = 5.0
        patch = mock.patch.object(engine, "arm")
        self.arm = patch.start()
        self.addCleanup(patch.stop)

    @staticmethod
    def _restore_state(old):
        if old is _MISSING:
            if hasattr(sys, "_skeldar_com"):
                del sys._skeldar_com
        else:
            sys._skeldar_com = old

    def fakes(self, cmds=None):
        self.world = World()
        self.om = make_om(self.world)
        self.oma = make_oma(self.world)
        use_fakes(self, cmds=cmds, om=self.om, oma=self.oma)
        return self.world


# ------------------------------------------------------------- the Scene

class SceneCmds(object):
    def __init__(self):
        self.time = 12.0
        self.playback = (1.0, 48.0)
        self.animation = (-10.0, 60.0)
        self.playing = 0
        self.modified = False
        self.file_calls = []
        self.refreshes = []
        self.paths = {}
        self.attrs = {}

    def currentTime(self, query=False):
        return self.time

    def playbackOptions(self, q=False, minTime=False, maxTime=False,
                        animationStartTime=False, animationEndTime=False):
        if minTime:
            return self.playback[0]
        if maxTime:
            return self.playback[1]
        if animationStartTime:
            return self.animation[0]
        return self.animation[1]

    def play(self, q=False, state=False):
        if isinstance(self.playing, Exception):
            raise self.playing
        return self.playing

    def ls(self, name, long=False):
        return list(self.paths.get(name, []))

    def getAttr(self, plug):
        return self.attrs[plug]

    def refresh(self, suspend=None):
        self.refreshes.append(suspend)

    def file(self, query=False, modified=None):
        if query:
            return self.modified
        self.file_calls.append(modified)


class SceneSeam(EngineCase):

    def setUp(self):
        super(SceneSeam, self).setUp()
        self.cmds = SceneCmds()
        self.fakes(self.cmds)
        self.sc = engine.Scene()

    def test_time_and_ranges_are_maya_s(self):
        self.assertEqual(self.sc.current(), 12.0)
        self.assertEqual(self.sc.playback(), (1.0, 48.0))
        self.assertEqual(self.sc.animation(), (-10.0, 60.0))

    def test_playing_is_false_when_play_cannot_be_asked(self):
        self.assertFalse(self.sc.playing())
        self.cmds.playing = 1
        self.assertTrue(self.sc.playing())
        self.cmds.playing = RuntimeError("no UI")
        self.assertFalse(self.sc.playing())

    def test_a_group_is_its_first_long_path_or_none(self):
        self.cmds.paths["UU-1"] = ["|a:CenterOfMass", "|b:CenterOfMass"]
        self.assertEqual(self.sc.group("UU-1"), "|a:CenterOfMass")
        self.assertIsNone(self.sc.group("UU-gone"))

    def test_settings_are_the_three_attributes_on_the_group(self):
        self.cmds.attrs.update({"|g.trail": True, "|g.range": 1, "|g.around": 7})
        self.assertEqual(self.sc.settings("|g"),
                         {"trail": True, "range": 1, "around": 7})

    def test_the_reader_reads_the_sum_and_the_root_row_live(self):
        w = self.world
        total = w.add(Node("sum").plug("output3D"))
        total.children = [Plug(total.node(), c, v) for c, v in
                          (("x", 1.0), ("y", 2.0), ("z", 3.0))]
        row = w.add(Node("rootRow").plug("outputY", 0.5))
        parts = {"sum": "sum", "rootRow": "rootRow"}
        with mock.patch.object(network, "part", side_effect=lambda g, n: parts[n]):
            read = self.sc.reader("|g")
        self.assertEqual(read(), (1.0, 2.0, 3.0, 0.5))
        total.children[1].value = 9.0
        row.value = -1.0
        self.assertEqual(read(), (1.0, 9.0, 3.0, -1.0))   # live, not a copy

    def test_walk_reads_every_frame_and_comes_back_to_where_it_was(self):
        w = self.world
        out = self.sc.walk([3, 5, 4], {"A": lambda: (w.time, 0.0, 0.0, 0.0)})
        self.assertEqual(out, {3: {"A": (3.0, 0.0, 0.0, 0.0)},
                               5: {"A": (5.0, 0.0, 0.0, 0.0)},
                               4: {"A": (4.0, 0.0, 0.0, 0.0)}})
        self.assertEqual(w.visits, [3.0, 5.0, 4.0, 12.0])
        self.assertEqual(w.time, 12.0)
        self.assertEqual(self.cmds.refreshes, [True, False])

    def test_a_failing_reader_still_puts_the_time_back_and_wakes_the_view(self):
        def boom():
            raise RuntimeError("deleted")
        with self.assertRaises(RuntimeError):
            self.sc.walk([3, 5], {"A": boom})
        self.assertEqual(self.world.time, 12.0)
        self.assertEqual(self.cmds.refreshes, [True, False])

    def test_tweaks_are_the_plugs_off_their_curve_now(self):
        curve = Node("curve", curve_type=1, curve=lambda f: f * 2.0)   # 24 at 12
        on = Plug(Node("a"), "tx", 24.0)
        off = Plug(Node("b"), "tx", 30.0)
        dead = Plug(Node("c"), "tx", RuntimeError("deleted"))
        broken = Node("bad", curve_type=1, curve=lambda f: RuntimeError("x"))
        got = self.sc.tweaks([(on, curve), (off, curve), (dead, curve),
                              (Plug(Node("d"), "tx", 1.0), broken)])
        self.assertEqual(got, [(off, 30.0)])

    def test_put_back_writes_every_tweak_in_one_modifier(self):
        a, b = Plug(Node("a"), "tx"), Plug(Node("b"), "ry")
        self.sc.put_back([(a, 1.5), (b, -3.0)])
        self.assertEqual(len(self.world.modifiers), 1)
        mod = self.world.modifiers[0]
        self.assertEqual(mod.values, [(a, 1.5), (b, -3.0)])
        self.assertEqual(mod.done, 1)
        self.sc.put_back([])
        self.assertEqual(len(self.world.modifiers), 1)   # nothing to do: no modifier

    def _shapes(self, *names):
        w = self.world
        made = {}
        for name in names:
            node = Node(name)
            made[name] = (w.add(node.plug("points")), w.add(node.plug("startTime")))
        return made

    def test_write_draws_the_trail_and_its_floor_shadow(self):
        shapes = self._shapes("trailShape", "floorShape")
        which = {"trail": "trailShape", "floorTrail": "floorShape"}
        points = {0: (1.0, 2.0, 3.0, 0.5), 2: (4.0, 5.0, 6.0, 0.25)}
        with mock.patch.object(network, "trail_shape",
                               side_effect=lambda g, n: which[n]):
            self.sc.write("|g", (0, 2), points)
        trail, trail_start = shapes["trailShape"]
        floor, floor_start = shapes["floorShape"]
        #  frame 1 has no point yet: it takes the nearest, the earlier on a tie
        self.assertEqual(trail.set_data, [("points", [(1.0, 2.0, 3.0), (1.0, 2.0, 3.0),
                                                      (4.0, 5.0, 6.0)])])
        self.assertEqual(floor.set_data, [("points", [(1.0, 0.5, 3.0), (1.0, 0.5, 3.0),
                                                      (4.0, 0.25, 6.0)])])
        self.assertEqual(trail_start.set_data, [("time", 0.0)])
        self.assertEqual(floor_start.set_data, [("time", 0.0)])

    def test_write_leaves_a_clean_scene_clean_and_a_modified_one_alone(self):
        self._shapes("trailShape")
        with mock.patch.object(network, "trail_shape",
                               side_effect=lambda g, n: "trailShape" if n == "trail" else None):
            self.sc.write("|g", (0, 0), {0: (0.0, 0.0, 0.0, 0.0)})
            self.assertEqual(self.cmds.file_calls, [False])
            self.cmds.modified = True
            self.sc.write("|g", (0, 0), {0: (0.0, 0.0, 0.0, 0.0)})
            self.assertEqual(self.cmds.file_calls, [False])

    def test_scene_is_made_once(self):
        made = []

        class Made(object):
            def __init__(self):
                made.append(self)

        with mock.patch.object(engine, "SCENE", [None]), \
                mock.patch.object(engine, "Scene", Made):
            first = engine.scene()
            self.assertIs(engine.scene(), first)
        self.assertEqual(len(made), 1)


# ---------------------------------------------------------- tracking

class TrackCmds(object):
    def __init__(self, uuids):
        self.uuids = uuids

    def ls(self, name, uuid=False):
        return list(self.uuids.get(name, []))


class Tracking(EngineCase):

    def setUp(self):
        super(Tracking, self).setUp()
        self.fakes(TrackCmds({"|a:CoM": ["AAAA"]}))
        self.sc = FakeScene({"AAAA": "|a:CoM"}, span=(0, 10))
        for name in ("_watch_nodes", "_snapshot_curves"):
            p = mock.patch.object(engine, name)
            setattr(self, name.strip("_"), p.start())
            self.addCleanup(p.stop)

    def test_a_new_group_is_watched_snapshot_and_queued_whole(self):
        tr = engine.track("|a:CoM", self.sc)
        self.assertIs(self.st["tracks"]["AAAA"], tr)
        self.assertEqual(tr.span, (0, 10))
        self.assertEqual(tr.dirty, set(range(0, 11)))
        self.watch_nodes.assert_called_once_with("AAAA", "|a:CoM")
        self.snapshot_curves.assert_called_once_with("AAAA", "|a:CoM", (0, 10))
        self.arm.assert_called_with(engine.IDLE_MS)

    def test_tracking_again_follows_the_settings_without_watching_twice(self):
        tr = engine.track("|a:CoM", self.sc)
        tr.dirty = set()
        tr.points = {f: (f, 0, 0, 0) for f in range(11)}
        self.sc.settings_by["AAAA"]["range"] = 1           # Around 5 at frame 5
        self.assertIs(engine.track("|a:CoM", self.sc), tr)
        self.assertEqual(tr.span, (0, 10))
        self.sc.now = 8
        engine.track("|a:CoM", self.sc)
        self.assertEqual(tr.span, (3, 13))
        self.assertEqual(tr.dirty, {11, 12, 13})
        self.assertEqual(self.watch_nodes.call_count, 1)

    def test_a_group_with_no_uuid_is_not_tracked(self):
        self.assertIsNone(engine.track("|gone", self.sc))
        self.assertEqual(self.st["tracks"], {})
        self.watch_nodes.assert_not_called()

    def test_dirty_all_marks_one_track_or_every_track(self):
        a, b = engine.Track("A", (0, 3)), engine.Track("B", (5, 6))
        a.dirty, b.dirty = set(), set()
        self.st["tracks"].update({"A": a, "B": b})
        engine.dirty_all("A")
        self.assertEqual((a.dirty, b.dirty), ({0, 1, 2, 3}, set()))
        engine.dirty_all()
        self.assertEqual(b.dirty, {5, 6})
        self.arm.assert_called_with(engine.IDLE_MS)

    def test_track_dirty_all_is_every_frame_of_its_span(self):
        tr = engine.Track("A", (2, 5))
        tr.dirty = {3}
        tr.dirty_all()
        self.assertEqual(tr.dirty, {2, 3, 4, 5})

    def test_rescan_forgets_everything_and_tracks_what_the_scene_holds(self):
        self.st["tracks"]["OLD"] = engine.Track("OLD", (0, 1))
        self.st["node_callbacks"]["OLD"] = {"ids": [], "hashes": set(), "curve_plugs": {}}
        self.st["snapshots"][("OLD", "c")] = {0: 1.0}
        self.st["live_frames"] = {4}
        with mock.patch.object(network, "find_all", return_value=["|a:CoM", "|b:CoM"]), \
                mock.patch.object(engine, "track") as track:
            engine.rescan()
        self.assertEqual(self.st["tracks"], {})
        self.assertNotIn("OLD", self.st["node_callbacks"])
        self.assertEqual(self.st["snapshots"], {})
        self.assertEqual(self.st["live_frames"], set())
        self.assertEqual([c.args[0] for c in track.call_args_list], ["|a:CoM", "|b:CoM"])


# ------------------------------------------------------------- the slice

class Slices(EngineCase):

    def setUp(self):
        super(Slices, self).setUp()
        self.sc = FakeScene({"A": "|a:CoM"}, span=(0, 20), current=10)
        self.tr = engine.Track("A", (0, 20))
        self.st["tracks"]["A"] = self.tr

    def test_a_slice_inside_a_slice_does_nothing(self):
        self.st["busy"] = True                   # a walk's own time change re-entering
        self.assertEqual(engine.tick(self.sc), 0)
        self.assertEqual(self.sc.walked, [])
        self.assertTrue(self.st["busy"])         # the outer slice still owns it

    def test_a_tweak_s_live_point_is_not_overwritten_by_the_keyed_pose(self):
        self.tr.points = {f: (f, 0.0, 0.0, 0.0) for f in range(21)}
        self.tr.points[10] = ("tweaked",)
        self.tr.dirty = {9, 10}
        self.st["live_frames"] = {10}
        engine.tick(self.sc)
        self.assertEqual(self.tr.points[10], ("tweaked",))
        self.assertEqual(self.tr.points[9], (9.0, 0.0, 0.0, 0.0))

    def test_a_live_frame_made_dirty_again_is_not_walked_for_ever(self):
        #  FIXED 2026-10-27, the bug as it was - engine.py `_tick` ("the live (tweaked) point wins here"): the
        #  `continue` skips `tr.dirty.discard(frame)`. A frame that is current,
        #  in `live_frames` (a standing tweak) and dirty again - a curve edit
        #  that changed it, absorbed with no attribute-set in between (e.g. a
        #  key moved in the Graph Editor at the tweaked frame) - stays dirty:
        #  `pending()` never reaches 0, the engine re-arms at IDLE_MS and walks
        #  that one frame slice after slice until the time moves.
        self.tr.points = {f: (f, 0.0, 0.0, 0.0) for f in range(21)}
        self.tr.dirty = {10}
        self.st["live_frames"] = {10}
        engine.run_until_clean(self.sc, limit=5)
        self.assertEqual(engine.pending(), 0)
        self.assertLessEqual(len(self.sc.walked), 1, self.sc.walked)


class FakeQt(object):
    """A PySide6 stand-in: an application with its mouse buttons, a timer."""

    def __init__(self, app=True):
        qt = self
        self.timers = []
        self.buttons = "NoButton"
        self.app = app

        class QTimer(object):
            def __init__(self):
                self.single = None
                self.active = False
                self.started = []
                self.timeout = mock.Mock()
                qt.timers.append(self)

            def setSingleShot(self, on):
                self.single = on

            def isActive(self):
                return self.active

            def start(self, ms):
                self.active = True
                self.started.append(ms)

        class App(object):
            def mouseButtons(self):
                if isinstance(qt.buttons, Exception):
                    raise qt.buttons
                return qt.buttons

        class QApplication(object):
            @staticmethod
            def instance():
                return App() if qt.app else None

        self.package = types.ModuleType("PySide6")
        self.package.QtCore = types.SimpleNamespace(QTimer=QTimer,
                                                    Qt=types.SimpleNamespace(NoButton="NoButton"))
        self.package.QtWidgets = types.SimpleNamespace(QApplication=QApplication)

    def install(self, test):
        test.addCleanup(_put_back, "PySide6", sys.modules.get("PySide6", _MISSING))
        sys.modules["PySide6"] = self.package


class Arm(unittest.TestCase):
    """The single-shot timer that asks for the next slice."""

    def setUp(self):
        old = getattr(sys, "_skeldar_com", _MISSING)
        sys._skeldar_com = {}
        self.addCleanup(EngineCase._restore_state, old)
        self.qt = FakeQt()
        self.qt.install(self)

    def test_a_slice_is_asked_for_once_while_one_is_pending(self):
        engine.arm(15)
        engine.arm(0)
        (timer,) = self.qt.timers
        self.assertTrue(timer.single)
        timer.timeout.connect.assert_called_once_with(engine._on_timer)
        self.assertEqual(timer.started, [15])
        timer.active = False                     # it fired
        engine.arm(120.7)
        self.assertEqual(timer.started, [15, 120])
        self.assertIs(engine.state()["timer"], timer)

    def test_with_no_application_there_is_no_timer(self):
        self.qt.app = False
        engine.arm(0)
        self.assertEqual(self.qt.timers, [])
        self.assertIsNone(engine.state()["timer"])

    def test_the_mouse_is_down_while_any_button_is(self):
        cmds = SceneCmds()
        world = World()
        use_fakes(self, cmds=cmds, om=make_om(world), oma=make_oma(world))
        sc = engine.Scene()
        self.assertFalse(sc.mouse_down())
        self.qt.buttons = "LeftButton"
        self.assertTrue(sc.mouse_down())
        self.qt.buttons = RuntimeError("deleted")
        self.assertFalse(sc.mouse_down())
        self.qt.app = False
        self.assertFalse(sc.mouse_down())


# ------------------------------------------------------------- the timer

class TimerAndTime(EngineCase):

    def test_a_failing_slice_is_remembered_not_raised(self):
        with mock.patch.object(engine, "tick", side_effect=RuntimeError("bad")):
            engine._on_timer()
        self.assertEqual(self.st["last_error"], "RuntimeError('bad')")

    def test_a_range_change_arms_a_slice(self):
        engine._on_range("ignored")
        self.arm.assert_called_once_with(engine.IDLE_MS)

    def _two_tracks(self):
        a, b = engine.Track("A", (0, 20)), engine.Track("B", (11, 30))
        a.dirty, b.dirty = set(), set()
        self.st["tracks"].update({"A": a, "B": b})
        return a, b

    def test_moving_the_time_gives_a_tweaked_frame_back_to_the_keys(self):
        a, b = self._two_tracks()
        self.st["live_frames"] = {10, 12}
        with mock.patch.object(engine, "SCENE", [FakeScene({}, current=12)]):
            engine._on_time()
        self.assertEqual(a.dirty, {10})            # 12 is where the time is: still live
        self.assertEqual(b.dirty, set())           # 10 is outside B's span
        self.assertEqual(self.st["live_frames"], {12})
        self.arm.assert_called_with(engine.IDLE_MS)

    def test_with_no_current_time_every_live_frame_goes_back(self):
        a, b = self._two_tracks()
        self.st["live_frames"] = {10, 12}
        broken = FakeScene({})
        broken.current = mock.Mock(side_effect=RuntimeError("no time"))
        with mock.patch.object(engine, "SCENE", [broken]):
            engine._on_time()
        self.assertEqual(a.dirty, {10, 12})
        self.assertEqual(b.dirty, {12})
        self.assertEqual(self.st["live_frames"], set())


# -------------------------------------------------- curves edited -> frames

def linear(f):
    return float(f)


class CurveEdits(EngineCase):
    """A curve edited: only the frames whose value changed get dirty, and only
    on the character the curve drives."""

    def setUp(self):
        super(CurveEdits, self).setUp()
        self.fakes()
        self.curve = Node("animCurveTL1", curve_type=1, curve=linear)
        out = self.curve.plug("output")
        self.blend = Node("animBlendNodeAdditive1")
        connect(out, self.blend.plug("inputA"))
        self.ctrl = Node("FKHead_M")
        connect(self.blend.plug("output"), self.ctrl.plug("translateX"))
        self.tr = engine.Track("A", (0, 6))
        self.tr.dirty = set()
        self.tr.points = {f: (f, 0, 0, 0) for f in range(7)}
        self.st["tracks"]["A"] = self.tr
        self.st["node_callbacks"]["A"] = {"ids": [], "hashes": {id(self.ctrl)},
                                          "curve_plugs": {}}
        self.groups = {"A": "|a:CoM"}

    def edit(self, *curves):
        engine._on_curves(list(curves))

    def test_an_edit_is_queued_and_arms_a_slice(self):
        self.edit(self.curve)
        self.assertEqual(len(self.st["pending_curves"]), 1)
        self.arm.assert_called_once_with(engine.IDLE_MS)

    def test_a_key_edit_dirties_only_the_frames_it_changed(self):
        self.st["snapshots"][("A", self.curve.uuid)] = {f: float(f) for f in range(7)}
        self.curve.curve = lambda f: 30.0 if f in (3, 4) else float(f)
        self.edit(self.curve)
        engine._absorb_curves(self.st, self.groups)
        self.assertEqual(self.tr.dirty, {3, 4})
        self.assertEqual(self.st["pending_curves"], set())
        self.assertEqual(self.st["snapshots"][("A", self.curve.uuid)][3], 30.0)

    def test_a_curve_never_sampled_dirties_the_whole_span(self):
        self.edit(self.curve)
        engine._absorb_curves(self.st, self.groups)
        self.assertEqual(self.tr.dirty, set(range(7)))

    def test_the_edited_curve_becomes_a_plug_a_tweak_can_be_on(self):
        self.edit(self.curve)
        engine._absorb_curves(self.st, self.groups)
        plugs = self.st["node_callbacks"]["A"]["curve_plugs"]
        self.assertEqual(list(plugs), ["animBlendNodeAdditive1.inputA"])
        self.assertIs(plugs["animBlendNodeAdditive1.inputA"][1], self.curve)

    def test_a_driven_key_curve_changes_nothing(self):
        self.curve.curve_type = 5                 # animCurveUU: not time-driven
        self.edit(self.curve)
        engine._absorb_curves(self.st, self.groups)
        self.assertEqual(self.tr.dirty, set())
        self.assertEqual(self.curve.evaluations, 0)

    def test_a_curve_deleted_since_the_edit_is_skipped(self):
        self.curve.valid = False
        self.edit(self.curve)
        engine._absorb_curves(self.st, self.groups)
        self.assertEqual(self.tr.dirty, set())

    def test_a_node_that_is_no_curve_is_skipped(self):
        self.edit(Node("pairBlend1"))
        engine._absorb_curves(self.st, self.groups)
        self.assertEqual(self.tr.dirty, set())

    def test_a_curve_on_another_character_leaves_this_one_clean(self):
        self.st["node_callbacks"]["A"]["hashes"] = {id(Node("someone_else"))}
        self.edit(self.curve)
        engine._absorb_curves(self.st, self.groups)
        self.assertEqual(self.tr.dirty, set())
        self.assertEqual(self.curve.evaluations, 0)

    def test_a_slice_after_an_edit_walks_only_the_changed_frames(self):
        sc = FakeScene({"A": "|a:CoM"}, span=(0, 6), current=0)
        self.st["snapshots"][("A", self.curve.uuid)] = {f: float(f) for f in range(7)}
        self.curve.curve = lambda f: -1.0 if f == 5 else float(f)
        self.edit(self.curve)
        walked = engine.run_until_clean(sc)
        self.assertEqual(walked, 1)
        self.assertEqual(sc.walked, [[5]])
        self.assertEqual(engine.pending(), 0)

    def test_a_moved_span_leaves_no_dirty_frame_outside_it(self):
        #  FIXED 2026-10-27, the bug as it was - engine.py `_absorb_curves`: the snapshot is over the span the
        #  track had when it was taken; after the span moves (Around follows
        #  the time, the playback range changes) `changed_frames(before,
        #  after)` also answers the frames only BEFORE holds - outside the new
        #  span - and `tr.dirty |=` keeps them. `_tick` walks them but stores
        #  (and discards) only frames inside the span, and `rerange` filters
        #  only when the span changes again: they stay dirty for ever, so the
        #  engine re-arms at IDLE_MS and walks them slice after slice.
        sc = FakeScene({"A": "|a:CoM"}, span=(0, 6), current=4)
        self.st["snapshots"][("A", self.curve.uuid)] = {f: float(f) for f in range(7)}
        sc.span = (3, 9)                         # the playback range moved
        self.curve.curve = lambda f: -1.0 if f == 4 else float(f)
        self.edit(self.curve)
        engine.run_until_clean(sc, limit=20)
        self.assertEqual(engine.pending(), 0)
        self.assertTrue(all(3 <= f <= 9 for batch in sc.walked for f in batch),
                        sc.walked)


class Owners(EngineCase):
    """Which tracks a curve drives: through blend nodes, at most four hops."""

    def setUp(self):
        super(Owners, self).setUp()
        self.fakes()

    def chain(self, between, out_plug="output"):
        curve = Node("curve", curve_type=1, curve=linear)
        prev = curve.plug("output")
        for i in range(between):
            node = Node("blend%d" % i)
            connect(prev, node.plug("input"))
            prev = node.plug(out_plug)
        end = Node("ctrl")
        connect(prev, end.plug("translateX"))
        return curve, end

    def owners(self, curve, watched):
        for uuid, nodes in watched.items():
            self.st["node_callbacks"][uuid] = {"ids": [], "curve_plugs": {},
                                               "hashes": {id(n) for n in nodes}}
        fn = self.oma.MFnAnimCurve(curve)
        return engine._owners(fn, {u: "|" + u for u in watched})

    def test_a_curve_straight_on_a_control(self):
        curve, ctrl = self.chain(0)
        self.assertEqual(self.owners(curve, {"A": [ctrl], "B": [Node("x")]}), ["A"])

    def test_through_an_animation_layer_s_blend_nodes(self):
        curve, ctrl = self.chain(3)              # the control four hops away
        self.assertEqual(self.owners(curve, {"A": [ctrl]}), ["A"])

    def test_through_a_pair_blend_s_out_translate(self):
        curve, ctrl = self.chain(1, out_plug="outTranslate")
        self.assertEqual(self.owners(curve, {"A": [ctrl]}), ["A"])

    def test_no_further_than_four_hops(self):
        curve, ctrl = self.chain(4)
        self.assertEqual(self.owners(curve, {"A": [ctrl]}), [])

    def test_a_control_two_characters_watch_names_both_once(self):
        curve, ctrl = self.chain(0)
        connect(curve.plugs["output"], ctrl.plug("translateY"))
        self.assertEqual(self.owners(curve, {"A": [ctrl], "B": [ctrl]}), ["A", "B"])

    def test_a_curve_with_no_output_drives_no_one(self):
        curve = Node("curve", curve_type=1, curve=linear)
        self.assertEqual(self.owners(curve, {"A": [Node("ctrl")]}), [])


# ------------------------------------------- the character's nodes and plugs

class CharacterCmds(object):
    def __init__(self):
        self.members = ["FKHead_M", "Main", "ControlSetHelper", "ns:Missing"]
        self.long = {"FKHead_M": "|r|FKHead_M", "Main": "|r|Main",
                     "ControlSetHelper": "|r|ControlSetHelper"}
        self.curves = {"|r|FKHead_M", "|r|Main"}

    def sets(self, name, q=False):
        return list(self.members)

    def ls(self, names, long=False):
        return [self.long[n] for n in names if n in self.long]

    def listRelatives(self, node, shapes=False, type=None):
        return [node + "Shape"] if node in self.curves else []


class CharacterNodes(EngineCase):

    def setUp(self):
        super(CharacterNodes, self).setUp()
        self.fakes(CharacterCmds())
        self.rig = types.SimpleNamespace(control_set="r:ControlSet")
        for target, name, value in (
                (network, "root_of", "|root"),
                (network, "joints_of", ["|root", "|root|pelvis"]),
                (maya_rigs, "rigs", ["a rig"]),
                (maya_rigs, "rig_of", self.rig)):
            p = mock.patch.object(target, name, return_value=value)
            setattr(self, name, p.start())
            self.addCleanup(p.stop)

    def test_a_rig_is_its_curve_controls_and_its_joints(self):
        self.assertEqual(engine._character_nodes("|g"),
                         ["|r|FKHead_M", "|r|Main", "|root", "|root|pelvis"])
        self.rig_of.assert_called_once_with("|root", ["a rig"])

    def test_a_bare_skeleton_is_its_joints(self):
        self.rig_of.return_value = None
        self.assertEqual(engine._character_nodes("|g"), ["|root", "|root|pelvis"])

    def test_no_root_no_nodes(self):
        self.root_of.return_value = None
        self.assertEqual(engine._character_nodes("|g"), [])


class Watching(EngineCase):

    def setUp(self):
        super(Watching, self).setUp()
        self.fakes()
        self.a = self.world.add(Node("|r|FKHead_M"))
        self.b = self.world.add(Node("|r|pelvis"))

    def test_each_node_gets_an_attribute_callback_for_this_track(self):
        with mock.patch.object(engine, "_character_nodes",
                               return_value=["|r|FKHead_M", "|r|deleted", "|r|pelvis"]), \
                mock.patch.object(engine, "_gather_curve_plugs") as gather:
            engine._watch_nodes("A", "|g")
        entry = self.st["node_callbacks"]["A"]
        self.assertEqual(entry["hashes"], {id(self.a), id(self.b)})
        self.assertEqual(len(entry["ids"]), 2)
        self.assertEqual([(obj, fn, data) for _cb, obj, fn, data in self.world.attr_callbacks],
                         [(self.a, engine._on_attribute, "A"),
                          (self.b, engine._on_attribute, "A")])
        self.assertEqual(entry["curve_plugs"], {})
        gather.assert_called_once_with("A", "|g")

    def test_unwatching_removes_the_callbacks(self):
        self.st["node_callbacks"]["A"] = {"ids": [7, "boom", 8], "hashes": set(),
                                          "curve_plugs": {}}
        engine._unwatch_nodes("A")
        self.assertEqual(self.world.removed, [7, 8])      # one failing does not stop the rest
        self.assertNotIn("A", self.st["node_callbacks"])

    def test_the_curve_plugs_are_the_time_curves_driving_the_character(self):
        ctrl = self.a
        keyed = Node("FKHead_M_rotateX", curve_type=1, curve=linear)
        connect(keyed.plug("output"), ctrl.plug("rotateX"))
        driven = Node("SDK_curve", curve_type=5, curve=linear)       # a driven key
        connect(driven.plug("output"), ctrl.plug("rotateY"))
        constraint = Node("FKHead_M_parentConstraint1")
        connect(constraint.plug("constraintTranslateX"), ctrl.plug("translateX"))
        ctrl.plug("translateZ").src = NULL                  # a destination, nothing in
        ctrl.plug("worldMatrix")                                     # an output only
        self.st["node_callbacks"]["A"] = {"ids": [], "hashes": set(), "curve_plugs": {}}
        with mock.patch.object(engine, "_character_nodes", return_value=["|r|FKHead_M"]):
            engine._gather_curve_plugs("A", "|g")
        plugs = self.st["node_callbacks"]["A"]["curve_plugs"]
        self.assertEqual(list(plugs), ["|r|FKHead_M.rotateX"])
        self.assertIs(plugs["|r|FKHead_M.rotateX"][1], keyed)

    def test_remembering_a_curve_with_no_track_entry_does_nothing(self):
        curve = Node("c", curve_type=1, curve=linear)
        connect(curve.plug("output"), Node("x").plug("tx"))
        engine._remember_curve_plug("NOPE", self.oma.MFnAnimCurve(curve))
        self.assertNotIn("NOPE", self.st["node_callbacks"])

    def test_remembering_a_curve_with_no_output_left_does_nothing(self):
        self.st["node_callbacks"]["A"] = {"ids": [], "hashes": set(), "curve_plugs": {}}
        engine._remember_curve_plug("A", self.oma.MFnAnimCurve(Node("c", curve_type=1)))
        self.assertEqual(self.st["node_callbacks"]["A"]["curve_plugs"], {})

    def test_gathering_skips_a_deleted_node_and_a_curve_maya_cannot_read(self):
        odd = Node("odd", curve_type=1)
        odd.hasFn = lambda kind: True            # says it is a curve ...
        connect(odd.plug("output"), self.a.plug("rotateZ"))
        self.st["node_callbacks"]["A"] = {"ids": [], "hashes": set(), "curve_plugs": {}}
        with mock.patch.object(engine, "_character_nodes",
                               return_value=["|r|deleted", "|r|FKHead_M"]), \
                mock.patch.object(self.oma, "MFnAnimCurve",
                                  side_effect=RuntimeError("... and is not")):
            engine._gather_curve_plugs("A", "|g")
        self.assertEqual(self.st["node_callbacks"]["A"]["curve_plugs"], {})

    def test_snapshots_sample_each_curve_once_over_the_span(self):
        c1 = Node("c1", curve_type=1, curve=lambda f: f * 10.0)
        c2 = Node("c2", curve_type=2, curve=lambda f: -f)
        self.st["node_callbacks"]["A"] = {"ids": [], "hashes": set(), "curve_plugs": {
            "a.tx": (Plug(self.a, "tx"), c1),
            "a.ty": (Plug(self.a, "ty"), c1),            # the same curve twice
            "b.rz": (Plug(self.b, "rz"), c2)}}
        engine._snapshot_curves("A", "|g", (2, 4))
        self.assertEqual(self.st["snapshots"][("A", "U-c1")], {2: 20.0, 3: 30.0, 4: 40.0})
        self.assertEqual(self.st["snapshots"][("A", "U-c2")], {2: -2.0, 3: -3.0, 4: -4.0})
        self.assertEqual(c1.evaluations, 3)


class AttributeSet(EngineCase):

    def setUp(self):
        super(AttributeSet, self).setUp()
        self.fakes()
        self.tr = engine.Track("A", (0, 4))
        self.tr.dirty = set()
        self.st["tracks"]["A"] = self.tr
        self.set = self.om.MNodeMessage.kAttributeSet

    def test_a_tweak_on_a_keyed_channel_moves_the_live_point_only(self):
        keyed = Plug(Node("ctrl"), "tx")
        keyed.src = Plug(Node("curve"), "output")
        engine._on_attribute(self.set, keyed, None, "A")
        self.assertTrue(self.st["live"])
        self.assertEqual(self.tr.dirty, set())
        self.arm.assert_called_once_with(engine.LIVE_MS)

    def test_a_static_value_dirties_every_frame(self):
        engine._on_attribute(self.set, Plug(Node("ctrl"), "tx"), None, "A")
        self.assertTrue(self.st["live"])
        self.assertEqual(self.tr.dirty, {0, 1, 2, 3, 4})
        self.arm.assert_called_once_with(engine.IDLE_MS)

    def test_a_plug_that_cannot_say_counts_as_static(self):
        class Gone(object):
            @property
            def isDestination(self):
                raise RuntimeError("deleted")
        engine._on_attribute(self.set, Gone(), None, "A")
        self.assertEqual(self.tr.dirty, {0, 1, 2, 3, 4})

    def test_other_messages_and_other_tracks_are_ignored(self):
        engine._on_attribute(self.om.MNodeMessage.kConnectionMade,
                             Plug(Node("ctrl"), "tx"), None, "A")
        engine._on_attribute(self.set, Plug(Node("ctrl"), "tx"), None, "GONE")
        self.assertFalse(self.st["live"])
        self.assertEqual(self.tr.dirty, set())
        self.arm.assert_not_called()


# ---------------------------------------------------- callbacks come and go

class JobCmds(object):
    def __init__(self):
        self.made = []          # (id, event, fn, scope current at the call)
        self.alive = set()
        self.killed = []
        self.next = 500

    def scriptJob(self, event=None, exists=None, kill=None, force=False):
        if exists is not None:
            return exists in self.alive
        if kill is not None:
            self.alive.discard(kill)
            self.killed.append(kill)
            return None
        self.next += 1
        self.made.append((self.next, event[0], event[1], hubcopy.current()))
        self.alive.add(self.next)
        return self.next


class Timer(object):
    def __init__(self):
        self.stopped = 0
        self.timeout = mock.Mock()

    def stop(self):
        self.stopped += 1


class StartStop(EngineCase):

    def setUp(self):
        super(StartStop, self).setUp()
        self.cmds = JobCmds()
        self.fakes(self.cmds)
        p = mock.patch.object(engine, "rescan")
        self.rescan = p.start()
        self.addCleanup(p.stop)

    def test_start_hangs_the_curve_callback_and_five_jobs_then_scans(self):
        engine.start()
        self.assertEqual(self.st["callbacks"], [self.world.curve_callbacks[0][0]])
        self.assertIs(self.world.curve_callbacks[0][1], engine._on_curves)
        self.assertEqual([(e, f) for _id, e, f, _s in self.cmds.made],
                         [("playbackRangeChanged", engine._on_range),
                          ("playbackRangeSliderChanged", engine._on_range),
                          ("timeChanged", engine._on_time),
                          ("SceneOpened", engine.rescan),
                          ("NewSceneOpened", engine.rescan)])
        self.assertEqual(self.st["jobs"], [m[0] for m in self.cmds.made])
        self.assertTrue(self.st["running"])
        self.rescan.assert_called_once_with()

    def test_the_jobs_are_the_scene_s_even_from_a_popup_copy(self):
        with hubcopy.entered(hubcopy.Scope("hubcopyTest")):
            engine.start()
        self.assertEqual({scope for _id, _e, _f, scope in self.cmds.made}, {None})

    def test_a_second_start_takes_the_first_one_s_callbacks_down(self):
        engine.start()
        first_jobs = list(self.st["jobs"])
        first_cb = self.st["callbacks"][0]
        engine.start()
        self.assertEqual(self.world.removed, [first_cb])
        self.assertEqual(self.cmds.killed, first_jobs)
        self.assertEqual(len(self.cmds.alive), 5)

    def test_stop_takes_everything_down_even_when_parts_are_gone(self):
        self.st["callbacks"] = ["boom", 41]
        self.st["node_callbacks"]["A"] = {"ids": [42], "hashes": set(), "curve_plugs": {}}
        self.cmds.alive = {601}
        self.st["jobs"] = [601, 602]                       # 602 died with its scene
        timer = Timer()
        self.st["timer"] = timer
        self.st["running"] = True
        engine.stop()
        self.assertEqual(self.world.removed, [41, 42])
        self.assertEqual(self.st["node_callbacks"], {})
        self.assertEqual(self.cmds.killed, [601])
        self.assertEqual((self.st["callbacks"], self.st["jobs"]), ([], []))
        self.assertEqual(timer.stopped, 1)
        timer.timeout.disconnect.assert_called_once_with()
        self.assertIsNone(self.st["timer"])
        self.assertFalse(self.st["running"])


if __name__ == "__main__":
    unittest.main()
