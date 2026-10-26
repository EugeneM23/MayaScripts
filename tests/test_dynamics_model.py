"""maya_dynamics.model - the Dynamics solver's pure half (2026-10-26)."""

import math
import os
import subprocess
import sys
import unittest

import numpy as np

from maya_dynamics import model

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SkeldarAnim")


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def rows_along(direction):
    """Rows with X along `direction` (a member's own axis down its bone)."""
    x = unit(direction)
    hint = np.array([0.0, 0.0, 1.0]) if abs(x[2]) < 0.9 else np.array([0.0, 1.0, 0.0])
    y = unit(np.cross(hint, x))
    return np.array([x, y, np.cross(x, y)])


def chain_frames(n=5, length=6.0, direction=(1, 0, 0), frames=60, root=None):
    """(n, T, 4, 4) members down a straight line from `root` (T, 3), each turned along it."""
    root = np.zeros((frames, 3)) if root is None else np.asarray(root, float)
    d = unit(direction)
    out = np.zeros((n, len(root), 4, 4))
    out[:, :, :3, :3] = rows_along(direction)
    for i in range(n):
        out[i, :, 3, :3] = root + i * length * d
    out[:, :, 3, 3] = 1.0
    return out


def make(frames, carrier=None, **given):
    carrier = frames[0, :, 3, :3].copy() if carrier is None else carrier
    return model.ChainInput(frames, carrier, model.settings(given))


def directions(out):
    """Every member's own axis (row 0) per frame: (n, T, 3)."""
    return out[:, :, 0, :3]


def angle(a, b):
    c = float(np.clip(np.dot(unit(a), unit(b)), -1.0, 1.0))
    return math.degrees(math.acos(c))


def points(out, chain_input, tip=True):
    """The simulated pivots of every member, then the tip: (n + 1, T, 3)."""
    pivots = out[:, :, 3, :3]
    last = chain_input.frames[-1, 0]
    before = chain_input.frames[-2, 0]
    tip_local = (last[3, :3] - before[3, :3]) @ last[:3, :3].T
    tip_world = pivots[-1] + np.einsum("i,tij->tj", tip_local, out[-1, :, :3, :3])
    return np.concatenate([pivots, tip_world[None]], axis=0)


# --------------------------------------------------------------------- pieces

class Settings(unittest.TestCase):

    def test_nothing_given_is_the_defaults(self):
        self.assertEqual(model.settings({}), model.DEFAULTS)
        self.assertEqual(model.settings(None), model.DEFAULTS)

    def test_values_are_clamped_and_unknown_keys_dropped(self):
        s = model.settings({"stiffness": 7, "limit": -5, "substeps": 99, "nonsense": 1})
        self.assertEqual(s["stiffness"], 1.0)
        self.assertEqual(s["limit"], 0.0)
        self.assertEqual(s["substeps"], model.MAX_SUBSTEPS)
        self.assertNotIn("nonsense", s)

    def test_every_preset_is_a_settings_dict(self):
        for name, values in model.PRESETS.items():
            s = model.settings(values)
            for key in values:
                self.assertEqual(s[key], values[key], (name, key))

    def test_a_ramp_runs_from_the_root_to_the_tip(self):
        np.testing.assert_allclose(model.ramp(2.0, 0.25, 3), [2.0, 1.25, 0.5])
        np.testing.assert_allclose(model.ramp(3.0, 0.5, 1), [3.0])

    def test_stiffness_zero_is_no_spring_and_grows(self):
        self.assertEqual(model.spring_k(0.0), 0.0)
        self.assertLess(model.spring_k(0.2), model.spring_k(0.6))
        self.assertAlmostEqual(model.spring_k(1.0), (2 * math.pi * model.F_FIRM) ** 2)


