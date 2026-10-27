"""The AT bar's tools (`maya_atbar.core`) on a fake scene: keys moved and inserted, the blend sliders'
arithmetic, the pose / animation / world-space clipboards, mirror, space switch, temp controls and pivot,
trails, bookmarks, select sets and anim recovery.

Every test rebinds `core.cmds` / `core.mel` to a fake for its own length; nothing of Maya runs.
"""

import datetime
import json
import math
import os
import shutil
import sys
import tempfile
import types
import unittest
from unittest import mock

import maya.api.OpenMaya as om

import maya_timebar
from maya_atbar import core

ANIM = core.ANIM_CURVE_TYPES


def translate(x, y, z):
    return [1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, float(x), float(y), float(z), 1.0]


def rot_z(deg, at=(0, 0, 0)):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return [c, s, 0, 0, -s, c, 0, 0, 0, 0, 1.0, 0, float(at[0]), float(at[1]), float(at[2]), 1.0]


def close(a, b, places=6):
    return all(abs(x - y) < 10 ** -places for x, y in zip(a, b))


class FakeMel(object):
    def __init__(self):
        self.names = {"$t=$gPlayBackSlider": "timeSlider", "$t=$gChannelBoxName": "mainChannelBox"}

    def eval(self, code):
        return self.names[code]


class FakeCmds(object):
    """A recording maya.cmds over a little scene: attribute values, transforms, keyed curves.
    A command the class does not know answers None and is recorded as a MagicMock."""

    def __init__(self):
        self.__dict__["_mocks"] = {}
        self.selected = []
        self.time = 0.0
        self.autokey = False
        self.values = {}            # plug, or (plug, time) -> value
        self.locked = set()
        self.unkeyable = set()
        self.types = {}             # plug -> attribute type
        self.long_names = {}
        self.defaults = {}
        self.enums = {}
        self.keyable = {}           # node -> [attr]
        self.transforms = []        # long names
        self.node_types = {}
        self.existing = set()
        self.curves = {}
        self.relatives = {}
        self.connections = {}
        self.panels = []
        self.box = {}
        self.range = None
        self.playback = (1.0, 120.0)
        self.messages, self.warnings, self.chunks = [], [], []
        self.visited, self.refreshes, self.keyed = [], [], []
        self.tangent_edits, self.xforms, self.selections = [], [], []
        self.deleted, self.disconnected, self.connected = [], [], []
        self.fail_disconnect, self.fail_edit = set(), set()

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        mocks = self.__dict__["_mocks"]
        if name not in mocks:
            mocks[name] = mock.MagicMock(name=name, return_value=None)
        return mocks[name]

    # -- the scene, as the tests build it
    def add_curve(self, plug, keys, kind="animCurveTL", name=None, tangents=None):
        name = name or plug.replace(".", "_").replace(":", "_").replace("|", "")
        n = len(keys)
        data = {"itt": ["auto"] * n, "ott": ["auto"] * n, "ia": [0.0] * n, "oa": [0.0] * n, "iw": [1.0] * n,
                "ow": [1.0] * n, "lock": [True] * n, "weightedTangents": [False]}
        data.update(tangents or {})
        self.curves[name] = {"plug": plug, "type": kind, "keys": [[float(t), float(v)] for t, v in keys],
                             "sel": set(), "tangents": data}
        return name

    def keys_of(self, plug):
        return [tuple(k) for c in self._curves_of(plug) for k in self.curves[c]["keys"]]

    def _curves_of(self, item):
        if item in self.curves:
            return [item]
        if "." in item:
            return [c for c, d in self.curves.items() if d["plug"] == item]
        return [c for c, d in self.curves.items() if d["plug"].split(".")[0] == item]

    # -- undo, messages
    def undoInfo(self, **kw):
        if kw.get("openChunk"):
            self.chunks.append("open")
        if kw.get("closeChunk"):
            self.chunks.append("close")

    def inViewMessage(self, **kw):
        self.messages.append(kw["amg"])

    def warning(self, text):
        self.warnings.append(text)

    # -- time
    def currentTime(self, *args, **kw):
        if kw.get("q") or kw.get("query"):
            return self.time
        self.time = float(args[0])
        self.visited.append(self.time)

    def refresh(self, **kw):
        self.refreshes.append(kw.get("suspend"))

    def autoKeyframe(self, **kw):
        return self.autokey

    def playbackOptions(self, **kw):
        return self.playback[0] if kw.get("min") else self.playback[1]

    def timeControl(self, slider, **kw):
        if kw.get("rangeVisible"):
            return self.range is not None
        if kw.get("rangeArray"):
            return list(self.range)

    def getPanel(self, **kw):
        return list(self.panels)

    def channelBox(self, cb, **kw):
        for flag in ("sma", "ssa", "sha", "soa"):
            if kw.get(flag):
                return list(self.box.get(flag, [])) or None

    # -- selection and nodes
    def ls(self, *args, **kw):
        if kw.get("sl") or kw.get("selection"):
            return list(self.selected)
        kind = kw.get("type")
        if isinstance(kind, list) and set(kind) <= set(ANIM):
            names = args[0] if args else list(self.curves)
            names = [names] if isinstance(names, str) else names
            return [n for n in names if n in self.curves and self.curves[n]["type"] in kind]
        if kind == "transform" and args and isinstance(args[0], str):
            return [p for p in self.transforms if p.split("|")[-1] == args[0]]
        return self.ls_more(*args, **kw)

    def ls_more(self, *args, **kw):
        return []

    def objExists(self, name):
        return (name in self.existing or name in self.values or name in self.curves
                or any(d["plug"] == name for d in self.curves.values()))

    def nodeType(self, node):
        if node in self.curves:
            return self.curves[node]["type"]
        return self.node_types.get(node, "transform")

    def listRelatives(self, node, **kw):
        if isinstance(node, list):
            found = []
            for n in node:
                found += self.listRelatives(n, **kw) or []
            return found or None
        for flag in ("shapes", "children", "parent"):
            if kw.get(flag):
                return self.relatives.get((node, flag))
        if kw.get("type"):
            return self.relatives.get((node, kw["type"]))
        return None

    def select(self, *args, **kw):
        self.selections.append((args, kw))

    def delete(self, *args, **kw):
        self.deleted.append((args, kw))

    def createNode(self, kind, name=None, **kw):
        self.existing.add(name)
        return name

    # -- attributes
    def getAttr(self, plug, **kw):
        if kw.get("settable"):
            return plug not in self.locked
        if kw.get("keyable"):
            return plug not in self.unkeyable
        if kw.get("type"):
            return self.types.get(plug, "double")
        if "time" in kw and (plug, kw["time"]) in self.values:
            value = self.values[(plug, kw["time"])]
        elif plug in self.values:
            value = self.values[plug]
        else:
            raise ValueError("No object matches name: " + plug)
        return list(value) if isinstance(value, list) else value

    def setAttr(self, plug, *args, **kw):
        if plug in self.locked:
            raise RuntimeError("locked: " + plug)
        self.values[plug] = args[0] if len(args) == 1 else list(args)

    def listAttr(self, node, **kw):
        return list(self.keyable.get(node, []))

    def attributeQuery(self, attr, node=None, **kw):
        plug = "%s.%s" % (node, attr)
        if kw.get("exists"):
            return self.objExists(plug) or attr in self.keyable.get(node, [])
        if kw.get("longName"):
            return self.long_names.get(attr, attr)
        if kw.get("listDefault"):
            if plug not in self.defaults:
                raise RuntimeError("no default")
            return [self.defaults[plug]]
        if kw.get("attributeType"):
            return self.types.get(plug, "double")
        if kw.get("listEnum"):
            return [self.enums[plug]]
        return None

    def listConnections(self, plug, **kw):
        if plug.endswith(".output") and plug[:-7] in self.curves:
            return [self.curves[plug[:-7]]["plug"]]
        if kw.get("s") and kw.get("d") is False:
            return [c for c, d in self.curves.items() if d["plug"] == plug] or None
        return self.connections.get(plug)

    def disconnectAttr(self, src, dst):
        if (src, dst) in self.fail_disconnect:
            raise RuntimeError("cannot disconnect")
        self.disconnected.append((src, dst))

    def connectAttr(self, src, dst, force=False):
        self.connected.append((src, dst))

    def xform(self, node, **kw):
        if kw.get("q") or kw.get("query"):
            return self.values.get(node + ".rotatePivot", [0.0, 0.0, 0.0])
        self.xforms.append((node, self.time, dict(kw)))
        if "matrix" in kw:
            self.values[node + ".worldMatrix[0]"] = list(kw["matrix"])
            self.values[(node + ".worldMatrix[0]", self.time)] = list(kw["matrix"])

    # -- keys
    def keyframe(self, *items, **kw):
        if kw.get("e") or kw.get("edit"):
            return self._edit_keys(items[0], kw)
        if not items:                                        # the Graph Editor's selected curves
            return [c for c, d in self.curves.items() if d["sel"]] or None
        curves = self._curves_of(items[0])
        if kw.get("name"):
            return curves or None
        picked = [(c, i, k) for c in curves for i, k in enumerate(self.curves[c]["keys"]) if self._picked(c, i, k, kw)]
        if kw.get("keyframeCount"):
            return len(picked)
        if kw.get("indexValue"):
            return [i for _c, i, _k in picked] or None
        if kw.get("tc") or kw.get("timeChange"):
            return [k[0] for _c, _i, k in picked] or None
        if kw.get("vc") or kw.get("valueChange"):
            return [k[1] for _c, _i, k in picked] or None
        return None

    def _picked(self, curve, i, key, kw):
        span = kw.get("t") or kw.get("time")
        if span is not None:
            return span[0] - 1e-9 <= key[0] <= span[1] + 1e-9
        if kw.get("sl"):
            return i in self.curves[curve]["sel"]
        return True

    def _edit_keys(self, target, kw):
        curve = target if target in self.curves else self._curves_of(target)[0]
        if curve in self.fail_edit:
            raise RuntimeError("cannot edit " + curve)
        keys = self.curves[curve]["keys"]
        if "index" in kw:
            keys[kw["index"][0]][1] = float(kw["valueChange"])
            return
        span = kw.get("t") or kw.get("time")
        for k in keys:
            if span is None or span[0] - 1e-9 <= k[0] <= span[1] + 1e-9:
                k[0] += kw["timeChange"]
        keys.sort()

    def cutKey(self, target, time=None, clear=True, **kw):
        for c in self._curves_of(target):
            keys = self.curves[c]["keys"]
            keys[:] = [k for k in keys if time is not None and not time[0] - 1e-9 <= k[0] <= time[1] + 1e-9]

    def setKeyframe(self, *targets, **kw):
        target = targets[0] if targets else None
        self.keyed.append((target, self.time, dict(kw)))
        if isinstance(target, str) and "t" in kw and "attribute" not in kw and ("v" in kw or kw.get("insert")):
            curves = self._curves_of(target)
            if not curves and "." in target:
                curves = [self.add_curve(target, [])]
            for c in curves:
                keys = self.curves[c]["keys"]
                t = float(kw["t"])
                v = float(kw["v"]) if "v" in kw else self._evaluate(keys, t)
                keys[:] = sorted([k for k in keys if abs(k[0] - t) > 1e-9] + [[t, v]])

    @staticmethod
    def _evaluate(keys, t):
        for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
            if t0 <= t <= t1:
                return v0 + (v1 - v0) * (t - t0) / (t1 - t0)
        return keys[0][1] if t < keys[0][0] else keys[-1][1]

    def keyTangent(self, curve, **kw):
        if kw.get("q") or kw.get("query"):
            data = self.curves[curve]["tangents"]
            for flag in ("itt", "ott", "ia", "oa", "iw", "ow", "lock", "weightedTangents"):
                if kw.get(flag):
                    return list(data[flag])
            return None
        self.tangent_edits.append((curve, {k: v for k, v in kw.items() if k not in ("e", "edit")}))


