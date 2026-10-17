"""The Time Bar offscreen (2026-10-16): the range row and the time row, on a fake
link so no Maya scene is touched - painting, scrubbing, the highlight moving and
scaling keys, the range block, zoom, the menus, the keys the playhead reaches.

Spec: docs/superpowers/specs/2026-10-16-time-bar-design.md
"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import maya_hubqt
    QT = maya_hubqt.qt()
except Exception:                                            # noqa: BLE001
    QT = None

import maya_hubstyle
from maya_timebar import bar, look


class FakeLink(object):

    def __init__(self):
        self.log = []
        self.s = {"now": 12.0, "a0": 0.0, "a1": 100.0, "p0": 10.0, "p1": 60.0,
                  "unit": "ntsc", "auto": True, "playing": False, "highlight": None}
        self.x = {"loop": "continuous", "speed": 1.0, "cache": True, "sound": "audio1",
                  "sound_shown": True, "character": ""}
        self.k = ([0.0, 6.0, 12.0, 30.0, 40.0], [9.0])
        self.marks = [(10.0, 20.0, (0.5, 0.6, 0.9), "Anticipation")]

    def _log(self, *entry):
        self.log.append(entry)

    def light(self):
        return dict(self.s)

    def extra(self):
        return dict(self.x)

    def keys(self):
        self._log("keys")
        return self.k

    def bookmarks(self):
        return list(self.marks)

    def waveform(self, node, start, end):
        return [(f, 0.5) for f in range(int(start), int(end) + 1)]

    def now(self):
        return self.s["now"]

    def set_time(self, frame):
        self._log("set_time", frame)
        self.s["now"] = float(frame)

    def scrub_only(self, frame):
        self._log("scrub_only", frame)
        self.s["now"] = float(frame)

    def begin_scrub(self):
        self._log("begin_scrub")

    def end_scrub(self):
        self._log("end_scrub")

    def set_ranges(self, a0, a1, p0, p1):
        self._log("set_ranges", a0, a1, p0, p1)
        self.s.update(a0=a0, a1=a1, p0=p0, p1=p1)

    def set_highlight(self, sel):
        self._log("set_highlight", sel)
        self.s["highlight"] = sel

    def move_keys(self, selection, target):
        self._log("move_keys", selection, target)

    def step_key(self, forward, known):
        frame = look.neighbour_key(known, self.s["now"], forward)
        if frame is not None:
            self.set_time(frame)

    def toggle_play(self, forward=True):
        self._log("toggle_play", forward)
        self.s["playing"] = not self.s["playing"]

    def toggle_auto(self):
        self.s["auto"] = not self.s["auto"]

    def cycle_loop(self):
        self.x["loop"] = {"continuous": "once", "once": "oscillate"}.get(self.x["loop"], "continuous")

    def toggle_cache(self):
        self.x["cache"] = not self.x["cache"]

    def set_speed(self, v):
        self.x["speed"] = v

    def set_unit(self, unit):
        self.s["unit"] = unit

    def layers(self):
        return [("BaseAnimation", "BaseAnimation", False), ("Layer1", "Layer1", True)]

    def layer_label(self):
        return "Layer1"

    def pick_layer(self, name):
        self._log("pick_layer", name)

    def character_sets(self):
        return ["hero"]

    def pick_character(self, name):
        self._log("pick_character", name)

    def sounds(self):
        return ["audio1"]

    def set_sound(self, node):
        self._log("set_sound", node)

    def toggle_sound(self):
        self.x["sound_shown"] = not self.x["sound_shown"]

    def add_bookmark(self, sel):
        self._log("add_bookmark", sel)

    def step_bookmark(self, forward):
        self._log("step_bookmark", forward)

    def preferences(self):
        self._log("preferences")

    def back_to_maya(self):
        self._log("back")


@unittest.skipIf(QT is None, "no Qt")
class Strip(unittest.TestCase):

    motion = False

    def setUp(self):
        self.app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
        self.link = FakeLink()
        self.strip = bar.make(self.link, 1.0, maya_hubstyle.TOKENS, motion=self.motion)
        self.strip.resize(1500, 80)
        self.strip.move(3000, 3000)
        self.strip.show()
        self.app.processEvents()
        self.addCleanup(self.strip.deleteLater)
        self.tl = self.strip.timeline

    def mouse(self, widget, kind, x, button, buttons, mods=None):
        Qt = QT.QtCore.Qt
        local = QT.QtCore.QPointF(x, widget.height() / 2.0)
        event = QT.QtGui.QMouseEvent(kind, local, QT.QtCore.QPointF(widget.mapToGlobal(local.toPoint())),
                                     button, buttons, mods if mods is not None else Qt.NoModifier)
        QT.QtWidgets.QApplication.sendEvent(widget, event)

    def drag(self, widget, x0, x1, button=None, mods=None):
        E, Qt = QT.QtCore.QEvent, QT.QtCore.Qt
        button = button or Qt.LeftButton
        self.mouse(widget, E.MouseButtonPress, x0, button, button, mods)
        self.mouse(widget, E.MouseMove, x1, Qt.NoButton, button, mods)
        self.mouse(widget, E.MouseButtonRelease, x1, button, Qt.NoButton, mods)

    def x(self, frame):
        """Just inside frame `frame`'s cell (its left edge is the frame line)."""
        return self.tl.track().x(frame) + 0.25

    def calls(self, name):
        return [e for e in self.link.log if e[0] == name]


