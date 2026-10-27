"""The main bar's Maya and Windows seams (maya_mainbar): Maya's main window found through its UI, the
caption painted through DWM (stood in for), the window's handle, and a reload painting the caption again."""

import ctypes
import os
import sys
import types
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import maya_mainbar as mb


def _app():
    from PySide6 import QtWidgets
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


class FakeFunction(object):
    """A ctypes function: takes argtypes / restype, records (hwnd, attribute, colour, size)."""

    def __init__(self, result):
        self.calls = []
        self.result = result
        self.argtypes = self.restype = None

    def __call__(self, hwnd, attribute, pointer, size):
        self.calls.append((hwnd, attribute, pointer._obj.value, size))
        return self.result(attribute) if callable(self.result) else self.result


class FakeDwm(object):
    """dwmapi with DwmSetWindowAttribute answering `result`."""

    def __init__(self, result=0):
        self.DwmSetWindowAttribute = FakeFunction(result)
        self.calls = self.DwmSetWindowAttribute.calls


class Caption(unittest.TestCase):
    def windll(self, dwm):
        return mock.patch.object(ctypes, "windll", types.SimpleNamespace(dwmapi=dwm), create=True)

    def test_on_writes_the_three_colours_to_the_window(self):
        dwm = FakeDwm()
        with self.windll(dwm):
            self.assertTrue(mb.paint_caption(4242, True))
        wanted = mb.caption_values(True)
        self.assertEqual({(attr, value) for _h, attr, value, _s in dwm.calls}, set(wanted.items()))
        self.assertTrue(all(h == 4242 and s == ctypes.sizeof(ctypes.c_ulong) for h, _a, _v, s in dwm.calls))

    def test_off_gives_windows_its_own(self):
        dwm = FakeDwm()
        with self.windll(dwm):
            mb.paint_caption(4242, False)
        self.assertEqual({value for _h, _a, value, _s in dwm.calls}, {mb.DWMWA_COLOR_DEFAULT})

    def test_one_refusal_is_no(self):
        dwm = FakeDwm(result=lambda attribute: -2147024809 if attribute == mb.DWMWA_BORDER_COLOR else 0)
        with self.windll(dwm):
            self.assertFalse(mb.paint_caption(4242, True))
        self.assertEqual(len(dwm.calls), 3)                     # it still tries every colour

    def test_no_dwm_is_no(self):
        with self.windll(None):
            self.assertFalse(mb.paint_caption(4242, True))

    @unittest.skipUnless(sys.platform == "win32", "Windows only")
    def test_windows_refuses_a_window_that_is_not_there(self):
        self.assertFalse(mb.paint_caption(0, True))


class MainWindow(unittest.TestCase):
    def omui(self, pointer):
        import maya
        fake = types.SimpleNamespace(MQtUtil=types.SimpleNamespace(mainWindow=lambda: pointer))
        patches = [mock.patch.dict(sys.modules, {"maya.OpenMayaUI": fake}),
                   mock.patch.object(maya, "OpenMayaUI", fake, create=True)]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def test_mayas_main_window_is_wrapped(self):
        from PySide6 import QtWidgets
        import shiboken6
        _app()
        window = QtWidgets.QMainWindow()
        self.addCleanup(window.deleteLater)
        self.omui(shiboken6.getCppPointer(window)[0])
        found = mb.main_window()
        self.assertEqual(shiboken6.getCppPointer(found)[0], shiboken6.getCppPointer(window)[0])

    def test_no_main_window_is_none(self):
        self.omui(0)
        self.assertIsNone(mb.main_window())

    def test_a_ui_that_raises_is_none(self):
        def broken():
            raise RuntimeError("no UI")
        self.omui(None)
        sys.modules["maya.OpenMayaUI"].MQtUtil.mainWindow = broken
        self.assertIsNone(mb.main_window())

    def test_without_a_window_there_is_no_menu_bar(self):
        with mock.patch.object(mb, "main_window", lambda: None):
            self.assertIsNone(mb.menu_bar())
        from PySide6 import QtWidgets
        _app()
        bare = QtWidgets.QWidget()
        self.addCleanup(bare.deleteLater)
        self.assertIsNone(mb.menu_bar(bare))