class CoreTest(unittest.TestCase):
    """core.cmds and core.mel rebound to fakes, core's own state kept as it was."""

    def setUp(self):
        self.fake = FakeCmds()
        self.mel = FakeMel()
        for patch in (mock.patch.object(core, "cmds", self.fake), mock.patch.object(core, "mel", self.mel),
                      mock.patch.dict(core._state), mock.patch.dict(core._clip)):
            patch.start()
            self.addCleanup(patch.stop)


# ---------------------------------------------------------------- helpers

class Helpers(CoreTest):

    def test_an_undoable_tool_closes_its_chunk_even_when_it_fails(self):
        @core.undoable
        def broken():
            raise RuntimeError("boom")
        with self.assertRaises(RuntimeError):
            broken()
        self.assertEqual(self.fake.chunks, ["open", "close"])
        self.assertEqual(broken.__name__, "broken")

    def test_messages_and_warnings_are_signed_by_the_bar(self):
        core.message("hello")
        core.warn("careful")
        self.assertTrue(self.fake.messages[0].endswith("hello"))
        self.assertIn("<hl>AT</hl>", self.fake.messages[0])
        self.assertEqual(self.fake.warnings, ["AT: careful"])

    def test_a_name_without_its_path_and_namespaces(self):
        self.assertEqual(core.strip_ns("|grp|tab_x:Manny_Rig:FKWrist_L"), "FKWrist_L")
        self.assertEqual(core.strip_ns("plain"), "plain")

    def test_nothing_selected_is_an_empty_list(self):
        self.assertEqual(core.selection(), [])
        self.fake.selected = ["|a", "|b"]
        self.assertEqual(core.selection(), ["|a", "|b"])

    def test_the_time_range_is_the_highlight_else_the_playback_range(self):
        self.assertEqual(core.time_range(), (1.0, 120.0))
        self.fake.range = (10.0, 21.0)
        self.assertEqual(core.time_range(), (10.0, 20.0))

    def test_the_time_range_is_the_time_bar_s_highlight_while_it_stands(self):
        """2026-10-27: Bake selection and the trails read only Maya's hidden slider; with our
        Time Bar standing they ignored its highlight and took the whole playback range."""
        self.fake.range = None
        with mock.patch.object(maya_timebar, "highlight", return_value=(30.0, 41.0)):
            self.assertEqual(core.time_range(), (30.0, 40.0))
            tsb = mock.MagicMock()
            with mock.patch.object(core, "_bookmarks", return_value=tsb):
                core.add_bookmark()
            tsb.createBookmark.assert_called_once_with(start=30.0, stop=40.0)

    def test_the_highlighted_range_comes_from_the_time_bar_first(self):
        self.fake.range = (50.0, 61.0)
        with mock.patch.object(maya_timebar, "highlight", return_value=(10.0, 21.0)):
            self.assertEqual(core.highlighted_range(), (10.0, 20.0))
        with mock.patch.object(maya_timebar, "highlight", side_effect=RuntimeError("no bar")):
            self.assertEqual(core.highlighted_range(), (50.0, 60.0))
        self.fake.range = None
        with mock.patch.object(maya_timebar, "highlight", return_value=None):
            self.assertIsNone(core.highlighted_range())

    def test_a_slider_that_cannot_be_asked_reads_as_no_highlight(self):
        self.fake.timeControl = mock.MagicMock(side_effect=RuntimeError("no slider"))
        with mock.patch.object(maya_timebar, "highlight", return_value=None):
            self.assertIsNone(core.highlighted_range())

    def test_the_channel_box_s_four_selections_together(self):
        self.fake.box = {"sma": ["tx"], "sha": ["visibility"], "soa": ["outX"]}
        self.assertEqual(core.channelbox_attrs(), ["tx", "visibility", "outX"])

    def test_the_graph_editor_counts_while_it_shows(self):
        self.assertFalse(core.graph_editor_visible())
        self.fake.panels = ["modelPanel4", "graphEditor1"]
        self.assertTrue(core.graph_editor_visible())

    def test_curves_are_listed_once_and_driven_key_curves_left_out(self):
        tx = self.fake.add_curve("ctrl.tx", [(0, 0)])
        rx = self.fake.add_curve("ctrl.rx", [(0, 0)], kind="animCurveTA")
        self.fake.add_curve("ctrl.blend", [(0, 0)], kind="animCurveUU")
        self.assertEqual(core.anim_curves(["ctrl", "ctrl.tx"]), [tx, rx])

    def test_a_node_s_curves_on_the_asked_attributes_only(self):
        tx = self.fake.add_curve("ctrl.tx", [(0, 0)])
        self.fake.add_curve("ctrl.ty", [(0, 0)])
        self.assertEqual(core.node_curves("ctrl", ["tx", "notThere"]), [tx])
        self.assertEqual(len(core.node_curves("ctrl")), 2)

    def test_the_selection_s_curves_on_the_channel_box_s_attributes(self):
        self.fake.selected = ["a", "b"]
        ax = self.fake.add_curve("a.tx", [(0, 0)])
        self.fake.add_curve("a.ty", [(0, 0)])
        bx = self.fake.add_curve("b.tx", [(0, 0)])
        self.fake.box = {"sma": ["tx"]}
        self.assertEqual(core.selected_curves(), [ax, bx])

    def test_a_curve_s_driven_plug(self):
        c = self.fake.add_curve("ctrl.tx", [(0, 0)])
        self.assertEqual(core.driven_plug(c), "ctrl.tx")
        self.fake.listConnections = mock.MagicMock(return_value=None)
        self.assertIsNone(core.driven_plug(c))

    def test_curves_are_detached_while_keys_move_and_joined_again_after_an_error(self):
        a = self.fake.add_curve("ctrl.tx", [(0, 0)])
        b = self.fake.add_curve("ctrl.ty", [(0, 0)])
        self.fake.fail_disconnect.add((b + ".output", "ctrl.ty"))
        with self.assertRaises(ValueError):
            with core.detached([a, b]):
                self.assertEqual(self.fake.disconnected, [(a + ".output", "ctrl.tx")])
                raise ValueError("inside")
        #  only the link that came off goes back on
        self.assertEqual(self.fake.connected, [(a + ".output", "ctrl.tx")])

    def test_animated_means_it_has_keys(self):
        self.assertFalse(core.is_animated("ctrl"))
        self.fake.add_curve("ctrl.tx", [(0, 0)])
        self.assertTrue(core.is_animated("ctrl"))

    def test_keyable_attributes_that_can_be_set(self):
        self.fake.keyable["ctrl"] = ["tx", "ty", "gone"]
        self.fake.values.update({"ctrl.tx": 0.0, "ctrl.ty": 0.0})
        self.fake.locked.add("ctrl.ty")
        real = self.fake.getAttr

        def get(plug, **kw):
            if plug == "ctrl.gone":
                raise RuntimeError("gone")
            return real(plug, **kw)
        self.fake.getAttr = get
        self.assertEqual(core.keyable_attrs("ctrl"), ["tx"])

    def test_free_transform_channels_are_keyable_and_settable(self):
        self.fake.unkeyable.add("ctrl.ry")
        self.fake.locked.add("ctrl.tz")
        self.assertEqual(core.free_transform_attrs("ctrl"), ["tx", "ty", "rx", "rz"])

    def test_a_transform_is_keyed_only_when_animated_auto_keyed_or_forced(self):
        core.key_transform("ctrl")
        self.assertEqual(self.fake.keyed, [])
        core.key_transform("ctrl", force=True, channels="r")
        self.assertEqual(self.fake.keyed[-1][2], {"attribute": ["rx", "ry", "rz"]})
        self.fake.autokey = True
        core.key_transform("ctrl", t=12)
        self.assertEqual(self.fake.keyed[-1][2], {"attribute": list(core.TRANSFORM_ATTRS), "t": 12})

    def test_key_times_of_several_nodes_together(self):
        self.fake.add_curve("a.tx", [(0, 0), (10, 1)])
        self.fake.add_curve("b.tx", [(5, 0), (10, 1)])
        self.assertEqual(core.key_times(["a", "b", "nothing"]), [0.0, 5.0, 10.0])

    def test_world_matrix_now_or_at_a_time(self):
        self.fake.values["n.worldMatrix[0]"] = translate(1, 2, 3)
        self.fake.values[("n.worldMatrix[0]", 7)] = translate(4, 5, 6)
        self.assertEqual(core.world_matrix("n")[12:15], [1, 2, 3])
        self.assertEqual(core.world_matrix("n", 7)[12:15], [4, 5, 6])

    def test_a_world_matrix_on_translate_keeps_the_rotation_and_scale_channels(self):
        others = ("rx", "ry", "rz", "sx", "sy", "sz")
        for a in others + ("tx", "ty", "tz"):
            self.fake.values["n." + a] = 5.0
        self.fake.locked.add("n.sx")
        real = self.fake.xform

        def xform(node, **kw):                               # Maya's xform rewrites every channel
            real(node, **kw)
            for a in others:
                self.fake.values["n." + a] = 0.0
        self.fake.xform = xform
        core.set_world_matrix("n", translate(1, 2, 3), channels="t")
        self.assertEqual(self.fake.xforms[-1][2], {"ws": True, "matrix": translate(1, 2, 3)})
        self.assertEqual([self.fake.values["n." + a] for a in others], [5.0, 5.0, 5.0, 0.0, 5.0, 5.0])
        core.set_world_matrix("n", translate(0, 0, 0))
        self.assertEqual([self.fake.values["n." + a] for a in others], [0.0] * 6)

    def test_a_walk_over_times_puts_the_time_and_the_viewport_back_even_when_it_fails(self):
        self.fake.time = 3.0
        core._state["suspended"] = True
        seen = []

        def step(t):
            seen.append((t, self.fake.time))
            if t == 20:
                raise RuntimeError("boom")
        with self.assertRaises(RuntimeError):
            core.run_at_times([10, 20, 30], step)
        self.assertEqual(seen, [(10, 10.0), (20, 20.0)])
        self.assertEqual(self.fake.time, 3.0)
        self.assertEqual(self.fake.refreshes, [True, True])

    def test_matrices_multiply_and_invert_in_maya_s_row_vector_order(self):
        follower, anchor = translate(12, 1, 0), translate(10, 0, 0)
        rel = core.mmul(follower, core.minv(anchor))
        self.assertTrue(close(rel, translate(2, 1, 0)))
        self.assertTrue(close(core.mmul(rel, anchor), follower))


