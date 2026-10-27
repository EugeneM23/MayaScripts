"""Where a drag out of the hub lands - the scene half (2026-10-27): every
character read once (`characters`, `snapshot`, `rig_snapshot`,
`skeleton_snapshot`), the model panel under the cursor (`Viewport.at`) and
its projection, ray and camera, and the weapon's `target` from them - on a
recording `maya.cmds`, a fake `M3dView` over an offscreen QWidget and fake
cameras, so no Maya scene is touched.

The pure half (`choose`, `figure_under`, `floor_hit`, `owner`) is
test_scenesetup_droptarget.py's.
"""

import sys
import types
import unittest

import maya
import maya.api.OpenMaya as om
import maya.api.OpenMayaUI as omui

try:
    import maya_hubqt
    QT = maya_hubqt.qt()
except Exception:                                            # noqa: BLE001
    QT = None

import maya_rigs
from maya_overrig import builder
from maya_scenesetup import droptarget as dt
from maya_scenesetup import equip
from maya_uebridge import skeletonimport

_MISSING = object()


def ns(**kwargs):
    return types.SimpleNamespace(**kwargs)


class Cmds(object):
    """A scene of nodes by long path: joints (by default) at world points."""

    def __init__(self, points, types_=None, uuids=None):
        self.points = dict(points)
        self.types = dict(types_ or {})
        self.uuids = dict(uuids or {})
        self.under = None
        self.panel_types = {}
        self.panels = []

    def xform(self, node, query=False, worldSpace=False, translation=False):
        return list(self.points[node])

    def listRelatives(self, node, parent=False, allDescendents=False, type=None,  # noqa: A002
                      fullPath=False):
        if parent:
            head = node.rsplit("|", 1)[0]
            return [head] if head else None
        found = [p for p in self.points if p.startswith(node + "|")
                 and (type is None or self.types.get(p, "joint") == type)]
        return found or None

    def objExists(self, node):
        return node in self.points

    def objectType(self, node):
        return self.types.get(node, "joint")

    def ls(self, node, uuid=False):
        return [self.uuids[node]] if node in self.uuids else []

    def getPanel(self, underPointer=False, typeOf=None, type=None):  # noqa: A002
        if underPointer:
            if isinstance(self.under, Exception):
                raise self.under
            return self.under
        if typeOf is not None:
            return self.panel_types.get(typeOf)
        return list(self.panels)


class Case(unittest.TestCase):

    def swap(self, owner, name, value):
        old = getattr(owner, name)
        setattr(owner, name, value)
        self.addCleanup(setattr, owner, name, old)
        return old

    def swap_module(self, name, value):
        old = sys.modules.get(name, _MISSING)
        sys.modules[name] = value
        if old is _MISSING:
            self.addCleanup(sys.modules.pop, name, None)
        else:
            self.addCleanup(sys.modules.__setitem__, name, old)

    def use(self, cmds):
        """`import maya.cmds as cmds` inside droptarget reads the package's
        attribute: both it and the sys.modules entry are swapped."""
        self.swap(maya, "cmds", cmds)
        self.swap_module("maya.cmds", cmds)
        return cmds


# ------------------------------------------------------------ the characters

class Characters(Case):
    """«a character»: the rigs' game skeletons, then the bare skeletons -
    never one lying inside a rig's group, never twice."""

    def test_the_rigs_first_then_the_bare_skeletons(self):
        rigs = [maya_rigs.Rig("A", "A:ControlSet", "A:Main", "|A:Group", "|A:root"),
                maya_rigs.Rig("B", "B:ControlSet", "B:Main", "|B:Group", ""),
                maya_rigs.Rig("C", "C:ControlSet", "C:Main", "", "")]
        self.swap(maya_rigs, "rigs", lambda: rigs)
        self.swap(builder, "character_roots",
                  lambda: ["|A:root", "|B:Group|B:FKX", "|bare:root", "|root"])
        self.swap(equip, "character_name", lambda root: "name of " + root)
        self.assertEqual(dt.characters(), [("|A:root", "name of |A:root"),
                                           ("|bare:root", "name of |bare:root"),
                                           ("|root", "name of |root")])

    def test_no_rig_and_no_skeleton_is_no_character(self):
        self.swap(maya_rigs, "rigs", lambda: [])
        self.swap(builder, "character_roots", lambda: [])
        self.assertEqual(dt.characters(), [])


