"""Maya's status-line tools on the skill bar's page row (2026-10-20): the pure table and layout,
the scene half on a fake cmds, the widget offscreen.

Spec: docs/superpowers/specs/2026-10-20-skill-bar-status-tools-design.md
"""
import os
import subprocess
import sys
import unittest
import xml.dom.minidom

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from maya_skillbar import status, statusscene

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SkeldarAnim")


class Pure(unittest.TestCase):

    def test_imports_nothing_but_the_stdlib(self):
        code = ("import sys; sys.path.insert(0, %r); import maya_skillbar.status; "
                "bad = [m for m in sys.modules if m.split('.')[0] in ('maya', 'PySide6', 'shiboken6')]; "
                "print(bad)" % PLUGIN)
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=PLUGIN)
        self.assertEqual(out.stdout.strip(), "[]", out.stderr)

    def test_every_icon_is_valid_svg(self):
        for name in status.ICONS:
            xml.dom.minidom.parseString(status.svg(name, "#fff"))

    def test_every_button_has_an_icon(self):
        for mode in (status.OBJECT, status.COMPONENT, status.HIERARCHY):
            for _g, _k, _l, icon in status.buttons(mode):
                self.assertIn(icon, status.ICONS)

    def test_the_object_mode_reads_as_the_status_line(self):
        keys = [(g, k) for g, k, _l, _i in status.buttons(status.OBJECT)]
        self.assertEqual(keys[:8], [("mask", k) for k in ("Marker", "Joint", "Curve", "Surface", "Deformer",
                                                          "Dynamic", "Rendering", "Other")])
        self.assertEqual(keys[8:10], [("select", "lock"), ("select", "hilite")])
        self.assertEqual([k for g, k in keys if g == "snap"], ["grid", "curve", "point", "viewPlane", "meshCenter"])
        self.assertEqual(keys[-1], ("live", "live"))

    def test_the_layout_is_packed_against_the_right_edge(self):
        for ui in (1.0, 1.5):
            rects = status.layout(500.0, status.OBJECT, ui)
            last = rects[-1]
            self.assertAlmostEqual(last[2] + last[3], 500.0 - status.END_PAD * ui)
            for a, b in zip(rects, rects[1:]):
                self.assertGreater(b[2], a[2] + a[3] - 1e-9)
            self.assertAlmostEqual(status.width_of(status.OBJECT, ui), 500.0 - rects[0][2])

    def test_dividers_stand_between_groups_and_not_before_make_live(self):
        rects = status.layout(500.0, status.OBJECT)
        self.assertEqual(len(status.dividers(rects)), 2)
        hier = status.layout(500.0, status.HIERARCHY)
        self.assertLess(status.width_of(status.HIERARCHY), status.width_of(status.OBJECT))
        self.assertEqual(len(status.dividers(hier)), 2)

    def test_hit(self):
        rects = status.layout(500.0, status.OBJECT)
        g, k, x, w = rects[3]
        self.assertEqual(status.hit(x + w / 2, rects), (g, k))
        self.assertIsNone(status.hit(rects[0][2] - 3, rects))

    def test_mask_state_reads_maya_s_partial_icon(self):
        self.assertEqual(status.mask_state(False, "pickJointObj.png"), "")
        self.assertEqual(status.mask_state(True, "pickJointObj.png"), "on")
        self.assertEqual(status.mask_state(True, "pickJointObjPartial.png"), "part")

    def test_flags_state(self):
        self.assertEqual(status.flags_state([]), "")
        self.assertEqual(status.flags_state([0, 0]), "")
        self.assertEqual(status.flags_state([1, 0]), "part")
        self.assertEqual(status.flags_state([1, 1]), "on")

    def test_a_click_on_on_or_part_turns_the_group_off(self):
        cmd = 'setObjectPickMask "Joint" #1'
        self.assertEqual(status.pressed(cmd, "on"), 'setObjectPickMask "Joint" 0')
        self.assertEqual(status.pressed(cmd, "part"), 'setObjectPickMask "Joint" 0')
        self.assertEqual(status.pressed(cmd, ""), 'setObjectPickMask "Joint" 1')

    def test_highlight_is_pressed_while_highlighting_is_off(self):
        st = status.blank_state()
        self.assertFalse(status.lit("select", "hilite", st))
        st["hilite"] = False
        self.assertTrue(status.lit("select", "hilite", st))

    def test_menu_rows_leave_out_unlabelled_rows(self):
        rows = status.menu_rows(["A", "", "B"], [1, 0, 0], ["a #1", "", "b #1"])
        self.assertEqual(rows, [("A", True, "a #1"), ("B", False, "b #1")])


