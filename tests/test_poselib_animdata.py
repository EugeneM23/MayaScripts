"""The pure arithmetic of an animation card (2026-10-03): the frame codec (a bone's world matrix as
seven numbers - a quaternion and a translation), a frame of the arrays read back as a pose card's
bones, the apply options, the paste plan (which source frame lands on which target frame, and what
the paste mode cuts or moves first), and Connect's offsets. Stdlib only.

Spec: docs/superpowers/specs/2026-10-03-pose-library-animation-design.md
"""
import math
import os
import random
import subprocess
import sys
import unittest

from maya_poselib import animdata as ad

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(ad.__file__)))


def rot_xyz(rx, ry, rz, t=(0, 0, 0)):
    """A row-vector 4x4 (flat) of X then Y then Z rotations (degrees), translated."""
    def rx_m(a):
        c, s = math.cos(a), math.sin(a)
        return [[1, 0, 0], [0, c, s], [0, -s, c]]

    def ry_m(a):
        c, s = math.cos(a), math.sin(a)
        return [[c, 0, -s], [0, 1, 0], [s, 0, c]]

    def rz_m(a):
        c, s = math.cos(a), math.sin(a)
        return [[c, s, 0], [-s, c, 0], [0, 0, 1]]

    def mul(a, b):
        return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]

    m = mul(mul(rx_m(math.radians(rx)), ry_m(math.radians(ry))), rz_m(math.radians(rz)))
    out = []
    for row in m:
        out += row + [0.0]
    return out + list(t) + [1.0]


class Codec(unittest.TestCase):

    def test_round_trip_keeps_rotation_and_translation(self):
        random.seed(3)
        for _ in range(200):
            m = rot_xyz(random.uniform(-180, 180), random.uniform(-89, 89),
                        random.uniform(-180, 180), (random.uniform(-500, 500), 3.25, -7.5))
            back = ad.decode(ad.encode(m))
            for a, b in zip(m, back):
                self.assertAlmostEqual(a, b, places=6)

    def test_scale_is_dropped(self):
        m = rot_xyz(10, 20, 30, (1, 2, 3))
        scaled = [v * 2.0 if i < 12 and i % 4 != 3 else v for i, v in enumerate(m)]
        back = ad.decode(ad.encode(scaled))
        for a, b in zip(m, back):
            self.assertAlmostEqual(a, b, places=6)

    def test_the_identity_and_the_half_turns(self):
        for angles in ((0, 0, 0), (180, 0, 0), (0, 180, 0), (0, 0, 180), (90, 90, 0)):
            m = rot_xyz(*angles)
            self.assertTrue(all(abs(a - b) < 1e-6 for a, b in zip(m, ad.decode(ad.encode(m)))),
                            angles)

    def test_seven_numbers_rounded(self):
        q = ad.encode(rot_xyz(10, 0, 0, (1.23456789, 0, 0)))
        self.assertEqual(len(q), 7)
        self.assertEqual(q[4], 1.234568)

    def test_a_turn_about_x_is_mayas_quaternion(self):
        # +90 about X in Maya's row-vector convention is (sin 45, 0, 0, cos 45), as MQuaternion
        q = ad.encode(rot_xyz(90, 0, 0))
        for a, b in zip(q[:4], (math.sqrt(0.5), 0.0, 0.0, math.sqrt(0.5))):
            self.assertAlmostEqual(a, b, places=9)

    def test_decode_answers_floats_of_a_unit_quaternion(self):
        back = ad.decode([0, 0, 0, 2, 1, 2, 3])        # not unit: the turn it names, no scale
        self.assertEqual(back, [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0,
                                0.0, 0.0, 1.0, 0.0, 1.0, 2.0, 3.0, 1.0])
        self.assertTrue(all(isinstance(v, float) for v in back))

    def test_no_negative_zero_in_the_numbers(self):
        q = ad.encode(rot_xyz(0, 0, 0, (-0.0, -1e-9, 0)))
        self.assertEqual([math.copysign(1.0, v) for v in q], [1.0] * 7)


def header_and_frames():
    header = {"bones": {"root": {"parent": None, "canonical": "root", "rest": [1.0] * 16,
                                 "rotateOrder": 0},
                        "upperarm_l": {"parent": "root", "canonical": "upperarm_l",
                                       "rest": [2.0] * 16, "rotateOrder": 3}}}
    frames = {"bones": ["root", "upperarm_l"],
              "world": [[0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 5, 0, 0],
                        [0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 6, 0, 0]],
              "drive": {"upperarm_l": [[0, 0, 0, 1, 7, 0, 0], [0, 0, 0, 1, 8, 0, 0]]}}
    return header, frames


