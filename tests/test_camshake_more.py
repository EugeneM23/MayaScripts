"""Camera Shake's scene half (maya_camshake, section 3) on a small fake scene: which camera a press takes and
over which frames, what drives a channel, what a shake keys on its layer and where, a re-tune keeping its layer,
an Apply replacing the shake of its mode, the undo chunk; and the card's last controls."""

import copy
import json
import math
import os
import sys
import types
import unittest
from unittest import mock

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.join(os.path.dirname(HERE), "SkeldarAnim")
if PLUGIN not in sys.path:
    sys.path.insert(0, PLUGIN)

import maya_camshake as cs  # noqa: E402

try:
    import maya.api.OpenMaya  # noqa: F401
    HAVE_API = True
except ImportError:
    HAVE_API = False


class Scene(object):
    """maya.cmds over a few transforms, cameras and additive layers.

    A node: its type, parent, attributes (rotate/translate triples, rotateAxis, jointOrient, rotateOrder),
    its locks and markers. A layer: the plugs it holds, a curve per keyed plug, lock, mute, weight, selected.
    A curve: {time: value}, held flat past its ends. A channel shows its node's value plus every unmuted
    layer's curve times its weight. `wires` / `types` model what listConnections / nodeType answer for the
    driver tests. openChunk snapshots the scene; undo() puts the last closed chunk's snapshot back."""

    def __init__(self):
        self.nodes = {}
        self.layers = {}
        self.curves = {}
        self.wires = {}
        self.types = {}
        self.selection = []
        self.calls = []
        self.uuids = 0
        self.chunks = []
        self.closed = []
        self.undo_on = True
        self.unit = "deg"
        self.batch = True
        self.playback = (1.0, 48.0)
        self.time = 10.0
        self.dirtied = []
        self.tangents = []

    # -- building
    def add(self, path, kind="transform", parent=None, rotate=(0.0, 0.0, 0.0), translate=(0.0, 0.0, 0.0),
            order=0, axis=(0.0, 0.0, 0.0), orient=(0.0, 0.0, 0.0), markers=()):
        self.uuids += 1
        self.nodes[path] = {"type": kind, "parent": parent, "uuid": "UUID%d" % self.uuids,
                            "rotate": list(rotate), "translate": list(translate), "rotateOrder": order,
                            "rotateAxis": list(axis), "jointOrient": list(orient), "locks": set(),
                            "markers": set(markers)}
        return path

    def camera(self, path, markers=()):
        self.add(path, markers=markers)
        self.add(path + "|" + path.split("|")[-1] + "Shape", kind="camera", parent=path)
        return path

    # -- helpers
    def _path(self, name):
        if name in self.nodes:
            return name
        for path, node in self.nodes.items():
            if path.split("|")[-1] == name.split("|")[-1] or node["uuid"] == name:
                return path
        return None

    def _curve_at(self, curve, time):
        keys = self.curves[curve]
        times = sorted(keys)
        if time <= times[0]:
            return keys[times[0]]
        if time >= times[-1]:
            return keys[times[-1]]
        for lo, hi in zip(times, times[1:]):
            if lo <= time <= hi:
                k = (time - lo) / float(hi - lo)
                return keys[lo] + (keys[hi] - keys[lo]) * k
        return 0.0

    def shown(self, node, attr, time):
        """What a channel shows at a time: the node's value and every unmuted layer on top."""
        base, axis = attr[:-1], "XYZ".index(attr[-1])
        value = self.nodes[node][base][axis]
        for layer in self.layers.values():
            curve = layer["curves"].get("%s.%s" % (node, attr))
            if curve and not layer["mute"]:
                value += self._curve_at(curve, time) * layer["weight"]
        return value

    # -- cmds
    def about(self, batch=False, **_kw):
        return self.batch

    def currentUnit(self, query=False, angle=False, **_kw):  # noqa: N802
        return self.unit

    def playbackOptions(self, query=False, minTime=False, maxTime=False, **_kw):  # noqa: N802
        return self.playback[0] if minTime else self.playback[1]

    def currentTime(self, query=False, **_kw):  # noqa: N802
        return self.time

    def objExists(self, name):  # noqa: N802
        return self._path(name) is not None or name in self.layers or name in self.curves

    def ls(self, *args, **kw):
        if kw.get("type") == "camera":
            return [p for p, n in self.nodes.items() if n["type"] == "camera"]
        if kw.get("type") == "animLayer":
            return list(self.layers)
        if kw.get("selection"):
            return list(self.selection)
        if not args:
            return []
        names = args[0] if isinstance(args[0], (list, tuple)) else [args[0]]
        out = []
        for name in names:
            if name in self.layers:
                out.append(self.layers[name]["uuid"] if kw.get("uuid") else name)
                continue
            if name in [layer["uuid"] for layer in self.layers.values()]:
                out.append([n for n, layer in self.layers.items() if layer["uuid"] == name][0])
                continue
            path = self._path(name)
            if path is None:
                continue
            out.append(self.nodes[path]["uuid"] if kw.get("uuid") else path)
        return out

    def listRelatives(self, node, parent=False, shapes=False, type=None, **_kw):  # noqa: N802,A002
        path = self._path(node)
        if parent:
            up = self.nodes[path]["parent"]
            return [up] if up else []
        if shapes:
            return [p for p, n in self.nodes.items() if n["parent"] == path and n["type"] == "camera"
                    and (type is None or n["type"] == type)]
        return []

    def attributeQuery(self, attr, node=None, exists=False):  # noqa: N802
        if node in self.layers:
            return attr == cs.LAYER_MARKER and self.layers[node]["marker"] is not None
        path = self._path(node)
        return path is not None and attr in self.nodes[path]["markers"]

    def objectType(self, node, isAType=None):  # noqa: N802,N803
        if node in self.types:
            kind = self.types[node]
            return isAType in ("constraint",) and kind.endswith("Constraint") or kind == isAType
        path = self._path(node)
        kind = self.nodes[path]["type"]
        if isAType == "shape":
            return kind == "camera"
        if isAType == "transform":
            return kind in ("transform", "joint")
        return kind == isAType

    def nodeType(self, node):  # noqa: N802
        if node in self.types:
            return self.types[node]
        if node in self.layers:
            return "animLayer"
        if node in self.curves:
            return "animCurveTA"
        return self.nodes[self._path(node)]["type"]

    def listConnections(self, plug, source=True, destination=False, type=None, **_kw):  # noqa: N802,A002
        if plug.endswith(".weight") and plug[:-7] in self.layers:
            curve = self.layers[plug[:-7]].get("weight_curve")
            return [curve] if curve else []
        return list(self.wires.get(plug, []))

    def dgdirty(self, nodes):
        self.dirtied.append(list(nodes))

    def getAttr(self, plug, time=None, lock=False, **_kw):  # noqa: N802
        node, attr = plug.rsplit(".", 1)
        if node in self.layers:
            layer = self.layers[node]
            return layer["weight"] if attr == "weight" else layer["marker"]
        path = self._path(node)
        if lock:
            return attr in self.nodes[path]["locks"]
        if attr in ("rotate", "translate"):
            return [tuple(self.shown(path, attr + a, time if time is not None else self.time) for a in "XYZ")]
        if attr in ("rotateAxis", "jointOrient"):
            return [tuple(self.nodes[path][attr])]
        return self.nodes[path][attr]

    def setAttr(self, plug, *values, **kw):  # noqa: N802
        self.calls.append(("setAttr", plug, values, kw))
        node, attr = plug.rsplit(".", 1)
        if node in self.layers:
            if attr == cs.LAYER_MARKER:
                self.layers[node]["marker"] = values[0]
            else:
                self.layers[node][attr] = values[0]

    def addAttr(self, node, longName=None, **_kw):  # noqa: N802,N803
        self.layers[node]["marker"] = ""

    def animLayer(self, name, query=False, edit=False, lock=None, mute=False, selected=False,  # noqa: N802
                  findCurveForPlug=None, attribute=None, removeAttribute=None, **_kw):
        if not query and not edit:
            self.uuids += 1
            self.layers[name] = {"plugs": set(), "curves": {}, "lock": False, "mute": False, "weight": 1.0,
                                 "selected": False, "marker": None, "uuid": "LAYER%d" % self.uuids}
            return name
        layer = self.layers[name]
        if query:
            if findCurveForPlug is not None:
                curve = layer["curves"].get(findCurveForPlug)
                return [curve] if curve else None
            if lock:
                return layer["lock"]
            if mute:
                return layer["mute"]
            if selected:
                return layer["selected"]
            return None
        if lock is not None:
            layer["lock"] = bool(lock)
        if attribute is not None:
            assert not layer["lock"], "a locked layer takes no attribute"
            layer["plugs"].update(attribute)
        if removeAttribute is not None:
            assert not layer["lock"], "a locked layer gives no attribute back"
            for plug in removeAttribute:
                layer["plugs"].discard(plug)
                curve = layer["curves"].pop(plug, None)
                self.curves.pop(curve, None)
        return None

    def setKeyframe(self, target, attribute=None, animLayer=None, time=None, value=None,  # noqa: N802,N803
                    identity=False, **_kw):
        if animLayer is not None:
            layer = self.layers[animLayer]
            assert not layer["lock"], "a locked layer takes no key"
            plug = "%s.%s" % (target, attribute)
            assert plug in layer["plugs"], plug
            curve = "%s_%s_%s" % (animLayer, target.split("|")[-1], attribute)
            self.curves[curve] = {float(time): 0.0}
            layer["curves"][plug] = curve
            return 1
        self.curves[target][float(time)] = float(value)
        return 1

    def keyTangent(self, curve, time=None, **kw):  # noqa: N802
        self.tangents.append((curve, time, kw))

    def keyframe(self, curve, query=False, eval=False, time=None, **_kw):  # noqa: A002
        return [self._curve_at(curve, time[0])]

    def delete(self, name):
        self.layers.pop(name)

    def undoInfo(self, openChunk=False, closeChunk=False, query=False, state=False, **_kw):  # noqa: N802,N803
        if openChunk:
            self.chunks.append(copy.deepcopy((self.layers, self.curves)))
        if closeChunk:
            self.closed.append(self.chunks.pop())
        if query and state:
            return self.undo_on
        return None

    def undo(self):
        self.layers, self.curves = self.closed.pop()


