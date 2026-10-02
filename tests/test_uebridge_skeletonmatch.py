"""The Auto card's matcher (2026-10-02): is a clip's skeleton one of our characters'?"""
import hashlib
import os
import subprocess
import sys
import unittest

from maya_uebridge import skeletonmatch as sm

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SkeldarAnim")

# A small chain: root > pelvis > spine > neck > head, and an arm off the spine.
_REST = {
    "root": (None, (0.0, 0.0, 0.0)),
    "pelvis": ("root", (0.0, 100.0, 0.0)),
    "spine_01": ("pelvis", (0.0, 120.0, 0.0)),
    "neck_01": ("spine_01", (0.0, 150.0, 0.0)),
    "head": ("neck_01", (0.0, 165.0, 0.0)),
    "clavicle_l": ("spine_01", (5.0, 140.0, 0.0)),
    "upperarm_l": ("clavicle_l", (18.0, 140.0, 0.0)),
    "lowerarm_l": ("upperarm_l", (45.0, 140.0, 0.0)),
    "hand_l": ("lowerarm_l", (72.0, 140.0, 0.0)),
    "thigh_l": ("pelvis", (10.0, 95.0, 0.0)),
    "calf_l": ("thigh_l", (10.0, 52.0, 0.0)),
    "foot_l": ("calf_l", (10.0, 9.0, 0.0)),
    "ball_l": ("foot_l", (10.0, 2.0, 12.0)),
    "ik_hand_l": ("root", (72.0, 140.0, 0.0)),
}


def clip_of(template, scale=1.0, frames=3, offset=(0.0, 0.0, 0.0), only=None):
    """The template as a clip: every frame the rest, scaled about the origin and moved."""
    out = {}
    for bone, (parent, pos) in template.items():
        if only is not None and bone not in only:
            continue
        # a bone the clip lacks is not in its hierarchy: its children hang off the next one up
        while only is not None and parent is not None and parent not in only:
            parent = template[parent][0]
        point = tuple(scale * c + o for c, o in zip(pos, offset))
        out[bone] = (parent, [point] * frames)
    return out


class Score(unittest.TestCase):

    def test_a_clip_of_the_skeleton_itself_scores_all_its_voters(self):
        found = sm.score(clip_of(_REST), _REST, "A")
        # root, pelvis and the ik_ helper do not vote; 11 bones do
        self.assertEqual((found.key, found.share, found.count), ("A", 1.0, 11))

    def test_a_scaled_clip_scores_nothing(self):
        found = sm.score(clip_of(_REST, scale=1.1), _REST)
        self.assertEqual(found.share, 0.0)
        self.assertEqual(found.count, 11)

    def test_a_moved_clip_is_still_the_skeleton(self):
        self.assertEqual(sm.score(clip_of(_REST, offset=(300.0, 0.0, -80.0)), _REST).share, 1.0)

    def test_helpers_never_vote(self):
        self.assertFalse(sm.votes("ik_hand_l"))
        self.assertFalse(sm.votes("weapon_r"))
        self.assertFalse(sm.votes("camera_root"))
        self.assertFalse(sm.votes("pelvis"))
        self.assertFalse(sm.votes("root"))
        self.assertTrue(sm.votes("hand_l"))

    def test_the_length_is_the_median_over_the_frames(self):
        clip = clip_of(_REST)
        parent, frames = clip["hand_l"]
        # one frame of three slides the hand 10 cm: the median keeps the bone its length
        clip["hand_l"] = (parent, [frames[0], (82.0, 140.0, 0.0), frames[2]])
        self.assertEqual(sm.score(clip, _REST).share, 1.0)

    def test_a_bone_whose_anchors_differ_does_not_vote(self):
        clip = clip_of(_REST)
        # the clip hangs the hand off the clavicle: no common anchor to measure against
        clip["hand_l"] = ("clavicle_l", clip["hand_l"][1])
        self.assertEqual(sm.score(clip, _REST).count, 10)

    def test_missing_bones_are_bridged_to_the_nearest_shared_one(self):
        only = set(_REST) - {"lowerarm_l"}
        found = sm.score(clip_of(_REST, only=only), _REST)
        # hand_l is measured to upperarm_l on both sides
        self.assertEqual((found.share, found.count), (1.0, 10))

    def test_short_bones_do_not_vote(self):
        rest = dict(_REST, tip_l=("hand_l", (72.5, 140.0, 0.0)))
        self.assertEqual(sm.score(clip_of(rest), rest).count, 11)

    def test_nothing_in_common_scores_zero_of_zero(self):
        found = sm.score({"Hips": (None, [(0.0, 0.0, 0.0)])}, _REST, "A")
        self.assertEqual((found.share, found.count), (0.0, 0))

    def test_a_cycle_in_a_parent_map_does_not_hang(self):
        parents = {"a": "b", "b": "a"}
        self.assertIsNone(sm.anchor("a", parents, set(["c"])))