class FakeCmds(object):
    """The calls statusscene makes."""

    def __init__(self, controls=None, mode="object"):
        self.controls = controls if controls is not None else {}
        self._mode = mode
        self.flags = {}
        self.prefs = {"xformNoSelect": False, "allowHiliteSelection": True}
        self.snaps = {f: False for _k, _l, _i, f in status.SNAPS}
        self.calls = []

    def selectMode(self, q=False, **kw):
        flag = list(kw)[0]
        return {"component": self._mode == "component", "hierarchical": self._mode == "hierarchy",
                "root": True}.get(flag, False)

    def iconTextCheckBox(self, name, exists=False, q=False, e=False, value=None, image1=False):
        if exists:
            return name in self.controls
        if e:
            self.calls.append(("edit", name, value))
            return None
        v, img = self.controls[name]
        return img if image1 else v

    def selectType(self, q=False, **kw):
        return self.flags.get(list(kw)[0], True)

    def selectPref(self, q=False, **kw):
        flag = list(kw)[0]
        if q:
            return self.prefs[flag]
        self.prefs[flag] = kw[flag]
        self.calls.append(("selectPref", flag, kw[flag]))

    def snapMode(self, q=False, **kw):
        flag = list(kw)[0]
        if q:
            return self.snaps[flag]
        self.snaps[flag] = kw[flag]
        self.calls.append(("snapMode", flag, kw[flag]))

    def makeLive(self, q=False):
        return []


class FakeMel(object):

    def __init__(self):
        self.ran = []

    def eval(self, text):
        self.ran.append(text)
        return 0


class Scene(unittest.TestCase):

    def setUp(self):
        self.cmds, self.mel = FakeCmds(), FakeMel()
        self.old = statusscene._cmds, statusscene._mel
        statusscene._cmds = lambda: self.cmds
        statusscene._mel = lambda: self.mel
        self.addCleanup(self._restore)

    def _restore(self):
        statusscene._cmds, statusscene._mel = self.old

    def test_masks_read_off_maya_s_controls(self):
        self.cmds.controls = {"objSelHandleBtn": (True, "pickHandlesObj.png"),
                              "objSelJointBtn": (False, "pickJointObj.png"),
                              "objSelCurveBtn": (True, "pickCurveObjPartial.png")}
        st = statusscene.MayaStatus().read()
        self.assertEqual(st["masks"]["Marker"], "on")
        self.assertEqual(st["masks"]["Joint"], "")
        self.assertEqual(st["masks"]["Curve"], "part")

    def test_without_a_status_line_the_flags_decide(self):
        self.cmds.flags = {"lattice": True, "cluster": False}
        st = statusscene.MayaStatus().read()
        self.assertEqual(st["masks"]["Deformer"], "part")
        self.assertEqual(st["masks"]["Joint"], "on")

    def test_a_mask_press_runs_maya_s_command(self):
        self.cmds.controls = {"objSelJointBtn": (True, "pickJointObj.png")}
        statusscene.MayaStatus().press("mask", "Joint")
        self.assertEqual(self.mel.ran, ['setObjectPickMask "Joint" 0'])

    def test_component_mode_runs_the_component_command(self):
        self.cmds._mode = "component"
        self.cmds.flags = {"facet": False, "surfaceFace": False}
        statusscene.MayaStatus().press("mask", "Facet")
        self.assertEqual(self.mel.ran, ['setComponentPickMask "Facet" 1'])

    def test_snaps_lock_and_highlight(self):
        model = statusscene.MayaStatus()
        model.press("snap", "grid")
        self.assertTrue(self.cmds.snaps["grid"])
        model.press("select", "lock")
        self.assertTrue(self.cmds.prefs["xformNoSelect"])
        model.press("select", "hilite")
        self.assertFalse(self.cmds.prefs["allowHiliteSelection"])
        st = model.read()
        self.assertTrue(st["snaps"]["grid"] and st["lock"] and not st["hilite"])

    def test_make_live_runs_maya_s_proc(self):
        statusscene.MayaStatus().press("live", "live")
        self.assertEqual(self.mel.ran, ["statusLineSetMakeLive"])

    def test_a_menu_row_runs_with_its_new_value(self):
        model = statusscene.MayaStatus()
        model.run("selectType -handle #1", True)
        model.run("selectType -ikHandle #1", False)
        model.run("statusLineAddSelToLive", None)
        self.assertEqual(self.mel.ran, ["selectType -handle 0", "selectType -ikHandle 1", "statusLineAddSelToLive"])


try:
    import maya_hubqt
    QT = maya_hubqt.qt()
