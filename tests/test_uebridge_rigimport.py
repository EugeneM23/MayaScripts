"""Tests for the bridge's one-press pipeline: the pure halves.

The press itself -- add the rig, import, retarget, bake, delete the source
-- needs a Maya and a 53 MB rig file, and is proved by
docs/superpowers/plans/verify_rig_pipeline.py in mayapy standalone. What is
testable here is every decision the press makes before and after touching
the scene: the refusals, which node is the source's root, and the wording.
"""

import math
import sys
import types
import unittest


def yaw_matrix(degrees, position):
    """A node turned `degrees` about world Y, standing at `position`: the flat
    row-major 16 list Maya's xform -q -ws -m answers."""
    a = math.radians(degrees)
    c, s = math.cos(a), math.sin(a)
    return [c, 0.0, -s, 0.0, 0.0, 1.0, 0.0, 0.0, s, 0.0, c, 0.0] + list(position) + [1.0]


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


class Place(unittest.TestCase):
    """2026-10-01: «я хочу чтобы риг остался на своем месте» - the rig's Main
    at the clip's first frame onto where it stood, turned as it was."""

    def test_the_heading_is_the_z_axis_on_the_floor(self):
        self.assertAlmostEqual(rigimport.heading(yaw_matrix(60.0, (0, 0, 0))), 60.0)
        self.assertAlmostEqual(rigimport.heading(yaw_matrix(-135.0, (0, 0, 0))), -135.0)

    def test_turn_about_mains_start_then_move_it_onto_the_place(self):
        pivot, turn, move = rigimport.place_moves(
            (90.0, 0.0, -40.0), 60.0, yaw_matrix(10.0, (5.0, 92.0, 20.0)))
        self.assertEqual(pivot, (5.0, 92.0, 20.0))
        self.assertAlmostEqual(turn, 50.0)
        self.assertEqual(move, (85.0, 0.0, -60.0))

    def test_the_short_way_round(self):
        self.assertAlmostEqual(rigimport.place_moves(
            (0, 0, 0), 170.0, yaw_matrix(-170.0, (0, 0, 0)))[1], -20.0)

    def test_no_heading_no_turn(self):
        """A floor point: the clip keeps its own facing."""
        self.assertEqual(rigimport.place_moves(
            (100.0, 0.0, -50.0), None, yaw_matrix(30.0, (5.0, 92.0, 20.0))),
            ((5.0, 92.0, 20.0), 0.0, (95.0, 0.0, -70.0)))


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
        self.main = "|%s:Group|%s:Main" % (namespace, namespace)

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
        real_label = rigimport._label        # the clip's name under the rig: tested apart
        rigimport._label = lambda rig, name: None
        self.addCleanup(lambda: setattr(rigimport, "_label", real_label))
        real_unlabel = rigimport._unlabel
        rigimport._unlabel = lambda rig: self.calls.append(("unlabel", rig.namespace)) or 0
        self.addCleanup(lambda: setattr(rigimport, "_unlabel", real_unlabel))
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
                setattr(self, "connected", True) or
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
        self.main_place = yaw_matrix(0.0, (0.0, 0.0, 0.0))   # where the rig stands
        self.main_start = yaw_matrix(0.0, (5.0, 92.0, 20.0))  # where the clip puts Main

        def xform(node, query=False, worldSpace=False, matrix=False, pivots=None):
            if pivots is not None:
                self.calls.append(("pivot", node, tuple(pivots)))
                return None
            return list(self.main_start if self.connected else self.main_place)

        self.connected = False
        fake_cmds = types.SimpleNamespace(
            xform=xform,
            currentTime=lambda *a, **k: 0.0,
            setAttr=lambda plug, value: self.calls.append(("rotate", plug, round(value, 9))),
            ungroup=lambda node: self.calls.append(("ungroup", node)),
            ls=lambda node, uuid=False, long=False: (
                ["UUID-" + node] if uuid else [self.paths.get(node, node)]),
            group=lambda node, name=None: self.calls.append(("group", node, name)) or (
                self.paths.update({"UUID-" + node: "|%s|%s" % (name, node.lstrip("|"))})
                or name),
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
        return [c[0] for c in self.calls if c[0] not in ("undo", "which", "unlabel")]

    def _one_rig_current(self):
        self.current = [self.rigs[0], ""]

    def test_with_a_rig_standing_the_press_resets_imports_connects_bakes_deletes(self):
        self._one_rig_current()
        text = rigimport.import_and_retarget("C:/t/A_Jump.fbx", "A_Jump")
        self.assertEqual(self._steps(), ["import", "reset", "group", "connect", "move",
                                         "bake", "delete_ns"])
        self.assertEqual([c for c in self.calls if c[0] == "connect"][0][1:],
                         ("|A_Jump:%s|A_Jump:root" % rigimport.SHIFT_NODE, "Manny_Rig"))
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

    def test_a_standing_rig_keeps_its_place_and_its_turn(self):
        """2026-10-01, «я хочу чтобы риг остался на своем месте»: read where
        Main stands BEFORE the reset zeroes it, then after the connect turn the
        clip about Main's start and move it there - a drop and the Import
        button alike; a floor point given with a standing rig changes nothing."""
        self._one_rig_current()
        self.main_place = yaw_matrix(60.0, (90.0, 0.0, -40.0))
        self.main_start = yaw_matrix(10.0, (5.0, 92.0, 20.0))
        text = rigimport.import_and_retarget("C:/t/A.fbx", "A", at=(300.0, 0.0, 300.0))
        self.assertEqual(self._steps(), ["import", "reset", "group", "connect", "pivot",
                                         "rotate", "move", "bake", "delete_ns"])
        group = "A:" + rigimport.SHIFT_NODE
        self.assertIn(("pivot", group, (5.0, 92.0, 20.0)), self.calls)
        self.assertIn(("rotate", group + ".rotateY", 50.0), self.calls)
        move = [c for c in self.calls if c[0] == "move"][0]
        self.assertEqual((move[1], move[2]), ((85.0, 0.0, -60.0), group))
        self.assertIn("kept in place at (90, -40)", text)

    def test_an_unturned_rig_gets_no_turn(self):
        self._one_rig_current()
        rigimport.import_and_retarget("C:/t/A.fbx", "A")
        self.assertNotIn("rotate", self._steps())
        self.assertNotIn("pivot", self._steps())

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
        # since 2026-10-02 the clip comes in first (the retarget version is
        # asked before the rig's take is reset) and goes again on the refusal
        self.assertEqual(self._steps(), ["import", "reset", "delete_ns"])
        # the take is gone, so its label went with it - a refusal leaves no lie
        self.assertIn(("unlabel", "Manny_Rig"), self.calls)

    def test_the_reset_takes_the_rigs_clip_label_with_the_take(self):
        """2026-10-02: whatever clears the take clears the name; the press
        writes the new one only after its bake."""
        self._one_rig_current()
        rigimport.import_and_retarget("C:/t/A.fbx", "A")
        names = [c[0] for c in self.calls]
        self.assertEqual(names[names.index("reset") + 1], "unlabel")

    def test_a_connect_refusal_leaves_no_label_standing(self):
        self._one_rig_current()
        self.rr.connect = lambda source_root=None, rig=None: "no bone of A matches"
        rigimport.import_and_retarget("C:/t/A.fbx", "A")
        self.assertIn(("unlabel", "Manny_Rig"), self.calls)

    def test_a_connect_refusal_keeps_the_imported_skeleton(self):
        self._one_rig_current()
        self.rr.connect = lambda source_root=None, rig=None: (
            self.calls.append(("connect", source_root, rig.namespace)) or "no bone of A matches")
        text = rigimport.import_and_retarget("C:/t/A.fbx", "A")
        self.assertEqual(self._steps(), ["import", "reset", "group", "connect", "ungroup"])
        self.assertIn("retarget refused: no bone of A matches", text)
        self.assertIn("imported as A", text)

    def test_the_whole_press_is_one_undo_chunk(self):
        self._one_rig_current()
        rigimport.import_and_retarget("C:/t/A.fbx", "A")
        undo = [c[1] for c in self.calls if c[0] == "undo"]
        self.assertEqual(undo, [("chunkName", "openChunk"), ("closeChunk",)])

    # ---- 2026-10-01: the pieces a press of several animations reuses

    def test_plan_press_refuses_a_missing_rig_file_before_anything(self):
        rigimport._rig_file_ok = lambda entry=None: False
        real_name = rigimport._rig_file_name
        rigimport._rig_file_name = lambda entry: "Manny_Rig.ma"
        self.addCleanup(setattr, rigimport, "_rig_file_name", real_name)
        plan, refusal = rigimport.plan_press("new_rig")
        self.assertIsNone(plan)
        self.assertIn("missing from assets", refusal)
        self.assertEqual(self.calls, [])

    def test_plan_press_for_a_new_rig_adds_the_active_characters_rig(self):
        plan, refusal = rigimport.plan_press("new_rig", rig=self.rigs[0])
        self.assertEqual(refusal, "")
        self.assertTrue(plan["add"])
        self.assertIsNone(plan["rig"])
        self.assertEqual(plan["entry"].key, "Manny_Rig")

    def test_ready_rig_adds_a_rig_on_every_call(self):
        plan, _ = rigimport.plan_press("new_rig")
        first = rigimport.ready_rig(plan)
        second = rigimport.ready_rig(plan)
        self.assertEqual((first[0].namespace, second[0].namespace), ("Manny_Rig1", "Manny_Rig2"))
        self.assertEqual((first[3], second[3]), ("", ""))
        self.assertEqual(self._steps(), ["add", "add"])

    def test_import_source_names_the_topmost_joint(self):
        namespace, info, source = rigimport.import_source("C:/t/A.fbx", "A", 30.0, False)
        self.assertEqual((namespace, source, info["end"]), ("A", "|A:root", 45.0))

    def test_retarget_imported_on_a_slot(self):
        plan, _ = rigimport.plan_press("new_rig")
        rig, mod, notes, _failure = rigimport.ready_rig(plan)
        namespace, info, source = rigimport.import_source("C:/t/A.fbx", "A")
        line, failure = rigimport.retarget_imported(
            rig, mod, namespace, info, source, "A", {"point": (-250.0, 0.0, 0.0), "yaw": None})
        self.assertEqual(failure, "")
        self.assertEqual(self._steps(), ["add", "import", "group", "connect", "move", "bake",
                                         "delete_ns"])
        self.assertIn("retargeted onto Manny_Rig1", line)
        self.assertIn("standing at floor (-250, 0)", line)

    def test_stand_skeleton_moves_its_wrapper_onto_the_point(self):
        """A skeleton of several in a line: the root, at the clip's first
        frame, onto its slot, horizontally - by a wrapper, keys untouched."""
        rigimport.cmds.getAttr = lambda plug, time=None: (
            self.calls.append(("read", plug, time)) or
            [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 4.0, 90.0, -12.0, 1])
        moved = rigimport.stand_skeleton("A", "|A:root", (250.0, 0.0, 0.0), 3.0)
        self.assertEqual(moved, (246.0, 12.0))
        self.assertIn(("read", "|A:root.worldMatrix[0]", 3.0), self.calls)
        self.assertEqual([c for c in self.calls if c[0] == "group"],
                         [("group", "|A:root", "A:" + rigimport.SHIFT_NODE)])
        self.assertEqual([c for c in self.calls if c[0] == "move"],
                         [("move", (246.0, 0.0, 12.0), "A:" + rigimport.SHIFT_NODE, True, True)])


if __name__ == "__main__":
    unittest.main()
