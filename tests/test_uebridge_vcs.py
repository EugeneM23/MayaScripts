"""Tests for the Perforce module's pure logic.

The fixtures are real p4 output captured on the user's machine 2026-08-21 -
including the double '... ...' prefix on other-open fields and the fact that
"no such file(s)" arrives on stderr with exit code 0.
"""

import os
import shutil
import stat
import tempfile
import unittest

from maya_uebridge import vcs

TRACKED_UNOPENED = """\
... depotFile //atone/main/Atone/Content/Prototype/Animation/PlayerCharacter/Unarmed/1P/AS_Unarmed_Idle_1P.uasset
... clientFile C:\\!!!Work\\Perforce\\Atone\\Content\\Prototype\\Animation\\PlayerCharacter\\Unarmed\\1P\\AS_Unarmed_Idle_1P.uasset
... isMapped
... headAction edit
... headType binary+l
... headRev 2
... headChange 41316
... haveRev 2
"""

OPENED_BY_OTHERS = TRACKED_UNOPENED + """\
... ... otherOpen0 aleksei.silantev@aleksei.silantev_Lehanomicon_2914
... ... otherAction0 edit
... ... otherChange0 default
... ... otherOpen1 emrys.ryan@emrys.ryan_SULACO_306
... ... otherAction1 edit
... ... otherChange1 default
... ... otherOpen 2
"""

OPENED_BY_ME = TRACKED_UNOPENED + "... action edit\n... change default\n"


class ParseZtag(unittest.TestCase):

    def test_reads_the_plain_fields(self):
        fields = vcs.parse_ztag(TRACKED_UNOPENED)
        self.assertIn("//atone/main/", fields["depotFile"])
        self.assertEqual(fields["headRev"], "2")

    def test_reads_the_double_prefixed_other_open_block(self):
        """otherOpen lines carry '... ... ' - a parser matching one prefix
        misses every one of them and reports a busy file as free."""
        fields = vcs.parse_ztag(OPENED_BY_OTHERS)
        self.assertIn("aleksei.silantev@", fields["otherOpen0"])
        self.assertIn("emrys.ryan@", fields["otherOpen1"])

    def test_the_count_key_does_not_eat_the_numbered_ones(self):
        fields = vcs.parse_ztag(OPENED_BY_OTHERS)
        self.assertEqual(fields["otherOpen"], "2")
        self.assertIn("otherOpen0", fields)

    def test_valueless_fields_survive(self):
        self.assertEqual(vcs.parse_ztag(TRACKED_UNOPENED)["isMapped"], "")

    def test_empty_text_is_an_empty_dict(self):
        self.assertEqual(vcs.parse_ztag(""), {})


class OtherOpeners(unittest.TestCase):

    def test_lists_every_opener(self):
        users = vcs.other_openers(vcs.parse_ztag(OPENED_BY_OTHERS))
        self.assertEqual(len(users), 2)
        self.assertTrue(users[0].startswith("aleksei.silantev@"))

    def test_sorts_numerically_not_lexically(self):
        fields = {"otherOpen{0}".format(i): "user{0}".format(i)
                  for i in range(12)}
        users = vcs.other_openers(fields)
        self.assertEqual(users[9], "user9")
        self.assertEqual(users[10], "user10")

    def test_no_openers_is_an_empty_list(self):
        self.assertEqual(vcs.other_openers(vcs.parse_ztag(TRACKED_UNOPENED)), [])


class ClassifyFailure(unittest.TestCase):

    def test_no_such_file_is_a_normal_answer(self):
        """Untracked is data, not an error - and p4 exits 0 saying it."""
        err = "C:\\x\\AS_Unarmed_Idle_1P.fbx - no such file(s).\n"
        self.assertEqual(vcs.classify_failure(err, 0), "")

    def test_outside_the_client_view_is_a_normal_answer(self):
        err = "C:\\elsewhere\\a.fbx - file(s) not in client view.\n"
        self.assertEqual(vcs.classify_failure(err, 0), "")

    def test_an_expired_session_names_the_cure(self):
        err = "Your session has expired, please login again.\n"
        reason = vcs.classify_failure(err, 1)
        self.assertIn("P4V", reason)

    def test_an_unset_password_reads_as_an_expired_session(self):
        err = "Perforce password (P4PASSWD) invalid or unset.\n"
        self.assertIn("P4V", vcs.classify_failure(err, 1))

    def test_a_dead_server_says_unreachable(self):
        err = ("Perforce client error:\n"
               "\tConnect to server failed; check $P4PORT.\n")
        self.assertIn("reach", vcs.classify_failure(err, 1))

    def test_an_unknown_error_shows_its_first_line(self):
        reason = vcs.classify_failure("something odd happened\nmore\n", 1)
        self.assertIn("something odd happened", reason)
        self.assertNotIn("more", reason)

    def test_clean_output_is_no_failure(self):
        self.assertEqual(vcs.classify_failure("", 0), "")


