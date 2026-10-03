"""The pose library's keys: the active animation layer, writable plugs, preview, final-value keys.

The animator: «Поза должна накладываться на текущий активный анимационный слой». The rule
(spec 2026-10-02-pose-library-design.md, "Keys - the active layer"): the selected non-base layer,
the topmost when several, else BaseAnimation; no layers at all means plain keys; a locked layer is
refused; a plug is added to a non-base layer before it is keyed; every value is the FINAL one
(`setKeyframe(..., value=v, animLayer=L)` writes `v - base` on an additive layer by itself).

The pure halves (`pick_layer`, `input_kind`, `quaternion_note`) are tested on plain data; the scene
halves run on a fake `cmds` rebound as the module attribute (CLAUDE.md's rule) and restored in
`tearDown`. The real Maya behaviour they stand on was measured in mayapy: a constrained plug takes a
`setAttr` WITHOUT an error (so `preview` must ask `writable`), a key refused by a layer returns 0,
re-adding a plug to its layer is a no-op, `animLayer -q -children` lists bottom to top. A
connection into a channel's COMPOUND parent (`decomposeMatrix.outputRotate -> joint.rotate`) is
invisible to `listConnections` on the leaf (None) while `getAttr(settable=True)` is False and
`connectionInfo` names the source - and a double3 into an angle compound has a `unitConversion`
in the path, which `connectionInfo` names instead of the real driver.
"""

import unittest

from maya_poselib import keys


def layer(name, order, base=False, selected=False, locked=False, override=False,
          quaternion=False):
    """One layer record as `active_layer` hands them to `pick_layer`."""
    return {"name": name, "base": base, "selected": selected, "locked": locked,
            "override": override, "quaternion": quaternion, "order": order}


class PickLayer(unittest.TestCase):

    def test_no_layers_means_plain_keys(self):
        self.assertEqual(keys.pick_layer([]), (None, ""))

    def test_the_base_alone_is_the_base(self):
        picked, refusal = keys.pick_layer([layer("BaseAnimation", 0, base=True, override=True)])
        self.assertEqual(refusal, "")
        self.assertEqual(picked, keys.Layer("BaseAnimation", True, False, False, False))

    def test_nothing_selected_is_the_base(self):
        picked, refusal = keys.pick_layer([
            layer("BaseAnimation", 0, base=True, override=True),
            layer("A", 1), layer("B", 2, override=True)])
        self.assertEqual(refusal, "")
        self.assertEqual(picked.name, "BaseAnimation")
        self.assertTrue(picked.base)

    def test_one_selected_layer_is_it(self):
        picked, refusal = keys.pick_layer([
            layer("BaseAnimation", 0, base=True, override=True),
            layer("A", 1), layer("B", 2, selected=True)])
        self.assertEqual((picked.name, refusal), ("B", ""))
        self.assertFalse(picked.base)

    def test_two_selected_layers_the_higher_order_wins(self):
        # the list order is not the stack order: the walk's index is
        picked, _ = keys.pick_layer([
            layer("BaseAnimation", 0, base=True, override=True),
            layer("Top", 3, selected=True), layer("Low", 1, selected=True),
            layer("Mid", 2)])
        self.assertEqual(picked.name, "Top")

    def test_the_base_selected_while_another_is_not_is_the_base(self):
        picked, _ = keys.pick_layer([
            layer("BaseAnimation", 0, base=True, override=True, selected=True),
            layer("A", 1)])
        self.assertEqual(picked.name, "BaseAnimation")

    def test_the_base_and_a_layer_selected_the_layer_wins(self):
        picked, _ = keys.pick_layer([
            layer("BaseAnimation", 0, base=True, override=True, selected=True),
            layer("A", 1, selected=True)])
        self.assertEqual(picked.name, "A")

    def test_additive_means_not_override_and_not_the_base(self):
        add, _ = keys.pick_layer([layer("BaseAnimation", 0, base=True, override=True),
                                  layer("Add", 1, selected=True, override=False)])
        over, _ = keys.pick_layer([layer("BaseAnimation", 0, base=True, override=True),
                                   layer("Over", 1, selected=True, override=True)])
        self.assertTrue(add.additive)
        self.assertFalse(over.additive)

    def test_a_locked_chosen_layer_is_refused_by_name(self):
        picked, refusal = keys.pick_layer([
            layer("BaseAnimation", 0, base=True, override=True),
            layer("Poses", 1, selected=True, locked=True)])
        self.assertIsNone(picked)
        self.assertEqual(refusal,
                         "the animation layer Poses is locked - unlock it or pick another")

    def test_a_locked_base_is_refused_too(self):
        picked, refusal = keys.pick_layer([
            layer("BaseAnimation", 0, base=True, override=True, locked=True), layer("A", 1)])
        self.assertIsNone(picked)
        self.assertIn("BaseAnimation", refusal)

    def test_a_locked_layer_that_is_not_chosen_is_no_problem(self):
        picked, refusal = keys.pick_layer([
            layer("BaseAnimation", 0, base=True, override=True),
            layer("Locked", 1, locked=True), layer("Open", 2, selected=True)])
        self.assertEqual((picked.name, refusal), ("Open", ""))

    def test_the_accumulation_mode_is_carried(self):
        picked, _ = keys.pick_layer([layer("BaseAnimation", 0, base=True, override=True),
                                     layer("Q", 1, selected=True, quaternion=True)])
        self.assertTrue(picked.quaternion)

    def test_no_base_in_the_list_falls_back_to_the_lowest_layer(self):
        # Maya always has a root; a record list without one must not crash the press
        picked, refusal = keys.pick_layer([layer("Upper", 2), layer("Lower", 1)])
        self.assertEqual((picked.name, refusal), ("Lower", ""))