class Shows(Strip):

    def test_both_rows_show_the_scene(self):
        st = self.strip
        self.assertEqual([f.text() for f in (st.anim_start, st.play_start, st.play_end, st.anim_end)],
                         ["0", "10", "60", "100"])
        self.assertEqual(st.field.text(), "12")
        self.assertTrue(st.fps.text().startswith("30 fps"))
        self.assertTrue(st.auto.isChecked())
        self.assertTrue(st.loop.isChecked() and st.cache.isChecked() and st.sound.isChecked())
        self.assertTrue(st.layer.text().startswith("Layer1"))
        self.assertTrue(st.character.text().startswith("No Character Set"))
        self.assertEqual(st.keys, [0.0, 6.0, 12.0, 30.0, 40.0])
        self.assertEqual(st.breakdowns, [9.0])
        self.assertEqual(len(st.marks), 1)
        self.assertTrue(st.wave)
        self.assertEqual(len(st.transport), 8)

    def test_the_timeline_shows_the_playback_range(self):
        t = self.tl.track()
        self.assertEqual((t.v0, t.v1), (10.0, 60.0))

    def test_it_paints_keys_and_the_playhead(self):
        image = QT.QtGui.QImage(self.tl.size(), QT.QtGui.QImage.Format_ARGB32)
        image.fill(0)
        self.tl.render(image)
        accent = QT.QtGui.QColor(maya_hubstyle.TOKENS["accent"])

        def near(px):
            return all(abs(a - b) < 30 for a, b in ((px.red(), accent.red()), (px.green(), accent.green()),
                                                     (px.blue(), accent.blue())))
        self.assertTrue(near(image.pixelColor(int(self.x(30)), bar.KEY_Y)), "a key")
        self.assertTrue(near(image.pixelColor(int(self.x(12)), self.tl.height() - 6)), "the playhead")
        self.assertFalse(near(image.pixelColor(int(self.x(50)), bar.KEY_Y)))