class PlanFor(unittest.TestCase):

    def test_empty_fields_mean_untracked(self):
        self.assertEqual(vcs.plan_for({})["kind"], "untracked")

    def test_tracked_and_free_means_edit(self):
        plan = vcs.plan_for(vcs.parse_ztag(TRACKED_UNOPENED))
        self.assertEqual(plan["kind"], "edit")

    def test_open_by_me_means_mine(self):
        plan = vcs.plan_for(vcs.parse_ztag(OPENED_BY_ME))
        self.assertEqual(plan["kind"], "mine")

    def test_open_by_others_names_them(self):
        plan = vcs.plan_for(vcs.parse_ztag(OPENED_BY_OTHERS))
        self.assertEqual(plan["kind"], "others")
        self.assertEqual(len(plan["users"]), 2)

    def test_mine_wins_over_others(self):
        """Already mine = already decided to work on it; others go to the
        status line, not a modal."""
        both = OPENED_BY_OTHERS + "... action edit\n"
        plan = vcs.plan_for(vcs.parse_ztag(both))
        self.assertEqual(plan["kind"], "mine")
        self.assertEqual(len(plan["users"]), 2)


class ConventionalFolder(unittest.TestCase):

    ROOT = os.path.join("C:\\", "src")

    def test_the_real_example(self):
        """The measured divergence: Exports inserted after Animation, the
        trailing 1P dropped."""
        folder = vcs.conventional_folder(
            "/Game/Prototype/Animation/PlayerCharacter/Unarmed/1P/AS_Unarmed_Idle_1P",
            self.ROOT)
        self.assertEqual(folder, os.path.join(
            self.ROOT, "Prototype", "Animation", "Exports",
            "PlayerCharacter", "Unarmed"))

    def test_3p_is_dropped_too(self):
        folder = vcs.conventional_folder("/Game/P/Animation/X/3P/Asset", self.ROOT)
        self.assertEqual(folder, os.path.join(
            self.ROOT, "P", "Animation", "Exports", "X"))

    def test_1p_matching_is_case_insensitive(self):
        folder = vcs.conventional_folder("/Game/P/Animation/X/1p/Asset", self.ROOT)
        self.assertTrue(folder.endswith("X"))

    def test_exports_is_not_doubled(self):
        folder = vcs.conventional_folder(
            "/Game/P/Animation/Exports/X/Asset", self.ROOT)
        self.assertEqual(folder.lower().count("exports"), 1)

    def test_a_path_without_animation_passes_through(self):
        folder = vcs.conventional_folder("/Game/Props/Swords/Asset", self.ROOT)
        self.assertEqual(folder, os.path.join(self.ROOT, "Props", "Swords"))

    def test_a_package_without_game_prefix_still_lands_under_root(self):
        folder = vcs.conventional_folder("Odd/Path/Asset", self.ROOT)
        self.assertEqual(folder, os.path.join(self.ROOT, "Odd", "Path"))

    def test_a_bare_asset_name_lands_on_the_root(self):
        self.assertEqual(vcs.conventional_folder("Asset", self.ROOT), self.ROOT)


class FindFbx(unittest.TestCase):

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="vcs_find_")
        self.addCleanup(shutil.rmtree, self.root, True)

    def plant(self, *parts):
        path = os.path.join(self.root, *parts)
        folder = os.path.dirname(path)
        if not os.path.isdir(folder):
            os.makedirs(folder)
        with open(path, "w") as handle:
            handle.write("x")
        return path

    def test_finds_a_nested_file(self):
        planted = self.plant("A", "B", "AS_Walk.fbx")
        self.assertEqual(vcs.find_fbx("AS_Walk", self.root), [planted])

    def test_matching_is_case_insensitive(self):
        self.plant("A", "as_walk.FBX")
        self.assertEqual(len(vcs.find_fbx("AS_Walk", self.root)), 1)

    def test_finds_every_duplicate(self):
        self.plant("A", "AS_Walk.fbx")
        self.plant("B", "AS_Walk.fbx")
        self.assertEqual(len(vcs.find_fbx("AS_Walk", self.root)), 2)

    def test_other_names_do_not_match(self):
        self.plant("A", "AS_Walk_Fast.fbx")
        self.assertEqual(vcs.find_fbx("AS_Walk", self.root), [])

    def test_a_missing_root_is_an_empty_list(self):
        gone = os.path.join(self.root, "nowhere")
        self.assertEqual(vcs.find_fbx("AS_Walk", gone), [])


class DirMap(unittest.TestCase):

    PACKAGE = "/Game/P/Animation/X/1P/AS_Walk"

    def test_remember_and_recall(self):
        grown = vcs.remember_folder({}, self.PACKAGE, "C:/src/somewhere")
        self.assertEqual(vcs.remembered_folder(grown, self.PACKAGE),
                         "C:/src/somewhere")

    def test_the_key_is_the_uasset_folder_not_the_asset(self):
        """Two animations in one uasset folder share the remembered answer."""
        grown = vcs.remember_folder({}, self.PACKAGE, "C:/src/somewhere")
        sibling = "/Game/P/Animation/X/1P/AS_Run"
        self.assertEqual(vcs.remembered_folder(grown, sibling),
                         "C:/src/somewhere")

    def test_remember_does_not_mutate_the_input(self):
        original = {}
        vcs.remember_folder(original, self.PACKAGE, "C:/x")
        self.assertEqual(original, {})

    def test_unknown_package_recalls_nothing(self):
        self.assertEqual(vcs.remembered_folder({}, self.PACKAGE), "")


if __name__ == "__main__":
    unittest.main()