FPS = None


class SceneTest(unittest.TestCase):
    def setUp(self):
        self.scene = Scene()
        saved_cmds = cs.cmds
        cs.cmds = self.scene
        self.addCleanup(setattr, cs, "cmds", saved_cmds)
        state = cs._state()
        saved = dict(state)
        self.addCleanup(lambda: (state.clear(), state.update(saved)))
        state["picked"] = None

    def patch(self, target, name, value, create=False):
        patcher = mock.patch.object(target, name, value, create=create)
        patcher.start()
        self.addCleanup(patcher.stop)


@unittest.skipUnless(HAVE_API, "needs maya.api.OpenMaya")
class Units(SceneTest):
    def test_the_frame_rate_and_the_length_unit_are_mayas(self):
        self.assertGreater(cs.frame_rate(), 0.0)
        self.assertAlmostEqual(cs.cm_to_ui(), 1.0)

    def test_degrees_or_radians(self):
        self.assertEqual(cs.deg_to_ui(), 1.0)
        self.scene.unit = "rad"
        self.assertAlmostEqual(cs.deg_to_ui(), math.pi / 180.0)


class Highlight(SceneTest):
    def test_batch_has_no_highlight(self):
        self.assertIsNone(cs.highlight())

    def test_the_time_bar_is_asked_first(self):
        self.scene.batch = False
        bar = types.SimpleNamespace(active=lambda: True, highlight=lambda: (12.0, 20.0))
        with mock.patch.dict(sys.modules, {"maya_timebar": bar}):
            self.assertEqual(cs.highlight(), (12, 19))
            bar.highlight = lambda: None
            self.assertIsNone(cs.highlight())

    def _slider(self, visible, start, end):
        import maya.mel
        self.patch(maya.mel, "eval", lambda text: "timeControl1", create=True)

        def time_control(name, query=False, rangeVisible=False, rangeArray=False):
            self.assertEqual(name, "timeControl1")
            return visible if rangeVisible else [start, end]
        self.patch(self.scene, "timeControl", time_control, create=True)

    def test_mayas_slider_when_the_time_bar_is_not_ours(self):
        self.scene.batch = False
        bar = types.SimpleNamespace(active=lambda: False, highlight=lambda: (1, 2))
        self._slider(True, 30.0, 41.0)
        with mock.patch.dict(sys.modules, {"maya_timebar": bar}):
            self.assertEqual(cs.highlight(), (30, 40))

    def test_a_time_bar_that_raises_falls_back_to_the_slider(self):
        self.scene.batch = False

        def broken():
            raise RuntimeError("no bar")
        bar = types.SimpleNamespace(active=broken)
        self._slider(True, 5.0, 9.0)
        with mock.patch.dict(sys.modules, {"maya_timebar": bar}):
            self.assertEqual(cs.highlight(), (5, 8))

    def test_no_range_shown_is_none(self):
        self.scene.batch = False
        self._slider(False, 5.0, 9.0)
        with mock.patch.dict(sys.modules, {"maya_timebar": None}):
            self.assertIsNone(cs.highlight())

    def test_a_one_frame_highlight_is_none(self):
        self.scene.batch = False
        self._slider(True, 5.0, 6.0)
        with mock.patch.dict(sys.modules, {"maya_timebar": None}):
            self.assertIsNone(cs.highlight())

    def test_a_slider_that_cannot_be_read_is_none(self):
        self.scene.batch = False
        import maya.mel

        def broken(text):
            raise RuntimeError("no slider")
        self.patch(maya.mel, "eval", broken, create=True)
        with mock.patch.dict(sys.modules, {"maya_timebar": None}):
            self.assertIsNone(cs.highlight())


