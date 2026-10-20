"""The viewport's menu and icon bar in the hub's look (2026-10-20,
maya_viewportbar): the sheets, the marks on a stand-in panel offscreen, the
images pointed and given back, the switch."""

import os
import sys
import tempfile
import types
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import maya_hubstyle as hubstyle
import maya_viewportbar as vb


class Sheets(unittest.TestCase):
    def test_every_rule_of_the_bar_is_under_the_panels_mark(self):
        """No blanket rule (trap 98): the sheet reaches our panels only."""
        text = vb.sheet(1.5)
        selectors = [part.split("{")[0].strip() for part in text.split("}")
                     if "{" in part]
        self.assertTrue(selectors)
        for selector in selectors:
            for one in selector.split(","):
                self.assertTrue(one.strip().startswith('QWidget[skeldarVpBar="1"]'),
                                one)

    def test_its_pixels_follow_the_scale_and_its_colours_are_the_hubs(self):
        one, two = vb.sheet(1.0), vb.sheet(2.0)
        self.assertIn("border-radius: 6px", one)
        self.assertIn("border-radius: 12px", two)
        for token in ("panel", "hover", "accent", "track", "text"):
            self.assertIn(hubstyle.TOKENS[token], one)
        self.assertIn(vb.CHECKED, one)

    def test_a_toggle_that_is_on_is_lit_with_an_accent_edge(self):
        text = vb.sheet(1.0)
        rule = text.split("QmayaIconTextCheckBox:checked")[1].split("}")[0]
        self.assertIn(hubstyle.TOKENS["accent"], rule)

    def test_the_drop_down_arrow_names_our_file_with_forward_slashes(self):
        text = vb.sheet(1.0, "C:\\x\\y\\skeldarVpChevron.png")
        self.assertIn("url(C:/x/y/skeldarVpChevron.png)", text)

    def test_a_group_well_is_by_its_own_name_only(self):
        text = vb.group_sheet("formLayout47", 1.5)
        self.assertTrue(text.startswith("#formLayout47 {"))
        self.assertIn(hubstyle.TOKENS["card"], text)
        self.assertIn("border-radius: 12px", text)
        self.assertEqual(text.count("{"), 1)


class Separators(unittest.TestCase):
    def test_mayas_collapse_handles_are_known_by_their_image(self):
        self.assertTrue(vb.is_separator("ShortOpenBar.png"))
        self.assertTrue(vb.is_separator("C:/x/SkeldarViewportIcons/ShortCloseBar.png"))
        self.assertFalse(vb.is_separator("Camera.png"))
        self.assertFalse(vb.is_separator(""))
        self.assertFalse(vb.is_separator(None))


class Pointed(unittest.TestCase):
    def test_on_points_into_our_folder_off_back_to_the_bare_name(self):
        have = frozenset(["Camera.png"])
        self.assertEqual(vb.pointed("Camera.png", "C:/f", have, True), "C:/f/Camera.png")
        self.assertIsNone(vb.pointed("Grid.png", "C:/f", have, True))
        self.assertEqual(vb.pointed("C:/f/Camera.png", "C:/f", have, False), "Camera.png")
        self.assertIsNone(vb.pointed("Camera.png", "C:/f", have, False))


class FakeCmds(object):
    """Just what the module asks: optionVars, batch, the image flags."""

    def __init__(self, batch=True):
        self.vars = {}
        self.batch = batch
        self.images = {}

    def optionVar(self, exists=None, query=None, intValue=None):  # noqa: N802
        if exists is not None:
            return exists in self.vars
        if query is not None:
            return self.vars[query]
        if intValue is not None:
            self.vars[intValue[0]] = intValue[1]
        return None

    def about(self, batch=False, version=False):
        return self.batch if batch else "2027"

    def mayaDpiSetting(self, query=True, realScaleValue=True):  # noqa: N802
        return 1.0

    def _image(self, control, query=False, edit=False, **flags):
        flag = list(flags)[0]
        if query:
            return self.images.get((control, flag))
        self.images[(control, flag)] = flags[flag]
        return None

    iconTextButton = iconTextCheckBox = symbolCheckBox = symbolButton = _image


class Switch(unittest.TestCase):
    def setUp(self):
        self.cmds = FakeCmds()
        patch = mock.patch.object(vb, "_cmds", lambda: self.cmds)
        patch.start()
        self.addCleanup(patch.stop)

    def test_on_by_default(self):
        self.assertTrue(vb.enabled())

    def test_the_switch_is_remembered(self):
        self.assertIn("off", vb.set_enabled(False))
        self.assertFalse(vb.enabled())
        vb.set_enabled(True)
        self.assertEqual(self.cmds.vars[vb.OPTIONVAR], 1)

    def test_batch_skins_nothing(self):
        self.assertEqual(vb.ensure(), 0)