class InputKind(unittest.TestCase):

    def test_nothing_connected_is_free(self):
        self.assertEqual(keys.input_kind(None), "free")

    def test_time_curves_are_curves(self):
        for kind in ("animCurveTL", "animCurveTA", "animCurveTU", "animCurveTT"):
            self.assertEqual(keys.input_kind(kind), "curve", kind)

    def test_driven_key_curves_are_driven(self):
        # animCurveU*: the x axis is a driver's VALUE, not time (CLAUDE.md, hotkeys section)
        for kind in ("animCurveUL", "animCurveUA", "animCurveUU", "animCurveUT"):
            self.assertEqual(keys.input_kind(kind), "driven", kind)

    def test_layer_blend_nodes_are_layers(self):
        for kind in ("animBlendNodeAdditiveDL", "animBlendNodeAdditiveDA",
                     "animBlendNodeAdditiveRotation", "animBlendNodeBase",
                     "animBlendNodeAdditive"):
            self.assertEqual(keys.input_kind(kind), "layer", kind)

    def test_everything_else_is_driven(self):
        for kind in ("parentConstraint", "orientConstraint", "pairBlend", "expression",
                     "multiplyDivide", "decomposeMatrix", "addDL"):
            self.assertEqual(keys.input_kind(kind), "driven", kind)


class PlugCmds(object):
    """A fake cmds that knows which plugs are locked, what feeds them, and what they read.

    `inputs` is what `listConnections` sees: plug -> (node, type), a connection INTO the plug
    itself. `compound` is what only `connectionInfo` sees: plug -> the source plug of a connection
    into its COMPOUND parent ("dm1.outputRotate" -> joint.rotate), where Maya's `listConnections`
    on the leaf answers None. `types` names the type of any node that is not in `inputs`; `behind`
    is what feeds a node's `.input` (a unitConversion Maya put in the path).
    """

    def __init__(self, locked=(), inputs=None, values=None, missing=(), compound=None,
                 types=None, behind=None):
        self.locked = set(locked)
        self.inputs = dict(inputs or {})          # plug -> (node, type)
        self.compound = dict(compound or {})      # plug -> source plug (the parent's connection)
        self.types = dict(types or {})            # node -> type
        self.behind = dict(behind or {})          # node -> the node feeding its .input
        self.values = dict(values or {})
        self.missing = set(missing)
        self.sets = []
        self.listed = []
        self.infos = []

    def getAttr(self, plug, **kw):
        if plug in self.missing:
            raise ValueError("No object matches name: " + plug)
        if kw.get("lock"):
            return plug in self.locked
        return self.values[plug]

    def listConnections(self, plug, **kw):
        self.listed.append((plug, kw))
        node = plug.split(".")[0]
        if plug.endswith(".input") and node in self.behind:
            return [self.behind[node]]
        entry = self.inputs.get(plug)
        return [entry[0]] if entry else None

    def connectionInfo(self, plug, **kw):
        self.infos.append((plug, kw))
        if kw.get("isDestination"):
            return plug in self.compound
        if kw.get("sourceFromDestination"):
            return self.compound.get(plug, "")
        raise AssertionError(kw)

    def objectType(self, node):
        if node in self.types:
            return self.types[node]
        for found, kind in self.inputs.values():
            if found == node:
                return kind
        raise AssertionError(node)

    def setAttr(self, plug, value):
        self.sets.append((plug, value))


class Restoring(unittest.TestCase):
    """Rebind `keys.cmds` for a test and put the real one back."""

    def setUp(self):
        self._cmds = keys.cmds

    def tearDown(self):
        keys.cmds = self._cmds


