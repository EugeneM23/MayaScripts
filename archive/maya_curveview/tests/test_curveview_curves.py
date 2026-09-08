"""The channel-box rule and the sampling, against a fake Maya.

The fake is rebound onto the module attribute (`curves.cmds = fake`) and
restored in tearDown -- never by deleting `sys.modules` entries, which
leaves the stale module bound as an attribute of the parent package and
hands the old object straight back (the repo has paid for that one).
"""

import unittest

from maya_curveview import curves


class FakeCmds(object):
    """Just enough Maya to answer the channel-box rule."""

    def __init__(self, selection=(), channel_selection=None, plugs=None,
                 keys=None, selected=None, playback=(0.0, 100.0),
                 angles=None):
        self._selection = list(selection)
        self._channel_selection = channel_selection
        self._plugs = plugs or {}
        self._keys = keys or {}
        self._selected = selected or {}
        self._playback = playback
        self._angles = angles or {}
        self.eval_calls = []
        self.tangent_calls = []

    def ls(self, *args, **kwargs):
        if kwargs.get("selection"):
            return list(self._selection)
        return []

    def channelBox(self, name, **kwargs):
        return self._channel_selection

    def listAttr(self, node, **kwargs):
        return [attribute for (owner, attribute) in self._plugs
                if owner == node]

    def listConnections(self, plug, **kwargs):
        node, _, attribute = plug.partition(".")
        return self._plugs.get((node, attribute))

    def keyframe(self, target, **kwargs):
        if kwargs.get("eval"):
            self.eval_calls.append(kwargs.get("time"))
            return [0.0]
        pairs = self._keys.get(target, [])
        if kwargs.get("selected"):
            pairs = [pairs[i] for i in self._selected.get(target, [])]
        if kwargs.get("timeChange"):
            return [t for (t, _v) in pairs]
        if kwargs.get("valueChange"):
            return [v for (_t, v) in pairs]
        return []

    def keyTangent(self, target, **kwargs):
        self.tangent_calls.append(kwargs)
        index = kwargs.get("index", (0, 0))[0]
        pair = self._angles.get((target, index), (0.0, 0.0))
        if kwargs.get("inAngle"):
            return [pair[0]]
        if kwargs.get("outAngle"):
            return [pair[1]]
        return []

    def playbackOptions(self, **kwargs):
        return self._playback[0] if kwargs.get("min") else self._playback[1]


class Fixture(unittest.TestCase):

    def tearDown(self):
        curves.cmds = curves._real_cmds


class TestChannelRule(Fixture):

    def test_channel_box_selection_wins(self):
        curves.cmds = FakeCmds(
            selection=["ctrl"], channel_selection=["translateX"],
            plugs={("ctrl", "translateX"): ["curveA"],
                   ("ctrl", "translateY"): ["curveB"]})
        self.assertEqual(curves.channel_attributes("ctrl"), ["translateX"])

    def test_nothing_selected_there_gives_every_animated_channel(self):
        curves.cmds = FakeCmds(
            selection=["ctrl"], channel_selection=None,
            plugs={("ctrl", "translateX"): ["curveA"],
                   ("ctrl", "translateY"): ["curveB"],
                   ("ctrl", "translateZ"): None})
        self.assertEqual(sorted(curves.channel_attributes("ctrl")),
                         ["translateX", "translateY"])

    def test_a_channel_selected_on_another_node_is_not_borrowed(self):
        # The channel box's selection is a set of attribute NAMES and it
        # applies to whatever it applies to; a node that has no animated
        # channel of that name must not gain one.
        curves.cmds = FakeCmds(
            selection=["ctrl", "other"], channel_selection=["translateX"],
            plugs={("ctrl", "translateX"): ["curveA"],
                   ("other", "translateY"): ["curveB"]})
        self.assertEqual(curves.channel_attributes("other"), [])

    def test_no_selection_means_no_curves(self):
        curves.cmds = FakeCmds(selection=[])
        self.assertEqual(curves.visible_curves(), [])

    def test_a_channel_with_no_curve_is_dropped(self):
        curves.cmds = FakeCmds(
            selection=["ctrl"], channel_selection=["translateZ"],
            plugs={("ctrl", "translateZ"): None})
        self.assertEqual(curves.visible_curves(), [])

    def test_visible_curves_carries_the_keys(self):
        curves.cmds = FakeCmds(
            selection=["ctrl"], channel_selection=["translateX"],
            plugs={("ctrl", "translateX"): ["curveA"]},
            keys={"curveA": [(0.0, 1.0), (10.0, 2.0)]})
        found = curves.visible_curves()
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].attribute, "translateX")
        self.assertEqual(found[0].node, "ctrl")
        self.assertEqual(found[0].plug, "ctrl.translateX")
        self.assertEqual(found[0].curve, "curveA")
        self.assertEqual(found[0].keys, [(0.0, 1.0), (10.0, 2.0)])

    def test_an_explicit_selection_overrides_the_scene(self):
        curves.cmds = FakeCmds(
            selection=["somebody_else"], channel_selection=["translateX"],
            plugs={("ctrl", "translateX"): ["curveA"]},
            keys={"curveA": [(0.0, 1.0)]})
        found = curves.visible_curves(selection=["ctrl"])
        self.assertEqual([c.curve for c in found], ["curveA"])

    def test_a_missing_channel_box_does_not_raise(self):
        class NoChannelBox(FakeCmds):
            def channelBox(self, name, **kwargs):
                raise RuntimeError("no such control")

        curves.cmds = NoChannelBox(
            selection=["ctrl"], plugs={("ctrl", "translateX"): ["curveA"]},
            keys={"curveA": [(0.0, 1.0)]})
        self.assertEqual([c.curve for c in curves.visible_curves()],
                         ["curveA"])


