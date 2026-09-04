"""The mode's decisions, against fakes.

What is worth testing here is the policy, not the plumbing: which curves end
up in the scene, what a press is classified as, and that the drag sends the
DIFFERENCE from what it has already applied rather than the running total --
the one bug that would drift a key by a frame over 800 events and look like
a snapping bug.
"""

import unittest

from maya_curveview import edits, mapping, overlay, tool, viewport


# ------------------------------------------------------------------- fakes

class FakeCurve(object):

    def __init__(self, attribute, curve, keys):
        self.attribute = attribute
        self.curve = curve
        self.keys = keys
        self.node = "ctrl"
        self.plug = "ctrl." + attribute


class FakeCurves(object):

    def __init__(self, found, selected=None, angles=None):
        self.found = found
        self.selected = selected or {}
        self.angles = angles or {}
        self.sample_calls = []

    def visible_curves(self):
        return list(self.found)

    def sample(self, curve, t0, t1, count):
        self.sample_calls.append((curve, count))
        return [(t0, 0.0), ((t0 + t1) / 2.0, 1.0), (t1, 0.0)]

    def selected_indices(self, curve):
        return list(self.selected.get(curve, []))

    def tangent_angles(self, curve, indices):
        return dict((index, self.angles.get((curve, index), (0.0, 0.0)))
                    for index in indices)

    def time_range(self):
        return (0.0, 100.0)


class FakeEdits(object):

    def __init__(self):
        self.deltas = []
        self.chunks = []
        self.times = []
        self.tangents = []

    def begin(self):
        self.chunks.append("open")

    def end(self):
        self.chunks.append("close")

    def apply_delta(self, dt, dv):
        if abs(dt) < 1e-9 and abs(dv) < 1e-9:
            return
        self.deltas.append((dt, dv))

    def set_tangent(self, curve, index, side, angle):
        self.tangents.append((curve, index, side, angle))

    def follow_time(self, at_time, now, last, interval=0.05):
        if not mapping.should_evaluate(now, last, interval):
            return last
        self.times.append(at_time)
        return now

    def settle(self, at_time):
        self.times.append(at_time)

    def insert_key(self, curve, at_time):
        pass

    def delete_selected(self):
        return 0


class FakeOverlay(object):
    """Stands in for the window: it only has to hold a scene and a size."""

    def __init__(self, width=1000, height=500):
        self._scene = overlay.empty_scene()
        self._size = mapping.Rect(width, height)
        self.marquees = []
        self.placed = []
        self.closed = False
        self.visible = True

    def rect_size(self):
        return self._size

    def set_scene(self, scene):
        self._scene = scene

    def scene(self):
        return self._scene

    def set_marquee(self, marquee):
        self.marquees.append(marquee)
        self._scene = self._scene._replace(marquee=marquee)

    def place(self, rect):
        self.placed.append(rect)

    def close_overlay(self):
        self.closed = True

    def isVisible(self):
        return self.visible

    def hide(self):
        self.visible = False


class FakeCmds(object):
    """Only what the gesture handlers ask of `cmds`."""

    def __init__(self, anchor=(0.0, 0.0), drag=(0.0, 0.0), button=1,
                 modifier="none", current=7.0):
        self.anchor = anchor
        self.drag = drag
        self.button = button
        self.modifier = modifier
        self.current = current
        self.selected_keys = []
        self.cleared = 0
        self.option = {}

    def draggerContext(self, name, **kwargs):
        if kwargs.get("anchorPoint"):
            return [self.anchor[0], self.anchor[1], 0.0]
        if kwargs.get("dragPoint"):
            return [self.drag[0], self.drag[1], 0.0]
        if kwargs.get("button"):
            return self.button
        if kwargs.get("modifier"):
            return self.modifier
        if kwargs.get("exists"):
            return False
        return None

    def currentTime(self, *args, **kwargs):
        if kwargs.get("query"):
            return self.current
        if args:
            self.current = args[0]
        return self.current

    def selectKey(self, *args, **kwargs):
        if kwargs.get("clear"):
            self.cleared += 1
            return
        self.selected_keys.append((args[0] if args else None,
                                   kwargs.get("index"),
                                   tuple(sorted(k for k in kwargs
                                                if k != "index"))))

    def optionVar(self, **kwargs):
        if kwargs.get("exists"):
            return kwargs["exists"] in self.option
        if kwargs.get("query"):
            return self.option.get(kwargs["query"], 0)
        if "intValue" in kwargs:
            name, value = kwargs["intValue"]
            self.option[name] = value


