"""The clip's name under the character (2026-10-02): `maya_scenesetup.cliplabel`.

The scene half is proved by docs/superpowers/plans/verify_clip_labels.py in
mayapy standalone and a disposable GUI Maya; here: what a label reads, where
it lives, what one import does to the labels standing, how it is dressed, and
that every road that puts a clip on a character asks for one.
"""

import sys
import types
import unittest


def _install_fake_maya():
    try:
        import maya.api.OpenMaya  # noqa: F401
        import maya.cmds  # noqa: F401
        import maya.mel  # noqa: F401
        return
    except ImportError:
        pass
    maya = types.ModuleType("maya")
    api = types.ModuleType("maya.api")
    openmaya = types.ModuleType("maya.api.OpenMaya")
    cmds = types.ModuleType("maya.cmds")
    mel = types.ModuleType("maya.mel")
    maya.cmds, maya.mel, maya.api = cmds, mel, api
    api.OpenMaya = openmaya
    sys.modules.setdefault("maya", maya)
    sys.modules["maya.api"] = api
    sys.modules["maya.api.OpenMaya"] = openmaya
    sys.modules["maya.cmds"] = cmds
    sys.modules["maya.mel"] = mel


_install_fake_maya()

import maya_hubstyle  # noqa: E402
from maya_scenesetup import cliplabel  # noqa: E402
from maya_scenesetup import deletion  # noqa: E402
from maya_uebridge import rigimport  # noqa: E402
from maya_uebridge import skeletonimport  # noqa: E402


class Text(unittest.TestCase):
    """What the label reads."""

    def test_the_clip_name_as_it_is(self):
        self.assertEqual(cliplabel.label_text("ShortSword_Walk_1P"), "ShortSword_Walk_1P")

    def test_a_file_keeps_its_name_without_the_extension(self):
        self.assertEqual(cliplabel.label_text("C:/clips/Run_Fwd.FBX"), "Run_Fwd")
        self.assertEqual(cliplabel.label_text("D:\\mocap\\walk 01.bvh"), "walk 01")

    def test_an_unknown_extension_stays(self):
        self.assertEqual(cliplabel.label_text("Idle.v2"), "Idle.v2")

    def test_whitespace_collapses(self):
        self.assertEqual(cliplabel.label_text("  Sword   Idle \t 02 "), "Sword Idle 02")

    def test_a_long_name_keeps_its_head_and_its_tail(self):
        name = "AS_am_LongS_Uni_Hitreact_Medium_Front_High_Variant_Long_1P"
        text = cliplabel.label_text(name, limit=40)
        self.assertEqual(len(text), 40)
        self.assertTrue(text.startswith("AS_am_LongS"))
        self.assertTrue(text.endswith("_Long_1P"))
        self.assertIn("...", text)

    def test_nothing_reads_nothing(self):
        self.assertEqual(cliplabel.label_text(None), "")
        self.assertEqual(cliplabel.label_text(""), "")


class Where(unittest.TestCase):
    """Its name and where it hangs - one function decides the home."""

    def test_a_rig_label_lives_in_the_rigs_namespace(self):
        self.assertEqual(cliplabel.node_name("Manny_Rig1"), "Manny_Rig1:clipLabel")

    def test_a_skeleton_label_has_no_namespace(self):
        self.assertEqual(cliplabel.node_name(""), "clipLabel")

    def test_a_skeleton_label_is_named_after_its_root(self):
        self.assertEqual(cliplabel.node_name("", "|Manny_Skeleton_root"),
                         "Manny_Skeleton_root_clipLabel")
        self.assertEqual(cliplabel.node_name("", "|Armature|root"), "root_clipLabel")

    def test_a_rig_label_keeps_its_namespace_name_whatever_the_root(self):
        self.assertEqual(cliplabel.node_name("Creep_Rig", "|Creep_Rig:Armature|Creep_Rig:root"),
                         "Creep_Rig:clipLabel")

    def test_a_rig_label_hangs_under_the_rigs_group(self):
        self.assertEqual(cliplabel.home_for("rig", "|Manny_Rig:Group"), "|Manny_Rig:Group")

    def test_a_skeleton_label_stands_at_world_level(self):
        self.assertIsNone(cliplabel.home_for("skeleton"))
        self.assertIsNone(cliplabel.home_for("skeleton", "|Somebody"))

    def test_a_rig_without_a_group_stands_at_world_level(self):
        self.assertIsNone(cliplabel.home_for("rig", None))

    def test_the_characters_own_group_wins_for_rig_and_skeleton(self):
        group = "|Manny_Rig_Character"
        self.assertEqual(cliplabel.home_for("rig", "|Manny_Rig_Character|Manny_Rig:Group",
                                            group), group)
        self.assertEqual(cliplabel.home_for("skeleton", None, "|Manny_Skeleton"),
                         "|Manny_Skeleton")


