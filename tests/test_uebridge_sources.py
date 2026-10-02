"""The Connect block's sources and the pure readers behind them (2026-10-02):
BVH, glTF, Unity's YAML and Hub list, the scan rules, the record model."""

import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from maya_uebridge import bvh, gltf, records, sources, unityfiles

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "SkeldarAnim")

SIMPLE_BVH = """HIERARCHY
ROOT Hips
{
  OFFSET 0 0 0
  CHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation
  JOINT Spine
  {
    OFFSET 0 10 0
    CHANNELS 3 Zrotation Xrotation Yrotation
    End Site
    {
      OFFSET 0 5 0
    }
  }
  JOINT LeftUpLeg
  {
    OFFSET 5 -2 0
    CHANNELS 3 Zrotation Xrotation Yrotation
    End Site
    {
      OFFSET 0 -20 0
    }
  }
}
MOTION
Frames: 2
Frame Time: 0.0333333
1 90 2   10 20 30   1 2 3   4 5 6
1.5 91 2   11 21 31   1 2 3   4 5 6
"""


class Bvh(unittest.TestCase):
    def test_the_hierarchy_and_its_channels(self):
        m = bvh.parse(SIMPLE_BVH)
        self.assertEqual([j.name for j in m.joints], ["Hips", "Spine", "LeftUpLeg"])
        self.assertEqual([j.parent for j in m.joints], [None, 0, 0])
        self.assertEqual(m.joints[1].offset, (0.0, 10.0, 0.0))
        self.assertEqual(len(m.frames), 2)
        self.assertAlmostEqual(m.frame_time, 0.0333333)

    def test_the_listed_order_reversed_is_mayas(self):
        self.assertEqual(bvh.rotate_order(("Zrotation", "Xrotation", "Yrotation")), "yxz")
        self.assertEqual(bvh.rotate_order(("Xrotation", "Yrotation", "Zrotation")), "zyx")
        self.assertEqual(bvh.rotate_order(("Yrotation",)), "xyz")

    def test_tracks_read_channels_by_name(self):
        m = bvh.parse(SIMPLE_BVH)
        tracks = bvh.joint_tracks(m)
        self.assertEqual(tracks[0]["t"][1], (1.5, 91.0, 2.0))
        # Zrotation Xrotation Yrotation 10 20 30 -> X 20, Y 30, Z 10
        self.assertEqual(tracks[0]["e"][0], (20.0, 30.0, 10.0))
        self.assertEqual(tracks[1]["t"][0], (0.0, 10.0, 0.0))   # the offset

    def test_fps_rounds_a_common_rate(self):
        self.assertEqual(bvh.fps_of(0.0333333), 30.0)
        self.assertEqual(bvh.fps_of(1 / 120.0), 120.0)

    def test_a_write_reads_back(self):
        m = bvh.parse(SIMPLE_BVH)
        again = bvh.parse(bvh.write(m.joints, m.frames, m.frame_time))
        self.assertEqual([j.name for j in again.joints], [j.name for j in m.joints])
        for a, b in zip(again.frames, m.frames):
            for x, y in zip(a, b):
                self.assertAlmostEqual(x, y, places=5)

    def test_a_write_takes_joints_in_any_order(self):
        """Measured 2026-10-02: Maya's allDescendents lists children first, so
        the writer puts the MOTION into the hierarchy's order."""
        j = [bvh.Joint("B", 1, (0, 1, 0), ("Xrotation",)),
             bvh.Joint("A", None, (0, 0, 0), ("Xrotation",))]
        text = bvh.write(j, [[5.0, 7.0]], 0.1)
        back = bvh.parse(text)
        self.assertEqual([x.name for x in back.joints], ["A", "B"])
        self.assertEqual(back.frames[0], [7.0, 5.0])

    def test_not_bvh_is_refused(self):
        with self.assertRaises(bvh.BvhError):
            bvh.parse("hello")


