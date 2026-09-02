"""Tests for the Maya-side import.

`import_clip` needs a live Maya and a real FBX, so it is proved by
docs/superpowers/plans/verify_uebridge.py. What is testable here is the policy
around it: the frame-rate rule and the key-range arithmetic.
"""

import sys
import types
import unittest


def _install_fake_maya():
    """Let animimport import without Maya. See CLAUDE.md on rebinding."""
    if "maya.cmds" in sys.modules:
        return
    maya = types.ModuleType("maya")
    cmds = types.ModuleType("maya.cmds")
    mel = types.ModuleType("maya.mel")
    maya.cmds = cmds
    maya.mel = mel
    sys.modules.setdefault("maya", maya)
    sys.modules["maya.cmds"] = cmds
    sys.modules["maya.mel"] = mel


_install_fake_maya()

from maya_uebridge import animimport  # noqa: E402


class FpsPolicy(unittest.TestCase):

    def test_silent_when_they_agree(self):
        self.assertEqual(animimport.fps_warning(30.0, 30.0), "")

    def test_tolerates_float_noise(self):
        """29.999999 against 30 is not worth shouting about."""
        self.assertEqual(animimport.fps_warning(30.0, 30.000001), "")

    def test_names_both_rates_when_they_differ(self):
        message = animimport.fps_warning(30.0, 24.0)
        self.assertIn("30", message)
        self.assertIn("24", message)

    def test_says_nothing_when_the_clip_rate_is_unknown(self):
        """UE does not always report a rate; silence beats a false alarm."""
        self.assertEqual(animimport.fps_warning(None, 24.0), "")

    def test_says_nothing_when_the_scene_rate_is_unknown(self):
        self.assertEqual(animimport.fps_warning(30.0, None), "")


class RiggedTargetMessage(unittest.TestCase):
    """A merge onto a rigged skeleton lands only on the unconstrained bones:
    Maya splices a pairBlend on some channels and skips others, leaving the
    character playing two clips at once. The import must refuse instead."""

    def test_names_the_count_and_a_sample(self):
        message = animimport.rigged_target_message(
            ["pelvis", "hand_r", "spine_01"])
        self.assertIn("3", message)
        self.assertIn("pelvis", message)
        self.assertIn("Bake+Delete", message)

    def test_long_lists_are_trimmed(self):
        names = ["bone_{0:02d}".format(i) for i in range(20)]
        message = animimport.rigged_target_message(names)
        self.assertIn("20", message)
        self.assertNotIn("bone_19", message)

    def test_sorted_so_the_message_is_stable(self):
        first = animimport.rigged_target_message(["b", "a"])
        second = animimport.rigged_target_message(["a", "b"])
        self.assertEqual(first, second)


class WeaponLinks(unittest.TestCase):
    """The bridge unlinks our weapon-driven bones around a merge
    (2026-08-21): weapon_r under the sword's constraint would otherwise
    trip the rigged-skeleton refusal on every import after an Add."""

    def test_our_bones_do_not_count_as_rigged(self):
        self.assertEqual(
            animimport.foreign_constrained(
                ["|s|weapon_r", "|s|hand_r"], ["|s|weapon_r"]),
            ["|s|hand_r"])

    def test_a_real_rig_still_refuses(self):
        self.assertEqual(
            animimport.foreign_constrained(["|s|hand_r"], []),
            ["|s|hand_r"])

    def test_nothing_constrained_is_nothing(self):
        self.assertEqual(animimport.foreign_constrained([], ["|s|weapon_r"]),
                         [])

    def test_relink_note_names_the_bones(self):
        self.assertIn("weapon_r", animimport.relink_note(["weapon_r"]))

    def test_no_relink_no_note(self):
        self.assertEqual(animimport.relink_note([]), "")

    def test_the_lookup_survives_a_maya_without_scenesetup(self):
        """Lazy and guarded: the bridge must work where the weapon tool was
        never installed. With the fake maya in place the import itself
        succeeds here; what this pins is that the helper answers a list."""
        self.assertIsInstance(animimport._weapon_links([]), list)