except Exception:                                            # noqa: BLE001
    QT = None


@unittest.skipIf(QT is None, "no Qt")
class Widget(unittest.TestCase):

    def setUp(self):
        import maya_hubstyle
        from maya_skillbar import look
        from maya_timebar import bar
        from tests.test_skillbar_grid import SkillLink
        self.app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
        self.link = SkillLink(look.defaults())
        self.strip = bar.make(self.link, 1.0, maya_hubstyle.TOKENS, motion=False)
        self.strip.resize(1200, 160)
        self.strip.move(3000, 3000)
        self.strip.show()
        self.app.processEvents()
        self.addCleanup(self.strip.deleteLater)
        self.tools = self.strip.tabs.tools
        self.model = self.tools.model

    def mouse(self, widget, kind, x, y, button, buttons):
        local = QT.QtCore.QPointF(x, y)
        event = QT.QtGui.QMouseEvent(kind, local, QT.QtCore.QPointF(widget.mapToGlobal(local.toPoint())),
                                     button, buttons, QT.QtCore.Qt.NoModifier)
        QT.QtWidgets.QApplication.sendEvent(widget, event)

    def click(self, x, button=None):
        E, Qt = QT.QtCore.QEvent, QT.QtCore.Qt
        button = button or Qt.LeftButton
        y = self.tools.height() / 2.0
        self.mouse(self.tools, E.MouseButtonPress, x, y, button, button)
        self.mouse(self.tools, E.MouseButtonRelease, x, y, button, Qt.NoButton)

    def centre_of(self, group, key):
        for g, k, x, w in self.tools.rects():
            if (g, k) == (group, key):
                return x + w / 2.0
        raise KeyError(key)

    def test_a_fake_link_reads_in_memory(self):
        self.assertIsInstance(self.model, status.MemoryStatus)

    def test_the_tools_stand_at_the_row_s_right_and_the_tabs_leave_them_room(self):
        tabs = self.strip.tabs
        self.assertEqual(self.tools.geometry().right() + 1, tabs.width())
        last = tabs.rects()[-1]
        self.assertLessEqual(last[0] + last[1], tabs.width() - self.tools.room() + 0.5)

    def test_narrow_the_tabs_fold_to_keys(self):
        self.strip.resize(700, 160)
        self.app.processEvents()
        rects = self.strip.tabs.rects()
        self.assertLessEqual(rects[-1][0] + rects[-1][1], self.strip.tabs.width() - self.tools.room() + 0.5)

    def test_a_click_presses_its_button(self):
        self.click(self.centre_of("snap", "grid"))
        self.assertIn(("press", "snap", "grid"), self.model.log)
        self.assertTrue(self.tools.state["snaps"]["grid"])
        self.click(self.centre_of("mask", "Joint"))
        self.assertEqual(self.tools.state["masks"]["Joint"], "")

    def test_the_right_button_shows_the_mask_s_types(self):
        seen = {}

        def fake_exec(menu, *_a):
            actions = menu.actions()
            seen["labels"] = [a.text() for a in actions]
            seen["checked"] = [a.isChecked() for a in actions]
            return actions[1]
        self.tools.exec_menu = fake_exec
        self.click(self.centre_of("mask", "Marker"), QT.QtCore.Qt.RightButton)
        self.assertEqual(seen["labels"], ["Type A", "Type B"])
        self.assertEqual(seen["checked"], [True, False])
        self.assertIn(("run", "selectType -b #1", False), self.model.log)

    def test_a_mode_change_read_by_the_poll_places_the_tools_again(self):
        wide = self.tools.width()
        self.model.state = status.blank_state(status.HIERARCHY)
        self.tools.poll()
        self.assertLess(self.tools.width(), wide)
        self.assertEqual(self.tools.geometry().right() + 1, self.strip.tabs.width())

    def test_it_paints_a_lit_button_in_the_accent(self):
        self.model.state["snaps"]["point"] = True
        self.tools.poll()
        image = QT.QtGui.QImage(self.tools.size(), QT.QtGui.QImage.Format_ARGB32)
        image.fill(0)
        self.tools.render(image)
        for g, k, x, w in self.tools.rects():
            if (g, k) == ("snap", "point"):
                y = int(self.tools.height() / 2)
                reds = [image.pixelColor(int(x) + d, y).red() for d in range(0, 3)]
                face = image.pixelColor(int(x + w / 2), int(y - w / 2 + 2))
        self.assertGreater(max(reds), 150, reds)            # the accent outline
        self.assertEqual(face.name(), "#383a41")            # the current tab's face


if __name__ == "__main__":
    unittest.main()
