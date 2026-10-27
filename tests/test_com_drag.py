"""The CoM tool's scene half, on a fake rig (no Maya).

test_com_dragmath.py proves the maths; this proves what the tool does with
it: the plan measured by probing the drivers (a pole riding the hips needs no
move of its own), every driver landing exactly d further in world, the keys
Maya's autoKey would set, the press / drag / release of the context, a click
that selects, and the tool switching on and off with the selection."""

import math
import sys
import types
import unittest
from unittest import mock

try:                         # the real package, so its attributes can be swapped
    import maya.cmds         # noqa: F401
    import maya.api.OpenMaya         # noqa: F401
except ImportError:          # pragma: no cover
    pass

import maya_hubcopy as hubcopy
from maya_com import drag, network, panel

_MISSING = object()

IDENT = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
#  the hips' parent: turned 90 about Y and scaled 2 (row-vector, world = t·P)
HIPS_P = ((0.0, 0.0, -2.0), (0.0, 2.0, 0.0), (2.0, 0.0, 0.0))
#  the pole's parent: turned 90 about Z, riding the hips' world place
POLE_P = ((0.0, 1.0, 0.0), (-1.0, 0.0, 0.0), (0.0, 0.0, 1.0))

ROOT = "|r|RootX_M"
LEG = "|r|IKLeg_L"
POLE = "|r|PoleLeg_L"
MAIN = "|r|Main"


def _mul(t, p):
    return tuple(sum(t[r] * p[r][c] for r in range(3)) for c in range(3))