SKELETON = {
    "|root": (0.0, 0.0, 0.0),
    "|root|pelvis": (0.0, 95.0, 0.0),
    "|root|pelvis|hand_r": (-40.0, 140.0, 0.0),
    "|root|pelvis|hand_r|weapon_r": (-45.0, 140.0, 5.0),
    "|root|pelvis|hand_l": (40.0, 140.0, 0.0),
    "|root|pelvis|hand_l|weapon_l": (45.0, 140.0, 5.0),
}


class Bones(Case):

    def test_points_and_the_segments_between_listed_joints(self):
        self.use(Cmds(SKELETON))
        points, segments = dt._bones(["|root|pelvis", "|root|pelvis|hand_r",
                                      "|root|pelvis|hand_r|weapon_r"])
        self.assertEqual(points["|root|pelvis|hand_r"], (-40.0, 140.0, 0.0))
        self.assertEqual(segments, [("|root|pelvis", "|root|pelvis|hand_r"),
                                    ("|root|pelvis|hand_r", "|root|pelvis|hand_r|weapon_r")])

    def test_a_joint_whose_parent_is_not_listed_has_no_segment(self):
        self.use(Cmds(SKELETON))
        points, segments = dt._bones(["|root", "|root|pelvis|hand_l"])
        self.assertEqual(sorted(points), ["|root", "|root|pelvis|hand_l"])
        self.assertEqual(segments, [])

    def test_a_world_level_joint_has_no_parent(self):
        self.use(Cmds({"|root": (1.0, 2.0, 3.0)}))
        self.assertEqual(dt._bones(["|root"]), ({"|root": (1.0, 2.0, 3.0)}, []))


class Snapshot(Case):

    def test_every_character_once_with_its_hands_and_whether_they_hold(self):
        self.use(Cmds(SKELETON))
        self.swap(dt, "characters", lambda: [("|root", "Manny")])
        self.swap(equip, "bones", lambda root, side: (
            {"R": "|root|pelvis|hand_r", "L": "|root|pelvis|hand_gone"}[side], None))
        self.swap(equip, "occupant", lambda root, side: (
            ("|sword", "hand") if side == "R" else (None, None)))
        snap = dt.snapshot()
        self.assertEqual(len(snap), 1)
        ch = snap[0]
        self.assertEqual((ch["key"], ch["label"], ch["root"]), ("|root", "Manny", (0.0, 0.0, 0.0)))
        self.assertEqual(ch["hands"], {"R": "|root|pelvis|hand_r", "L": None})
        self.assertEqual(ch["taken"], {"R": True, "L": False})
        self.assertEqual(len(ch["points"]), len(SKELETON))
        self.assertIn(("|root", "|root|pelvis"), ch["segments"])

    def test_a_root_with_no_joints_under_it_is_a_point(self):
        self.use(Cmds({"|lone": (5.0, 0.0, 5.0)}))
        self.swap(dt, "characters", lambda: [("|lone", "lone")])
        self.swap(equip, "bones", lambda root, side: (None, None))
        self.swap(equip, "occupant", lambda root, side: (None, None))
        snap = dt.snapshot()
        self.assertEqual(snap[0]["segments"], [])
        self.assertEqual(snap[0]["hands"], {"R": None, "L": None})


class RigSnapshot(Case):

    def test_each_rig_by_its_game_skeleton_else_the_joints_under_its_group(self):
        points = dict(("|A:root" + p[5:], v) for p, v in SKELETON.items())
        points.update({"|B:Group": (0.0, 0.0, 0.0),
                       "|B:Group|B:FKX": (10.0, 0.0, 0.0),
                       "|B:Group|B:FKX|B:FKX2": (10.0, 50.0, 0.0),
                       "|B:Group|B:Main": (300.0, 0.0, 7.0),
                       "|C:Group": (0.0, 0.0, 0.0)})
        cmds = self.use(Cmds(points, types_={"|B:Group": "transform",
                                             "|B:Group|B:Main": "transform",
                                             "|C:Group": "transform"}))
        rigs = [maya_rigs.Rig("A", "", "|A:Main", "|A:Group", "|A:root"),
                maya_rigs.Rig("B", "", "|B:Group|B:Main", "|B:Group", ""),
                maya_rigs.Rig("C", "", "|C:Main", "|C:Group", ""),        # no joints
                maya_rigs.Rig("D", "", "|D:Main", "|D:Group", "|D:root"),  # gone
                maya_rigs.Rig("E", "", "|E:Main", "", "")]                 # nothing
        self.swap(maya_rigs, "rigs", lambda: rigs)
        self.swap(maya_rigs, "label", lambda rig: "rig " + rig.namespace)
        snap = dt.rig_snapshot()
        self.assertEqual([c["key"] for c in snap], ["A", "B"])
        a, b = snap
        self.assertEqual((a["label"], a["root"]), ("rig A", (0.0, 0.0, 0.0)))
        self.assertIn("|A:root", a["points"])                    # the root is a joint
        self.assertEqual(len(a["points"]), len(SKELETON))
        self.assertNotIn("|B:Group", b["points"])                # the group is not
        self.assertEqual(sorted(b["points"]), ["|B:Group|B:FKX", "|B:Group|B:FKX|B:FKX2"])
        self.assertEqual(b["segments"], [("|B:Group|B:FKX", "|B:Group|B:FKX|B:FKX2")])
        self.assertEqual(b["root"], (300.0, 0.0, 7.0))           # Main stands for it
        del cmds