class Match(unittest.TestCase):

    def setUp(self):
        self.big = dict((bone, (parent, tuple(1.3 * c for c in pos)))
                        for bone, (parent, pos) in _REST.items())
        self.templates = {"A": _REST, "B": self.big}

    def test_the_best_row_matches(self):
        found = sm.match(clip_of(self.big), self.templates, ["A", "B"])
        self.assertEqual(found.key, "B")
        self.assertEqual([s.key for s in found.scores], ["A", "B"])

    def test_only_the_rows_asked_take_part(self):
        found = sm.match(clip_of(self.big), self.templates, ["A"])
        self.assertIsNone(found.key)
        self.assertEqual(found.best.key, "A")

    def test_too_few_voters_decide_nothing(self):
        only = ("root", "pelvis", "spine_01", "neck_01", "head", "clavicle_l")
        found = sm.match(clip_of(_REST, only=only), self.templates, ["A", "B"])
        self.assertEqual(found.best.count, 4)
        self.assertIsNone(found.key)

    def test_under_the_share_nothing_matches(self):
        clip = clip_of(_REST)
        for bone in ("head", "hand_l", "calf_l", "foot_l"):
            parent, frames = clip[bone]
            clip[bone] = (parent, [tuple(c * 1.5 for c in frames[0])] * 3)
        found = sm.match(clip, self.templates, ["A"])
        self.assertLess(found.best.share, sm.MIN_SHARE)
        self.assertIsNone(found.key)

    def test_ties_go_to_the_first_row_asked(self):
        found = sm.match(clip_of(_REST), {"A": _REST, "C": dict(_REST)}, ["C", "A"])
        self.assertEqual(found.key, "C")

    def test_no_template_no_best(self):
        found = sm.match(clip_of(_REST), {}, ["A"])
        self.assertEqual((found.key, found.best, found.scores), (None, None, []))


class Wording(unittest.TestCase):

    def test_a_match_names_the_row_and_the_bones(self):
        found = sm.Match("Manny_Rig", sm.Score("Manny_Rig", 1.0, 78, 0.0), [])
        self.assertEqual(sm.match_text(found, lambda key: "Manny [rig]"),
                         "matched Manny [rig] - 78 of 78 bones")

    def test_a_miss_names_the_best_and_its_share(self):
        found = sm.Match(None, sm.Score("Orc_D_Rig", 0.45, 78, 0.02), [])
        self.assertEqual(sm.match_text(found, lambda key: "Orc D [rig]"),
                         "no skeleton of ours (best Orc D [rig]: 45 % of 78 bones)")

    def test_a_clip_named_like_nobody(self):
        self.assertEqual(sm.match_text(sm.Match(None, None, [])),
                         "no skeleton of ours (no bone named as ours)")


class ShippedTemplates(unittest.TestCase):
    """assets/character_skeletons.json against the catalog and the assets it was read from."""

    @classmethod
    def setUpClass(cls):
        from maya_scenesetup import catalog
        cls.catalog = catalog
        cls.templates = sm.load_templates()
        import json
        with open(sm.TEMPLATES_PATH) as handle:
            cls.payload = json.load(handle)

    def test_every_catalog_row_has_a_template(self):
        self.assertEqual(sorted(self.templates), sorted(self.catalog.character_keys()))

    def test_each_template_was_read_from_the_shipped_asset(self):
        for entry in self.catalog.CHARACTERS:
            row = self.payload["rows"][entry.key]
            self.assertEqual(row["file"], entry.file)
            digest = hashlib.sha1()
            with open(self.catalog.character_file(entry), "rb") as handle:
                for block in iter(lambda: handle.read(1 << 20), b""):
                    digest.update(block)
            self.assertEqual(
                row["sha1"], digest.hexdigest(),
                "%s changed since its bones were read - run "
                "docs/superpowers/plans/make_character_skeletons.py in mayapy" % entry.file)

    def test_each_rig_is_its_own_match_among_the_rigs(self):
        rigs = [e.key for e in self.catalog.CHARACTERS if e.kind == "rig"]
        for key in rigs:
            found = sm.match(clip_of(self.templates[key]), self.templates, rigs)
            self.assertEqual(found.key, key)

    def test_each_skeleton_is_its_own_match_among_the_skeletons(self):
        bare = [e.key for e in self.catalog.CHARACTERS if e.kind == "skeleton"]
        for key in bare:
            found = sm.match(clip_of(self.templates[key]), self.templates, bare)
            self.assertEqual(found.key, key)

    def test_the_orc_is_no_skeleton_of_ours_among_the_skeletons(self):
        """Manny's names, its own proportions: the Skeleton kind has no Orc, so it is not Manny."""
        bare = [e.key for e in self.catalog.CHARACTERS if e.kind == "skeleton"]
        found = sm.match(clip_of(self.templates["Orc_D_Rig"]), self.templates, bare)
        self.assertIsNone(found.key)
        self.assertEqual(found.best.key, "Manny")
        self.assertLess(found.best.share, 0.6)

    def test_the_rig_and_the_skeleton_of_a_model_are_one_skeleton(self):
        for rig, bare in (("Manny_Rig", "Manny"), ("Creep_Rig", "Creep")):
            self.assertEqual(sm.score(clip_of(self.templates[rig]), self.templates[bare]).share,
                             1.0)


class Purity(unittest.TestCase):

    def test_imports_without_maya(self):
        code = ("import sys; sys.path.insert(0, %r);"
                "import maya_uebridge.skeletonmatch;"
                "assert 'maya.cmds' not in sys.modules, 'maya.cmds leaked in';"
                "print('clean')" % PLUGIN)
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertIn("clean", out.stdout, out.stderr)


if __name__ == "__main__":
    unittest.main()
