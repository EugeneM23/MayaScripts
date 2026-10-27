"""The corners of maya_walk.meanpose and maya_walk.keyposes test_walkmeanpose and test_walk_keyposes leave: their
files read and written wrong, the geometry's degenerate cases, readings that must not be taken, a helper that
follows no bone, toes with a bone under them, a result that cannot be read. numpy only, no Maya."""

import copy
import math
import os
import shutil
import tempfile
import types
import unittest

import numpy as np

from tests import test_walkmodel as T

wm = T.wm
mp = T.load("meanpose")
kp = T.load("keyposes")


def angle_deg(r):
    return math.degrees(float(np.linalg.norm(wm.log_rot(r))))


class Folder(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="walkfix_")
        self.addCleanup(shutil.rmtree, self.folder, True)


# ---- meanpose ----

class MeanFileTests(Folder):

    def test_plain_data_of_another_format_or_a_newer_version_is_refused(self):
        self.assertTrue(mp.is_empty(mp.loads({})))
        self.assertTrue(mp.is_empty(mp.loads(None)))
        with self.assertRaises(mp.Refusal) as caught:
            mp.loads({"format": "something else", "version": 1}, "asd.walkfix.json")
        self.assertIn("asd.walkfix.json is not a correction this tool reads", str(caught.exception))
        with self.assertRaises(mp.Refusal):
            mp.loads({"format": mp.FORMAT, "version": mp.VERSION + 1})
        self.assertEqual(mp.dumps(mp.empty()), {})

    def test_a_file_that_is_not_json_is_refused_by_its_name(self):
        path = os.path.join(self.folder, "broken.walkfix.json")
        with open(path, "w") as handle:
            handle.write("{not json")
        with self.assertRaises(mp.Refusal) as caught:
            mp.load(path)
        self.assertIn("broken.walkfix.json is not a walk correction", str(caught.exception))

    def test_save_makes_its_folder_and_replaces_a_file_standing(self):
        path = os.path.join(self.folder, "new", "deeper", mp.path_for("asd.walk.gz"))
        fix = mp.empty()
        fix["height"] = 2.0
        mp.save(path, fix)
        fix["height"] = -6.5
        fix["toe"]["l"] = 0.3
        mp.save(path, fix)
        back = mp.load(path)
        self.assertEqual((back["height"], back["toe"]["l"]), (-6.5, 0.3))
        self.assertFalse(os.path.exists(path + ".part"))
        mp.save(os.path.join(self.folder, "never.walkfix.json"), mp.empty())       # nothing to remove: no error

    def test_path_for_a_name_without_the_walk_suffix(self):
        self.assertEqual(mp.path_for("C:/w/asd"), "C:/w/asd" + mp.SUFFIX)


