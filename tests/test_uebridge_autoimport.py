"""The Auto card's import (2026-10-02): ours if the clip's skeleton is ours, else its own.

Every scene call is faked - the import, the match, the rig, the retarget, the keeping. What is
tested is which road each match takes, what a failure takes back, and the pure halves of
`autoimport` and `nativeimport`. The scene half is docs/superpowers/plans/verify_auto_character.py.

Spec: docs/superpowers/specs/2026-10-02-auto-character-import-design.md
"""
import collections
import math
import sys
import types
import unittest


def _install_fake_maya():
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

from maya_uebridge import autoimport, nativeimport, rigimport, skeletonmatch  # noqa: E402

Rig = collections.namedtuple("Rig", "namespace")


class Pure(unittest.TestCase):

    def test_nine_frames_both_ends_in(self):
        frames = autoimport.sample_frames(0.0, 80.0)
        self.assertEqual(len(frames), 9)
        self.assertEqual((frames[0], frames[-1]), (0.0, 80.0))

    def test_a_short_clip_samples_each_frame_once(self):
        self.assertEqual(autoimport.sample_frames(0.0, 3.0), [0.0, 1.0, 2.0, 3.0])
        self.assertEqual(autoimport.sample_frames(5.0, 5.0), [5.0])
        self.assertEqual(autoimport.sample_frames(None, None), [None])

    def test_the_selection_names_one_rig_or_none(self):
        a, b = Rig("Manny_Rig"), Rig("Creep_Rig")
        self.assertEqual(autoimport.pick_rig([None, None]), (None, ""))
        self.assertEqual(autoimport.pick_rig([a, None, a]), (a, ""))
        rig, refusal = autoimport.pick_rig([a, b])
        self.assertIsNone(rig)
        self.assertIn("two rigs selected", refusal)

    def test_the_largest_mesh_names_a_native(self):
        self.assertEqual(nativeimport.native_base([("Hat", 120), ("Kwang_GDC", 40000)],
                                                  "Ability_Q_Catch", "root"), "Kwang_GDC")
        self.assertEqual(nativeimport.native_base([], "Ability_Q_Catch", "root"),
                         "Ability_Q_Catch")
        self.assertEqual(nativeimport.native_base([], "", "Hips"), "Hips")

    def test_a_world_move_in_the_parent_s_space(self):
        self.assertEqual(nativeimport.local_delta((1.0, 2.0, 3.0), None), (1.0, 2.0, 3.0))
        # Maya's row vectors: a node's world point is p_local * M. A parent turned +90 deg about
        # Y has rows x -> (0, 0, -1), z -> (1, 0, 0): its local +Z points along world +X, so its
        # INVERSE takes a world +X move onto local +Z - the sign is the convention, asserted.
        world = [0, 0, -1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1]
        inverse = [0, 0, 1, 0, 0, 1, 0, 0, -1, 0, 0, 0, 0, 0, 0, 1]
        x, y, z = nativeimport.local_delta((10.0, 0.0, 0.0), inverse)
        self.assertAlmostEqual(x, 0.0)
        self.assertAlmostEqual(z, 10.0)
        back = nativeimport.local_delta((x, y, z), world)
        for got, want in zip(back, (10.0, 0.0, 0.0)):
            self.assertAlmostEqual(got, want)
        # not symmetric: 30 deg about Y, a non-uniform scale, and a translation row to ignore -
        # the row-vector product written out, and the column-vector one shown to differ
        c, s = math.cos(math.radians(30)), math.sin(math.radians(30))
        m = [2 * c, 0, -2 * s, 0, 0, 1, 0, 0, 0.5 * s, 0, 0.5 * c, 0, 7.0, 8.0, 9.0, 1]
        v = (3.0, -1.0, 4.0)
        rows = (v[0] * m[0] + v[1] * m[4] + v[2] * m[8],
                v[0] * m[1] + v[1] * m[5] + v[2] * m[9],
                v[0] * m[2] + v[1] * m[6] + v[2] * m[10])
        columns = (v[0] * m[0] + v[1] * m[1] + v[2] * m[2],
                   v[0] * m[4] + v[1] * m[5] + v[2] * m[6],
                   v[0] * m[8] + v[1] * m[9] + v[2] * m[10])
        got = nativeimport.local_delta(v, m)
        for g, want in zip(got, rows):
            self.assertAlmostEqual(g, want)
        self.assertGreater(max(abs(a - b) for a, b in zip(rows, columns)), 1.0)

    def test_only_a_chain_of_namespaces_is_flattened(self):
        self.assertTrue(nativeimport.single_chain("A", ["A:mixamorig"]))
        self.assertTrue(nativeimport.single_chain("A", ["A:b", "A:b:c"]))
        self.assertTrue(nativeimport.single_chain("A", []))
        self.assertFalse(nativeimport.single_chain("A", ["A:Hero", "A:Enemy"]))
        self.assertFalse(nativeimport.single_chain("A", ["A:b", "A:b:c", "A:b:d"]))

    def test_namespaces_deepest_first(self):
        self.assertEqual(nativeimport.depth_first(["A", "A:mixamorig", "A:b:c", ""]),
                         ["A:b:c", "A:mixamorig", "A"])

    def test_the_line_of_a_kept_clip(self):
        line = nativeimport.line_for("Ability_Q_Catch", "Kwang_GDC", 116, 1,
                                     {"start": 0.0, "end": 36.0},
                                     "no skeleton of ours (best Orc D [rig]: 3 % of 64 bones)",
                                     "standing at floor (120, -36)")
        self.assertEqual(line, "Ability_Q_Catch: no skeleton of ours (best Orc D [rig]: 3 % of "
                               "64 bones) - in its own skeleton Kwang_GDC: 116 joints, 1 mesh, "
                               "frames 0-36  |  standing at floor (120, -36)")
        self.assertIn("2 meshes", nativeimport.line_for("A", "B", 1, 2, {}))