class Fixture(unittest.TestCase):

    def setUp(self):
        tool._STATE.reset()
        self.curves = FakeCurves([])
        self.edits = FakeEdits()
        self.cmds = FakeCmds()
        tool.curves = self.curves
        tool.edits = self.edits
        tool.cmds = self.cmds

    def tearDown(self):
        tool._STATE.reset()
        tool.curves = tool._real_curves
        tool.edits = tool._real_edits
        tool.cmds = tool._real_cmds
        tool.viewport = tool._real_viewport

    def stub_select(self):
        """Catch the scene-selection calls, and put the real one back.

        Saved and restored rather than deleted: assigning over the module
        attribute replaces the real function, so a `del` would take it away
        for the rest of the session.
        """
        picked = []
        original = tool.select_from_screen
        tool.select_from_screen = lambda *a: picked.append(a)
        self.addCleanup(setattr, tool, "select_from_screen", original)
        return picked

    def arm(self, found, selected=None, angles=None, width=1000, height=500):
        self.curves.found = found
        self.curves.selected = selected or {}
        self.curves.angles = angles or {}
        window = FakeOverlay(width, height)
        tool._STATE.overlay = window
        window.set_scene(tool.build_scene(window.rect_size()))
        return window


# ------------------------------------------------------------------- tests

class TestBuildScene(Fixture):

    def test_one_drawn_curve_per_visible_curve(self):
        self.arm([FakeCurve("translateX", "curveA",
                            [(0.0, 0.0), (10.0, 1.0)])])
        scene = tool._STATE.overlay.scene()
        self.assertEqual(len(scene.curves), 1)
        self.assertEqual(scene.curves[0].attribute, "translateX")
        self.assertEqual(scene.curves[0].keys, [(0.0, 0.0), (10.0, 1.0)])

    def test_nothing_selected_gives_an_empty_scene_and_says_so(self):
        window = self.arm([])
        scene = window.scene()
        self.assertEqual(scene.curves, [])
        self.assertEqual(scene.message, tool.NO_CURVES)

    def test_the_window_is_fitted_to_the_samples_not_only_the_keys(self):
        # The fake's samples reach 1.0 while the keys stay at 0.0: a window
        # fitted to the keys alone would clip the overshoot, which is the
        # very shape an animator is looking at.
        window = self.arm([FakeCurve("translateX", "curveA",
                                     [(0.0, 0.0), (100.0, 0.0)])])
        self.assertGreater(window.scene().frame.v1, 1.0)

    def test_the_shared_axis_is_one_frame_for_every_curve(self):
        window = self.arm([
            FakeCurve("translateX", "curveA", [(0.0, 0.0), (10.0, 100.0)]),
            FakeCurve("rotateZ", "curveB", [(0.0, 0.0), (10.0, 1.0)])])
        frames = [drawn.frame for drawn in window.scene().curves]
        self.assertEqual(frames[0], frames[1])

    def test_sampling_asks_for_the_curve_node(self):
        self.arm([FakeCurve("translateX", "curveA", [(0.0, 0.0)])])
        self.assertEqual(self.curves.sample_calls[0][0], "curveA")

    def test_the_sample_count_follows_the_width(self):
        self.arm([FakeCurve("translateX", "curveA", [(0.0, 0.0)])],
                 width=300)
        self.assertEqual(self.curves.sample_calls[0][1],
                         mapping.sample_count(mapping.Rect(300, 500)))


class TestPressClassification(Fixture):

    def test_lmb_is_always_a_select_gesture(self):
        self.arm([FakeCurve("translateX", "curveA", [(50.0, 0.5)])])
        self.cmds.button = 1
        self.cmds.anchor = (10.0, 10.0)
        tool.on_press()
        self.assertEqual(tool._STATE.gesture, "select")

    def test_mmb_with_no_selected_key_does_nothing(self):
        self.arm([FakeCurve("translateX", "curveA", [(50.0, 0.5)])])
        self.cmds.button = 2
        tool.on_press()
        self.assertIsNone(tool._STATE.gesture)
        self.assertEqual(self.edits.chunks, [])

    def test_mmb_with_a_selected_key_starts_a_drag_in_one_chunk(self):
        self.arm([FakeCurve("translateX", "curveA",
                            [(0.0, 0.0), (50.0, 1.0)])],
                 selected={"curveA": [1]})
        self.cmds.button = 2
        tool.on_press()
        self.assertEqual(tool._STATE.gesture, "drag")
        self.assertEqual(self.edits.chunks, ["open"])

    def test_the_followed_time_is_the_selected_key_nearest_the_press(self):
        window = self.arm([FakeCurve("translateX", "curveA",
                                     [(10.0, 0.0), (90.0, 0.0)])],
                          selected={"curveA": [0, 1]})
        scene = window.scene()
        rect = window.rect_size()
        near, _ = mapping.to_pixels(scene.curves[0].frame, rect, 90.0, 0.0)
        self.cmds.button = 2
        # anchorPoint arrives in Maya's bottom-up Y, which the handler flips
        self.cmds.anchor = (near, mapping.flip_y(rect, 250.0))
        tool.on_press()
        self.assertEqual(tool._STATE.drag_time, 90.0)

    def test_a_press_with_no_overlay_is_a_no_op(self):
        tool._STATE.reset()
        tool.on_press()          # must not raise
        self.assertIsNone(tool._STATE.gesture)