# ---------------------------------------------------------------- default pose

class DefaultPose(CoreTest):

    def setUp(self):
        super(DefaultPose, self).setUp()
        self.fake.long_names = {"tx": "translateX", "ry": "rotateY"}

    def test_the_data_node_is_made_once_with_an_empty_snapshot(self):
        self.assertEqual(core._data_node(), core.DATA_NODE)
        self.fake.addAttr.assert_called_once_with(core.DATA_NODE, longName="defaultPose", dataType="string")
        self.assertEqual(self.fake.values[core.DATA_NODE + ".defaultPose"], "{}")
        core._data_node()
        self.fake.addAttr.assert_called_once()

    def test_no_data_node_or_a_broken_one_reads_as_no_snapshot(self):
        self.assertEqual(core._load_snapshot(), {})
        self.fake.values[core.DATA_NODE + ".defaultPose"] = "{broken"
        self.assertEqual(core._load_snapshot(), {})

    def test_a_snapshot_is_kept_by_the_control_s_name_without_namespace(self):
        self.fake.selected = ["rig:ctrl"]
        self.fake.keyable["rig:ctrl"] = ["tx", "ry"]
        self.fake.values.update({"rig:ctrl.tx": 1.5, "rig:ctrl.ry": 30.0})
        core.snapshot_default_pose()
        saved = json.loads(self.fake.values[core.DATA_NODE + ".defaultPose"])
        self.assertEqual(saved, {"ctrl": {"translateX": 1.5, "rotateY": 30.0}})
        self.assertEqual(core.default_value("rig1:ctrl.tx"), 1.5)
        self.assertIn("1 controls", self.fake.messages[-1])

    def test_a_snapshot_of_nothing_asks_for_a_selection(self):
        core.snapshot_default_pose()
        self.assertIn("select controls", self.fake.warnings[0])
        self.assertNotIn(core.DATA_NODE + ".defaultPose", self.fake.values)

    def test_without_a_snapshot_the_attribute_s_default_in_ui_units(self):
        self.fake.defaults = {"c.tx": 2.0, "c.ry": math.radians(90)}
        self.fake.types = {"c.ry": "doubleAngle"}
        self.assertEqual(core.default_value("c.tx"), 2.0)
        self.assertAlmostEqual(core.default_value("c.ry"), 90.0, places=6)
        self.assertIsNone(core.default_value("c.nothing"))

    def test_a_long_name_that_cannot_be_asked_falls_back_to_the_default(self):
        self.fake.defaults = {"c.tx": 4.0}
        real = self.fake.attributeQuery

        def query(attr, node=None, **kw):
            if kw.get("longName"):
                raise RuntimeError("no attribute")
            return real(attr, node=node, **kw)
        self.fake.attributeQuery = query
        self.assertEqual(core.default_value("c.tx"), 4.0)

    def test_reset_puts_each_channel_on_its_default_and_keys_an_animated_control(self):
        self.fake.selected = ["c"]
        self.fake.keyable["c"] = ["tx", "ry"]
        self.fake.values.update({"c.tx": 9.0, "c.ry": 9.0})
        self.fake.defaults = {"c.tx": 0.0}
        core.reset_to_default_pose()
        self.assertEqual(self.fake.values["c.tx"], 0.0)
        self.assertEqual(self.fake.values["c.ry"], 9.0)
        self.assertEqual(self.fake.keyed, [])
        self.fake.add_curve("c.tx", [(0, 1)])
        core.reset_to_default_pose()
        self.assertEqual(self.fake.keyed[-1][0], "c")

    def test_clear_empties_the_snapshot(self):
        self.fake.existing.add(core.DATA_NODE)
        self.fake.values[core.DATA_NODE + ".defaultPose"] = '{"ctrl": {"translateX": 1}}'
        core.clear_default_pose()
        self.assertEqual(core._load_snapshot(), {})
        self.assertIn("cleared", self.fake.messages[-1])


# ---------------------------------------------------------------- nudge / inbetweens

class NudgeAndInbetween(CoreTest):

    def setUp(self):
        super(NudgeAndInbetween, self).setUp()
        self.fake.selected = ["ctrl"]
        self.tx = self.fake.add_curve("ctrl.tx", [(0, 0), (10, 1), (12, 2), (20, 3)])
        self.ty = self.fake.add_curve("ctrl.ty", [(0, 0), (20, 3)])
        self.other = self.fake.add_curve("other.tx", [(15, 0), (30, 1)])
        self.fake.time = 10.0

    def times(self, curve):
        return [k[0] for k in self.fake.curves[curve]["keys"]]

    def test_a_nudge_moves_every_key_of_the_selection(self):
        core.nudge(3)
        self.assertEqual(self.times(self.tx), [3, 13, 15, 23])
        self.assertEqual(self.times(self.ty), [3, 23])
        self.assertEqual(self.times(self.other), [15, 30])
        self.assertEqual(len(self.fake.connected), 2)
        self.assertIn("2 curves moved +3 frames", self.fake.messages[-1])

    def test_a_nudge_follows_the_channel_box(self):
        self.fake.box = {"sma": ["tx"]}
        core.nudge(-2)
        self.assertEqual(self.times(self.tx), [-2, 8, 10, 18])
        self.assertEqual(self.times(self.ty), [0, 20])

    def test_a_curve_that_refuses_is_not_counted(self):
        self.fake.fail_edit.add(self.ty)
        core.nudge(1)
        self.assertIn("1 curves moved +1 frames", self.fake.messages[-1])

    def test_nothing_animated_selected_or_no_frames(self):
        core.nudge(0)
        self.assertEqual(self.fake.chunks, ["open", "close"])
        self.assertEqual(self.times(self.tx), [0, 10, 12, 20])
        self.fake.selected = []
        core.nudge(2)
        self.assertIn("select animated controls", self.fake.warnings[-1])

    def test_an_inbetween_pushes_the_keys_after_the_current_frame(self):
        core.inbetween(2)
        self.assertEqual(self.times(self.tx), [0, 10, 14, 22])
        self.assertEqual(self.times(self.ty), [0, 22])
        self.assertEqual(self.times(self.other), [15, 30])
        self.assertIn("inserted 2 frame(s) after frame 10", self.fake.messages[-1])

    def test_removing_frames_deletes_their_keys_then_pulls_the_rest_back(self):
        core.inbetween(-2)
        self.assertEqual(self.times(self.tx), [0, 10, 18])
        self.assertEqual(self.times(self.ty), [0, 18])
        self.assertIn("removed 2 frame(s)", self.fake.messages[-1])

    def test_the_scene_wide_inbetween_moves_every_curve(self):
        self.fake.selected = []
        core.inbetween(5, scene=True)
        self.assertEqual(self.times(self.other), [20, 35])
        self.assertEqual(self.times(self.tx), [0, 10, 17, 25])
        self.assertIn("in the scene", self.fake.messages[-1])

    def test_nothing_after_the_current_frame_is_said(self):
        self.fake.time = 40.0
        core.inbetween(2)
        self.assertIn("no keys after frame 40", self.fake.warnings[-1])
        self.fake.selected = []
        core.inbetween(2)
        self.assertIn("select animated controls", self.fake.warnings[-1])
        self.fake.curves.clear()
        core.inbetween(2, scene=True)
        self.assertIn("nothing animated", self.fake.warnings[-1])


# ---------------------------------------------------------------- blend sliders

