"""maya_channelbox.scene, the rest of it, on a fake cmds: what a channel reads as for
each kind of plug (enum, bool, locked, layered, muted with no curve, driven, ranged),
SHAPES / INPUTS / OUTPUTS read ourselves while Maya's box is hidden, and every write
the box sends - values, keys, mute, lock, connections, speed, precision, undo chunks,
layers - with what it says to cmds."""

import unittest
from unittest import mock

from maya_channelbox import scene


class Cmds(object):
    """Just enough of maya.cmds, recording what is asked to change."""

    def __init__(self):
        self.t = 10.0
        self.sel = ["|ctrl"]
        self.attrs = {"|ctrl": []}
        self.values = {}
        self.kinds = {}
        self.locked = set()
        self.ranges = {}
        self.enums = {}
        self.sources = {}                   # plug -> [source node]
        self.source_plugs = {}              # plug -> [source plug]
        self.types = {}
        self.downstream = {}                # node -> [destinations]
        self.keys = {}                      # plug -> (times, breakdowns, curve value)
        self.muted = set()
        self.nice = {}
        self.box = True
        self.box_lists = {}
        self.shapes = {}
        self.history = {}
        self.exists = set()
        self.calls = []
        self.fail = set()
        self.cut = {}

    def _maybe(self, name):
        if name in self.fail:
            raise RuntimeError(name + " failed")

    # reads ----------------------------------------------------------------------
    def currentTime(self, q=True):
        return self.t

    def ls(self, **kw):
        return list(self.sel)

    def listAttr(self, node, keyable=False, channelBox=False, userDefined=False):
        if userDefined:
            return []
        return list(self.attrs.get(node, [])) if keyable else []

    def nodeType(self, node):
        self._maybe("nodeType")
        return self.types.get(node, "transform")

    def getAttr(self, plug, type=False, lock=False):             # noqa: A002
        self._maybe("getAttr")
        if type:
            return self.kinds.get(plug, "double")
        if lock:
            return plug in self.locked
        value = self.values[plug]
        if isinstance(value, Exception):
            raise value
        return value

    def attributeName(self, plug, nice=False):
        self._maybe("attributeName")
        return self.nice.get(plug, plug.split(".")[-1].upper())

    def attributeQuery(self, attr, node=None, **kw):
        plug = node + "." + attr
        if kw.get("listEnum"):
            self._maybe("listEnum")
            return [self.enums[plug]] if plug in self.enums else None
        if kw.get("minExists") or kw.get("maxExists"):
            self._maybe("range")
            return plug in self.ranges
        if kw.get("minimum"):
            return [self.ranges[plug][0]]
        if kw.get("maximum"):
            return [self.ranges[plug][1]]
        if kw.get("exists"):
            self._maybe("exists:" + node)
            return attr in self.attrs.get(node, [])
        return False

    def listConnections(self, plug, source=True, destination=True, plugs=False, **kw):
        self._maybe("listConnections")
        if source and not destination:
            if plugs:
                return list(self.source_plugs.get(plug, []))
            return list(self.sources.get(plug, []))
        return list(self.downstream.get(plug, []))

    def mute(self, plug, q=False, disable=False, force=False):
        self._maybe("mute")
        if q:
            return plug in self.muted
        self.calls.append(("mute", plug, bool(disable), bool(force)))

    def keyframe(self, plug, q=True, timeChange=False, breakdown=False, eval=False, time=None):  # noqa: A002
        times, bds, curve = self.keys.get(plug, ([], [], None))
        if timeChange:
            return list(times)
        if breakdown:
            return list(bds)
        if eval:
            if isinstance(curve, Exception):
                raise curve
            return [curve]
        return []

    def channelBox(self, name, **kw):
        if kw.get("exists"):
            self._maybe("box")
            return self.box
        self._maybe("channelBox")
        if kw.get("edit"):
            self.calls.append(("channelBox", kw))
            return None
        for flag, found in self.box_lists.items():
            if kw.get(flag):
                return found
        if kw.get("speed"):
            return self.box_lists.get("speed_value")
        if kw.get("precision"):
            return self.box_lists.get("precision_value")
        return []

    def listRelatives(self, node, **kw):
        self._maybe("listRelatives")
        return list(self.shapes.get(node, []))

    def listHistory(self, node, **kw):
        self._maybe("listHistory")
        return list(self.history.get(node, []))

    def objExists(self, node):
        return node in self.exists

    # writes ---------------------------------------------------------------------
    def setAttr(self, plug, *args, **kw):
        self._maybe("setAttr")
        self.calls.append(("setAttr", plug, args, kw))

    def setKeyframe(self, plug, **kw):
        self._maybe("setKeyframe")
        self.calls.append(("setKeyframe", plug, kw))

    def cutKey(self, plug, **kw):
        self._maybe("cutKey")
        self.calls.append(("cutKey", plug, kw))
        return self.cut.get(plug)

    def select(self, nodes, **kw):
        self.calls.append(("select", list(nodes), kw))

    def disconnectAttr(self, src, dst):
        if ("disconnect", src) in self.fail:
            raise RuntimeError("cannot disconnect " + src)
        self.calls.append(("disconnectAttr", src, dst))

    def delete(self, node):
        self.calls.append(("delete", node))

    def undoInfo(self, **kw):
        self.calls.append(("undoInfo", kw))