class Plan(unittest.TestCase):
    """One label per character: made, replaced, kept, extras dropped."""

    def test_nothing_standing_makes_one(self):
        self.assertEqual(cliplabel.plan([], "A"), ("create", None, []))

    def test_the_same_clip_again_keeps_it(self):
        self.assertEqual(cliplabel.plan([("|l", "A")], "A"), ("keep", "|l", []))

    def test_another_clip_replaces_the_text(self):
        self.assertEqual(cliplabel.plan([("|l", "A")], "B"), ("update", "|l", []))

    def test_a_second_label_goes(self):
        self.assertEqual(cliplabel.plan([("|l", "A"), ("|m", "C")], "B"),
                         ("update", "|l", ["|m"]))


class Look(unittest.TestCase):

    def test_the_colour_is_the_hubs_accent(self):
        self.assertEqual(cliplabel.COLOUR, maya_hubstyle.TOKENS["accent"])

    def test_the_label_stands_past_mains_ring(self):
        self.assertGreater(cliplabel.FRONT, 40.52)

    def test_colour_of(self):
        self.assertEqual(cliplabel.colour_of("#ff8000"), (1.0, 128 / 255.0, 0.0))

    def test_the_marker_deletion_spells_is_ours(self):
        self.assertEqual(deletion.LABEL_MARKER, cliplabel.MARKER)

    def test_dressed_unselectable_and_in_our_colour(self):
        """The transform in reference display (the pick), the shape's own override
        normal with RGB (the draw) - measured: reference alone draws it black."""
        writes = {}
        fake = types.SimpleNamespace(setAttr=lambda plug, *v, **k: writes.__setitem__(plug, v))
        saved = cliplabel.cmds
        cliplabel.cmds = fake
        try:
            cliplabel._dress("|lab", "|lab|labShape")
        finally:
            cliplabel.cmds = saved
        self.assertEqual(writes["|lab|labShape.displayArrow"], (0,))
        self.assertEqual(writes["|lab.overrideEnabled"], (1,))
        self.assertEqual(writes["|lab.overrideDisplayType"], (2,))
        self.assertEqual(writes["|lab|labShape.overrideDisplayType"], (0,))
        self.assertEqual(writes["|lab|labShape.overrideRGBColors"], (1,))
        self.assertEqual(writes["|lab|labShape.overrideColorRGB"],
                         cliplabel.colour_of(maya_hubstyle.TOKENS["accent"]))

    def test_a_failing_label_never_fails_the_import(self):
        saved = cliplabel.ensure
        cliplabel.ensure = lambda *a, **k: 1 / 0
        try:
            rig = types.SimpleNamespace(skeleton_root="|r:root", main="r:Main",
                                        namespace="r", group="|r:Group")
            self.assertIsNone(cliplabel.label_rig(rig, "A"))
            self.assertIsNone(cliplabel.label_skeleton("|root", "A"))
        finally:
            cliplabel.ensure = saved


