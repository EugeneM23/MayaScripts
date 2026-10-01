"""Several animations at once, in a line (2026-10-01): the press's order.

Every scene call is faked - the editor's export, the import, the rig, the
retarget, the progress window. What is tested is the order (every clip out of
the editor before the first import, every import before the layout, the
timeline once before the first retarget), the slots each clip is given, what a
failure and a cancel leave, and the wording. The scene half is
docs/superpowers/plans/verify_uebridge_many.py's.

Spec: docs/superpowers/specs/2026-10-01-uebridge-many-animations-design.md
"""
import collections
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

from maya_uebridge import lineimport, lineup, rigimport  # noqa: E402

Rec = collections.namedtuple("Rec", "name package")
Rig = collections.namedtuple("Rig", "namespace")

#  each clip's root track over its frames: A still, B wanders 30 to the right
TRACKS = {"A": [(0.0, 0.0, 0.0)] * 3,
          "B": [(5.0, 0.0, 0.0), (35.0, 0.0, 9.0), (15.0, 0.0, 0.0)],
          "C": [(0.0, 0.0, 0.0)] * 3}


class Press(unittest.TestCase):

    def setUp(self):
        self.calls = []
        self.cancel_after = None        # cancel when this many steps were shown
        self.steps = 0
        self.namespaces = set()
        self.records = [Rec(n, "/Game/" + n) for n in ("A", "B", "C")]
        saved = dict((name, getattr(rigimport, name)) for name in (
            "plan_press", "ready_rig", "import_source", "retarget_imported",
            "stand_skeleton", "root_at"))
        saved_cmds = lineimport.cmds
        saved_rigs = sys.modules.get("maya_rigs")

        def restore():
            for name, value in saved.items():
                setattr(rigimport, name, value)
            lineimport.cmds = saved_cmds
            if saved_rigs is not None:
                sys.modules["maya_rigs"] = saved_rigs
            else:
                sys.modules.pop("maya_rigs", None)
        self.addCleanup(restore)

        self.rig_count = 0

        def plan_press(target, rig=None):
            self.calls.append(("plan", target))
            return dict(add=True, entry="Manny", rig=None, mod=None), ""

        def ready_rig(plan):
            self.rig_count += 1
            self.calls.append(("add",))
            return Rig("Manny_Rig%d" % self.rig_count), "mod", ["added"], ""

        def import_source(fbx, name, clip_fps=None, set_timeline=True):
            self.calls.append(("import", name, set_timeline))
            self.namespaces.add(name)
            return name, {"start": 0.0, "end": 2.0 + len(self.calls)}, "|%s:root" % name

        def retarget_imported(rig, mod, namespace, info, source, name, place=None):
            self.calls.append(("retarget", name, rig.namespace, place["point"], place["yaw"]))
            self.namespaces.discard(namespace)
            return "%s retargeted onto %s" % (name, rig.namespace), ""

        def stand_skeleton(namespace, source, point, start=None):
            self.calls.append(("stand", namespace, point, start))
            return (point[0], point[2])

        frames = {}

        def root_at(source, frame=None):
            name = source.split(":")[0].lstrip("|")
            index = frames.setdefault(name, [0])
            point = TRACKS[name][min(index[0], len(TRACKS[name]) - 1)]
            index[0] += 1
            return point

        rigimport.plan_press = plan_press
        rigimport.ready_rig = ready_rig
        rigimport.import_source = import_source
        rigimport.retarget_imported = retarget_imported
        rigimport.stand_skeleton = stand_skeleton
        rigimport.root_at = root_at

        def progress(*args, **kwargs):
            if kwargs.get("query"):
                return self.cancel_after is not None and self.steps >= self.cancel_after
            if kwargs.get("edit"):
                self.steps += 1
                self.calls.append(("step", kwargs.get("status")))
            return None

        lineimport.cmds = types.SimpleNamespace(
            progressWindow=progress,
            playbackOptions=lambda **k: self.calls.append(
                ("timeline", k["minTime"], k["maxTime"])),
            namespace=lambda exists=None, removeNamespace=None, **k: (
                exists in self.namespaces if exists is not None else
                self.calls.append(("discard", removeNamespace)) or
                self.namespaces.discard(removeNamespace)),
            undoInfo=lambda **k: None)
        sys.modules["maya_rigs"] = types.SimpleNamespace(label=lambda rig: rig.namespace)

    def export(self, record):
        self.calls.append(("export", record.name))
        if record.name == getattr(self, "broken", None):
            raise RuntimeError("the editor said no\nAssertion failed")
        return "C:/t/%s.fbx" % record.name, 30.0

    def kinds(self):
        return [c[0] for c in self.calls if c[0] != "step"]

    def test_every_clip_leaves_the_editor_before_the_first_import(self):
        lineimport.run(self.records, self.export, "new_rig")
        kinds = self.kinds()
        self.assertEqual(kinds[:4], ["plan", "export", "export", "export"])
        self.assertEqual(kinds[4:7], ["import", "import", "import"])
        self.assertTrue(all(c[2] is False for c in self.calls if c[0] == "import"))

    def test_new_rigs_stand_on_the_line_in_list_order(self):
        text = lineimport.run(self.records, self.export, "new_rig")
        extents = [lineup.side_extent(TRACKS[n], (1.0, 0.0, 0.0)) for n in "ABC"]
        points = lineup.slots((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), lineup.offsets(extents))
        got = [c for c in self.calls if c[0] == "retarget"]
        self.assertEqual([(c[1], c[2]) for c in got],
                         [("A", "Manny_Rig1"), ("B", "Manny_Rig2"), ("C", "Manny_Rig3")])
        self.assertEqual([c[3] for c in got], points)
        self.assertEqual([c[4] for c in got], [None, None, None])
        self.assertAlmostEqual(points[1][0] - points[0][0], 250.0)          # A is still
        self.assertAlmostEqual(points[2][0] - points[1][0], 250.0 + 30.0)   # B wanders right
        self.assertIn("3 animations onto 3 new rigs in a line about (0, 0)", text)
        self.assertIn("Manny_Rig1 A, Manny_Rig2 B, Manny_Rig3 C", text)
        self.assertIn("widened beside B", text)

    def test_about_a_point_along_an_axis(self):
        lineimport.run(self.records, self.export, "new_rig", centre=(100.0, 0.0, -40.0),
                       axis=(0.0, 3.0, 2.0))
        points = [c[3] for c in self.calls if c[0] == "retarget"]
        self.assertEqual([p[0] for p in points], [100.0, 100.0, 100.0])
        self.assertAlmostEqual(points[0][2] + points[2][2], 2 * -40.0)

    def test_the_timeline_is_the_union_set_once_before_the_first_retarget(self):
        lineimport.run(self.records, self.export, "new_rig")
        kinds = self.kinds()
        self.assertEqual(kinds.count("timeline"), 1)
        self.assertLess(kinds.index("timeline"), kinds.index("add"))
        timeline = [c for c in self.calls if c[0] == "timeline"][0]
        ends = [c for c in self.calls if c[0] == "import"]
        self.assertEqual(timeline[1], 0.0)
        self.assertGreaterEqual(timeline[2], 2.0 + len(ends))

    def test_the_checkbox_off_leaves_the_timeline(self):
        lineimport.run(self.records, self.export, "new_rig", set_timeline=False)
        self.assertNotIn("timeline", self.kinds())

    def test_skeletons_stand_on_the_line_and_no_rig_is_added(self):
        text = lineimport.run(self.records, self.export, "skeleton")
        self.assertNotIn("plan", self.kinds())
        self.assertNotIn("add", self.kinds())
        stood = [c for c in self.calls if c[0] == "stand"]
        self.assertEqual([c[1] for c in stood], ["A", "B", "C"])
        self.assertEqual([c[3] for c in stood], [0.0, 0.0, 0.0])
        self.assertAlmostEqual(stood[0][2][0] + stood[2][2][0], 0.0)
        self.assertIn("3 animations as skeletons in a line about (0, 0): A, B, C", text)

    def test_a_clip_the_editor_cannot_export_is_named_and_left_out(self):
        self.broken = "B"
        text = lineimport.run(self.records, self.export, "new_rig")
        self.assertEqual([c[1] for c in self.calls if c[0] == "retarget"], ["A", "C"])
        self.assertIn("2 of 3 animations", text)
        self.assertIn("failed: B (Assertion failed)", text)

    def test_a_rig_file_refusal_touches_nothing(self):
        rigimport.plan_press = lambda target, rig=None: (None, "no rig file")
        self.assertEqual(lineimport.run(self.records, self.export, "new_rig"), "no rig file")
        self.assertEqual(self.calls, [])

    def test_a_cancel_while_exporting_imports_nothing(self):
        self.cancel_after = 1
        text = lineimport.run(self.records, self.export, "new_rig")
        self.assertNotIn("import", self.kinds())
        self.assertIn("cancelled", text)

    def test_a_cancel_while_retargeting_keeps_the_done_and_discards_the_rest(self):
        self.cancel_after = 7          # 3 exports + 3 imports + the first retarget
        text = lineimport.run(self.records, self.export, "new_rig")
        self.assertEqual([c[1] for c in self.calls if c[0] == "retarget"], ["A"])
        self.assertEqual(sorted(c[1] for c in self.calls if c[0] == "discard"), ["B", "C"])
        self.assertEqual(self.namespaces, set())
        self.assertIn("1 of 3 animations", text)
        self.assertIn("cancelled", text)

    def test_a_retarget_refusal_is_named_and_the_rest_go_on(self):
        real = rigimport.retarget_imported

        def refuse_b(rig, mod, namespace, info, source, name, place=None):
            if name == "B":
                return "", "B imported as B; retarget refused: no bone matches"
            return real(rig, mod, namespace, info, source, name, place)
        rigimport.retarget_imported = refuse_b
        text = lineimport.run(self.records, self.export, "new_rig")
        self.assertIn("Manny_Rig1 A, Manny_Rig3 C", text)
        self.assertIn("failed: B (B imported as B; retarget refused: no bone matches)", text)

    def test_nothing_picked(self):
        self.assertEqual(lineimport.run([], self.export, "new_rig"), "select an animation first")


class Words(unittest.TestCase):

    def test_first_only(self):
        self.assertEqual(lineimport.first_only(["A_Jump"]), "")
        self.assertEqual(lineimport.first_only(["A_Jump", "A_Walk", "A_Run"]),
                         "only A_Jump: a rig takes one animation (2 more picked)")

    def test_one_animation_reads_in_the_singular(self):
        text = lineimport.summary("new_rig", [("Manny_Rig1", "A")], 1, (0.0, 0.0, 0.0), [], [])
        self.assertTrue(text.startswith("1 animation onto 1 new rig in a line about (0, 0)"))

    def test_the_centre_is_rounded(self):
        text = lineimport.summary("skeleton", [("A", "A"), ("B", "B")], 2,
                                  (120.4, 0.0, -35.6), [], [])
        self.assertIn("about (120, -36)", text)
        self.assertIn("step 2.5 m", text)

    def test_nothing_laid_out(self):
        text = lineimport.summary("new_rig", [], 2, (0.0, 0.0, 0.0), [],
                                  [("A", "x"), ("B", "y")])
        self.assertTrue(text.startswith("no animation laid out"))
        self.assertIn("failed: A (x); B (y)", text)


if __name__ == "__main__":
    unittest.main()