class RigCmds(object):
    """A few transforms whose world place is translate·P + origin; a node may
    ride another (its origin is that node's world place plus an offset)."""

    def __init__(self):
        self.t = {ROOT: [1.0, 2.0, 3.0], LEG: [10.0, 0.0, 5.0],
                  POLE: [0.0, 4.0, 1.0], MAIN: [0.0, 0.0, 0.0]}
        self.P = {ROOT: HIPS_P, LEG: IDENT, POLE: POLE_P, MAIN: IDENT}
        self.origin = {ROOT: (0.0, 90.0, 0.0), LEG: (0.0, 0.0, 0.0),
                       POLE: (0.0, 0.0, 30.0), MAIN: (0.0, 0.0, 0.0)}
        self.rides = {POLE: ROOT}
        self.locked = {}
        self.follows = {}
        self.curves = set()
        self.keys = []
        self.sets = 0
        self.chunks = []
        self.autokey = True
        self.xform_fail = None
        self.calls = []
        # the context and the tool
        self.selection = []
        self.anchor = (10.0, 20.0, 0.0)
        self.drag_at = (10.0, 20.0, 0.0)
        self.modifier = "none"
        self.context_exists = False
        self.contexts = []
        self.tool = "selectSuperContext"
        self.tools = []
        self.deferred = []
        self.refreshes = []
        self.messages = []
        self.jobs = {}
        self.killed = []
        self.next_job = 300
        self.attrs = {}
        self.types = {}
        self.parents = {}

    # the rig
    def _origin(self, node):
        o = self.origin[node]
        ride = self.rides.get(node)
        if ride:
            w = self.world(ride)
            o = tuple(a + b for a, b in zip(o, w))
        return o

    def world(self, node):
        return tuple(a + b for a, b in zip(_mul(self.t[node], self.P[node]),
                                           self._origin(node)))

    def getAttr(self, plug, settable=False):
        node, attr = plug.split(".", 1)
        if attr == "translate":
            return [tuple(self.t[node])]
        if attr in ("tx", "ty", "tz"):
            if settable:
                return attr not in self.locked.get(node, ())
            return self.t[node]["xyz".index(attr[1])]
        if attr == "parentMatrix[0]":
            p, o = self.P[node], self._origin(node)
            return list(p[0]) + [0.0] + list(p[1]) + [0.0] + list(p[2]) + [0.0] \
                + list(o) + [1.0]
        if attr in self.follows.get(node, {}):
            return self.follows[node][attr]
        return self.attrs[plug]

    def setAttr(self, plug, *values):
        node, attr = plug.split(".", 1)
        if attr == "translate":
            self.t[node] = list(values)
            self.sets += 1
            return
        self.attrs[plug] = values[0]

    def xform(self, node, query=False, worldSpace=False, translation=False):
        if self.xform_fail is not None:
            self.xform_fail -= 1
            if self.xform_fail < 0:
                raise RuntimeError("the node went away")
        return list(self.world(node))

    def listAttr(self, node, userDefined=False):
        return list(self.follows.get(node, {}))

    def listConnections(self, plug, source=False, destination=False, type=None):
        node, attr = plug.split(".", 1)
        return [plug + "_curve"] if (node, attr) in self.curves else []

    def setKeyframe(self, node, attribute=None):
        self.keys.append((node, attribute))

    def undoInfo(self, openChunk=False, closeChunk=False, chunkName=None):
        self.chunks.append("open" if openChunk else "close")

    def autoKeyframe(self, query=False, state=False):
        return self.autokey

    # the context, the tool, the selection
    def ls(self, selection=False, long=False):
        return list(self.selection)

    def draggerContext(self, ctx, exists=False, query=False, edit=False,
                       anchorPoint=False, dragPoint=False, modifier=False, **kw):
        if exists:
            return self.context_exists
        if query:
            if anchorPoint:
                return list(self.anchor)
            if dragPoint:
                return list(self.drag_at)
            return self.modifier
        self.contexts.append(("edit" if edit else "create", ctx, kw))
        self.context_exists = True
        return ctx

    def refresh(self, currentView=False):
        self.refreshes.append(currentView)

    def inViewMessage(self, **kw):
        self.messages.append(kw)

    def currentCtx(self):
        return self.tool

    def setToolTo(self, name):
        self.tool = name
        self.tools.append(name)

    def evalDeferred(self, fn):
        self.deferred.append(fn)

    def scriptJob(self, event=None, exists=None, kill=None, force=False):
        if exists is not None:
            return exists in self.jobs
        if kill is not None:
            if kill == "boom":
                raise RuntimeError("no such job")
            self.jobs.pop(kill, None)
            self.killed.append(kill)
            return None
        self.next_job += 1
        self.jobs[self.next_job] = (event[0], event[1], hubcopy.current())
        return self.next_job

    def objectType(self, node):
        return self.types.get(node, "transform")

    def listRelatives(self, node, parent=False, fullPath=False):
        return [self.parents[node]] if node in self.parents else []

    def attributeQuery(self, attr, node=None, exists=False):
        return (node + "." + attr) in self.attrs


Char = network.Character


class DragCase(unittest.TestCase):

    def setUp(self):
        old = getattr(sys, "_skeldar_com", _MISSING)
        sys._skeldar_com = {}
        self.addCleanup(self._restore_state, old)
        self.cmds = RigCmds()
        self.patch(drag, "cmds", self.cmds)
        self.char = Char("|r|root", None, "", "Manny_Rig")
        self.patch(network, "drivers", lambda char: [ROOT, LEG, POLE])
        self.patch(network, "root_of", lambda group: "|r|root")
        self.patch(network, "_character_for", lambda root: self.char)

    def patch(self, target, name, value):
        p = mock.patch.object(target, name, value)
        p.start()
        self.addCleanup(p.stop)

    @staticmethod
    def _restore_state(old):
        if old is _MISSING:
            if hasattr(sys, "_skeldar_com"):
                del sys._skeldar_com
        else:
            sys._skeldar_com = old

    def assertVec(self, got, want, places=9):
        self.assertEqual(len(got), len(want))
        for g, w in zip(got, want):
            self.assertAlmostEqual(g, w, places=places, msg="%r != %r" % (got, want))


# ------------------------------------------------------------------ plan

