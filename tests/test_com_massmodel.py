"""The mass model: a voxel union of capped shells, skinned per joint.

Pure numpy - no Maya. Spec: docs/superpowers/specs/2026-10-01-center-of-mass-design.md
"""

import math
import subprocess
import sys
import os
import unittest

import numpy as np

from maya_com import massmodel as mm


def box(lo, hi):
    """A closed box as (points, triangles), outward faces."""
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    p = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
                  [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], float)
    q = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6),
         (1, 2, 6, 5), (0, 4, 7, 3)]
    t = []
    for a, b, c, d in q:
        t += [(a, b, c), (a, c, d)]
    return p, np.array(t, int)


def tube(radius, height, segments=48, rings=8):
    """A cylinder's side only - open at both ends, along +Y from 0."""
    pts = []
    for r in range(rings + 1):
        y = height * r / rings
        for s in range(segments):
            a = 2 * math.pi * s / segments
            pts.append((radius * math.cos(a), y, radius * math.sin(a)))
    tri = []
    for r in range(rings):
        for s in range(segments):
            a = r * segments + s
            b = r * segments + (s + 1) % segments
            c = a + segments
            d = b + segments
            tri += [(a, b, d), (a, d, c)]
    return np.array(pts, float), np.array(tri, int)


def soup(*meshes):
    """Several meshes as one triangle soup with shared numbering."""
    pts, tris, n = [], [], 0
    for p, t in meshes:
        pts.append(p)
        tris.append(t + n)
        n += len(p)
    return np.concatenate(pts), np.concatenate(tris)


def volume_of(points, triangles, step):
    lo = points.min(axis=0)
    hi = points.max(axis=0)
    grid = mm.Grid.around(lo, hi, step)
    inside = mm.solid(points, triangles, grid)
    return inside.sum() * step ** 3, grid, inside


class Topology(unittest.TestCase):

    def test_a_closed_box_has_no_border(self):
        p, t = box((0, 0, 0), (1, 1, 1))
        self.assertEqual(mm.border_loops(t), [])

    def test_a_tube_has_two_loops_of_its_rim(self):
        p, t = tube(5, 20, segments=12, rings=3)
        loops = mm.border_loops(t)
        self.assertEqual(sorted(len(l) for l in loops), [12, 12])

    def test_capping_closes_the_tube(self):
        p, t = tube(5, 20, segments=12, rings=3)
        p2, t2 = mm.capped(p, t)
        self.assertEqual(mm.border_loops(t2), [])
        self.assertEqual(len(p2), len(p) + 2)

    def test_two_boxes_are_two_shells(self):
        p, t = soup(box((0, 0, 0), (1, 1, 1)), box((3, 0, 0), (4, 1, 1)))
        self.assertEqual(sorted(len(s) for s in mm.shells(t)), [12, 12])

    def test_welding_rejoins_a_seam_split_box(self):
        """Unreal's mesh is split along its normal seams (CLAUDE.md, the Orc D
        1P): each face of this box has its own four corners. Welded by
        position it is one closed shell again."""
        p, t = box((0, 0, 0), (2, 2, 2))
        pts, tris = [], []
        for a, b, c in t:
            base = len(pts)
            pts += [p[a], p[b], p[c]]
            tris.append((base, base + 1, base + 2))
        pts = np.array(pts)
        tris = np.array(tris)
        self.assertNotEqual(mm.border_loops(tris), [])
        wp, wt = mm.welded(pts, tris)
        self.assertEqual(len(wp), 8)
        self.assertEqual(mm.border_loops(wt), [])


class Solid(unittest.TestCase):

    def test_a_box_s_volume(self):
        p, t = box((0, 0, 0), (10, 6, 4))
        v, _, _ = volume_of(p, t, 0.5)
        self.assertAlmostEqual(v, 240.0, delta=240 * 0.03)

    def test_an_open_tube_is_capped_into_a_cylinder(self):
        p, t = tube(5, 20)
        v, _, _ = volume_of(p, t, 0.5)
        want = math.pi * 25 * 20 * (math.sin(2 * math.pi / 48) * 48 / (2 * math.pi))
        self.assertAlmostEqual(v, want, delta=want * 0.03)

    def test_a_box_inside_a_box_is_the_bigger_box(self):
        """One soup, two shells, nested: the union - parity over the whole
        soup would call the inner box outside."""
        p, t = soup(box((0, 0, 0), (10, 10, 10)), box((3, 3, 3), (7, 7, 7)))
        v, _, _ = volume_of(p, t, 0.5)
        self.assertAlmostEqual(v, 1000.0, delta=30)

    def test_two_overlapping_boxes_are_counted_once(self):
        p, t = soup(box((0, 0, 0), (10, 10, 10)), box((5, 0, 0), (15, 10, 10)))
        v, _, _ = volume_of(p, t, 0.5)
        self.assertAlmostEqual(v, 1500.0, delta=45)

    def test_nothing_is_inside_an_empty_soup(self):
        grid = mm.Grid.around(np.zeros(3), np.ones(3), 0.5)
        inside = mm.solid(np.zeros((0, 3)), np.zeros((0, 3), int), grid)
        self.assertEqual(inside.sum(), 0)

    def test_the_grid_is_offset_off_the_lattice(self):
        grid = mm.Grid.around(np.zeros(3), np.ones(3) * 10, 1.0)
        frac = (grid.centres()[0] / 1.0) % 1.0
        for f in frac:
            self.assertGreater(min(f, 1 - f), 0.05)