class Frames(SceneTest):
    def test_given_frames_win(self):
        self.assertEqual(cs.frames_for("handheld", cs.settings("handheld"), (3, 9)), (3, 9, ""))

    def test_the_highlight_comes_next(self):
        self.patch(cs, "highlight", lambda: (20, 30))
        self.assertEqual(cs.frames_for("impact", cs.settings("impact")), (20, 30, "the highlight"))

    def test_a_handheld_takes_the_playback_range(self):
        self.patch(cs, "highlight", lambda: None)
        self.scene.playback = (0.9999999, 72.0000001)
        self.assertEqual(cs.frames_for("handheld", cs.settings("handheld")), (1, 72, "the playback range"))

    def test_an_impact_takes_the_current_frame_and_its_length(self):
        self.patch(cs, "highlight", lambda: None)
        self.scene.time = 40.0
        s = cs.settings("impact", {"length": 30})
        self.assertEqual(cs.frames_for("impact", s), (40, 70, "the current frame + Length"))

    def test_a_shake_needs_two_frames(self):
        with self.assertRaises(cs.Refused) as raised:
            cs.frames_for("impact", cs.settings("impact"), (5, 5))
        self.assertIn("at least 2 frames", str(raised.exception))


class Targets(SceneTest):
    def test_the_selection_shapes_counting_as_their_transforms(self):
        self.scene.camera("|camA")
        self.scene.camera("|camB")
        self.scene.selection = ["|camA|camAShape", "|camB", "|camA"]
        self.assertEqual(cs.targets(), ["|camA", "|camB"])

    def test_a_given_selection_and_an_empty_one(self):
        self.scene.camera("|camA")
        self.scene.camera("|ours", markers=[cs.OUR_CAMERA])
        self.assertEqual(cs.targets(["|camA"]), ["|camA"])
        self.assertEqual(cs.targets([]), ["|ours"])

    def test_nothing_selected_takes_our_only_camera(self):
        self.scene.camera("|plain")
        self.scene.camera("|Manny_Rig:SceneSetup_camera", markers=[cs.OUR_CAMERA])
        self.assertEqual(cs.our_cameras(), ["|Manny_Rig:SceneSetup_camera"])
        self.assertEqual(cs.targets(), ["|Manny_Rig:SceneSetup_camera"])

    def test_two_of_ours_are_named(self):
        self.scene.camera("|a:SceneSetup_camera", markers=[cs.OUR_CAMERA])
        self.scene.camera("|b:SceneSetup_camera", markers=[cs.OUR_CAMERA])
        with self.assertRaises(cs.Refused) as raised:
            cs.targets()
        self.assertIn("2 cameras of ours", str(raised.exception))
        self.assertIn("a:SceneSetup_camera", str(raised.exception))

    def test_none_of_ours_asks_for_a_camera(self):
        self.scene.camera("|plain")
        with self.assertRaisesRegex(cs.Refused, "select a camera to shake"):
            cs.targets()


