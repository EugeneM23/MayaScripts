"""Shared sends from the Cascadeur bridge, with a fake net. No network."""

import json
import os
import shutil
import tempfile
import unittest
import zipfile

from skeldar_cascadeur import shared
import maya_sharenet


class FakeNet(object):
    ShareError = maya_sharenet.ShareError

    def __init__(self, fail=False):
        self.published = []
        self.uploads = []
        self.fail = fail

    def publish(self, text, topic=None, base=None):
        self.published.append(text)
        return "id"

    def upload_any(self, path, progress=None):
        self.uploads.append(path)
        if self.fail:
            raise maya_sharenet.ShareError("temp.sh refused")
        return "https://temp.sh/abc/A_Jump.fbx.zip"


class Send(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="share_")
        self.fbx = os.path.join(self.folder, "A_Jump.fbx")
        with open(self.fbx, "wb") as handle:
            handle.write(b"FBX-DATA" * 10)

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def states(self, net):
        return [json.loads(text)["state"] for text in net.published]

    def test_sends_sending_then_ready_with_url(self):
        net = FakeNet()
        ready = shared.send(self.fbx, "A_Jump.fbx", "Yevhen", "PC", net=net,
                            now=lambda: 1000)
        self.assertEqual(self.states(net), ["sending", "ready"])
        self.assertEqual(ready["url"], "https://temp.sh/abc/A_Jump.fbx.zip")
        self.assertEqual(ready["from"], "Yevhen")
        self.assertEqual(ready["kind"], "fbx")

    def test_the_archive_is_removed_after_the_upload(self):
        net = FakeNet()
        shared.send(self.fbx, "A_Jump.fbx", "Y", "PC", net=net, now=lambda: 1)
        self.assertEqual(len(net.uploads), 1)
        self.assertFalse(os.path.exists(net.uploads[0]))

    def test_zip_helper_keeps_the_name(self):
        archive = shared.zip_fbx(self.fbx, "A_Jump.fbx", folder=self.folder)
        try:
            with zipfile.ZipFile(archive) as zipped:
                self.assertEqual(zipped.namelist(), ["A_Jump.fbx"])
        finally:
            os.remove(archive)

    def test_failure_publishes_failed_and_raises(self):
        net = FakeNet(fail=True)
        with self.assertRaises(maya_sharenet.ShareError):
            shared.send(self.fbx, "A_Jump.fbx", "Y", "PC", net=net,
                        now=lambda: 1)
        self.assertEqual(self.states(net), ["sending", "failed"])


if __name__ == "__main__":
    unittest.main()