class Base(unittest.TestCase):

    def setUp(self):
        self.saved = scene.cmds
        self.saved_static = dict(scene._STATIC)
        scene._STATIC.clear()
        self.fake = Cmds()
        scene.cmds = self.fake

    def tearDown(self):
        scene.cmds = self.saved
        scene._STATIC.clear()
        scene._STATIC.update(self.saved_static)

    def plug(self, attr, value, kind="double", **extra):
        p = "|ctrl." + attr
        self.fake.attrs["|ctrl"].append(attr)
        self.fake.values[p] = value
        self.fake.kinds[p] = kind
        return p

    def main(self):
        snap = scene.snapshot()
        return dict((c["attr"], c) for c in snap["sections"][0]["channels"])


class ChannelKinds(Base):

    def test_an_enum_reads_its_names_without_the_values(self):
        p = self.plug("blend", 2, kind="enum")
        self.fake.enums[p] = "Off:On=3:Both"
        row = self.main()["blend"]
        self.assertEqual((row["kind"], row["value"], row["names"]), ("enum", 2, ["Off", "On", "Both"]))

    def test_an_enum_whose_names_cannot_be_read_has_none(self):
        p = self.plug("blend", 0, kind="enum")
        self.fake.enums[p] = "A:B"
        self.fake.fail.add("listEnum")
        self.assertEqual(self.main()["blend"]["names"], [])

    def test_a_non_enum_has_no_names(self):
        self.plug("tx", 1.0)
        self.assertIsNone(self.main()["tx"]["names"])

    def test_a_bool_reads_as_an_int_and_is_never_changed_off_its_curve(self):
        p = self.plug("visibility", True, kind="bool")
        self.fake.sources[p] = ["vis_curve"]
        self.fake.types["vis_curve"] = "animCurveTU"
        self.fake.keys[p] = ([0.0, 10.0], [], 0.0)       # the curve says off, the plug on
        row = self.main()["visibility"]
        self.assertEqual(row["value"], 1)
        self.assertIs(type(row["value"]), int)
        self.assertTrue(row["on_key"])
        self.assertFalse(row["changed"])

    def test_a_locked_channel_says_so(self):
        p = self.plug("tx", 1.0)
        self.fake.locked.add(p)
        self.assertTrue(self.main()["tx"]["locked"])

    def test_a_ranged_channel_carries_its_limits(self):
        p = self.plug("fkik", 5.0)
        self.fake.ranges[p] = (0.0, 10.0)
        row = self.main()["fkik"]
        self.assertEqual((row["lo"], row["hi"]), (0.0, 10.0))

    def test_an_unranged_channel_has_none(self):
        self.plug("tx", 1.0)
        row = self.main()["tx"]
        self.assertEqual((row["lo"], row["hi"]), (None, None))

    def test_a_layered_channel_reads_its_keys_but_never_changed(self):
        p = self.plug("tx", 3.0)
        self.fake.sources[p] = ["tx_blend"]
        self.fake.types["tx_blend"] = "animBlendNodeAdditiveDL"
        self.fake.keys[p] = ([5.0, 10.0], [10.0], 99.0)
        row = self.main()["tx"]
        self.assertEqual(row["source"], "layer")
        self.assertEqual(row["keys"], [5.0, 10.0])
        self.assertTrue(row["on_key"])
        self.assertTrue(row["breakdown"])
        self.assertFalse(row["changed"])                       # only a plain curve is compared

    def test_a_driven_channel_reads_no_keys(self):
        p = self.plug("tx", 3.0)
        self.fake.sources[p] = ["expr1"]
        self.fake.types["expr1"] = "expression"
        self.fake.keys[p] = ([10.0], [], 3.0)
        row = self.main()["tx"]
        self.assertEqual(row["source"], "driven")
        self.assertEqual((row["keys"], row["on_key"]), ([], False))

    def test_a_muted_channel_with_no_curve_still_asks_for_keys(self):
        p = self.plug("tx", 3.0)
        self.fake.muted.add(p)
        self.fake.keys[p] = ([10.0], [], 3.0)
        row = self.main()["tx"]
        self.assertIsNone(row["source"])
        self.assertTrue(row["muted"])
        self.assertTrue(row["on_key"])
        self.assertFalse(row["changed"])

    def test_a_mute_node_with_nothing_in_it_reads_as_a_curve(self):
        p = self.plug("tx", 3.0)
        self.fake.sources[p] = ["mute_tx"]
        self.fake.types["mute_tx"] = "mute"
        self.assertEqual(self.main()["tx"]["source"], "curve")

    def test_keys_off_the_frame_are_not_on_key(self):
        p = self.plug("tx", 3.0)
        self.fake.sources[p] = ["tx_curve"]
        self.fake.types["tx_curve"] = "animCurveTL"
        self.fake.keys[p] = ([0.0, 20.0, 0.0], [20.0], 3.0)
        row = self.main()["tx"]
        self.assertEqual(row["keys"], [0.0, 20.0])               # sorted, once each
        self.assertEqual((row["on_key"], row["breakdown"], row["changed"]), (False, False, False))

    def test_a_curve_that_cannot_be_evaluated_is_not_changed(self):
        p = self.plug("tx", 3.0)
        self.fake.sources[p] = ["tx_curve"]
        self.fake.types["tx_curve"] = "animCurveTL"
        self.fake.keys[p] = ([10.0], [], RuntimeError("no eval"))
        self.assertFalse(self.main()["tx"]["changed"])

    def test_a_list_value_reads_its_first_item_and_an_empty_one_zero(self):
        self.plug("a", [7.5])
        self.plug("b", [])
        main = self.main()
        self.assertEqual((main["a"]["value"], main["b"]["value"]), (7.5, 0))

    def test_reads_that_fail_fall_back(self):
        p = self.plug("tx", 1.0)
        self.fake.fail.update(("attributeName", "mute", "listConnections"))
        row = self.main()["tx"]
        self.assertEqual(row["nice"], "tx")                     # the attribute's own name
        self.assertFalse(row["muted"])
        self.assertIsNone(row["source"])
        self.assertEqual(row["plug"], p)

    def test_a_plug_the_box_cannot_show_is_left_out(self):
        self.plug("good", 1.0)
        self.plug("bad", RuntimeError("cannot read"))
        self.assertEqual(list(self.main()), ["good"])

    def test_limits_maya_cannot_read_are_none(self):
        p = self.plug("fkik", 5.0)
        self.fake.ranges[p] = (0.0, 10.0)
        self.fake.fail.add("range")
        row = self.main()["fkik"]
        self.assertEqual((row["lo"], row["hi"]), (None, None))

    def test_another_selected_object_maya_cannot_ask_gets_no_target(self):
        self.plug("tx", 1.0)
        self.fake.sel = ["|other", "|third", "|ctrl"]
        self.fake.attrs.update({"|other": ["tx"], "|third": ["tx"]})
        self.fake.fail.add("exists:|third")
        self.assertEqual(self.main()["tx"]["targets"], ["|other.tx", "|ctrl.tx"])

    def test_a_node_whose_type_cannot_be_read_is_never_cached(self):
        self.plug("tx", 1.0)
        self.fake.fail.add("nodeType")
        self.assertEqual(self.main()["tx"]["kind"], "double")
        self.assertEqual(scene._STATIC, {})

    def test_the_definition_cache_starts_again_past_its_size(self):
        self.plug("tx", 1.0)
        scene._STATIC.update(((("t%d" % i, "a"), ("double", None, None)) for i in range(4001)))
        self.main()
        self.assertEqual(scene._STATIC, {("transform", "tx"): ("double", None, None)})
        self.fake.kinds["|ctrl.tx"] = "doubleLinear"            # read from the cache now
        self.assertEqual(self.main()["tx"]["kind"], "double")

    def test_a_shape_section_s_channel_is_keyed_by_its_plug(self):
        self.plug("tx", 1.0)
        self.fake.attrs["|ctrl|ctrlShape"] = ["lodVisibility"]
        self.fake.values["|ctrl|ctrlShape.lodVisibility"] = 1.0
        rows = scene.channels("|ctrl|ctrlShape")
        self.assertEqual(rows[0]["key"], "|ctrl|ctrlShape.lodVisibility")
        self.assertEqual(rows[0]["targets"], ["|ctrl|ctrlShape.lodVisibility"])