class Plan(DragCase):

    def test_each_driver_learns_its_parent_s_inverse_and_the_pole_rides(self):
        a = drag.plan(self.char)
        self.assertEqual(set(a), {ROOT, LEG, POLE})
        #  the hips: the inverse of a 90-turned, 2-scaled parent
        for row, want in zip(a[ROOT], ((0.0, 0.0, 0.5), (0.0, 0.5, 0.0), (-0.5, 0.0, 0.0))):
            self.assertVec(row, want)
        for row, want in zip(a[LEG], IDENT):
            self.assertVec(row, want)
        #  the pole's parent rides the hips: moving them moves it already
        for row in a[POLE]:
            self.assertVec(row, (0.0, 0.0, 0.0))

    def test_the_order_of_the_drivers_does_not_matter(self):
        a = drag.plan(self.char, drivers=[POLE, LEG, ROOT])
        for row in a[POLE]:
            self.assertVec(row, (0.0, 0.0, 0.0), places=6)
        self.assertVec(a[ROOT][0], (0.0, 0.0, 0.5), places=6)

    def test_the_probes_leave_every_translate_where_it_was(self):
        before = {n: list(v) for n, v in self.cmds.t.items()}
        drag.plan(self.char)
        self.assertEqual(self.cmds.t, before)

    def test_a_driver_with_a_locked_channel_is_left_out(self):
        self.cmds.locked[LEG] = {"tz"}
        self.assertEqual(set(drag.plan(self.char)), {ROOT, POLE})

    def test_a_second_plan_is_the_cached_one(self):
        first = drag.plan(self.char)
        sets = self.cmds.sets
        self.assertIs(drag.plan(self.char), first)
        self.assertEqual(self.cmds.sets, sets)              # no probe

    def test_a_follow_blend_or_a_turned_parent_measures_again(self):
        self.cmds.follows[POLE] = {"followLeg": 10.0}
        first = drag.plan(self.char)
        sets = self.cmds.sets
        self.cmds.follows[POLE]["followLeg"] = 0.0
        self.assertIsNot(drag.plan(self.char), first)
        self.assertGreater(self.cmds.sets, sets)
        sets = self.cmds.sets
        self.cmds.P[LEG] = POLE_P
        drag.plan(self.char)
        self.assertGreater(self.cmds.sets, sets)

    def test_a_probe_that_fails_still_puts_every_translate_back(self):
        before = {n: list(v) for n, v in self.cmds.t.items()}
        self.cmds.xform_fail = 7               # base 3 reads, then 4 into the probes
        with self.assertRaises(RuntimeError):
            drag.plan(self.char)
        self.assertEqual(self.cmds.t, before)

    def test_the_cache_does_not_grow_without_end(self):
        cache = drag._state()["plans"]
        for i in range(65):
            cache[("old", i)] = {}
        a = drag.plan(self.char)
        self.assertEqual(list(cache.values()), [a])

    def test_the_follows_key_reads_only_follow_attributes(self):
        self.cmds.follows[POLE] = {"followLeg": 3.1234567891, "stretchy": 1.0}
        self.assertEqual(drag._follows([POLE]), ((POLE, "followLeg", 3.123457),))


# ------------------------------------------------------------------ move