class Sliders(CoreTest):

    def setUp(self):
        super(Sliders, self).setUp()
        self.fake.selected = ["ctrl"]
        self.fake.time = 10.0

    def values(self, curve):
        return [k[1] for k in self.fake.curves[curve]["keys"]]

    def test_the_tweener_slides_between_the_neighbours(self):
        c = self.fake.add_curve("ctrl.tx", [(0, 0), (10, 5), (20, 20)])
        session = core.SliderSession("TW")
        for pct, want in ((0, 10.0), (-100, 0.0), (100, 20.0), (50, 15.0)):
            session.apply(pct)
            self.assertAlmostEqual(self.values(c)[1], want)
        session.finish()
        self.assertEqual(self.fake.chunks, ["open", "close"])

    def test_a_key_with_no_neighbours_is_left_alone_by_the_tweener(self):
        c = self.fake.add_curve("ctrl.tx", [(10, 5)])
        core.SliderSession("TW").apply(100)
        self.assertEqual(self.values(c), [5.0])

    def test_blend_to_neighbours_goes_toward_the_next_or_the_previous(self):
        c = self.fake.add_curve("ctrl.tx", [(0, 0), (10, 5), (20, 20)])
        session = core.SliderSession("BN")
        session.apply(50)
        self.assertAlmostEqual(self.values(c)[1], 12.5)
        session.apply(-50)
        self.assertAlmostEqual(self.values(c)[1], 2.5)

    def test_a_missing_key_on_the_current_frame_is_inserted_first(self):
        c = self.fake.add_curve("ctrl.tx", [(0, 0), (20, 20)])
        session = core.SliderSession("TW")
        self.assertEqual([k[0] for k in self.fake.curves[c]["keys"]], [0, 10, 20])
        session.apply(-100)
        self.assertEqual(self.values(c), [0, 0, 20])

    def test_blend_to_default_reaches_the_default_and_takes_unkeyed_channels_along(self):
        c = self.fake.add_curve("ctrl.tx", [(0, 0), (10, 8), (20, 0)])
        self.fake.keyable["ctrl"] = ["tx", "ty", "tz"]
        self.fake.values.update({"ctrl.tx": 8.0, "ctrl.ty": 4.0, "ctrl.tz": "text"})
        defaults = {"ctrl.tx": 2.0, "ctrl.ty": 0.0, "ctrl.tz": 1.0}
        with mock.patch.object(core, "default_value", side_effect=lambda plug: defaults.get(plug)):
            session = core.SliderSession("BD")
            session.apply(100)
            self.assertAlmostEqual(self.values(c)[1], 2.0)
            self.assertAlmostEqual(self.fake.values["ctrl.ty"], 0.0)
            self.assertEqual(self.fake.values["ctrl.tz"], "text")
            session.apply(50)
            self.assertAlmostEqual(self.values(c)[1], 5.0)
            self.assertAlmostEqual(self.fake.values["ctrl.ty"], 2.0)

    def test_a_curve_with_no_default_is_not_blended_to_default(self):
        c = self.fake.add_curve("ctrl.tx", [(10, 8)])
        with mock.patch.object(core, "default_value", return_value=None):
            session = core.SliderSession("BD")
        self.assertEqual(session.keys, [])
        session.apply(100)
        self.assertEqual(self.values(c), [8.0])

    def test_a_block_of_selected_keys_blends_against_the_keys_around_it(self):
        self.fake.panels = ["graphEditor1"]
        c = self.fake.add_curve("ctrl.tx", [(0, 0), (1, 10), (2, 20), (3, 30), (4, 40)])
        self.fake.curves[c]["sel"] = {1, 2}
        session = core.SliderSession("TW")
        session.apply(100)
        self.assertEqual(self.values(c), [0, 30, 30, 30, 40])
        session.apply(-100)
        self.assertEqual(self.values(c), [0, 0, 0, 30, 40])

    def test_smoothing_eases_the_key_and_its_tangents_and_gives_them_back(self):
        tangents = {"itt": ["fixed"] * 5, "ott": ["linear"] * 5, "ia": [12.0] * 5, "oa": [0.0] * 5}
        c = self.fake.add_curve("ctrl.tx", [(8, 0), (9, 10), (10, 0), (11, 10), (12, 0)], tangents=tangents)
        levels = core.smoothing_levels([0.0, 10.0, 0.0, 10.0, 0.0])
        column = [level[2] for level in levels]
        session = core.SliderSession("SM")
        session.apply(-100)
        self.assertAlmostEqual(self.values(c)[2], core.smooth_at(column, -1.0))
        self.assertEqual(self.fake.tangent_edits[-1], (c, {"index": [(2, 2)], "itt": "auto", "ott": "auto"}))
        session.apply(0)
        self.assertAlmostEqual(self.values(c)[2], 0.0)
        edits = [e for _c, e in self.fake.tangent_edits]
        self.assertIn({"index": (2, 2), "itt": "fixed", "ott": "linear"}, edits)
        self.assertIn({"index": (2, 2), "ia": 12.0}, edits)
        self.assertFalse(any("lock" in e for e in edits))
        session.apply(50)
        self.assertAlmostEqual(self.values(c)[2], 0.0 - (column[core.SM_ROUGH_PASSES] - 0.0) * 0.5)

    def test_tangents_already_aligned_are_not_edited_again(self):
        c = self.fake.add_curve("ctrl.tx", [(9, 1), (10, 0), (11, 1)])
        session = core.SliderSession("SM")
        session.apply(-50)
        session.apply(-80)
        self.assertEqual(len([e for e in self.fake.tangent_edits if e[0] == c]), 1)

    def test_a_session_that_cannot_collect_closes_its_chunk(self):
        self.fake.getPanel = mock.MagicMock(side_effect=RuntimeError("no panels"))
        with self.assertRaises(RuntimeError):
            core.SliderSession("TW")
        self.assertEqual(self.fake.chunks, ["open", "close"])

    def test_an_unknown_mode_changes_nothing(self):
        c = self.fake.add_curve("ctrl.tx", [(0, 0), (10, 5), (20, 20)])
        core.SliderSession("XX").apply(100)
        self.assertEqual(self.values(c), [0, 5, 20])


# ---------------------------------------------------------------- clipboards

class PoseClipboard(CoreTest):

    def test_entries_pair_by_name_then_by_order_then_one_onto_all(self):
        clip = [("FKWrist_L", "wrist"), ("FKElbow_L", "elbow")]
        self.assertEqual(core._match_clip(clip, ["rig1:FKElbow_L", "rig1:FKWrist_L"]),
                         [("rig1:FKElbow_L", "elbow"), ("rig1:FKWrist_L", "wrist")])
        self.assertEqual(core._match_clip(clip, ["a", "b"]), [("a", "wrist"), ("b", "elbow")])
        self.assertEqual(core._match_clip([("x", "one")], ["a", "b", "c"]),
                         [("a", "one"), ("b", "one"), ("c", "one")])
        self.assertEqual(core._match_clip(clip, ["a", "b", "c"]), [])

    def test_a_pose_copied_from_one_rig_lands_on_the_other(self):
        self.fake.selected = ["rig:ctrl"]
        self.fake.keyable["rig:ctrl"] = ["tx", "ry"]
        self.fake.values.update({"rig:ctrl.tx": 1.0, "rig:ctrl.ry": 45.0})
        core.copy_pose()
        self.assertIn("1 controls", self.fake.messages[-1])
        self.fake.selected = ["rig1:ctrl"]
        self.fake.keyable["rig1:ctrl"] = ["tx", "ry"]
        self.fake.values.update({"rig1:ctrl.tx": 0.0, "rig1:ctrl.ry": 0.0})
        core.paste_pose()
        self.assertEqual((self.fake.values["rig1:ctrl.tx"], self.fake.values["rig1:ctrl.ry"]), (1.0, 45.0))
        self.assertEqual(self.fake.keyed, [])

    def test_a_pasted_pose_is_keyed_on_an_animated_control_and_a_locked_channel_skipped(self):
        core._clip["pose"] = [("ctrl", {"tx": 3.0, "ty": 4.0})]
        self.fake.selected = ["ctrl"]
        self.fake.keyable["ctrl"] = ["tx", "ty"]
        self.fake.values.update({"ctrl.tx": 0.0, "ctrl.ty": 0.0})
        self.fake.locked.add("ctrl.ty")
        self.fake.add_curve("ctrl.tx", [(0, 0)])
        core.paste_pose()
        self.assertEqual(self.fake.values["ctrl.tx"], 3.0)
        self.assertEqual(self.fake.values["ctrl.ty"], 0.0)
        self.assertEqual(self.fake.keyed[-1], ("ctrl", 0.0, {"attribute": ["tx", "ty"]}))

    def test_nothing_to_copy_or_paste_is_said(self):
        core.copy_pose()
        core.paste_pose()
        self.assertEqual(len(self.fake.warnings), 2)


class AnimationClipboard(CoreTest):

    def setUp(self):
        super(AnimationClipboard, self).setUp()
        tangents = {"itt": ["fixed", "auto"], "ott": ["linear", "linear"], "ia": [15.0, 0.0], "oa": [0.0, 0.0],
                    "iw": [2.0, 1.0], "ow": [3.0, 1.0], "lock": [False, True], "weightedTangents": [True]}
        self.src = self.fake.add_curve("src.translateX", [(0, 1), (10, 2)], tangents=tangents)
        self.fake.values.update({self.src + ".preInfinity": 3, self.src + ".postInfinity": 4})
        self.fake.selected = ["src"]
        core.copy_animation()
        self.dst = self.fake.add_curve("dst.translateX", [(0, 7), (35, 7), (50, 7)])
        self.fake.values.update({"dst.translateX": 7.0, self.dst + ".preInfinity": 0, self.dst + ".postInfinity": 0})
        self.fake.selected = ["dst"]
        self.fake.time = 30.0

    def test_copied_curves_are_kept_by_attribute_with_their_tangents(self):
        name, attrs = core._clip["anim"][0]
        self.assertEqual(name, "src")
        data = attrs["translateX"]
        self.assertEqual((data["times"], data["values"]), ([0.0, 10.0], [1.0, 2.0]))
        self.assertEqual((data["itt"], data["weighted"], data["pre"], data["post"]), (["fixed", "auto"], True, 3, 4))

    def test_a_paste_at_the_current_frame_replaces_only_the_pasted_span(self):
        core.paste_animation()
        self.assertEqual(self.fake.keys_of("dst.translateX"), [(0, 7), (30, 1), (40, 2), (50, 7)])
        edits = [e for c, e in self.fake.tangent_edits if c == self.dst]
        self.assertIn({"time": (30.0, 30.0), "lock": False}, edits)
        self.assertIn({"time": (30.0, 30.0), "itt": "fixed", "ott": "linear", "ia": 15.0}, edits)
        self.assertIn({"time": (40.0, 40.0), "itt": "auto", "ott": "linear"}, edits)
        self.assertNotIn({"time": (40.0, 40.0), "lock": False}, edits)
        #  the target's own curve keeps its weighting and its infinity
        self.assertFalse(any("weightedTangents" in e for e in edits))
        self.assertEqual(self.fake.values[self.dst + ".preInfinity"], 0)
        self.assertIn("1 controls at frame 30", self.fake.messages[-1])

    def test_an_insert_pushes_the_later_keys_after_the_pasted_span(self):
        core.paste_animation("insert")
        self.assertEqual(self.fake.keys_of("dst.translateX"), [(0, 7), (30, 1), (40, 2), (46, 7), (61, 7)])

    def test_the_original_mode_replaces_the_curve_at_the_copied_frames(self):
        self.fake.curves[self.dst]["tangents"]["weightedTangents"] = [True]
        core.paste_animation("original")
        self.assertEqual(self.fake.keys_of("dst.translateX"), [(0, 1), (10, 2)])
        edits = [e for c, e in self.fake.tangent_edits if c == self.dst]
        self.assertIn({"weightedTangents": True}, edits)
        self.assertIn({"time": (0.0, 0.0), "itt": "fixed", "ott": "linear", "ia": 15.0, "iw": 2.0, "ow": 3.0}, edits)
        self.assertEqual((self.fake.values[self.dst + ".preInfinity"], self.fake.values[self.dst + ".postInfinity"]), (3, 4))
        self.assertIn("at the copied frames", self.fake.messages[-1])

    def test_an_unkeyed_target_gets_a_new_curve_with_the_copied_weighting(self):
        del self.fake.curves[self.dst]
        core.paste_animation()
        self.assertEqual(self.fake.keys_of("dst.translateX"), [(30, 1), (40, 2)])
        new = self.fake._curves_of("dst.translateX")[0]
        self.assertIn((new, {"weightedTangents": True}), self.fake.tangent_edits)

    def test_a_target_that_cannot_take_keys_is_skipped(self):
        del self.fake.curves[self.dst]
        self.fake.locked.add("dst.translateX")
        core.paste_animation()
        self.assertEqual(self.fake.keys_of("dst.translateX"), [])
        self.assertIn("onto 0 controls", self.fake.messages[-1])

    def test_nothing_copied_nothing_matching_or_no_keys_is_said(self):
        core._clip["anim"] = None
        core.paste_animation()
        self.assertIn("copy animation first", self.fake.warnings[-1])
        core._clip["anim"] = [("a", {}), ("b", {})]
        core.paste_animation()
        self.assertIn("no selected control matches", self.fake.warnings[-1])
        core._clip["anim"] = [("dst", {})]
        core.paste_animation()
        self.assertIn("no keys", self.fake.warnings[-1])

    def test_copying_nothing_asks_for_a_selection(self):
        self.fake.selected = []
        core.copy_animation()
        self.assertIn("select animated controls", self.fake.warnings[-1])