class MeanGeometryTests(unittest.TestCase):

    def test_turn_between_the_same_opposite_and_any_two_directions(self):
        a = np.array([0.0, 2.0, 0.0])
        self.assertTrue(np.allclose(mp.turn_between(a, a * 5.0), np.eye(3)))
        flip = mp.turn_between(a, -a)
        self.assertTrue(np.allclose(np.array([0.0, 1.0, 0.0]) @ flip, [0.0, -1.0, 0.0]))
        self.assertAlmostEqual(angle_deg(flip), 180.0, places=6)
        b = np.array([1.0, 1.0, 0.0])
        r = mp.turn_between(a, b)
        self.assertTrue(np.allclose(np.array([0.0, 1.0, 0.0]) @ r, b / np.linalg.norm(b)))
        self.assertAlmostEqual(angle_deg(r), 45.0, places=6)

    def test_a_straight_leg_turns_the_least_way(self):
        h0, k0, a0 = np.zeros(3), np.array([0.0, -40.0, 0.0]), np.array([0.0, -80.0, 0.0])
        h1, k1, a1 = np.zeros(3), np.array([0.0, -40.0, 5.0]), np.array([0.0, -80.0, 10.0])
        rt, rc = mp._leg_turns(h0, k0, a0, h1, k1, a1)
        self.assertTrue(np.allclose(mp._unit(k0 - h0) @ rt, mp._unit(k1 - h1)))
        self.assertTrue(np.allclose(mp._unit(a0 - k0) @ rc, mp._unit(a1 - k1)))

    def test_a_straight_leg_reads_no_knee_turn_and_no_bend(self):
        straight = (np.zeros(3), np.array([0.0, -40.0, 0.0]), np.array([0.0, -80.0, 0.0]))
        bent = (np.zeros(3), np.array([0.0, -40.0, 8.0]), np.array([0.0, -78.0, 0.0]))
        self.assertEqual(mp.knee_turn(bent, straight), 0.0)
        self.assertEqual(mp.leg_bend((np.zeros(3), np.zeros(3), np.zeros(3))), 0.0)
        self.assertIsNone(mp._bend(np.zeros(3), np.array([0.0, -40.0, 0.0]), np.array([0.0, -80.0, 0.0])))
        b = mp._bend(np.zeros(3), np.array([0.0, -40.0, 8.0]), np.array([0.0, -80.0, 0.0]))
        self.assertTrue(np.allclose(b, [0.0, 0.0, 8.0]))

    def test_legs_fixed_leaves_a_skeleton_with_no_legs_as_it_is(self):
        walk = types.SimpleNamespace(index={"root": 0, "spine": 1}, parents=[-1, 0], up=np.array([0.0, 1.0, 0.0]))
        worlds = {0: np.eye(4), 1: np.eye(4)}
        mp._legs_fixed(walk, worlds, mp.model_fix(mp.empty()))
        self.assertEqual(sorted(worlds), [0, 1])
        self.assertTrue(np.allclose(worlds[1], np.eye(4)))


class MeanReadingTests(unittest.TestCase):

    def setUp(self):
        self.walk = T.walk()
        self.pose = mp.mean_pose(self.walk)

    def test_a_pose_missing_a_bone_reads_the_rest_and_one_with_no_root_reads_from_the_origin(self):
        pose = dict(self.pose)
        del pose["head"]
        m = mp.measure(pose, self.walk)
        self.assertNotIn("head", m["local"])
        self.assertIn("neck_01", m["local"])
        del pose["root"]
        m2 = mp.measure(pose, self.walk)
        self.assertAlmostEqual(m2["height"], float(self.pose["pelvis"][3, 1]), places=9)

    def test_a_bone_only_the_new_reading_holds_is_not_taken(self):
        base, now = mp.measure(self.pose, self.walk), mp.measure(self.pose, self.walk)
        del base["local"]["head"]
        now["local"]["head"] = T.rot_x(30) @ now["local"]["head"]
        fix, moved = mp.combine(mp.empty(), base, now)
        self.assertEqual((fix["rot"], moved), ({}, []))

    def test_a_knee_of_a_straight_leg_is_not_taken(self):
        base, now = mp.measure(self.pose, self.walk), mp.measure(self.pose, self.walk)
        hip, thigh, ankle = base["knee"]["l"]
        line = ankle - hip
        straight = (hip, line * (float(np.linalg.norm(thigh)) / float(np.linalg.norm(line))), ankle)
        now["knee"]["l"] = straight
        fix, moved = mp.combine(mp.empty(), base, now)
        self.assertEqual(fix["knee"]["l"], 0.0)
        self.assertNotIn("knee_l", [m[0] for m in moved])

    def test_a_turn_taken_back_drops_the_bone_from_the_correction(self):
        fix = mp.empty()
        fix["rot"]["spine_02"] = T.rot_x(10)
        base, now = mp.measure(self.pose, self.walk), mp.measure(self.pose, self.walk)
        now["local"]["spine_02"] = T.rot_x(-10) @ base["local"]["spine_02"]
        out, moved = mp.combine(fix, base, now)
        self.assertEqual(out["rot"], {})
        self.assertEqual([m[0] for m in moved], ["spine_02"])

    def test_describe_and_summary(self):
        self.assertEqual(mp.describe([]), "nothing moved")
        moved = [("a", 1.0, "deg"), ("b", -9.0, "deg"), ("c", 3.0, "deg"), ("d", 2.0, "deg"), ("e", 4.0, "deg"),
                 ("pelvis", -2.5, "cm"), ("width", 1.0, "cm")]
        self.assertEqual(mp.describe(moved), "b -9.0, e 4.0, c 3.0, d 2.0 deg (+1 more), pelvis -2.5 cm, width +1.0 cm")
        self.assertEqual(mp.describe(moved[-2:]), "pelvis -2.5 cm, width +1.0 cm")
        self.assertEqual(mp.summary(mp.empty()), "no correction")
        fix = mp.empty()
        fix["rot"] = {"spine_02": T.rot_x(5), "head": T.rot_y(3)}
        fix["height"], fix["width"] = -3.0, 2.0
        fix["knee"] = {"l": math.radians(10.0), "r": 0.0}
        fix["toe"] = {"l": 0.0, "r": math.radians(-20.0)}
        self.assertEqual(mp.summary(fix), "2 bones turned, pelvis -3.0 cm, width +2.0 cm, knees +10/+0, feet +0/-20")


