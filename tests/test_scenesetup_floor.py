"""A weapon on the floor (2026-09-29): lying flat, its lowest point on the
floor, the blade along the given heading, the bone's own track parked on it.

The pure placement is measured here with real matrices; the scene half (the
park round trip, the bone on its socket, a retarget leaving it on the floor)
is docs/superpowers/plans/verify_inventory.py's.

Spec: docs/superpowers/specs/2026-09-29-weapon-inventory-design.md
"""

import math
import os
import unittest

import maya.api.OpenMaya as om

from maya_scenesetup import bonedrive
from maya_scenesetup import floor

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "SkeldarAnim")
SWORD_BOX = (-15.576, -31.119, -1.57, 15.576, 115.925, 1.57)


def placed(rotate, translate, scale, box):
    """The box's corners and the node's world matrix."""
    m = om.MTransformationMatrix()
    m.setScale((scale, scale, scale), om.MSpace.kTransform)
    m.setRotation(om.MEulerRotation(*[math.radians(v) for v in rotate]))
    m.setTranslation(om.MVector(*translate), om.MSpace.kTransform)
    matrix = m.asMatrix()
    corners = [om.MPoint(x, y, z) * matrix for x in (box[0], box[3])
               for y in (box[1], box[4]) for z in (box[2], box[5])]
    return corners, matrix


def axis(matrix, row):
    return om.MVector(matrix[4 * row], matrix[4 * row + 1],
                      matrix[4 * row + 2]).normal()


class LyingPose(unittest.TestCase):

    def test_the_lowest_point_is_on_the_floor(self):
        rotate, translate = floor.lying_pose(SWORD_BOX, 1.0, (30.0, 0.0, -12.0),
                                             (1.0, 0.0, 0.0))
        corners, _ = placed(rotate, translate, 1.0, SWORD_BOX)
        self.assertAlmostEqual(min(p.y for p in corners), 0.0, places=9)

    def test_the_thickness_stands_up_and_the_blade_runs_along_the_heading(self):
        rotate, translate = floor.lying_pose(SWORD_BOX, 1.0, (0.0, 0.0, 0.0),
                                             (0.0, 0.3, 2.0))
        _, matrix = placed(rotate, translate, 1.0, SWORD_BOX)
        self.assertAlmostEqual(axis(matrix, 2).y, 1.0, places=9)
        self.assertAlmostEqual(axis(matrix, 1) * om.MVector(0, 0, 1), 1.0,
                               places=9)

    def test_the_middle_of_the_weapon_is_over_the_point(self):
        rotate, translate = floor.lying_pose(SWORD_BOX, 0.4, (30.0, 5.0, -12.0),
                                             (0.0, 0.0, -1.0))
        corners, _ = placed(rotate, translate, 0.4, SWORD_BOX)
        middle_x = (min(p.x for p in corners) + max(p.x for p in corners)) / 2
        middle_z = (min(p.z for p in corners) + max(p.z for p in corners)) / 2
        self.assertAlmostEqual(middle_x, 30.0, places=9)
        self.assertAlmostEqual(middle_z, -12.0, places=9)
        self.assertAlmostEqual(min(p.y for p in corners), 5.0, places=9)

    def test_a_vertical_heading_falls_back_to_world_x(self):
        rotate, translate = floor.lying_pose(SWORD_BOX, 1.0, (0, 0, 0),
                                             (0.0, 1.0, 0.0))
        _, matrix = placed(rotate, translate, 1.0, SWORD_BOX)
        self.assertAlmostEqual(axis(matrix, 1).x, 1.0, places=9)

    def test_it_is_a_rotation_never_a_mirror(self):
        rotate, translate = floor.lying_pose(SWORD_BOX, 1.0, (0, 0, 0),
                                             (0.6, 0.0, -0.8))
        _, matrix = placed(rotate, translate, 1.0, SWORD_BOX)
        x, y, z = axis(matrix, 0), axis(matrix, 1), axis(matrix, 2)
        self.assertAlmostEqual((x ^ y) * z, 1.0, places=9)


class Parking(unittest.TestCase):

    def test_one_attribute_per_channel(self):
        self.assertEqual(bonedrive.park_attr("translateX"),
                         "skeldarParkTranslateX")
        self.assertEqual(bonedrive.park_attr("rotateZ"), "skeldarParkRotateZ")

    def test_the_space_marker_is_weaponspaces(self):
        from maya_scenesetup import weaponspace
        self.assertEqual(bonedrive.SPACE_MARKER, weaponspace.SPACE_MARKER)

    def _source(self, name):
        with open(os.path.join(PLUGIN, "maya_scenesetup", name),
                  encoding="utf-8") as handle:
            return handle.read()

    def test_the_curves_are_moved_not_baked(self):
        """«главное чтобы наша анимация сохранилась в исходном виде»: the
        bone's own curves are reconnected onto the weapon and back, never
        re-baked."""
        source = self._source("bonedrive.py")
        park = source[source.index("def park("):source.index("def _our_constraints")]
        self.assertIn("cmds.connectAttr(curves[0], weapon", park)
        self.assertIn("cmds.disconnectAttr(curves[0], plug)", park)
        self.assertNotIn("bakeResults", park)

    def test_a_world_weapon_is_relinked_where_it_lies(self):
        source = self._source("bonedrive.py")
        relink = source[source.index("def relink("):]
        self.assertLess(relink.index("if not is_held(weapon)"),
                        relink.index("place_at_grip"))
        self.assertIn("park(weapon, bone)", relink)
        self.assertIn("drive_socket(weapon, bone)", relink)

    def test_the_floor_parks_then_drives(self):
        source = self._source("floor.py")
        drop = source[source.index("def drop("):]
        self.assertLess(drop.index("bonedrive.park(weapon, bone)"),
                        drop.index("bonedrive.drive_socket(weapon, bone)"))
        self.assertIn("attach.import_weapon(entry, None, rgb)", drop)

    def test_a_hang_in_connections_drops_the_park(self):
        source = self._source("connections.py")
        self.assertIn("bonedrive.drop_park(weapon)", source)