class Geometry(unittest.TestCase):

    def test_turn_between_takes_a_onto_b(self):
        rng = np.random.default_rng(3)
        a = rng.normal(size=(50, 3))
        b = rng.normal(size=(50, 3))
        a /= np.linalg.norm(a, axis=1)[:, None]
        b /= np.linalg.norm(b, axis=1)[:, None]
        t = model.turn_between(a, b)
        np.testing.assert_allclose(np.einsum("ni,nij->nj", a, t), b, atol=1e-9)
        np.testing.assert_allclose(np.einsum("nij,nkj->nik", t, t), np.tile(np.eye(3), (50, 1, 1)),
                                   atol=1e-9)

    def test_turn_between_opposite_and_equal(self):
        a = np.array([[1.0, 0, 0], [0, 1.0, 0]])
        t = model.turn_between(a, -a)
        np.testing.assert_allclose(np.einsum("ni,nij->nj", a, t), -a, atol=1e-9)
        np.testing.assert_allclose(model.turn_between(a, a), np.tile(np.eye(3), (2, 1, 1)),
                                   atol=1e-12)

    def test_turned_applies_turn_between_without_building_it(self):
        rng = np.random.default_rng(5)
        a, b, v = (rng.normal(size=(40, 3)) for _ in range(3))
        a /= np.linalg.norm(a, axis=1)[:, None]
        b /= np.linalg.norm(b, axis=1)[:, None]
        b[0] = -a[0]
        want = np.einsum("ni,nij->nj", v, model.turn_between(a, b))
        np.testing.assert_allclose(model.turned(v, a, b), want, atol=1e-9)

    def test_the_cone_keeps_inside_and_clamps_outside(self):
        axis = np.array([[1.0, 0, 0], [1.0, 0, 0]])
        d = np.array([unit((1, 0.1, 0)), unit((0, 1, 0))])
        out = model.clamp_cone(d, axis, np.radians([30.0, 30.0]))
        np.testing.assert_allclose(out[0], d[0], atol=1e-12)
        self.assertAlmostEqual(angle(out[1], (1, 0, 0)), 30.0, places=6)
        self.assertAlmostEqual(np.linalg.norm(out[1]), 1.0)

    def test_a_sphere_pushes_a_point_inside_out_and_leaves_one_outside(self):
        p = np.array([[0.0, 1.0, 0], [0, 9.0, 0]])
        pushed, touching, normal = model.sphere_push(p, np.array([0.5, 0.5]), np.zeros(3), 3.0)
        self.assertAlmostEqual(pushed[0, 1], 3.5)
        np.testing.assert_allclose(pushed[1], p[1])
        self.assertEqual(list(touching), [True, False])
        np.testing.assert_allclose(normal[0], (0, 1, 0))

    def test_a_capsule_pushes_from_the_nearest_point_on_its_segment(self):
        p = np.array([[5.0, 1.0, 0.0], [15.0, 0.0, 0.0], [5.0, 0.0, 9.0]])
        pushed, touching, _ = model.capsule_push(p, np.zeros(3), np.zeros(3),
                                                 np.array([10.0, 0, 0]), 2.0)
        np.testing.assert_allclose(pushed[0], (5.0, 2.0, 0.0))
        np.testing.assert_allclose(pushed[1], (15.0, 0.0, 0.0))   # past the end, 5 away: outside
        self.assertEqual(list(touching), [True, False, False])
        p2 = np.array([[11.0, 0.5, 0.0]])
        pushed2, _, _ = model.capsule_push(p2, np.zeros(1), np.zeros(3), np.array([10.0, 0, 0]), 2.0)
        self.assertAlmostEqual(np.linalg.norm(pushed2[0] - (10.0, 0, 0)), 2.0)

    def test_a_plane_holds_a_point_above_it_by_its_radius(self):
        p = np.array([[0.0, -3.0, 0.0], [0.0, 5.0, 0.0]])
        pushed, touching, _ = model.plane_push(p, np.array([1.0, 1.0]), np.zeros(3),
                                               np.array([0.0, 1.0, 0.0]))
        np.testing.assert_allclose(pushed[0], (0.0, 1.0, 0.0))
        np.testing.assert_allclose(pushed[1], p[1])
        self.assertEqual(list(touching), [True, False])


class Noise(unittest.TestCase):

    def test_the_noise_is_periodic_and_of_unit_rms(self):
        t = np.linspace(0.0, 4.0, 2001)
        n = model.noise(t, 1.5, 4.0, 7, 0)
        later = model.noise(t + 4.0, 1.5, 4.0, 7, 0)
        np.testing.assert_allclose(n, later, atol=1e-9)
        self.assertAlmostEqual(float(np.sqrt(np.mean(n[:-1] ** 2))), 1.0, delta=0.05)

    def test_channels_and_seeds_differ(self):
        t = np.linspace(0.0, 2.0, 200)
        self.assertGreater(float(np.abs(model.noise(t, 1, 2, 1, 0) - model.noise(t, 1, 2, 1, 1)).max()),
                           0.1)
        self.assertGreater(float(np.abs(model.noise(t, 1, 2, 1, 0) - model.noise(t, 1, 2, 2, 0)).max()),
                           0.1)


