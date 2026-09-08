"""Which panel the overlay draws on. The `cmds`-only half, headless."""

import unittest

from maya_curveview import viewport


class FakeCmds(object):

    def __init__(self, panels=(), focus=None, types=None):
        self._panels = list(panels)
        self._focus = focus
        self._types = types or {}

    def getPanel(self, **kwargs):
        if kwargs.get("withFocus"):
            return self._focus
        if kwargs.get("visiblePanels"):
            return list(self._panels)
        if "typeOf" in kwargs:
            return self._types.get(kwargs["typeOf"], "")
        return []


class Fixture(unittest.TestCase):

    def tearDown(self):
        viewport.cmds = viewport._real_cmds


class TestActivePanel(Fixture):

    def test_focus_wins_when_it_is_a_model_panel(self):
        viewport.cmds = FakeCmds(panels=["modelPanel1", "modelPanel4"],
                                 focus="modelPanel4",
                                 types={"modelPanel1": "modelPanel",
                                        "modelPanel4": "modelPanel"})
        self.assertEqual(viewport.active_panel(), "modelPanel4")

    def test_falls_back_to_the_first_visible_model_panel(self):
        viewport.cmds = FakeCmds(panels=["outlinerPanel1", "modelPanel1"],
                                 focus="outlinerPanel1",
                                 types={"outlinerPanel1": "outlinerPanel",
                                        "modelPanel1": "modelPanel"})
        self.assertEqual(viewport.active_panel(), "modelPanel1")

    def test_a_focused_non_model_panel_is_not_drawn_on(self):
        viewport.cmds = FakeCmds(panels=["graphEditor1", "modelPanel2"],
                                 focus="graphEditor1",
                                 types={"graphEditor1": "scriptedPanel",
                                        "modelPanel2": "modelPanel"})
        self.assertEqual(viewport.active_panel(), "modelPanel2")

    def test_no_model_panel_at_all(self):
        viewport.cmds = FakeCmds(panels=["outlinerPanel1"], focus=None,
                                 types={"outlinerPanel1": "outlinerPanel"})
        self.assertIsNone(viewport.active_panel())

    def test_a_panel_whose_type_raises_is_skipped_not_fatal(self):
        class Raising(FakeCmds):
            def getPanel(self, **kwargs):
                if "typeOf" in kwargs and kwargs["typeOf"] == "ghost":
                    raise RuntimeError("gone")
                return FakeCmds.getPanel(self, **kwargs)

        viewport.cmds = Raising(panels=["ghost", "modelPanel1"], focus=None,
                                types={"modelPanel1": "modelPanel"})
        self.assertEqual(viewport.active_panel(), "modelPanel1")

    def test_panel_rect_with_no_panel_is_none(self):
        viewport.cmds = FakeCmds(panels=[], focus=None)
        self.assertIsNone(viewport.panel_rect())

    def test_the_gl_class_name_is_the_measured_one(self):
        self.assertEqual(viewport.GL_CLASS, "QmayaGLWidget")


if __name__ == "__main__":
    unittest.main()
