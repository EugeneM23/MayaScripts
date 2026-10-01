"""Where a weapon dragged out of the inventory lands (2026-09-29): the hand
under the cursor, else the floor under it and the character nearest to that.

The choice is pure (screen-space figures in, a target out); the viewport half
(the panel under the cursor, the projection, the camera ray) is proved in a
live Maya by docs/superpowers/plans/verify_inventory_live.py.

Spec: docs/superpowers/specs/2026-09-29-weapon-inventory-design.md
"""

import unittest

from maya_scenesetup import droptarget as dt


def figure(key, x0, hands, depth=10.0):
    """A stick figure standing at x0, 100 px tall, arms out at y = 70."""
    segments = [((x0, 0.0), (x0, 100.0)), ((x0 - 30.0, 70.0), (x0 + 30.0, 70.0))]
    return dt.Figure(key, segments, hands, depth)


class Choose(unittest.TestCase):

    def test_on_the_figure_the_nearer_hand(self):
        f = figure("A", 100.0, {"R": (70.0, 70.0), "L": (130.0, 70.0)})
        self.assertEqual(dt.choose((125.0, 60.0), [f], 16), ("hand", "A", "L"))
        self.assertEqual(dt.choose((95.0, 30.0), [f], 16), ("hand", "A", "R"))

    def test_off_the_figure_nothing(self):
        f = figure("A", 100.0, {"R": (70.0, 70.0), "L": (130.0, 70.0)})
        self.assertIsNone(dt.choose((300.0, 60.0), [f], 16))

    def test_the_radius_grows_with_the_figure_on_screen(self):
        """8 % of its projected height: a character filling the view is
        'under the cursor' further from its bones than a distant one."""
        big = dt.Figure("A", [((0.0, 0.0), (0.0, 1000.0))], {"R": (0.0, 700.0)}, 1.0)
        self.assertEqual(dt.choose((70.0, 500.0), [big], 16), ("hand", "A", "R"))
        self.assertIsNone(dt.choose((90.0, 500.0), [big], 16))

    def test_the_nearest_figure_wins(self):
        a = figure("A", 100.0, {"R": (70.0, 70.0)})
        b = figure("B", 140.0, {"R": (110.0, 70.0)})
        self.assertEqual(dt.choose((136.0, 40.0), [a, b], 16)[1], "B")

    def test_a_tie_goes_to_the_one_nearer_the_camera(self):
        a = figure("A", 100.0, {"R": (70.0, 70.0)}, depth=500.0)
        b = figure("B", 100.0, {"R": (70.0, 70.0)}, depth=200.0)
        self.assertEqual(dt.choose((100.0, 50.0), [a, b], 16)[1], "B")

    def test_a_missing_hand_is_skipped(self):
        f = figure("A", 100.0, {"R": None, "L": (130.0, 70.0)})
        self.assertEqual(dt.choose((75.0, 70.0), [f], 16), ("hand", "A", "L"))

    def test_a_figure_without_hands_is_no_target(self):
        f = figure("A", 100.0, {"R": None, "L": None})
        self.assertIsNone(dt.choose((100.0, 50.0), [f], 16))

    def test_a_point_on_a_bone_is_distance_zero(self):
        self.assertEqual(dt.seg_distance((5.0, 0.0), (0.0, 0.0), (10.0, 0.0)), 0.0)
        self.assertEqual(dt.seg_distance((15.0, 0.0), (0.0, 0.0), (10.0, 0.0)), 5.0)
        self.assertEqual(dt.seg_distance((3.0, 4.0), (0.0, 0.0), (0.0, 0.0)), 5.0)


