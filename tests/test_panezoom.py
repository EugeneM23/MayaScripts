"""Space's tap flown in and out (2026-10-22): the timing, and the overlay painted offscreen."""

import os
import subprocess
import sys
import unittest

import maya_panezoom_rules as rules

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SkeldarAnim")

QUAD = (0.0, 0.0, 200.0, 150.0)
FULL = (0.0, 0.0, 400.0, 300.0)


class Rules(unittest.TestCase):
    def test_in_starts_on_the_quarter_and_lands_on_the_whole(self):
        a = rules.frame(rules.IN, 0, QUAD, FULL)
        self.assertEqual(a["rect"], QUAD)
        self.assertEqual(a["dim"], 0.0)
        self.assertAlmostEqual(a["alpha"], 1.0)
        b = rules.frame(rules.IN, rules.MOVE_MS[rules.IN], QUAD, FULL)
        self.assertEqual(b["rect"], FULL)
        self.assertAlmostEqual(b["dim"], rules.DIM)
        self.assertAlmostEqual(b["ring"], 0.0)

    def test_out_brightens_the_others_as_it_lands(self):
        a = rules.frame(rules.OUT, 0, FULL, QUAD)
        self.assertAlmostEqual(a["dim"], rules.DIM)
        b = rules.frame(rules.OUT, rules.MOVE_MS[rules.OUT], FULL, QUAD)
        self.assertEqual(b["rect"], QUAD)
        self.assertAlmostEqual(b["dim"], 0.0)

    def test_the_move_is_monotonic_and_eases_out(self):
        last = -1.0
        for ms in range(0, 341, 10):
            w = rules.frame(rules.IN, ms, QUAD, FULL)["rect"][2]
            self.assertGreaterEqual(w, last)
            last = w
        first = rules.frame(rules.IN, 34, QUAD, FULL)["rect"][2] - 200.0
        late = 400.0 - rules.frame(rules.IN, 306, QUAD, FULL)["rect"][2]
        self.assertGreater(first, late * 10)

    def test_it_fades_after_landing_and_is_done(self):
        move = rules.MOVE_MS[rules.IN]
        half = rules.frame(rules.IN, move + rules.FADE_MS / 2, QUAD, FULL)
        self.assertAlmostEqual(half["alpha"], 0.5)
        self.assertFalse(half["done"])
        self.assertTrue(rules.frame(rules.IN, rules.total_ms(rules.IN), QUAD, FULL)["done"])

    def test_short_enough(self):
        self.assertLessEqual(rules.total_ms(rules.IN), 500)
        self.assertLessEqual(rules.total_ms(rules.OUT), 500)

    def test_the_direction_comes_from_the_layout(self):
        self.assertEqual(rules.kind_of("single"), rules.OUT)
        self.assertEqual(rules.kind_of("quad"), rules.IN)

    def test_the_view_inside_a_panel_spreads_with_its_bars(self):
        panel = (0.0, 0.0, 200.0, 150.0)
        view = (0.0, 40.0, 200.0, 110.0)          # a 40 px menu + icon bar on top
        m = rules.margins(panel, view)
        self.assertEqual(m, (0.0, 40.0, 0.0, 0.0))
        self.assertEqual(rules.inset(FULL, m), (0.0, 40.0, 400.0, 260.0))

    def test_the_old_view_turns_into_the_new_one_as_it_flies(self):
        move = rules.MOVE_MS[rules.IN]
        self.assertEqual(rules.mix(0, rules.IN), 0.0)
        self.assertAlmostEqual(rules.mix(move / 2, rules.IN), 0.5)
        self.assertEqual(rules.mix(move, rules.IN), 1.0)

    def test_the_smallest_picture_still_big_enough(self):
        widths = [1600, 800, 400, 200]
        self.assertEqual(rules.mip_for(widths, 1700), 0)
        self.assertEqual(rules.mip_for(widths, 790), 1)
        self.assertEqual(rules.mip_for(widths, 401), 1)
        self.assertEqual(rules.mip_for(widths, 50), 3)

    def test_the_rules_import_nothing_of_maya_or_qt(self):
        code = ("import sys, maya_panezoom_rules; "
                "bad = [m for m in sys.modules if m.split('.')[0] in ('maya', 'PySide6')]; "
                "print(bad)")
        out = subprocess.run([sys.executable, "-c", code], cwd=PLUGIN, capture_output=True,
                             text=True)
        self.assertEqual(out.stdout.strip(), "[]", out.stderr)


try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:            # pragma: no cover
    QtWidgets = None