class SceneFps(unittest.TestCase):

    def test_knows_the_units_maya_reports(self):
        self.assertEqual(animimport.TIME_UNIT_TO_FPS["ntsc"], 30)
        self.assertEqual(animimport.TIME_UNIT_TO_FPS["film"], 24)
        self.assertEqual(animimport.TIME_UNIT_TO_FPS["pal"], 25)

    def test_reads_a_numeric_unit_name(self):
        """Maya reports custom rates as e.g. '30fps', absent from the table."""
        self.assertEqual(animimport.fps_from_unit("30fps"), 30.0)
        self.assertEqual(animimport.fps_from_unit("120fps"), 120.0)

    def test_an_unknown_unit_is_none_rather_than_a_guess(self):
        self.assertIsNone(animimport.fps_from_unit("whatever"))


class ImportCommand(unittest.TestCase):

    def test_uses_the_plugin_own_importer(self):
        """cmds.file with the FBX translator brings the skeleton and drops every
        animation curve - measured 1081 curves against 0."""
        self.assertIn("FBXImport", animimport.import_command("C:/a/x.fbx"))

    def test_windows_paths_are_converted_to_forward_slashes(self):
        r"""Inside a MEL string a backslash starts an escape, so C:\anim mangles."""
        command = animimport.import_command("C:\\temp\\anim\\x.fbx")
        self.assertIn("C:/temp/anim/x.fbx", command)
        self.assertNotIn("\\", command)

    def test_the_path_is_quoted(self):
        """Paths on this machine contain spaces and exclamation marks."""
        command = animimport.import_command("C:/My Docs/x.fbx")
        self.assertIn('"C:/My Docs/x.fbx"', command)


class ImportMode(unittest.TestCase):

    def test_merging_uses_exclusive_merge(self):
        """exmerge writes animation onto nodes that already exist and creates
        none - measured: 0 new joints, 819 new curves, 92/93 joints keyed."""
        self.assertIn("exmerge", animimport.import_mode_command(merge=True))

    def test_a_separate_skeleton_uses_add(self):
        self.assertIn("add", animimport.import_mode_command(merge=False))
        self.assertNotIn("exmerge", animimport.import_mode_command(merge=False))


class TargetSkeleton(unittest.TestCase):
    """Which skeleton a merge lands on.

    It has to be decided rather than assumed: the merge clears the target's
    animation first, because the FBX importer edits existing curves in place
    (measured: 836 curves before, 836 after, same names AND same uuids), so
    without clearing there is no way to tell what the clip touched - or even
    whether it touched anything.
    """

    def test_the_only_skeleton_wins(self):
        self.assertEqual(animimport.choose_target_root(["|root"]), "|root")

    def test_nothing_in_the_scene_is_no_target(self):
        self.assertIsNone(animimport.choose_target_root([]))

    def test_a_selected_skeleton_beats_everything(self):
        chosen = animimport.choose_target_root(
            ["|root", "|other"], selected_roots=["|other"])
        self.assertEqual(chosen, "|other")

    def test_the_one_called_root_wins_among_several(self):
        chosen = animimport.choose_target_root(["|rig_root", "|root"])
        self.assertEqual(chosen, "|root")

    def test_two_plausible_skeletons_with_no_hint_is_no_answer(self):
        """Guessing here would animate the wrong character in silence."""
        self.assertIsNone(animimport.choose_target_root(["|hero", "|enemy"]))

    def test_namespaced_skeletons_are_never_the_target(self):
        """A merge matches plain bone names, so a namespaced skeleton could
        not receive it anyway - and ours sit there as reference imports."""
        chosen = animimport.choose_target_root(["|AS_Clip:root", "|root"])
        self.assertEqual(chosen, "|root")

    def test_only_namespaced_skeletons_means_no_target(self):
        self.assertIsNone(animimport.choose_target_root(["|AS_Clip:root"]))

    def test_a_namespaced_selection_does_not_override(self):
        chosen = animimport.choose_target_root(
            ["|root", "|AS_Clip:root"], selected_roots=["|AS_Clip:root"])
        self.assertEqual(chosen, "|root")

    def test_the_no_target_message_says_what_to_do(self):
        self.assertIn("select", animimport.NO_TARGET_MESSAGE.lower())