class Drivers(SceneTest):
    def setUp(self):
        super(Drivers, self).setUp()
        self.scene.camera("|cam")

    def test_keys_and_layers_are_no_foreign_driver(self):
        self.scene.wires["|cam.rotateX"] = ["cam_rotateX"]
        self.scene.types["cam_rotateX"] = "animCurveTA"
        self.scene.wires["|cam.rotateY"] = ["blend1"]
        self.scene.types["blend1"] = "animBlendNodeAdditiveRotation"
        #  a layer's rotation blend reads its owner's rotateOrder: the owner is no driver
        self.scene.wires["blend1"] = ["curveA", "Anim1", "|cam", "blend1"]
        self.scene.types["curveA"] = "animCurveTA"
        self.scene.types["Anim1"] = "animLayer"
        self.assertIsNone(cs.foreign_driver("|cam", "rotateX"))
        self.assertIsNone(cs.foreign_driver("|cam", "rotateY"))
        self.assertEqual(sorted(cs._upstream_curves("|cam", cs.ROTATE)), ["cam_rotateX", "curveA"])

    def test_a_constraint_through_a_layer_is_found(self):
        self.scene.wires["|cam.rotate"] = ["blend1"]
        self.scene.types["blend1"] = "animBlendNodeAdditiveRotation"
        self.scene.wires["blend1"] = ["pc1"]
        self.scene.types["pc1"] = "parentConstraint"
        self.assertEqual(cs.foreign_driver("|cam", "rotateZ"), "pc1")

    def test_a_constraint_from_another_camera_says_to_select_that_one(self):
        self.scene.camera("|lead")
        self.scene.wires["pc1"] = ["|lead"]
        self.scene.types["pc1"] = "parentConstraint"
        text = cs._driver_message("|cam", "rotateX", "pc1")
        self.assertIn("cam.rotateX is driven by pc1 (parentConstraint)", text)
        self.assertTrue(text.endswith("select lead, which drives it"), text)

    def test_any_other_driver_wants_keys_or_free_channels(self):
        self.scene.types["expr1"] = "expression"
        self.assertTrue(cs._driver_message("|cam", "rotateX", "expr1").endswith("keyed or free"))

    def test_a_driven_channel_refuses_the_press_by_name(self):
        self.scene.wires["|cam.rotateY"] = ["expr1"]
        self.scene.types["expr1"] = "expression"
        with self.assertRaisesRegex(cs.Refused, "cam.rotateY is driven by expr1"):
            cs._channels("|cam", "handheld", cs.settings("handheld"), None)


class Channels(SceneTest):
    def setUp(self):
        super(Channels, self).setUp()
        self.scene.camera("|cam")

    def test_rotate_only_unless_the_shake_moves_the_camera(self):
        keep, locked = cs._channels("|cam", "handheld", cs.settings("handheld", {"drift": 0.0}), None)
        self.assertEqual((keep, locked), (list(cs.ROTATE), []))
        keep, _ = cs._channels("|cam", "impact", cs.settings("impact", {"push": 3.0}), None)
        self.assertEqual(keep, list(cs.ROTATE + cs.TRANSLATE))

    def test_a_layer_already_holding_translate_keeps_it(self):
        layer = self.scene.animLayer("L")
        self.scene.layers[layer]["curves"]["|cam.translateY"] = "c"
        keep, _ = cs._channels("|cam", "handheld", cs.settings("handheld", {"drift": 0.0}), layer)
        self.assertIn("translateY", keep)

    def test_locked_channels_are_skipped(self):
        self.scene.nodes["|cam"]["locks"] = {"rotateZ", "translateX"}
        keep, locked = cs._channels("|cam", "impact", cs.settings("impact", {"push": 1.0}), None)
        self.assertEqual(locked, ["rotateZ", "translateX"])
        self.assertNotIn("rotateZ", keep)

    def test_a_locked_rotate_refuses(self):
        self.scene.nodes["|cam"]["locks"] = set(cs.ROTATE)
        with self.assertRaisesRegex(cs.Refused, "cam's rotate is locked"):
            cs._channels("|cam", "handheld", cs.settings("handheld"), None)