class Pure(unittest.TestCase):

    def test_the_model_imports_no_maya(self):
        code = ("import sys; sys.path.insert(0, %r); import maya_dynamics.model; "
                "bad = [m for m in sys.modules if m.split('.')[0] in ('maya', 'PySide6', 'shiboken6')];"
                " print(bad); sys.exit(1 if bad else 0)" % PLUGIN)
        done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


# ---------------------------------------------------------------- simulation

class Simulate(unittest.TestCase):

    def test_a_still_chain_with_no_forces_stays_on_its_animation(self):
        frames = chain_frames(frames=40)
        (out,), _info = model.simulate([make(frames, gravity=0.0, wind=0.0)])
        np.testing.assert_allclose(out, frames, atol=1e-9)

    def test_with_no_stiffness_it_hangs_straight_down(self):
        frames = chain_frames(frames=300)
        (out,), _ = model.simulate([make(frames, stiffness=0.0, damping=0.3)])
        for d in directions(out)[:, -1]:
            self.assertLess(angle(d, (0, -1, 0)), 1.0)

    def test_lengths_are_the_animation_s_on_every_frame(self):
        frames = chain_frames(frames=80)
        chain = make(frames, stiffness=0.0, damping=0.05)
        (out,), _ = model.simulate([chain])
        pts = points(out, chain)
        steps = np.linalg.norm(np.diff(pts, axis=0), axis=2)
        np.testing.assert_allclose(steps, 6.0, atol=1e-6)

    def test_stiffness_holds_the_pose_against_gravity(self):
        frames = chain_frames(frames=240)
        (stiff,), _ = model.simulate([make(frames, stiffness=1.0, stiffness_tip=1.0, damping=0.3)])
        (soft,), _ = model.simulate([make(frames, stiffness=0.0, damping=0.3)])
        self.assertLess(angle(directions(stiff)[0, -1], (1, 0, 0)), 15.0)
        self.assertGreater(angle(directions(soft)[0, -1], (1, 0, 0)), 80.0)

    def test_the_limit_cages_each_joint_against_the_one_above(self):
        frames = chain_frames(frames=200)
        (out,), _ = model.simulate([make(frames, stiffness=0.0, limit=20.0, damping=0.3)])
        d = directions(out)
        for t in range(0, 200, 10):
            self.assertLess(angle(d[0, t], (1, 0, 0)), 20.5)
            for i in range(1, d.shape[0]):
                self.assertLess(angle(d[i, t], d[i - 1, t]), 20.5)

    def test_damping_zero_still_swings_where_a_half_has_stopped(self):
        # a hanging chain whose root slides 10 cm and stops: the swing it is given dies with Damping
        T = 240
        t = np.arange(T)
        root = np.stack([np.clip(t / 10.0, 0.0, 1.0) * 10.0, np.zeros(T), np.zeros(T)], axis=1)
        frames = chain_frames(direction=(0, -1, 0), frames=T, root=root)

        def swing(damping):
            chain = make(frames, root, stiffness=0.0, damping=damping)
            (out,), _ = model.simulate([chain])
            return float(np.ptp(points(out, chain)[-1, 210:, 0]))
        self.assertGreater(swing(0.0), 2.0)
        self.assertLess(swing(0.5), 0.01)

    def test_colliders_keep_every_point_out(self):
        frames = chain_frames(n=6, frames=200)
        T = frames.shape[1]
        sphere = model.Collider("sphere", np.tile((12.0, -14.0, 0.0), (T, 1)),
                                np.tile((12.0, -14.0, 0.0), (T, 1)), np.full(T, 6.0))
        capsule = model.Collider("capsule", np.tile((-5.0, -28.0, -10.0), (T, 1)),
                                 np.tile((-5.0, -28.0, 10.0), (T, 1)), np.full(T, 4.0))
        floor = model.Collider("plane", np.tile((0.0, -26.0, 0.0), (T, 1)), None, None,
                               normal=np.tile((0.0, 1.0, 0.0), (T, 1)))
        chain = make(frames, stiffness=0.0, damping=0.2, radius=0.5, radius_tip=1.0)
        (out,), info = model.simulate([chain], colliders=[sphere, capsule, floor])
        self.assertEqual(info["ignored"], 0)
        pts = points(out, chain)[1:]
        tol = 0.05
        self.assertTrue((np.linalg.norm(pts - (12.0, -14.0, 0.0), axis=2) > 6.5 - tol).all())
        self.assertTrue((pts[..., 1] > -26.0 + 0.5 - tol).all())
        seg = np.clip(pts[..., 2], -10.0, 10.0)
        near = np.stack([np.full_like(seg, -5.0), np.full_like(seg, -28.0), seg], axis=-1)
        self.assertTrue((np.linalg.norm(pts - near, axis=-1) > 4.5 - tol).all())

    def test_substeps_change_the_answer_little(self):
        frames = chain_frames(n=6, frames=40)
        (four,), _ = model.simulate([make(frames, stiffness=0.0, damping=0.2, substeps=4)])
        (many,), _ = model.simulate([make(frames, stiffness=0.0, damping=0.2, substeps=16)])
        chain = make(frames)
        tips = points(four, chain)[-1, -1], points(many, chain)[-1, -1]
        self.assertLess(float(np.linalg.norm(tips[0] - tips[1])), 1.0)

    def test_the_frame_rate_changes_the_answer_little(self):
        a = chain_frames(n=6, frames=31)
        b = chain_frames(n=6, frames=25)
        (at30,), _ = model.simulate([make(a, stiffness=0.0, damping=0.2)], fps=30.0)
        (at24,), _ = model.simulate([make(b, stiffness=0.0, damping=0.2)], fps=24.0)
        tip30 = points(at30, make(a))[-1, 30]
        tip24 = points(at24, make(b))[-1, 24]
        self.assertLess(float(np.linalg.norm(tip30 - tip24)), 1.0)

    def test_wind_pushes_along_its_arrow_and_not_a_bone_along_it(self):
        T = 90
        down = chain_frames(direction=(0, -1, 0), frames=T)
        wind = model.WindInput(np.tile((1.0, 0, 0), (T, 1)), np.full(T, 0.5), np.zeros(T),
                               np.zeros(T), np.full(T, 1.0), 1)
        chain = make(down, gravity=0.0, stiffness=0.2, damping=0.3)
        (out,), _ = model.simulate([chain], wind=wind)
        self.assertGreater(points(out, chain)[-1, -1, 0], 1.0)
        along = chain_frames(direction=(1, 0, 0), frames=T)
        (still,), _ = model.simulate([make(along, gravity=0.0, stiffness=0.2)], wind=wind)
        np.testing.assert_allclose(still, along, atol=1e-6)

    def test_inertia_one_ignores_the_carrier_s_travel(self):
        T = 60
        root = np.stack([np.zeros(T), np.arange(T) * 2.0, np.zeros(T)], axis=1)
        frames = chain_frames(frames=T, root=root)
        (felt,), _ = model.simulate([make(frames, root, gravity=0.0, stiffness=0.0, damping=0.1)])
        (ignored,), _ = model.simulate([make(frames, root, gravity=0.0, stiffness=0.0, damping=0.1,
                                             inertia=1.0)])
        self.assertGreater(angle(directions(felt)[0, 30], (1, 0, 0)), 5.0)
        self.assertLess(angle(directions(ignored)[0, 30], (1, 0, 0)), 0.5)

    def test_preroll_starts_a_settled_chain(self):
        frames = chain_frames(frames=20)
        (cold,), _ = model.simulate([make(frames, stiffness=0.0, damping=0.3, preroll=0)])
        (warm,), _ = model.simulate([make(frames, stiffness=0.0, damping=0.3, preroll=90)])
        np.testing.assert_allclose(cold[:, 0], frames[:, 0], atol=1e-9)
        self.assertGreater(angle(directions(warm)[0, 0], (1, 0, 0)), 30.0)

    def test_a_tail_inside_a_collider_at_the_start_ignores_it(self):
        frames = chain_frames(frames=30)
        T = frames.shape[1]
        inside = model.Collider("sphere", np.tile((6.0, 0, 0), (T, 1)), np.tile((6.0, 0, 0), (T, 1)),
                                np.full(T, 2.0))
        (out,), info = model.simulate([make(frames, gravity=0.0)], colliders=[inside])
        self.assertGreaterEqual(info["ignored"], 1)
        np.testing.assert_allclose(out, frames, atol=1e-9)

    def test_two_chains_in_one_press_each_hang_from_their_own_root(self):
        a = chain_frames(n=4, frames=200)
        b = chain_frames(n=6, frames=200, root=np.tile((50.0, 0, 0), (200, 1)))
        (oa, ob), _ = model.simulate([make(a, stiffness=0.0, damping=0.3),
                                      make(b, stiffness=0.0, damping=0.3)])
        np.testing.assert_allclose(ob[0, :, 3, :3], b[0, :, 3, :3], atol=1e-12)
        self.assertLess(angle(directions(oa)[0, -1], (0, -1, 0)), 2.0)
        self.assertLess(angle(directions(ob)[0, -1], (0, -1, 0)), 2.0)

    def test_without_a_tip_the_last_member_rides_the_one_above(self):
        frames = chain_frames(frames=120)
        (out,), _ = model.simulate([make(frames, stiffness=0.0, damping=0.3, tip=False)])
        d = directions(out)
        np.testing.assert_allclose(d[-1], d[-2], atol=1e-9)