class Gltf(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder, True)

    def write(self):
        path = os.path.join(self.folder, "a.glb")
        nodes = [("Armature", None, (0, 0, 0), (0, 0, 0, 1), (1, 1, 1)),
                 ("Hips", 0, (0, 1, 0), (0, 0, 0, 1), (1, 1, 1)),
                 ("Spine", 1, (0, 0.2, 0), (0, 0, 0, 1), (1, 1, 1))]
        half = math.sqrt(0.5)
        tracks = {1: {"t": [(0, 1, 0), (0, 1, 1)],
                      "r": [(0, 0, 0, 1), (0, 0, half, half)]}}
        gltf.write_glb(path, nodes, "walk", [0.0, 1.0], tracks, skin_joints=[1, 2])
        return path

    def test_a_glb_reads_back(self):
        doc, buffers = gltf.load(self.write())
        self.assertEqual([c.name for c in gltf.clips(doc)], ["walk"])
        self.assertEqual(gltf.clips(doc)[0].end, 1.0)
        # the skin's joints and their ancestor
        self.assertEqual(gltf.skeleton_nodes(doc), [0, 1, 2])
        times, tracks = gltf.tracks(doc, buffers, 0)
        self.assertEqual(times, [0.0, 1.0])
        self.assertAlmostEqual(tracks[1]["t"][1][2], 1.0)

    def test_linear_rotation_is_a_slerp(self):
        q = gltf.slerp((0, 0, 0, 1), (0, 0, math.sqrt(0.5), math.sqrt(0.5)), 0.5)
        self.assertAlmostEqual(q[2], math.sin(math.radians(22.5)), places=6)

    def test_a_matrix_decomposes(self):
        c, s = math.cos(math.radians(30)), math.sin(math.radians(30))
        # rotation about Z 30 deg, column-major, translation (1, 2, 3), scale 2
        m = [2 * c, 2 * s, 0, 0, -2 * s, 2 * c, 0, 0, 0, 0, 2, 0, 1, 2, 3, 1]
        t, r, sc = gltf.decompose(m)
        self.assertEqual(t, (1, 2, 3))
        self.assertAlmostEqual(sc[0], 2.0)
        self.assertAlmostEqual(r[2], math.sin(math.radians(15)), places=6)
        self.assertAlmostEqual(r[3], math.cos(math.radians(15)), places=6)

    def test_normalized_bytes_are_scaled(self):
        import base64
        import struct
        data = struct.pack("<4b", 127, -127, 0, 64)
        doc = {"buffers": [{"uri": "data:application/octet-stream;base64,"
                            + base64.b64encode(data).decode(), "byteLength": 4}],
               "bufferViews": [{"buffer": 0, "byteLength": 4}],
               "accessors": [{"bufferView": 0, "componentType": 5120, "count": 1,
                              "type": "VEC4", "normalized": True}]}
        values = gltf.accessor(doc, gltf.buffers_of(doc), 0)[0]
        self.assertEqual(values[:3], (1.0, -1.0, 0.0))
        self.assertAlmostEqual(values[3], 64 / 127.0)

    def test_a_cubic_spline_takes_the_value_between_its_tangents(self):
        v = gltf._evaluate([0.0, 1.0], [(9,), (1,), (9,), (9,), (3,), (9,)],
                           "CUBICSPLINE", 0.0, "translation")
        self.assertEqual(v, (1,))

    def test_not_a_glb_is_refused(self):
        with self.assertRaises(gltf.GltfError):
            gltf.split_glb(b"\x00" * 40)


ANIM = """%YAML 1.1
--- !u!74 &7400000
AnimationClip:
  m_Name: Fire
  m_Compressed: 0
  m_RotationCurves:
  - curve:
      serializedVersion: 2
      m_Curve:
      - time: 0
        value: {x: 0, y: 0, z: 0, w: 1}
        inSlope: {x: 0, y: 0, z: 0, w: 0}
        outSlope: {x: 0, y: 0, z: 0, w: 0}
        tangentMode: 0
      - serializedVersion: 3
        time: 1
        value: {x: .5, y: -.5, z: 0, w: .70710678}
        inSlope: {x: 0, y: 0, z: 0, w: 0}
        outSlope: {x: 0, y: 0, z: 0, w: 0}
      m_PreInfinity: 2
    path: Bip01/Bip01_Pelvis
  m_PositionCurves:
  - curve:
      m_Curve:
      - time: 0
        value: {x: 1, y: 2, z: 3}
        inSlope: {x: 0, y: 0, z: 0}
        outSlope: {x: 0, y: 0, z: 0}
    path: Bip01
  m_ScaleCurves: []
  m_FloatCurves: []
  m_SampleRate: 30
  m_AnimationClipSettings:
    m_StartTime: 0
    m_StopTime: 1
  m_EditorCurves:
  - curve:
      m_Curve: []
    attribute: m_LocalPosition.x
    path: Bip01
"""

META = """fileFormatVersion: 2
ModelImporter:
  animations:
    clipAnimations:
    - serializedVersion: 16
      name: Bow_Aim
      takeName: Take 001
      firstFrame: 0
      lastFrame: 5
      curves: []
    - serializedVersion: 16
      name: Bow_Release
      takeName: Take 001
      firstFrame: 5.5
      lastFrame: 40
    isReadable: 0
  importAnimation: 1
"""