class Handle(unittest.TestCase):
    def test_a_widgets_handle_is_its_win_id(self):
        from PySide6 import QtWidgets
        _app()
        window = QtWidgets.QWidget()
        self.addCleanup(window.deleteLater)
        self.assertEqual(mb._hwnd(window), int(window.effectiveWinId()))

    def test_anything_else_has_none(self):
        self.assertIsNone(mb._hwnd(object()))


class FakeCmds(object):
    def __init__(self, batch=False):
        self.vars = {}
        self.batch = batch

    def optionVar(self, exists=None, query=None, intValue=None, **_):  # noqa: N802
        if exists is not None:
            return exists in self.vars
        if query is not None:
            return self.vars[query]
        self.vars[intValue[0]] = intValue[1]

    def about(self, batch=False, **_):
        return self.batch

    def mayaDpiSetting(self, **_):  # noqa: N802
        return 1.0


class Reload(unittest.TestCase):
    def setUp(self):
        from PySide6 import QtWidgets
        _app()
        self.window = QtWidgets.QMainWindow()
        self.window.menuBar().addMenu("File")
        self.addCleanup(self.window.deleteLater)
        self.cmds = FakeCmds()
        self.captions = []
        saved = getattr(sys, mb.STATE, None)
        if hasattr(sys, mb.STATE):
            delattr(sys, mb.STATE)

        def put_back():
            mb.unwatch()
            if saved is None:
                if hasattr(sys, mb.STATE):
                    delattr(sys, mb.STATE)
            else:
                setattr(sys, mb.STATE, saved)
        self.addCleanup(put_back)
        for name, value in (("_cmds", lambda: self.cmds), ("main_window", lambda: self.window),
                            ("paint_caption", lambda hwnd, on: self.captions.append((hwnd, on)) or True),
                            ("_hwnd", lambda window: 77)):
            patch = mock.patch.object(mb, name, value)
            patch.start()
            self.addCleanup(patch.stop)

    def test_a_reload_paints_the_caption_again_and_keeps_one_watch(self):
        mb.ensure()
        old = getattr(sys, mb.STATE)["timer"]
        self.assertTrue(mb.reload_live())
        self.assertEqual(self.captions, [(77, True), (77, True)])
        state = getattr(sys, mb.STATE)
        self.assertIsNot(state["timer"], old)
        self.assertFalse(old.isActive())
        self.assertEqual(self.window.menuBar().property(mb.MARK), "1")

    def test_off_and_a_caption_we_painted_is_given_back(self):
        mb.ensure()
        self.cmds.vars[mb.OPTIONVAR] = 0
        self.assertTrue(mb.ensure())
        self.assertEqual(self.captions, [(77, True), (77, False)])
        self.assertFalse(mb.ensure())                            # nothing of ours left to give back

    def test_batch_does_nothing(self):
        self.cmds.batch = True
        self.assertFalse(mb.ensure())
        self.assertEqual(mb.set_enabled(True), "Main bar on")
        self.assertEqual(self.captions, [])

    def test_a_tick_with_the_switch_off_paints_nothing(self):
        self.cmds.vars[mb.OPTIONVAR] = 0
        mb._tick()
        self.assertEqual(self.captions, [])


class Seams(unittest.TestCase):
    def test_cmds_is_mayas(self):
        try:
            import maya.cmds
        except ImportError:                                      # pragma: no cover
            self.skipTest("no maya")
        self.assertIs(mb._cmds(), maya.cmds)

    def test_the_wrapper_is_handed_its_argtypes(self):
        dwm = FakeDwm()
        with mock.patch.object(ctypes, "windll", types.SimpleNamespace(dwmapi=dwm), create=True):
            mb.paint_caption(1, True)
        self.assertEqual(len(dwm.DwmSetWindowAttribute.argtypes), 4)
        self.assertIs(dwm.DwmSetWindowAttribute.restype, ctypes.c_long)


if __name__ == "__main__":
    unittest.main()