class Objects(Base):

    def test_the_selection_once_each_in_its_order(self):
        self.fake.sel = ["|a", "|b", "|a"]
        self.assertEqual(scene.objects(), ["|a", "|b"])

    def test_now_is_a_float(self):
        self.fake.t = 12
        self.assertIsInstance(scene.now(), float)

    def test_short_takes_the_leaf(self):
        self.assertEqual(scene.short("|grp|ctrl"), "ctrl")

    def test_short_without_scene_tabs_takes_the_leaf_too(self):
        import maya_scenetabs.scope as scope
        with mock.patch.object(scope, "local", mock.Mock(side_effect=RuntimeError("no tabs"))):
            self.assertEqual(scene.short("|grp|tab_x:ctrl"), "tab_x:ctrl")

    def test_nothing_selected_is_an_empty_snapshot(self):
        self.fake.sel = []
        self.assertEqual(scene.snapshot(), {"objects": [], "lead": None, "frame": 10.0, "sections": []})

    def test_visibility_after_the_scales_in_the_snapshot(self):
        for attr in ("visibility", "translateX", "rotateOrder", "scaleX", "blend"):
            self.plug(attr, 1.0)
        self.assertEqual(list(self.main()), ["translateX", "rotateOrder", "scaleX", "visibility", "blend"])