class Static(SceneTest):
    def test_the_rotate_order_axis_and_a_joints_orient(self):
        self.scene.add("|j", kind="joint", order=2, axis=(10.0, 0.0, 0.0), orient=(0.0, 30.0, 0.0))
        order, axis, orient = cs._static("|j")
        self.assertEqual(order, "zxy")
        self.assertEqual(list(axis), [10.0, 0.0, 0.0])
        self.assertEqual(list(orient), [0.0, 30.0, 0.0])

    def test_a_transform_has_no_orient_and_radians_are_read_as_degrees(self):
        self.scene.add("|t", axis=(math.pi / 2.0, 0.0, 0.0), orient=(1.0, 1.0, 1.0))
        self.scene.unit = "rad"
        _order, axis, orient = cs._static("|t")
        self.assertAlmostEqual(axis[0], 90.0)
        self.assertEqual(list(orient), [0.0, 0.0, 0.0])


class LayerShare(SceneTest):
    def setUp(self):
        super(LayerShare, self).setUp()
        self.scene.camera("|cam", )
        self.scene.nodes["|cam"]["rotate"] = [5.0, 10.0, 0.0]
        self.layer = self.scene.animLayer("L")
        self.scene.curves["c"] = {0.0: 2.0, 10.0: 4.0}
        self.scene.layers["L"]["curves"]["|cam.rotateY"] = "c"

    def test_a_layers_share_is_its_curve_times_its_weight(self):
        self.scene.layers["L"]["weight"] = 0.5
        share = cs._layer_share("L", "|cam", "rotateY", [0, 5, 10])
        self.assertEqual(list(share), [1.0, 1.5, 2.0])

    def test_a_keyed_weight_is_read_per_frame(self):
        self.scene.curves["w"] = {0.0: 0.0, 10.0: 1.0}
        self.scene.layers["L"]["weight_curve"] = "w"
        self.assertEqual(list(cs._layer_share("L", "|cam", "rotateY", [0, 10])), [0.0, 4.0])

    def test_muted_gone_or_not_holding_the_channel_is_nothing(self):
        self.assertEqual(list(cs._layer_share("L", "|cam", "rotateX", [0, 1])), [0.0, 0.0])
        self.assertEqual(list(cs._layer_share(None, "|cam", "rotateY", [0])), [0.0])
        self.assertEqual(list(cs._layer_share("gone", "|cam", "rotateY", [0])), [0.0])
        self.scene.layers["L"]["mute"] = True
        self.assertEqual(list(cs._layer_share("L", "|cam", "rotateY", [0])), [0.0])

    def test_the_base_is_what_shows_without_this_layer(self):
        base = cs.base_rotations("|cam", "L", [0, 10])
        np.testing.assert_allclose(base, [[5.0, 10.0, 0.0], [5.0, 10.0, 0.0]])
        shown = cs.base_rotations("|cam", None, [0, 10])
        np.testing.assert_allclose(shown, [[5.0, 12.0, 0.0], [5.0, 14.0, 0.0]])

    def test_curves_upstream_are_dirtied_first(self):
        self.scene.wires["|cam.rotateY"] = ["c"]
        cs.base_rotations("|cam", "L", [0])
        self.assertEqual(self.scene.dirtied, [["c"]])

    def test_no_layers_at_all_finds_no_curve(self):
        def no_layers(*args, **kw):
            raise RuntimeError("A single anim layer node must be specified")
        self.patch(self.scene, "animLayer", no_layers)
        self.assertIsNone(cs._find_curve("L", "|cam.rotateY"))


class Keys(SceneTest):
    def test_every_frame_spline_zero_a_frame_outside_and_straight_edges(self):
        self.scene.curves["c"] = {}
        frames = np.arange(10, 14)
        cs._key("c", frames, [1.0, 2.0, 3.0, 4.0])
        self.assertEqual(self.scene.curves["c"], {9.0: 0.0, 10.0: 1.0, 11.0: 2.0, 12.0: 3.0, 13.0: 4.0,
                                                  14.0: 0.0})
        edges = [(time, kw) for _c, time, kw in self.scene.tangents if "lock" not in kw]
        self.assertEqual(edges, [((10, 10), {"inTangentType": "linear"}),
                                 ((13, 13), {"outTangentType": "linear"})])


def expected(mode, s, a, b, base, index=0, order="xyz"):
    frames = np.arange(a, b + 1)
    rot, off = cs.shake(mode, frames, a, b, cs.frame_rate(), s, index)
    return cs.deltas(rot, off * cs.cm_to_ui(), base, order)