class Move(DragCase):

    def setUp(self):
        super(Move, self).setUp()
        self.cmds.curves = {(ROOT, "tx"), (LEG, "ty"), (POLE, "tx")}

    def test_every_driver_lands_d_further_and_main_stays(self):
        before = {n: self.cmds.world(n) for n in (ROOT, LEG, POLE, MAIN)}
        d = (3.0, -1.0, 2.0)
        drag.move("|r|CenterOfMass", d)
        for node in (ROOT, LEG, POLE):
            self.assertVec(self.cmds.world(node),
                           tuple(b + x for b, x in zip(before[node], d)))
        self.assertEqual(self.cmds.world(MAIN), before[MAIN])

    def test_autokey_keys_the_moved_channels_that_already_have_curves(self):
        text = drag.move("|r|CenterOfMass", (3.0, -1.0, 2.0), autokey=True)
        #  the pole did not move: its curve gets no key
        self.assertEqual(sorted(self.cmds.keys), [(LEG, "ty"), (ROOT, "tx")])
        self.assertEqual(text, "Manny_Rig: CoM moved 3.74 cm - 2 control(s) - 2 key(s) set")

    def test_autokey_off_keys_nothing(self):
        text = drag.move("|r|CenterOfMass", (3.0, 0.0, 4.0), autokey=False)
        self.assertEqual(self.cmds.keys, [])
        self.assertEqual(text, "Manny_Rig: CoM moved 5.00 cm - 2 control(s)")

    def test_autokey_is_maya_s_when_not_given(self):
        self.cmds.autokey = False
        drag.move("|r|CenterOfMass", (1.0, 0.0, 0.0))
        self.assertEqual(self.cmds.keys, [])

    def test_the_move_is_one_undo_chunk(self):
        drag.move("|r|CenterOfMass", (1.0, 0.0, 0.0))
        self.assertEqual(self.cmds.chunks, ["open", "close"])

    def test_nothing_to_move_with_is_said_and_the_chunk_closed(self):
        self.patch(network, "drivers", lambda char: [])
        text = drag.move("|r|CenterOfMass", (1.0, 0.0, 0.0))
        self.assertEqual(text, "Manny_Rig: nothing to move the CoM with")
        self.assertEqual(self.cmds.chunks, ["open", "close"])

    def test_a_failing_plan_still_closes_the_chunk(self):
        self.cmds.xform_fail = 0
        with self.assertRaises(RuntimeError):
            drag.move("|r|CenterOfMass", (1.0, 0.0, 0.0))
        self.assertEqual(self.cmds.chunks, ["open", "close"])

    def test_the_summary_names_controls_once_without_their_paths(self):
        moved = [("|a|ns:IKLeg_L", "tx"), ("|a|ns:IKLeg_L", "ty"), ("|b|RootX_M", "tz")]
        self.assertEqual(drag.summary(self.char, (0.0, 0.0, 0.0), moved, []),
                         "Manny_Rig: CoM moved 0.00 cm - 2 control(s)")

    def test_com_of_reads_the_live_sum(self):
        self.cmds.attrs["sum1.output3D"] = [(1.0, 95.0, -2.0)]
        self.patch(network, "part", lambda group, name: "sum1")
        self.assertEqual(drag.com_of("|g"), (1.0, 95.0, -2.0))


# -------------------------------------------------- press, drag, release

def side_view(x, y):
    """An orthographic front camera: the ray through pixel (x, y)."""
    return (float(x), float(y), 100.0), (0.0, 0.0, -1.0)


