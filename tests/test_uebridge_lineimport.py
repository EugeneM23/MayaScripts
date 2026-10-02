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

from maya_uebridge import lineimport, lineup, rigimport, skeletonimport  # noqa: E402

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

        saved_si = dict((name, getattr(skeletonimport, name)) for name in (
            "precheck", "skeleton_entry", "onto_skeleton", "travel_scale"))
        self.addCleanup(lambda: [setattr(skeletonimport, k, v) for k, v in saved_si.items()])
        self.skeleton_refusal = ""
        skeletonimport.precheck = lambda entry=None: self.skeleton_refusal
        skeletonimport.skeleton_entry = lambda: types.SimpleNamespace(
            key="Manny", label="Manny UE5 [skeleton]")
        tops = iter(["root", "root1", "root2", "root3"])

        def onto_skeleton(entry, namespace, info, source, name, point=None, decide=None):
            self.calls.append(("onto", namespace, point, entry.label))
            self.namespaces.discard(namespace)
            return "%s onto %s" % (name, entry.label), "", next(tops)
        skeletonimport.onto_skeleton = onto_skeleton
        self.scales = {}                # clip name: the size its travel is baked at

        def travel_scale(source, target):
            self.calls.append(("scale", source, target))
            return self.scales.get(source.split(":")[0].lstrip("|"), 1.0)
        skeletonimport.travel_scale = travel_scale

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
        return [c[0] for c in self.calls if c[0] not in ("step", "scale")]

    def test_every_clip_leaves_the_editor_before_the_first_import(self):
        lineimport.run(self.records, self.export, "new_rig")
        kinds = self.kinds()
        self.assertEqual(kinds[:4], ["plan", "export", "export", "export"])
        self.assertEqual(kinds[4:7], ["import", "import", "import"])
        self.assertTrue(all(c[2] is False for c in self.calls if c[0] == "import"))

    def test_new_rigs_stand_in_a_square_in_list_order(self):
        """2026-10-01, «всегда ... в квадратной формации в не зависимости от
        угла камеры»: three clips on a 2 x 2 square on the world's axes."""
        text = lineimport.run(self.records, self.export, "new_rig")
        x = [lineup.side_extent(TRACKS[n], lineup.COLUMNS) for n in "ABC"]
        z = [lineup.side_extent(TRACKS[n], lineup.ROWS) for n in "ABC"]
        points = lineup.square_slots((0.0, 0.0, 0.0), x, z)
        got = [c for c in self.calls if c[0] == "retarget"]
        self.assertEqual([(c[1], c[2]) for c in got],
                         [("A", "Manny_Rig1"), ("B", "Manny_Rig2"), ("C", "Manny_Rig3")])
        self.assertEqual([c[3] for c in got], points)
        self.assertEqual([c[4] for c in got], [None, None, None])
        self.assertAlmostEqual(points[1][0] - points[0][0], 250.0)          # B reaches right
        self.assertGreater(points[0][2], points[2][2])                      # row 0 in front
        self.assertAlmostEqual(points[0][0], points[2][0])                  # columns aligned
        self.assertIn("3 animations onto 3 new rigs in a 2 x 2 square about (0, 0)", text)
        self.assertIn("Manny_Rig1 A, Manny_Rig2 B, Manny_Rig3 C", text)
        self.assertIn("widened beside B", text)

    def test_a_scaled_clip_is_laid_out_at_the_size_it_will_travel(self):
        """The fix pass, 2026-10-02: a CMU or metre-scale clip is baked at our
        size about its first frame, so its travel is read at that size before
        the square is laid out - or neighbours overlap. B first, so its reach
        (30 to the right, three times that baked) pushes the next column."""
        self.scales = {"B": 3.0}
        order = "BAC"
        records = [next(r for r in self.records if r.name == n) for n in order]
        lineimport.run(records, self.export, "new_rig")
        self.assertIn(("scale", "|B:root", "new_rig"), self.calls)
        tracks = dict((n, TRACKS[n]) for n in "AC")
        first = TRACKS["B"][0]
        tracks["B"] = [tuple(f + 3.0 * (c - f) for c, f in zip(p, first)) for p in TRACKS["B"]]
        x = [lineup.side_extent(tracks[n], lineup.COLUMNS) for n in order]
        z = [lineup.side_extent(tracks[n], lineup.ROWS) for n in order]
        points = [c[3] for c in self.calls if c[0] == "retarget"]
        self.assertEqual(points, lineup.square_slots((0.0, 0.0, 0.0), x, z))
        self.assertAlmostEqual(points[1][0] - points[0][0], 250.0 + 90.0)   # B's baked reach
        unscaled = lineup.square_slots((0.0, 0.0, 0.0),
                                       [lineup.side_extent(TRACKS[n], lineup.COLUMNS) for n in order],
                                       [lineup.side_extent(TRACKS[n], lineup.ROWS) for n in order])
        self.assertAlmostEqual(unscaled[1][0] - unscaled[0][0], 250.0 + 30.0)

    def test_the_skeleton_road_asks_for_its_own_scale(self):
        lineimport.run(self.records, self.export, "skeleton")
        self.assertIn(("scale", "|A:root", "skeleton"), self.calls)

    def test_about_a_point_whatever_the_camera(self):
        lineimport.run(self.records, self.export, "new_rig", centre=(100.0, 0.0, -40.0))
        points = [c[3] for c in self.calls if c[0] == "retarget"]
        here = lineup.square_slots((0.0, 0.0, 0.0),
                                   [lineup.side_extent(TRACKS[n], lineup.COLUMNS) for n in "ABC"],
                                   [lineup.side_extent(TRACKS[n], lineup.ROWS) for n in "ABC"])
        self.assertEqual(points, [(p[0] + 100.0, p[1], p[2] - 40.0) for p in here])

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

    def test_skeletons_are_the_characters_skeleton_on_the_square(self):
        """2026-10-01, addendum 3: each clip onto a new Characters skeleton
        standing on its slot; no rig is added."""
        text = lineimport.run(self.records, self.export, "skeleton")
        self.assertNotIn("plan", self.kinds())
        self.assertNotIn("add", self.kinds())
        onto = [c for c in self.calls if c[0] == "onto"]
        self.assertEqual([c[1] for c in onto], ["A", "B", "C"])
        self.assertEqual(set(c[3] for c in onto), {"Manny UE5 [skeleton]"})
        self.assertAlmostEqual(onto[0][2][0] + onto[1][2][0], 0.0)
        self.assertAlmostEqual(onto[0][2][2] + onto[2][2][2], 0.0)
        self.assertIn("3 animations onto 3 new Manny UE5 [skeleton] in a 2 x 2 square about "
                      "(0, 0): root A, root1 B, root2 C", text)

    def test_a_missing_skeleton_file_refuses_before_the_editor(self):
        self.skeleton_refusal = "no skeleton file - Creep_Skeleton.ma is missing from assets/"
        text = lineimport.run(self.records, self.export, "skeleton")
        self.assertEqual(text, self.skeleton_refusal)
        self.assertEqual(self.calls, [])

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
        text = lineimport.summary("new_rig", [("Manny_Rig1", "A")], 1, (0.0, 0.0, 0.0), [], [],
                                  shape=(1, 1))
        self.assertTrue(text.startswith("1 animation onto 1 new rig in a 1 x 1 square about (0, 0)"))

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
