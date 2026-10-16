import unittest

try:
    import maya.cmds  # noqa: F401
    HAVE_MAYA = True
except ImportError:
    HAVE_MAYA = False


@unittest.skipUnless(HAVE_MAYA, "needs maya.cmds importable")
class Renamed(unittest.TestCase):

    def test_maya_s_proc_is_defined_again_under_our_name(self):
        from maya_scenetabs import cameramenus
        text = "// x\nglobal proc buildPerspLookthruMenu( string $parent, string $panel )\n{ }\n"
        out = cameramenus.renamed(text, "buildPerspLookthruMenu")
        self.assertIn("global proc skeldarTabsOrig_buildPerspLookthruMenu(", out)
        self.assertNotIn("global proc buildPerspLookthruMenu(", out)
        self.assertIsNone(cameramenus.renamed("nothing", "buildPerspLookthruMenu"))

    def test_the_wrapper_calls_maya_s_and_prunes(self):
        from maya_scenetabs import cameramenus
        text = cameramenus.wrapper("buildOrthoLookthruMenu")
        self.assertIn("global proc buildOrthoLookthruMenu(string $parent, string $panel)", text)
        self.assertIn("skeldarTabsOrig_buildOrthoLookthruMenu($parent, $panel);", text)
        self.assertIn("_m.prune(", text)


if __name__ == "__main__":
    unittest.main()