class Sections(Base):

    def setUp(self):
        super(Sections, self).setUp()
        self.plug("tx", 1.0)
        self.fake.box_lists = {}

    def kinds(self, snap):
        return [(s["kind"], s["label"], s["title"]) for s in snap["sections"][1:]]

    def test_with_maya_s_box_hidden_shapes_and_inputs_are_read_ourselves(self):
        self.fake.shapes["|ctrl"] = ["|ctrl|ctrlShape", "|ctrl|ctrlShape2"]
        self.fake.history = {"|ctrl|ctrlShape": ["|ctrl|ctrlShape", "skinCluster1", "tweak1"],
                             "|ctrl|ctrlShape2": ["skinCluster1", "blendShape1"]}
        self.fake.exists = {"|ctrl|ctrlShape", "|ctrl|ctrlShape2", "skinCluster1", "tweak1",
                            "blendShape1"}
        snap = scene.snapshot()
        self.assertEqual(self.kinds(snap), [("shapes", "ctrlShape", "SHAPES"),
                                            ("shapes", "ctrlShape2", ""),
                                            ("inputs", "skinCluster1", "INPUTS"),
                                            ("inputs", "tweak1", ""),
                                            ("inputs", "blendShape1", "")])

    def test_maya_s_own_lists_win_and_nodes_gone_are_left_out(self):
        self.fake.box_lists = {"shapeObjectList": ["|ctrl|S"], "historyObjectList": ["gone"],
                               "outputObjectList": ["out1"]}
        self.fake.shapes["|ctrl"] = ["|ctrl|other"]
        self.fake.exists = {"|ctrl|S", "out1"}
        self.assertEqual(self.kinds(scene.snapshot()), [("shapes", "S", "SHAPES"),
                                                        ("outputs", "out1", "OUTPUTS")])

    def test_no_box_and_reads_that_fail_give_empty_lists(self):
        self.fake.box = False
        self.fake.fail.add("listRelatives")
        self.assertEqual(self.kinds(scene.snapshot()), [])

    def test_a_history_that_fails_gives_no_inputs(self):
        self.fake.shapes["|ctrl"] = ["|ctrl|S"]
        self.fake.exists = {"|ctrl|S"}
        self.fake.fail.add("listHistory")
        self.assertEqual(self.kinds(scene.snapshot()), [("shapes", "S", "SHAPES")])

    def test_a_box_list_query_that_fails_falls_back(self):
        self.fake.fail.add("channelBox")
        self.fake.shapes["|ctrl"] = ["|ctrl|S"]
        self.fake.exists = {"|ctrl|S"}
        self.assertEqual(self.kinds(scene.snapshot()), [("shapes", "S", "SHAPES")])