class ConnectedCharacterIsTheFallback(unittest.TestCase):
    """The 2026-09-01 order, in the user's words: "look first at whether a
    bone hierarchy is selected... if the selection is empty, look at the
    connect"."""

    def test_the_selection_still_beats_the_connect(self):
        chosen = animimport.choose_target_root(
            ["|root", "|root1"], selected_roots=["|root1"],
            bound_root="|root")
        self.assertEqual(chosen, "|root1")

    def test_the_connect_decides_when_nothing_is_selected(self):
        chosen = animimport.choose_target_root(
            ["|root", "|root1"], selected_roots=[], bound_root="|root1")
        self.assertEqual(chosen, "|root1")

    def test_the_connect_beats_the_one_called_root(self):
        """Otherwise a picker connected to the second Manny would still
        import onto the first one, which is the whole bug."""
        chosen = animimport.choose_target_root(
            ["|root", "|root1"], bound_root="|root1")
        self.assertEqual(chosen, "|root1")

    def test_a_namespaced_connect_does_not_override(self):
        chosen = animimport.choose_target_root(
            ["|root", "|AS_Clip:root"], bound_root="|AS_Clip:root")
        self.assertEqual(chosen, "|root")

    def test_no_connect_falls_through_to_the_old_rules(self):
        self.assertEqual(
            animimport.choose_target_root(["|rig_root", "|root"],
                                          bound_root=None),
            "|root")
        self.assertIsNone(
            animimport.choose_target_root(["|hero", "|enemy"],
                                          bound_root=None))


class HoldingOtherSkeletons(unittest.TestCase):
    """Choosing the right target is not enough: `FBXImport -v exmerge`
    matches bone names inside the plugin, so with two Mannys in the scene
    `pelvis` is ambiguous and the plugin lands on whichever it finds."""

    def test_the_other_plain_skeleton_is_held(self):
        self.assertEqual(
            animimport.skeletons_to_hold(["|root", "|root1"], "|root"),
            ["|root1"])

    def test_the_target_itself_is_never_held(self):
        self.assertNotIn(
            "|root", animimport.skeletons_to_hold(["|root"], "|root"))

    def test_a_single_character_scene_holds_nothing(self):
        """Every scene the tool has ever run in: the whole mechanism has to
        be a no-op there."""
        self.assertEqual(animimport.skeletons_to_hold(["|root"], "|root"), [])
        self.assertEqual(animimport.skeletons_to_hold([], "|root"), [])
        self.assertEqual(animimport.skeletons_to_hold(None, "|root"), [])

    def test_namespaced_skeletons_are_left_alone(self):
        """Their bones cannot collide with the plain names the merge
        matches - and a referenced skeleton (always namespaced) could not
        be renamed anyway."""
        self.assertEqual(
            animimport.skeletons_to_hold(["|root", "|AS_Clip:root"], "|root"),
            [])

    def test_the_hold_name_is_a_prefix_nothing_else_uses(self):
        self.assertEqual(animimport.hold_name("pelvis"), "rpHold_pelvis")
        self.assertTrue(
            animimport.hold_name("pelvis").startswith(
                animimport.HOLD_PREFIX))

    def test_a_joint_that_could_not_be_held_is_warned_about(self):
        warning = animimport.unheld_warning(["pelvis", "pelvis", "spine_01"])
        self.assertIn("pelvis", warning)
        self.assertIn("spine_01", warning)
        self.assertIn("2", warning)

    def test_nothing_unheld_is_no_warning(self):
        self.assertEqual(animimport.unheld_warning([]), "")
        self.assertEqual(animimport.unheld_warning(None), "")


