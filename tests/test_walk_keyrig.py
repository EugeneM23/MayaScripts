"""Walk Builder's key poses on four rigs (maya_walk.keyrig) on the fakes of test_walk_meanrig: no Maya scene.

The walker walks the synthetic walker; its key poses are found on it (keyposes.on_result) and its key edits put on
it with the real maths, so what a rig shows after an Update is what the walker then does."""

import contextlib
import io
import math
import unittest

import numpy as np

from tests import test_walkmodel as T
from tests.test_walk_meanrig import FakedTest, angle_deg, flat, mat, translate

wm = T.wm
mp = T.load("meanpose")
kp = T.load("keyposes")
wscene = T.load("scene")
keyrig = T.load("keyrig")
meanrig = T.load("meanrig")

FRAMES = {"contact": 23, "down": 2, "passing": 5, "up": 8}     # the synthetic walker's left step, its keys


def local_at(moving, walk, name, f):
    j = walk.index[name]
    R = moving[:, f, :3, :3]
    return wm.orthonormal(R[j]) @ wm.orthonormal(R[walk.parents[j]]).T


class KeyFaked(FakedTest):

    def setUp(self):
        FakedTest.setUp(self)
        self.walker("|walkerA", "UUID-A", at=(40.0, 0.0, -10.0))
        self.w.timed["|walkerA"] = lambda t: flat(translate(40.0, 0.0, -10.0 + 5.0 * t))     # walks along +Z
        self.rekeyed, self.shifted = [], []

    def rekey(self, root):
        self.rekeyed.append(root)
        return " -> %s keyed again" % root

    def shift(self, root, common):
        self.shifted.append((root, dict(common)))
        return ""

    def press(self):
        keyrig.press("|walkerA")
        return dict((keyrig.memo_of(r)["key"], r) for r in keyrig.rigs("|walkerA"))