class Writable(Restoring):

    def test_a_free_plug_is_writable(self):
        keys.cmds = PlugCmds()
        self.assertEqual(keys.writable("a.tx"), (True, ""))

    def test_a_keyed_plug_is_writable(self):
        keys.cmds = PlugCmds(inputs={"a.tx": ("a_translateX", "animCurveTL")})
        self.assertEqual(keys.writable("a.tx"), (True, ""))

    def test_a_layered_plug_is_writable(self):
        keys.cmds = PlugCmds(inputs={"a.tx": ("a_tx_AddL", "animBlendNodeAdditiveDL")})
        self.assertEqual(keys.writable("a.tx"), (True, ""))

    def test_a_locked_plug_is_locked(self):
        keys.cmds = PlugCmds(locked=["a.tx"])
        self.assertEqual(keys.writable("a.tx"), (False, "locked"))

    def test_a_constrained_plug_names_its_driver(self):
        keys.cmds = PlugCmds(inputs={"a.tx": ("a_parentConstraint1", "parentConstraint")})
        self.assertEqual(keys.writable("a.tx"), (False, "driven by a_parentConstraint1"))

    def test_a_driven_key_plug_is_driven(self):
        keys.cmds = PlugCmds(inputs={"a.tx": ("sdk_curve", "animCurveUL")})
        ok, reason = keys.writable("a.tx")
        self.assertFalse(ok)
        self.assertEqual(reason, "driven by sdk_curve")

    def test_locked_wins_over_driven(self):
        keys.cmds = PlugCmds(locked=["a.tx"],
                             inputs={"a.tx": ("c", "parentConstraint")})
        self.assertEqual(keys.writable("a.tx"), (False, "locked"))

    def test_a_missing_plug_is_not_writable_and_does_not_raise(self):
        keys.cmds = PlugCmds(missing=["gone.tx"])
        self.assertEqual(keys.writable("gone.tx"), (False, "missing"))

    def test_unit_conversion_nodes_are_looked_through(self):
        fake = PlugCmds()
        keys.cmds = fake
        keys.writable("a.rx")
        (plug, kw), = fake.listed
        self.assertTrue(kw.get("skipConversionNodes"))
        self.assertTrue(kw.get("source"))
        self.assertFalse(kw.get("destination"))

    # -- a connection into the COMPOUND parent (decomposeMatrix.outputRotate -> joint.rotate):
    # -- measured in mayapy 2027, listConnections on the leaf answers None, getAttr(settable) is
    # -- False, and only connectionInfo knows - the silent "pose that did not land"

    def test_a_plug_driven_through_its_compound_parent_is_driven(self):
        keys.cmds = PlugCmds(compound={"j.rotateX": "dm1.outputRotate"},
                             types={"dm1": "decomposeMatrix"})
        self.assertEqual(keys.writable("j.rotateX"), (False, "driven by dm1"))

    def test_translate_hookups_are_driven_too(self):
        # plusMinusAverage.output3D, a motion path's position, decomposeMatrix.outputTranslate
        keys.cmds = PlugCmds(compound={"j.translateY": "pma1.output3D"},
                             types={"pma1": "plusMinusAverage"})
        self.assertEqual(keys.writable("j.translateY"), (False, "driven by pma1"))

    def test_the_compound_driver_is_read_with_connectioninfo(self):
        fake = PlugCmds(compound={"j.rotateX": "dm1.outputRotate"},
                        types={"dm1": "decomposeMatrix"})
        keys.cmds = fake
        keys.writable("j.rotateX")
        self.assertIn(("j.rotateX", {"isDestination": True}), fake.infos)
        self.assertIn(("j.rotateX", {"sourceFromDestination": True}), fake.infos)

    def test_a_unit_conversion_in_a_compound_path_is_looked_through(self):
        # a double3 into an angle compound: Maya puts unitConversion1 in between, and
        # connectionInfo names IT; the animator wants the real driver
        keys.cmds = PlugCmds(compound={"j.rotateX": "unitConversion1.output"},
                             types={"unitConversion1": "unitConversion", "pma1": "plusMinusAverage"},
                             behind={"unitConversion1": "pma1"})
        self.assertEqual(keys.writable("j.rotateX"), (False, "driven by pma1"))

    def test_a_unit_conversion_with_nothing_behind_it_is_still_driven(self):
        keys.cmds = PlugCmds(compound={"j.rotateX": "unitConversion1.output"},
                             types={"unitConversion1": "unitConversion"})
        self.assertEqual(keys.writable("j.rotateX"), (False, "driven by unitConversion1"))

    def test_a_compound_source_that_is_a_curve_or_a_layer_is_still_writable(self):
        # the same classification as a leaf's own source: input_kind decides, not "connected"
        for node, kind in (("crv", "animCurveTA"), ("lay", "animBlendNodeAdditiveRotation")):
            keys.cmds = PlugCmds(compound={"j.rotateX": node + ".output"}, types={node: kind})
            self.assertEqual(keys.writable("j.rotateX"), (True, ""), kind)

    def test_locked_wins_over_a_compound_driver(self):
        keys.cmds = PlugCmds(locked=["j.rotateX"], compound={"j.rotateX": "dm1.outputRotate"},
                             types={"dm1": "decomposeMatrix"})
        self.assertEqual(keys.writable("j.rotateX"), (False, "locked"))

    def test_a_free_plug_with_no_compound_driver_is_still_writable(self):
        fake = PlugCmds()
        keys.cmds = fake
        self.assertEqual(keys.writable("j.rotateX"), (True, ""))
        self.assertEqual(fake.infos, [("j.rotateX", {"isDestination": True})])

    def test_a_plug_with_its_own_connection_never_asks_connectioninfo(self):
        # the common rig case (a keyed control) must not pay a second query
        fake = PlugCmds(inputs={"a.tx": ("a_translateX", "animCurveTL"),
                                "a.ty": ("c", "parentConstraint")},
                        values={})
        keys.cmds = fake
        keys.writable("a.tx")
        keys.writable("a.ty")
        self.assertEqual(fake.infos, [])

    def test_a_missing_plug_still_says_missing_when_connectioninfo_raises(self):
        class Gone(PlugCmds):
            def connectionInfo(self, plug, **kw):
                raise RuntimeError("Error: line 0: No object matches name: " + plug)
        keys.cmds = Gone()
        self.assertEqual(keys.writable("gone.tx"), (False, "missing"))