class Unity(unittest.TestCase):
    def test_hub_projects_one_per_folder_newest_first(self):
        payload = {"schema_version": "v1", "data": {
            "C:\\A": {"title": "A", "path": "C:\\A", "lastModified": 1},
            "c:\\b": {"title": "B", "path": "c:\\b", "lastModified": 5},
            "C:\\b": {"title": "B", "path": "C:\\b", "lastModified": 5}}}
        projects = unityfiles.projects_from_hub(payload)
        self.assertEqual([p[0] for p in projects], ["B", "A"])

    def test_meta_clips(self):
        self.assertEqual(unityfiles.meta_clips(META),
                         [("Bow_Aim", "Take 001", 0.0, 5.0),
                          ("Bow_Release", "Take 001", 5.5, 40.0)])
        self.assertEqual(unityfiles.meta_value(META, "importAnimation"), "1")
        self.assertEqual(unityfiles.meta_clips("clipAnimations: []\n"), [])

    def test_anim_summary(self):
        s = unityfiles.anim_summary(ANIM)
        self.assertEqual((s["name"], s["rate"], s["stop"], s["kind"]),
                         ("Fire", 30.0, 1.0, "generic"))

    def test_a_humanoid_clip_says_so(self):
        text = ANIM.replace("  m_RotationCurves:", "  m_RotationCurves: []\n  m_X:") \
            .replace("  m_PositionCurves:", "  m_PositionCurves: []\n  m_Y:")
        text += "  - attribute: RootT.x\n"
        self.assertEqual(unityfiles.anim_summary(text)["kind"], "humanoid")

    def test_curves_both_key_versions(self):
        curves = unityfiles.anim_curves(ANIM)
        rot = curves["Bip01/Bip01_Pelvis"]["r"]
        self.assertEqual([k[0] for k in rot], [0.0, 1.0])
        self.assertEqual(rot[1][1], (0.5, -0.5, 0.0, 0.70710678))
        self.assertEqual(curves["Bip01"]["t"][0][1], (1.0, 2.0, 3.0))
        self.assertNotIn("", curves)            # editor curves are not read

    def test_hermite_is_exact_at_keys_and_steps_on_infinity(self):
        rows = [(0.0, (0.0,), (0.0,), (0.0,)), (1.0, (2.0,), (0.0,), (0.0,))]
        self.assertEqual(unityfiles.hermite(rows, 0.0), (0.0,))
        self.assertEqual(unityfiles.hermite(rows, 1.0), (2.0,))
        self.assertAlmostEqual(unityfiles.hermite(rows, 0.5)[0], 1.0)
        step = [(0.0, (0.0,), (0.0,), (float("inf"),)), (1.0, (2.0,), (0.0,), (0.0,))]
        self.assertEqual(unityfiles.hermite(step, 0.5), (0.0,))

    def test_left_handed_values_come_back_mirrored(self):
        self.assertEqual(unityfiles.to_maya_position((1, 2, 3), 100), (-100, 200, 300))
        q = unityfiles.to_maya_rotation((0.1, 0.2, 0.3, 0.9))
        for got, want in zip(q, (0.1, -0.2, -0.3, 0.9)):
            self.assertAlmostEqual(got, want / math.sqrt(0.95))

    def test_unity_euler_applies_z_then_x_then_y(self):
        q = unityfiles.unity_euler_quat((0, 90, 0))
        self.assertAlmostEqual(q[1], math.sqrt(0.5))
        self.assertAlmostEqual(q[3], math.sqrt(0.5))

    def test_numbers_unity_writes(self):
        self.assertEqual(unityfiles.number(".5"), 0.5)
        self.assertEqual(unityfiles.number("-.25"), -0.25)
        self.assertEqual(unityfiles.number("Infinity"), float("inf"))


