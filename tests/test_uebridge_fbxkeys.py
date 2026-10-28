"""The baked bone keys read back out of an FBX the exporter wrote (2026-10-27).

The animator: «в сцене 30 фпс после экспорта в uassete 120». Measured: Maya 2027's FBX plugin
latches its bake step at the first export of a session made at a rate other than 30, and every
later export bakes at that step while its header says the scene's rate -- a 30 fps scene came out
with keys every 1/24 s, and Unreal's legacy import, which finds the sample rate that passes
through every key, read 120 (LCM of 24 and the last key's 1/120 s step). These tests build a tiny
binary FBX by hand so the reader is proven on the format, not on Maya."""

import os
import struct
import sys
import tempfile
import unittest
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "SkeldarAnim"))

from maya_uebridge import fbxkeys  # noqa: E402

TICKS = 46186158000


# ---------------------------------------------------------------------------
# a minimal binary FBX writer (version 7500: 64-bit record headers)
# ---------------------------------------------------------------------------

def _prop(value):
    kind, data = value
    if kind == "L":
        return b"L" + struct.pack("<q", data)
    if kind == "S":
        return b"S" + struct.pack("<I", len(data)) + data
    if kind == "I":
        return b"I" + struct.pack("<i", data)
    if kind in ("l", "lz", "f"):
        fmt = "q" if kind != "f" else "f"
        raw = struct.pack("<%d%s" % (len(data), fmt), *data)
        encoding = 0
        if kind == "lz":
            raw, encoding = zlib.compress(raw), 1
        tag = b"l" if kind != "f" else b"f"
        return tag + struct.pack("<III", len(data), encoding, len(raw)) + raw
    raise ValueError(kind)


def _node(name, props=(), kids=(), offset=0):
    body = b"".join(_prop(p) for p in props)
    name = name.encode()
    head_len = 24 + 1 + len(name)
    children = b""
    pos = offset + head_len + len(body)
    for kid in kids:
        blob = kid(pos)
        children += blob
        pos += len(blob)
    if kids:
        children += b"\x00" * 25
    end = offset + head_len + len(body) + len(children)
    return (struct.pack("<QQQ", end, len(props), len(body)) + bytes([len(name)]) + name
            + body + children)


def node(name, props=(), kids=()):
    return lambda offset: _node(name, props, kids, offset)


def write_fbx(path, curves, extra_layer_curve=True, compress=False):
    """`curves`: [(model name, channel, [times in seconds])]. Writes Objects + Connections."""
    objects, links = [], []
    next_id = [100]

    def new_id():
        next_id[0] += 1
        return next_id[0]

    arr = "lz" if compress else "l"
    for model, channel, times in curves:
        mid, cnid, cid = new_id(), new_id(), new_id()
        objects.append(node("Model", [("L", mid), ("S", model.encode() + b"\x00\x01Model"),
                                      ("S", b"LimbNode")]))
        objects.append(node("AnimationCurveNode", [("L", cnid), ("S", b"R\x00\x01AnimCurveNode"),
                                                   ("S", b"")]))
        objects.append(node("AnimationCurve", [("L", cid), ("S", b"\x00\x01AnimCurve"), ("S", b"")],
                            [node("KeyTime", [(arr, [int(round(t * TICKS)) for t in times])]),
                             node("KeyValueFloat", [("f", [0.0] * len(times))])]))
        links.append(node("C", [("S", b"OP"), ("L", cid), ("L", cnid), ("S", b"d|X")]))
        links.append(node("C", [("S", b"OP"), ("L", cnid), ("L", mid), ("S", channel.encode())]))
    if extra_layer_curve:
        # a layer's weight curve: four keys nowhere near the frame grid -- not a bone, not read
        lid, cnid, cid = new_id(), new_id(), new_id()
        objects.append(node("AnimationLayer", [("L", lid), ("S", b"Shake\x00\x01AnimLayer"),
                                               ("S", b"")]))
        objects.append(node("AnimationCurveNode", [("L", cnid), ("S", b"W\x00\x01AnimCurveNode"),
                                                   ("S", b"")]))
        objects.append(node("AnimationCurve", [("L", cid), ("S", b"\x00\x01AnimCurve"), ("S", b"")],
                            [node("KeyTime", [(arr, [0, 12345, 777777777, 9999999999])])]))
        links.append(node("C", [("S", b"OP"), ("L", cid), ("L", cnid), ("S", b"d|Weight")]))
        links.append(node("C", [("S", b"OP"), ("L", cnid), ("L", lid), ("S", b"Weight")]))
    data = b"Kaydara FBX Binary  \x00\x1a\x00" + struct.pack("<I", 7500)
    for top in (node("FBXHeaderExtension", [], [node("FBXVersion", [("I", 7500)])]),
                node("Objects", [], objects), node("Connections", [], links)):
        data += top(len(data))
    data += b"\x00" * 25
    with open(path, "wb") as handle:
        handle.write(data)