class Values(Base):

    def test_each_plug_s_value_or_none(self):
        self.fake.values = {"a.x": 1.5, "a.y": [2.0], "a.z": [], "a.v": True,
                            "a.bad": RuntimeError("gone")}
        self.assertEqual(scene.values(["a.x", "a.y", "a.z", "a.v", "a.bad", "a.missing"]),
                         [1.5, 2.0, 0, 1, None, None])


class Writes(Base):

    def setUp(self):
        super(Writes, self).setUp()
        self.fake.values = {"a.x": 0.0, "a.y": 0.0, "a.z": 0.0}

    def test_write_passes_locked_plugs_by_and_counts(self):
        self.fake.locked = {"a.y"}
        self.assertEqual(scene.write([("a.x", 1.0), ("a.y", 2.0), ("a.z", 3.0)]), 2)
        self.assertEqual([c[:3] for c in self.fake.calls],
                         [("setAttr", "a.x", (1.0,)), ("setAttr", "a.z", (3.0,))])

    def test_write_skips_a_plug_that_refuses(self):
        self.fake.fail.add("setAttr")
        self.assertEqual(scene.write([("a.x", 1.0)]), 0)

    def test_key_sets_a_key_or_a_breakdown_on_every_open_plug(self):
        self.fake.locked = {"a.z"}
        self.assertEqual(scene.key(["a.x", "a.z"], breakdown=1), 1)
        self.assertEqual(self.fake.calls, [("setKeyframe", "a.x", {"breakdown": True})])
        self.fake.calls[:] = []
        self.assertEqual(scene.key(["a.y"]), 1)
        self.assertEqual(self.fake.calls, [("setKeyframe", "a.y", {"breakdown": False})])

    def test_key_counts_nothing_when_maya_refuses(self):
        self.fake.fail.add("setKeyframe")
        self.assertEqual(scene.key(["a.x"]), 0)

    def test_unkey_cuts_the_frame_and_sums_what_went(self):
        self.fake.cut = {"a.x": 1, "a.y": None}
        self.assertEqual(scene.unkey(["a.x", "a.y"], 7.0), 1)
        self.assertEqual(self.fake.calls[0], ("cutKey", "a.x", {"time": (7.0, 7.0), "clear": True}))
        self.fake.fail.add("cutKey")
        self.assertEqual(scene.unkey(["a.x"], 7.0), 0)

    def test_mute_on_and_off(self):
        scene.mute(["a.x", "a.y"], True)
        scene.mute(["a.x"], False)
        self.assertEqual(self.fake.calls, [("mute", "a.x", False, False), ("mute", "a.y", False, False),
                                           ("mute", "a.x", True, True)])
        self.fake.fail.add("mute")
        scene.mute(["a.x"], True)                               # swallowed

    def test_lock_writes_the_lock_flag(self):
        scene.lock(["a.x"], 1)
        scene.lock(["a.y"], 0)
        self.assertEqual(self.fake.calls, [("setAttr", "a.x", (), {"lock": True}),
                                           ("setAttr", "a.y", (), {"lock": False})])
        self.fake.fail.add("setAttr")
        scene.lock(["a.x"], True)                               # swallowed