class Ensure(unittest.TestCase):
    """`ensure` over a scene of strings: the plan's three answers reach it."""

    def setUp(self):
        self.calls = []
        self.links = {}          # root -> [label]
        self.marks = {}          # label -> clip
        saved = dict(cmds=cliplabel.cmds, make=cliplabel._make, write=cliplabel._write,
                     follows=cliplabel.follows, follow=cliplabel._follow,
                     unfollow=cliplabel._unfollow)

        def restore():
            cliplabel.cmds = saved["cmds"]
            cliplabel._make = saved["make"]
            cliplabel._write = saved["write"]
            cliplabel.follows = saved["follows"]
            cliplabel._follow = saved["follow"]
            cliplabel._unfollow = saved["unfollow"]
        self.addCleanup(restore)
        self.whole = True        # does the standing label still follow its root?
        cliplabel.follows = lambda label, root: self.whole
        cliplabel._follow = lambda label, root: self.calls.append(("follow", label, root))
        cliplabel._unfollow = lambda label: self.calls.append(("unfollow", label))
        cliplabel.cmds = types.SimpleNamespace(
            ls=lambda node, long=False: [node],
            objExists=lambda node: True,
            listConnections=lambda plug, **k: list(self.links.get(plug.split(".")[0], [])),
            attributeQuery=lambda attr, node=None, exists=False: node in self.marks,
            getAttr=lambda plug: self.marks[plug.split(".")[0]],
            delete=lambda node: self.calls.append(("delete", node)))
        cliplabel._make = lambda root, ns, home, name, text: (
            self.calls.append(("make", root, ns, home, name, text)) or "|new")
        cliplabel._write = lambda label, name, text: self.calls.append(("write", label, name))

    def test_a_first_import_makes_it_under_the_home(self):
        out = cliplabel.ensure("|Manny_Rig:root", "Walk.fbx", "Manny_Rig", "|Manny_Rig:Group")
        self.assertEqual(out, "|new")
        self.assertEqual(self.calls, [("make", "|Manny_Rig:root", "Manny_Rig",
                                       "|Manny_Rig:Group", "Walk.fbx", "Walk")])

    def test_a_second_import_replaces_the_text_of_the_one_standing(self):
        self.links["|root"] = ["|root_clipLabel"]
        self.marks["|root_clipLabel"] = "Walk"
        out = cliplabel.ensure("|root", "Run")
        self.assertEqual(out, "|root_clipLabel")
        self.assertEqual(self.calls, [("write", "|root_clipLabel", "Run")])

    def test_the_same_clip_again_writes_nothing(self):
        self.links["|root"] = ["|root_clipLabel"]
        self.marks["|root_clipLabel"] = "Walk"
        self.assertEqual(cliplabel.ensure("|root", "Walk"), "|root_clipLabel")
        self.assertEqual(self.calls, [])

    def test_a_label_that_stopped_following_is_made_to_follow_again(self):
        """Its network deleted, or the first build's pointConstraint: the next
        import does not leave it frozen where it stands."""
        self.links["|root"] = ["|root_clipLabel"]
        self.marks["|root_clipLabel"] = "Walk"
        self.whole = False
        self.assertEqual(cliplabel.ensure("|root", "Walk"), "|root_clipLabel")
        self.assertEqual(self.calls, [("unfollow", "|root_clipLabel"),
                                      ("follow", "|root_clipLabel", "|root")])

    def test_a_repair_with_a_new_clip_rewrites_the_text_too(self):
        self.links["|root"] = ["|root_clipLabel"]
        self.marks["|root_clipLabel"] = "Walk"
        self.whole = False
        cliplabel.ensure("|root", "Run")
        self.assertEqual([c[0] for c in self.calls], ["write", "unfollow", "follow"])


class SourceName(unittest.TestCase):
    """The Retarget button's source gives a clip name, or none - never a wrong one."""

    def test_a_namespaced_source_is_named_by_its_namespace(self):
        self.assertEqual(cliplabel.clip_name_from("|A_Jump:root|A_Jump:pelvis"), "A_Jump")

    def test_a_nested_namespace_gives_the_outermost(self):
        self.assertEqual(cliplabel.clip_name_from("|Sweep_Fall:mixamorig:Hips"), "Sweep_Fall")

    def test_a_named_group_above_the_bones_names_it(self):
        self.assertEqual(cliplabel.clip_name_from("|Run_Fwd|root", top_is_joint=False), "Run_Fwd")

    def test_an_importers_wrapper_names_nothing(self):
        for top in ("Armature", "SK_Mannequin_root", "Root", "Group"):
            name = cliplabel.clip_name_from("|%s|root" % top, top_is_joint=False)
            self.assertEqual(name, "" if top != "SK_Mannequin_root" else top)

    def test_a_bare_root_joint_names_nothing(self):
        self.assertEqual(cliplabel.clip_name_from("|root"), "")

    def test_a_scene_opened_from_a_clip_file_names_it(self):
        self.assertEqual(cliplabel.clip_name_from("|root", True, "C:/clips/Walk_01.fbx"), "Walk_01")
        self.assertEqual(cliplabel.clip_name_from("|Hips", True, "D:\\mocap\\jump.BVH"), "jump")

    def test_a_working_scene_never_names_the_clip(self):
        self.assertEqual(cliplabel.clip_name_from("|root", True, "C:/work/shot_010.ma"), "")
        self.assertEqual(cliplabel.clip_name_from("|root", True, "C:/work/shot_010.mb"), "")

    def test_nothing_gives_nothing(self):
        self.assertEqual(cliplabel.clip_name_from(None), "")
        self.assertEqual(cliplabel.clip_name_from("", True, ""), "")