class SkeletonSnapshot(Case):

    def test_every_bare_skeleton_with_its_uuid_and_label(self):
        self.use(Cmds(SKELETON, uuids={"|root": "U-1"}))
        self.swap(skeletonimport, "bare_roots", lambda: ["|root"])
        self.swap(skeletonimport, "skeleton_label", lambda root: "Manny UE5 [skeleton] (root)")
        snap = dt.skeleton_snapshot()
        self.assertEqual(len(snap), 1)
        self.assertEqual((snap[0]["key"], snap[0]["uuid"], snap[0]["label"], snap[0]["root"]),
                         ("|root", "U-1", "Manny UE5 [skeleton] (root)", (0.0, 0.0, 0.0)))
        self.assertEqual(len(snap[0]["points"]), len(SKELETON))

    def test_a_root_with_no_uuid_answers_empty(self):
        self.use(Cmds({"|root": (0.0, 0.0, 0.0)}))
        self.swap(skeletonimport, "bare_roots", lambda: ["|root"])
        self.swap(skeletonimport, "skeleton_label", lambda root: "root")
        self.assertEqual(dt.skeleton_snapshot()[0]["uuid"], "")


# ----------------------------------------------------------- the viewport

class View3d(object):
    """An M3dView over a real widget: its pointer, port, projection, ray."""

    def __init__(self, widget, port=None):
        self._widget = widget
        self.port = port or (widget.width(), widget.height())
        self.projected = []
        self.rays = []
        self.camera = "cameraPath"

    def widget(self):
        return QT.shiboken.getCppPointer(self._widget)[0]

    def portWidth(self):
        return self.port[0]

    def portHeight(self):
        return self.port[1]

    def worldToView(self, point):
        self.projected.append((point.x, point.y, point.z))
        return int(point.x * 2), int(point.z), True

    def viewToWorld(self, x, y, near, far):
        self.rays.append((x, y))
        near.x, near.y, near.z = float(x), 500.0, float(y)
        far.x, far.y, far.z = float(x), 400.0, float(y)

    def getCamera(self):
        return self.camera


@unittest.skipIf(QT is None, "no Qt")
class ViewportAt(Case):
    """The model panel under the cursor: the one Maya names first, else any
    model panel whose visible widget holds the point."""

    def setUp(self):
        QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
        self.widgets = {}
        self.views = {}
        for name, x in (("modelPanel1", 2000), ("modelPanel4", 2400)):
            widget = QT.QtWidgets.QWidget()
            widget.setGeometry(x, 2000, 200, 150)
            widget.show()
            self.addCleanup(widget.deleteLater)
            self.widgets[name] = widget
            self.views[name] = View3d(widget, port=(400, 300))
        views = self.views

        class M3dView(object):
            @staticmethod
            def getM3dViewFromModelPanel(panel):
                if panel not in views:
                    raise RuntimeError("no view: " + panel)
                return views[panel]
        self.swap(omui, "M3dView", M3dView)
        self.cmds = self.use(Cmds({}))
        self.cmds.panels = ["modelPanel1", "modelPanel4"]
        self.cmds.panel_types = {"modelPanel4": "modelPanel", "outlinerPanel1": "outlinerPanel"}

    def test_a_point_in_a_panel_is_that_panel_and_its_local_point(self):
        view, local = dt.Viewport.at(2410, 2020)
        self.assertEqual(view.panel, "modelPanel4")
        self.assertEqual(local, (10, 20))
        self.assertIs(view.view, self.views["modelPanel4"])
        self.assertEqual((view.sx, view.sy), (2.0, 2.0))

    def test_the_panel_under_the_pointer_is_asked_first(self):
        asked = []
        real = self.views["modelPanel4"]
        self.cmds.under = "modelPanel4"
        get = omui.M3dView.getM3dViewFromModelPanel
        omui.M3dView.getM3dViewFromModelPanel = staticmethod(
            lambda panel: asked.append(panel) or get(panel))
        view, _local = dt.Viewport.at(2410, 2020)
        self.assertIs(view.view, real)
        self.assertEqual(asked, ["modelPanel4"])

    def test_a_pointer_over_another_kind_of_panel_or_no_answer_is_ignored(self):
        self.cmds.under = "outlinerPanel1"
        self.assertEqual(dt.Viewport.at(2010, 2010)[0].panel, "modelPanel1")
        self.cmds.under = RuntimeError("no pointer")
        self.assertEqual(dt.Viewport.at(2010, 2010)[0].panel, "modelPanel1")

    def test_a_panel_with_no_view_or_a_hidden_one_is_skipped(self):
        self.cmds.panels = ["modelPanel9", "modelPanel1", "modelPanel4"]
        self.widgets["modelPanel1"].hide()
        view, _local = dt.Viewport.at(2010, 2010)
        self.assertIsNone(view)
        view, local = dt.Viewport.at(2450, 2100)
        self.assertEqual((view.panel, local), ("modelPanel4", (50, 100)))

    def test_off_every_panel_nothing(self):
        self.assertEqual(dt.Viewport.at(10, 10), (None, None))
        self.cmds.panels = []
        self.assertEqual(dt.Viewport.at(2010, 2010), (None, None))