# ----------------------------------------------------------------------- loop

class Loop(unittest.TestCase):

    def swinging(self, T=40, n=5):
        """A root swinging along X with period T, sampled 0..T (frame T = frame 0)."""
        t = np.arange(T + 1)
        root = np.stack([10.0 * np.sin(2 * math.pi * t / T), np.zeros(T + 1), np.zeros(T + 1)], axis=1)
        return chain_frames(n=n, direction=(0, -1, 0), frames=T + 1, root=root), root

    def test_the_loop_settles_and_its_seam_is_no_bigger_than_a_step(self):
        frames, root = self.swinging()
        chain = make(frames, root, stiffness=0.1, damping=0.2, loop=True)
        (out,), info = model.simulate([chain], loop=True)
        self.assertEqual(out.shape[1], 40)
        self.assertTrue(info["settled"])
        self.assertLessEqual(info["cycles"], model.MAX_CYCLES)
        d = directions(out)
        inside = max(angle(d[i, t], d[i, t + 1]) for i in range(d.shape[0]) for t in range(39))
        seam = max(angle(d[i, 39], d[i, 0]) for i in range(d.shape[0]))
        self.assertLessEqual(seam, 1.5 * inside + 1e-6)

    def test_a_cycle_that_travels_settles_too(self):
        T = 32
        t = np.arange(T + 1)
        root = np.stack([np.zeros(T + 1), 3.0 * np.sin(2 * math.pi * t / T), t * 5.0], axis=1)
        frames = chain_frames(n=4, direction=(0, -1, 0), frames=T + 1, root=root)
        (out,), info = model.simulate([make(frames, root, stiffness=0.1, damping=0.25)], loop=True)
        self.assertTrue(info["settled"])
        self.assertEqual(out.shape[1], T)

    def test_a_still_loop_is_the_animation(self):
        frames = chain_frames(frames=21)
        (out,), info = model.simulate([make(frames, gravity=0.0)], loop=True)
        np.testing.assert_allclose(out, frames[:, :20], atol=1e-9)
        self.assertTrue(info["settled"])

    def test_a_range_whose_last_frame_repeats_its_first_is_found(self):
        frames, root = self.swinging(T=40)
        self.assertTrue(model.repeats_first([frames], root))
        # one frame short: the chain swings with a still carrier, so its last frame is not its first
        self.assertFalse(model.repeats_first([frames[:, :-1]], np.zeros((40, 3))))

    def test_the_wind_in_a_loop_is_periodic(self):
        frames, root = self.swinging()
        T = 41
        wind = model.WindInput(np.tile((1.0, 0, 0), (T, 1)), np.full(T, 0.3), np.full(T, 0.8),
                               np.full(T, 0.5), np.full(T, 1.5), 4)
        chain = make(frames, root, stiffness=0.2, damping=0.2)
        (out,), info = model.simulate([chain], wind=wind, loop=True)
        self.assertTrue(info["settled"])
        d = directions(out)
        inside = max(angle(d[i, t], d[i, t + 1]) for i in range(d.shape[0]) for t in range(39))
        seam = max(angle(d[i, 39], d[i, 0]) for i in range(d.shape[0]))
        self.assertLessEqual(seam, 1.5 * inside + 1e-6)


if __name__ == "__main__":
    unittest.main()
