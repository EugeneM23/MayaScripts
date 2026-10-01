"""Tests for the bridge's one-press pipeline: the pure halves.

The press itself -- add the rig, import, retarget, bake, delete the source
-- needs a Maya and a 53 MB rig file, and is proved by
docs/superpowers/plans/verify_rig_pipeline.py in mayapy standalone. What is
testable here is every decision the press makes before and after touching
the scene: the refusals, which node is the source's root, and the wording.
"""

import sys
import types
import unittest


def _install_fake_maya():
    """Let rigimport import without Maya. See CLAUDE.md on rebinding."""
    try:
        import maya.cmds  # noqa: F401
        import maya.mel  # noqa: F401
        return
    except ImportError:
        pass
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

from maya_uebridge import rigimport  # noqa: E402


class Precheck(unittest.TestCase):
    """Every refusal happens before anything is imported."""

    def test_no_rig_and_no_rig_file_is_refused_by_the_file(self):
        text = rigimport.precheck(False, False, False, False)
        self.assertEqual(text, rigimport.NO_RIG_FILE.format("Manny_Rig.ma"))
        self.assertIn("Manny_Rig.ma", text)
        self.assertIn("Creep_Rig.ma", rigimport.precheck(False, False, False, False,
                                                         "Creep_Rig.ma"))

    def test_no_rig_but_a_rig_file_goes_ahead(self):
        self.assertEqual(rigimport.precheck(False, False, False, True), "")

    def test_a_standing_holder_names_bake(self):
        text = rigimport.precheck(True, True, False, True)
        self.assertEqual(text, rigimport.CONNECTED)
        self.assertIn("MoCapConstraints", text)
        self.assertIn("Retarget", text)     # one button since 2026-09-08

    def test_a_posed_rig_names_the_vendors_button(self):
        text = rigimport.precheck(True, False, True, True)
        self.assertEqual(text, rigimport.POSED)
        self.assertIn("BuildPose", text)

    def test_a_posed_flag_without_a_rig_means_nothing(self):
        """A freshly added rig stands in its build pose by construction."""
        self.assertEqual(rigimport.precheck(False, False, True, True), "")

    def test_a_missing_rig_file_does_not_matter_when_a_rig_stands(self):
        self.assertEqual(rigimport.precheck(True, False, False, False), "")

    def test_the_holder_outranks_the_pose(self):
        self.assertEqual(rigimport.precheck(True, True, True, True),
                         rigimport.CONNECTED)


class SourceRoot(unittest.TestCase):
    """The imported skeleton's root, from the namespace's DAG nodes."""

    def test_the_topmost_joint_of_the_namespace(self):
        nodes = ["|c:root|c:pelvis", "|c:root", "|c:root|c:pelvis|c:spine_01",
                 "|c:rootShape", "c:animCurve1"]
        self.assertEqual(
            rigimport.source_root_in(nodes, lambda p: not p.endswith("Shape")),
            "|c:root")

    def test_a_nested_namespace_still_resolves(self):
        nodes = ["|m:mixamorig:Hips|m:mixamorig:Spine", "|m:mixamorig:Hips"]
        self.assertEqual(rigimport.source_root_in(nodes, lambda p: True),
                         "|m:mixamorig:Hips")

    def test_no_joint_is_none(self):
        self.assertIsNone(rigimport.source_root_in(["|c:locator1"],
                                                   lambda p: False))
        self.assertIsNone(rigimport.source_root_in([], lambda p: True))

    def test_two_roots_at_one_depth_pick_by_name_so_the_answer_is_stable(self):
        nodes = ["|c:zeta", "|c:alpha"]
        self.assertEqual(rigimport.source_root_in(nodes, lambda p: True),
                         "|c:alpha")