@unittest.skipIf(QtWidgets is None, "no Qt")
class Painted(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def picture(self, colour):
        img = QtGui.QImage(400, 300, QtGui.QImage.Format_ARGB32)
        img.fill(QtGui.QColor(colour))
        return img

    def zoom(self, kind, now):
        import maya_panezoom
        clock = {"t": 0.0}
        before = self.picture("#2060c0")
        after = self.picture("#30a040")
        z = maya_panezoom.Zoom(kind, before, before, None, None, "modelPanel4",
                               clock=lambda: clock["t"])
        if kind == rules.IN:
            z.setup(after, QUAD, FULL)
        else:
            z.setup(after, FULL, QUAD)
        z.started = 0.0
        clock["t"] = now / 1000.0
        return z

    def render(self, z):
        out = QtGui.QImage(400, 300, QtGui.QImage.Format_ARGB32)
        out.fill(QtCore.Qt.transparent)
        p = QtGui.QPainter(out)
        z.paint(p, QtCore.QRectF(0, 0, 400, 300))
        p.end()
        return out

    def test_in_the_quarter_grows_over_the_dimmed_rest(self):
        img = self.render(self.zoom(rules.IN, 120))
        inside = img.pixelColor(20, 20)
        outside = img.pixelColor(395, 295)
        self.assertGreater(inside.blue(), outside.blue())     # the piece over the dimmed back

    def test_out_lands_on_the_new_layout(self):
        img = self.render(self.zoom(rules.OUT, rules.MOVE_MS[rules.OUT] + 1))
        far = img.pixelColor(350, 250)                         # outside the quarter: the after
        self.assertGreater(far.green(), far.blue())

    def test_it_ends_transparent(self):
        z = self.zoom(rules.IN, rules.total_ms(rules.IN) + 5)
        self.assertTrue(z.state()["done"])
        self.assertEqual(self.render(z).pixelColor(200, 150).alpha(), 0)

    def test_held_while_switching_shows_the_old_picture(self):
        z = self.zoom(rules.IN, 0)
        z.hold = True
        self.assertEqual(self.render(z).pixelColor(300, 200).name(), "#2060c0")

    def test_only_the_area_is_painted(self):
        import maya_panezoom
        clock = {"t": 0.12}
        before = self.picture("#2060c0")
        z = maya_panezoom.Zoom(rules.IN, before, before, None, None, "p",
                               clock=lambda: clock["t"], area=(0.0, 40.0, 400.0, 260.0))
        z.setup(self.picture("#30a040"), (0.0, 40.0, 200.0, 110.0), (0.0, 40.0, 400.0, 260.0))
        z.started = 0.0
        out = QtGui.QImage(400, 260, QtGui.QImage.Format_ARGB32)
        out.fill(QtCore.Qt.transparent)
        p = QtGui.QPainter(out)
        z.paint(p, QtCore.QRectF(0, 0, 400, 260))
        p.end()
        self.assertEqual(out.pixelColor(300, 200).alpha(), 255)  # the whole area is drawn
        self.assertEqual(out.pixelColor(0, 0).alpha(), 255)

    def test_a_big_picture_is_halved_into_mips(self):
        import maya_panezoom
        img = QtGui.QImage(1600, 900, QtGui.QImage.Format_RGB32)
        img.fill(QtGui.QColor("#808080"))
        widths = [m.width() for m in maya_panezoom._mips(img)]
        self.assertEqual(widths, [1600, 800, 400, 200])

    def test_the_real_overlay_fades_by_its_window_not_its_paint(self):
        z = self.zoom(rules.IN, rules.MOVE_MS[rules.IN] + rules.FADE_MS / 2)
        z.window_fade = True
        self.assertEqual(self.render(z).pixelColor(200, 150).alpha(), 255)

    def test_nowhere_to_fly_fades_the_old_picture(self):
        import maya_panezoom
        z = maya_panezoom.Zoom(rules.OUT, self.picture("#2060c0"), None, FULL, None, "p",
                               clock=lambda: 0.1)
        z.setup(self.picture("#30a040"), FULL, None)
        z.started = 0.0
        self.assertLess(z.state()["alpha"], 1.0)
        self.assertGreater(z.state()["alpha"], 0.0)


@unittest.skipIf(QtWidgets is None, "no Qt")
class Tap(unittest.TestCase):
    def test_animations_off_switches_plainly(self):
        import maya_panezoom
        calls = []
        old = (maya_panezoom._animations, maya_panezoom.switch_plain)
        maya_panezoom._animations = lambda: False
        maya_panezoom.switch_plain = lambda panel: calls.append(panel)
        try:
            self.assertEqual(maya_panezoom.tap("modelPanel4"), "instant")
        finally:
            maya_panezoom._animations, maya_panezoom.switch_plain = old
        self.assertEqual(calls, ["modelPanel4"])

    def test_a_failure_before_the_switch_switches_once(self):
        import maya_panezoom
        calls = []
        old = (maya_panezoom._animations, maya_panezoom.switch_plain, maya_panezoom.Zoom.start)
        maya_panezoom._animations = lambda: True
        maya_panezoom.switch_plain = lambda panel: calls.append(panel)
        maya_panezoom.Zoom.start = classmethod(lambda cls, panel: None)
        try:
            self.assertEqual(maya_panezoom.tap("modelPanel4"), "instant")
        finally:
            (maya_panezoom._animations, maya_panezoom.switch_plain,
             maya_panezoom.Zoom.start) = old
        self.assertEqual(calls, ["modelPanel4"])

    def test_a_failure_after_the_switch_never_switches_again(self):
        import maya_panezoom
        calls = []

        def start(cls, panel):
            maya_panezoom._state()["switched"] = True
            calls.append("switched-inside")
            raise RuntimeError("capture")

        old = (maya_panezoom._animations, maya_panezoom.switch_plain, maya_panezoom.Zoom.start)
        maya_panezoom._animations = lambda: True
        maya_panezoom.switch_plain = lambda panel: calls.append(panel)
        maya_panezoom.Zoom.start = classmethod(start)
        try:
            import io
            import contextlib
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(maya_panezoom.tap("modelPanel4"), "instant")
        finally:
            (maya_panezoom._animations, maya_panezoom.switch_plain,
             maya_panezoom.Zoom.start) = old
        self.assertEqual(calls, ["switched-inside"])


if __name__ == "__main__":
    unittest.main()