class TestDrag(Fixture):

    def arm_drag(self):
        window = self.arm([FakeCurve("translateX", "curveA",
                                     [(20.0, 0.0), (50.0, 1.0)])],
                          selected={"curveA": [1]})
        self.cmds.button = 2
        rect = window.rect_size()
        frame = window.scene().curves[0].frame
        anchor_qt = mapping.to_pixels(frame, rect, 50.0, 1.0)
        self.cmds.anchor = (anchor_qt[0], mapping.flip_y(rect, anchor_qt[1]))
        tool.on_press()
        return window, rect, frame, anchor_qt

    def test_a_ten_frame_drag_moves_ten_frames(self):
        window, rect, frame, anchor = self.arm_drag()
        target = mapping.to_pixels(frame, rect, 60.0, 1.0)
        self.cmds.drag = (target[0], mapping.flip_y(rect, target[1]))
        tool.on_drag()
        self.assertEqual(self.edits.deltas[0][0], 10.0)

    def test_the_second_event_sends_only_the_difference(self):
        window, rect, frame, anchor = self.arm_drag()
        for at in (60.0, 65.0):
            target = mapping.to_pixels(frame, rect, at, 1.0)
            self.cmds.drag = (target[0], mapping.flip_y(rect, target[1]))
            tool.on_drag()
        self.assertEqual([round(d[0], 6) for d in self.edits.deltas],
                         [10.0, 5.0])

    def test_the_total_never_drifts_over_many_events(self):
        # 200 events walking to +37 frames must add up to exactly 37, which
        # is the property that would break if the handler re-sent the total
        # or re-rounded it against the last applied value.
        window, rect, frame, anchor = self.arm_drag()
        for step in range(1, 201):
            at = 50.0 + 37.0 * step / 200.0
            target = mapping.to_pixels(frame, rect, at, 1.0)
            self.cmds.drag = (target[0], mapping.flip_y(rect, target[1]))
            tool.on_drag()
        self.assertAlmostEqual(sum(d[0] for d in self.edits.deltas), 37.0)
        self.assertAlmostEqual(tool._STATE.applied[0], 37.0)

    def test_time_is_gated_by_the_throttle(self):
        window, rect, frame, anchor = self.arm_drag()
        for step in range(50):
            target = mapping.to_pixels(frame, rect, 51.0 + step, 1.0)
            self.cmds.drag = (target[0], mapping.flip_y(rect, target[1]))
            tool.on_drag()
        self.assertLess(len(self.edits.times), 50,
                        "the throttle let every event through")
        self.assertGreaterEqual(len(self.edits.times), 1)

    def test_the_release_settles_the_time_and_closes_the_chunk(self):
        window, rect, frame, anchor = self.arm_drag()
        target = mapping.to_pixels(frame, rect, 62.0, 1.0)
        self.cmds.drag = (target[0], mapping.flip_y(rect, target[1]))
        tool.on_release()
        self.assertEqual(self.edits.chunks, ["open", "close"])
        self.assertEqual(self.edits.times[-1], 62.0)

    def test_a_marquee_drag_only_draws_a_rectangle(self):
        window = self.arm([FakeCurve("translateX", "curveA", [(0.0, 0.0)])])
        self.cmds.button = 1
        self.cmds.anchor = (100.0, 100.0)
        tool.on_press()
        self.cmds.drag = (300.0, 200.0)
        tool.on_drag()
        self.assertEqual(self.edits.deltas, [])
        self.assertIsNotNone(window.marquees[-1])