def wobbled_clip():
    """The synthetic clip with its camera_root swaying against the root: a helper that follows no bone rigidly."""
    c = T.clip()
    j = c.names.index("camera_root")
    for f in range(c.worlds.shape[1]):
        c.worlds[j, f, 3, 0] += 3.0 * math.sin(2.0 * math.pi * f / 24.0)
    return c


class MeanCorrectTests(unittest.TestCase):

    def test_a_turn_on_the_root_is_not_put_in_the_frames(self):
        c = T.clip()
        fix = mp.empty()
        fix["rot"]["root"] = T.rot_y(30)
        fix["rot"]["head"] = T.rot_x(5)
        out = mp.correct(c, fix)
        j = c.names.index("root")
        self.assertTrue(np.allclose(out.worlds[j], c.worlds[j]))

    def test_a_helper_that_follows_no_bone_keeps_its_place_on_its_parent(self):
        c = wobbled_clip()
        fix = mp.empty()
        fix["rot"]["pelvis"] = T.rot_x(10)
        out = mp.correct(c, fix)
        j, p = c.names.index("camera_root"), c.names.index("root")
        for f in (0, 7, 13):
            before = c.worlds[j, f] @ np.linalg.inv(c.worlds[p, f])
            after = out.worlds[j, f] @ np.linalg.inv(out.worlds[p, f])
            self.assertLess(float(np.abs(before - after).max()), 1e-9)


# ---- keyposes ----

class KeyFileTests(Folder):

    def test_plain_data_read_and_written_strictly(self):
        self.assertEqual(kp.loads({}), {})
        with self.assertRaises(kp.Refusal) as caught:
            kp.loads({"format": "x"}, "asd.walkkeys.json")
        self.assertIn("asd.walkkeys.json are not key pose edits this tool reads", str(caught.exception))
        with self.assertRaises(kp.Refusal):
            kp.loads({"format": kp.FORMAT, "version": kp.VERSION + 1})
        data = {"format": kp.FORMAT, "version": 1,
                "keys": {"sideways": {"pelvis": [1, 2, 3]},
                         "down": {"pelvis": [0, 0, -2], "foot": {"l": {"t": [1, 0, 0]}}}}}
        keys = kp.loads(data)
        self.assertEqual(sorted(keys), ["down"])
        self.assertTrue(np.allclose(keys["down"]["foot"]["l"]["r"], np.eye(3)), "a foot with no turn: identity")
        self.assertTrue(np.allclose(keys["down"]["print"]["l"]["t"], 0.0))
        self.assertEqual(kp.dumps({}), {})
        keys["up"] = kp.empty_key()
        self.assertEqual(sorted(kp.dumps(keys)["keys"]), ["down"], "an empty key is not written")

    def test_a_file_that_is_not_json_and_save_into_a_new_folder(self):
        broken = os.path.join(self.folder, "x.walkkeys.json")
        with open(broken, "w") as handle:
            handle.write("[")
        with self.assertRaises(kp.Refusal) as caught:
            kp.load(broken)
        self.assertIn("x.walkkeys.json is not a key poses file", str(caught.exception))
        path = os.path.join(self.folder, "a", "b", kp.path_for("asd.walk.gz"))
        keys = {"down": kp.empty_key()}
        keys["down"]["pelvis"] = np.array([0.0, 0.0, -3.0])
        kp.save(path, keys)
        keys["down"]["pelvis"] = np.array([0.0, 0.0, -1.0])
        kp.save(path, keys)
        self.assertEqual(float(kp.load(path)["down"]["pelvis"][2]), -1.0)
        kp.save(path, {})
        self.assertFalse(os.path.exists(path))
        self.assertEqual(kp.path_for("plain"), "plain" + kp.SUFFIX)