class Floor(unittest.TestCase):

    def test_a_ray_down_meets_the_floor(self):
        self.assertEqual(dt.floor_hit((0.0, 100.0, 50.0), (0.0, -100.0, -50.0)),
                         (0.0, 0.0, 0.0))

    def test_a_ray_up_misses(self):
        self.assertIsNone(dt.floor_hit((0.0, 10.0, 0.0), (0.0, 20.0, 5.0)))

    def test_a_level_ray_misses(self):
        self.assertIsNone(dt.floor_hit((0.0, 10.0, 0.0), (5.0, 10.0, 5.0)))

    def test_the_owner_is_the_nearest_on_the_floor(self):
        roots = {"A": (0.0, 0.0, 0.0), "B": (300.0, 90.0, 0.0)}
        self.assertEqual(dt.owner((250.0, 0.0, 10.0), roots), "B")
        self.assertEqual(dt.owner((20.0, 0.0, 10.0), roots), "A")
        self.assertIsNone(dt.owner((0.0, 0.0, 0.0), {}))

    def test_the_caption_names_the_bone_the_drop_would_take(self):
        self.assertEqual(dt.floor_text("Manny_Rig1", "weapon_l"),
                         "floor · Manny_Rig1 · weapon_l")
        self.assertEqual(dt.hand_text("Manny_Rig", "L"),
                         "Manny_Rig · left hand")


class FloorAt(unittest.TestCase):
    """2026-09-30, a character dragged into the scene: the floor under the
    cursor, or why not."""

    class View(object):
        def __init__(self, near, far):
            self.near, self.far = near, far

        def to_port(self, local):
            return local

        def ray(self, port):
            return self.near, self.far

    def setUp(self):
        self.saved = dt.Viewport.__dict__["at"]

    def tearDown(self):
        dt.Viewport.at = self.saved

    def test_the_ray_meets_the_floor(self):
        view = self.View((0.0, 100.0, 50.0), (10.0, 0.0, 40.0))
        dt.Viewport.at = classmethod(lambda cls, gx, gy: (view, (5, 5)))
        self.assertEqual(dt.floor_at(1, 2), dict(kind="floor", point=(10.0, 0.0, 40.0)))

    def test_off_every_viewport(self):
        dt.Viewport.at = classmethod(lambda cls, gx, gy: (None, None))
        self.assertEqual(dt.floor_at(1, 2), dict(kind="none", text=dt.NO_VIEWPORT))

    def test_looking_up_is_no_floor(self):
        view = self.View((0.0, 100.0, 50.0), (0.0, 200.0, 40.0))
        dt.Viewport.at = classmethod(lambda cls, gx, gy: (view, (5, 5)))
        self.assertEqual(dt.floor_at(1, 2), dict(kind="none", text=dt.NO_FLOOR))


class FigureUnder(unittest.TestCase):
    """2026-10-01, an animation dragged out of the UE Bridge: which rig is
    under the cursor - the Weapons rule without the hands."""

    def test_on_a_figure_its_key(self):
        f = dt.Figure("Manny_Rig", [((100.0, 0.0), (100.0, 100.0))], {}, 10.0)
        self.assertEqual(dt.figure_under((108.0, 50.0), [f], 16), "Manny_Rig")

    def test_off_every_figure_none(self):
        f = dt.Figure("Manny_Rig", [((100.0, 0.0), (100.0, 100.0))], {}, 10.0)
        self.assertIsNone(dt.figure_under((200.0, 50.0), [f], 16))
        self.assertIsNone(dt.figure_under((0.0, 0.0), [], 16))

    def test_the_nearest_wins_a_tie_the_nearer_camera(self):
        a = dt.Figure("A", [((100.0, 0.0), (100.0, 100.0))], {}, 500.0)
        b = dt.Figure("B", [((110.0, 0.0), (110.0, 100.0))], {}, 900.0)
        self.assertEqual(dt.figure_under((108.0, 50.0), [a, b], 16), "B")
        c = dt.Figure("C", [((100.0, 0.0), (100.0, 100.0))], {}, 200.0)
        self.assertEqual(dt.figure_under((100.0, 50.0), [a, c], 16), "C")

    def test_a_figure_without_bones_is_no_target(self):
        self.assertIsNone(dt.figure_under((0.0, 0.0), [dt.Figure("A", [], {}, 1.0)], 16))

    def test_the_captions(self):
        self.assertEqual(dt.rig_text("Manny_Rig1"), "retarget onto Manny_Rig1")
        self.assertEqual(dt.new_rig_text("Manny [rig]"), "a new Manny [rig]")
        self.assertEqual(dt.new_rig_text("Creep [rig]", (120.4, 0.0, -35.6)),
                         "a new Creep [rig] · floor (120, -36)")