class TestKeys(Fixture):

    def test_selected_indices_are_positions_not_times(self):
        curves.cmds = FakeCmds(
            keys={"curveA": [(0.0, 0.0), (5.0, 1.0), (10.0, 2.0)]},
            selected={"curveA": [1, 2]})
        self.assertEqual(curves.selected_indices("curveA"), [1, 2])

    def test_nothing_selected_gives_no_indices(self):
        curves.cmds = FakeCmds(
            keys={"curveA": [(0.0, 0.0)]}, selected={})
        self.assertEqual(curves.selected_indices("curveA"), [])

    def test_a_fractional_key_time_still_matches(self):
        curves.cmds = FakeCmds(
            keys={"curveA": [(0.0, 0.0), (2.5, 1.0)]},
            selected={"curveA": [1]})
        self.assertEqual(curves.selected_indices("curveA"), [1])

    def test_tangent_angles_only_asks_for_what_it_was_given(self):
        fake = FakeCmds(keys={"curveA": [(0.0, 0.0), (5.0, 1.0)]},
                        angles={("curveA", 1): (10.0, 20.0)})
        curves.cmds = fake
        self.assertEqual(curves.tangent_angles("curveA", [1]),
                         {1: (10.0, 20.0)})
        for call in fake.tangent_calls:
            self.assertEqual(call["index"], (1, 1))


class TestSampling(Fixture):

    def test_sampling_evaluates_the_curve_node_not_the_plug(self):
        fake = FakeCmds()
        curves.cmds = fake
        curves.sample("curveA", 0.0, 10.0, 3)
        self.assertEqual(len(fake.eval_calls), 3)
        self.assertEqual(fake.eval_calls[0], (0.0, 0.0))
        self.assertEqual(fake.eval_calls[-1], (10.0, 10.0))

    def test_a_single_sample_does_not_divide_by_zero(self):
        curves.cmds = FakeCmds()
        self.assertEqual(len(curves.sample("curveA", 0.0, 10.0, 1)), 1)

    def test_time_range_is_the_playback_range(self):
        curves.cmds = FakeCmds(playback=(-20.0, 30.0))
        self.assertEqual(curves.time_range(), (-20.0, 30.0))


if __name__ == "__main__":
    unittest.main()


class TestTransformNarrowing(Fixture):
    """With nothing picked in the channel box the answer is the TRANSFORM
    channels. Measured on the animator's scene: a UE clip's root carries
    141 animated channels -- Pose_0..9, MoveData_* and ~130 pose drivers,
    which is the game's data (trap 40) -- and drawing them all buried the
    animation in a flat band."""

    def _ue_root(self):
        plugs = {}
        for attribute in ("translateX", "translateY", "translateZ",
                          "rotateX", "rotateY", "rotateZ"):
            plugs[("root", attribute)] = ["curve_" + attribute]
        for attribute in ("Pose_0", "Pose_1", "MoveData_Speed",
                          "DisableLegIK", "thigh_l_fwd_90"):
            plugs[("root", attribute)] = ["curve_" + attribute]
        return plugs

    def test_the_fallback_is_the_transform_channels(self):
        curves.cmds = FakeCmds(selection=["root"], channel_selection=None,
                               plugs=self._ue_root())
        found = curves.channel_attributes("root")
        self.assertEqual(len(found), 6)
        self.assertNotIn("Pose_0", found)
        self.assertNotIn("MoveData_Speed", found)

    def test_a_channel_box_pick_still_reaches_a_custom_attribute(self):
        plugs = self._ue_root()
        plugs[("root", "Pose_3")] = ["curve_Pose_3"]
        curves.cmds = FakeCmds(selection=["root"],
                               channel_selection=["Pose_3", "MoveData_Speed"],
                               plugs=plugs)
        self.assertEqual(sorted(curves.channel_attributes("root")),
                         ["MoveData_Speed", "Pose_3"])

    def test_a_node_animated_only_on_custom_attributes_still_shows(self):
        curves.cmds = FakeCmds(
            selection=["gizmo"], channel_selection=None,
            plugs={("gizmo", "autoTwist"): ["curveA"],
                   ("gizmo", "bias"): ["curveB"]})
        self.assertEqual(sorted(curves.channel_attributes("gizmo")),
                         ["autoTwist", "bias"])