class ResultLine(unittest.TestCase):

    def test_the_rig_is_named_when_given(self):
        text = rigimport.result_line("A", {"start": 0.0, "end": 45.0}, "c", "b", "A", "Manny_Rig1")
        self.assertTrue(text.startswith("A retargeted onto Manny_Rig1, frames 0-45"))

    def test_names_the_clip_the_range_both_steps_and_the_deletion(self):
        text = rigimport.result_line(
            "A_Jump", {"joints": 93, "start": 0.0, "end": 45.0},
            "retarget connected: 74 controls driven\nmore", "baked 20 controls",
            "A_Jump")
        self.assertIn("A_Jump retargeted onto the rig, frames 0-45", text)
        self.assertIn("retarget connected: 74 controls driven", text)
        self.assertNotIn("more", text)
        self.assertIn("baked 20 controls", text)
        self.assertIn("source skeleton A_Jump deleted", text)

    def test_no_range_prints_no_broken_range(self):
        text = rigimport.result_line("A", {"start": None}, "c", "b", "A")
        self.assertNotIn("None", text)

    def test_a_kept_source_says_so(self):
        self.assertIn("source skeleton kept",
                      rigimport.result_line("A", {}, "c", "b", ""))


class RigEntry(unittest.TestCase):
    """2026-10-01: a rig the bridge adds is the one active in Characters, and
    Manny when that is no rig."""

    def test_the_active_rig_row(self):
        creep = types.SimpleNamespace(key="Creep_Rig", kind="rig")
        manny = types.SimpleNamespace(key="Manny_Rig", kind="rig")
        self.assertIs(rigimport.rig_entry_for(creep, manny), creep)

    def test_a_skeleton_or_nothing_is_manny(self):
        manny = types.SimpleNamespace(key="Manny_Rig", kind="rig")
        skeleton = types.SimpleNamespace(key="Creep_Skeleton", kind="skeleton")
        self.assertIs(rigimport.rig_entry_for(skeleton, manny), manny)
        self.assertIs(rigimport.rig_entry_for(None, manny), manny)


class Shift(unittest.TestCase):

    def test_the_root_at_the_first_frame_onto_the_floor_point(self):
        self.assertEqual(rigimport.shift_for((100.0, 0.0, -50.0), (5.0, 92.0, 20.0)),
                         (95.0, 0.0, -70.0))

    def test_the_height_is_never_moved(self):
        self.assertEqual(rigimport.shift_for((0.0, 40.0, 0.0), (0.0, 0.0, 0.0))[1], 0.0)


class FakeRig(object):
    def __init__(self, namespace):
        self.namespace = namespace
        self.skeleton_root = "|%s:root" % namespace if namespace else "|root"

    def __eq__(self, other):
        return isinstance(other, FakeRig) and other.namespace == self.namespace

    def __hash__(self):
        return hash(self.namespace)


class FreshRig(unittest.TestCase):

    def test_the_one_new_namespace_is_the_added_rig(self):
        a, b = FakeRig("Manny_Rig"), FakeRig("Manny_Rig1")
        self.assertEqual(rigimport.fresh_rig([a], [a, b]), b)

    def test_nothing_new_or_two_new_is_none(self):
        a, b, c = FakeRig("Manny_Rig"), FakeRig("Manny_Rig1"), FakeRig("Manny_Rig2")
        self.assertIsNone(rigimport.fresh_rig([a], [a]))
        self.assertIsNone(rigimport.fresh_rig([a], [a, b, c]))
        self.assertEqual(rigimport.fresh_rig([], [a]), a)