class Repoint(unittest.TestCase):
    def test_every_image_flag_is_pointed_and_given_back(self):
        cmds = FakeCmds()
        cmds.images = {("a|CameraBtn", "image1"): "Camera.png",
                       ("a|cm", "onImage"): "rvViewingPipelineOn.png",
                       ("a|cm", "offImage"): "rvViewingPipelineOff.png",
                       ("a|odd", "image1"): "NotOurs.png"}
        controls = [("iconTextButton", ("image1",), "a|CameraBtn"),
                    ("symbolCheckBox", ("onImage", "offImage"), "a|cm"),
                    ("iconTextButton", ("image1",), "a|odd")]
        have = frozenset(["Camera.png", "rvViewingPipelineOn.png",
                          "rvViewingPipelineOff.png"])
        with mock.patch.object(vb, "_cmds", lambda: cmds):
            self.assertEqual(vb._repoint(controls, "C:/f", have, True), 3)
            self.assertEqual(cmds.images[("a|cm", "offImage")],
                             "C:/f/rvViewingPipelineOff.png")
            self.assertEqual(cmds.images[("a|odd", "image1")], "NotOurs.png")
            self.assertEqual(vb._repoint(controls, "C:/f", have, False), 3)
        self.assertEqual(cmds.images[("a|CameraBtn", "image1")], "Camera.png")


def _qt():
    try:
        from PySide6 import QtWidgets
    except ImportError:                                      # pragma: no cover
        return None
    return QtWidgets


@unittest.skipIf(_qt() is None, "no PySide6")
class OnAStandInPanel(unittest.TestCase):
    """A panel built like Maya's (measured): a menu bar, an icon bar whose
    flowLayout holds formLayout groups and 13 px collapse handles."""

    def setUp(self):
        w = _qt()
        self.app = w.QApplication.instance() or w.QApplication([])
        self.panel = w.QWidget()
        self.panel.setObjectName("modelPanel4")
        self.panel.setStyleSheet("/* maya's */")
        flow = w.QWidget(self.panel)
        flow.setObjectName("flowLayout6")
        self.sep = w.QPushButton(flow)
        self.sep.setObjectName("iconTextButton34")
        self.group = w.QWidget(flow)
        self.group.setObjectName("formLayout47")
        self.button = w.QPushButton(self.group)
        self.button.setObjectName("CameraBtn")
        self.other = w.QWidget(self.panel)
        self.other.setObjectName("formLayout99")    # not in the bar's flow
        self.cmds = FakeCmds(batch=False)
        self.cmds.images = {("bar|iconTextButton34", "image1"): "ShortOpenBar.png",
                            ("bar|formLayout47|CameraBtn", "image1"): "Camera.png"}
        self.controls = [("iconTextButton", ("image1",), "bar|iconTextButton34"),
                         ("iconTextButton", ("image1",), "bar|formLayout47|CameraBtn")]
        state = {"skinned": set()}
        for target, value in (("_cmds", lambda: self.cmds),
                              ("_panel_widget", lambda name: self.panel),
                              ("bar_controls", lambda name, listed=None: self.controls),
                              ("_state", lambda: state)):
            patch = mock.patch.object(vb, target, value)
            patch.start()
            self.addCleanup(patch.stop)

    def tearDown(self):
        self.panel.deleteLater()

    def test_skinning_marks_the_panel_the_groups_and_the_handles(self):
        self.assertTrue(vb.skin_panel("modelPanel4", text="X"))
        self.assertEqual(self.panel.property(vb.MARK), "1")
        self.assertEqual(self.panel.styleSheet(), "X")
        self.assertEqual(self.group.styleSheet(), vb.group_sheet("formLayout47", 1.0))
        self.assertEqual(self.other.styleSheet(), "")
        self.assertEqual(self.sep.property("skeldarVpSep"), "1")
        self.assertIsNone(self.button.property("skeldarVpSep"))

    def test_a_second_pass_restyles_nothing(self):
        vb.skin_panel("modelPanel4", text="X")
        with mock.patch.object(self.panel, "setStyleSheet") as set_sheet:
            self.assertFalse(vb.skin_panel("modelPanel4", text="X"))
        set_sheet.assert_not_called()

    def test_unskinning_gives_every_sheet_back(self):
        vb.skin_panel("modelPanel4", text="X")
        vb.unskin_panel("modelPanel4")
        self.assertEqual(self.panel.styleSheet(), "/* maya's */")
        self.assertIsNone(self.panel.property(vb.MARK))
        self.assertEqual(self.group.styleSheet(), "")

    def test_icons_are_recoloured_once_into_our_folder(self):
        dest = tempfile.mkdtemp()
        have = vb.write_icons({"Camera.png"}, dest)
        self.assertIn(vb.CHEVRON, have)
        before = sorted(os.listdir(dest))
        vb.write_icons({"Camera.png"}, dest)
        self.assertEqual(sorted(os.listdir(dest)), before)


