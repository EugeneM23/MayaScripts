"""The Unreal side of the Cascadeur bridge, with a fake run_script. No editor."""

import os
import shutil
import tempfile
import unittest

from skeldar_cascadeur import unreal
from maya_uebridge import records


class FakeRun(object):
    """Records each call. For an export it writes the FBX a real export would
    write, at the path the export's own out-file name says it is for."""

    def __init__(self, reply, write_fbx=False):
        self.reply = reply
        self.write_fbx = write_fbx
        self.calls = []

    def __call__(self, source, out_path, project=None, **kwargs):
        self.calls.append((source, out_path, project))
        if self.write_fbx and os.path.basename(out_path).startswith("uexport_"):
            fbx = os.path.join(os.path.dirname(out_path),
                               os.path.basename(out_path)[len("uexport_"):-len(".json")]
                               + ".fbx")
            with open(fbx, "wb") as handle:
                handle.write(b"fbx")
        return self.reply


def clip(name="A_Jump", package="/Game/Anim/A_Jump"):
    return records.AnimRecord(name=name, package=package, skeleton="", frames=45,
                              length=1.5, fps=30.0, source="unreal", path="",
                              clip="", fmt="")


class Unreal(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="ue_")

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def test_safe_name_keeps_letters_digits_and_underscore(self):
        self.assertEqual(unreal.safe_name("A Jump/Q"), "A_Jump_Q")
        self.assertEqual(unreal.safe_name(""), "clip")

    def test_list_returns_content_dir_and_records(self):
        run = FakeRun({"content_dir": "C:/P/Content",
                       "assets": [{"name": "A_Jump",
                                   "package": "/Game/Anim/A_Jump",
                                   "frames": 45, "fps": 30.0}]})
        content, recs = unreal.list_clips(self.folder, project="P", run_script=run)
        self.assertEqual(content, "C:/P/Content")
        self.assertEqual([r.name for r in recs], ["A_Jump"])
        self.assertEqual(run.calls[0][2], "P")

    def test_export_returns_the_fbx_path_and_payload(self):
        run = FakeRun({"ok": True, "error": ""}, write_fbx=True)
        fbx, payload = unreal.export_clip(clip(), self.folder, run_script=run)
        self.assertTrue(fbx.endswith("A_Jump.fbx"))
        self.assertTrue(os.path.isfile(fbx))
        self.assertTrue(payload["ok"])

    def test_export_without_a_file_is_an_error_not_a_silent_success(self):
        run = FakeRun({"ok": False, "error": "no animation"}, write_fbx=False)
        with self.assertRaises(Exception) as caught:
            unreal.export_clip(clip(), self.folder, run_script=run)
        self.assertIn("A_Jump.fbx", str(caught.exception))

    def test_reimport_passes_the_package_and_fbx(self):
        run = FakeRun({"saved": True, "frames": 45, "error": ""})
        payload = unreal.reimport("/Game/Anim/A_Jump", r"C:\x\A_Jump.fbx",
                                  self.folder, run_script=run)
        self.assertTrue(payload["saved"])
        self.assertIn("/Game/Anim/A_Jump", run.calls[0][0])


if __name__ == "__main__":
    unittest.main()