# ---------------------------------------------------------------- mirror

class Mirror(CoreTest):

    def setUp(self):
        super(Mirror, self).setUp()
        self.fake.transforms = ["|rig:FKWrist_L", "|rig:FKWrist_R", "|Right_hand", "|arm_r_ctrl", "|Rt_eye",
                                "|Lower_R"]

    def test_the_opposite_by_side_names(self):
        self.assertEqual(core.opposite("|rig:FKWrist_L"), "|rig:FKWrist_R")
        self.assertEqual(core.opposite("|Left_hand"), "|Right_hand")
        self.assertEqual(core.opposite("|grp|arm_l_ctrl"), "|arm_r_ctrl")
        self.assertEqual(core.opposite("|Lf_eye"), "|Rt_eye")
        self.assertEqual(core.opposite("|Lower_L"), "|Lower_R")
        self.assertIsNone(core.opposite("|spine"))
        self.assertIsNone(core.opposite("|other:FKWrist_L"))

    def pose(self, node, **values):
        self.fake.keyable[node] = list(values)
        for a, v in values.items():
            self.fake.values["%s.%s" % (node, a)] = v
        self.fake.values[node + ".parentMatrix[0]"] = translate(0, 0, 0)

    def test_a_centre_control_mirrors_onto_itself_across_the_yz_plane(self):
        self.pose("spine", translateX=3.0, translateY=4.0, rotateX=10.0, rotateY=20.0, rotateZ=30.0)
        self.fake.selected = ["spine"]
        core.mirror_pose()
        got = [self.fake.values["spine." + a] for a in ("translateX", "translateY", "rotateX", "rotateY", "rotateZ")]
        self.assertEqual(got, [-3.0, 4.0, 10.0, -20.0, -30.0])

    def test_a_left_right_pair_swaps_poses(self):
        self.pose("|rig:FKWrist_L", translateX=1.0, rotateY=10.0)
        self.pose("|rig:FKWrist_R", translateX=-5.0, rotateY=-50.0)
        self.fake.add_curve("|rig:FKWrist_R.translateX", [(0, 0)])
        self.fake.selected = ["|rig:FKWrist_L"]
        core.mirror_pose()
        self.assertEqual(self.fake.values["|rig:FKWrist_R.translateX"], -1.0)
        self.assertEqual(self.fake.values["|rig:FKWrist_R.rotateY"], -10.0)
        self.assertEqual(self.fake.values["|rig:FKWrist_L.translateX"], 5.0)
        self.assertEqual(self.fake.values["|rig:FKWrist_L.rotateY"], 50.0)
        self.assertEqual([k[0] for k in self.fake.keyed], ["|rig:FKWrist_R"])

    def test_a_joint_s_orient_counts_in_the_signs(self):
        self.pose("src", translateX=1.0, translateZ=1.0, rotateX=1.0, rotateZ=1.0)
        self.pose("dst", translateX=0.0, translateZ=0.0, rotateX=0.0, rotateZ=0.0)
        self.fake.node_types["dst"] = "joint"
        self.fake.values["dst.jointOrient"] = [(0.0, 180.0, 0.0)]
        values = core._mirrored_values("src", "dst")
        self.assertEqual((values["translateX"], values["translateZ"]), (1.0, -1.0))
        self.assertEqual((values["rotateX"], values["rotateZ"]), (-1.0, 1.0))

    def test_frames_that_do_not_line_up_copy_the_values_unsigned(self):
        self.pose("src", translateX=2.0)
        self.pose("dst", translateX=0.0)
        self.fake.values["dst.parentMatrix[0]"] = list(om.MEulerRotation(0, math.radians(45), 0).asMatrix())
        self.assertIsNone(core._axis_signs("src", "dst"))
        self.assertEqual(core._mirrored_values("src", "dst"), {"translateX": 2.0})

    def test_the_opposite_is_selected_or_added(self):
        self.fake.selected = ["|rig:FKWrist_L", "|spine"]
        core.select_opposite(add=True)
        self.assertEqual(self.fake.selections[-1], ((["|rig:FKWrist_R"],), {"add": True}))
        self.fake.selected = ["|spine"]
        core.select_opposite()
        self.assertEqual(len(self.fake.selections), 1)

    def test_mirroring_nothing_asks_for_a_selection(self):
        core.mirror_pose()
        self.assertIn("select controls to mirror", self.fake.warnings[-1])


# ---------------------------------------------------------------- xform tools

class Xform(CoreTest):

    def test_align_puts_every_object_on_the_last_one(self):
        self.fake.selected = ["a", "b", "target"]
        self.fake.values["target.worldMatrix[0]"] = translate(5, 6, 7)
        core.align_objects()
        self.assertEqual([(n, kw["matrix"]) for n, _t, kw in self.fake.xforms],
                         [("a", translate(5, 6, 7)), ("b", translate(5, 6, 7))])
        self.fake.selected = ["a"]
        core.align_objects()
        self.assertIn("target last", self.fake.warnings[-1])

    def test_world_space_copied_from_one_object_pastes_onto_the_selection(self):
        self.fake.selected = ["a"]
        self.fake.values["a.worldMatrix[0]"] = translate(1, 2, 3)
        self.fake.existing.add("a")
        core.copy_world_space()
        self.fake.selected = ["b", "c"]
        core.paste_world_space()
        self.assertEqual([n for n, _t, _kw in self.fake.xforms], ["b", "c"])
        self.assertTrue(all(kw["matrix"] == translate(1, 2, 3) for _n, _t, kw in self.fake.xforms))

    def test_world_space_on_all_keys_is_set_and_keyed_at_each_key(self):
        core._clip["world"] = [("a", translate(1, 2, 3))]
        self.fake.existing.add("a")
        self.fake.add_curve("a.tx", [(4, 0), (8, 0)])
        core.paste_world_space(all_keys=True)
        self.assertEqual([t for _n, t, _kw in self.fake.xforms], [4.0, 8.0])
        self.assertEqual([(n, t) for n, t, _kw in self.fake.keyed], [("a", 4), ("a", 8)])

    def test_world_space_needs_a_copy_and_a_selection(self):
        core.copy_world_space()
        core.paste_world_space()
        self.assertEqual(len(self.fake.warnings), 2)

    def test_a_relationship_follows_the_anchor_rigidly(self):
        self.fake.selected = ["follower", "anchor"]
        self.fake.values.update({"follower.worldMatrix[0]": translate(12, 1, 0),
                                 "anchor.worldMatrix[0]": translate(10, 0, 0)})
        self.fake.existing.update(("follower", "anchor"))
        core.copy_relationship()
        self.assertIn("anchor", self.fake.messages[-1])
        self.fake.values["anchor.worldMatrix[0]"] = rot_z(90, at=(20, 0, 0))
        core.paste_relationship()
        self.assertTrue(close(self.fake.xforms[-1][2]["matrix"][12:15], [19, 2, 0]))

    def test_a_translate_only_relationship_keeps_the_world_offset(self):
        for a in ("rx", "ry", "rz", "sx", "sy", "sz"):
            self.fake.values["follower." + a] = 0.0
        self.fake.selected = ["follower", "anchor"]
        self.fake.values.update({"follower.worldMatrix[0]": translate(12, 1, 0),
                                 "anchor.worldMatrix[0]": translate(10, 0, 0)})
        self.fake.existing.update(("follower", "anchor"))
        core.copy_relationship()
        self.fake.values["anchor.worldMatrix[0]"] = rot_z(90, at=(20, 0, 0))
        core.paste_relationship(channels="t")
        self.assertTrue(close(self.fake.xforms[-1][2]["matrix"][12:15], [22, 1, 0]))

    def test_a_relationship_needs_two_objects_a_copy_and_an_anchor_still_there(self):
        self.fake.selected = ["one"]
        core.copy_relationship()
        core.paste_relationship()
        core._clip["rel"] = ("gone", [])
        core.paste_relationship()
        self.assertEqual(len(self.fake.warnings), 3)
        self.assertIn("anchor no longer exists", self.fake.warnings[-1])


# ---------------------------------------------------------------- space switch