class Press(unittest.TestCase):
    """`import_auto`'s roads, every scene step faked."""

    def setUp(self):
        self.calls = []
        self.match_key = None
        saved = [(rigimport, n, getattr(rigimport, n)) for n in (
            "time_state", "restore_time", "import_source", "_undo_failed_import")]
        saved += [(autoimport, n, getattr(autoimport, n)) for n in (
            "match_clip", "onto_new_rig", "onto_new_skeleton")]
        saved += [(nativeimport, "keep", nativeimport.keep)]
        self.addCleanup(lambda: [setattr(o, n, v) for o, n, v in saved])
        saved_ns = autoimport.animimport.existing_namespaces
        self.addCleanup(setattr, autoimport.animimport, "existing_namespaces", saved_ns)
        autoimport.animimport.existing_namespaces = lambda: []

        rigimport.time_state = lambda: "T"
        rigimport.restore_time = lambda state: self.calls.append(("restore", state))
        self.raise_on_import = None

        def import_source(fbx, name, clip_fps=None, set_timeline=True):
            self.calls.append(("import", fbx, name, clip_fps, set_timeline))
            if self.raise_on_import:
                raise RuntimeError(self.raise_on_import)
            return name, {"start": 0.0, "end": 10.0}, "|%s:root" % name
        rigimport.import_source = import_source
        rigimport._undo_failed_import = lambda before, plan, rig: (
            self.calls.append(("undo", plan, rig)) or "nothing of it was kept")

        def match_clip(source, info, kind):
            self.calls.append(("match", source, kind))
            best = skeletonmatch.Score(self.match_key or "Orc_D_Rig",
                                       1.0 if self.match_key else 0.45, 78, 0.0)
            return skeletonmatch.Match(self.match_key, best, [best])
        autoimport.match_clip = match_clip
        nativeimport.keep = lambda ns, info, source, name, at=None, why="": (
            self.calls.append(("keep", ns, name, at, why)) or ("kept " + name, "", "SK"))
        autoimport.onto_new_rig = lambda entry, ns, info, source, name, at=None: (
            self.calls.append(("rig", entry.key, ns, at)) or ("onto " + entry.key, "", "R"))
        autoimport.onto_new_skeleton = lambda entry, ns, info, source, name, at=None, \
            decide=None: (self.calls.append(("skeleton", entry.key, ns, at))
                          or ("onto " + entry.key, "", "root"))

    def roads(self):
        return [c[0] for c in self.calls if c[0] in ("keep", "rig", "skeleton")]

    def test_nobody_s_skeleton_is_kept_as_its_own(self):
        text = autoimport.import_auto("C:/t/K.fbx", "K", "rig", 30.0, True, (5.0, 0.0, 6.0))
        self.assertEqual(self.roads(), ["keep"])
        keep = [c for c in self.calls if c[0] == "keep"][0]
        self.assertEqual(keep[1:4], ("K", "K", (5.0, 0.0, 6.0)))
        self.assertIn("no skeleton of ours (best Orc D [rig]: 45 % of 78 bones)", keep[4])
        self.assertEqual(text, "kept K")

    def test_a_matched_rig_row_takes_the_clip(self):
        self.match_key = "Manny_Rig"
        text = autoimport.import_auto("C:/t/A.fbx", "A", "rig")
        self.assertEqual(self.roads(), ["rig"])
        self.assertEqual([c for c in self.calls if c[0] == "rig"][0][1:], ("Manny_Rig", "A", None))
        self.assertEqual(text, "matched Manny [rig] - 78 of 78 bones  |  onto Manny_Rig")

    def test_a_matched_skeleton_row_takes_the_clip(self):
        self.match_key = "UE4_Mannequin"
        text = autoimport.import_auto("C:/t/U.fbx", "U", "skeleton", at=(1.0, 0.0, 2.0))
        self.assertEqual([c for c in self.calls if c[0] == "skeleton"][0][1:],
                         ("UE4_Mannequin", "U", (1.0, 0.0, 2.0)))
        self.assertTrue(text.startswith("matched UE4 Mannequin [skeleton]"))

    def test_the_match_is_asked_among_the_kind(self):
        autoimport.import_auto("C:/t/A.fbx", "A", "skeleton")
        self.assertEqual([c[2] for c in self.calls if c[0] == "match"], ["skeleton"])

    def test_a_failed_import_takes_back_what_it_made(self):
        self.raise_on_import = "take not found\nmore"
        text = autoimport.import_auto("C:/t/A.fbx", "A", "rig")
        self.assertEqual(self.roads(), [])
        self.assertIn(("undo", {}, None), self.calls)
        self.assertIn(("restore", "T"), self.calls)
        self.assertEqual(text, "A could not be imported: take not found - nothing of it was kept")

    def test_a_clip_with_no_joint(self):
        rigimport.import_source = lambda fbx, name, clip_fps=None, set_timeline=True: (
            "A", {}, None)
        text = autoimport.import_auto("C:/t/A.fbx", "A", "rig")
        self.assertEqual(text, rigimport.NO_JOINT.format("A", "A"))

    def test_a_cancel_puts_the_time_back(self):
        import maya_retargetmode
        self.match_key = "Manny_Rig"

        def cancel(*a, **k):
            raise maya_retargetmode.Cancelled("A")
        autoimport.onto_new_rig = cancel
        self.assertEqual(autoimport.import_auto("C:/t/A.fbx", "A", "rig"), rigimport.CANCELLED)
        self.assertIn(("restore", "T"), self.calls)

    def test_an_unknown_kind_imports_nothing(self):
        self.assertIn("unknown kind", autoimport.import_auto("C:/t/A.fbx", "A", "prop"))
        self.assertEqual(self.calls, [])