class TestSelecting(Fixture):

    def test_a_click_on_a_key_selects_that_key(self):
        window = self.arm([FakeCurve("translateX", "curveA",
                                     [(0.0, 0.0), (50.0, 1.0)])])
        rect = window.rect_size()
        frame = window.scene().curves[0].frame
        at = mapping.to_pixels(frame, rect, 50.0, 1.0)
        raw = (at[0], mapping.flip_y(rect, at[1]))
        self.cmds.button = 1
        self.cmds.anchor = raw
        self.cmds.drag = raw
        picked = self.stub_select()
        tool.on_press()
        tool.on_release()
        self.assertEqual(picked, [], "it fell through to the scene")
        self.assertEqual(len(self.cmds.selected_keys), 1)
        self.assertEqual(self.cmds.selected_keys[0][1], (1, 1))

    def test_a_click_on_nothing_selects_in_the_scene(self):
        window = self.arm([FakeCurve("translateX", "curveA",
                                     [(0.0, 0.0), (50.0, 1.0)])])
        self.cmds.button = 1
        self.cmds.anchor = (5.0, 5.0)
        self.cmds.drag = (5.0, 5.0)
        picked = self.stub_select()
        tool.on_press()
        tool.on_release()
        self.assertEqual(len(picked), 1)
        self.assertEqual(self.cmds.selected_keys, [])

    def test_a_marquee_over_keys_takes_the_keys(self):
        window = self.arm([FakeCurve("translateX", "curveA",
                                     [(10.0, 0.0), (50.0, 1.0),
                                      (90.0, 0.0)])])
        rect = window.rect_size()
        frame = window.scene().curves[0].frame
        low = mapping.to_pixels(frame, rect, 5.0, -0.5)
        high = mapping.to_pixels(frame, rect, 95.0, 1.5)
        self.cmds.button = 1
        self.cmds.anchor = (low[0], mapping.flip_y(rect, low[1]))
        self.cmds.drag = (high[0], mapping.flip_y(rect, high[1]))
        picked = self.stub_select()
        tool.on_press()
        tool.on_release()
        self.assertEqual(picked, [])
        self.assertEqual(len(self.cmds.selected_keys), 3)

    def test_a_marquee_over_nothing_box_selects_in_the_scene(self):
        self.arm([FakeCurve("translateX", "curveA", [(50.0, 0.5)])])
        self.cmds.button = 1
        self.cmds.anchor = (1.0, 1.0)
        self.cmds.drag = (4.0, 60.0)
        picked = self.stub_select()
        tool.on_press()
        tool.on_release()
        self.assertEqual(len(picked), 1)

    def test_replace_clears_the_key_selection_first(self):
        self.arm([FakeCurve("translateX", "curveA", [(0.0, 0.0)])])
        tool.select_keys({0: [0]}, "replace")
        self.assertEqual(self.cmds.cleared, 1)
        self.assertIn("add", self.cmds.selected_keys[0][2])

    def test_toggle_does_not_clear(self):
        self.arm([FakeCurve("translateX", "curveA", [(0.0, 0.0)])])
        tool.select_keys({0: [0]}, "toggle")
        self.assertEqual(self.cmds.cleared, 0)
        self.assertIn("toggle", self.cmds.selected_keys[0][2])

    def test_a_clear_that_raises_is_survived(self):
        # CLAUDE.md trap 43: selectKey(clear=True) raises when nothing is
        # selected, and that is exactly the case with nothing to clear.
        class Raising(FakeCmds):
            def selectKey(self, *args, **kwargs):
                if kwargs.get("clear"):
                    raise TypeError("Error retrieving default arguments")
                FakeCmds.selectKey(self, *args, **kwargs)

        self.cmds = Raising()
        tool.cmds = self.cmds
        self.arm([FakeCurve("translateX", "curveA", [(0.0, 0.0)])])
        tool.select_keys({0: [0]}, "replace")
        self.assertEqual(len(self.cmds.selected_keys), 1)


class TestAdjustment(Fixture):
    """The half of the object pick that carries the decisions.

    The pick itself is always a REPLACE, because the CLICK form of
    kXORWithList was measured live to be a no-op while its BOX form toggles
    correctly -- so the modifier is applied here instead.
    """

    def setUp(self):
        Fixture.setUp(self)
        self.selects = []

        def select(*args, **kwargs):
            self.selects.append((args, tuple(sorted(kwargs))))

        self.cmds.select = select

    def test_replace_leaves_the_pick_alone(self):
        tool.apply_adjustment(["old"], ["new"], "replace")
        self.assertEqual(self.selects, [])

    def test_add_restores_then_adds(self):
        tool.apply_adjustment(["old"], ["new"], "add")
        self.assertEqual([call[1] for call in self.selects],
                         [("replace",), ("add",)])
        self.assertEqual(self.selects[0][0], (["old"],))
        self.assertEqual(self.selects[1][0], (["new"],))

    def test_toggle_uses_the_toggle_flag(self):
        tool.apply_adjustment(["old"], ["new"], "toggle")
        self.assertEqual(self.selects[-1][1], ("toggle",))

    def test_remove_uses_deselect(self):
        tool.apply_adjustment(["old"], ["new"], "remove")
        self.assertEqual(self.selects[-1][1], ("deselect",))

    def test_an_empty_before_clears_instead_of_selecting_nothing(self):
        tool.apply_adjustment([], ["new"], "add")
        self.assertEqual(self.selects[0][1], ("clear",))

    def test_picking_nothing_only_restores(self):
        tool.apply_adjustment(["old"], [], "toggle")
        self.assertEqual([call[1] for call in self.selects],
                         [("replace",)])