class Sources(unittest.TestCase):
    def test_a_reference_splits_back(self):
        ref = sources.ref("C:\\a\\b.fbx", sources.clip_text(take=2, take_name="Take 001"))
        self.assertEqual(ref, "C:/a/b.fbx|take=2&take_name=Take+001")
        self.assertEqual(sources.split_ref(ref),
                         ("C:/a/b.fbx", {"take": "2", "take_name": "Take 001"}))
        self.assertEqual(sources.split_ref("C:/a/b.fbx"), ("C:/a/b.fbx", {}))

    def test_only_a_whole_fbx_is_the_old_road(self):
        self.assertTrue(sources.is_plain_fbx("C:/a/b.FBX"))
        self.assertFalse(sources.is_plain_fbx("C:/a/b.fbx|take=2"))
        self.assertFalse(sources.is_plain_fbx("C:/a/b.bvh"))

    def test_formats_by_extension(self):
        self.assertEqual([sources.fmt_of(p) for p in (
            "a.FBX", "a.glb", "a.gltf", "a.usdz", "a.anim", "a.obj")],
            ["fbx", "gltf", "gltf", "usd", "anim", ""])

    def test_one_take_one_row_several_one_each(self):
        one = sources.take_rows("C:/a/walk.fbx", [(1, "Take 001", 0.0, 30.0)])
        self.assertEqual([(r.name, r.clip, r.frames) for r in one], [("walk.fbx", "", 31)])
        many = sources.take_rows("C:/a/pack.fbx", [(1, "Take 001", 0.0, 30.0),
                                                   (2, "jump", 0.0, 10.0),
                                                   (3, "still", 5.0, 5.0)])
        self.assertEqual([(r.name, r.clip) for r in many],
                         [("pack.fbx · Take 001", "take=1"), ("pack.fbx · jump", "take=2")])

    def test_a_unity_model_lists_its_meta_clips(self):
        rows = sources.unity_model_rows("C:/p/Assets/Bow.fbx",
                                        unityfiles.meta_clips(META), [])
        self.assertEqual([(r.name, r.frames, r.source) for r in rows],
                         [("Bow_Aim", 6, "unity"), ("Bow_Release", 35, "unity")])
        self.assertEqual(sources.split_ref(rows[1].package)[1],
                         {"first": "5.5", "last": "40", "take_name": "Take 001"})

    def test_the_scan_walks_and_skips_the_caches(self):
        top = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, top, True)
        for name in ("a/run.bvh", "a/clip.anim", "Library/skip.bvh", "b/x.txt"):
            path = os.path.join(top, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as handle:
                handle.write(SIMPLE_BVH if name.endswith(".bvh") else ANIM)
        rows = sources.scan(top, "folder", takes_of=lambda p: [])
        self.assertEqual(sorted((r.name, r.fmt, r.frames) for r in rows),
                         [("Fire", "anim", 31), ("run.bvh", "bvh", 2)])

    def test_a_broken_file_keeps_a_row_that_says_so(self):
        top = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, top, True)
        with open(os.path.join(top, "bad.bvh"), "w") as handle:
            handle.write("nonsense")
        rows = sources.scan(top, "folder", takes_of=lambda p: [])
        self.assertTrue(rows[0].skeleton.startswith("unreadable"))

    def test_a_stop_from_the_progress_ends_the_scan(self):
        top = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, top, True)
        for i in range(3):
            with open(os.path.join(top, "c%d.bvh" % i), "w") as handle:
                handle.write(SIMPLE_BVH)
        rows = sources.scan(top, "folder", lambda p: [],
                            progress=lambda done, total, path: done < 1)
        self.assertEqual(len(rows), 1)

    def test_recent_puts_the_pick_first(self):
        self.assertEqual(sources.recent(["C:/a", "C:/b"], "C:/B"), ["C:/B", "C:/a"])

    def test_the_cache_name_is_per_place(self):
        a = sources.cache_name("folder", "C:/a")
        self.assertNotEqual(a, sources.cache_name("folder", "C:/b"))
        self.assertEqual(a, sources.cache_name("folder", "c:\\a"))


class RecordModel(unittest.TestCase):
    def test_old_records_are_unreal_assets(self):
        rec = records.AnimRecord("A", "/Game/A", "", 3, 0.1, 30.0)
        self.assertEqual((rec.source, rec.path, rec.clip, rec.fmt), ("unreal", "", "", ""))

    def test_a_file_record_survives_its_cache(self):
        rec = sources.file_record("C:/f/run.bvh", "run", "", 10, fps=30.0)
        back = records.parse_payload({"assets": [dict(rec._asdict())]})[0]
        self.assertEqual(back, rec)

    def test_a_file_row_shows_its_folder_and_format(self):
        rec = sources.file_record("C:/f/clips/run.bvh", "run", "", 10, note="")
        row = records.format_row(rec)
        self.assertIn("C:/f/clips", row)
        self.assertTrue(row.rstrip().endswith("10 fr  bvh"))

    def test_an_unreal_row_is_unchanged(self):
        rec = records.AnimRecord("A", "/Game/X/A", "", 3, 0.1, 30.0)
        self.assertEqual(records.format_row(rec).split()[-2:], ["3", "fr"])


class Purity(unittest.TestCase):
    def test_the_readers_need_no_maya(self):
        code = ("import sys; sys.path.insert(0, %r); "
                "import maya_uebridge.sources, maya_uebridge.bvh, "
                "maya_uebridge.gltf, maya_uebridge.unityfiles; "
                "print('maya' in sys.modules)" % PLUGIN)
        out = subprocess.check_output([sys.executable, "-c", code], cwd=PLUGIN,
                                      stderr=subprocess.STDOUT).decode().strip()
        self.assertTrue(out.endswith("False"), out)


if __name__ == "__main__":
    unittest.main()