class Connections(Base):

    def test_select_connection_selects_each_input_node_once(self):
        self.fake.source_plugs = {"a.x": ["c1.output"], "a.y": ["c1.output", "c2.o"]}
        self.assertEqual(scene.select_connection(["a.x", "a.y", "a.z"]), ["c1", "c2"])
        self.assertEqual(self.fake.calls, [("select", ["c1", "c2"], {"replace": True})])

    def test_select_connection_with_nothing_connected_selects_nothing(self):
        self.fake.fail.add("listConnections")
        self.assertEqual(scene.select_connection(["a.x"]), [])
        self.assertEqual(self.fake.calls, [])

    def test_break_connections_cuts_and_deletes_an_orphaned_curve_only(self):
        self.fake.source_plugs = {"a.x": ["curveA.output"], "a.y": ["curveB.output"],
                                  "a.z": ["expr1.out"]}
        self.fake.types = {"curveA": "animCurveTL", "curveB": "animCurveTA", "expr1": "expression"}
        self.fake.downstream = {"curveB": ["other.rotateX"]}
        self.assertEqual(scene.break_connections(["a.x", "a.y", "a.z"]), 3)
        self.assertIn(("delete", "curveA"), self.fake.calls)
        self.assertNotIn(("delete", "curveB"), self.fake.calls)     # still feeds another plug
        self.assertNotIn(("delete", "expr1"), self.fake.calls)      # not a curve
        self.assertEqual([c for c in self.fake.calls if c[0] == "disconnectAttr"],
                         [("disconnectAttr", "curveA.output", "a.x"),
                          ("disconnectAttr", "curveB.output", "a.y"),
                          ("disconnectAttr", "expr1.out", "a.z")])

    def test_break_connections_goes_on_past_a_refusal(self):
        self.fake.source_plugs = {"a.x": ["c1.o"], "a.y": ["c2.o"]}
        self.fake.types = {"c1": "expression", "c2": "expression"}
        self.fake.fail.add(("disconnect", "c1.o"))
        self.assertEqual(scene.break_connections(["a.x", "a.y"]), 1)

    def test_break_connections_with_nothing_readable(self):
        self.fake.fail.add("listConnections")
        self.assertEqual(scene.break_connections(["a.x"]), 0)