@unittest.skipIf(QT is None, "no Qt")
class ViewportMath(Case):
    """Port pixels are the view's (y up), scaled from the widget's."""

    def setUp(self):
        QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
        self.widget = QT.QtWidgets.QWidget()
        self.widget.resize(200, 100)
        self.addCleanup(self.widget.deleteLater)
        self.m3d = View3d(self.widget, port=(300, 200))
        self.view = dt.Viewport("modelPanel4", self.m3d, self.widget)

    def test_the_scale_from_widget_to_port(self):
        self.assertEqual((self.view.sx, self.view.sy), (1.5, 2.0))

    def test_a_widget_point_in_port_pixels_y_up(self):
        self.assertEqual(self.view.to_port((10, 0)), (15.0, 200.0))
        self.assertEqual(self.view.to_port((200, 100)), (300.0, 0.0))

    def test_an_empty_widget_divides_by_one(self):
        widget = QT.QtWidgets.QWidget()
        widget.resize(0, 0)
        self.addCleanup(widget.deleteLater)
        view = dt.Viewport("p", View3d(widget, port=(30, 20)), widget)
        self.assertEqual((view.sx, view.sy), (30.0, 20.0))

    def test_project_hands_the_view_a_world_point(self):
        self.assertEqual(self.view.project((10.0, 20.0, 30.0)), (20.0, 30.0))
        self.assertEqual(self.m3d.projected, [(10.0, 20.0, 30.0)])

    def test_the_ray_through_a_port_point(self):
        near, far = self.view.ray((12.7, 34.2))
        self.assertEqual(self.m3d.rays, [(12, 34)])
        self.assertEqual((near, far), ((12.0, 500.0, 34.0), (12.0, 400.0, 34.0)))

    def test_heading_and_depth_come_from_the_views_camera(self):
        made = []

        class Camera(object):
            def __init__(self, path):
                made.append(path)

            def rightDirection(self, space):
                made.append(("right", space))
                return om.MVector(0.0, 0.0, -1.0)

            def eyePoint(self, space):
                made.append(("eye", space))
                return om.MPoint(0.0, 0.0, 10.0)
        self.swap(om, "MFnCamera", Camera)
        self.assertEqual(self.view.heading(), (0.0, 0.0, -1.0))
        self.assertAlmostEqual(self.view.depth((3.0, 4.0, 10.0)), 5.0)
        self.assertEqual(made, ["cameraPath", ("right", om.MSpace.kWorld),
                                "cameraPath", ("eye", om.MSpace.kWorld)])


# ----------------------------------------------------------------- target

class FlatView(object):
    """A view looking straight down: port (x, y) is world (x, -y) on the
    floor; depth is the world z."""

    sx = 1.0

    def __init__(self):
        self.down = True

    def to_port(self, local):
        return local

    def project(self, world):
        return world[0], world[1]

    def depth(self, world):
        return world[2]

    def ray(self, port):
        if not self.down:
            return (0.0, 10.0, 0.0), (0.0, 20.0, 5.0)
        return (port[0], 500.0, -port[1]), (port[0], 400.0, -port[1])

    def heading(self):
        return (1.0, 0.0, 0.0)


