"""maya_filedrag: rows of Stash and Shared dragged between them and into the
scene (2026-10-21). The pure half here; the drag on a real QListWidget below.

Spec: docs/superpowers/specs/2026-10-21-stash-shared-drag-design.md
"""
import unittest

import maya_filedrag as fd


class SectionUnder(unittest.TestCase):

    def test_the_hub_s_list_and_a_popup_copy_s(self):
        self.assertEqual(fd.section_under(["skeldarStashList", "x"]), "stash")
        self.assertEqual(fd.section_under(["hubcopy3_skeldarShareList"]), "shared")

    def test_a_child_of_the_list_counts(self):
        self.assertEqual(fd.section_under(["qt_scrollarea_viewport", "skeldarShareList"]), "shared")

    def test_the_rail_icons(self):
        self.assertEqual(fd.section_under(["skeldarHubJump_stash", "rail"]), "stash")
        self.assertEqual(fd.section_under(["skeldarHubJump_shared"]), "shared")
        self.assertIsNone(fd.section_under(["skeldarHubJump_tools"]))

    def test_nothing_of_ours(self):
        self.assertIsNone(fd.section_under(["", "MayaWindow"]))
        self.assertIsNone(fd.section_under([]))


class AimFor(unittest.TestCase):

    def test_a_viewport_imports_from_either(self):
        for source in ("stash", "shared"):
            aim = fd.aim_for(source, None, True)
            self.assertEqual(aim["kind"], "import")
            self.assertEqual(aim["text"], "import into the scene")

    def test_the_other_section(self):
        self.assertEqual(fd.aim_for("stash", "shared", False)["kind"], "send")
        self.assertEqual(fd.aim_for("stash", "shared", False)["text"], "send to Shared")
        self.assertEqual(fd.aim_for("shared", "stash", False)["kind"], "stash")
        self.assertEqual(fd.aim_for("shared", "stash", False)["text"], "copy into Stash")

    def test_a_section_wins_over_a_viewport_behind_it(self):
        self.assertEqual(fd.aim_for("stash", "shared", True)["kind"], "send")

    def test_its_own_section_and_nowhere_are_nothing(self):
        self.assertEqual(fd.aim_for("stash", "stash", False)["kind"], "none")
        aim = fd.aim_for("shared", None, False)
        self.assertEqual(aim["kind"], "none")
        self.assertEqual(aim["text"], fd.NOWHERE)


class Caption(unittest.TestCase):

    def items(self, *names):
        return [fd.Item(n, "stash", n) for n in names]

    def test_one_and_several(self):
        aim = fd.aim_for("stash", "shared", False)
        self.assertEqual(fd.caption(self.items("A.fbx"), aim), ("A.fbx · send to Shared", True))
        self.assertEqual(fd.caption(self.items("A.fbx", "B.ma", "C.mb"), aim),
                         ("3 files · send to Shared", True))

    def test_nothing_is_muted(self):
        text, good = fd.caption(self.items("A.fbx"), fd.aim_for("stash", None, False))
        self.assertFalse(good)
        self.assertEqual(text, fd.NOWHERE)


class Pure(unittest.TestCase):

    def test_no_maya_or_qt_at_import(self):
        import subprocess, sys, os
        code = ("import sys; import maya_filedrag; "
                "bad = [m for m in sys.modules if m.split('.')[0] in ('maya', 'PySide6')]; "
                "sys.exit(1 if bad else 0)")
        plugin = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SkeldarAnim")
        self.assertEqual(subprocess.call([sys.executable, "-c", code], cwd=plugin), 0)


if __name__ == "__main__":
    unittest.main()