class ClipTarget(unittest.TestCase):
    """The rig under the cursor, else a new rig, over a viewport; nothing off
    every viewport. The view is faked: identity projection, depth by x."""

    class View(object):
        sx = 1.0

        def to_port(self, local):
            return local

        def project(self, world):
            return world[0], world[1]

        def depth(self, world):
            return world[2]

        def ray(self, port):
            # straight down onto the floor under the port point
            return (port[0], 500.0, -port[1]), (port[0], 400.0, -port[1])

        def heading(self):
            # the camera's right, tilted: only its floor part is the line's axis
            return (0.0, 0.5, -2.0)

    def setUp(self):
        self.saved = dt.Viewport.__dict__["at"]
        self.addCleanup(setattr, dt.Viewport, "at", self.saved)
        self.snap = [dict(key="Manny_Rig", label="Manny_Rig", root=(100.0, 0.0, 50.0),
                          points={"r": (100.0, 0.0, 50.0), "h": (100.0, 100.0, 50.0)},
                          segments=[("r", "h")]),
                     dict(key="", label="Group", root=(300.0, 0.0, 50.0),
                          points={"r": (300.0, 0.0, 50.0), "h": (300.0, 100.0, 50.0)},
                          segments=[("r", "h")])]

    def at(self, local):
        view = self.View()
        dt.Viewport.at = classmethod(lambda cls, gx, gy: (view, local))

    def test_on_a_rig_its_namespace(self):
        self.at((104.0, 60.0))
        self.assertEqual(dt.clip_target(1, 2, self.snap),
                         dict(kind="rig", rig="Manny_Rig", label="Manny_Rig",
                              text="retarget onto Manny_Rig"))

    def test_the_root_namespace_rig_too(self):
        self.at((300.0, 20.0))
        aim = dt.clip_target(1, 2, self.snap)
        self.assertEqual((aim["kind"], aim["rig"], aim["label"]), ("rig", "", "Group"))

    def test_beside_every_rig_a_new_rig_on_the_floor_point(self):
        """2026-10-01: the new rig stands where the floor was pointed at."""
        self.at((200.0, 60.0))
        self.assertEqual(dt.clip_target(1, 2, self.snap, new_label="Creep [rig]"),
                         dict(kind="new_rig", point=(200.0, 0.0, -60.0), label="Creep [rig]",
                              axis=(0.0, 0.0, -1.0),
                              text="a new Creep [rig] · floor (200, -60)"))

    def test_no_floor_under_the_cursor_a_new_rig_where_the_clip_is(self):
        view = self.View()
        view.ray = lambda port: ((0.0, 10.0, 0.0), (0.0, 20.0, 5.0))
        dt.Viewport.at = classmethod(lambda cls, gx, gy: (view, (200.0, 60.0)))
        self.assertEqual(dt.clip_target(1, 2, self.snap, new_label="Manny [rig]"),
                         dict(kind="new_rig", point=None, label="Manny [rig]",
                              axis=(0.0, 0.0, -1.0), text="a new Manny [rig]"))

    def test_the_line_runs_along_the_cameras_right_on_the_floor(self):
        """2026-10-01: several animations dropped on the floor stand across
        the screen; a camera looking straight down still has a right."""
        self.assertEqual(dt.on_floor((3.0, 9.0, 4.0)), (0.6, 0.0, 0.8))
        self.assertEqual(dt.on_floor((0.0, 1.0, 0.0)), (1.0, 0.0, 0.0))

    def test_an_empty_scene_is_a_new_rig(self):
        self.at((200.0, 60.0))
        self.assertEqual(dt.clip_target(1, 2, [])["kind"], "new_rig")

    def test_off_every_viewport_nothing(self):
        dt.Viewport.at = classmethod(lambda cls, gx, gy: (None, None))
        self.assertEqual(dt.clip_target(1, 2, self.snap),
                         dict(kind="none", text=dt.NO_VIEWPORT))