class BonesAt(unittest.TestCase):

    def test_a_frame_is_a_pose_cards_bones(self):
        header, frames = header_and_frames()
        bones = ad.bones_at(header, frames, 1)
        self.assertEqual(bones["root"]["world"][13], 1.0)
        self.assertEqual(bones["upperarm_l"]["world"][12], 6.0)
        self.assertEqual(bones["upperarm_l"]["drive"][12], 8.0)
        self.assertEqual(bones["upperarm_l"]["rotateOrder"], 3)
        self.assertNotIn("drive", bones["root"])
        self.assertIsNot(bones["root"], header["bones"]["root"])   # the header is not touched

    def test_the_header_is_left_as_it_was(self):
        header, frames = header_and_frames()
        bones = ad.bones_at(header, frames, 0)
        bones["root"]["rest"][0] = 99.0
        self.assertEqual(header["bones"]["root"]["rest"][0], 1.0)
        self.assertNotIn("world", header["bones"]["root"])
        self.assertEqual(list(bones), ["root", "upperarm_l"])        # the header's order

    def test_a_bone_the_frames_do_not_hold_is_left_out(self):
        header, frames = header_and_frames()
        header["bones"]["weapon_r"] = {"parent": "root", "canonical": None, "rest": [0.0] * 16,
                                       "rotateOrder": 0}
        self.assertNotIn("weapon_r", ad.bones_at(header, frames, 0))

    def test_an_index_outside_the_arrays_is_refused(self):
        header, frames = header_and_frames()
        for index in (-1, 2):
            with self.assertRaises(IndexError):
                ad.bones_at(header, frames, index)


