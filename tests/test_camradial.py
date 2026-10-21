"""Space's camera menu (2026-10-20): the eight slots, the scene's cameras, looking through, the tap,
and the shared radial Menu drawing a camera spec offscreen."""

import unittest

import maya_radial_rules as rules

try:
    import maya.cmds  # noqa: F401
    HAVE_MAYA = True
except ImportError:
    HAVE_MAYA = False

if HAVE_MAYA:
    import maya_camflight
    import maya_camradial
    import maya_radial


IDENTITY = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
TOP = [1, 0, 0, 0, 0, 0, -1, 0, 0, 1, 0, 0, 0, 0, 0, 1]      # rotateX -90: up is world -Z


class Rules(unittest.TestCase):
    def test_a_camera_item_parses(self):
        self.assertEqual(rules.parse(rules.camera_item("|persp")), ("camera", "|persp"))

    def test_views_on_the_compass_scene_cameras_on_the_diagonals(self):
        items = rules.camera_slots({"persp": "|persp", "top": "|top", "front": "|front",
                                    "side": "|side"}, ["|a", "|b"])
        self.assertEqual(items, ["camera:|top", "camera:|a", "camera:|side", "camera:|b",
                                 "camera:|front", "", "camera:|persp", ""])

    def test_at_most_four_scene_cameras(self):
        items = rules.camera_slots({}, ["|a", "|b", "|c", "|d", "|e"])
        self.assertEqual([items[i] for i in rules.SCENE_SLOTS],
                         ["camera:|a", "camera:|b", "camera:|c", "camera:|d"])

    def test_camera_setup_first_then_by_name(self):
        self.assertEqual(rules.scene_order(["|zeta", "|Alpha", "|ns:SceneSetup_camera"],
                                           ["|ns:SceneSetup_camera"]),
                         ["|ns:SceneSetup_camera", "|Alpha", "|zeta"])

    def test_axes_as_a_front_and_a_top_camera_see_them(self):
        front = rules.axes_seen(IDENTITY)
        self.assertEqual(front["x"], (1, 0))
        self.assertEqual(front["y"], (0, -1))        # up on screen
        self.assertEqual(front["z"], (0, 0))         # end on
        top = rules.axes_seen(TOP)
        self.assertEqual(top["z"], (0, 1))           # world +Z points down the screen from above
        self.assertEqual(top["y"], (0, 0))

    def test_the_release(self):
        self.assertEqual(rules.camera_release(2, True, 1.0), rules.RUN)
        self.assertEqual(rules.camera_release(5, False, 1.0), rules.CLOSE)
        self.assertEqual(rules.camera_release(None, False, 0.1), rules.TAP)
        self.assertEqual(rules.camera_release(None, False, 1.0), rules.CLOSE)


class FakeCmds(object):
    """Four startup cameras, two of the scene's, one marked by Camera Setup."""

    def __init__(self):
        self.cams = {"|persp": True, "|top": True, "|front": True, "|side": True,
                     "|shotCam": False, "|rig:SceneSetup_camera": False}
        self.marked = {"|rig:SceneSetup_camera"}
        self.looked = []
        self.messages = []
        self.panel_cam = "|persp"
        self.subs = set()

    def ls(self, *args, **kw):
        if kw.get("type") == "camera":
            return [c + "|" + c.rsplit("|", 1)[-1] + "Shape" for c in self.cams]
        return [a for a in args if a in self.cams]

    def listRelatives(self, node, parent=False, **_kw):
        return [node.rsplit("|", 1)[0]] if parent else []

    def camera(self, node, query=False, startupCamera=False):
        return self.cams.get(node, False)

    def attributeQuery(self, attr, node=None, exists=False):
        return node in self.marked

    def getPanel(self, underPointer=False, withFocus=False, typeOf=None):
        if typeOf:
            return "modelPanel"
        return "modelPanel4" if underPointer else ""

    def modelPanel(self, panel, query=False, camera=False):
        return self.panel_cam

    def objectType(self, node, isAType=None):
        return False

    def xform(self, node, **_kw):
        return list(IDENTITY)

    def objExists(self, node):
        if node.endswith(".skeldarCameraFlight"):
            return node.rsplit(".", 1)[0] in self.subs
        return node in self.cams

    def lookThru(self, panel, cam):
        self.looked.append((panel, cam))

    def inViewMessage(self, assistMessage=None, **_kw):
        self.messages.append(assistMessage)