def fake_walk(contact, P=24):
    return types.SimpleNamespace(P=P, contact=contact, placement_note="", index={"pelvis": 0},
                                 up=np.array([0.0, 1.0, 0.0]))


class KeyFindTests(unittest.TestCase):

    def test_feet_that_do_not_take_turns_are_refused(self):
        with self.assertRaises(kp.Refusal) as caught:
            kp.find(fake_walk({"l": [(3.0, 10.0)], "r": []}))
        self.assertIn("the feet do not take turns in this cycle (l)", str(caught.exception))
        with self.assertRaises(kp.Refusal):
            kp.find(fake_walk({"l": [(3.0, 10.0), (15.0, 20.0)], "r": [(9.0, 12.0)]}))

    def test_a_step_too_short_is_refused(self):
        with self.assertRaises(kp.Refusal) as caught:
            kp.find(fake_walk({"l": [(0.0, 1.0)], "r": [(2.0, 3.0)]}))
        self.assertIn("a step of 2 frames (the left foot's at frame 0): too short", str(caught.exception))

    def test_two_strikes_on_one_frame_make_a_whole_cycle_step(self):
        w = T.walk()
        w.contact = {"l": [(5.0, 14.0)], "r": [(5.0, 14.0)]}
        steps = kp.find(w)
        self.assertEqual([(s["side"], s["contact"], s["next"]) for s in steps], [("l", 5, 29), ("r", 5, 29)])

    def test_feet_that_never_pass_take_passing_where_they_come_nearest(self):
        """A strafe: read along the side axis the feet never cross."""
        w = copy.copy(T.walk())
        w.fwd = np.array(w.side, float)
        for s in kp.find(w):
            span = s["next"] - s["contact"]
            self.assertLessEqual(abs(s["passing"] - (s["contact"] + 0.5 * span)), span / 16.0 + 1.0)

    def test_bands_extremes_and_the_reference(self):
        self.assertEqual(kp._band(0, 5, 0.5), [2])
        self.assertEqual(kp._band(10, 16, 0.25), [13, 14, 15])
        self.assertEqual(kp._extreme([], lambda f: f, min, 3, 7), 5)
        self.assertEqual(kp._extreme([4, 5, 6], lambda f: 0.0, min, 2, 10), 6, "flat: the middle, kept in frames")
        self.assertEqual(kp.reference([{"side": "r", "contact": 3}])["contact"], 3)
        self.assertEqual(kp.yaw_of(np.eye(3), np.array([0.0, 1.0, 0.0])), 0.0)
        self.assertAlmostEqual(math.degrees(kp.yaw_of(T.rot_y(30), np.array([0.0, 1.0, 0.0]))), 30.0, places=6)


