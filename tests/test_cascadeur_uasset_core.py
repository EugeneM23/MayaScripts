"""The Maya-free helpers moved out of uassetexport. Neither Maya nor Unreal."""

import os
import stat
import subprocess
import sys
import tempfile
import unittest

from maya_uebridge import uasset_core


class ReadOnly(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="core_ro_")
        self.path = os.path.join(self.folder, "AS_X.uasset")
        with open(self.path, "wb") as handle:
            handle.write(b"x")

    def tearDown(self):
        os.chmod(self.path, stat.S_IWRITE | stat.S_IREAD)
        os.remove(self.path)
        os.rmdir(self.folder)

    def test_writable_file_is_not_read_only(self):
        self.assertFalse(uasset_core.is_read_only(self.path))

    def test_missing_file_is_not_read_only(self):
        self.assertFalse(uasset_core.is_read_only(self.path + ".nope"))

    def test_clear_read_only_makes_it_writable(self):
        os.chmod(self.path, stat.S_IREAD)
        self.assertTrue(uasset_core.is_read_only(self.path))
        self.assertEqual(uasset_core.clear_read_only(self.path), "")
        self.assertFalse(uasset_core.is_read_only(self.path))


class Staging(unittest.TestCase):

    def test_staging_path_names_the_clip(self):
        path = uasset_core.fbx_staging_path("A_Jump", r"C:\tmp")
        self.assertTrue(path.endswith("A_Jump.uasset.fbx"))

    def test_readonly_note(self):
        self.assertEqual(uasset_core.readonly_note(True), "read-only cleared")
        self.assertEqual(uasset_core.readonly_note(False), "")

    def test_lost_curves_named(self):
        self.assertIn("Pose_0..9", uasset_core.LOST_CURVES)


class Purity(unittest.TestCase):

    def test_uasset_core_imports_no_maya(self):
        plugin = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "SkeldarAnim")
        code = ("import sys; sys.path.insert(0, %r); "
                "import maya_uebridge.uasset_core as u; "
                "print('maya.cmds' in sys.modules, 'unreal' in sys.modules)") % plugin
        out = subprocess.check_output([sys.executable, "-c", code],
                                      cwd=plugin).decode().strip()
        self.assertEqual(out, "False False")


if __name__ == "__main__":
    unittest.main()