class Interactive(DragCase):

    def setUp(self):
        super(Interactive, self).setUp()
        self.cmds.selection = ["|r|CenterOfMass|handle"]
        #  a drag of (6, 4, 0) moves the hips' ty and tz (their parent is turned)
        self.cmds.curves = {(ROOT, "tx"), (ROOT, "tz")}
        self.said = []
        self.clicked = []
        self.patch(drag, "_group_of_handle",
                   lambda p: "|r|CenterOfMass" if p.endswith("|handle") else None)
        self.patch(drag, "_ray", side_view)
        self.patch(drag, "_view_dir", lambda: (0.0, 0.0, -1.0))
        self.patch(drag, "com_of", lambda group: (0.0, 50.0, 0.0))
        self.patch(drag, "_say", self.said.append)
        self.patch(drag, "_click_select", lambda x, y: self.clicked.append((x, y)))
        self.start = {n: self.cmds.world(n) for n in (ROOT, LEG, POLE)}

    def press_drag(self, to, modifier="none"):
        self.cmds.modifier = modifier
        drag._press()
        self.cmds.drag_at = to
        drag._drag()

    def moved_by(self, d):
        for node in (ROOT, LEG, POLE):
            self.assertVec(self.cmds.world(node),
                           tuple(s + x for s, x in zip(self.start[node], d)))

    def test_a_drag_moves_the_com_with_the_mouse_in_the_view_plane(self):
        self.press_drag((16.0, 24.0, 0.0))
        self.moved_by((6.0, 4.0, 0.0))
        self.assertEqual(self.cmds.refreshes, [True])

    def test_shift_keeps_the_com_on_its_height(self):
        #  a side view's ray never meets the floor: the view plane, its height zeroed
        self.press_drag((16.0, 24.0, 0.0), modifier="shift")
        self.moved_by((6.0, 0.0, 0.0))

    def test_shift_from_above_follows_the_floor(self):
        self.patch(drag, "_ray", lambda x, y: ((float(x), 200.0, float(y)), (0.0, -1.0, 0.0)))
        self.patch(drag, "_view_dir", lambda: (0.0, -1.0, 0.0))
        self.press_drag((16.0, 24.0, 0.0), modifier="shift")
        self.moved_by((6.0, 0.0, 4.0))

    def test_ctrl_moves_it_straight_up_or_down(self):
        self.press_drag((16.0, 24.0, 0.0), modifier="ctrl")
        self.moved_by((0.0, 4.0, 0.0))

    def test_a_release_keys_what_autokey_would_and_says_so(self):
        self.press_drag((16.0, 24.0, 0.0))
        drag._release()
        self.assertEqual(self.cmds.keys, [(ROOT, "tz")])      # tx has a curve, did not move
        self.assertEqual(self.said, ["Manny_Rig: CoM moved 7.21 cm - 2 control(s)"
                                     " - 1 key(s) set"])
        self.assertIsNone(drag._state()["press"])

    def test_a_click_puts_the_body_back_and_selects_under_the_mouse(self):
        before = {n: list(v) for n, v in self.cmds.t.items()}
        self.press_drag((11.0, 21.0, 0.0))                 # 1.4 px: a click
        drag._release()
        self.assertEqual(self.cmds.t, before)
        self.assertEqual(self.clicked, [(10.0, 20.0)])
        self.assertEqual(self.cmds.keys, [])
        self.assertEqual(self.said, [])

    def test_the_drag_s_longest_reach_counts_not_where_it_ends(self):
        self.press_drag((40.0, 20.0, 0.0))
        self.cmds.drag_at = (10.5, 20.0, 0.0)              # back near the press point
        drag._drag()
        drag._release()
        self.assertEqual(self.clicked, [])
        self.assertEqual(len(self.said), 1)

    def test_a_press_on_two_handles_moves_nothing(self):
        self.patch(drag, "_group_of_handle", lambda p: p)
        self.cmds.selection = ["|a|CoM", "|b|CoM"]
        drag._press()
        self.assertEqual(self.said, ["Select one CoM handle to move it"])
        self.assertIsNone(drag._state()["press"])
        drag._drag()
        drag._release()
        self.assertEqual(self.cmds.sets, 0)
        self.assertEqual(self.clicked, [])

    def test_a_plan_that_fails_is_said(self):
        self.cmds.xform_fail = 0
        drag._press()
        self.assertEqual(len(self.said), 1)
        self.assertTrue(self.said[0].startswith("Manny_Rig: cannot move the CoM ("),
                        self.said[0])
        self.assertIsNone(drag._state()["press"])

    def test_a_release_with_no_press_does_nothing(self):
        drag._release()
        self.assertEqual((self.said, self.clicked, self.cmds.keys), ([], [], []))


class Say(DragCase):

    def test_the_card_and_the_viewport_both_hear_it(self):
        with mock.patch.object(panel, "status") as status:
            drag._say("moved")
        status.assert_called_once_with("moved")
        self.assertEqual(self.cmds.messages[0]["assistMessage"], "moved")

    def test_a_card_that_cannot_hear_does_not_stop_the_viewport(self):
        with mock.patch.object(panel, "status", side_effect=RuntimeError("gone")):
            drag._say("moved")
        self.assertEqual(len(self.cmds.messages), 1)

    def test_a_viewport_that_cannot_show_it_is_no_error(self):
        self.cmds.inViewMessage = mock.Mock(side_effect=RuntimeError("batch"))
        with mock.patch.object(panel, "status") as status:
            drag._say("moved")
        status.assert_called_once_with("moved")