class TestTangent(Fixture):

    def test_mmb_on_a_handle_drags_the_tangent(self):
        window = self.arm([FakeCurve("translateX", "curveA",
                                     [(50.0, 0.5)])],
                          selected={"curveA": [0]},
                          angles={("curveA", 0): (0.0, 0.0)})
        rect = window.rect_size()
        drawn = window.scene().curves[0]
        _, out = mapping.tangent_points(drawn.frame, rect, drawn.keys[0],
                                        0.0, 0.0,
                                        length=overlay.TANGENT_LENGTH)
        self.cmds.button = 2
        self.cmds.anchor = (out[0], mapping.flip_y(rect, out[1]))
        tool.on_press()
        self.assertEqual(tool._STATE.gesture, "tangent")
        target = (out[0], out[1] - 40.0)
        self.cmds.drag = (target[0], mapping.flip_y(rect, target[1]))
        tool.on_drag()
        self.assertEqual(len(self.edits.tangents), 1)
        self.assertGreater(self.edits.tangents[0][3], 0.0)

    def test_an_unselected_key_has_no_handle_to_grab(self):
        window = self.arm([FakeCurve("translateX", "curveA",
                                     [(50.0, 0.5)])])
        rect = window.rect_size()
        drawn = window.scene().curves[0]
        _, out = mapping.tangent_points(drawn.frame, rect, drawn.keys[0],
                                        0.0, 0.0,
                                        length=overlay.TANGENT_LENGTH)
        self.cmds.button = 2
        self.cmds.anchor = (out[0], mapping.flip_y(rect, out[1]))
        tool.on_press()
        self.assertIsNone(tool._STATE.gesture)


class TestModeState(Fixture):

    def test_is_on_follows_the_overlay(self):
        self.assertFalse(tool.is_on())
        self.arm([])
        self.assertTrue(tool.is_on())

    def test_enable_without_a_panel_says_so_and_builds_nothing(self):
        class NoPanel(object):
            @staticmethod
            def panel_rect(panel=None):
                return None

        tool.viewport = NoPanel
        message = tool.enable()
        self.assertIn("no model panel", message)
        self.assertFalse(tool.is_on())

    def test_a_second_enable_is_refused(self):
        self.arm([])
        self.assertIn("already on", tool.enable())

    def test_disable_when_off_says_so(self):
        self.assertIn("already off", tool.disable())


if __name__ == "__main__":
    unittest.main()


class TestCurveCap(Fixture):
    """A UE clip's root carries 141 animated channels (measured). The cap
    is the backstop behind curves.py's transform narrowing, and it says
    what to do rather than silently drawing twelve of a hundred."""

    def _many(self, count):
        return [FakeCurve("attr{0}".format(i), "curve{0}".format(i),
                          [(0.0, float(i))]) for i in range(count)]

    def test_more_than_the_cap_is_truncated(self):
        window = self.arm(self._many(40))
        self.assertEqual(len(window.scene().curves), tool.MAX_CURVES)

    def test_and_the_message_says_how_many_there_were(self):
        window = self.arm(self._many(40))
        message = window.scene().message
        self.assertIn("of 40 channels", message)
        self.assertIn("channel box", message)

    def test_the_state_list_is_truncated_with_the_scene(self):
        # scene.curves is index-parallel to _STATE.curves; if the cap
        # trimmed one and not the other, every click would resolve to the
        # wrong animCurve.
        window = self.arm(self._many(40))
        self.assertEqual(len(tool._STATE.curves),
                         len(window.scene().curves))

    def test_under_the_cap_the_message_is_the_plain_count(self):
        window = self.arm(self._many(3))
        self.assertIn("3 curve(s)", window.scene().message)

    def test_the_scene_reports_whether_it_is_normalised(self):
        window = self.arm(self._many(2))
        self.assertFalse(window.scene().normalised)