#  every icon of the bar Maya 2027 draws (read off a GUI Maya, 2026-10-20) but
#  the two the redraw leaves to Maya's recolour: the separator, the CM toggle
BAR_STEMS = ("Camera CameraLock CameraAE Bookmark ImagePlane PanZoom BluePencil "
             "Grid FilmGate ResolutionGate GateMask FieldChart SafeAction SafeTitle "
             "WireFrame Shaded UseDefaultMaterial WireFrameOnShaded Textured Light "
             "Shadows SSAO MotionBlur MultisampleAA DepthOfField IsolateSelected "
             "XRay XRayActiveComponents XRayJoints Exposure Gamma").split()


class Art(unittest.TestCase):
    def setUp(self):
        import maya_viewportbar_art as art
        self.art = art

    def test_every_icon_of_the_bar_is_redrawn(self):
        self.assertEqual(sorted(self.art.ICONS), sorted(BAR_STEMS))

    def test_a_drawing_is_a_whole_svg_in_our_colours(self):
        for name in self.art.ICONS:
            text = self.art.svg(name)
            self.assertTrue(text.startswith("<svg "), name)
            self.assertNotIn('class="', text, name)
            self.assertNotIn('d=""', text, name)
        self.assertIn(hubstyle.TOKENS["accent"], self.art.svg("ResolutionGate"))
        self.assertNotIn("#48aeb9", "".join(self.art.svg(n) for n in self.art.ICONS))

    def test_a_cut_out_shows_the_face_it_is_drawn_for(self):
        self.assertIn('fill="#123456"', self.art.svg("CameraAE", face="#123456"))

    def test_the_gear_has_its_teeth(self):
        self.assertEqual(self.art.gear().count("L") + 1, 32)

    def test_the_ring_grows_a_shape_and_stays_inside_the_picture(self):
        import numpy as np
        alpha = np.zeros((10, 10), np.float32)
        alpha[4:6, 4:6] = 1
        ring = self.art.halo_of(alpha, 1.5)
        self.assertEqual(ring.shape, alpha.shape)
        self.assertEqual(float(ring[3, 4]), 1.0)
        self.assertEqual(float(ring[0, 0]), 0.0)
        edge = np.zeros((6, 6), np.float32)
        edge[:, 5] = 1
        self.assertEqual(float(self.art.halo_of(edge, 1.0)[0, 0]), 0.0)   # no wrap round

    @unittest.skipIf(_qt() is None, "no PySide6")
    def test_render_draws_ink_and_the_ring(self):
        _qt().QApplication.instance() or _qt().QApplication([])
        image = self.art.render("Bookmark", 32)
        self.assertEqual((image.width(), image.height()), (32, 32))
        inside = image.pixelColor(16, 10)
        self.assertEqual(inside.name(), self.art.PALETTE["g"])
        ring = image.pixelColor(9, 10)                      # just left of the ribbon
        self.assertGreater(ring.alpha(), 120)
        self.assertLess(ring.lightness(), 60)
        self.assertEqual(image.pixelColor(1, 1).alpha(), 0)

    def test_a_size_follows_mayas_image_else_the_scale(self):
        class Img(object):
            def isNull(self):
                return False

            def width(self):
                return 20

            def height(self):
                return 20
        self.assertEqual(vb.drawn_size("Camera", "_150", Img()), 20)
        self.assertEqual(vb.drawn_size("Camera", "_150", None), 24)
        self.assertEqual(vb.drawn_size("Camera", "_200", None), 32)


class FreshFolder(unittest.TestCase):
    def test_an_older_drawing_is_taken_out_once(self):
        import maya_viewportbar_art as art
        dest = tempfile.mkdtemp()
        for name in ("Camera.png", vb.CHEVRON):
            open(os.path.join(dest, name), "w").close()
        self.assertTrue(vb._fresh_folder(dest))
        self.assertEqual(sorted(os.listdir(dest)), sorted([vb.CHEVRON, vb.STAMP]))
        open(os.path.join(dest, "Camera.png"), "w").close()
        self.assertFalse(vb._fresh_folder(dest))
        self.assertIn("Camera.png", os.listdir(dest))
        self.assertEqual(open(os.path.join(dest, vb.STAMP)).read(), str(art.VERSION))


class HubMenu(unittest.TestCase):
    def test_the_hub_routes_the_row_and_dresses_it(self):
        import maya_hub
        source = open(maya_hub.__file__, encoding="utf-8").read()
        self.assertIn('"viewportbar": set_viewportbar', source)
        self.assertIn("_dress_viewportbar(skin)", source)
        self.assertIn("_viewport_bar_soon()", source)

    def test_it_ships_and_an_install_rebuilds_it(self):
        import install
        self.assertIn("maya_viewportbar.py", install.payload())
        self.assertIn("maya_viewportbar_art.py", install.payload())
        import maya_interface
        source = open(maya_interface.__file__, encoding="utf-8").read()
        self.assertIn('"maya_viewportbar"', source)


if __name__ == "__main__":
    unittest.main()