class TheBox(Base):

    def test_sync_selection_clears_with_nothing_and_answers_false_without_a_box(self):
        self.assertTrue(scene.sync_selection([]))
        self.assertEqual(self.fake.calls[-1][1]["select"], "")
        self.fake.fail.add("channelBox")
        self.assertFalse(scene.sync_selection(["a.x"]))
        self.fake.box = False
        self.assertFalse(scene.sync_selection(["a.x"]))

    def test_a_box_maya_cannot_ask_about_is_no_box(self):
        self.fake.fail.add("box")
        self.assertFalse(scene._box_exists())
        self.assertEqual(scene._box_list("shapeObjectList"), [])
        self.assertFalse(scene.sync_selection(["a.x"]))

    def test_speed_reads_maya_s_box_else_one(self):
        self.fake.box_lists = {"speed_value": 0.1}
        self.assertEqual(scene.speed(), 0.1)
        self.fake.box_lists = {"speed_value": None}
        self.assertEqual(scene.speed(), 1.0)
        self.fake.box = False
        self.assertEqual(scene.speed(), 1.0)
        self.fake.box = True
        self.fake.fail.add("channelBox")
        self.assertEqual(scene.speed(), 1.0)

    def test_set_speed_writes_a_float_and_swallows_a_refusal(self):
        scene.set_speed("10")
        self.assertEqual(self.fake.calls, [("channelBox", {"edit": True, "speed": 10.0})])
        self.fake.fail.add("channelBox")
        scene.set_speed(1)

    def test_precision_reads_maya_s_box_else_three(self):
        self.fake.box_lists = {"precision_value": 5}
        self.assertEqual(scene.precision(), 5)
        self.fake.box_lists = {}
        self.assertEqual(scene.precision(), 3)
        self.fake.box = False
        self.assertEqual(scene.precision(), 3)
        self.fake.box = True
        self.fake.fail.add("channelBox")
        self.assertEqual(scene.precision(), 3)

    def test_undo_chunks(self):
        scene.chunk_open("skeldarChannelDrag")
        scene.chunk_close()
        self.assertEqual(self.fake.calls, [("undoInfo", {"openChunk": True, "chunkName": "skeldarChannelDrag"}),
                                           ("undoInfo", {"closeChunk": True})])


class Layers(unittest.TestCase):
    """The layer chip's road: the Time Bar's scene, never fatal."""

    def setUp(self):
        from maya_timebar import scene as bar_scene
        self.bar = bar_scene
        self.saved = (bar_scene.layers, bar_scene.layer_label, bar_scene.pick_layer)
        self.picked = []

    def tearDown(self):
        self.bar.layers, self.bar.layer_label, self.bar.pick_layer = self.saved

    def test_it_asks_the_time_bar(self):
        self.bar.layers = lambda: ["BaseAnimation", "Layer1"]
        self.bar.layer_label = lambda: "Layer1"
        self.bar.pick_layer = self.picked.append
        self.assertEqual(scene.layers(), ["BaseAnimation", "Layer1"])
        self.assertEqual(scene.layer_label(), "Layer1")
        scene.pick_layer("Layer1")
        self.assertEqual(self.picked, ["Layer1"])

    def test_a_time_bar_that_fails_gives_nothing(self):
        def boom():
            raise RuntimeError("no layers")
        self.bar.layers = boom
        self.bar.layer_label = boom
        self.assertEqual(scene.layers(), [])
        self.assertEqual(scene.layer_label(), "")


class ShowMayaBox(unittest.TestCase):

    def test_the_menu_row_turns_ours_off(self):
        import maya_channelbox
        saved = maya_channelbox.set_enabled
        asked = []
        maya_channelbox.set_enabled = lambda on: asked.append(on) or "off"
        try:
            self.assertEqual(scene.show_maya_box(), "off")
        finally:
            maya_channelbox.set_enabled = saved
        self.assertEqual(asked, [False])


if __name__ == "__main__":
    unittest.main()