class InputOf(Restoring):
    """What feeds a plug - a Blend cancelled after the time moved sets back the FREE channels
    only and evaluates the rest at the frame shown."""

    def test_nothing_connected_is_free(self):
        keys.cmds = PlugCmds()
        self.assertEqual(keys.input_of("a.tx"), "free")

    def test_a_time_curve_a_layer_and_a_constraint(self):
        keys.cmds = PlugCmds(inputs={"a.tx": ("a_tx", "animCurveTL"),
                                     "a.rx": ("blend1", "animBlendNodeAdditiveRotation"),
                                     "a.ty": ("c1", "parentConstraint")})
        self.assertEqual(keys.input_of("a.tx"), "curve")
        self.assertEqual(keys.input_of("a.rx"), "layer")
        self.assertEqual(keys.input_of("a.ty"), "driven")

    def test_a_feed_through_the_compound_parent_is_seen(self):
        keys.cmds = PlugCmds(compound={"a.rx": "dm1.outputRotate"},
                             types={"dm1": "decomposeMatrix"})
        self.assertEqual(keys.input_of("a.rx"), "driven")

    def test_a_locked_keyed_plug_is_still_a_curve(self):
        # a lock is no feed: the channel shows its curve at the frame either way
        keys.cmds = PlugCmds(locked=["a.tx"], inputs={"a.tx": ("a_tx", "animCurveTL")})
        self.assertEqual(keys.input_of("a.tx"), "curve")

    def test_a_missing_plug_is_missing(self):
        class Gone(PlugCmds):
            def listConnections(self, plug, **kw):
                raise ValueError("No object matches name: " + plug)
        keys.cmds = Gone()
        self.assertEqual(keys.input_of("gone.tx"), "missing")
        self.assertEqual(keys.feed_of("gone.tx"), ("missing", None))

    def test_feed_of_names_the_node_a_blend_dirties(self):
        # a Blend cancelled after the time moved dirties the node feeding a keyed or layered
        # channel - a static channel in a layer is not time-dependent (fix round 1)
        keys.cmds = PlugCmds(inputs={"a.tx": ("a_tx", "animCurveTL"),
                                     "a.rx": ("blend1", "animBlendNodeAdditiveRotation"),
                                     "a.ty": ("c1", "parentConstraint")})
        self.assertEqual(keys.feed_of("a.tx"), ("curve", "a_tx"))
        self.assertEqual(keys.feed_of("a.rx"), ("layer", "blend1"))
        self.assertEqual(keys.feed_of("a.ty"), ("driven", "c1"))
        self.assertEqual(keys.feed_of("a.tz"), ("free", None))

    def test_feed_of_through_the_compound_parent(self):
        # a layered rotate is fed through `rotate`, not `rotateX`
        keys.cmds = PlugCmds(compound={"a.rx": "blend2.output"},
                             types={"blend2": "animBlendNodeAdditiveRotation"})
        self.assertEqual(keys.feed_of("a.rx"), ("layer", "blend2"))


class CurrentAndPreview(Restoring):

    def test_current_reads_floats(self):
        keys.cmds = PlugCmds(values={"a.tx": 3, "a.visibility": True, "a.ry": 12.5})
        got = keys.current(["a.tx", "a.visibility", "a.ry"])
        self.assertEqual(got, {"a.tx": 3.0, "a.visibility": 1.0, "a.ry": 12.5})
        self.assertTrue(all(isinstance(v, float) for v in got.values()))

    def test_preview_sets_the_writable_ones(self):
        fake = PlugCmds()
        keys.cmds = fake
        keys.preview({"a.tx": 1.0, "a.ty": 2.0})
        self.assertEqual(sorted(fake.sets), [("a.tx", 1.0), ("a.ty", 2.0)])

    def test_preview_skips_locked_and_driven_silently(self):
        # a constrained plug takes setAttr without an error in Maya, so writable() is the guard
        fake = PlugCmds(locked=["a.tx"], inputs={"a.ty": ("c", "parentConstraint")})
        keys.cmds = fake
        self.assertIsNone(keys.preview({"a.tx": 1.0, "a.ty": 2.0, "a.tz": 3.0}))
        self.assertEqual(fake.sets, [("a.tz", 3.0)])

    def test_preview_skips_a_plug_driven_through_its_compound_parent(self):
        # Maya's setAttr takes it without an error and the next evaluation overwrites it
        fake = PlugCmds(compound={"a.rx": "dm1.outputRotate"}, types={"dm1": "decomposeMatrix"})
        keys.cmds = fake
        keys.preview({"a.rx": 5.0, "a.ty": 3.0})
        self.assertEqual(fake.sets, [("a.ty", 3.0)])

    def test_preview_survives_a_setattr_that_raises(self):
        class Refusing(PlugCmds):
            def setAttr(self, plug, value):
                if plug == "a.tx":
                    raise RuntimeError("setAttr: locked or connected")
                PlugCmds.setAttr(self, plug, value)
        fake = Refusing()
        keys.cmds = fake
        keys.preview({"a.tx": 1.0, "a.ty": 2.0})
        self.assertEqual(fake.sets, [("a.ty", 2.0)])


class FakeCmds(object):
    def __init__(self):
        self.calls = []
        self.layer_attrs = {"AddL": set()}

    def animLayer(self, name=None, **kw):
        if kw.get("edit") and "attribute" in kw:
            self.layer_attrs[name].add(kw["attribute"])
            self.calls.append(("add", name, kw["attribute"]))
            return None
        if kw.get("query") and kw.get("attribute"):
            return sorted(self.layer_attrs.get(name, ()))
        raise AssertionError(kw)

    def setKeyframe(self, plug, **kw):
        self.calls.append(("key", plug, kw.get("time"), kw.get("value"), kw.get("animLayer")))
        return 1

    def getAttr(self, plug, **kw):
        return False                       # never locked in this fake

    def listConnections(self, plug, **kw):
        return None

    def connectionInfo(self, plug, **kw):
        return False                       # no compound-parent connection in this fake