class OntoNewRig(unittest.TestCase):
    """A matched rig row: the rig added, the clip retargeted, one undo chunk."""

    def setUp(self):
        self.calls = []
        saved = [(rigimport, n, getattr(rigimport, n)) for n in (
            "_rig_file_ok", "ready_rig", "decide_bones", "retarget_imported", "discard_added")]
        saved += [(autoimport, "cmds", autoimport.cmds)]
        self.addCleanup(lambda: [setattr(o, n, v) for o, n, v in saved])
        saved_rigs = sys.modules.get("maya_rigs")
        self.addCleanup(lambda: sys.modules.__setitem__("maya_rigs", saved_rigs)
                        if saved_rigs is not None else sys.modules.pop("maya_rigs", None))
        sys.modules["maya_rigs"] = types.SimpleNamespace(label=lambda rig: rig.namespace)
        autoimport.cmds = types.SimpleNamespace(
            undoInfo=lambda **k: self.calls.append(("undo", tuple(sorted(k)))),
            namespace=lambda exists=None, removeNamespace=None, **k: (
                True if exists is not None else self.calls.append(("discard", removeNamespace))))
        rigimport._rig_file_ok = lambda entry=None: True
        rigimport.ready_rig = lambda plan: (
            self.calls.append(("add", plan["entry"], plan["add"]))
            or (Rig("Manny_Rig1"), "mod", ["added"], ""))
        import maya_retargetmode
        self.decision = maya_retargetmode.Decision("stretch", False, "stretch - twin, exact", True)
        rigimport.decide_bones = lambda rig, mod, source: self.decision
        rigimport.retarget_imported = lambda rig, mod, ns, info, source, name, place=None, \
            bones=None: (self.calls.append(("retarget", rig.namespace, place, bones))
                         or ("A retargeted", ""))
        rigimport.discard_added = lambda rig: self.calls.append(("discard_rig", rig.namespace))
        from maya_scenesetup import catalog
        self.entry = catalog.character_by_key("Manny_Rig")

    def test_the_rig_is_added_and_the_clip_retargeted_standing_on_the_point(self):
        line, failure, label = autoimport.onto_new_rig(self.entry, "A", {}, "|A:root", "A",
                                                       (3.0, 0.0, 4.0))
        self.assertEqual((failure, label), ("", "Manny_Rig1"))
        self.assertIn(("add", self.entry, True), self.calls)
        self.assertIn(("retarget", "Manny_Rig1", {"point": (3.0, 0.0, 4.0), "yaw": None},
                       "stretch"), self.calls)
        self.assertEqual(line, "added  |  stretch - twin, exact  |  A retargeted")
        undo = [c[1] for c in self.calls if c[0] == "undo"]
        self.assertEqual(undo, [("chunkName", "openChunk"), ("closeChunk",)])

    def test_a_missing_rig_file_discards_the_clip(self):
        rigimport._rig_file_ok = lambda entry=None: False
        line, failure, label = autoimport.onto_new_rig(self.entry, "A", {}, "|A:root", "A")
        self.assertIn("no rig file", failure)
        self.assertIn(("discard", "A"), self.calls)
        self.assertNotIn("add", [c[0] for c in self.calls])

    def test_a_cancel_removes_the_rig_and_the_clip(self):
        import maya_retargetmode

        def cancel(rig, mod, source):
            raise maya_retargetmode.Cancelled("A")
        rigimport.decide_bones = cancel
        with self.assertRaises(maya_retargetmode.Cancelled):
            autoimport.onto_new_rig(self.entry, "A", {}, "|A:root", "A")
        self.assertIn(("discard", "A"), self.calls)
        self.assertIn(("discard_rig", "Manny_Rig1"), self.calls)
        self.assertEqual([c[1] for c in self.calls if c[0] == "undo"][-1], ("closeChunk",))