def character(key, x, label=None, taken=None, hands=True):
    """A stick figure standing at x, 100 tall, its hands out at y = 70."""
    points = {"r": (x, 0.0, 50.0), "h": (x, 100.0, 50.0),
              "hr": (x - 30.0, 70.0, 50.0), "hl": (x + 30.0, 70.0, 50.0)}
    return dict(key=key, label=label or key, points=points,
                segments=[("r", "h"), ("hr", "hl")],
                hands={"R": "hr" if hands else None, "L": "hl" if hands else None},
                taken=dict(taken or {"R": False, "L": False}),
                root=(x, 0.0, 50.0))


class Target(Case):
    """A weapon released: the hand under the cursor, else the floor and the
    character standing nearest to it - with the side a floor drop takes."""

    def setUp(self):
        self.view = FlatView()
        self.local = (0.0, 0.0)
        old = dt.Viewport.__dict__["at"]
        dt.Viewport.at = classmethod(
            lambda cls, gx, gy: (self.view, self.local) if self.view else (None, None))
        self.addCleanup(setattr, dt.Viewport, "at", old)
        self.snap = [character("|A:root", 100.0, "Manny_Rig"),
                     character("|B:root", 400.0, "Creep_Rig", taken={"R": True, "L": False})]

    def aim(self, local, **kwargs):
        self.local = local
        return dt.target(1, 2, self.snap, **kwargs)

    def test_off_every_viewport(self):
        self.view = None
        self.assertEqual(dt.target(1, 2, self.snap), dict(kind="none", text=dt.NO_VIEWPORT))

    def test_on_a_character_the_hand_nearer_the_cursor(self):
        self.assertEqual(self.aim((125.0, 65.0)),
                         dict(kind="hand", root="|A:root", side="L",
                              text="Manny_Rig · left hand"))
        self.assertEqual(self.aim((80.0, 70.0))["side"], "R")

    def test_beside_every_character_the_floor_under_the_cursor(self):
        aim = self.aim((240.0, -30.0))
        self.assertEqual(aim, dict(kind="floor", root="|A:root", side="R",
                                   point=(240.0, 0.0, 30.0), heading=(1.0, 0.0, 0.0),
                                   text="floor · Manny_Rig · weapon_r"))

    def test_the_owner_is_the_character_nearest_on_the_floor(self):
        aim = self.aim((330.0, -50.0))
        self.assertEqual((aim["root"], aim["side"]), ("|B:root", "L"))
        self.assertEqual(aim["text"], "floor · Creep_Rig · weapon_l")

    def test_the_hand_a_drag_comes_from_counts_as_free(self):
        self.assertEqual(self.aim((330.0, -50.0), freed=("|B:root", "R"))["side"], "R")
        self.assertEqual(self.aim((330.0, -50.0), freed=("|A:root", "R"))["side"], "L")

    def test_both_hands_taken_replaces_the_right_ones(self):
        self.snap[1]["taken"] = {"R": True, "L": True}
        self.assertEqual(self.aim((330.0, -50.0))["side"], "R")

    def test_looking_above_the_floor_is_no_floor(self):
        self.view.down = False
        self.assertEqual(self.aim((250.0, -30.0)), dict(kind="none", text=dt.NO_FLOOR))

    def test_no_character_in_the_scene(self):
        self.snap = []
        self.assertEqual(self.aim((250.0, -30.0)),
                         dict(kind="none", text="no character in the scene"))

    def test_a_character_with_no_hands_is_only_a_floor_owner(self):
        self.snap = [character("|A:root", 100.0, hands=False)]
        self.assertEqual(self.aim((125.0, 65.0))["kind"], "floor")

    def test_the_radius_follows_the_display_scale(self):
        """16 logical px times the scale, in port px: 22 px off the hand."""
        self.assertEqual(self.aim((140.0, 90.0))["kind"], "floor")
        self.assertEqual(self.aim((140.0, 90.0), scale=2.0)["kind"], "hand")

    def test_the_nearer_camera_wins_a_tie(self):
        far = character("|far:root", 100.0, "Far")
        near = character("|near:root", 100.0, "Near")
        for ch in (far, near):
            ch["points"] = dict((k, (v[0], v[1], 900.0 if ch is far else 100.0))
                                for k, v in ch["points"].items())
            ch["root"] = ch["points"]["r"]
        self.snap = [far, near]
        self.assertEqual(self.aim((100.0, 50.0))["root"], "|near:root")


if __name__ == "__main__":
    unittest.main()