@unittest.skipUnless(HAVE_API, "needs maya.api.OpenMaya")
class Press(SceneTest):
    """apply / retune / delete on the scene."""

    def setUp(self):
        super(Press, self).setUp()
        self.scene.camera("|cam")
        self.scene.nodes["|cam"]["rotate"] = [-10.0, 25.0, 0.0]
        self.scene.camera("|cam2")
        self.scene.selection = ["|cam"]

    def curve_values(self, layer, node, attr, frames):
        curve = self.scene.layers[layer]["curves"]["%s.%s" % (node, attr)]
        return np.array([self.scene._curve_at(curve, f) for f in frames])

    def assert_keys(self, layer, node, mode, s, a, b, base, index=0):
        dr, dt = expected(mode, s, a, b, np.tile(base, (b - a + 1, 1)), index)
        frames = np.arange(a, b + 1)
        for i, attr in enumerate(cs.ROTATE):
            np.testing.assert_allclose(self.curve_values(layer, node, attr, frames), dr[:, i], atol=1e-9)
            self.assertEqual(self.curve_values(layer, node, attr, [a - 1, b + 1]).tolist(), [0.0, 0.0])
        return dr, dt

    def test_apply_keys_a_new_locked_layer_named_for_its_frames(self):
        s = {"strength": 5.0, "push": 0.0, "rattle": 0.0, "direction": "Left"}
        layer, text = cs.apply("impact", s, frames=(40, 60))
        self.assertEqual(layer, "CamShake_Impact_40_60")
        info = self.scene.layers[layer]
        self.assertTrue(info["lock"])
        self.assertEqual(sorted(info["plugs"]), sorted("|cam." + a for a in cs.ROTATE))
        self.assertTrue(any(c[1] == layer + ".rotationAccumulationMode" and c[2] == (0,)
                            for c in self.scene.calls))
        data = cs.record(layer)
        self.assertEqual((data["mode"], data["frames"], data["targets"]),
                         ("impact", [40, 60], [self.scene.nodes["|cam"]["uuid"]]))
        self.assertEqual(data["settings"]["strength"], 5.0)
        dr, _ = self.assert_keys(layer, "|cam", "impact", cs.settings("impact", s), 40, 60, [-10.0, 25.0, 0.0])
        self.assertGreater(np.abs(dr).max(), 1.0)
        self.assertEqual(cs.picked(), layer)
        self.assertIn("Impact from the left: 5.0 deg", text)
        self.assertIn("on cam, frames 40-60", text)
        self.assertIn("layer CamShake_Impact_40_60", text)

    def test_the_camera_shows_the_base_plus_the_shake(self):
        s = cs.settings("handheld", {"drift": 0.0})
        layer, _ = cs.apply("handheld", s, frames=(1, 30))
        dr, _ = expected("handheld", s, 1, 30, np.tile([-10.0, 25.0, 0.0], (30, 1)))
        shown = np.array([[self.scene.shown("|cam", a, f) for a in cs.ROTATE] for f in range(1, 31)])
        np.testing.assert_allclose(shown, [-10.0, 25.0, 0.0] + dr, atol=1e-9)
        self.assertEqual(self.scene.shown("|cam", "rotateY", 0), 25.0)          # nothing outside
        self.assertEqual(self.scene.shown("|cam", "rotateY", 31), 25.0)

    def test_a_push_keys_translate_too(self):
        s = cs.settings("impact", {"push": 4.0, "direction": "Front"})
        layer, _ = cs.apply("impact", s, frames=(10, 30))
        _dr, dt = self.assert_keys(layer, "|cam", "impact", s, 10, 30, [-10.0, 25.0, 0.0])
        for i, attr in enumerate(cs.TRANSLATE):
            np.testing.assert_allclose(self.curve_values(layer, "|cam", attr, np.arange(10, 31)), dt[:, i],
                                       atol=1e-9)
        self.assertGreater(np.abs(dt).max(), 1.0)

    def test_two_cameras_shake_each_their_own_way(self):
        self.scene.selection = ["|cam", "|cam2"]
        s = cs.settings("handheld", {"drift": 0.0})
        layer, text = cs.apply("handheld", s, frames=(1, 40))
        self.assert_keys(layer, "|cam", "handheld", s, 1, 40, [-10.0, 25.0, 0.0], index=0)
        self.assert_keys(layer, "|cam2", "handheld", s, 1, 40, [0.0, 0.0, 0.0], index=1)
        self.assertIn("on cam, cam2", text)

    def test_a_retune_keeps_the_layer_its_weight_and_its_lock(self):
        layer, _ = cs.apply("impact", {"strength": 3.0, "push": 0.0}, frames=(40, 60))
        self.scene.layers[layer]["weight"] = 0.5                  # the strength dial
        text = cs.retune(layer, {"strength": 8.0, "push": 0.0, "decay": "Linear"})
        self.assertEqual(list(self.scene.layers), [layer])
        self.assertEqual(self.scene.layers[layer]["weight"], 0.5)
        self.assertTrue(self.scene.layers[layer]["lock"])
        #  re-keyed on the base WITHOUT its own share: the same keys a fresh apply would make
        s = cs.settings("impact", {"strength": 8.0, "push": 0.0, "decay": "Linear"})
        self.assert_keys(layer, "|cam", "impact", s, 40, 60, [-10.0, 25.0, 0.0])
        self.assertEqual(cs.record(layer)["settings"]["decay"], "Linear")
        self.assertIn("8.0 deg", text)
        self.assertIn("linear decay", text)

    def test_a_retune_of_an_unlocked_layer_leaves_it_unlocked(self):
        layer, _ = cs.apply("handheld", {"drift": 0.0}, frames=(1, 10))
        self.scene.layers[layer]["lock"] = False
        cs.retune(layer, {"drift": 0.0, "sway": 2.0})
        self.assertFalse(self.scene.layers[layer]["lock"])

    def test_a_retune_refuses_what_is_not_ours_or_lost_its_camera(self):
        with self.assertRaisesRegex(cs.Refused, "not a shake of ours"):
            cs.retune("nothing", {})
        layer, _ = cs.apply("handheld", {"drift": 0.0}, frames=(1, 10))
        del self.scene.nodes["|cam"]
        with self.assertRaisesRegex(cs.Refused, "a camera of %s is gone" % layer):
            cs.retune(layer, {})

    def test_an_apply_replaces_the_shake_of_its_mode_and_leaves_the_other(self):
        first, _ = cs.apply("impact", {"push": 0.0}, frames=(40, 60))
        hand, _ = cs.apply("handheld", {"drift": 0.0}, frames=(1, 80))
        second, text = cs.apply("impact", {"push": 0.0}, frames=(70, 90))
        self.assertNotIn(first, self.scene.layers)
        self.assertEqual(sorted(self.scene.layers), sorted([hand, second]))
        self.assertIn("replaced %s" % first, text)
        self.assertEqual(cs.picked(), second)

    def test_a_shared_layer_keeps_the_other_camera(self):
        self.scene.selection = ["|cam", "|cam2"]
        first, _ = cs.apply("impact", {"push": 0.0}, frames=(40, 60))
        self.scene.selection = ["|cam"]
        second, text = cs.apply("impact", {"push": 0.0}, frames=(40, 60))
        self.assertEqual(second, "CamShake_Impact_40_60_v2")          # the name was still taken
        self.assertIn(first, self.scene.layers)
        self.assertEqual(sorted(self.scene.layers[first]["curves"]), sorted("|cam2." + a for a in cs.ROTATE))
        self.assertEqual(cs.record(first)["targets"], [self.scene.nodes["|cam2"]["uuid"]])
        self.assertTrue(self.scene.layers[first]["lock"])
        self.assertIn("%s (other cameras kept)" % first, text)

    def test_nothing_selected_takes_the_picked_shakes_cameras(self):
        layer, _ = cs.apply("impact", {"push": 0.0}, frames=(40, 60))
        self.scene.selection = []
        self.assertEqual(cs.apply_targets("impact"), ["|cam"])
        with self.assertRaisesRegex(cs.Refused, "select a camera"):
            cs.apply_targets("handheld")                            # another mode: the plain rule
        self.assertEqual(cs.replaced("impact", [self.scene.nodes["|cam"]["uuid"]]), [(layer, cs.record(layer))])

    def test_a_failure_inside_the_chunk_takes_back_what_it_did(self):
        def broken(*args, **kwargs):
            raise RuntimeError("keying failed")
        self.patch(cs, "_key", broken)
        with self.assertRaisesRegex(RuntimeError, "keying failed"):
            cs.apply("impact", {"push": 0.0}, frames=(40, 60))
        self.assertEqual(self.scene.layers, {})

    def test_a_refusal_changes_nothing(self):
        self.scene.nodes["|cam"]["locks"] = set(cs.ROTATE)
        with self.assertRaises(cs.Refused):
            cs.apply("impact", {}, frames=(40, 60))
        self.assertEqual(self.scene.layers, {})

    def test_locked_channels_are_named_on_the_line(self):
        self.scene.nodes["|cam"]["locks"] = {"rotateZ"}
        layer, text = cs.apply("handheld", {"drift": 0.0}, frames=(1, 10))
        self.assertNotIn("|cam.rotateZ", self.scene.layers[layer]["plugs"])
        self.assertIn("locked, not shaken: rotateZ", text)

    def test_delete_takes_the_layer_and_unpicks_it(self):
        layer, _ = cs.apply("impact", {"push": 0.0}, frames=(40, 60))
        self.assertEqual(cs.delete(layer), "deleted %s" % layer)
        self.assertEqual(self.scene.layers, {})
        self.assertIsNone(cs.picked())
        with self.assertRaisesRegex(cs.Refused, "pick a shake"):
            cs.delete(layer)

    def test_shakes_lists_only_ours_and_the_editor_pick_needs_one(self):
        layer, _ = cs.apply("impact", {"push": 0.0}, frames=(40, 60))
        self.scene.animLayer("AnimLayer1")
        self.assertEqual(cs.shakes(), [layer])
        self.assertIsNone(cs.editor_pick())
        self.scene.layers[layer]["selected"] = True
        self.assertEqual(cs.editor_pick(), layer)

    def test_the_card_names_a_shake_by_its_cameras(self):
        self.scene.selection = ["|cam", "|cam2"]
        layer, _ = cs.apply("handheld", {"drift": 0.0}, frames=(1, 10))
        self.assertEqual(cs._node_names(cs.record(layer)), "cam, cam2")
        del self.scene.nodes["|cam2"]
        self.assertEqual(cs._node_names(cs.record(layer)), "cam, ?")


