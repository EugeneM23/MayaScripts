"""The three flows over fake ports. No Cascadeur, Unreal or network."""

import os
import shutil
import stat
import tempfile
import unittest

from skeldar_cascadeur import actions
from skeldar_cascadeur import characters
from skeldar_cascadeur import prefs
from maya_uebridge import records


def clip(name="A_Jump", package="/Game/Anim/A_Jump", frames=45, fps=30.0):
    return records.AnimRecord(name=name, package=package, skeleton="", frames=frames,
                              length=1.5, fps=fps, source="unreal", path="",
                              clip="", fmt="")


class FakeUnreal(object):
    def __init__(self, reply=None):
        self.reply = reply if reply is not None else {
            "saved": True, "frames": 45, "error": "",
            "before_frames": 45, "before_length": 1.5, "length": 1.6}
        self.exports = []
        self.reimports = []

    def list_clips(self, out_dir, project=None, run_script=None):
        return "C:/P/Content", [clip()]

    def export_clip(self, record, out_dir, project=None, run_script=None):
        path = os.path.join(out_dir, record.name + ".fbx")
        with open(path, "wb") as handle:
            handle.write(b"fbx")
        self.exports.append(record.name)
        return path, {"ok": True}

    def reimport(self, package, fbx, out_dir, project=None, run_script=None):
        self.reimports.append((package, fbx))
        return self.reply


class FakeCascade(object):
    def __init__(self, roots=("root",), frames=45, fps=30.0):
        self.roots = list(roots)
        self.frames = frames
        self.fps = fps
        self.imported = []
        self.exported = []

    def import_clip_onto(self, character_path, clip_path):
        self.imported.append((character_path, clip_path))

    def export_skeleton(self, path):
        with open(path, "wb") as handle:
            handle.write(b"fbx")
        self.exported.append(path)

    def skeleton_roots(self):
        return list(self.roots)

    def animation_frames(self):
        return self.frames

    def scene_fps(self):
        return self.fps


class FakeShare(object):
    def __init__(self):
        self.sent = []

    def send(self, path, name, author, machine, net=None, now=None, progress=None):
        self.sent.append((path, name, author))
        return {"name": name, "url": "https://x", "zip": 10}


