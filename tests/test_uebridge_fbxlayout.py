"""Tests for the Cascadeur export layout (2026-09-25): the pure half, and the rules the scene
half rests on. The surgery itself is proven in a scene by verify_cascadeur_layout.py."""

import inspect
import math
import unittest

try:
    import maya.cmds  # noqa: F401  the real one: mayapy has it (trap 60)
    import maya.api.OpenMaya as om
except ImportError:  # pragma: no cover
    raise unittest.SkipTest("needs maya.api.OpenMaya")

from maya_uebridge import fbxlayout

TR = ("translateX", "translateY", "translateZ")
RO = ("rotateX", "rotateY", "rotateZ")


def kinds(t, r):
    return dict(list(zip(TR, t)) + list(zip(RO, r)))


def euler(e):
    return om.MEulerRotation(*[math.radians(v) for v in e]).asMatrix()


class Swizzle(unittest.TestCase):

    def test_is_the_translation_in_the_wrappers_space(self):
        """t' = t . W^-1 for W = Rx(-90): the wrapper then puts it back."""
        t = (1.0, 2.0, 3.0)
        back = om.MPoint(*fbxlayout.swizzled(t)) * euler(fbxlayout.WRAP_ROTATE)
        self.assertLess(max(abs(a - b) for a, b in zip((back.x, back.y, back.z), t)), 1e-12)
        self.assertEqual(fbxlayout.swizzled(t), (1.0, -3.0, 2.0))

    def test_is_cascadeurs_own_root_translation(self):
        """Measured: the Creep's root stands at (0.002, 0, 2.401) in Maya and Cascadeur's file
        writes (0.002, -2.401, 0) under its -90 X Null."""
        self.assertEqual(fbxlayout.swizzled((0.002, 0.0, 2.401)), (0.002, -2.401, 0.0))


class JointOrientAfter(unittest.TestCase):

    def test_our_roots_minus_ninety_becomes_zero(self):
        self.assertLess(max(abs(v) for v in fbxlayout.jo_after((-90.0, 0.0, 0.0))), 1e-9)

    def test_any_orient_keeps_the_world(self):
        """R . JO' . W == R . JO for any JO: the rotate curves need no edit."""
        jo = (12.0, -30.0, 47.0)
        got = euler(fbxlayout.jo_after(jo)) * euler(fbxlayout.WRAP_ROTATE)
        self.assertLess(max(abs(a - b) for a, b in zip(list(got), list(euler(jo)))), 1e-9)


class WrapperName(unittest.TestCase):
    """2026-09-25, the same evening: «появилось требование чтобы верхняя группа называлась
    Armature» -- one name for every character, in place of the character's own."""

    def test_the_wrapper_is_armature(self):
        self.assertEqual(fbxlayout.WRAPPER_NAME, "Armature")

    def test_the_per_character_naming_is_gone(self):
        for gone in ("wrapper_name", "character_name", "FALLBACK_NAME", "COLOUR_MARKER", "_colour_keys"):
            self.assertFalse(hasattr(fbxlayout, gone), gone)


class LayoutPlan(unittest.TestCase):

    def test_the_rigs_constrained_root(self):
        self.assertEqual(fbxlayout.layout_plan("", kinds(["constraint"] * 3, ["constraint"] * 3)),
                         ("constrained", ""))

    def test_a_keyed_root(self):
        self.assertEqual(fbxlayout.layout_plan("", kinds(["curve", None, "curve"], [None, "curve", None])),
                         ("keyed", ""))

    def test_a_root_with_nothing_on_it(self):
        self.assertEqual(fbxlayout.layout_plan("", kinds([None] * 3, [None] * 3)), ("static", ""))

    def test_a_pairblend_is_the_plain_layout(self):
        mode, reason = fbxlayout.layout_plan("", kinds(["pairBlend"] * 3, ["pairBlend"] * 3))
        self.assertIsNone(mode)
        self.assertIn("pairBlend", reason)

    def test_keys_and_a_constraint_together_is_the_plain_layout(self):
        mode, reason = fbxlayout.layout_plan("", kinds(["constraint", "curve", None], [None] * 3))
        self.assertIsNone(mode)
        self.assertIn("plain", reason)

    def test_a_root_under_a_parent_is_the_plain_layout(self):
        mode, reason = fbxlayout.layout_plan("|casc:SKM_Manny_Simple", kinds([None] * 3, [None] * 3))
        self.assertIsNone(mode)
        self.assertIn("SKM_Manny_Simple", reason)


class SceneHalf(unittest.TestCase):
    """The rules the surgery rests on; its behaviour is measured in verify_cascadeur_layout.py."""

    def test_root_goes_under_the_wrapper_without_compensation(self):
        """Maya's own compensation is not pose-preserving for a joint (2026-09-01)."""
        source = inspect.getsource(fbxlayout.wrapped)
        self.assertIn("relative=True", source)
        self.assertNotIn("relative=False", source)

    def test_everything_is_found_again_by_uuid_in_the_finally(self):
        source = inspect.getsource(fbxlayout.wrapped)
        self.assertIn("finally:", source)
        self.assertIn("uuid=True", source)

    def test_no_key_is_ever_edited(self):
        source = inspect.getsource(fbxlayout.wrapped) + inspect.getsource(fbxlayout._route_translate)
        for forbidden in ("keyframe(", "scaleKey", "setKeyframe", "cutKey"):
            self.assertNotIn(forbidden, source)

    def test_the_name_is_freed_and_checked(self):
        source = inspect.getsource(fbxlayout.wrapped)
        self.assertIn("HOLD_PREFIX", source)
        self.assertIn("!= name", source)

    def test_openmaya_is_imported_lazily(self):
        """The bridge's own tests install a fake `maya` with no `api`; animexport imports this."""
        source = inspect.getsource(fbxlayout)
        header = source.split("def ", 1)[0]
        self.assertNotIn("import maya.api", header)