class KeyIncrementTests(unittest.TestCase):
    """Readings made by hand on the synthetic walk's ground (frame 5: the left foot down, the right in the air)."""

    def setUp(self):
        self.w = T.walk()
        self.f = 5

    def reading(self, pelvis=(0.0, 0.0, 0.0), knee_l=None, foot_r=np.eye(3), ball_l=np.eye(3)):
        hip, ankle = np.array([10.0, 85.0, 0.0]), np.array([10.0, 8.0, 0.0])
        bent = knee_l if knee_l is not None else np.array([0.0, -40.0, 14.0])
        knee = (hip, bent, ankle)
        return {"local": {"ball_l": ball_l}, "pelvis": np.array(pelvis, float),
                "knee": {"l": knee, "r": knee},
                "foot": {"l": (np.zeros(3), np.eye(3)), "r": (np.zeros(3), foot_r)}}

    def test_the_toes_of_a_leg_the_pelvis_pulled_straight_are_not_taken(self):
        base = self.reading()
        now = self.reading(pelvis=(0.0, 0.0, 6.0), knee_l=np.array([0.0, -38.5, 0.0]), ball_l=T.rot_x(15))
        now["local"]["head"] = T.rot_y(40)                   # a bone the base did not read: not taken either
        inc, moved, ignored = kp.increment("passing", base, now, self.w, self.f)
        self.assertNotIn("ball_l", inc["rot"])
        self.assertNotIn("head", inc["rot"])
        self.assertIn("leg_l at Passing is pulled straight by the pelvis", ignored[0])

    def test_a_foot_turned_in_the_air_is_its_turn(self):
        base = self.reading()
        now = self.reading(foot_r=T.rot_z(12))
        inc, moved, ignored = kp.increment("passing", base, now, self.w, self.f)
        self.assertAlmostEqual(angle_deg(inc["foot"]["r"]["r"]), 12.0, places=6)
        self.assertIn(("foot_r", 12.0), [(n, round(v, 6)) for n, v, _ in moved])

    def test_a_knee_turned_on_a_nearly_straight_leg_is_not_taken(self):
        base = self.reading(knee_l=np.array([0.0, -40.0, 3.0]))
        hip, thigh, ankle = base["knee"]["l"]
        e = mp._unit(hip - ankle)
        now = self.reading(knee_l=thigh @ wm.exp_rot(e * math.radians(25.0)))
        inc, moved, ignored = kp.increment("down", base, now, self.w, self.f)
        self.assertEqual(inc["knee"]["l"], 0.0)
        self.assertTrue(any("knee_l is nearly straight at Down" in i for i in ignored), ignored)

    def test_an_edit_added_back_out_drops_the_bone(self):
        inc = kp.empty_key()
        inc["rot"]["head"] = T.rot_x(8)
        keys = kp.add({}, "up", inc)
        back = kp.empty_key()
        back["rot"]["head"] = T.rot_x(-8)
        self.assertEqual(kp.add(keys, "up", back)["up"]["rot"], {})

    def test_a_split_needs_all_four_keys(self):
        incs = {"down": kp.empty_key(), "up": kp.empty_key()}
        common, out = kp.split_common(incs)
        self.assertEqual(common, {"forward": 0.0, "height": 0.0})
        self.assertIs(out, incs)

    def test_summary(self):
        self.assertEqual(kp.summary({}), "no key pose edited")
        entry = kp.empty_key()
        entry["pelvis"] = np.array([0.0, 0.0, 1.0])
        self.assertEqual(kp.summary({"up": entry, "contact": entry, "down": kp.empty_key()}), "Contact, Up edited")


def toed_clip():
    """The synthetic clip with a bone under each ball (its toe tip), riding it rigidly."""
    c = T.clip()
    names, parents = list(c.names), list(c.parents)
    worlds = [c.worlds]
    for side in ("l", "r"):
        b = names.index("ball_" + side)
        tip = np.eye(4)
        tip[3, :3] = (0.0, 0.0, 6.0)
        names.append("toe_tip_" + side)
        parents.append(b)
        worlds.append(np.einsum("ij,fjk->fik", tip, c.worlds[b])[None])
    return wm.Clip(names, parents, np.concatenate(worlds, axis=0), fps=30.0, up=(0, 1, 0), name="toed")