class Time(Strip):

    def test_a_press_scrubs_in_maya_s_scrub_mode(self):
        self.drag(self.tl, self.x(40.3), self.x(44.6))
        #  a frame is a cell (2026-10-17): 44.6 is inside frame 44's
        self.assertEqual(self.calls("set_time"), [("set_time", 40), ("set_time", 44)])
        names = [e[0] for e in self.link.log if e[0] in ("begin_scrub", "set_time", "end_scrub")]
        self.assertEqual((names[0], names[-1]), ("begin_scrub", "end_scrub"))
        self.assertEqual(self.strip.field.text(), "44")

    def test_a_scrub_paints_the_new_frame_before_maya_evaluates_it(self):
        painted, seen = [], []
        real = self.tl.paintEvent
        self.tl.paintEvent = lambda e: (painted.append(self.strip.state["now"]), real(e))
        self.link.set_time = lambda f: seen.append(list(painted))
        E, Qt = QT.QtCore.QEvent, QT.QtCore.Qt
        self.mouse(self.tl, E.MouseButtonPress, self.x(40), Qt.LeftButton, Qt.LeftButton)
        self.assertEqual(seen and seen[0][-1:], [40])

    def test_a_middle_drag_moves_time_without_updating_the_scene(self):
        Qt = QT.QtCore.Qt
        self.drag(self.tl, self.x(20), self.x(25), Qt.MiddleButton)
        self.assertEqual(self.calls("scrub_only"), [("scrub_only", 20), ("scrub_only", 25)])
        self.assertFalse(self.calls("set_time"))

    def test_the_transport_buttons(self):
        st = self.strip
        st.transport["nkey"].click()
        self.assertEqual(self.link.s["now"], 30.0)
        st.transport["pkey"].click()
        st.transport["pkey"].click()
        self.assertEqual(self.link.s["now"], 9.0)
        st.transport["end"].click()
        self.assertEqual(self.link.s["now"], 60.0)
        st.transport["pfrm"].click()
        self.assertEqual(self.link.s["now"], 59.0)
        st.transport["start"].click()
        self.assertEqual(self.link.s["now"], 10.0)
        st.transport["back"].click()
        self.assertEqual(self.calls("toggle_play")[-1], ("toggle_play", False))
        st.transport["play"].click()
        self.assertEqual(self.calls("toggle_play")[-1], ("toggle_play", True))

    def test_keys_are_not_read_while_playing(self):
        self.link.s["playing"] = True
        self.link.log.clear()
        self.strip.refresh(keys=True)
        self.assertNotIn(("keys",), self.link.log)
        self.link.s["playing"] = False
        self.strip.refresh()
        self.assertIn(("keys",), self.link.log)

    def test_the_time_job_moves_only_the_playhead(self):
        self.link.s["now"] = 33.0
        self.link.log.clear()
        self.strip.on_time()
        self.assertEqual(self.strip.field.text(), "33")
        self.assertEqual(self.link.log, [])

    def test_a_typed_frame_goes_to_maya(self):
        self.strip.field.setText("27")
        self.strip.field.returnPressed.emit()
        self.assertIn(("set_time", 27.0), self.link.log)

    def test_a_link_that_raises_never_leaves_the_slot(self):
        def boom(*_a):
            raise RuntimeError("no")
        self.link.set_time = boom
        self.strip.field.setText("5")
        self.strip.field.returnPressed.emit()        # printed, not raised


class TimeCallback(Strip):

    def test_maya_s_time_callback_moves_the_playhead_every_frame(self):
        saved = bar._state().get("bar")
        bar._state()["bar"] = self.strip
        self.addCleanup(lambda: bar._state().__setitem__("bar", saved))
        seen = []
        for frame in (13.0, 14.0, 15.0):
            self.link.s["now"] = frame
            bar._time_changed(None, None)
            seen.append(self.strip.field.text())
        self.assertEqual(seen, ["13", "14", "15"])

    def test_a_callback_that_raises_stays_inside(self):
        saved = bar._state().get("bar")
        bar._state()["bar"] = self.strip
        self.addCleanup(lambda: bar._state().__setitem__("bar", saved))
        self.link.now = lambda: 1 / 0
        bar._time_changed(None, None)


class Meter(Strip):

    def test_a_running_meter_clocks_each_step_and_none_runs_otherwise(self):
        state = bar._state()
        saved = state.get("meter")
        self.addCleanup(lambda: state.__setitem__("meter", saved) if saved else state.pop("meter", None))
        state.pop("meter", None)
        self.drag(self.tl, self.x(20), self.x(22))
        state["meter"] = {"stamps": [], "ours": [], "mayas": [], "seconds": 10.0}
        self.drag(self.tl, self.x(30), self.x(33))
        meter = state["meter"]
        self.assertEqual(len(meter["ours"]), 2)
        self.assertTrue(all(ms >= 0 for ms in meter["ours"] + meter["mayas"]))

    def test_the_key_menu_offers_it(self):
        self.assertIn("Measure scrubbing (10 s)", [r[0] for r in self.strip.key_rows(30) if r])


