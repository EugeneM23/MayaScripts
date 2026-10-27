"""The viewport bar's whole pass on a stand-in panel offscreen (maya_viewportbar): which controls are the bar's,
the icons written into our folder and the buttons pointed there, the sheet set; everything given back; the
watch telling a rebuilt bar from the one skinned; the switch with a UI."""

import os
import shutil
import sys
import tempfile
import types
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import maya_viewportbar as vb

BAR = "MainPane|modelPanel4|modelPanel4|modelEditorIconBar"
SEP = BAR + "|flowLayout6|iconTextButton34"
CAMERA = BAR + "|flowLayout6|formLayout47|CameraBtn"
CM = BAR + "|flowLayout6|formLayout50|cmToggle"
OTHER = "MainPane|modelPanel1|modelPanel1|modelEditorIconBar|flowLayout2|formLayout3|GridBtn"


def _app():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


class Cmds(object):
    """The UI half of maya.cmds the pass reads: panels, their bars, every image control and its images."""

    def __init__(self, app_dir):
        self.vars = {}
        self.batch = False
        self.app_dir = app_dir
        self.panel_names = ["modelPanel4"]
        self.bars = {"modelPanel4": BAR, "modelPanel1": None}
        self.controls = {"iconTextButton": [SEP, CAMERA, OTHER], "iconTextCheckBox": [],
                         "symbolCheckBox": [CM], "symbolButton": []}
        self.images = {(SEP, "image1"): "ShortOpenBar.png", (CAMERA, "image1"): "Camera.png",
                       (OTHER, "image1"): "Grid.png", (CM, "onImage"): "rvViewingPipelineOn.png",
                       (CM, "offImage"): "rvViewingPipelineOff.png"}
        self.broken = set()

    def optionVar(self, exists=None, query=None, intValue=None):  # noqa: N802
        if exists is not None:
            return exists in self.vars
        if query is not None:
            return self.vars[query]
        self.vars[intValue[0]] = intValue[1]

    def about(self, batch=False, version=False):
        return self.batch if batch else "2027"

    def internalVar(self, userAppDir=False):  # noqa: N802,N803
        return self.app_dir

    def mayaDpiSetting(self, **_kw):  # noqa: N802
        return 1.0

    def getPanel(self, type=None):  # noqa: N802,A002
        if type == "raise":
            raise RuntimeError
        return list(self.panel_names)

    def lsUI(self, type=None, long=False):  # noqa: N802,A002
        return list(self.controls.get(type, []))

    def modelPanel(self, panel, query=False, barLayout=False):  # noqa: N802,N803
        bar = self.bars.get(panel, "raise")
        if bar == "raise":
            raise RuntimeError("no panel " + panel)
        return bar

    def _image(self, control, query=False, edit=False, **flags):
        flag = list(flags)[0]
        if (control, flag) in self.broken:
            raise RuntimeError("no such control")
        if query:
            return self.images.get((control, flag))
        self.images[(control, flag)] = flags[flag]

    iconTextButton = iconTextCheckBox = symbolCheckBox = symbolButton = _image