class KeyCorrectTests(unittest.TestCase):

    def test_the_bone_under_a_turned_ball_rides_it(self):
        w = wm.analyse(toed_clip())
        steps = kp.find(w)
        f = kp.frames_of(steps, w.P)["passing"]
        entry = kp.empty_key()
        entry["rot"]["ball_l"] = T.rot_x(25)
        out = kp.correct(w.clip, {"passing": entry}, steps, w)
        b, t = w.index["ball_l"], w.index["toe_tip_l"]
        rel = lambda clip: clip.worlds[t, f] @ np.linalg.inv(clip.worlds[b, f])
        self.assertLess(float(np.abs(rel(out) - rel(w.clip)).max()), 1e-9)
        ball = lambda clip: clip.worlds[b, f, :3, :3] @ clip.worlds[w.index["foot_l"], f, :3, :3].T
        self.assertAlmostEqual(angle_deg(ball(out) @ ball(w.clip).T), 25.0, places=6)

    def test_a_helper_that_follows_no_bone_keeps_its_place_on_its_parent(self):
        w = wm.analyse(wobbled_clip())
        steps = kp.find(w)
        entry = kp.empty_key()
        entry["pelvis"] = np.array([0.0, 0.0, -3.0])
        out = kp.correct(w.clip, {"down": entry}, steps, w)
        j, p = w.index["camera_root"], w.index["root"]
        for f in (0, 2, 11):
            before = w.clip.worlds[j, f] @ np.linalg.inv(w.clip.worlds[p, f])
            after = out.worlds[j, f] @ np.linalg.inv(out.worlds[p, f])
            self.assertLess(float(np.abs(before - after).max()), 1e-9)

    def test_a_turn_on_the_root_is_not_mirrored_onto_the_other_step(self):
        w = T.walk()
        steps = kp.find(w)
        entry = kp.empty_key()
        entry["rot"]["root"] = T.rot_y(20)
        entry["rot"]["nonesuch"] = T.rot_x(5)
        points = kp.knots({"contact": entry}, steps, w)
        mirrored = [values for (f, values), step in zip(points, [s for s in steps for _ in kp.KEYS])
                    if step["side"] != kp.REF_SIDE]
        own = [values for (f, values), step in zip(points, [s for s in steps for _ in kp.KEYS])
               if step["side"] == kp.REF_SIDE]
        self.assertTrue(all("root" not in v["rot"] for v in mirrored))
        self.assertIn("root", own[0]["rot"])
        self.assertTrue(all("nonesuch" not in v["rot"] for v in own + mirrored))

    def test_a_foot_with_no_stance_has_no_weight(self):
        w = types.SimpleNamespace(P=24, contact={"l": []})
        self.assertTrue(np.array_equal(kp.stance_weights(w, "l", 25), np.zeros(25)))
        self.assertTrue(np.array_equal(kp.stance_weights(w, "r", 25), np.zeros(25)))


class KeyResultTests(unittest.TestCase):

    def test_a_result_that_cannot_be_read_gets_no_edit_and_says_why(self):
        w = T.walk()
        worlds = np.array(w.clip.worlds, copy=True)
        worlds[:, -1, 3, :3] += 40.0                            # the loop does not close
        entry = kp.empty_key()
        entry["pelvis"] = np.array([0.0, 0.0, -3.0])
        out, rw, steps, note = kp.on_result(w, worlds, {"down": entry})
        self.assertTrue(np.array_equal(out, worlds))
        self.assertIsNone(rw)
        self.assertIsNone(steps)
        self.assertTrue(note.startswith("the key poses: "), note)

    def test_no_edit_reads_the_result_and_gives_its_frames_back(self):
        w = T.walk()
        out, rw, steps, note = kp.on_result(w, w.clip.worlds, {})
        self.assertTrue(np.array_equal(out, w.clip.worlds))
        self.assertEqual(note, "")
        self.assertEqual(len(steps), 2)
        self.assertEqual(rw.P, w.P)

    def test_in_place_nothing_asked_gives_the_frames_back(self):
        w = T.walk()
        worlds = w.clip.worlds
        self.assertIs(kp.in_place(worlds, w, 0.0), worlds)
        moved = kp.in_place(worlds, w, 1.0)
        root = w.index["root"]
        along = (moved[root, :, 3, :3] - moved[root, 0, 3, :3]) @ w.fwd
        self.assertLess(float(np.abs(along).max()), 1e-9)


if __name__ == "__main__":
    unittest.main()