class LineTests(KeyFaked):

    def test_a_walker_in_place_has_its_keys_in_a_line_along_z(self):
        self.assertEqual(keyrig.line_point((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 2), (-150.0, 0.0, 220.0))

    def test_a_diagonal_travel_is_made_a_direction(self):
        x, _, z = keyrig.line_point((10.0, 0.0, 20.0), (300.0, 5.0, 400.0), 1)
        # right of a (0.6, 0.8) travel is (-0.8, 0.6): 150 to the right, 110 along
        self.assertAlmostEqual(x, 10.0 + 150.0 * -0.8 + 110.0 * 0.6, places=9)
        self.assertAlmostEqual(z, 20.0 + 150.0 * 0.6 + 110.0 * 0.8, places=9)

    def test_the_travel_is_the_walker_s_root_over_the_playback_range(self):
        self.assertEqual(keyrig._travel("|walkerA"), (0.0, 0.0, 120.0))
        self.w.playback = (10.0, 10.1)
        self.assertEqual(keyrig._travel("|walkerA"), (0.0, 0.0, 1.0), "under a cm: in place, +Z")
        self.assertEqual(keyrig._travel("|nobody"), (0.0, 0.0, 1.0), "a root that cannot be read: +Z")

    def test_the_point_of_a_key_beside_the_walker(self):
        self.assertEqual(keyrig._point("|walkerA", 0), keyrig.line_point((40.0, 0.0, -10.0), (0.0, 0.0, 120.0), 0))
        self.assertEqual(keyrig._point("|walkerA", 3), (-110.0, 0.0, 320.0))
        self.assertEqual(keyrig._point("|gone", 1), (-150.0, 0.0, 110.0))
        self.assertEqual(keyrig._point(None, 0), (-150.0, 0.0, 0.0))


class CreateTests(KeyFaked):

    def test_create_adds_four_rigs_in_a_line_each_in_its_key_pose(self):
        self.w.selection = ["|walkerA"]
        line = keyrig.press("|walkerA")
        self.assertEqual([at for _, at in self.w.added], [keyrig._point("|walkerA", i) for i in range(4)])
        self.assertEqual(self.w.selection, ["|walkerA"])
        rigs = keyrig.rigs("|walkerA")
        self.assertEqual([keyrig.memo_of(r)["key"] for r in rigs], list(kp.KEYS))
        anim = self.scene.walker_animation("|walkerA")
        for rig in rigs:
            memo = keyrig.memo_of(rig)
            self.assertEqual((memo["walker"], memo["walk"]), ("UUID-A", "asd"))
            self.assertEqual(memo["frame"], FRAMES[memo["key"]])
            self.assertEqual(memo["poles"], {"l": {"ik": True, "t": [1.0, 2.0, 3.0]},
                                             "r": {"ik": True, "t": [1.0, 2.0, 3.0]}})
            self.assertEqual(len(memo["main0"]), 16)
            # the rig stands in the walker's frame: its base reads as that frame
            frame = dict((n, anim.moving[j, memo["frame"]]) for j, n in enumerate(anim.walk.names))
            inc, moved, ignored = kp.increment(memo["key"], kp.measure(frame, anim.rw),
                                               kp.measure(meanrig._unflat(memo["base"]), anim.rw), anim.rw,
                                               memo["frame"])
            self.assertEqual((moved, ignored), ([], []), memo["key"])
            for side in ("L", "R"):
                self.assertEqual(self.w.attrs["%s:FKIKLeg_%s" % (rig.namespace, side)]["FKIKBlend"], 10.0)
        self.assertEqual([name for _, name in self.w.posed],
                         ["walkerA - Contact", "walkerA - Down", "walkerA - Passing", "walkerA - Up"])
        self.assertEqual([text for _, text in self.w.labels],
                         ["walkerA - Contact (frame 23)", "walkerA - Down (frame 2)", "walkerA - Passing (frame 5)",
                          "walkerA - Up (frame 8)"])
        self.assertTrue(line.startswith("key poses of walkerA on 4 rigs (Contact 23, Down 2, Passing 5, Up 8; no key "
                                        "pose edited) - added Manny_Rig, Manny_Rig1, Manny_Rig2, Manny_Rig3"), line)
        self.assertIn(" - pose their controls, then Update | 1 not posed", line)
        self.assertIn(("|walkerA", True), self.scene.anim_calls)
        self.assertTrue(all(unrecorded for plug, _, unrecorded in self.w.writes
                            if plug.endswith((keyrig.MARKER, ".FKIKBlend"))))

    def test_a_second_press_poses_the_walker_s_own_rigs_again(self):
        rigs = self.press()
        self.w.turn(rigs["down"].namespace, "head", T.rot_x(20))
        line = keyrig.press("|walkerA")
        self.assertEqual(len(self.w.rigs), 4)
        self.assertNotIn("added", line)
        self.assertEqual(keyrig.update(self.rekey), keyrig.NOTHING_MOVED, "the turned head stood back")

    def test_two_walkers_have_four_rigs_each(self):
        self.walker("|walkerB", "UUID-B", at=(-300.0, 0.0, 0.0))
        keyrig.press("|walkerA")
        keyrig.press("|walkerB")
        self.assertEqual(len(keyrig.rigs()), 8)
        self.assertEqual([keyrig.memo_of(r)["walker"] for r in keyrig.rigs()], ["UUID-A"] * 4 + ["UUID-B"] * 4)
        self.assertEqual([keyrig.memo_of(r)["key"] for r in keyrig.rigs("|walkerB")], list(kp.KEYS))
        self.assertIs(keyrig.find("|walkerB", "passing"), keyrig.rigs("|walkerB")[2])
        self.assertIsNone(keyrig.find("|walkerC", "passing"))

    def test_no_walker_and_no_steps_are_refused(self):
        with self.assertRaises(keyrig.Refusal) as caught:
            keyrig.press(None)
        self.assertEqual(str(caught.exception), meanrig.NO_WALKER)
        self.scene.no_steps = "the left foot never lifts"
        with self.assertRaises(keyrig.Refusal) as caught:
            keyrig.press("|walkerA")
        self.assertEqual(str(caught.exception), "no key poses in walkerA's walk: the left foot never lifts")
        self.scene.no_steps = ""
        with self.assertRaises(keyrig.Refusal) as caught:
            keyrig.press("|walkerA")
        self.assertIn("its steps were not read", str(caught.exception))
        self.assertEqual(self.w.rigs, [])

    def test_add_character_adding_no_rig_is_refused(self):
        from maya_scenesetup import character
        character.add_character = lambda entry=None, rgb=None, at=None: "nothing came out"
        with self.assertRaises(keyrig.Refusal) as caught:
            keyrig.press("|walkerA")
        self.assertIn("no Manny rig was added: nothing came out", str(caught.exception))

    def test_a_label_that_fails_does_not_fail_the_press(self):
        self.w.label_error = "no annotation"
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            line = keyrig.press("|walkerA")
        self.assertIn("on 4 rigs", line)
        self.assertEqual(stderr.getvalue().count("no annotation"), 4)

    def test_rigs_are_sorted_walker_then_key(self):
        rigs = self.press()
        keyrig._set_memo(rigs["contact"], dict(keyrig.memo_of(rigs["contact"]), key="nonsense"))
        self.assertEqual([keyrig.memo_of(r)["key"] for r in keyrig.rigs()], ["down", "passing", "up", "nonsense"])


class LegsTests(KeyFaked):

    def test_legs_stand_in_ik_where_the_blend_can_be_set(self):
        rig = self.w.add_rig()
        self.w.locked.add(rig.namespace + ":FKIKLeg_R.FKIKBlend")
        del self.w.attrs[rig.namespace + ":FKIKLeg_L"]
        keyrig._legs_ik(rig)
        self.assertEqual(self.w.attrs[rig.namespace + ":FKIKLeg_R"]["FKIKBlend"], 0.0)

    def test_a_blend_that_cannot_be_asked_is_left_alone(self):
        rig = self.w.add_rig()

        def broken(plug, settable=False, time=None):
            raise RuntimeError("Maya command error")
        self.f.cmds.getAttr = broken
        keyrig._legs_ik(rig)
        self.assertEqual(self.w.attrs[rig.namespace + ":FKIKLeg_L"]["FKIKBlend"], 0.0)

    def test_a_memo_that_is_not_json_reads_empty(self):
        rig = self.w.add_rig()
        self.assertEqual(keyrig.memo_of(rig), {})
        self.w.attrs[rig.main][keyrig.MARKER] = "{oops"
        self.assertEqual(keyrig.memo_of(rig), {})

    def test_poles_read_as_the_rig_stands_and_a_leg_that_cannot_be_read_is_none(self):
        rig = self.w.add_rig()
        self.w.attrs[rig.namespace + ":FKIKLeg_L"]["FKIKBlend"] = 10.0
        del self.w.attrs[rig.namespace + ":PoleLeg_R"]
        self.assertEqual(keyrig._poles(rig), {"l": {"ik": True, "t": [1.0, 2.0, 3.0]},
                                              "r": {"ik": False, "t": None}})

    def test_knees_taken(self):
        still = {"l": {"ik": True, "t": [1.0, 2.0, 3.0]}, "r": {"ik": True, "t": [1.0, 2.0, 3.0]}}
        self.assertIsNone(keyrig.knees_taken(None, still))
        self.assertEqual(keyrig.knees_taken(still, still), {"l": False, "r": False})
        moved = {"l": {"ik": True, "t": [1.0, 2.0, 3.5]}, "r": {"ik": False, "t": [1.0, 2.0, 3.0]}}
        self.assertEqual(keyrig.knees_taken(still, moved), {"l": True, "r": True})
        self.assertEqual(keyrig.knees_taken(still, {"l": still["l"], "r": {"ik": True, "t": None}}),
                         {"l": False, "r": True})


class UpdateTests(KeyFaked):

    def setUp(self):
        KeyFaked.setUp(self)
        self.rigs = self.press()

    def test_no_rig_is_refused(self):
        self.w.rigs = []
        with self.assertRaises(keyrig.Refusal) as caught:
            keyrig.update(self.rekey, self.shift)
        self.assertEqual(str(caught.exception), keyrig.NO_RIG)

    def test_nothing_moved_writes_nothing(self):
        self.assertEqual(keyrig.update(self.rekey, self.shift), keyrig.NOTHING_MOVED)
        self.assertEqual((self.scene.edit_calls, self.rekeyed, self.shifted), ([], [], []))

    def test_a_bone_turned_on_one_rig_is_that_key_s_edit_and_the_walker_shows_it(self):
        anim0 = self.scene.walker_animation("|walkerA")
        self.w.turn(self.rigs["contact"].namespace, "spine_02", T.rot_x(10))
        line = keyrig.update(self.rekey, self.shift)
        self.assertEqual(line, "key poses of walkerA: Contact: spine_02 10.0 deg -> |walkerA keyed again")
        self.assertEqual((self.rekeyed, self.shifted), (["|walkerA"], []))
        keys = self.scene.edits["|walkerA"]["keys"]
        self.assertEqual(sorted(keys), ["contact"])
        self.assertEqual(sorted(keys["contact"]["rot"]), ["spine_02"])
        self.assertAlmostEqual(angle_deg(keys["contact"]["rot"]["spine_02"]), 10.0, places=5)
        # the walker shows it at the contact, exactly, and nothing at the other keys of the left step
        anim = self.scene.walker_animation("|walkerA")
        f = FRAMES["contact"]
        turned = local_at(anim.moving, anim.walk, "spine_02", f) @ local_at(anim0.moving, anim.walk, "spine_02", f).T
        self.assertAlmostEqual(angle_deg(turned), 10.0, places=4)
        for key in ("down", "passing", "up"):
            g = FRAMES[key]
            other = local_at(anim.moving, anim.walk, "spine_02", g) @ local_at(anim0.moving, anim.walk, "spine_02", g).T
            self.assertLess(angle_deg(other), 1e-6, key)
        # the rig was stood again in what the walker now does: a second Update finds nothing
        self.assertEqual(keyrig.update(self.rekey, self.shift), keyrig.NOTHING_MOVED)
        self.assertEqual(self.rekeyed, ["|walkerA"])

    def test_two_keys_edited_at_once(self):
        self.w.turn(self.rigs["down"].namespace, "head", T.rot_y(15))
        self.w.turn(self.rigs["up"].namespace, "upperarm_l", T.rot_z(-12))
        line = keyrig.update(self.rekey, self.shift)
        self.assertIn("Down: head 15.0 deg", line)
        self.assertIn("Up: upperarm_l 12.0 deg", line)
        self.assertEqual(sorted(self.scene.edits["|walkerA"]["keys"]), ["down", "up"])

    def test_the_pelvis_lowered_alike_on_all_four_is_the_whole_walk_s_height(self):
        for rig in self.rigs.values():
            self.w.lower(rig.namespace, -4.0)
        line = keyrig.update(self.rekey, self.shift)
        self.assertEqual(len(self.shifted), 1)
        root, common = self.shifted[0]
        self.assertEqual(root, "|walkerA")
        self.assertAlmostEqual(common["height"], -4.0, places=4)
        self.assertAlmostEqual(common["forward"], 0.0, places=6)
        self.assertTrue(kp.is_empty(self.scene.edits["|walkerA"]["keys"]), "nothing left for the keys")
        self.assertIn("| on all four: Height -4.0 cm (the walk moves +0.0 cm)", line)
        self.assertNotIn("legs reach no further", line, "a lowered pelvis is not about the legs' reach")
        self.assertTrue(line.endswith(" -> |walkerA keyed again"), line)
        self.assertEqual(len(self.w.posed), 8, "every rig stood again")
        self.assertEqual(keyrig.update(self.rekey, self.shift), keyrig.NOTHING_MOVED)

    def test_a_raised_pelvis_the_walk_does_not_follow_says_its_legs_reach_no_further(self):
        for rig in self.rigs.values():
            self.w.lower(rig.namespace, 2.0)
        line = keyrig.update(self.rekey, self.shift)
        self.assertIn("on all four: Height +2.0 cm (the walk moves +0.0 cm - its legs reach no further, a shorter "
                      "Step raises it more)", line)

    def test_the_default_shift_moves_the_walker_s_own_parameters(self):
        self.scene.memos["|walkerA"]["params"] = {"changes": {"height": ["offset", -1.0]}, "pins": ["height"]}
        for rig in self.rigs.values():
            self.w.lower(rig.namespace, -4.0)
        line = keyrig.update(self.rekey)
        params = self.scene.memos["|walkerA"]["params"]
        self.assertEqual(params["changes"]["height"][0], "offset")
        self.assertAlmostEqual(params["changes"]["height"][1], -5.0, places=4)
        self.assertIn("height", params["pins"])
        self.assertIn("(Height now -5.0 cm, the walk moves +0.0 cm)", line)
        self.assertAlmostEqual(keyrig._height_of("|walkerA"), -5.0, places=4)

    def test_a_planted_foot_lifted_is_not_taken_and_the_rig_stands_again(self):
        self.w.move_foot(self.rigs["down"].namespace, "l", (0.0, 2.0, 0.0))
        line = keyrig.update(self.rekey, self.shift)
        self.assertEqual(line, "key poses of walkerA: nothing taken | not taken: foot_l stands on the ground at Down: "
                               "lifted 2.0 cm, not taken (a planted foot stays on the ground)")
        self.assertEqual(self.rekeyed, [])
        self.assertTrue(kp.is_empty(self.scene.edits["|walkerA"]["keys"]))
        self.assertEqual(keyrig.update(self.rekey, self.shift), keyrig.NOTHING_MOVED, "stood back where it was")

    def test_a_planted_foot_moved_alike_on_two_rigs_is_one_print(self):
        """The left foot stands through Down and Passing: moved 3 cm forward on both rigs, it is one move of its
        print, not two."""
        for key in ("down", "passing"):
            self.w.move_foot(self.rigs[key].namespace, "l", (0.0, 0.0, 3.0))
        line = keyrig.update(self.rekey, self.shift)
        self.assertIn("Down: foot_l print +3.0 cm; Passing: foot_l print +3.0 cm", line)
        prints = kp.stance_prints(self.scene.edits["|walkerA"]["keys"])
        self.assertAlmostEqual(float(prints["l"]["t"][0]), 3.0, places=4)
        self.assertAlmostEqual(float(np.linalg.norm(prints["l"]["t"])), 3.0, places=4)

    def test_main_moved_by_hand_is_nothing_moved(self):
        for rig in self.rigs.values():
            self.w.move_main(rig.namespace, wm.matrix(T.rot_y(25), [500.0, 0.0, 80.0]))
        self.assertEqual(keyrig.update(self.rekey, self.shift), keyrig.NOTHING_MOVED)

    def test_a_foot_in_the_air_moved_is_taken(self):
        self.w.move_foot(self.rigs["passing"].namespace, "r", (0.0, 3.0, 0.0))
        line = keyrig.update(self.rekey, self.shift)
        self.assertIn("Passing: foot_r +3.0 cm", line)
        foot = self.scene.edits["|walkerA"]["keys"]["passing"]["foot"]["r"]
        self.assertAlmostEqual(float(foot["t"][2]), 3.0, places=4)

    def test_a_knee_is_taken_only_when_its_pole_moved(self):
        ns = self.rigs["passing"].namespace
        self.w.turn_knee(ns, "l", 20.0)
        self.assertEqual(keyrig.update(self.rekey, self.shift), keyrig.NOTHING_MOVED,
                         "the pole stayed: the IK leg turned by itself")
        keyrig.press("|walkerA")                                     # stood again in the walker's passing
        self.w.turn_knee(ns, "l", 20.0)
        self.w.attrs[ns + ":PoleLeg_L"]["translate"] = [(1.0, 2.0, 9.0)]
        line = keyrig.update(self.rekey, self.shift)
        self.assertIn("Passing: knee_l", line)
        self.assertAlmostEqual(abs(math.degrees(self.scene.edits["|walkerA"]["keys"]["passing"]["knee"]["l"])), 20.0,
                               delta=0.5)

    def test_more_than_two_things_not_taken_are_counted(self):
        for key in ("contact", "down", "passing"):                  # the left foot planted at all three
            self.w.move_foot(self.rigs[key].namespace, "l", (0.0, 2.0, 0.0))
        line = keyrig.update(self.rekey, self.shift)
        self.assertIn("not taken: ", line)
        self.assertIn("(+1 more)", line)

    def test_a_rig_with_no_base_takes_what_it_shows_as_its_base(self):
        keyrig._set_memo(self.rigs["up"], dict(keyrig.memo_of(self.rigs["up"]), base={}))
        self.w.turn(self.rigs["up"].namespace, "head", T.rot_x(9))
        self.assertEqual(keyrig.update(self.rekey, self.shift), keyrig.NOTHING_MOVED)
        self.assertTrue(keyrig.memo_of(self.rigs["up"])["base"])

    def test_a_rig_of_no_key_is_left_alone(self):
        keyrig._set_memo(self.rigs["up"], dict(keyrig.memo_of(self.rigs["up"]), key="nonsense"))
        self.w.turn(self.rigs["up"].namespace, "head", T.rot_x(9))
        self.assertEqual(keyrig.update(self.rekey, self.shift), keyrig.NOTHING_MOVED)

    def test_a_rig_of_no_key_beside_a_whole_walk_change_is_left_alone(self):
        """Fixed 2026-10-27, the bug as it was (keyrig.update, the loop that stands the rigs again): a whole-walk change (the pelvis alike on all four
        keys) sets `stood_again = own` - every rig of the walker, the one whose memo names no key of KEYS too, which
        the reading loop skipped - and `frames[key]` then raises KeyError: Update dies instead of leaving it alone."""
        for rig in self.rigs.values():
            self.w.lower(rig.namespace, -4.0)
        stray = self.w.add_rig(at=(900.0, 0.0, 0.0))
        keyrig._set_memo(stray, dict(keyrig.memo_of(self.rigs["up"]), key="flight"))
        line = keyrig.update(self.rekey, self.shift)
        self.assertIn("on all four: Height -4.0 cm", line)

    def test_rigs_stood_by_an_older_build_are_stood_again_and_read_nothing(self):
        for key in ("contact", "down"):
            memo = keyrig.memo_of(self.rigs[key])
            keyrig._set_memo(self.rigs[key], dict((k, memo[k]) for k in ("walker", "walk", "key", "frame", "base")))
        self.w.turn(self.rigs["contact"].namespace, "spine_02", T.rot_x(10))
        line = keyrig.update(self.rekey, self.shift)
        self.assertEqual(line, "Manny_Rig, Manny_Rig1 stood by an older build: stood again in walkerA's animation, "
                               "nothing read - pose them again, then Update")
        self.assertEqual(self.scene.edit_calls, [])
        self.assertIn("main0", keyrig.memo_of(self.rigs["contact"]))
        self.assertEqual(keyrig.update(self.rekey, self.shift), keyrig.NOTHING_MOVED)

    def test_older_rigs_beside_an_edit_are_stood_after_it(self):
        memo = keyrig.memo_of(self.rigs["down"])
        keyrig._set_memo(self.rigs["down"], dict((k, memo[k]) for k in ("walker", "walk", "key", "frame", "base")))
        self.w.turn(self.rigs["up"].namespace, "head", T.rot_x(9))
        line = keyrig.update(self.rekey, self.shift)
        self.assertIn("Manny_Rig1 stood by an older build", line)
        self.assertIn("key poses of walkerA: Up: head 9.0 deg", line)
        self.assertIn("main0", keyrig.memo_of(self.rigs["down"]))
        self.assertEqual(keyrig.update(self.rekey, self.shift), keyrig.NOTHING_MOVED)

    def test_rigs_whose_walker_is_gone_say_so(self):
        for rig in self.rigs.values():
            keyrig._set_memo(rig, dict(keyrig.memo_of(rig), walker="UUID-GONE"))
        self.assertEqual(keyrig.update(self.rekey, self.shift),
                         "key poses Manny_Rig, Manny_Rig1, Manny_Rig2, Manny_Rig3 stand for no walker in the scene - "
                         "Delete them and Create again")

    def test_a_walk_whose_steps_cannot_be_read_says_why(self):
        self.scene.no_steps = "the feet do not take turns"
        self.assertEqual(keyrig.update(self.rekey, self.shift),
                         "no key poses in walkerA's walk: the feet do not take turns")

    def test_each_walker_s_rigs_move_their_own_walker(self):
        self.walker("|walkerB", "UUID-B", at=(-300.0, 0.0, 0.0))
        keyrig.press("|walkerB")
        down_b = keyrig.find("|walkerB", "down")
        self.w.turn(down_b.namespace, "head", T.rot_y(-11))
        line = keyrig.update(self.rekey, self.shift)
        self.assertEqual(line, "key poses of walkerB: Down: head 11.0 deg -> |walkerB keyed again")
        self.assertNotIn("|walkerA", self.scene.edits)

    def test_the_default_rekey_keys_the_walker_as_it_was_keyed_last(self):
        self.w.turn(self.rigs["down"].namespace, "head", T.rot_y(15))
        line = keyrig.update()
        self.assertTrue(line.endswith(" -> walkerA keyed again"), line)
        self.assertEqual(self.scene.applied[-1]["record"], False)


class LineHelperTests(KeyFaked):

    def test_common_line(self):
        self.assertEqual(keyrig.common_line({"height": 5.0, "forward": -2.0}),
                         "on all four: Height +5.0 cm, Forward -2.0 cm")
        self.assertEqual(keyrig.common_line({"height": 0.0, "forward": 0.0}), "")
        self.assertEqual(keyrig.common_line({}), "")

    def test_height_of(self):
        self.assertEqual(keyrig._height_of("|walkerA"), None, "a memo with no parameters: unread")
        self.scene.memos["|walkerA"]["params"] = {"changes": {}}
        self.assertEqual(keyrig._height_of("|walkerA"), 0.0)
        self.scene.memos["|walkerA"]["params"] = {"changes": {"height": ["offset", 2.5]}}
        self.assertEqual(keyrig._height_of("|walkerA"), 2.5)

    def test_pelvis_height_is_the_mean_over_the_cycle(self):
        anim = self.scene.walker_animation("|walkerA")
        j = anim.walk.index["pelvis"]
        self.assertAlmostEqual(keyrig._pelvis_height(anim), float(np.mean(anim.moving[j, :-1, 3, 1])), places=9)

    def test_shift_memo_pins_the_walk_s_height_and_forward(self):
        self.assertEqual(keyrig.shift_memo("|walkerA", {"height": 3.0, "forward": -1.5}), "")
        params = self.scene.memos["|walkerA"]["params"]
        self.assertEqual(params["changes"]["height"], ["offset", 3.0])
        self.assertEqual(params["changes"]["forward"], ["offset", -1.5])
        self.assertEqual(params["pins"], ["forward", "height"])


class ResetDeleteTests(KeyFaked):

    def test_reset_drops_the_key_edits_and_stands_the_rigs_in_the_plain_key_poses(self):
        rigs = self.press()
        self.w.turn(rigs["contact"].namespace, "spine_02", T.rot_x(10))
        keyrig.update(self.rekey, self.shift)
        line = keyrig.reset("|walkerA", rekey=self.rekey)
        self.assertEqual(line, "walkerA: the key poses' edits dropped, the key rigs back in its key poses -> "
                               "|walkerA keyed again")
        self.assertTrue(kp.is_empty(self.scene.edits["|walkerA"]["keys"]))
        self.assertEqual(self.rekeyed, ["|walkerA", "|walkerA"])
        anim = self.scene.walker_animation("|walkerA")
        f = FRAMES["contact"]
        base = mp.measure(meanrig._unflat(keyrig.memo_of(rigs["contact"])["base"]), anim.walk)
        frame = mp.measure(dict((n, anim.moving[j, f]) for j, n in enumerate(anim.walk.names)), anim.walk)
        self.assertEqual(mp.combine(mp.empty(), frame, base)[1], [], "the rig back in the plain contact")

    def test_reset_with_nothing_edited_keys_nothing(self):
        line = keyrig.reset("|walkerA", rekey=self.rekey)
        self.assertEqual(line, "walkerA has no key pose edited")
        self.assertEqual(self.rekeyed, [])
        self.assertEqual(self.w.rigs, [])
        with self.assertRaises(keyrig.Refusal):
            keyrig.reset(None)

    def test_delete_takes_the_walker_s_rigs_and_keeps_its_edits(self):
        rigs = self.press()
        self.w.turn(rigs["contact"].namespace, "spine_02", T.rot_x(10))
        keyrig.update(self.rekey, self.shift)
        line = keyrig.delete("|walkerA")
        self.assertEqual(line, "key poses of walkerA deleted (Deleted Manny_Rig, Manny_Rig1, Manny_Rig2, Manny_Rig3 - "
                               "400 nodes) - the walker keeps their edits")
        self.assertEqual(self.w.delete_calls[0][1], True)
        self.assertEqual(self.w.rigs, [])
        self.assertIn("contact", self.scene.edits["|walkerA"]["keys"])

    def test_delete_with_no_walker_takes_the_only_owner_s_rigs(self):
        self.press()
        self.assertIn("key poses of walkerA deleted", keyrig.delete())
        self.walker("|walkerB", "UUID-B")
        self.press()
        self.assertIn("key poses of walkerA deleted", keyrig.delete("|walkerB"))

    def test_delete_when_several_walkers_own_rigs_is_refused(self):
        self.walker("|walkerB", "UUID-B")
        self.walker("|walkerC", "UUID-C")
        keyrig.press("|walkerA")
        keyrig.press("|walkerB")
        with self.assertRaises(keyrig.Refusal) as caught:
            keyrig.delete("|walkerC")
        self.assertEqual(str(caught.exception), "walkerC has no key poses - 2 other walkers have some (click one in "
                                                "the list)")
        with self.assertRaises(keyrig.Refusal) as caught:
            keyrig.delete()
        self.assertIn("the working walker has no key poses", str(caught.exception))

    def test_delete_with_no_rig(self):
        with self.assertRaises(keyrig.Refusal) as caught:
            keyrig.delete("|walkerA")
        self.assertEqual(str(caught.exception), "no key poses in the scene")


if __name__ == "__main__":
    unittest.main()