# ----------------------------------------------------- OpenMaya's view

def fake_api(test, om, omui):
    """`import maya.api.OpenMaya(UI)` answer the fakes until the test ends."""
    import maya
    api = types.ModuleType("maya.api")
    api.__path__ = []
    api.OpenMaya, api.OpenMayaUI = om, omui
    for name, module in (("maya.api", api), ("maya.api.OpenMaya", om),
                         ("maya.api.OpenMayaUI", omui)):
        old = sys.modules.get(name, _MISSING)
        test.addCleanup(lambda n=name, o=old: (sys.modules.pop(n, None) if o is _MISSING
                                               else sys.modules.__setitem__(n, o)))
        sys.modules[name] = module
    p = mock.patch.object(maya, "api", api, create=True)
    p.start()
    test.addCleanup(p.stop)


class Point(object):
    def __init__(self):
        self.x = self.y = self.z = 0.0


class View(DragCase):

    def setUp(self):
        super(View, self).setUp()
        self.calls = []
        calls = self.calls

        class View3d(object):
            def viewToWorld(self, x, y, point, vector):
                calls.append((x, y))
                point.x, point.y, point.z = x * 1.0, y * 2.0, 100.0
                vector.x, vector.y, vector.z = 0.0, 0.0, -1.0

            def getCamera(self):
                return "perspShape"

        class MFnCamera(object):
            def __init__(self, cam):
                calls.append(cam)

            def viewDirection(self, space):
                v = Point()
                v.x, v.y, v.z = 0.0, -0.6, -0.8
                return v

        class MGlobal(object):
            kReplaceList = "replace"
            kSurfaceSelectMethod = "surface"
            fail = False

            @staticmethod
            def selectFromScreen(x, y, how, method):
                if MGlobal.fail:
                    raise RuntimeError("no view")
                calls.append(("select", x, y, how, method))

        self.MGlobal = MGlobal
        om = types.SimpleNamespace(MPoint=Point, MVector=Point, MFnCamera=MFnCamera,
                                   MSpace=types.SimpleNamespace(kWorld="world"),
                                   MGlobal=MGlobal)
        omui = types.SimpleNamespace(M3dView=types.SimpleNamespace(
            active3dView=lambda: View3d()))
        fake_api(self, om, omui)

    def test_the_ray_is_what_the_view_fills_in_at_whole_pixels(self):
        self.assertEqual(drag._ray(10.7, 20.2), ((10.0, 40.0, 100.0), (0.0, 0.0, -1.0)))
        self.assertEqual(self.calls, [(10, 20)])

    def test_the_view_direction_is_the_active_camera_s(self):
        self.assertEqual(drag._view_dir(), (0.0, -0.6, -0.8))
        self.assertEqual(self.calls, ["perspShape"])

    def test_a_click_selects_what_is_under_it_replacing(self):
        drag._click_select(12.9, 30.1)
        self.assertEqual(self.calls, [("select", 12, 30, "replace", "surface")])
        self.MGlobal.fail = True
        drag._click_select(1, 1)                           # never raises


# ------------------------------------------------- the tool comes and goes