class Cache(Strip):

    def test_the_still_part_is_drawn_once_while_scrubbing(self):
        self.tl.repaint()
        built = self.tl.static_builds
        self.drag(self.tl, self.x(20), self.x(40))
        for f in range(20, 40):
            self.strip.state["now"] = float(f)
            self.tl.repaint()
        self.assertEqual(self.tl.static_builds, built)

    def test_it_is_drawn_again_when_the_keys_or_the_view_change(self):
        self.tl.repaint()
        built = self.tl.static_builds
        self.strip.keys = self.strip.keys + [50.0]
        self.tl.repaint()
        self.assertEqual(self.tl.static_builds, built + 1)
        self.tl.view = (10.0, 30.0)
        self.tl.repaint()
        self.assertEqual(self.tl.static_builds, built + 2)
        self.strip.state["highlight"] = (12, 14)
        self.tl.repaint()
        self.assertEqual(self.tl.static_builds, built + 3)


class Highlight(Strip):

    def test_a_shift_drag_highlights_and_a_click_clears_it(self):
        S = QT.QtCore.Qt.ShiftModifier
        self.drag(self.tl, self.x(40), self.x(22), mods=S)
        self.assertEqual(self.link.s["highlight"], (22, 40))
        self.assertFalse(self.calls("set_time"))
        self.drag(self.tl, self.x(50), self.x(50))
        self.assertIsNone(self.link.s["highlight"])

    def test_a_shift_click_highlights_one_frame(self):
        S = QT.QtCore.Qt.ShiftModifier
        self.drag(self.tl, self.x(30), self.x(30), mods=S)
        self.assertEqual(self.link.s["highlight"], (30, 30))

    def test_dragging_the_highlight_moves_its_keys_once_on_release(self):
        self.strip.state["highlight"] = (22, 40)
        E, Qt = QT.QtCore.QEvent, QT.QtCore.Qt
        self.mouse(self.tl, E.MouseButtonPress, self.x(30), Qt.LeftButton, Qt.LeftButton)
        self.mouse(self.tl, E.MouseMove, self.x(35), Qt.NoButton, Qt.LeftButton)
        self.assertEqual(self.tl.preview, (27, 45))
        self.assertFalse(self.calls("move_keys"))
        self.mouse(self.tl, E.MouseButtonRelease, self.x(35), Qt.LeftButton, Qt.NoButton)
        self.assertEqual(self.calls("move_keys"), [("move_keys", (22, 40), (27, 45))])
        self.assertEqual(self.link.s["highlight"], (27, 45))
        self.assertFalse(self.calls("set_time"))

    def test_dragging_an_edge_scales_toward_the_other_edge(self):
        self.strip.state["highlight"] = (20, 40)
        self.drag(self.tl, self.x(41) - 0.5, self.x(51))      # the right edge: cell 40's end
        self.assertEqual(self.calls("move_keys"), [("move_keys", (20, 40), (20, 50))])

    def test_a_single_frame_highlight_moves_its_key(self):
        self.strip.state["highlight"] = (30, 30)
        self.drag(self.tl, self.x(30), self.x(33))
        self.assertEqual(self.calls("move_keys"), [("move_keys", (30, 30), (33, 33))])


class Range(Strip):

    def range_x(self, frame):
        s = self.strip.state
        return (frame - s["a0"]) / (s["a1"] - s["a0"]) * self.strip.range.width()

    def test_dragging_the_block_slides_the_playback_range(self):
        self.drag(self.strip.range, self.range_x(35), self.range_x(45))
        self.assertEqual((self.link.s["p0"], self.link.s["p1"]), (20, 70))

    def test_dragging_an_edge_resizes_it(self):
        self.drag(self.strip.range, self.range_x(60) - 3, self.range_x(80) - 3)
        self.assertEqual((self.link.s["p0"], self.link.s["p1"]), (10, 80))

    def test_a_typed_range_field(self):
        self.strip.anim_end.setText("150")
        self.strip.anim_end.returnPressed.emit()
        self.assertEqual(self.link.s["a1"], 150)