class Follows(unittest.TestCase):
    """Is the follow network whole - the translate from one of ours, one of ours reading the root."""

    def test_whole(self):
        self.assertTrue(cliplabel.follows_plan("loc", "at", ["at", "floor", "mult", "loc"]))

    def test_the_first_builds_constraint_is_not_ours(self):
        self.assertFalse(cliplabel.follows_plan("label_pointConstraint1", None, []))

    def test_nothing_drives_it(self):
        self.assertFalse(cliplabel.follows_plan(None, "at", ["at", "loc"]))

    def test_reading_another_root_is_not_following_this_one(self):
        self.assertFalse(cliplabel.follows_plan("loc", None, ["at", "loc"]))

    def test_the_offset_is_a_world_point_through_the_parents_inverse(self):
        """The fix for a group that moves: the network ends in the label's own
        parentInverseMatrix, so FRONT and the floor stay world numbers."""
        import inspect
        src = inspect.getsource(cliplabel._follow)
        self.assertIn("parentInverseMatrix", src)
        self.assertNotIn("pointConstraint", inspect.getsource(cliplabel._make))


class Clear(unittest.TestCase):
    """A label and its follow nodes go when the character's take is cleared."""

    def test_clear_deletes_the_labels_and_their_parts(self):
        deleted = []
        saved = cliplabel.cmds, cliplabel.labels_of, cliplabel.parts_of
        self.addCleanup(lambda: setattr(cliplabel, "cmds", saved[0]))
        self.addCleanup(lambda: setattr(cliplabel, "labels_of", saved[1]))
        self.addCleanup(lambda: setattr(cliplabel, "parts_of", saved[2]))
        cliplabel.cmds = types.SimpleNamespace(
            ls=lambda node, long=False: [node], objExists=lambda node: True,
            delete=lambda nodes: deleted.extend(nodes))
        cliplabel.labels_of = lambda root: ["|g|ns:clipLabel"]
        cliplabel.parts_of = lambda label: ["ns:clipLabel_rootAt", "ns:clipLabel_labelLocal"]
        self.assertEqual(cliplabel.clear("|ns:root"), 1)
        self.assertEqual(deleted, ["ns:clipLabel_rootAt", "ns:clipLabel_labelLocal",
                                   "|g|ns:clipLabel"])

    def test_clear_rig_never_raises(self):
        saved = cliplabel.clear
        self.addCleanup(lambda: setattr(cliplabel, "clear", saved))
        cliplabel.clear = lambda root: 1 / 0
        rig = types.SimpleNamespace(skeleton_root="|r:root", main="r:Main")
        self.assertEqual(cliplabel.clear_rig(rig), 0)

    def test_relabel_without_a_name_clears(self):
        calls = []
        saved = cliplabel.clip_name_of, cliplabel.clear_rig, cliplabel.label_rig
        self.addCleanup(lambda: setattr(cliplabel, "clip_name_of", saved[0]))
        self.addCleanup(lambda: setattr(cliplabel, "clear_rig", saved[1]))
        self.addCleanup(lambda: setattr(cliplabel, "label_rig", saved[2]))
        cliplabel.clear_rig = lambda rig: calls.append("clear")
        cliplabel.label_rig = lambda rig, name: calls.append(("label", name))
        cliplabel.clip_name_of = lambda source: ""
        cliplabel.relabel_rig("R", "|root")
        cliplabel.clip_name_of = lambda source: "A_Jump"
        cliplabel.relabel_rig("R", "|A_Jump:root")
        self.assertEqual(calls, ["clear", ("label", "A_Jump")])