class Tool(DragCase):

    def setUp(self):
        super(Tool, self).setUp()
        self.cmds.attrs.update({"|g|handle." + network.PART: "handle",
                                "|g|floor." + network.PART: "floor"})
        self.cmds.types["|g|handle|handleShape"] = "nurbsCurve"
        self.cmds.parents["|g|handle|handleShape"] = "|g|handle"
        self.patch(network, "group_of_part",
                   lambda path: "|g" if path.startswith("|g|") else None)

    def test_a_handle_or_its_shape_names_its_group(self):
        self.assertEqual(drag._group_of_handle("|g|handle"), "|g")
        self.assertEqual(drag._group_of_handle("|g|handle|handleShape"), "|g")

    def test_another_part_or_a_stranger_names_none(self):
        self.assertIsNone(drag._group_of_handle("|g|floor"))
        self.assertIsNone(drag._group_of_handle("|g|trail"))        # no part attribute
        self.assertIsNone(drag._group_of_handle("|pCube1"))

    def test_selecting_a_handle_puts_the_tool_on_and_remembers_the_last(self):
        self.cmds.selection = ["|g|handle"]
        self.cmds.tool = "moveSuperContext"
        drag.on_selection()
        self.assertEqual(self.cmds.tool, drag.CONTEXT)
        self.assertEqual(drag._state()["previous"], "moveSuperContext")
        self.assertEqual(self.cmds.contexts[0][0], "create")

    def test_selecting_a_handle_again_changes_nothing(self):
        self.cmds.selection = ["|g|handle"]
        self.cmds.tool = drag.CONTEXT
        drag.on_selection()
        self.assertEqual(self.cmds.tools, [])

    def test_selecting_anything_else_gives_the_last_tool_back(self):
        self.cmds.selection = ["|g|handle"]
        self.cmds.tool = "moveSuperContext"
        drag.on_selection()
        self.cmds.selection = ["|pCube1"]
        drag.on_selection()
        self.assertEqual(self.cmds.tool, "moveSuperContext")
        self.assertIsNone(drag._state()["previous"])

    def test_with_no_last_tool_it_is_select(self):
        self.cmds.tool = drag.CONTEXT
        drag.on_selection()
        self.assertEqual(self.cmds.tool, "selectSuperContext")

    def test_another_tool_is_left_alone_when_no_handle_is_selected(self):
        self.cmds.tool = "RotateSuperContext"
        drag.on_selection()
        self.assertEqual(self.cmds.tools, [])

    def test_w_with_a_handle_selected_bounces_back_to_the_tool(self):
        self.cmds.selection = ["|g|handle"]
        self.cmds.tool = "moveSuperContext"
        drag.on_tool()
        self.assertEqual(len(self.cmds.deferred), 1)
        self.cmds.deferred[0]()
        self.assertEqual(self.cmds.tool, drag.CONTEXT)

    def test_a_tool_change_without_a_handle_stays(self):
        self.cmds.tool = "moveSuperContext"
        drag.on_tool()
        self.assertEqual(self.cmds.deferred, [])

    def test_the_context_is_made_once_then_edited(self):
        self.assertEqual(drag.ensure_context(), drag.CONTEXT)
        drag.ensure_context()
        (kind1, name, kw), (kind2, _n, _k) = self.cmds.contexts
        self.assertEqual((kind1, kind2), ("create", "edit"))
        self.assertEqual(kw["name"], drag.CONTEXT)
        self.assertEqual(kw["undoMode"], "all")
        self.assertIs(kw["pressCommand"], drag._press)
        self.assertIs(kw["dragCommand"], drag._drag)
        self.assertIs(kw["releaseCommand"], drag._release)

    def test_start_hangs_two_jobs_in_the_root_scope_and_forgets_the_plans(self):
        drag._state()["plans"]["stale"] = {}
        with hubcopy.entered(hubcopy.Scope("hubcopyTest")):
            drag.start()
        made = sorted(self.cmds.jobs.values(), key=lambda j: j[0])
        self.assertEqual(made, [("SelectionChanged", drag.on_selection, None),
                                ("ToolChanged", drag.on_tool, None)])
        self.assertEqual(drag._state()["plans"], {})

    def test_a_second_start_kills_the_first_jobs(self):
        drag.start()
        first = list(drag._state()["jobs"])
        drag.start()
        self.assertEqual(self.cmds.killed, first)
        self.assertEqual(len(self.cmds.jobs), 2)

    def test_stop_survives_a_job_maya_no_longer_knows(self):
        self.cmds.jobs = {"boom": None, 7: None}
        drag._state()["jobs"] = ["boom", 7]
        drag.stop()
        self.assertEqual(self.cmds.killed, [7])
        self.assertEqual(drag._state()["jobs"], [])


if __name__ == "__main__":
    unittest.main()