class Write(Restoring):

    def test_adds_then_keys_final_values_on_the_layer(self):
        fake = FakeCmds()
        keys.cmds = fake
        layer = keys.Layer("AddL", False, True, False, False)
        count, notes = keys.write({"a:FKShoulder_L.rotateX": 12.0}, 5.0, layer)
        self.assertEqual(count, 1)
        self.assertIn(("add", "AddL", "a:FKShoulder_L.rotateX"), fake.calls)
        self.assertIn(("key", "a:FKShoulder_L.rotateX", 5.0, 12.0, "AddL"), fake.calls)

    def test_no_layers_no_flag(self):
        fake = FakeCmds()
        keys.cmds = fake
        keys.write({"j.rotateX": 1.0}, 3.0, None)
        self.assertIn(("key", "j.rotateX", 3.0, 1.0, None), fake.calls)

    def test_the_plug_is_added_before_it_is_keyed(self):
        fake = FakeCmds()
        keys.cmds = fake
        keys.write({"j.rotateX": 1.0}, 3.0, keys.Layer("AddL", False, True, False, False))
        self.assertEqual([c[0] for c in fake.calls], ["add", "key"])

    def test_the_base_layer_is_keyed_but_never_added_to(self):
        fake = FakeCmds()
        keys.cmds = fake
        count, _ = keys.write({"j.rotateX": 1.0}, 3.0,
                              keys.Layer("BaseAnimation", True, False, False, False))
        self.assertEqual(count, 1)
        self.assertEqual([c for c in fake.calls if c[0] == "add"], [])
        self.assertIn(("key", "j.rotateX", 3.0, 1.0, "BaseAnimation"), fake.calls)

    def test_no_layer_never_touches_animlayer(self):
        class NoLayerCmds(FakeCmds):
            def animLayer(self, name=None, **kw):
                raise AssertionError("animLayer must not be called without a layer")
        keys.cmds = NoLayerCmds()
        count, notes = keys.write({"j.tx": 2.0, "j.ty": 3.0}, 1.0, None)
        self.assertEqual((count, notes), (2, []))

    def test_every_plug_is_keyed_and_counted(self):
        fake = FakeCmds()
        keys.cmds = fake
        values = {"a.tx": 1.0, "a.ty": 2.0, "a.tz": 3.0}
        count, notes = keys.write(values, 7.0, keys.Layer("AddL", False, True, False, False))
        self.assertEqual((count, notes), (3, []))
        keyed = {c[1]: c[3] for c in fake.calls if c[0] == "key"}
        self.assertEqual(keyed, values)

    def test_nothing_to_write(self):
        keys.cmds = FakeCmds()
        self.assertEqual(keys.write({}, 1.0, None), (0, []))
        self.assertEqual(keys.write({}, 1.0, None).plugs, [])

    def test_the_answer_is_the_pair_it_was_and_names_the_plugs_keyed(self):
        # a status line counts what was KEYED (the review of task 7): the pair unpacks and
        # compares as ever, `plugs` holds the plugs that took a key, in their order
        class Locked(FakeCmds):
            def getAttr(self, plug, **kw):
                return plug == "a.ty"
        keys.cmds = Locked()
        written = keys.write({"b.tx": 1.0, "a.ty": 2.0, "a.tz": 3.0}, 1.0, None)
        count, notes = written
        self.assertEqual((count, len(notes)), (2, 1))
        self.assertEqual(written, (2, notes))
        self.assertEqual((written.count, written.notes), (2, notes))
        self.assertEqual(written.plugs, ["b.tx", "a.tz"])

    def test_a_key_the_layer_refused_is_not_among_the_plugs(self):
        class Refusing(FakeCmds):
            def setKeyframe(self, plug, **kw):
                FakeCmds.setKeyframe(self, plug, **kw)
                return 0 if plug == "a.ty" else 1
        keys.cmds = Refusing()
        written = keys.write({"a.tx": 1.0, "a.ty": 2.0}, 1.0,
                             keys.Layer("AddL", False, True, False, False))
        self.assertEqual(written.plugs, ["a.tx"])

    def test_a_locked_plug_is_skipped_and_named(self):
        class Locked(FakeCmds):
            def getAttr(self, plug, **kw):
                return plug == "a.tz"
        fake = Locked()
        keys.cmds = fake
        count, notes = keys.write({"a.tx": 1.0, "a.tz": 3.0}, 1.0, None)
        self.assertEqual(count, 1)
        self.assertEqual(len(notes), 1)
        self.assertIn("a.tz", notes[0])
        self.assertIn("locked", notes[0])
        self.assertNotIn("a.tx", notes[0])
        self.assertEqual([c[1] for c in fake.calls if c[0] == "key"], ["a.tx"])

    def test_a_plug_driven_through_its_compound_parent_is_skipped_and_named(self):
        # the animator's own object: decomposeMatrix.outputRotate -> joint.rotate. Maya takes a
        # key on rotateX and the next evaluation overwrites it - the pose "did not land" with no
        # word, unless write refuses it here (measured: write returned (2, []) before this)
        class Compound(FakeCmds):
            def connectionInfo(self, plug, **kw):
                driven = {"jA.rotateX": "dm1.outputRotate",
                          "jA.translateY": "dm1.outputTranslate"}
                if kw.get("isDestination"):
                    return plug in driven
                return driven.get(plug, "")

            def objectType(self, node):
                assert node == "dm1", node
                return "decomposeMatrix"
        fake = Compound()
        keys.cmds = fake
        count, notes = keys.write({"jA.rotateX": 5.0, "jA.translateY": 3.0, "jA.scaleZ": 2.0},
                                  2.0, None)
        self.assertEqual(count, 1)
        self.assertEqual([c[1] for c in fake.calls if c[0] == "key"], ["jA.scaleZ"])
        self.assertEqual(len(notes), 1)                       # one decomposeMatrix, one line
        self.assertIn("driven by dm1", notes[0])
        self.assertIn("jA.rotateX", notes[0])
        self.assertIn("jA.translateY", notes[0])
        self.assertNotIn("jA.scaleZ", notes[0])

    def test_a_compound_driven_plug_is_not_added_to_the_layer(self):
        class Compound(FakeCmds):
            def connectionInfo(self, plug, **kw):
                return True if kw.get("isDestination") else "dm1.outputRotate"

            def objectType(self, node):
                return "decomposeMatrix"
        fake = Compound()
        keys.cmds = fake
        count, notes = keys.write({"jA.rotateX": 5.0}, 2.0,
                                  keys.Layer("AddL", False, True, False, False))
        self.assertEqual((count, fake.calls), (0, []))
        self.assertEqual(len(notes), 1)

    def test_skipped_plugs_are_grouped_by_reason(self):
        class Mixed(FakeCmds):
            def getAttr(self, plug, **kw):
                return plug in ("l1.tx", "l2.tx")

            def listConnections(self, plug, **kw):
                return {"c1.tx": ["con1"], "c1.ty": ["con1"], "c2.tx": ["con2"]}.get(plug)

            def objectType(self, node):
                return "parentConstraint"
        keys.cmds = Mixed()
        count, notes = keys.write({"l1.tx": 0.0, "l2.tx": 0.0, "c1.tx": 0.0, "c1.ty": 0.0,
                                   "c2.tx": 0.0, "ok.tx": 5.0}, 1.0, None)
        self.assertEqual(count, 1)
        self.assertEqual(len(notes), 3)                       # locked / driven by con1 / by con2
        locked = [n for n in notes if "locked" in n]
        self.assertEqual(len(locked), 1)
        self.assertIn("l1.tx", locked[0])
        self.assertIn("l2.tx", locked[0])
        con1 = [n for n in notes if "con1" in n]
        self.assertEqual(len(con1), 1)
        self.assertIn("c1.tx", con1[0])
        self.assertIn("c1.ty", con1[0])
        self.assertTrue(any("con2" in n and "c2.tx" in n for n in notes))

    def test_a_long_group_is_cut_with_a_count(self):
        class AllLocked(FakeCmds):
            def getAttr(self, plug, **kw):
                return True
        keys.cmds = AllLocked()
        plugs = {"j%d.tx" % i: 0.0 for i in range(12)}
        count, notes = keys.write(plugs, 1.0, None)
        self.assertEqual(count, 0)
        self.assertEqual(len(notes), 1)
        self.assertIn("12", notes[0])
        self.assertIn("more", notes[0])
        self.assertIn("j0.tx", notes[0])
        self.assertNotIn("j11.tx", notes[0])

    def test_a_key_the_layer_refused_is_not_counted_and_is_named(self):
        # Maya answers 0 (and a warning) for a plug that is not part of the layer
        class Refusing(FakeCmds):
            def setKeyframe(self, plug, **kw):
                FakeCmds.setKeyframe(self, plug, **kw)
                return 0 if plug == "a.ty" else 1
        keys.cmds = Refusing()
        count, notes = keys.write({"a.tx": 1.0, "a.ty": 2.0}, 1.0,
                                  keys.Layer("AddL", False, True, False, False))
        self.assertEqual(count, 1)
        self.assertEqual(len(notes), 1)
        self.assertIn("a.ty", notes[0])

    def test_a_setkeyframe_that_raises_skips_that_plug_only(self):
        class Raising(FakeCmds):
            def setKeyframe(self, plug, **kw):
                if plug == "a.ty":
                    raise RuntimeError("setKeyframe: cannot key this\nsecond line")
                return FakeCmds.setKeyframe(self, plug, **kw)
        fake = Raising()
        keys.cmds = fake
        count, notes = keys.write({"a.tx": 1.0, "a.ty": 2.0, "a.tz": 3.0}, 1.0, None)
        self.assertEqual(count, 2)
        self.assertEqual(len(notes), 1)
        self.assertIn("a.ty", notes[0])
        self.assertIn("cannot key this", notes[0])
        self.assertNotIn("second line", notes[0])

    def test_a_missing_plug_is_skipped_not_raised(self):
        class Missing(FakeCmds):
            def getAttr(self, plug, **kw):
                if plug == "gone.tx":
                    raise ValueError("No object matches name: gone.tx")
                return False
        keys.cmds = Missing()
        count, notes = keys.write({"gone.tx": 1.0, "a.tx": 2.0}, 1.0, None)
        self.assertEqual(count, 1)
        self.assertIn("missing", notes[0])
        self.assertIn("gone.tx", notes[0])