@unittest.skipUnless(HAVE_MAYA, "needs maya.cmds importable")
class Scene(unittest.TestCase):
    def setUp(self):
        self.fake = FakeCmds()
        saved = maya_camradial.cmds
        maya_camradial.cmds = self.fake
        self.addCleanup(setattr, maya_camradial, "cmds", saved)
        self.flown, self.taking, self.flying_to = [], False, None
        for name, fn in (("fly", self._fly), ("target_of", lambda panel: self.flying_to)):
            self.addCleanup(setattr, maya_camflight, name, getattr(maya_camflight, name))
            setattr(maya_camflight, name, fn)

    def _fly(self, panel, path):
        self.flown.append((panel, path))
        return self.taking

    def test_cameras(self):
        views, scene = maya_camradial.cameras()
        self.assertEqual(sorted(views), ["front", "persp", "side", "top"])
        self.assertEqual(scene, ["|rig:SceneSetup_camera", "|shotCam"])

    def test_the_spec_marks_the_camera_looked_through(self):
        spec = maya_camradial.spec()
        self.assertEqual(spec["items"][0], "camera:|top")
        self.assertEqual(spec["items"][1], "camera:|rig:SceneSetup_camera")
        self.assertEqual(spec["texts"][6], "Persp")
        self.assertEqual(spec["marked"], {6})
        self.assertTrue(spec["axes"][0])
        self.assertEqual(spec["axes"][5], {})

    def test_look_through_uses_the_panel_the_menu_opened_over(self):
        maya_camradial.spec()
        maya_camradial.look_through("|shotCam")
        self.assertEqual(self.fake.looked, [("modelPanel4", "|shotCam")])

    def test_a_flight_takes_the_switch_over(self):
        self.taking = True
        maya_camradial.spec()
        maya_camradial.look_through("|shotCam")
        self.assertEqual(self.flown, [("modelPanel4", "|shotCam")])
        self.assertEqual(self.fake.looked, [])

    def test_without_a_flight_the_panel_switches_at_once(self):
        maya_camradial.spec()
        maya_camradial.look_through("|shotCam")
        self.assertEqual(self.flown, [("modelPanel4", "|shotCam")])
        self.assertEqual(self.fake.looked, [("modelPanel4", "|shotCam")])

    def test_a_flight_s_substitute_is_not_in_the_menu(self):
        self.fake.cams["|skeldarCameraFlight"] = False
        self.fake.subs.add("|skeldarCameraFlight")
        views, scene = maya_camradial.cameras()
        self.assertNotIn("|skeldarCameraFlight", scene)

    def test_mid_flight_the_target_is_the_camera_marked(self):
        self.fake.panel_cam = "|skeldarCameraFlight"
        self.flying_to = "|shotCam"
        spec = maya_camradial.spec()
        self.assertEqual(spec["marked"], {spec["items"].index("camera:|shotCam")})

    def test_a_gone_camera_is_said(self):
        maya_camradial.spec()
        maya_camradial.look_through("|gone")
        self.assertEqual(self.fake.looked, [])
        self.assertTrue(self.fake.messages)


@unittest.skipUnless(HAVE_MAYA, "needs maya.cmds importable")
class MenuWithCameras(unittest.TestCase):
    def setUp(self):
        import os
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6 import QtWidgets
        self.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        import maya_hubqt
        self.q = maya_hubqt.qt()
        self.clock = [1000.0]
        self.ran, self.tapped, self.later = [], [], []
        for name, value in (("animated", lambda: True), ("_now_ms", lambda: self.clock[0]),
                            ("_run_later", lambda q, item, point: self.ran.append(item)),
                            ("_call_later", lambda q, func: self.later.append(func))):
            old = getattr(maya_radial, name)
            setattr(maya_radial, name, value)
            self.addCleanup(setattr, maya_radial, name, old)
        state = maya_radial._state()
        saved = dict(state)
        self.addCleanup(lambda: (state.clear(), state.update(saved)))
        state["menu"] = state["leaving"] = None

    def _menu(self, axes=True):
        items = rules.camera_slots({"persp": "|persp", "top": "|top", "front": "|front",
                                    "side": "|side"}, ["|shotCam"])
        texts = ["Top", "shotCam", "Side", "", "Front", "", "Persp", ""]
        seen = [rules.axes_seen(IDENTITY) if (axes and item) else {} for item in items]
        spec = {"items": items, "texts": texts, "axes": seen, "marked": {6},
                "on_tap": lambda: self.tapped.append(1), "release": rules.camera_release,
                "centre": "camera"}
        menu = maya_radial.Menu(self.q, spec)
        menu.centre = (300, 300)
        menu.origin = (0, 0)
        menu.cursor = lambda: (300, 300)
        menu.window = maya_radial._overlay_class(self.q)(menu)
        menu.window.resize(600, 600)
        self.addCleanup(menu.window.deleteLater)
        maya_radial._state()["menu"] = menu
        return menu

    def _ink(self, menu, colour=None):
        from PySide6 import QtGui
        image = QtGui.QImage(600, 600, QtGui.QImage.Format_ARGB32)
        image.fill(0)
        menu.paint(menu.window, device=image)
        count = 0
        for y in range(0, 600, 2):
            for x in range(0, 600, 2):
                c = image.pixelColor(x, y)
                if c.alpha() > 60 and (colour is None or (c.red() > 180 and c.green() < 120
                                                          and c.blue() < 120)):
                    count += 1
        return count

    def test_eight_slots_from_the_spec(self):
        menu = self._menu()
        self.assertEqual(menu.count, 8)
        self.assertEqual(menu.texts[6], "Persp")

    def test_a_quick_tap_in_the_centre_toggles_the_panes(self):
        menu = self._menu()
        menu.keys = [0x20]
        menu.released()
        self.assertEqual(self.tapped, [])
        self.assertEqual(len(self.later), 1)
        self.later[0]()
        self.assertEqual(self.tapped, [1])
        self.assertNotEqual(menu.phase, "open")

    def test_release_on_a_camera_runs_it(self):
        menu = self._menu()
        self.clock[0] += rules.open_total(8)
        menu.cursor = lambda: (300 + 112, 300)       # east: Side
        menu.released()
        self.assertEqual(self.ran, ["camera:|side"])

    def test_the_pills_draw_the_axes(self):
        menu = self._menu(axes=True)
        self.clock[0] += rules.open_total(8)
        with_axes = self._ink(menu, colour="red")
        plain = self._menu(axes=False)
        self.assertGreater(with_axes, self._ink(plain, colour="red"))


if __name__ == "__main__":
    unittest.main()