class ThePress(unittest.TestCase):
    """The orchestration, with every scene call faked: the order, the early
    returns, the undo chunk, and -- since 2026-09-08 -- which rig."""

    def setUp(self):
        self.calls = []
        self.real_cmds = rigimport.cmds
        self.real_file_ok = rigimport._rig_file_ok
        self.real_import = rigimport.animimport.import_clip
        self.real_namespaces = rigimport.animimport.existing_namespaces
        rigimport._rig_file_ok = lambda entry=None: True
        self.real_entry = rigimport.new_rig_entry
        rigimport.new_rig_entry = lambda: types.SimpleNamespace(key="Manny_Rig", label="Manny [rig]")
        rigimport.animimport.existing_namespaces = lambda: []
        rigimport.animimport.import_clip = lambda *a, **k: (
            self.calls.append(("import", a[1])) or
            {"start": 0.0, "end": 45.0, "joints": 93})
        self.holder = set()
        self.paths = {}
        self.rigs = [FakeRig("Manny_Rig")]
        self.current = [None, ""]     # what current_rig() answers when asked
        self.mod = types.SimpleNamespace(
            holder_of=lambda rig: "%s:MoCapConstraints" % rig.namespace,
            posed_controls=lambda rig=None: [],
            reset_build_pose=lambda rig=None: self.calls.append(("reset", rig.namespace)) or (12, 3),
        )
        self.rr = types.SimpleNamespace(
            rig_module=lambda rig=None: (self.mod, ""),
            connect=lambda source_root=None, rig=None: (
                self.calls.append(("connect", source_root, rig.namespace)) or
                self.holder.add(self.mod.holder_of(rig)) or "retarget connected: 74"),
            bake=lambda rig=None: self.calls.append(("bake", rig.namespace)) or
            self.holder.discard(self.mod.holder_of(rig)) or "baked 20",
        )

        def add_character(entry):
            self.calls.append(("add", entry.key))
            self.rigs.append(FakeRig("Manny_Rig%d" % len(self.rigs)))
            return "Manny [rig] added as %s" % self.rigs[-1].namespace

        self.character = types.SimpleNamespace(add_character=add_character)
        self.catalog = types.SimpleNamespace(
            default_rig=lambda: types.SimpleNamespace(key="Manny_Rig"))

        def current_rig():
            self.calls.append(("which",))
            return tuple(self.current)

        self.maya_rigs = types.SimpleNamespace(
            Rig=FakeRig, rigs=lambda: list(self.rigs), current_rig=current_rig,
            label=lambda rig: rig.namespace or "Group")
        self.root_at = (5.0, 92.0, 20.0)
        fake_cmds = types.SimpleNamespace(
            ls=lambda node, uuid=False, long=False: (
                ["UUID-" + node] if uuid else [self.paths.get(node, node)]),
            group=lambda node, name=None: self.calls.append(("group", node, name)) or (
                self.paths.update({"UUID-" + node: "|%s|%s" % (name, node.lstrip("|"))})
                or name),
            getAttr=lambda plug, time=None: (
                [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0] + list(self.root_at) + [1]),
            move=lambda x, y, z, node, relative=False, worldSpace=False: self.calls.append(
                ("move", (x, y, z), node, relative, worldSpace)),
            objExists=lambda name: name in self.holder,
            undoInfo=lambda **k: self.calls.append(("undo", tuple(sorted(k)))),
            namespaceInfo=lambda ns, **k: ["|%s:root" % ns, "|%s:root|%s:pelvis" % (ns, ns)],
            objectType=lambda p: "joint",
            namespace=lambda **k: self.calls.append(("delete_ns", k.get("removeNamespace"))),
        )
        rigimport.cmds = fake_cmds
        # The lazy imports inside the press are answered from sys.modules;
        # every entry touched is saved whole and put back, so the rest of
        # the suite keeps the real packages (CLAUDE.md's module-object trap).
        self.touched = ("maya_rig_retarget", "maya_rigs", "maya_scenesetup",
                        "maya_scenesetup.character", "maya_scenesetup.catalog")
        self.saved_modules = dict((name, sys.modules.get(name))
                                  for name in self.touched)
        pkg = types.ModuleType("maya_scenesetup")
        pkg.character = self.character
        pkg.catalog = self.catalog
        sys.modules["maya_rig_retarget"] = self.rr
        sys.modules["maya_rigs"] = self.maya_rigs
        sys.modules["maya_scenesetup"] = pkg
        sys.modules["maya_scenesetup.character"] = self.character
        sys.modules["maya_scenesetup.catalog"] = self.catalog

    def tearDown(self):
        rigimport.cmds = self.real_cmds
        rigimport._rig_file_ok = self.real_file_ok
        rigimport.new_rig_entry = self.real_entry
        rigimport.animimport.import_clip = self.real_import
        rigimport.animimport.existing_namespaces = self.real_namespaces
        for name in self.touched:
            if self.saved_modules[name] is not None:
                sys.modules[name] = self.saved_modules[name]
            else:
                sys.modules.pop(name, None)

    def _steps(self):
        return [c[0] for c in self.calls if c[0] not in ("undo", "which")]

    def _one_rig_current(self):
        self.current = [self.rigs[0], ""]

    def test_with_a_rig_standing_the_press_resets_imports_connects_bakes_deletes(self):
        self._one_rig_current()
        text = rigimport.import_and_retarget("C:/t/A_Jump.fbx", "A_Jump")
        self.assertEqual(self._steps(), ["reset", "import", "connect", "bake", "delete_ns"])
        self.assertEqual([c for c in self.calls if c[0] == "connect"][0][1:],
                         ("|A_Jump:root", "Manny_Rig"))
        self.assertIn("previous take cleared (12 curves), rig at build pose", text)
        self.assertIn("A_Jump retargeted onto Manny_Rig, frames 0-45", text)
        self.assertIn("source skeleton A_Jump deleted", text)

    def test_a_clean_rig_says_nothing_about_a_previous_take(self):
        self._one_rig_current()
        self.mod.reset_build_pose = lambda rig=None: self.calls.append(("reset", rig.namespace)) or (0, 0)
        text = rigimport.import_and_retarget("C:/t/A.fbx", "A")
        self.assertNotIn("previous take", text)
        self.assertTrue(text.startswith("A retargeted onto Manny_Rig"))

    def test_without_a_rig_the_press_adds_one_first_and_resets_nothing(self):
        self.rigs[:] = []
        text = rigimport.import_and_retarget("C:/t/A.fbx", "A")
        self.assertEqual(self._steps(), ["add", "import", "connect", "bake", "delete_ns"])
        self.assertTrue(text.startswith("Manny [rig] added as Manny_Rig0  |  "))
        self.assertIn("retargeted onto Manny_Rig0", text)
        self.assertNotIn(("which",), self.calls)     # nothing to choose between

    def test_onto_a_new_rig_adds_one_beside_the_standing_rig(self):
        """«добавить в сцену много ригов ... через import»: the new rig takes
        the clip, the standing one is never asked about, never reset."""
        text = rigimport.import_and_retarget("C:/t/A.fbx", "A", target="new_rig")
        self.assertEqual(self._steps(), ["add", "import", "connect", "bake", "delete_ns"])
        self.assertNotIn(("which",), self.calls)
        self.assertEqual([c for c in self.calls if c[0] == "connect"][0][2], "Manny_Rig1")
        self.assertIn("added as Manny_Rig1", text)
        self.assertIn("retargeted onto Manny_Rig1", text)

    def test_two_rigs_and_no_choice_is_refused_before_anything_is_touched(self):
        self.rigs.append(FakeRig("Manny_Rig1"))
        self.current = [None, "2 rigs in the scene (Manny_Rig, Manny_Rig1) - select"]
        text = rigimport.import_and_retarget("C:/t/A.fbx", "A")
        self.assertEqual(text, "2 rigs in the scene (Manny_Rig, Manny_Rig1) - select")
        self.assertEqual(self._steps(), [])

    def test_the_selected_rig_of_two_takes_the_clip(self):
        second = FakeRig("Manny_Rig1")
        self.rigs.append(second)
        self.current = [second, ""]
        text = rigimport.import_and_retarget("C:/t/A.fbx", "A")
        self.assertEqual([c for c in self.calls if c[0] == "reset"], [("reset", "Manny_Rig1")])
        self.assertEqual([c for c in self.calls if c[0] == "connect"][0][2], "Manny_Rig1")
        self.assertIn("retargeted onto Manny_Rig1", text)

    def test_a_dropped_on_rig_takes_the_clip_and_the_selection_is_not_asked(self):
        """2026-10-01, an animation dragged onto a rig in the viewport: that
        rig, whatever is selected (two rigs, nothing chosen, would refuse)."""
        second = FakeRig("Manny_Rig1")
        self.rigs.append(second)
        self.current = [None, "2 rigs in the scene - select"]
        text = rigimport.import_and_retarget("C:/t/A.fbx", "A", rig=second)
        self.assertNotIn(("which",), self.calls)
        self.assertEqual([c for c in self.calls if c[0] == "reset"], [("reset", "Manny_Rig1")])
        self.assertEqual([c for c in self.calls if c[0] == "connect"][0][2], "Manny_Rig1")
        self.assertIn("retargeted onto Manny_Rig1", text)

    def test_a_new_rig_ignores_a_given_rig(self):
        text = rigimport.import_and_retarget("C:/t/A.fbx", "A", target="new_rig",
                                             rig=self.rigs[0])
        self.assertEqual(self._steps(), ["add", "import", "connect", "bake", "delete_ns"])
        self.assertNotIn("reset", self._steps())
        self.assertIn("retargeted onto Manny_Rig1", text)

    def test_a_new_rig_is_the_active_characters_rig(self):
        rigimport.new_rig_entry = lambda: types.SimpleNamespace(key="Creep_Rig", label="Creep [rig]")
        rigimport.import_and_retarget("C:/t/A.fbx", "A", target="new_rig")
        self.assertEqual([c for c in self.calls if c[0] == "add"], [("add", "Creep_Rig")])

    def test_a_floor_point_moves_the_clip_after_the_connect(self):
        """2026-10-01, «если мы указываем на пол ... риг с анимацией оставался в
        том месте куда мы указали после всех перезапеканий»: the clip's root at
        its first frame onto the point, horizontally, between connect and bake
        - the connect measures the clip unmoved, the bake carries the move."""
        text = rigimport.import_and_retarget("C:/t/A.fbx", "A", target="new_rig",
                                             at=(100.0, 0.0, -50.0))
        self.assertEqual(self._steps(), ["add", "import", "group", "connect", "move",
                                         "bake", "delete_ns"])
        self.assertEqual([c for c in self.calls if c[0] == "group"],
                         [("group", "|A:root", "A:" + rigimport.SHIFT_NODE)])
        self.assertEqual([c for c in self.calls if c[0] == "connect"][0][1],
                         "|A:%s|A:root" % rigimport.SHIFT_NODE)
        self.assertEqual([c for c in self.calls if c[0] == "move"],
                         [("move", (95.0, 0.0, -70.0), "A:" + rigimport.SHIFT_NODE, True, True)])
        self.assertIn("standing at floor (100, -50)", text)

    def test_a_floor_point_does_not_move_a_standing_rig(self):
        self._one_rig_current()
        rigimport.import_and_retarget("C:/t/A.fbx", "A", at=(100.0, 0.0, -50.0))
        self.assertNotIn("group", self._steps())
        self.assertNotIn("move", self._steps())

    def test_an_unknown_target_is_refused(self):
        self.assertIn("unknown import target", rigimport.import_and_retarget("C:/t/A.fbx", "A", target="x"))
        self.assertEqual(self.calls, [])

    def test_a_connected_rig_is_refused_before_anything_is_touched(self):
        self._one_rig_current()
        self.holder.add("Manny_Rig:MoCapConstraints")
        self.assertEqual(rigimport.import_and_retarget("C:/t/A.fbx", "A"),
                         rigimport.CONNECTED)
        self.assertEqual(self._steps(), [])

    def test_a_rig_still_posed_after_the_reset_is_refused_by_name(self):
        """What the reset cannot zero is a channel nothing here may touch."""
        self._one_rig_current()
        self.mod.posed_controls = lambda rig=None: ["FKWrist_R", "FKElbow_R"]
        text = rigimport.import_and_retarget("C:/t/A.fbx", "A")
        self.assertIn(rigimport.POSED, text)
        self.assertIn("FKElbow_R, FKWrist_R", text)
        self.assertEqual(self._steps(), ["reset"])

    def test_a_connect_refusal_keeps_the_imported_skeleton(self):
        self._one_rig_current()
        self.rr.connect = lambda source_root=None, rig=None: (
            self.calls.append(("connect", source_root, rig.namespace)) or "no bone of A matches")
        text = rigimport.import_and_retarget("C:/t/A.fbx", "A")
        self.assertEqual(self._steps(), ["reset", "import", "connect"])
        self.assertIn("retarget refused: no bone of A matches", text)
        self.assertIn("imported as A", text)

    def test_the_whole_press_is_one_undo_chunk(self):
        self._one_rig_current()
        rigimport.import_and_retarget("C:/t/A.fbx", "A")
        undo = [c[1] for c in self.calls if c[0] == "undo"]
        self.assertEqual(undo, [("chunkName", "openChunk"), ("closeChunk",)])


if __name__ == "__main__":
    unittest.main()