class QuaternionNote(unittest.TestCase):

    def test_no_layer_no_note(self):
        self.assertEqual(keys.quaternion_note(None), "")

    def test_an_additive_quaternion_layer_is_named(self):
        note = keys.quaternion_note(keys.Layer("Poses", False, True, False, True))
        self.assertIn("Poses", note)
        self.assertIn("quaternion", note)

    def test_an_additive_component_layer_needs_none(self):
        self.assertEqual(keys.quaternion_note(keys.Layer("Poses", False, True, False, False)), "")

    def test_an_override_layer_needs_none(self):
        self.assertEqual(keys.quaternion_note(keys.Layer("Poses", False, False, False, True)), "")

    def test_the_base_needs_none(self):
        self.assertEqual(
            keys.quaternion_note(keys.Layer("BaseAnimation", True, False, False, True)), "")


class LayerSceneCmds(object):
    """Maya's animLayer queries over a small tree: {parent: [children]}, children bottom to top."""

    def __init__(self, tree, selected=(), locked=(), override=(), quaternion=(), root="BaseAnimation",
                 muted=(), weights=None):
        self.tree = tree
        self.root = root
        self.selected = set(selected)
        self.locked = set(locked)
        self.override = set(override) | ({root} if root else set())
        self.quaternion = set(quaternion)
        self.muted = set(muted)
        self.weights = dict(weights or {})

    def animLayer(self, name=None, **kw):
        if not kw.get("query"):
            raise AssertionError(kw)
        if kw.get("root"):
            return self.root
        if kw.get("children"):
            return self.tree.get(name) or None         # Maya answers None for no children
        if kw.get("selected"):
            return name in self.selected
        if kw.get("lock"):
            return name in self.locked
        if kw.get("override"):
            return name in self.override
        if kw.get("mute"):
            return name in self.muted
        if kw.get("weight"):
            return self.weights.get(name, 1.0)
        if kw.get("parent"):
            return next((p for p, kids in self.tree.items() if name in kids), None)
        raise AssertionError(kw)

    def getAttr(self, plug, **kw):
        node, attr = plug.split(".")
        assert attr == "rotationAccumulationMode", plug
        return 1 if node in self.quaternion else 0