class TheTargetsOwnRootName(unittest.TestCase):
    """Holding the OTHER characters aside is only half of it.

    Maya will not let two nodes at world level share a short name, so a
    second character has exactly one joint renamed: its root. Everything
    below keeps its plain name, because its path is unique already. An
    exmerge matches by name, so the clip's `root` reaches nothing and the
    character plays the clip on the spot while the first one walks.
    """

    def test_a_plain_root_is_left_alone(self):
        """Every single-character scene: the whole mechanism is a no-op."""
        self.assertEqual(animimport.plain_root_name("root", ["pelvis"]), "")

    def test_a_trailing_number_is_a_decoration(self):
        """`duplicate`, a plain rename and the FBX importer all increment."""
        self.assertEqual(animimport.plain_root_name("root2", ["pelvis"]),
                         "root")

    def test_a_file_stem_prefix_is_a_decoration(self):
        """`cmds.file(i=True)` of Manny_Skeleton.ma prefixes the clashing top
        node with the FILE STEM, not with a number."""
        self.assertEqual(
            animimport.plain_root_name("Manny_Skeleton_root", ["pelvis"]),
            "root")

    def test_both_decorations_at_once(self):
        """A third character: the stem prefix, then Maya's increment."""
        self.assertEqual(
            animimport.plain_root_name("Manny_Skeleton_root1", ["pelvis"]),
            "root")

    def test_a_schema_bone_ending_in_root_is_not_a_decoration(self):
        """`ik_foot_root` is a bone of the UE skeleton, not a renamed `root`
        - and its own children wear the prefix, which is what says so.
        Only the TOP node ever collides, so a prefix the rest of the
        skeleton also wears was never a collision."""
        self.assertEqual(
            animimport.plain_root_name("ik_foot_root",
                                       ["ik_foot_l", "ik_foot_r"]), "")

    def test_a_root_called_something_else_is_left_alone(self):
        """No guessing: a non-UE rig keeps exactly today's behaviour."""
        self.assertEqual(animimport.plain_root_name("Bip001", ["Bip002"]), "")
        self.assertEqual(animimport.plain_root_name("hero", ["pelvis"]), "")

    def test_nothing_is_left_alone(self):
        self.assertEqual(animimport.plain_root_name("", []), "")
        self.assertEqual(animimport.plain_root_name(None, None), "")

    def test_names_are_reduced_to_their_leaf(self):
        self.assertEqual(
            animimport.plain_root_name("|Manny_Skeleton_root", ["|grp|pelvis"]),
            "root")


class RootNameNote(unittest.TestCase):
    """Said out loud, or the next person finds one name in the outliner and
    another in the FBX with nothing to go on."""

    def test_silent_when_nothing_was_renamed(self):
        self.assertEqual(animimport.root_note("root", ""), "")

    def test_silent_when_the_name_did_not_change(self):
        self.assertEqual(animimport.root_note("root", "root"), "")

    def test_names_the_rename_and_says_why(self):
        note = animimport.root_note("Manny_Skeleton_root", "root")
        self.assertIn("Manny_Skeleton_root", note)
        self.assertIn("root motion", note)


class FakeScene(object):
    """Just enough Maya for the rename dance: names, uuids, and the
    UNIQUIFYING rename.

    Deliberately minimal, and deliberately honest about the one behaviour
    the manager has to defend against - `cmds.rename` onto a taken name
    succeeds with a DIFFERENT name rather than failing. Everything lives at
    world level, which is where roots live. The real proof is the live
    verify script.
    """

    def __init__(self, names):
        self.names = {}                      # uuid -> short name
        for index, name in enumerate(names):
            self.names["uuid%d" % index] = name
        self.renames = 0

    def uuid_of(self, short):
        for uuid, name in self.names.items():
            if name == short:
                return uuid
        return None

    def ls(self, *args, **kwargs):
        if not args:
            return sorted("|" + n for n in self.names.values())
        wanted = args[0]
        if wanted in self.names:                       # a uuid
            return ["|" + self.names[wanted]]
        short = str(wanted).split("|")[-1]
        uuid = self.uuid_of(short)
        if uuid is None:
            return []
        if kwargs.get("uuid"):
            return [uuid]
        return ["|" + short]

    def rename(self, path, new):
        short = str(path).split("|")[-1]
        uuid = self.uuid_of(short)
        if uuid is None:
            raise RuntimeError("no object matches name: " + str(path))
        taken = set(self.names.values()) - {short}
        assigned = new
        suffix = 1
        while assigned in taken:                       # Maya uniquifies
            assigned = "{0}{1}".format(new, suffix)
            suffix += 1
        self.names[uuid] = assigned
        self.renames += 1
        return assigned