class Zoom(Strip):

    def test_the_wheel_zooms_about_the_mouse_and_framing_goes_back(self):
        x = self.x(30)
        under = self.tl.track().frame(x)
        local = QT.QtCore.QPointF(x, 10)
        wheel = QT.QtGui.QWheelEvent(local, QT.QtCore.QPointF(self.tl.mapToGlobal(local.toPoint())),
                                     QT.QtCore.QPoint(), QT.QtCore.QPoint(0, 120), QT.QtCore.Qt.NoButton,
                                     QT.QtCore.Qt.NoModifier, QT.QtCore.Qt.NoScrollPhase, False)
        QT.QtWidgets.QApplication.sendEvent(self.tl, wheel)
        t = self.tl.track()
        self.assertLess(t.v1 - t.v0, 50.0)
        self.assertAlmostEqual(t.frame(x), under, places=3)
        self.strip.frame_playback()
        self.assertEqual((self.tl.track().v0, self.tl.track().v1), (10.0, 60.0))


class Menus(Strip):

    def labels(self, rows):
        return [r[0] for r in rows if r is not None]

    def test_the_key_menu(self):
        rows = self.strip.key_rows(30)
        self.assertEqual(rows[0], ("Keys at frame 30", None))
        self.assertIn("Tangents", self.labels(rows))
        self.strip.state["highlight"] = (20, 40)
        self.assertEqual(self.strip.key_rows(30)[0][0], "Keys in 20-40")
        menu, picked = self.strip.menu_rows(self.strip.key_rows(30))
        self.assertTrue(picked)
        menu.deleteLater()

    def test_the_chips_menus_are_checked_where_the_scene_is(self):
        self.assertEqual([r[2] for r in self.strip.fps_rows()], [False, False, True, False, False, False])
        self.assertTrue(self.strip.speed_rows()[0][2])
        self.assertEqual(self.labels(self.strip.layer_rows()), ["BaseAnimation", "Layer1"])
        self.assertEqual(self.labels(self.strip.character_rows()), ["No Character Set", "hero"])
        self.assertEqual(self.labels(self.strip.sound_rows()), ["No sound", "audio1", "Show on the timeline"])

    def test_the_toggles_go_to_maya(self):
        self.strip.loop.click()
        self.assertEqual(self.link.x["loop"], "once")
        self.assertFalse(self.strip.loop.isChecked())
        self.strip.cache.click()
        self.assertFalse(self.link.x["cache"])
        self.strip.bm_add.click()
        self.assertEqual(self.calls("add_bookmark"), [("add_bookmark", None)])
        self.strip.bm_next.click()
        self.assertEqual(self.calls("step_bookmark"), [("step_bookmark", True)])


class Motion(Strip):

    motion = True

    def test_a_key_the_playhead_reaches_lights_up(self):
        self.strip.state["now"] = 10.0
        self.link.s["now"] = 13.0
        self.strip.on_time()
        self.assertIn(12.0, self.tl.reached)
        self.assertNotIn(30.0, self.tl.reached)

    def test_the_opening_starts_small(self):
        self.strip.replay_opening()
        scale, _opacity = self.strip.opening_of(5)
        self.assertLess(scale, 1.0)

    def test_without_motion_nothing_lights(self):
        self.strip.motion = False
        self.link.s["now"] = 13.0
        self.strip.on_time()
        self.assertEqual(self.tl.reached, {})
        self.assertEqual(self.strip.opening_of(5), (1.0, 1.0))