class Bridge(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="bridge_")
        self.temp = os.path.join(self.folder, "temp")
        os.makedirs(self.temp)
        self.uasset = os.path.join(self.folder, "Content", "Anim", "A_Jump.uasset")
        os.makedirs(os.path.dirname(self.uasset))
        with open(self.uasset, "wb") as handle:
            handle.write(b"uasset")
        self.asks = []
        self.ue = FakeUnreal()
        self.cs = FakeCascade()
        self.share = FakeShare()
        self.prefs = os.path.join(self.folder, "prefs.json")

    def tearDown(self):
        if os.path.exists(self.uasset):
            os.chmod(self.uasset, stat.S_IWRITE | stat.S_IREAD)
        shutil.rmtree(self.folder, ignore_errors=True)

    def make(self, ask_answer=True):
        def ask(text):
            self.asks.append(text)
            return ask_answer
        return actions.Bridge(self.ue, self.cs, self.share, self.prefs, self.temp,
                              ask, "PC", now=lambda: 1000)

    def with_target(self, bridge):
        bridge.target = clip()
        bridge.content_dir = os.path.join(self.folder, "Content")
        return bridge

    def test_refresh_lists_and_keeps_the_content_dir(self):
        bridge = self.make()
        text = bridge.refresh()
        self.assertEqual(bridge.content_dir, "C:/P/Content")
        self.assertEqual([r.name for r in bridge.records], ["A_Jump"])
        self.assertIn("1", text)

    def test_import_exports_then_imports_onto_the_chosen_character(self):
        bridge = self.make()
        bridge.refresh()
        bridge.choose_character(characters.default())
        text = bridge.import_clips([clip()])
        self.assertEqual(self.ue.exports, ["A_Jump"])
        self.assertEqual(len(self.cs.imported), 1)
        character_path, clip_path = self.cs.imported[0]
        self.assertEqual(character_path, characters.default().path)
        self.assertTrue(clip_path.endswith("A_Jump.fbx"))
        self.assertEqual(bridge.target.package, "/Game/Anim/A_Jump")
        self.assertIn("A_Jump on Manny UE5", text)
        self.assertEqual(prefs.get(self.prefs, "target"), "/Game/Anim/A_Jump")

    def test_import_without_a_character_refuses_and_writes_nothing(self):
        bridge = self.make()
        text = bridge.import_clips([clip()])
        self.assertEqual(text, actions.NO_CHARACTER)
        self.assertEqual(self.ue.exports, [])
        self.assertEqual(self.cs.imported, [])

    def test_export_refused_without_a_target(self):
        bridge = self.make()
        self.assertIn("no Unreal animation", bridge.export_to_uasset())
        self.assertEqual(self.cs.exported, [])

    def test_export_refused_with_several_skeletons_and_nothing_written(self):
        self.cs.roots = ["root", "Hips"]
        bridge = self.with_target(self.make())
        text = bridge.export_to_uasset()
        self.assertIn("2 skeletons", text)
        self.assertEqual(self.ue.reimports, [])

    def test_declined_confirm_writes_nothing(self):
        bridge = self.with_target(self.make(ask_answer=False))
        text = bridge.export_to_uasset()
        self.assertEqual(self.ue.reimports, [])
        self.assertEqual(self.cs.exported, [])
        self.assertIn("cancelled", text)

    def test_export_writes_back_and_reports_the_unchanged_warning(self):
        bridge = self.with_target(self.make())
        self.ue.reply = {"saved": True, "frames": 45, "before_frames": 45,
                         "before_length": 1.5, "length": 1.5, "error": ""}
        text = bridge.export_to_uasset()
        self.assertEqual(len(self.ue.reimports), 1)
        self.assertIn("did NOT change", text)

    def test_export_names_the_fps_when_it_differs(self):
        self.cs.fps = 24.0
        bridge = self.with_target(self.make())
        self.assertIn("24 fps", bridge.export_to_uasset())

    def test_read_only_uasset_is_cleared_after_the_export(self):
        os.chmod(self.uasset, stat.S_IREAD)
        bridge = self.with_target(self.make())
        text = bridge.export_to_uasset()
        self.assertIn("read-only cleared", text)
        self.assertTrue(os.access(self.uasset, os.W_OK))

    def test_send_exports_the_scene_then_sends(self):
        bridge = self.make()
        text = bridge.send_to_shared("A_Jump", "Yevhen")
        self.assertEqual(len(self.cs.exported), 1)
        self.assertEqual(self.share.sent[0][1], "A_Jump.fbx")
        self.assertEqual(self.share.sent[0][2], "Yevhen")
        self.assertIn("A_Jump.fbx", text)

    def test_send_needs_an_author(self):
        bridge = self.make()
        self.assertIn("author", bridge.send_to_shared("A", ""))
        self.assertEqual(self.share.sent, [])

    def test_author_is_remembered(self):
        bridge = self.make()
        bridge.send_to_shared("A", "Yevhen")
        self.assertEqual(prefs.get(self.prefs, "author"), "Yevhen")

    def test_plan_writes_nothing_and_names_the_asset(self):
        bridge = self.with_target(self.make())
        refusal, plan = bridge.plan_export()
        self.assertEqual(refusal, "")
        self.assertIn("/Game/Anim/A_Jump", plan.confirm_text)
        self.assertEqual(self.ue.reimports, [])
        self.assertEqual(self.cs.exported, [])

    def test_plan_refusal_has_no_plan(self):
        bridge = self.make()
        refusal, plan = bridge.plan_export()
        self.assertIn("no Unreal animation", refusal)
        self.assertIsNone(plan)

    def test_run_after_plan_writes_back(self):
        bridge = self.with_target(self.make())
        _refusal, plan = bridge.plan_export()
        text = bridge.run_export(plan)
        self.assertEqual(len(self.ue.reimports), 1)
        self.assertIn("reimported", text)

    def test_a_blocked_export_stops_the_write_back(self):
        class Blocked(FakeCascade):
            def export_skeleton(self, path):
                raise RuntimeError("licence does not allow FBX export")
        self.cs = Blocked()
        bridge = self.with_target(self.make())
        text = bridge.export_to_uasset()
        self.assertIn("licence", text)
        self.assertEqual(self.ue.reimports, [])

    def test_a_blocked_export_stops_the_send(self):
        class Blocked(FakeCascade):
            def export_skeleton(self, path):
                raise RuntimeError("licence does not allow FBX export")
        self.cs = Blocked()
        bridge = self.make()
        text = bridge.send_to_shared("A", "Yevhen")
        self.assertIn("licence", text)
        self.assertEqual(self.share.sent, [])


if __name__ == "__main__":
    unittest.main()