class EveryRoad(unittest.TestCase):
    """Every road that puts a clip on a character asks for its label - the rig
    press (`retarget_imported`, which the button, a drag and a batch square
    share) and the two skeleton presses."""

    def test_the_rig_press_labels_the_rig_after_the_bake(self):
        calls = []
        saved = dict(cmds=rigimport.cmds, label=rigimport._label)

        def restore():
            rigimport.cmds = saved["cmds"]
            rigimport._label = saved["label"]
        self.addCleanup(restore)
        rr = types.SimpleNamespace(
            connect=lambda source_root=None, rig=None: calls.append("connect") or "connected",
            bake=lambda rig=None: calls.append("bake") or "baked")
        rigs = types.SimpleNamespace(label=lambda rig: rig.namespace)
        mod = types.SimpleNamespace(holder_of=lambda rig: "holder")
        saved_modules = dict((n, sys.modules.get(n)) for n in ("maya_rig_retarget", "maya_rigs"))

        def put_back():
            for n, m in saved_modules.items():
                if m is None:
                    sys.modules.pop(n, None)
                else:
                    sys.modules[n] = m
        self.addCleanup(put_back)
        sys.modules["maya_rig_retarget"] = rr
        sys.modules["maya_rigs"] = rigs
        rigimport.cmds = types.SimpleNamespace(
            objExists=lambda node: True,
            namespace=lambda **k: calls.append("delete_ns"))
        rigimport._label = lambda rig, name: calls.append(("label", rig.namespace, name))
        rig = types.SimpleNamespace(namespace="Manny_Rig1")
        line, failure = rigimport.retarget_imported(rig, mod, "A", {"start": 0.0, "end": 9.0},
                                                    "|A:root", "A_Jump")
        self.assertEqual(failure, "")
        self.assertEqual(calls, ["connect", "bake", "delete_ns", ("label", "Manny_Rig1", "A_Jump")])

    def _onto(self):
        calls = []
        si = skeletonimport
        saved = dict(cmds=si.cmds, new=si.new_skeleton, transfer=si.transfer,
                     label=si._label, wrap=si.rigimport._wrap, move=si.rigimport.move_wrapper)

        def restore():
            si.cmds = saved["cmds"]
            si.new_skeleton = saved["new"]
            si.transfer = saved["transfer"]
            si._label = saved["label"]
            si.rigimport._wrap = saved["wrap"]
            si.rigimport.move_wrapper = saved["move"]
        self.addCleanup(restore)
        si.new_skeleton = lambda entry: ("|root1", "added")
        si.transfer = lambda *a: calls.append("transfer") or dict(
            twin=True, moved=9, skipped=[], missing=[])
        si._label = lambda root, name: calls.append(("label", root, name))
        si.rigimport._wrap = lambda source, ns: ("%s:shift" % ns, "|%s:shift|%s:root" % (ns, ns))
        si.rigimport.move_wrapper = lambda *a, **k: "kept in place at (0, 0)"
        si.cmds = types.SimpleNamespace(
            ls=lambda node, uuid=False, long=False: ["UUID"] if uuid else ["|root1"],
            getAttr=lambda plug, time=None: [0.0] * 16,
            namespace=lambda **k: calls.append("delete_ns"))
        return calls

    def test_a_new_skeleton_is_labelled_after_the_clip_went_on(self):
        calls = self._onto()
        entry = types.SimpleNamespace(key="Manny_Skeleton", label="Manny UE5 [skeleton]")
        line, failure, _top = skeletonimport.onto_skeleton(
            entry, "A", {"start": 0.0, "end": 9.0}, "|A:root", "A_Walk", None)
        self.assertEqual(failure, "")
        self.assertEqual(calls, ["transfer", "delete_ns", ("label", "|root1", "A_Walk")])

    def test_a_skeleton_in_the_scene_is_labelled_too(self):
        calls = self._onto()
        saved_links, saved_label = skeletonimport._links, skeletonimport.skeleton_label
        self.addCleanup(lambda: setattr(skeletonimport, "_links", saved_links))
        self.addCleanup(lambda: setattr(skeletonimport, "skeleton_label", saved_label))
        skeletonimport._links = lambda root: []
        skeletonimport.skeleton_label = lambda root: "root"
        line, failure = skeletonimport.onto_existing(
            "|root", "A", {"start": 0.0, "end": 9.0}, "|A:root", "A_Run",
            {"point": (0.0, 0.0, 0.0), "yaw": 0.0, "kept": True})
        self.assertEqual(failure, "")
        self.assertEqual(calls, ["transfer", "delete_ns", ("label", "|root", "A_Run")])

    def test_the_seams_ask_cliplabel(self):
        saved = cliplabel.label_rig, cliplabel.label_skeleton

        def restore():
            cliplabel.label_rig, cliplabel.label_skeleton = saved
        self.addCleanup(restore)
        cliplabel.label_rig = lambda rig, name: ("rig", rig, name)
        cliplabel.label_skeleton = lambda root, name: ("skeleton", root, name)
        self.assertEqual(rigimport._label("R", "A"), ("rig", "R", "A"))
        self.assertEqual(skeletonimport._label("|root", "A"), ("skeleton", "|root", "A"))


if __name__ == "__main__":
    unittest.main()
