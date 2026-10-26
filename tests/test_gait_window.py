"""Gait Builder's window (docs/superpowers/plans/gaitbuilder/skeldar_gait.py): what a slider shows. Its pure
halves only - the window itself is proven in a GUI Maya by verify_gait_window.py."""

import types
import unittest

from tests.test_gait_model import load

try:
    import maya.cmds   # noqa: F401  (the window imports it; mayapy has it)
    tool = load("skeldar_gait")
except ImportError:                                  # pragma: no cover - outside mayapy
    tool = None


def fake_asp(left, right):
    knob = types.SimpleNamespace(sided=True, kind="measured")
    return types.SimpleNamespace(BY_NAME={"lift": knob},
                                 value=lambda gait, base, name, side=None: {"l": left, "r": right}[side])


@unittest.skipIf(tool is None, "needs maya.cmds")
class SliderStep(unittest.TestCase):

    def test_by_the_range(self):
        self.assertEqual(tool._slider_step(0.0, 2.0), (0.01, 2))
        self.assertEqual(tool._slider_step(0.0, 20.0), (0.1, 1))
        self.assertEqual(tool._slider_step(40.0, 120.0), (0.5, 1))


@unittest.skipIf(tool is None, "needs maya.cmds")
class SideMark(unittest.TestCase):
    state = {"gait": {}, "side": "both"}

    def test_sides_that_agree_at_the_shown_digits_are_one_value(self):
        # CAT Run's own feet lift 55.214 / 55.214 cm, apart in the fifth digit
        value, marked = tool._display(fake_asp(55.21412, 55.21398), {}, self.state, "lift", 1)
        self.assertAlmostEqual(value, 55.21405)
        self.assertFalse(marked)

    def test_sides_that_differ_where_it_shows_are_marked(self):
        self.assertTrue(tool._display(fake_asp(43.91, 44.43), {}, self.state, "lift", 1)[1])

    def test_one_side_shown_is_never_marked(self):
        for side in ("l", "r"):
            self.assertFalse(tool._display(fake_asp(43.91, 44.43), {}, {"gait": {}, "side": side}, "lift", 1)[1])


@unittest.skipIf(tool is None, "needs maya.cmds")
class Sources(unittest.TestCase):

    def test_a_walk_moved_into_the_library_is_listed_once_as_its_card(self):
        import sys
        gl = types.SimpleNamespace(label_of=lambda key: key.split("/")[-1][:-5])
        scene = types.SimpleNamespace(walk_names=lambda: ["asd", "dw", "sadda"])
        card = types.SimpleNamespace(path="lib/Walk cycles/asd.anim")
        store = types.SimpleNamespace(cards=lambda root, folder, recursive: ([card], []))
        cards = types.SimpleNamespace(library_root=lambda cmds: "lib", WALK_FOLDER="Walk cycles",
                                      relative=lambda path, root: path[len(root) + 1:])
        kept = tool._modules
        mods = dict((n, sys.modules.get(n)) for n in ("maya_poselib", "maya_poselib.store", "maya_walk.cards"))
        try:
            tool._modules = lambda: (gl, None, scene, None, None)
            sys.modules["maya_poselib"] = types.SimpleNamespace(store=store)
            sys.modules["maya_poselib.store"] = store
            sys.modules["maya_walk.cards"] = cards
            import maya_walk
            had = getattr(maya_walk, "cards", None)
            maya_walk.cards = cards
            labels = [label for _, label in tool.sources()]
        finally:
            tool._modules = kept
            for n, m in mods.items():
                if m is None:
                    sys.modules.pop(n, None)
                else:
                    sys.modules[n] = m
            if had is not None:
                maya_walk.cards = had
        self.assertEqual(labels.count("asd"), 1)
        self.assertIn("dw", labels)
        self.assertIn("CAT Walk", labels)


if __name__ == "__main__":
    unittest.main()