class Describe(unittest.TestCase):
    def test_axes_off_are_named(self):
        s = cs.settings("handheld", {"tilt_on": False, "roll_on": False})
        text = cs.describe("handheld", s, 1, 9, ["|cam"], "L", "the highlight")
        self.assertIn("(no tilt, roll)", text)
        self.assertIn("frames 1-9 (the highlight)", text)
        self.assertIn("Handheld: sway 1.00 deg, jitter 0.12 deg at 7 Hz, drift 1.5 cm", text)


#  ---------------------------------------------------------------------------------------- the card

from tests.test_camshake import FakeCmds as CardCmds  # noqa: E402

LAYER = "CamShake_Impact_40_60"


class Card(unittest.TestCase):
    """The card's last controls: the chip and seed lambdas, its tool buttons, undo, the hub."""

    def setUp(self):
        self.fake = CardCmds()
        names = ("cmds", "apply", "retune", "delete", "picked", "pick", "record", "shakes", "targets",
                 "apply_targets", "replaced", "_uuid", "frames_for", "editor_pick", "_node_names")
        saved = {name: getattr(cs, name) for name in names}
        self.addCleanup(lambda: [setattr(cs, name, value) for name, value in saved.items()])
        self.addCleanup(cs.JOB.clear)
        self.addCleanup(lambda: cs._state().pop("editor", None))
        self.addCleanup(lambda: cs._QUIET.__setitem__(0, False))
        import maya_hubstyle
        self.addCleanup(maya_hubstyle.take_marks)
        cs.cmds = self.fake
        self.calls = []
        self.current = None
        cs.picked = lambda: self.current
        cs.pick = lambda layer: setattr(self, "current", layer)
        cs.record = lambda layer: {"mode": "impact", "frames": [40, 60], "targets": ["U"],
                                   "settings": cs.settings("impact", {"strength": 7.0})} if layer else None
        cs.shakes = lambda: [LAYER]
        cs.targets = lambda selection=None: ["|cam"]
        cs.apply_targets = lambda mode, selection=None: ["|cam"]
        cs.replaced = lambda mode, uuids: []
        cs._uuid = lambda node: "U"
        cs.frames_for = lambda mode, s, given=None: (0, 50, "the playback range")
        cs.editor_pick = lambda: None
        cs.apply = lambda mode, given=None, selection=None, frames=None: (
            self.calls.append(("apply", mode, given)) or (LAYER, "applied"))
        cs.retune = lambda layer, given: self.calls.append(("retune", layer, given)) or "re-tuned"
        cs.delete = lambda layer: self.calls.append(("delete", layer)) or "deleted"
        cs._node_names = lambda found: "cam"
        cs.build_panel()

    def control(self, name):
        return self.fake.controls[name]

    def test_an_axis_chip_sets_up_the_next_apply(self):
        chip = self.control(cs._axis_chip("pan_on"))
        chip["value"] = False
        chip["changeCommand"]()
        self.assertEqual(self.control(cs.STATUS)["label"], "Set for the next Apply.")
        self.assertFalse(cs.remembered("handheld")["pan_on"])

    def test_a_chip_re_keys_the_picked_shake_of_its_mode(self):
        self.current = LAYER
        cs._load(LAYER)
        self.control(cs._axis_chip("roll_on"))["value"] = False
        self.control(cs._axis_chip("roll_on"))["changeCommand"]()
        verb, layer, given = self.calls[-1]
        self.assertEqual((verb, layer, given["roll_on"]), ("retune", LAYER, False))

    def test_a_chip_filled_from_code_runs_nothing(self):
        cs._QUIET[0] = True
        cs._chip_changed()
        self.assertEqual(self.calls, [])

    def test_a_typed_seed_is_read_by_the_next_press(self):
        self.control(cs.SEED_FIELD)["value"] = 77
        self.control(cs.SEED_FIELD)["changeCommand"]()
        self.assertEqual(cs.remembered("handheld")["seed"], 77)

    def test_the_tool_buttons_press_what_they_say(self):
        self.current = LAYER
        cs._load(LAYER)
        self.control(cs.DELETE_BTN)["command"]()
        self.assertEqual(self.calls[-1], ("delete", LAYER))
        self.control(cs.SEED_BTN)["command"]()
        self.assertEqual(self.calls[-1][0], "retune")
        self.control(cs.APPLY_BTN)["command"]()
        self.assertEqual(self.calls[-1][:2], ("apply", "impact"))

    def test_an_undo_shows_the_picked_shakes_settings_again(self):
        self.current = LAYER
        cs.after_undo()
        self.assertEqual(cs.current_mode(), "impact")
        self.assertEqual(self.control(cs._slider("impact", "strength"))["value"], 7.0)
        self.assertIn("Editing %s" % LAYER, self.control(cs.SUBTITLE)["label"])

    def test_an_undo_with_nothing_picked_only_refreshes(self):
        cs.after_undo()
        self.assertIn("New handheld shake on cam", self.control(cs.SUBTITLE)["label"])

    def test_the_subtitle_says_a_refusal(self):
        def refuse(mode, selection=None):
            raise cs.Refused("2 cameras of ours (a, b) - select the one to shake")
        cs.apply_targets = refuse
        cs.refresh()
        self.assertTrue(self.control(cs.SUBTITLE)["label"].startswith("2 cameras of ours"))

        def none(mode, selection=None):
            raise cs.Refused("select a camera to shake")
        cs.apply_targets = none
        cs.refresh()
        self.assertEqual(self.control(cs.SUBTITLE)["label"], cs.NOTHING)

    def test_a_press_that_breaks_is_said_and_the_card_stays(self):
        def broken(*args, **kwargs):
            raise ValueError("scene gone")
        cs.apply = broken
        with mock.patch("builtins.print"):
            self.assertEqual(cs.press_apply(), "Camera Shake failed: scene gone")

    def test_a_second_build_kills_the_cards_old_jobs(self):
        old = list(cs.JOB[""])
        cs.build_panel()
        self.assertEqual(sorted(self.fake.killed), sorted(old))

    def test_show_window_opens_the_hub_on_the_card(self):
        import maya_hub
        with mock.patch.object(maya_hub, "show", lambda key=None: "hub " + key):
            self.assertEqual(cs.show_window(), "hub camshake")


if __name__ == "__main__":
    unittest.main()