class KeptSelection(unittest.TestCase):
    """The review, 2026-10-02: a rig an Auto press adds selects itself (Add Character's rule), and
    the next Auto press, Onto selected, read that as the animator's explicit target. The press
    leaves the selection as it found it."""

    def setUp(self):
        self.selection = []
        self.nodes = {"|Manny_Rig:Main": "U-MAIN", "|cube": "U-CUBE"}
        saved = autoimport.cmds
        self.addCleanup(setattr, autoimport, "cmds", saved)

        def ls(*args, **kwargs):
            if kwargs.get("selection"):
                return list(self.selection)
            items = args[0] if args else []
            items = [items] if isinstance(items, str) else list(items)
            if kwargs.get("uuid"):
                return [self.nodes[i] for i in items if i in self.nodes]
            back = dict((u, p) for p, u in self.nodes.items())
            return [back[i] for i in items if i in back]

        def select(*args, **kwargs):
            if kwargs.get("clear"):
                self.selection = []
            else:
                self.selection = list(args[0])
        autoimport.cmds = types.SimpleNamespace(ls=ls, select=select)

    def test_nothing_selected_stays_nothing_selected(self):
        with autoimport.kept_selection():
            self.selection = ["|Manny_Rig:Main"]          # the rig the press added selects itself
        self.assertEqual(self.selection, [])

    def test_the_animator_s_selection_comes_back(self):
        self.selection = ["|cube"]
        with autoimport.kept_selection():
            self.selection = ["|Manny_Rig:Main"]
        self.assertEqual(self.selection, ["|cube"])

    def test_a_scene_less_cmds_keeps_nothing_and_raises_nothing(self):
        autoimport.cmds = types.SimpleNamespace()
        with autoimport.kept_selection() as kept:
            pass
        self.assertIsNone(kept.uuids)


class Purity(unittest.TestCase):

    def test_the_wording_needs_no_scene(self):
        self.assertEqual(autoimport.join("a", "", "b"), "a  |  b")
        self.assertEqual(autoimport.label_of("Orc_D_Rig"), "Orc D [rig]")
        self.assertEqual(autoimport.label_of("Sevarog"), "Sevarog")


if __name__ == "__main__":
    unittest.main()