class SpaceSwitch(CoreTest):

    def setUp(self):
        super(SpaceSwitch, self).setUp()
        for n in ("hand", "foot"):
            self.fake.keyable[n] = ["space", "follow", "tx"]
            self.fake.types.update({n + ".space": "enum", n + ".follow": "enum"})
            self.fake.enums.update({n + ".space": "World:Hand:Chest", n + ".follow": "Off:On"})
        self.fake.keyable["foot"] = ["space", "tx"]

    def test_enum_attributes_shared_by_every_node(self):
        self.assertEqual(core.enum_attrs(["hand", "foot"]), {"space": ["World", "Hand", "Chest"]})
        self.assertEqual(core.enum_attrs([]), {})

    def test_a_switch_keeps_the_object_where_it_stands(self):
        self.fake.selected = ["hand"]
        self.fake.values.update({"hand.space": 0, "hand.worldMatrix[0]": translate(3, 4, 5)})
        self.fake.add_curve("hand.tx", [(0, 0)])
        core.space_switch("space", 2)
        self.assertEqual(self.fake.values["hand.space"], 2)
        self.assertEqual(self.fake.xforms[-1][2]["matrix"], translate(3, 4, 5))
        self.assertIn(("hand", 0.0, {"attribute": "space"}), self.fake.keyed)

    def test_a_switch_on_all_keys_keeps_the_motion_at_each_key(self):
        self.fake.selected = ["hand"]
        self.fake.add_curve("hand.tx", [(0, 0), (10, 1)])
        self.fake.values.update({("hand.worldMatrix[0]", 0.0): translate(0, 0, 0),
                                 ("hand.worldMatrix[0]", 10.0): translate(9, 0, 0)})
        core.space_switch("space", 1, all_keys=True)
        attr_keys = [(t, kw["t"], kw["v"]) for _n, t, kw in self.fake.keyed if kw.get("attribute") == "space"]
        self.assertEqual([(t, v) for _now, t, v in attr_keys], [(0.0, 1), (10.0, 1)])
        self.assertEqual([(t, kw["matrix"][12]) for _n, t, kw in self.fake.xforms], [(0.0, 0.0), (10.0, 9.0)])

    def test_nothing_happens_when_no_selected_node_has_the_attribute(self):
        self.fake.selected = ["box"]
        core.space_switch("space", 1)
        self.assertEqual(self.fake.xforms, [])


# ---------------------------------------------------------------- temp controls / pivot

class TempControls(CoreTest):

    def setUp(self):
        super(TempControls, self).setUp()
        self.fake.namespaceInfo = mock.MagicMock(return_value=":")
        self.fake.spaceLocator = mock.MagicMock(side_effect=lambda name: [name])
        self.fake.parent = mock.MagicMock(side_effect=lambda node, grp: ["|%s|%s" % (grp, node)])
        self.fake.parentConstraint = mock.MagicMock(return_value=["pc1"])

    def test_a_locator_per_control_follows_its_world_motion_and_drives_it(self):
        self.fake.selected = ["armA", "armB"]
        self.fake.add_curve("armA.tx", [(0, 0), (10, 1)])
        self.fake.add_curve("armB.tx", [(5, 0)])
        for n in ("armA", "armB"):
            for t in (0.0, 5.0, 10.0):
                self.fake.values[("%s.worldMatrix[0]" % n, t)] = translate(t, 0, 1 if n == "armB" else 0)
        core.toggle_temp_controls()
        locs = ["|AT_TEMP|AT_tempCtrl_armA", "|AT_TEMP|AT_tempCtrl_armB"]
        self.assertEqual([self.fake.values[l + ".atTarget"] for l in locs], ["armA", "armB"])
        self.assertEqual(self.fake.values[locs[0] + "Shape.localScale"], [10, 10, 10])
        placed = [(n, t, kw["matrix"][12:15]) for n, t, kw in self.fake.xforms]
        self.assertIn((locs[1], 5.0, [5.0, 0.0, 1.0]), placed)
        self.assertEqual(sorted(set(t for n, t, kw in self.fake.keyed if n == locs[0])), [0.0, 5.0, 10.0])
        self.fake.parentConstraint.assert_any_call(locs[0], "armA", mo=True, skipTranslate="none", skipRotate="none")
        self.assertEqual(self.fake.selections[-1][0], (locs,))
        self.assertIn("temp controls on 2 objects", self.fake.messages[-1])

    def test_a_control_with_every_channel_locked_is_not_constrained(self):
        for ax in "xyz":
            self.fake.locked.update(("c.t" + ax, "c.r" + ax))
        self.assertIsNone(core._constrain("loc", "c"))
        self.fake.parentConstraint.assert_not_called()
        self.fake.locked = {"c.tx", "c.rz"}
        self.assertEqual(core._constrain("loc", "c"), "pc1")
        self.fake.parentConstraint.assert_called_once_with("loc", "c", mo=True, skipTranslate=["x"], skipRotate=["z"])

    def test_the_second_click_bakes_the_controls_back_and_takes_the_locators_away(self):
        loc = "|AT_TEMP|AT_tempCtrl_armA"
        self.fake.values[loc + ".atTarget"] = "armA"
        self.fake.existing.add("armA")
        self.fake.ls = mock.MagicMock(side_effect=lambda *a, **k: [loc] if a == (":AT_tempCtrl_*",) else [])
        self.fake.add_curve(loc + ".tx", [(2, 0), (6, 0)])
        self.fake.relatives = {("armA", "parentConstraint"): ["armA|pc1"]}
        for t in (2.0, 6.0):
            self.fake.values[("armA.worldMatrix[0]", t)] = translate(t, 1, 0)
        self.fake.existing.add(":AT_TEMP")
        self.assertTrue(core.temp_controls_active())
        core.toggle_temp_controls()
        self.assertIn(((["armA|pc1"],), {}), self.fake.deleted)
        self.assertIn((([loc],), {}), self.fake.deleted)
        self.assertIn(((":AT_TEMP",), {}), self.fake.deleted)
        self.assertEqual([(n, t) for n, t, _kw in self.fake.xforms], [("armA", 2.0), ("armA", 6.0)])
        self.assertEqual([(n, t) for n, t, _kw in self.fake.keyed], [("armA", 2), ("armA", 6)])
        self.assertIn("baked back", self.fake.messages[-1])

    def test_temp_controls_need_a_selection(self):
        core.toggle_temp_controls()
        self.assertIn("select controls", self.fake.warnings[-1])

    def test_a_temp_pivot_drives_the_selection_from_the_last_one_s_pivot(self):
        self.fake.selected = ["a", "b"]
        self.fake.values["b.rotatePivot"] = [1.0, 2.0, 3.0]
        core.toggle_temp_pivot()
        piv = "|AT_TEMP|AT_tempPivot"
        self.assertEqual(self.fake.values[piv + ".atTargets"], "a;b")
        self.assertEqual(self.fake.xforms[-1][2], {"ws": True, "t": [1.0, 2.0, 3.0]})
        self.assertEqual([c.args[1] for c in self.fake.parentConstraint.call_args_list], ["a", "b"])
        self.fake.setToolTo.assert_called_once_with("RotateSuperContext")

    def test_the_second_pivot_click_keeps_the_objects_where_they_are(self):
        piv = ":AT_tempPivot"
        self.fake.existing.update((piv, "a"))
        self.fake.values[piv + ".atTargets"] = "a;gone"
        self.fake.values["a.worldMatrix[0]"] = translate(7, 0, 0)
        self.fake.add_curve("a.tx", [(0, 0)])
        core.toggle_temp_pivot()
        self.assertIn(((piv,), {}), self.fake.deleted)
        self.assertEqual(self.fake.xforms[-1][0], "a")
        self.assertEqual(self.fake.xforms[-1][2]["matrix"], translate(7, 0, 0))
        self.assertEqual(self.fake.keyed[-1][0], "a")
        self.assertEqual(self.fake.selections[-1][0], (["a"],))

    def test_a_temp_pivot_needs_a_selection(self):
        core.toggle_temp_pivot()
        self.assertIn("select the objects to pivot", self.fake.warnings[-1])

    def test_the_temp_group_goes_only_when_empty(self):
        self.fake.existing.add(":AT_TEMP")
        self.fake.relatives[(":AT_TEMP", "children")] = ["x"]
        core._drop_empty_temp_group()
        self.assertEqual(self.fake.deleted, [])
        self.assertEqual(core._shape("loc"), "locShape")
        self.fake.relatives[("loc", "shapes")] = ["|loc|AT_tempCtrl_IKArm_LShape"]
        self.assertEqual(core._shape("loc"), "|loc|AT_tempCtrl_IKArm_LShape")


# ---------------------------------------------------------------- motion trails