class StandIn(unittest.TestCase):
    """A panel built like Maya's: its bar's flowLayout holding two groups and a collapse handle."""

    def setUp(self):
        from PySide6 import QtWidgets
        self.app = _app()
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.cmds = Cmds(self.root)
        saved = getattr(sys, vb.STATE, None)
        if hasattr(sys, vb.STATE):
            delattr(sys, vb.STATE)

        def put_back():
            vb.unwatch()
            if saved is None:
                if hasattr(sys, vb.STATE):
                    delattr(sys, vb.STATE)
            else:
                setattr(sys, vb.STATE, saved)
        self.addCleanup(put_back)
        self.panel = QtWidgets.QWidget()
        self.panel.setObjectName("modelPanel4")
        self.panel.setStyleSheet("/* maya's */")
        self.addCleanup(self.panel.deleteLater)
        self.flow = QtWidgets.QWidget(self.panel)
        self.flow.setObjectName("flowLayout6")
        self.sep = QtWidgets.QPushButton(self.flow)
        self.sep.setObjectName("iconTextButton34")
        self.group = QtWidgets.QWidget(self.flow)
        self.group.setObjectName("formLayout47")
        self.widgets = {"modelPanel4": self.panel}
        for target, value in (("_cmds", lambda: self.cmds),
                              ("_panel_widget", lambda name: self.widgets.get(name))):
            patcher = mock.patch.object(vb, target, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def dest(self):
        return os.path.join(self.root, "2027", vb.FOLDER)


class Listing(StandIn):
    def test_our_folder_is_under_mayas_version(self):
        self.assertEqual(vb.folder(), os.path.normpath(self.dest()))

    def test_the_panels_and_a_maya_that_cannot_list_them(self):
        self.assertEqual(vb.panels(), ["modelPanel4"])
        self.cmds.getPanel = mock.Mock(side_effect=RuntimeError("no UI"))
        self.assertEqual(vb.panels(), [])

    def test_a_bars_controls_are_those_under_its_bar_only(self):
        listed = vb._all_controls()
        self.assertEqual(sorted(listed), sorted(kind for kind, _ in vb.KINDS))
        controls = vb.bar_controls("modelPanel4", listed)
        self.assertEqual(sorted(c for _k, _f, c in controls), sorted([SEP, CAMERA, CM]))
        self.assertIn(("symbolCheckBox", ("onImage", "offImage"), CM), controls)
        self.assertEqual(vb.bar_controls("modelPanel4"), controls)     # lists for itself

    def test_a_panel_with_no_bar_or_gone_has_none(self):
        self.assertEqual(vb.bar_controls("modelPanel1"), [])
        self.assertEqual(vb.bar_controls("modelPanel9"), [])

    def test_the_images_are_bare_names_wherever_they_point(self):
        self.cmds.images[(CAMERA, "image1")] = "C:\\x\\SkeldarViewportIcons\\Camera.png"
        self.cmds.images[(CM, "offImage")] = ""
        self.cmds.broken.add((SEP, "image1"))
        names = vb._images(vb.bar_controls("modelPanel4"))
        self.assertEqual(names, {"Camera.png", "rvViewingPipelineOn.png"})


class Pass(StandIn):
    def test_apply_all_writes_our_icons_points_the_buttons_and_sets_the_sheet(self):
        self.assertEqual(vb.apply_all(), 1)
        dest = os.path.normpath(self.dest())
        written = set(os.listdir(dest))
        self.assertTrue({"Camera.png", "Camera_150.png", "Camera_200.png", vb.CHEVRON} <= written, written)
        # Maya's resource is recoloured when the process has one: offscreen it has none, unless an
        # earlier test in the same process registered it (the whole suite does)
        from PySide6 import QtGui
        maya_has = not QtGui.QImage(":/ShortOpenBar.png").isNull()
        self.assertEqual("ShortOpenBar.png" in written, maya_has)
        have = frozenset(n for n in written if n.endswith(".png"))
        self.assertEqual(self.cmds.images[(CAMERA, "image1")], vb.pointed("Camera.png", dest, have, True))
        self.assertTrue(self.cmds.images[(CAMERA, "image1")].startswith(dest.replace("\\", "/"))
                        or self.cmds.images[(CAMERA, "image1")].startswith(dest))
        self.assertEqual(self.cmds.images[(OTHER, "image1")], "Grid.png")    # another panel's
        self.assertEqual(self.panel.property(vb.MARK), "1")
        self.assertEqual(self.panel.styleSheet(), vb.sheet(1.0, os.path.join(dest, vb.CHEVRON)))
        self.assertEqual(self.sep.property("skeldarVpSep"), "1")
        self.assertEqual(self.group.styleSheet(), vb.group_sheet("formLayout47", 1.0))
        state = getattr(sys, vb.STATE)
        self.assertEqual(state["skinned"], {"modelPanel4"})
        self.assertEqual(state["seen"], {"modelPanel4": vb.signature(self.panel)})

    def test_a_panel_that_fails_is_left_and_the_rest_counted(self):
        from PySide6 import QtWidgets
        second = QtWidgets.QWidget()
        self.addCleanup(second.deleteLater)
        self.widgets["modelPanel2"] = second
        self.cmds.panel_names = ["modelPanel4", "modelPanel2"]
        real = vb.skin_panel

        def picky(panel, *args, **kwargs):
            if panel == "modelPanel2":
                raise RuntimeError("a widget Maya deleted")
            return real(panel, *args, **kwargs)
        with mock.patch.object(vb, "skin_panel", picky):
            self.assertEqual(vb.apply_all(), 1)
        self.assertEqual(self.panel.property(vb.MARK), "1")

    def test_remove_all_gives_every_image_and_sheet_back(self):
        vb.apply_all()
        self.assertEqual(vb.remove_all(), 1)
        self.assertEqual(self.cmds.images[(CAMERA, "image1")], "Camera.png")
        self.assertEqual(self.panel.styleSheet(), "/* maya's */")
        self.assertIsNone(self.panel.property(vb.MARK))
        self.assertEqual(self.group.styleSheet(), "")
        state = getattr(sys, vb.STATE)
        self.assertEqual((state["skinned"], state["seen"]), (set(), {}))

    def test_remove_all_with_no_folder_still_gives_the_sheets_back(self):
        vb.skin_panel("modelPanel4", text="X")
        self.assertEqual(vb.remove_all(), 1)
        self.assertEqual(self.panel.styleSheet(), "/* maya's */")

    def test_a_panel_whose_widget_is_gone_is_given_its_images_back(self):
        vb.apply_all()
        self.widgets.clear()
        self.assertEqual(vb.remove_all(), 0)
        self.assertEqual(self.cmds.images[(CAMERA, "image1")], "Camera.png")


class FlowOnly(object):
    """A widget whose findChildren takes no name filter (an older binding)."""

    def __init__(self, names, mark=None):
        self.names = names
        self.mark = mark

    def findChildren(self, *args):  # noqa: N802
        if len(args) > 1:
            raise TypeError("no overload")
        return [types.SimpleNamespace(objectName=lambda n=n: n) for n in self.names]

    def property(self, name):
        return self.mark


class Watch(StandIn):
    def test_a_signature_is_the_mark_and_the_bars_flow_names(self):
        from PySide6 import QtWidgets
        other = QtWidgets.QWidget(self.panel)
        other.setObjectName("flowLayout2")
        self.assertEqual(vb.signature(self.panel), (None, ("flowLayout2", "flowLayout6")))
        self.panel.setProperty(vb.MARK, "1")
        self.assertEqual(vb.signature(self.panel)[0], "1")

    def test_a_binding_without_the_name_filter_reads_the_same(self):
        widget = FlowOnly(["formLayout1", "flowLayout9", "flowLayout3"], mark="1")
        self.assertEqual(vb.signature(widget), ("1", ("flowLayout3", "flowLayout9")))

    def test_stale_names_the_panels_whose_bar_changed(self):
        seen = {"a": ("1", ("flowLayout1",)), "b": ("1", ("flowLayout2",))}
        now = {"a": ("1", ("flowLayout1",)), "b": ("1", ("flowLayout7",)), "c": (None, ())}
        self.assertEqual(vb.stale(now, seen), ["b", "c"])
        self.assertEqual(vb.stale(seen, seen), [])

    def test_a_tick_skins_again_only_a_bar_maya_rebuilt(self):
        from PySide6 import QtWidgets
        vb.apply_all()
        with mock.patch.object(vb, "apply_all") as again:
            vb._tick()
            again.assert_not_called()
            self.flow.setObjectName("flowLayout11")             # the bar made anew, under new names
            vb._tick()
            again.assert_called_once_with()
        new = QtWidgets.QWidget(self.panel)
        new.setObjectName("flowLayout12")
        vb.apply_all()
        self.assertEqual(getattr(sys, vb.STATE)["seen"]["modelPanel4"], vb.signature(self.panel))

    def test_a_tick_with_the_switch_off_does_nothing(self):
        self.cmds.vars[vb.OPTIONVAR] = 0
        with mock.patch.object(vb, "apply_all") as again:
            vb._tick()
        again.assert_not_called()

    def test_a_tick_never_raises(self):
        with mock.patch.object(vb, "panels", mock.Mock(side_effect=RuntimeError("gone"))):
            vb._tick()

    def test_watch_runs_one_timer_and_unwatch_stops_it(self):
        vb.watch()
        first = getattr(sys, vb.STATE)["timer"]
        self.assertTrue(first.isActive())
        self.assertEqual(first.interval(), vb.WATCH_MS)
        vb.watch()
        self.assertFalse(first.isActive())
        second = getattr(sys, vb.STATE)["timer"]
        self.assertTrue(second.isActive())
        vb.unwatch()
        self.assertFalse(second.isActive())
        self.assertNotIn("timer", getattr(sys, vb.STATE))
        vb.unwatch()                                            # twice: nothing


class Switch(StandIn):
    def test_with_a_ui_on_skins_and_watches(self):
        message = vb.set_enabled(True)
        self.assertEqual(message, "Viewport bar in our look - 1 viewport")
        self.assertEqual(self.panel.property(vb.MARK), "1")
        self.assertTrue(getattr(sys, vb.STATE)["timer"].isActive())

    def test_off_gives_every_bar_back_and_stops_the_watch(self):
        vb.set_enabled(True)
        message = vb.set_enabled(False)
        self.assertEqual(message, "Viewport bar back to Maya's - 1 viewport")
        self.assertIsNone(self.panel.property(vb.MARK))
        self.assertNotIn("timer", getattr(sys, vb.STATE))
        self.assertEqual(self.cmds.vars[vb.OPTIONVAR], 0)

    def test_two_viewports_are_counted_in_the_plural(self):
        from PySide6 import QtWidgets
        second = QtWidgets.QWidget()
        self.addCleanup(second.deleteLater)
        self.widgets["modelPanel1"] = second
        self.cmds.panel_names = ["modelPanel4", "modelPanel1"]
        self.assertEqual(vb.set_enabled(True), "Viewport bar in our look - 2 viewports")

    def test_ensure_with_the_switch_off_unskins_only_what_it_skinned(self):
        self.cmds.vars[vb.OPTIONVAR] = 0
        self.assertEqual(vb.ensure(), 0)
        vb.skin_panel("modelPanel4", text="X")
        self.assertEqual(vb.ensure(), 1)
        self.assertEqual(self.panel.styleSheet(), "/* maya's */")

    def test_ensure_with_the_switch_on_skins_and_watches(self):
        self.assertEqual(vb.ensure(), 1)
        self.assertTrue(getattr(sys, vb.STATE)["timer"].isActive())

    def test_reload_live_stops_the_old_watch_and_skins_again(self):
        vb.watch()
        old = getattr(sys, vb.STATE)["timer"]
        self.assertEqual(vb.reload_live(), 1)
        self.assertFalse(old.isActive())
        self.assertIsNot(getattr(sys, vb.STATE)["timer"], old)
        self.assertEqual(self.panel.property(vb.MARK), "1")

    def test_a_switch_that_cannot_read_its_optionvar_is_off(self):
        self.cmds.optionVar = mock.Mock(side_effect=RuntimeError("no prefs"))
        self.assertFalse(vb.enabled())


class MayaSeams(unittest.TestCase):
    def test_cmds_is_mayas(self):
        try:
            import maya.cmds
        except ImportError:                                      # pragma: no cover
            self.skipTest("no maya")
        self.assertIs(vb._cmds(), maya.cmds)

    def test_the_state_lives_on_sys(self):
        saved = getattr(sys, vb.STATE, None)
        if hasattr(sys, vb.STATE):
            delattr(sys, vb.STATE)
        try:
            state = vb._state()
            self.assertEqual(state, {"skinned": set()})
            self.assertIs(vb._state(), state)
        finally:
            if saved is None:
                delattr(sys, vb.STATE)
            else:
                setattr(sys, vb.STATE, saved)

    def test_a_panels_widget_is_found_through_mayas_ui(self):
        """maya.OpenMayaUI stood in for: its findControl needs a GUI Maya."""
        import maya
        from PySide6 import QtWidgets
        import shiboken6
        _app()
        widget = QtWidgets.QWidget()
        self.addCleanup(widget.deleteLater)
        pointers = {"modelPanel4": shiboken6.getCppPointer(widget)[0]}
        fake = types.SimpleNamespace(MQtUtil=types.SimpleNamespace(findControl=lambda name: pointers.get(name)))
        with mock.patch.dict(sys.modules, {"maya.OpenMayaUI": fake}), \
                mock.patch.object(maya, "OpenMayaUI", fake, create=True):
            found = vb._panel_widget("modelPanel4")
            self.assertEqual(shiboken6.getCppPointer(found)[0], pointers["modelPanel4"])
            self.assertIsNone(vb._panel_widget("modelPanel9"))


if __name__ == "__main__":
    unittest.main()