class TheRootWearsItsPlainName(unittest.TestCase):
    """The lever itself. A temporary rename is the only thing that reaches
    inside the FBX plugin's own name matching."""

    def setUp(self):
        self.real_cmds = animimport.cmds

    def tearDown(self):
        animimport.cmds = self.real_cmds

    def use(self, names):
        scene = FakeScene(names)
        animimport.cmds = scene
        return scene

    def test_the_root_takes_the_plain_name_and_gives_it_back(self):
        """The import path: `other_skeletons_held` has already taken the
        name away, so there is nothing to displace."""
        scene = self.use(["Manny_Skeleton_root", "pelvis", "rpHold_root"])
        with animimport.target_root_plain(
                "|Manny_Skeleton_root",
                ["|Manny_Skeleton_root", "|Manny_Skeleton_root|pelvis"]) as took:
            self.assertEqual(took, "root")
            self.assertIn("root", scene.names.values())
        self.assertIn("Manny_Skeleton_root", scene.names.values())
        self.assertNotIn("root", scene.names.values())

    def test_whatever_holds_the_name_is_displaced_and_restored(self):
        """The export path: no hold has run, so the first character is
        still answering to `root`."""
        scene = self.use(["Manny_Skeleton_root", "root"])
        with animimport.target_root_plain(
                "|Manny_Skeleton_root", ["|Manny_Skeleton_root"]) as took:
            self.assertEqual(took, "root")
            self.assertIn("rpHold_root", scene.names.values())
        self.assertEqual(sorted(scene.names.values()),
                         ["Manny_Skeleton_root", "root"])

    def test_a_plain_root_renames_nothing_at_all(self):
        scene = self.use(["root", "pelvis"])
        with animimport.target_root_plain("|root", ["|root"]) as took:
            self.assertEqual(took, "")
        self.assertEqual(scene.renames, 0)

    def test_a_rename_maya_uniquified_is_undone_not_reported(self):
        """`cmds.rename` onto a taken name succeeds with `root1`, which
        matches the clip no better than the name we started with. Reporting
        it would be a lie, and leaving it would rename the animator's joint
        for nothing."""
        scene = self.use(["Manny_Skeleton_root", "root"])
        scene.rename = lambda path, new: "root1"      # nothing actually moves
        with animimport.target_root_plain(
                "|Manny_Skeleton_root", ["|Manny_Skeleton_root"]) as took:
            self.assertEqual(took, "")

    def test_the_names_come_back_even_when_the_body_raises(self):
        scene = self.use(["Manny_Skeleton_root", "root"])
        try:
            with animimport.target_root_plain(
                    "|Manny_Skeleton_root", ["|Manny_Skeleton_root"]):
                raise ValueError("the importer died")
        except ValueError:
            pass
        self.assertEqual(sorted(scene.names.values()),
                         ["Manny_Skeleton_root", "root"])


class MergeDefault(unittest.TestCase):
    """`merge` left unset must follow the namespace, or a caller asking for a
    named skeleton silently gets its scene overwritten instead."""

    def test_a_namespace_means_a_separate_skeleton(self):
        self.assertFalse(animimport.wants_merge(namespace="AS_Clip", merge=None))

    def test_no_namespace_means_merge(self):
        self.assertTrue(animimport.wants_merge(namespace=None, merge=None))
        self.assertTrue(animimport.wants_merge(namespace="", merge=None))

    def test_an_explicit_choice_is_obeyed_either_way(self):
        self.assertTrue(animimport.wants_merge(namespace="AS_Clip", merge=True))
        self.assertFalse(animimport.wants_merge(namespace=None, merge=False))


class MergeReporting(unittest.TestCase):

    def test_nothing_matched_is_explained_not_silent(self):
        """A name mismatch imports cleanly and moves nothing at all, which
        reads as a broken tool unless we say what happened."""
        message = animimport.merge_warning(0)
        self.assertIn("no bone", message.lower())
        self.assertTrue(message)

    def test_a_namespace_is_named_as_the_likely_cause(self):
        self.assertIn("namespace", animimport.merge_warning(0).lower())

    def test_matches_are_not_warned_about(self):
        self.assertEqual(animimport.merge_warning(92), "")

    def test_bones_the_clip_had_nothing_for_are_reported(self):
        """A hand that does not move while the arm does is a mystery unless
        the tool says the clip carried no keys for it."""
        line = animimport.stale_line(["weapon_l", "weapon_r"])
        self.assertIn("2", line)
        self.assertIn("weapon_l", line)

    def test_nothing_stale_is_silent(self):
        self.assertEqual(animimport.stale_line([]), "")

    def test_a_long_stale_list_is_trimmed(self):
        line = animimport.stale_line(["b{0}".format(i) for i in range(30)])
        self.assertIn("30", line)
        self.assertLess(len(line), 200)


class ClipRange(unittest.TestCase):

    def test_takes_the_outermost_keys(self):
        self.assertEqual(animimport.clip_range([5.0, 1.0, 3.0]), (1.0, 5.0))

    def test_no_keys_is_no_range(self):
        self.assertEqual(animimport.clip_range([]), (None, None))

    def test_a_single_key_is_a_zero_length_range(self):
        self.assertEqual(animimport.clip_range([7.0]), (7.0, 7.0))


if __name__ == "__main__":
    unittest.main()