class Trails(CoreTest):

    def setUp(self):
        super(Trails, self).setUp()
        self.handles = []
        self.fake.ls = mock.MagicMock(side_effect=self.ls)
        self.fake.snapshot = mock.MagicMock(side_effect=lambda n, **kw: [kw["name"] + "Handle", kw["name"]])
        self.fake.addAttr = mock.MagicMock()
        self.fake.parent = mock.MagicMock()

    def ls(self, *args, **kw):
        if kw.get("uuid"):
            return ["uuid-" + args[0]]
        if kw.get("sl"):
            return list(self.fake.selected)
        return []

    def test_trail_handles_say_whose_trail_they_are(self):
        self.fake.relatives[("|G", "children")] = ["|G|h1", "|G|h2"]
        self.fake.values["|G|h1." + core.TRAIL_OF] = "uuid-a"
        self.fake.existing.add("|G|h1." + core.TRAIL_OF)
        with mock.patch.object(core, "trail_groups", return_value=["|G"]):
            self.assertEqual(core.trail_handles(), [("|G|h1", "uuid-a"), ("|G|h2", None)])

    def test_a_trail_is_built_only_for_objects_without_one(self):
        self.fake.range = (10.0, 41.0)
        with mock.patch.object(core, "trail_handles", return_value=[("|G|h", "uuid-a")]), \
                mock.patch.object(core, "_trail_group", return_value="|AT_MOTION_TRAILS"):
            self.assertEqual(core._build_trails(["a", "rig:b"]), 1)
        self.fake.snapshot.assert_called_once_with("rig:b", motionTrail=True, increment=1, startTime=10.0,
                                                   endTime=40.0, name="AT_trail_b")
        self.assertEqual(self.fake.values["AT_trail_bHandle." + core.TRAIL_OF], "uuid-rig:b")
        self.fake.parent.assert_called_once_with("AT_trail_bHandle", "|AT_MOTION_TRAILS")

    def test_the_trails_group_is_the_marked_one_else_a_new_one(self):
        self.fake.ls = mock.MagicMock(side_effect=lambda *a, **k: ["|AT_MOTION_TRAILS4"] if a[0].startswith("*.") else
                                      ["|" + a[0]])
        self.assertEqual(core._trail_group(), "|AT_MOTION_TRAILS4")
        self.fake.ls = mock.MagicMock(side_effect=lambda *a, **k: [] if a[0].startswith("*.") else ["|" + a[0]])
        self.assertEqual(core._trail_group(), "|" + core.TRAIL_GRP)
        self.fake.addAttr.assert_called_once_with(core.TRAIL_GRP, longName=core.TRAIL_MARKER, attributeType="bool")

    def test_add_keeps_the_others_and_says_when_there_is_nothing_new(self):
        core.add_motion_trail()
        self.assertIn("select the controls", self.fake.warnings[-1])
        self.fake.selected = ["a"]
        with mock.patch.object(core, "_build_trails", return_value=0):
            core.add_motion_trail()
        self.assertIn("has its trails already", self.fake.messages[-1])

    def test_clear_takes_the_selection_s_trails_and_their_nodes(self):
        core.clear_motion_trail()
        self.assertIn("select the controls whose trails", self.fake.warnings[-1])
        self.fake.selected = ["a"]
        with mock.patch.object(core, "trail_handles", return_value=[("|G|h", "uuid-b")]):
            core.clear_motion_trail()
        self.assertIn("has no trails", self.fake.warnings[-1])
        self.fake.relatives[("|G|h", "shapes")] = ["|G|h|hShape"]
        self.fake.listConnections = mock.MagicMock(return_value=["motionTrail1"])
        self.fake.existing.update(("motionTrail1", "|G|h"))
        with mock.patch.object(core, "trail_handles", return_value=[("|G|h", "uuid-a")]), \
                mock.patch.object(core, "trail_groups", return_value=["|G"]):
            core.clear_motion_trail()
        self.assertEqual([d[0][0] for d in self.fake.deleted], ["motionTrail1", "|G|h", "|G"])

    def test_clear_all_takes_every_group(self):
        self.fake.existing.add("|G")
        with mock.patch.object(core, "trail_groups", return_value=["|G"]):
            core.clear_all_motion_trails()
        self.assertIn((("|G",), {}), self.fake.deleted)


# ---------------------------------------------------------------- bookmarks, viewport, curve tools

class Bookmarks(CoreTest):

    def setUp(self):
        super(Bookmarks, self).setUp()
        self.fake.ls = mock.MagicMock(side_effect=lambda **kw: ["bmB", "bmA"] if kw.get("type") == "timeSliderBookmark"
                                      else [])
        self.fake.values.update({"bmA.name": "intro", "bmA.timeRangeStart": 10.0, "bmA.timeRangeStop": 20.0,
                                 "bmB.name": "", "bmB.timeRangeStart": 40.0, "bmB.timeRangeStop": 45.0})

    def test_bookmarks_in_time_order_named_by_their_node_when_unnamed(self):
        self.assertEqual(core.bookmarks(), [("intro", 10.0, 20.0), ("bmB", 40.0, 45.0)])

    def test_next_and_previous_bookmark(self):
        self.fake.time = 15.0
        core.go_to_bookmark(1)
        self.assertEqual(self.fake.time, 40.0)
        core.go_to_bookmark(-1)
        self.assertEqual(self.fake.time, 10.0)
        core.go_to_bookmark(-1)
        self.assertEqual(self.fake.time, 10.0)

    def test_a_bookmark_on_the_highlight_or_the_current_frame(self):
        tsb = mock.MagicMock()
        with mock.patch.object(core, "_bookmarks", return_value=tsb):
            self.fake.range = (10.0, 21.0)
            core.add_bookmark()
            self.fake.range = None
            self.fake.time = 7.0
            core.add_bookmark()
            core.delete_bookmark_here()
        self.assertEqual(tsb.createBookmark.call_args_list, [mock.call(start=10.0, stop=20.0),
                                                             mock.call(start=7.0, stop=7.0)])
        tsb.deleteBookmarkAtCurrentTime.assert_called_once_with()

    def test_clear_takes_every_bookmark(self):
        core.clear_bookmarks()
        self.assertEqual(self.fake.deleted, [((["bmB", "bmA"],), {})])
        self.fake.ls = mock.MagicMock(return_value=[])
        core.clear_bookmarks()
        self.assertEqual(len(self.fake.deleted), 1)

    def test_the_viewport_suspended_is_remembered_for_the_next_walk(self):
        core.set_viewport_suspended(1)
        self.assertIs(core._state["suspended"], True)
        self.assertEqual(self.fake.refreshes, [True])
        core.run_at_times([], lambda t: None)
        self.assertEqual(self.fake.refreshes[-1], True)
        core.set_viewport_suspended(False)
        self.assertIn("resumed", self.fake.messages[-1])


class CurveTools(CoreTest):

    def test_the_euler_filter_takes_rotation_curves_only(self):
        self.fake.selected = ["c"]
        rx = self.fake.add_curve("c.rx", [(0, 0)], kind="animCurveTA")
        self.fake.add_curve("c.tx", [(0, 0)])
        core.euler_filter()
        self.fake.filterCurve.assert_called_once_with([rx], filter="euler")
        self.assertIn("1 curves", self.fake.messages[-1])

    def test_with_nothing_selected_the_euler_filter_takes_the_scene(self):
        other = self.fake.add_curve("o.ry", [(0, 0)], kind="animCurveTA")
        core.euler_filter()
        self.fake.filterCurve.assert_called_once_with([other], filter="euler")
        self.fake.curves.clear()
        core.euler_filter()
        self.fake.filterCurve.assert_called_once()

    def test_the_rig_s_controls_are_the_curves_of_its_namespace(self):
        core.select_rig_controls()
        self.assertIn("select one control", self.fake.warnings[-1])
        self.fake.selected = ["rig:FKWrist_L"]
        self.fake.ls_more = lambda *a, **k: (["|rig:a|rig:aShape", "|rig:a|rig:aShape1", "|rig:b|rig:bShape"]
                                             if a == ("rig:*",) and k.get("type") == "nurbsCurve" else [])
        self.fake.relatives = {("|rig:a|rig:aShape", "parent"): ["|rig:a"], ("|rig:a|rig:aShape1", "parent"): ["|rig:a"],
                               ("|rig:b|rig:bShape", "parent"): ["|rig:b"]}
        core.select_rig_controls()
        self.assertEqual(self.fake.selections[-1][0], (["|rig:a", "|rig:b"],))

    def test_the_animated_controls_of_the_selection_s_namespace(self):
        self.fake.add_curve("rig:a.tx", [(0, 0)])
        self.fake.add_curve("rig:a.ty", [(0, 0)])
        self.fake.add_curve("other:b.tx", [(0, 0)])
        self.fake.selected = ["rig:c"]
        core.select_animated()
        self.assertEqual(self.fake.selections[-1][0], (["rig:a"],))
        self.fake.selected = []
        core.select_animated()
        self.assertEqual(self.fake.selections[-1][0], (["rig:a", "other:b"],))

    def test_key_delete_static_and_bake_act_on_the_selection(self):
        core.key_selection()
        core.delete_static_channels()
        core.bake_selection()
        self.assertEqual(self.fake.keyed, [])
        self.fake.bakeResults.assert_not_called()
        self.fake.selected = ["a"]
        self.fake.range = (5.0, 16.0)
        core.key_selection()
        core.delete_static_channels()
        core.bake_selection()
        self.assertEqual(self.fake.keyed[-1][0], ["a"])
        self.assertIn(((["a"],), {"staticChannels": True}), self.fake.deleted)
        self.fake.bakeResults.assert_called_once_with(["a"], t=(5.0, 15.0), simulation=True, sampleBy=1,
                                                      preserveOutsideKeys=True)


# ---------------------------------------------------------------- select sets in the library