class KeyEffects(Strip):
    """A key set flashes a round glow, a key deleted throws sparks (2026-10-17)."""

    motion = True

    def kinds(self):
        return [i["kind"] for i in self.strip.fx.items]

    def paint(self):
        self.strip.fx.grab()
        self.assertFalse(getattr(self.strip.fx, "_failed", False))

    def test_a_key_set_flashes(self):
        self.link.k = ([0.0, 6.0, 12.0, 20.0, 30.0, 40.0], [9.0])
        self.strip.refresh(keys=True)
        self.assertEqual(self.kinds(), ["set"])
        self.paint()

    def test_a_key_deleted_throws_sparks(self):
        self.link.k = ([0.0, 6.0, 12.0, 40.0], [9.0])
        self.strip.refresh(keys=True)
        self.assertEqual(self.kinds(), ["delete"])
        self.paint()

    def test_a_reload_or_a_snap_is_no_edit(self):
        self.link.k = ([float(f) for f in range(0, 100, 3)], [9.0])
        self.strip.refresh(keys=True)
        self.assertEqual(self.kinds(), [])
        self.link.k = ([0.0, 6.5], [9.0])
        self.strip.refresh(keys=True)
        self.strip.fx.items[:] = []
        self.link.k = ([0.0, 7.0], [9.0])
        self.strip.refresh(keys=True)
        self.assertEqual(self.kinds(), [])

    def test_moving_keys_is_no_set_and_delete(self):
        self.strip.state["highlight"] = (30, 30)
        self.link.k = ([0.0, 6.0, 12.0, 35.0, 40.0], [9.0])
        self.drag(self.tl, self.x(30), self.x(35))
        self.assertEqual(self.kinds(), [])

    def test_the_effects_end(self):
        self.link.k = ([0.0, 6.0, 12.0, 20.0, 30.0, 40.0], [9.0])
        self.strip.refresh(keys=True)
        self.assertFalse(self.strip.fx.busy(self.strip.clock() + 5000))

    def test_without_motion_nothing_starts(self):
        self.strip.motion = False
        self.link.k = ([0.0, 6.0, 12.0, 20.0, 40.0], [9.0])
        self.strip.refresh(keys=True)
        self.assertEqual(self.kinds(), [])


class PlayAndTrail(Strip):
    """Play pressed closes a frame round the bar; the cells the playhead leaves
    glow and fade, scrubbing and playing (2026-10-17)."""

    motion = True

    def test_a_scrub_leaves_fading_cells(self):
        self.drag(self.tl, self.x(20), self.x(25))
        self.assertTrue(self.tl.trail)
        self.tl.grab()
        self.assertFalse(getattr(self.tl, "_failed", False))
        later = self.strip.clock() + 5000
        self.strip.clock = lambda: later
        self.tl.step(16)
        self.assertEqual(self.tl.trail, {})

    def test_playback_leaves_fading_cells(self):
        self.strip.state["playing"] = True
        self.link.s["playing"] = True
        for now in (13.0, 14.0, 15.0):
            self.link.s["now"] = now
            self.strip.on_time()
        self.assertEqual(sorted(self.tl.trail), [12, 13, 14])

    def test_a_time_change_while_still_leaves_no_trail(self):
        self.link.s["now"] = 20.0
        self.strip.on_time()
        self.assertEqual(self.tl.trail, {})

    def test_play_closes_a_frame_round_the_bar(self):
        self.strip.play.click()
        self.assertIsNotNone(self.tl.play_at)
        self.assertTrue(self.tl.busy(self.strip.clock()))
        self.tl.grab()
        self.assertFalse(getattr(self.tl, "_failed", False))

    def test_stopping_closes_no_frame(self):
        self.strip.state["playing"] = True
        self.link.s["playing"] = True
        self.strip.refresh()
        self.tl.play_at = None
        self.strip.play.click()
        self.assertIsNone(self.tl.play_at)

    def test_without_motion_neither(self):
        self.strip.motion = False
        self.drag(self.tl, self.x(20), self.x(25))
        self.strip.play.click()
        self.assertEqual(self.tl.trail, {})
        self.assertIsNone(self.tl.play_at)


if __name__ == "__main__":
    unittest.main()