def matrix(translate=(0, 0, 0), rot_z=0.0):
    """A Maya row-vector matrix: rotate about Z, then translate."""
    c, s = math.cos(rot_z), math.sin(rot_z)
    m = np.identity(4)
    m[0, :2] = (c, s)
    m[1, :2] = (-s, c)
    m[3, :3] = translate
    return m


class Accumulate(unittest.TestCase):

    def test_one_joint_holds_the_box_s_mass_and_centroid(self):
        p, t = box((0, 0, 0), (10, 6, 4))
        v, grid, inside = volume_of(p, t, 0.5)
        centres = grid.centres()[inside.ravel()]
        n = len(centres)
        world = {"a": matrix((100, 0, 0))}
        bind = {"a": np.linalg.inv(world["a"])}
        model = mm.accumulate(centres, 0.125, [("a",)] * n, np.ones((n, 1)),
                              bind, world)
        self.assertAlmostEqual(model.masses["a"], v, delta=1e-6)
        #  The samples sit on a lattice offset off the box's corners, so
        #  their centroid is the box's to within half a step.
        np.testing.assert_allclose(model.centres["a"],
                                   np.array([5, 3, 2]) - (100, 0, 0), atol=0.25)
        np.testing.assert_allclose(mm.com(model, world), (5, 3, 2), atol=0.25)

    def test_the_com_follows_the_joints_like_the_skin_does(self):
        """Two elements weighted 50/50 between two joints: the CoM a pose
        later is the LBS-deformed point, exactly."""
        rest = {"a": matrix((0, 0, 0)), "b": matrix((10, 0, 0))}
        bind = {k: np.linalg.inv(m) for k, m in rest.items()}
        centres = np.array([[5.0, 2.0, 0.0], [7.0, -1.0, 1.0]])
        model = mm.accumulate(centres, 1.0, [("a", "b")] * 2,
                              np.array([[0.5, 0.5], [0.25, 0.75]]), bind, rest)
        pose = {"a": matrix((3, 4, 0), 0.3), "b": matrix((12, 1, 5), -0.7)}

        def lbs(point, ws):
            out = np.zeros(4)
            for name, w in zip(("a", "b"), ws):
                out += w * (np.append(point, 1.0) @ bind[name] @ pose[name])
            return out[:3]
        want = (lbs(centres[0], (0.5, 0.5)) + lbs(centres[1], (0.25, 0.75))) / 2
        np.testing.assert_allclose(mm.com(model, pose), want, atol=1e-9)

    def test_the_model_can_be_built_in_any_pose(self):
        """The rest point of an element is q·(Σ w B M)⁻¹: building from a
        posed mesh gives the same model as building at the bind pose."""
        rest = {"a": matrix((0, 0, 0)), "b": matrix((10, 0, 0))}
        bind = {k: np.linalg.inv(m) for k, m in rest.items()}
        pose = {"a": matrix((3, 4, 0), 0.3), "b": matrix((12, 1, 5), -0.7)}
        centres = np.array([[5.0, 2.0, 0.0], [7.0, -1.0, 1.0]])
        ws = np.array([[0.5, 0.5], [0.25, 0.75]])
        at_bind = mm.accumulate(centres, 1.0, [("a", "b")] * 2, ws, bind, rest)

        def lbs(point, w):
            out = np.zeros(4)
            for name, wi in zip(("a", "b"), w):
                out += wi * (np.append(point, 1.0) @ bind[name] @ pose[name])
            return out[:3]
        posed = np.array([lbs(c, w) for c, w in zip(centres, ws)])
        at_pose = mm.accumulate(posed, 1.0, [("a", "b")] * 2, ws, bind, pose)
        for name in ("a", "b"):
            self.assertAlmostEqual(at_bind.masses[name], at_pose.masses[name])
            np.testing.assert_allclose(at_bind.centres[name],
                                       at_pose.centres[name], atol=1e-9)

    def test_zero_weights_carry_no_mass(self):
        model = mm.accumulate(np.array([[0.0, 0, 0]]), 1.0, [("a", "b")],
                              np.array([[1.0, 0.0]]),
                              {"a": np.identity(4), "b": np.identity(4)},
                              {"a": np.identity(4), "b": np.identity(4)})
        self.assertEqual(sorted(model.masses), ["a"])

    def test_segment_fractions(self):
        model = mm.Model({"thigh_l": 2.0, "calf_l": 1.0, "pelvis": 7.0},
                         {"thigh_l": np.zeros(3), "calf_l": np.zeros(3),
                          "pelvis": np.zeros(3)}, 10.0)
        fr = mm.segment_fractions(model, {"thigh_l": "thigh", "calf_l": "shank"})
        self.assertAlmostEqual(fr["thigh"], 0.2)
        self.assertAlmostEqual(fr["shank"], 0.1)
        self.assertAlmostEqual(fr["other"], 0.7)


class Barycentric(unittest.TestCase):

    def test_weights_at_a_closest_point(self):
        tri_weights = [{"a": 1.0}, {"a": 0.5, "b": 0.5}, {"b": 1.0}]
        out = mm.blend_weights(tri_weights, (0.5, 0.25, 0.25))
        self.assertAlmostEqual(out["a"], 0.625)
        self.assertAlmostEqual(out["b"], 0.375)


class Purity(unittest.TestCase):

    def test_the_model_imports_no_maya(self):
        plugin = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "SkeldarAnim")
        code = ("import sys; import maya_com.massmodel, maya_com.frames, "
                "maya_com.dragmath; "
                "print(any(m == 'maya' or m.startswith('maya.') for m in sys.modules))")
        out = subprocess.run([sys.executable, "-c", code], cwd=plugin,
                             capture_output=True, text=True)
        self.assertEqual(out.stdout.strip(), "False", out.stderr)


if __name__ == "__main__":
    unittest.main()