class SelectSets(CoreTest):

    def setUp(self):
        super(SelectSets, self).setUp()
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder, True)
        self.fake.internalVar = mock.MagicMock(return_value=self.folder + "/")
        self.fake.namespaceInfo = mock.MagicMock(return_value=":")
        self.scene_nodes = []
        self.fake.ls = mock.MagicMock(side_effect=self.ls)
        self.fake.sets = mock.MagicMock(side_effect=lambda node, q=False: {"AT_sel_old": ["rig:FKHead_M"]}.get(node))

    def ls(self, *args, **kw):
        if kw.get("sl"):
            return list(self.fake.selected)
        if kw.get("type") == "objectSet":
            return ["AT_sel_old", "defaultObjectSet"]
        if kw.get("recursive"):
            keys = args[0]
            return [n for n in self.scene_nodes if n.split(":")[-1] in keys]
        return []

    def library(self):
        return core.load_library()

    def answer(self, button, text=""):
        self.fake.promptDialog = mock.MagicMock(side_effect=lambda **kw: text if kw.get("q") else button)

    def test_the_library_lives_in_maya_s_user_folder(self):
        self.assertEqual(os.path.normpath(core.library_path()),
                         os.path.normpath(os.path.join(self.folder, core.LIBRARY_NAME)))

    def test_the_scene_s_old_sets_join_the_library_once(self):
        self.assertEqual(core.selection_sets(), [("old", "old")])
        self.assertEqual(self.library()["sets"]["old"]["members"], ["FKHead_M"])
        self.assertTrue(core.has_set("old"))
        self.assertFalse(core.has_set("missing"))

    def test_a_set_is_made_named_and_updated_from_the_selection(self):
        self.fake.selected = ["rig:FKWrist_L", "rig:FKElbow_L"]
        self.answer("OK", "  left arm! ")
        core.create_selection_set()
        self.assertEqual(self.library()["sets"]["left_arm_"]["members"], ["FKWrist_L", "FKElbow_L"])
        self.assertIn("saved: 2 objects", self.fake.messages[-1])
        core.paint_set("left_arm_", "#c89be8")
        self.fake.selected = ["rig:FKWrist_L"]
        core.create_selection_set()
        entry = self.library()["sets"]["left_arm_"]
        self.assertEqual((entry["members"], entry["colour"]), (["FKWrist_L"], "#c89be8"))
        self.assertIn("updated", self.fake.messages[-1])

    def test_a_cancelled_or_empty_name(self):
        self.fake.selected = ["a"]
        self.answer("Cancel")
        core.create_selection_set()
        self.assertEqual(self.library()["sets"], {})
        self.answer("OK", "   ")
        core.create_selection_set()
        self.assertEqual(list(self.library()["sets"]), ["set"])

    def test_a_set_needs_a_selection(self):
        core.create_selection_set()
        core.update_selection_set("x")
        self.assertEqual(len(self.fake.warnings), 2)

    def test_the_set_s_members_in_this_scene_from_the_selected_rig(self):
        core.save_library({"sets": {"hands": {"members": ["FKWrist_L", "FKWrist_R"], "colour": None}}, "seen": []})
        self.scene_nodes = ["rig:FKWrist_L", "rig:FKWrist_R", "rig1:FKWrist_L", "rig1:FKWrist_R"]
        self.fake.selected = ["rig1:FKHead_M"]
        self.assertEqual(core.set_members("hands"), ["rig1:FKWrist_L", "rig1:FKWrist_R"])
        self.assertEqual(core.set_size("hands"), 2)
        core.select_set("hands", add=True)
        self.assertEqual(self.fake.selections[-1], ((["rig1:FKWrist_L", "rig1:FKWrist_R"],), {"add": True}))
        core.deselect_set("hands")
        self.assertEqual(self.fake.selections[-1], ((["rig1:FKWrist_L", "rig1:FKWrist_R"],), {"deselect": True}))
        self.assertEqual(core.set_members("nothing"), [])

    def test_a_set_with_none_of_its_objects_here_is_said(self):
        core.save_library({"sets": {"hands": {"members": ["FKWrist_L"], "colour": None}}, "seen": []})
        core.select_set("hands")
        self.assertIn("none of its objects", self.fake.warnings[-1])
        core.deselect_set("hands")
        self.assertEqual(self.fake.selections, [])

    def test_a_scene_tab_keeps_the_set_inside_it(self):
        core.save_library({"sets": {"hands": {"members": ["FKWrist_L"], "colour": None}}, "seen": []})
        self.scene_nodes = ["rig:FKWrist_L", "tab_b:rig:FKWrist_L"]
        self.fake.namespaceInfo = mock.MagicMock(return_value="tab_b")
        self.assertEqual(core.set_members("hands"), ["tab_b:rig:FKWrist_L"])

    def test_update_rename_colour_and_delete(self):
        core.save_library({"sets": {"a": {"members": ["x"], "colour": None}, "b": {"members": [], "colour": None}},
                           "seen": []})
        self.fake.selected = ["ns:y", "ns:z"]
        core.update_selection_set("a")
        self.assertEqual(self.library()["sets"]["a"]["members"], ["y", "z"])
        self.answer("OK", "b")
        self.assertIsNone(core.rename_selection_set("a"))
        self.assertIn("already exists", self.fake.warnings[-1])
        self.answer("OK", "a")
        self.assertIsNone(core.rename_selection_set("a"))
        self.answer("OK", "renamed")
        self.assertEqual(core.rename_selection_set("a"), "renamed")
        self.answer("OK", "fresh")
        self.assertIsNone(core.rename_selection_set("missing"))
        self.assertEqual(sorted(self.library()["sets"]), ["b", "renamed"])
        core.paint_set("renamed", "#7fa9e6")
        core.paint_set("missing", "#7fa9e6")
        self.assertEqual(core.set_colour("renamed"), "#7fa9e6")
        self.assertIsNone(core.set_colour("b"))
        core.delete_selection_set("renamed")
        core.delete_selection_set("missing")
        self.assertEqual(list(self.library()["sets"]), ["b"])
        self.assertEqual(sum("deleted" in m for m in self.fake.messages), 1)


# ---------------------------------------------------------------- anim recovery

class Recovery(CoreTest):

    def setUp(self):
        super(Recovery, self).setUp()
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.fake.internalVar = mock.MagicMock(return_value=self.root + "/")
        self.folder = os.path.join(self.root + "/", "AT_recovery")         # as Maya's userAppDir ends
        self.modified = True
        self.scene = os.path.join(self.root, "scenes", "shot_1.mb")
        self.exported = []
        self.file_calls = []
        self.fake.file = mock.MagicMock(side_effect=self.file)

    def file(self, *args, **kw):
        self.file_calls.append((args, kw))
        if kw.get("q"):
            if kw.get("modified"):
                return self.modified
            if kw.get("sn"):
                return self.scene
        if kw.get("exportAll"):
            self.exported.append(args[0])
            with open(args[0], "w") as handle:
                handle.write("scene")

    def test_an_unmodified_scene_is_not_backed_up(self):
        self.modified = False
        self.assertIsNone(core.save_recovery())
        self.assertEqual(self.exported, [])

    def test_a_backup_is_written_whole_then_named_and_only_the_newest_kept(self):
        os.makedirs(self.folder)
        old = ["shot_1_202001%02d_120000.mb" % d for d in range(1, 23)]
        for name in old + ["shot_1_2_20261001_120000.mb"]:
            open(os.path.join(self.folder, name), "w").close()
        path = core.save_recovery()
        self.assertTrue(os.path.isfile(path))
        self.assertTrue(self.exported[0].endswith(".partial.mb"))
        self.assertFalse(os.path.exists(self.exported[0]))
        names = sorted(os.listdir(self.folder))
        mine = [n for _when, n in core.backups_of("shot_1", names)]
        self.assertEqual(len(mine), core.RECOVERY_KEEP)
        self.assertEqual(mine[-1], os.path.basename(path))
        self.assertNotIn(old[0], names)
        self.assertIn("shot_1_2_20261001_120000.mb", names)

    def test_an_untitled_scene_is_backed_up_as_untitled(self):
        self.scene = ""
        path = core.save_recovery(force=True)
        self.assertTrue(os.path.basename(path).startswith("untitled_"))

    def make_scene(self, saved_at, backups):
        os.makedirs(os.path.dirname(self.scene), exist_ok=True)
        open(self.scene, "w").close()
        stamp = saved_at.timestamp()
        os.utime(self.scene, (stamp, stamp))
        os.makedirs(self.folder, exist_ok=True)
        for name in backups:
            open(os.path.join(self.folder, name), "w").close()

    def test_newer_changes_are_offered_once_and_opened_in_place_of_the_scene(self):
        self.make_scene(datetime.datetime(2026, 10, 22, 15, 0, 0),
                        ["shot_1_20261022_140000.mb", "shot_1_20261022_163000.mb"])
        self.fake.confirmDialog = mock.MagicMock(return_value="Open recovered")
        with mock.patch.object(core, "restore_recovery") as restore:
            core.check_recovery()
            core.check_recovery()
        self.fake.confirmDialog.assert_called_once()
        self.assertIn("16:30:00", self.fake.confirmDialog.call_args.kwargs["message"])
        restore.assert_called_once_with(os.path.join(self.folder, "shot_1_20261022_163000.mb"), self.scene)

    def test_keeping_the_saved_file_or_nothing_newer_opens_nothing(self):
        self.make_scene(datetime.datetime(2026, 10, 22, 15, 0, 0), ["shot_1_20261022_163000.mb"])
        self.fake.confirmDialog = mock.MagicMock(return_value="Keep saved file")
        with mock.patch.object(core, "restore_recovery") as restore:
            core.check_recovery()
        restore.assert_not_called()
        os.remove(os.path.join(self.folder, "shot_1_20261022_163000.mb"))
        os.utime(self.scene, (datetime.datetime(2026, 10, 22, 17, 0, 0).timestamp(),) * 2)
        self.fake.confirmDialog.reset_mock()
        core.check_recovery()
        self.fake.confirmDialog.assert_not_called()

    def test_no_scene_no_folder_or_a_backup_itself_is_not_checked(self):
        self.scene = ""
        core.check_recovery()
        self.scene = os.path.join(self.folder, "shot_1_20261022_163000.mb")
        self.make_scene(datetime.datetime(2026, 10, 22, 15, 0, 0), [])
        core.check_recovery()
        self.fake.confirmDialog.assert_not_called()
        self.assertNotIn("recovery_checked", core._state)

    def test_a_recovered_backup_is_named_as_the_scene_and_left_modified(self):
        core.restore_recovery("C:/r/shot_1_20261022_163000.mb", "C:/scenes/shot_1.ma")
        self.assertEqual([c for c in self.file_calls],
                         [(("C:/r/shot_1_20261022_163000.mb",), {"open": True, "force": True}),
                          ((), {"rename": "C:/scenes/shot_1.ma"}), ((), {"type": "mayaAscii"}),
                          ((), {"modified": True})])
        self.assertIn("shot_1_20261022_163000.mb", self.fake.messages[-1])

    def test_the_check_runs_after_every_open_and_once_now(self):
        fake_om = types.SimpleNamespace(MMessage=mock.MagicMock(), MSceneMessage=mock.MagicMock(kAfterOpen=7))
        fake_om.MSceneMessage.addCallback.return_value = "cb2"
        fake_om.MMessage.removeCallback.side_effect = RuntimeError("gone already")
        core._state["recovery_callback"] = "cb1"
        with mock.patch.object(core, "om", fake_om), mock.patch.object(core, "_deferred_check") as deferred:
            core.install_recovery_check()
        fake_om.MMessage.removeCallback.assert_called_once_with("cb1")
        fake_om.MSceneMessage.addCallback.assert_called_once_with(7, deferred)
        self.assertEqual(core._state["recovery_callback"], "cb2")
        deferred.assert_called_once_with()

    def test_the_check_waits_for_maya_to_settle(self):
        import maya.utils
        with mock.patch.object(maya.utils, "executeDeferred", create=True) as later:
            core._deferred_check("ignored")
        later.assert_called_once_with(core.check_recovery)

    def test_the_backups_folder_is_made_and_opened(self):
        with mock.patch.object(core.os, "startfile", create=True) as start:
            core.open_recovery_folder()
        self.assertTrue(os.path.isdir(self.folder))
        start.assert_called_once_with(self.folder)


if __name__ == "__main__":
    unittest.main()