class ActiveLayer(Restoring):

    TREE = {"BaseAnimation": ["A", "B", "C"], "B": ["Nested"]}

    def test_no_layers_in_the_scene(self):
        keys.cmds = LayerSceneCmds({}, root=None)
        self.assertEqual(keys.active_layer(), (None, ""))

    def test_the_base_alone(self):
        keys.cmds = LayerSceneCmds({})
        layer, refusal = keys.active_layer()
        self.assertEqual(refusal, "")
        self.assertEqual(layer, keys.Layer("BaseAnimation", True, False, False, False))

    def test_nothing_selected_is_the_base(self):
        keys.cmds = LayerSceneCmds(self.TREE)
        layer, _ = keys.active_layer()
        self.assertEqual(layer.name, "BaseAnimation")
        self.assertTrue(layer.base)

    def test_a_selected_layer_is_the_active_one(self):
        keys.cmds = LayerSceneCmds(self.TREE, selected=["A"])
        layer, _ = keys.active_layer()
        self.assertEqual((layer.name, layer.additive), ("A", True))

    def test_an_override_layer_is_not_additive(self):
        keys.cmds = LayerSceneCmds(self.TREE, selected=["A"], override=["A"])
        layer, _ = keys.active_layer()
        self.assertFalse(layer.additive)

    def test_the_walk_is_depth_first_so_a_nested_layer_sits_above_its_parent(self):
        # preorder: Base 0, A 1, B 2, Nested 3, C 4 - level by level it would be C 3, Nested 4
        keys.cmds = LayerSceneCmds(self.TREE, selected=["B", "Nested"])
        layer, _ = keys.active_layer()
        self.assertEqual(layer.name, "Nested")

    def test_the_parents_next_sibling_sits_above_the_nested_layer(self):
        keys.cmds = LayerSceneCmds(self.TREE, selected=["Nested", "C"])
        layer, _ = keys.active_layer()
        self.assertEqual(layer.name, "C")

    def test_the_topmost_selected_layer_wins(self):
        keys.cmds = LayerSceneCmds(self.TREE, selected=["A", "Nested", "C"])
        layer, _ = keys.active_layer()
        self.assertEqual(layer.name, "C")

    def test_a_locked_active_layer_is_refused(self):
        keys.cmds = LayerSceneCmds(self.TREE, selected=["A"], locked=["A"])
        layer, refusal = keys.active_layer()
        self.assertIsNone(layer)
        self.assertIn("A is locked", refusal)

    def test_the_quaternion_mode_is_read_off_the_layer(self):
        keys.cmds = LayerSceneCmds(self.TREE, selected=["A"], quaternion=["A"])
        layer, _ = keys.active_layer()
        self.assertTrue(layer.quaternion)
        self.assertNotEqual(keys.quaternion_note(layer), "")

    def test_a_layer_without_the_accumulation_attribute_is_component_mode(self):
        class Old(LayerSceneCmds):
            def getAttr(self, plug, **kw):
                raise ValueError("No attribute: " + plug)
        keys.cmds = Old(self.TREE, selected=["A"])
        layer, _ = keys.active_layer()
        self.assertFalse(layer.quaternion)

    # the final review (2026-10-03): a muted or zero-weight active layer took the keys and the
    # pose did not show, with no word why - keyed anyway, and said

    def test_a_muted_layer_takes_the_keys_and_is_said(self):
        keys.cmds = LayerSceneCmds(self.TREE, selected=["A"], muted=["A"])
        layer, refusal = keys.active_layer()
        self.assertEqual((layer.name, refusal), ("A", ""))
        self.assertTrue(layer.muted)
        self.assertEqual(keys.layer_note(layer), keys.MUTED % "A")

    def test_a_layer_under_a_muted_parent_is_muted(self):
        keys.cmds = LayerSceneCmds(self.TREE, selected=["Nested"], muted=["B"])
        layer, _ = keys.active_layer()
        self.assertEqual(layer.name, "Nested")
        self.assertTrue(layer.muted)

    def test_a_layer_at_weight_zero_is_said(self):
        keys.cmds = LayerSceneCmds(self.TREE, selected=["C"], weights={"C": 0.0})
        layer, _ = keys.active_layer()
        self.assertEqual(layer.weight, 0.0)
        self.assertEqual(keys.layer_note(layer), keys.NO_WEIGHT % "C")

    def test_a_layer_on_at_any_weight_and_the_base_say_nothing(self):
        keys.cmds = LayerSceneCmds(self.TREE, selected=["C"], weights={"C": 0.4})
        self.assertEqual(keys.layer_note(keys.active_layer()[0]), "")
        keys.cmds = LayerSceneCmds(self.TREE)
        self.assertEqual(keys.layer_note(keys.active_layer()[0]), "")
        self.assertEqual(keys.layer_note(None), "")


class TweakCmds(object):
    """A scene of time curves for `time_fed` / `Tweaks`: `links` {node: [destination plugs]} (a
    curve's, or a layer blend node's output), `types` {node: type}, `values` {plug: value},
    `uuids` {node name, any spelling's leaf: uuid}; `setAttr` and autoKey logged."""

    def __init__(self, links, types, values, uuids=None):
        self.links, self.types, self.values = links, types, dict(values)
        self.uuids = dict(uuids or {})
        self.log, self.auto = [], True

    def ls(self, *args, **kw):
        if kw.get("type"):
            return [n for n, t in self.types.items() if t in kw["type"]]
        if kw.get("uuid"):
            leaf = args[0].split("|")[-1]
            return [self.uuids[leaf]] if leaf in self.uuids else []
        raise AssertionError((args, kw))

    def listConnections(self, nodes, **kw):
        assert kw.get("connections") and kw.get("plugs") and kw.get("skipConversionNodes")
        out = []
        for node in nodes:
            for plug in self.links.get(node, ()):
                out += [node + ".output", plug]
        return out

    def nodeType(self, node):
        return self.types.get(node, "transform")

    def getAttr(self, plug):
        return self.values[plug]

    def setAttr(self, plug, value):
        self.values[plug] = value
        self.log.append(("set", plug, value, self.auto))

    def autoKeyframe(self, query=False, state=None):
        if query:
            return self.auto
        self.auto = state