def frames(fps, first, last, step=1.0):
    times, frame = [], float(first)
    while frame <= last + 1e-9:
        times.append(frame / fps)
        frame += step
    return times


class ReadKeyTimes(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.path = os.path.join(self.folder, "clip.fbx")

    def test_the_bone_curves_come_back_in_seconds(self):
        write_fbx(self.path, [("root", "Lcl Translation", frames(30, 0, 10)),
                              ("pelvis", "Lcl Rotation", frames(30, 0, 10))])
        curves = fbxkeys.read_key_times(self.path)
        self.assertEqual(len(curves), 2)
        for times in curves:
            self.assertEqual(len(times), 11)
            self.assertAlmostEqual(times[3], 0.1, places=9)

    def test_a_compressed_key_array_reads_the_same(self):
        write_fbx(self.path, [("root", "Lcl Rotation", frames(30, 0, 10))], compress=True)
        self.assertAlmostEqual(fbxkeys.read_key_times(self.path)[0][10], 10 / 30.0, places=9)

    def test_an_animation_layers_weight_is_not_a_bone_curve(self):
        write_fbx(self.path, [("root", "Lcl Scaling", frames(30, 0, 5))])
        self.assertEqual(len(fbxkeys.read_key_times(self.path)), 1)

    def test_a_file_that_is_not_binary_fbx_answers_none(self):
        with open(self.path, "w") as handle:
            handle.write("; FBX 7.7.0 project file\n")
        self.assertIsNone(fbxkeys.read_key_times(self.path))

    def test_a_missing_file_answers_none(self):
        self.assertIsNone(fbxkeys.read_key_times(os.path.join(self.folder, "nope.fbx")))


class BakeProblem(unittest.TestCase):

    def test_keys_on_every_frame_of_the_scene_say_nothing(self):
        curves = [frames(30, 0, 59), frames(30, 0, 59)]
        self.assertEqual(fbxkeys.bake_problem(curves, 30.0), "")

    def test_the_measured_case_keys_every_1_24_s_in_a_30_fps_scene(self):
        """What AS_Dg_Atk_JA_Passive_1P's FBX held: 0, 1/24 ... 47/24, then the end at 59/30."""
        times = frames(24, 0, 47) + [59 / 30.0]
        problem = fbxkeys.bake_problem([times], 30.0)
        self.assertIn("1/24", problem)
        self.assertIn("30 fps", problem)

    def test_keys_on_every_other_frame_are_a_problem_though_on_the_grid(self):
        """Latched at 15 in a 30 scene: every key lands on a 30 frame, half the frames are gone."""
        problem = fbxkeys.bake_problem([frames(15, 0, 29)], 30.0)
        self.assertIn("1/15", problem)

    def test_half_frame_keys_are_a_problem(self):
        self.assertIn("1/60", fbxkeys.bake_problem([frames(60, 0, 118)], 30.0))

    def test_a_negative_start_on_the_grid_is_fine(self):
        self.assertEqual(fbxkeys.bake_problem([frames(30, -12, 40)], 30.0), "")

    def test_a_single_key_or_nothing_says_nothing(self):
        self.assertEqual(fbxkeys.bake_problem([[0.5]], 30.0), "")
        self.assertEqual(fbxkeys.bake_problem([], 30.0), "")
        self.assertEqual(fbxkeys.bake_problem(None, 30.0), "")

    def test_an_unknown_scene_rate_says_nothing(self):
        self.assertEqual(fbxkeys.bake_problem([frames(24, 0, 47)], None), "")

    def test_24_fps_keys_in_a_24_fps_scene_are_fine(self):
        self.assertEqual(fbxkeys.bake_problem([frames(24, 0, 47)], 24.0), "")


class TheExportedRange(unittest.TestCase):
    """2026-10-28, the animator: «чому не експортиться анімація». A 0-62 scene whose weapon_l and
    camera_bone carry their own keys to frame 65: the plugin baked 0..62 and kept 64 and 65, and
    the rate check read the hole 62 -> 64 as a latched plugin («bakes keys every 1/30 s, the scene
    is 30 fps and would not let go»)."""

    MEASURED = frames(30, 0, 62) + [64 / 30.0, 65 / 30.0]

    def test_the_measured_file_was_read_as_a_stuck_rate(self):
        self.assertIn("1/30", fbxkeys.bake_problem([self.MEASURED], 30.0))

    def test_with_the_range_the_rate_check_looks_only_inside_it(self):
        self.assertEqual(fbxkeys.bake_problem([self.MEASURED], 30.0, 0, 62), "")

    def test_a_real_latch_is_still_caught_inside_the_range(self):
        times = frames(24, 0, 47) + [59 / 30.0, 64 / 30.0]
        self.assertIn("1/24", fbxkeys.bake_problem([times], 30.0, 0, 59))

    def test_keys_inside_the_range_are_nothing_to_say(self):
        self.assertEqual(fbxkeys.outside_range([frames(30, 0, 62)], 30.0, 0, 62), "")
        self.assertEqual(fbxkeys.outside_range([frames(30, -12, 40)], 30.0, -12, 40), "")

    def test_keys_outside_are_counted_and_placed(self):
        text = fbxkeys.outside_range([[-5 / 30.0] + frames(30, 0, 62) + [64 / 30.0, 65 / 30.0]],
                                     30.0, 0, 62)
        self.assertIn("3 keys", text)
        self.assertIn("-5", text)
        self.assertIn("65", text)
        self.assertIn("0-62", text)

    def test_the_last_frame_read_back_a_hair_over_is_inside(self):
        """FBX ticks read back as 62.00000000000001 (measured)."""
        self.assertEqual(fbxkeys.outside_range([[0.0, 62.00000000000001 / 30.0]], 30.0, 0, 62), "")

    def test_no_keys_or_no_rate_say_nothing(self):
        self.assertEqual(fbxkeys.outside_range([], 30.0, 0, 62), "")
        self.assertEqual(fbxkeys.outside_range(None, 30.0, 0, 62), "")
        self.assertEqual(fbxkeys.outside_range([[9.0]], None, 0, 62), "")


class KeyRate(unittest.TestCase):

    def test_the_rate_is_the_commonest_step(self):
        self.assertAlmostEqual(fbxkeys.key_rate([frames(24, 0, 47) + [59 / 30.0]]), 24.0)
        self.assertAlmostEqual(fbxkeys.key_rate([frames(30, 0, 59)]), 30.0)

    def test_no_step_no_rate(self):
        self.assertIsNone(fbxkeys.key_rate([[0.0]]))


class StaysStdlib(unittest.TestCase):

    def test_the_reader_imports_no_maya(self):
        import subprocess
        code = ("import sys; sys.path.insert(0, %r); import maya_uebridge.fbxkeys; "
                "print('maya' in sys.modules)" % os.path.join(os.path.dirname(HERE), "SkeldarAnim"))
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                             cwd=os.path.join(os.path.dirname(HERE), "SkeldarAnim"))
        self.assertEqual(out.stdout.strip(), "False", out.stderr)


if __name__ == "__main__":
    unittest.main()