class Plan(unittest.TestCase):

    def test_replace_at_the_current_frame(self):
        p = ad.paste_plan(0, 47, [], ad.Options(), 100)
        self.assertEqual((p.a, p.b, p.offset), (100, 147, 100))
        self.assertEqual(p.frames[0], (0, 0, 100))
        self.assertEqual(p.frames[-1], (47, 47, 147))
        self.assertEqual(p.ops, [("cut", 100, 147)])

    def test_at_its_own_frames(self):
        p = ad.paste_plan(10, 20, [], ad.Options(at_current=False), 100)
        self.assertEqual((p.a, p.b, p.offset), (10, 20, 0))
        self.assertEqual(p.frames[0], (10, 0, 10))

    def test_a_sub_range(self):
        p = ad.paste_plan(0, 47, [], ad.Options(start=10, end=19), 5)
        self.assertEqual((p.a, p.b, len(p.frames)), (5, 14, 10))
        self.assertEqual(p.frames[0], (10, 10, 5))

    def test_a_sub_range_is_clamped_to_the_clip(self):
        p = ad.paste_plan(0, 10, [], ad.Options(start=-5, end=40), 0)
        self.assertEqual((p.frames[0][0], p.frames[-1][0], p.a, p.b), (0, 10, 0, 10))

    def test_a_range_outside_the_clip_is_refused(self):
        with self.assertRaises(ValueError) as caught:
            ad.paste_plan(0, 10, [], ad.Options(start=20, end=30), 0)
        self.assertEqual(str(caught.exception), ad.EMPTY_RANGE)

    def test_the_modes(self):
        o = lambda m: ad.paste_plan(0, 9, [], ad.Options(mode=m), 50).ops
        self.assertEqual(o("replace_all"), [("cut_all",)])
        self.assertEqual(o("insert"), [("shift", 50, 10)])
        self.assertEqual(o("merge"), [])

    def test_an_unknown_mode_is_refused_not_guessed(self):
        with self.assertRaises(ValueError):
            ad.paste_plan(0, 9, [], ad.Options(mode="bogus"), 0)
        with self.assertRaises(ValueError):
            ad.paste_plan(0, 9, [], ad.Options(keys="bogus"), 0)

    def test_source_keys_take_the_ends_and_the_keys_inside(self):
        p = ad.paste_plan(0, 20, [0.0, 4.4, 12.0, 30.0, -3.0], ad.Options(keys="source", start=2), 0)
        self.assertEqual([f[0] for f in p.frames], [2, 4, 12, 20])
        self.assertEqual(p.frames[0], (2, 2, 0))

    def test_source_keys_without_key_times_are_the_ends(self):
        p = ad.paste_plan(3, 9, None, ad.Options(keys="source"), 0)
        self.assertEqual(p.frames, [(3, 0, 0), (9, 6, 6)])
        self.assertEqual((p.a, p.b), (0, 6))

    def test_a_single_frame(self):
        p = ad.paste_plan(0, 10, [], ad.Options(start=4, end=4, mode="insert"), 7)
        self.assertEqual(p.frames, [(4, 4, 7)])
        self.assertEqual(p.ops, [("shift", 7, 1)])

    def test_the_current_frame_is_rounded(self):
        self.assertEqual(ad.paste_plan(0, 3, [], ad.Options(), 12.6).a, 13)

    def test_a_half_frame_rounds_up_both_ways(self):
        # Python's round() goes to even: 12.5 and 13.5 would land on 12 and 14
        self.assertEqual(ad.paste_plan(0, 3, [], ad.Options(), 12.5).a, 13)
        self.assertEqual(ad.paste_plan(0, 3, [], ad.Options(), 13.5).a, 14)

    def test_options_from_a_mapping_keeps_only_what_it_knows(self):
        o = ad.options_from({"mode": "bogus", "keys": "source", "connect": 1, "start": "3"})
        self.assertEqual((o.mode, o.keys, o.connect, o.start), ("replace", "source", True, 3.0))

    def test_options_defaults(self):
        self.assertEqual(ad.Options(), ("replace", True, None, None, False, "every", False))
        self.assertEqual(ad.paste_plan(0, 3, [], None, 5), ad.paste_plan(0, 3, [], ad.Options(), 5))
        self.assertEqual(ad.options_from(None), ad.Options())
        self.assertEqual(ad.options_from({"bogus": 1}), ad.Options())

    def test_options_from_reads_flags_and_numbers_as_they_are_stored(self):
        o = ad.options_from({"at_current": "0", "in_place": "true", "keys": "bogus",
                             "start": "", "end": "nan"})
        self.assertEqual((o.at_current, o.in_place, o.keys, o.start, o.end),
                         (False, True, "every", None, None))
        self.assertEqual(ad.options_from({"end": 12}).end, 12.0)

    def test_every_mode_has_a_label(self):
        self.assertEqual(set(ad.MODE_LABELS), set(ad.MODES))
        self.assertEqual(ad.MODE_LABELS["replace_all"], "Replace all")


class Connect(unittest.TestCase):

    def test_offsets_and_their_use(self):
        off = ad.connect_offsets({"a.tx": 5.0, "a.rx": 90.0, "M.tx": 1.0},
                                 {"a.tx": 2.0, "a.rx": 80.0, "M.tx": 9.0}, skip=["M.tx"])
        self.assertEqual(off, {"a.tx": 3.0, "a.rx": 10.0})
        out = ad.apply_offsets({"a.tx": 2.5, "M.tx": 4.0}, off)
        self.assertEqual(out, {"a.tx": 5.5, "M.tx": 4.0})

    def test_a_plug_on_one_side_only_has_no_offset(self):
        off = ad.connect_offsets({"a.tx": 5.0}, {"a.tx": 2.0, "b.tx": 1.0})
        self.assertEqual(off, {"a.tx": 3.0})

    def test_apply_keeps_the_order_and_leaves_the_values_alone(self):
        values = {"b.tx": 1.0, "a.tx": 2.0}
        out = ad.apply_offsets(values, {"a.tx": 1.0})
        self.assertEqual(list(out), ["b.tx", "a.tx"])
        self.assertIsNot(out, values)
        self.assertEqual(values, {"b.tx": 1.0, "a.tx": 2.0})


class Purity(unittest.TestCase):

    def test_imports_nothing_but_the_stdlib(self):
        code = ("import sys; sys.path.insert(0, %r); import maya_poselib.animdata; "
                "bad=[m for m in sys.modules if m.startswith(('maya.','PySide','shiboken')) "
                "or m=='maya']; print(bad)") % PLUGIN
        out = subprocess.check_output([sys.executable, "-c", code], cwd=PLUGIN).decode()
        self.assertEqual(out.strip(), "[]")


if __name__ == "__main__":
    unittest.main()