class Tweaks(Restoring):
    """The final review (2026-10-03): a same-frame time change - and an evaluation manager
    switch - throws away every unkeyed tweak on a keyed channel in the scene. `Tweaks` reads
    every time-fed channel first and sets back the ones that moved, but the plugs a press keyed."""

    SCENE = dict(
        links={"spine_rx": ["rig:FKSpine1_M.rotateX"], "prop_tx": ["prop.translateX"],
               "wrist_base": ["wrist_rx_L1.inputA"], "wrist_layer": ["wrist_rx_L1.inputB"],
               "wrist_rx_L1": ["rig:FKWrist_L.rotateX"], "elbow_rx": ["pairBlend1.inRotateX1"]},
        types={"spine_rx": "animCurveTA", "prop_tx": "animCurveTL", "wrist_base": "animCurveTA",
               "wrist_layer": "animCurveTA", "wrist_rx_L1": "animBlendNodeAdditiveRotation",
               "elbow_rx": "animCurveTA", "pairBlend1": "pairBlend"},
        values={"rig:FKSpine1_M.rotateX": 25.0, "prop.translateX": 40.0,
                "rig:FKWrist_L.rotateX": 15.0},
        uuids={"rig:FKSpine1_M": "U-SPINE", "prop": "U-PROP", "rig:FKWrist_L": "U-WRIST"})

    def test_every_time_fed_channel_through_layers_but_no_pair_blend(self):
        keys.cmds = TweakCmds(**self.SCENE)
        self.assertEqual(sorted(keys.time_fed()), ["prop.translateX", "rig:FKSpine1_M.rotateX",
                                                   "rig:FKWrist_L.rotateX"])

    def test_what_moved_is_set_back_but_what_the_press_keyed(self):
        fake = TweakCmds(**self.SCENE)
        keys.cmds = fake
        tweaks = keys.Tweaks()
        # a re-evaluation: every tweak back on its curve
        for plug in fake.values:
            fake.values[plug] = 0.0
        back = tweaks.restore(skip=["|grp|rig:FKWrist_L.rotateX"])     # keyed: another spelling
        self.assertEqual(sorted(back), ["prop.translateX", "rig:FKSpine1_M.rotateX"])
        self.assertEqual(fake.values, {"rig:FKSpine1_M.rotateX": 25.0, "prop.translateX": 40.0,
                                       "rig:FKWrist_L.rotateX": 0.0})
        self.assertTrue(all(auto is False for _s, _p, _v, auto in fake.log))   # never keyed
        self.assertTrue(fake.auto)                                          # autoKey back

    def test_nothing_moved_nothing_set(self):
        fake = TweakCmds(**self.SCENE)
        keys.cmds = fake
        self.assertEqual(keys.Tweaks().restore(), [])
        self.assertEqual(fake.log, [])

    def api(self, fail=()):
        """keys._api_set replaced by a recorder (the plugs it set, and the values into the fake
        scene); a plug in `fail` raises as the API does for one it cannot reach."""
        original, ready = keys._api_set, keys._api_ready
        self.addCleanup(setattr, keys, "_api_set", original)
        self.addCleanup(setattr, keys, "_api_ready", ready)
        keys._api_ready = lambda: True
        calls = []

        def record(plug, value):
            if plug in fail:
                raise RuntimeError("(kInvalidParameter): Object does not exist")
            calls.append((plug, value))
            keys.cmds.values[plug] = value
        keys._api_set = record
        return calls

    def test_the_restore_is_no_step_on_the_undo_queue(self):
        # fix round 2: through setAttr the restore was recorded in the press's chunk, and one
        # Ctrl+Z of the press replayed it backwards - every tweak gone again (parallel, the
        # GUI's default). It goes through the API, which the undo queue never sees.
        fake = TweakCmds(**self.SCENE)
        keys.cmds = fake
        calls = self.api()
        tweaks = keys.Tweaks()
        for plug in fake.values:
            fake.values[plug] = 0.0
        back = tweaks.restore(skip=["rig:FKWrist_L.rotateX"])
        self.assertEqual(sorted(back), ["prop.translateX", "rig:FKSpine1_M.rotateX"])
        self.assertEqual(sorted(calls), [("prop.translateX", 40.0),
                                         ("rig:FKSpine1_M.rotateX", 25.0)])
        self.assertEqual([entry for entry in fake.log if entry[0] == "set"], [])   # no setAttr

    def test_a_plug_the_api_cannot_reach_still_goes_back_through_set_attr(self):
        fake = TweakCmds(**self.SCENE)
        keys.cmds = fake
        calls = self.api(fail=("prop.translateX",))
        tweaks = keys.Tweaks()
        for plug in fake.values:
            fake.values[plug] = 0.0
        tweaks.restore()
        self.assertEqual(fake.values["prop.translateX"], 40.0)
        self.assertEqual([p for _s, p, _v, _a in fake.log], ["prop.translateX"])
        self.assertIn(("rig:FKSpine1_M.rotateX", 25.0), calls)


if __name__ == "__main__":
    unittest.main()
